#include "compression.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <zstd.h>

namespace {
char lower(char value) { return value >= 'A' && value <= 'Z' ? value + ('a' - 'A') : value; }
bool suffix_match(std::string_view pattern, std::string_view suffix) {
  size_t position = 0;
  for (size_t index = 0; index < pattern.size(); ++index) {
    if (position == suffix.size()) return false;
    if (pattern[index] == '[') {
      size_t end = pattern.find(']', index + 1);
      if (pattern.substr(index + 1, end - index - 1).find(suffix[position]) == pattern.npos) return false;
      index = end;
    } else if (pattern[index] != suffix[position]) return false;
    ++position;
  }
  return position == suffix.size();
}
}

bool CompressionSuffixes::assign(std::string_view list) {
  if (list.size() > 65536 || list.find('\0') != list.npos) return false;
  std::unordered_set<std::string> literals;
  std::vector<std::string> classes;
  size_t start = 0;
  while (start < list.size()) {
    size_t end = list.find('/', start);
    if (end == list.npos) end = list.size();
    std::string pattern(list.substr(start, end - start));
    std::transform(pattern.begin(), pattern.end(), pattern.begin(), lower);
    bool has_class = false;
    for (size_t index = 0; index < pattern.size(); ++index) {
      if (pattern[index] == ']') return false;
      if (pattern[index] != '[') continue;
      size_t close = pattern.find(']', index + 1);
      if (close == pattern.npos || close == index + 1 || pattern.find('[', index + 1) < close) return false;
      has_class = true; index = close;
    }
    if (!pattern.empty()) {
      if (has_class) classes.push_back(std::move(pattern));
      else literals.insert(std::move(pattern));
    }
    start = end + 1;
  }
  literals_ = std::move(literals); classes_ = std::move(classes);
  initialized_ = true;
  return true;
}

bool CompressionSuffixes::matches(std::string_view name) const {
  if (!initialized_) {
    static const CompressionSuffixes defaults = [] {
      CompressionSuffixes result; result.assign(DEFAULT_SKIP_COMPRESS); return result;
    }();
    return defaults.matches(name);
  }
  size_t dot = name.rfind('.'), slash = name.rfind('/');
  if (dot == name.npos || (slash != name.npos && dot < slash) || dot + 1 == name.size()) return false;
  std::string suffix(name.substr(dot + 1));
  std::transform(suffix.begin(), suffix.end(), suffix.begin(), lower);
  if (literals_.count(suffix)) return true;
  for (const auto& pattern : classes_) if (suffix_match(pattern, suffix)) return true;
  return false;
}

void CompressionLink::observe(uint64_t count, uint64_t elapsed, Transport state, uint64_t now) {
  if (!count) return;
  if (!bytes_) window_start_ = now - elapsed;
  bytes_ += count;
  nanoseconds_ += elapsed;
  if (state == Transport::saturated) saturated_bytes_ += count;
  if (state == Transport::starved) starved_ = true;
  // Do not infer anything from tiny acknowledgments, or from less than a window.
  if (bytes_ < MIN_BYTES || (bytes_ < WINDOW_BYTES && nanoseconds_ < WINDOW_NS)) return;
  uint64_t wall = now - window_start_;
  int level = current.load(std::memory_order_relaxed);
  if (saturated_bytes_ * 2 >= bytes_) {
    starved_ns_ = 0;
    double rate = nanoseconds_ ? (double)bytes_ * 1e9 / (double)nanoseconds_ : (double)FAST;
    if (awaiting_ceiling_) ceiling_ = rate, awaiting_ceiling_ = false;
    int target = rate >= (double)FAST ? 1 : rate < (double)SLOW ? 6 : 3;
    if (target < level) {
      level = level == 6 ? 3 : 1;
      slow_ns_ = 0;
    } else if (target > level) {
      slow_ns_ += nanoseconds_;
      if (slow_ns_ >= RAISE_NS && (ceiling_ == 0 || rate < 0.75 * ceiling_)) {
        level = level == 1 ? 3 : 6;
        slow_ns_ = 0;
        ceiling_ = 0;
      }
    } else {
      slow_ns_ = 0;
    }
  } else if (starved_ && !saturated_bytes_) {
    slow_ns_ = 0;
    starved_ns_ += wall;
    if (starved_ns_ >= DROP_NS && level > 1) {
      // This machine cannot compress this hard as fast as the transport drains.
      level = level == 6 ? 3 : 1;
      starved_ns_ = 0;
      awaiting_ceiling_ = true;
    }
  } else {
    starved_ns_ -= std::min(starved_ns_, wall);  // occasional starvation is not a verdict
  }
  current.store(level, std::memory_order_relaxed);
  bytes_ = nanoseconds_ = saturated_bytes_ = 0;
  starved_ = false;
}

std::string CompressionLink::summary() const {
  static constexpr int levels[3] = {1, 3, 6};
  uint64_t bytes[3], total = 0;
  size_t most = 0, used_levels = 0;
  for (size_t i = 0; i < 3; ++i) {
    bytes[i] = compressed_input[i].load(std::memory_order_relaxed);
    total += bytes[i];
    used_levels += bytes[i] != 0;
    if (bytes[i] > bytes[most]) most = i;
  }
  if (!total) return std::to_string(current.load(std::memory_order_relaxed)) + " (automatic)";
  std::string text = std::to_string(levels[most]) + " (automatic";
  if (used_levels < 2) return text + ")";
  const char* separator = "; ";
  for (size_t i = 0; i < 3; ++i) {
    if (!bytes[i]) continue;
    text += separator + ("level " + std::to_string(levels[i]) + ": " + std::to_string((bytes[i] * 100 + total / 2) / total) + "%");
    separator = ", ";
  }
  return text + " of compressed input)";
}

int CompressionLink::level(bool explicit_level, int requested) const {
  return explicit_level ? requested : current.load(std::memory_order_relaxed);
}

bool compression_worthwhile(std::string_view raw, void* context) {
  if (raw.size() < 16 * 1024) return true;
  constexpr size_t span = 2048;
  std::array<char, span * 4> sample;
  for (size_t index = 0; index < 4; ++index)
    memcpy(sample.data() + index * span, raw.data() + (raw.size() - span) * index / 3, span);
  std::array<char, ZSTD_COMPRESSBOUND(span * 4)> compressed;
  size_t size = ZSTD_compressCCtx((ZSTD_CCtx*)context, compressed.data(), compressed.size(), sample.data(), sample.size(), 1);
  return ZSTD_isError(size) || size < sample.size() * 95 / 100;
}
