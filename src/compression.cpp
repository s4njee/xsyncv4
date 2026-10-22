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

void CompressionLink::observe(uint64_t count, uint64_t elapsed, Transport state, uint64_t now, uint64_t rate_limit) {
  if (!count || !elapsed) return;
  nanoseconds.fetch_add(elapsed, std::memory_order_relaxed);
  bytes.fetch_add(count, std::memory_order_relaxed);

  // Kept up for long enough: the level in force is more than this machine can
  // sustain here. Counted in bytes, so a phase that writes little proves nothing.
  if (state != Transport::keeping_up) {
    keeping_up_bytes_ = 0;
  } else {
    if (!keeping_up_bytes_) keeping_up_since_ = now - elapsed;
    keeping_up_bytes_ += count;
    if (keeping_up_bytes_ >= DROP_BYTES) {
      int in_force = level(false, 0, rate_limit);
      if (in_force > 1 && now > keeping_up_since_) {
        sustained_ = (double)keeping_up_bytes_ * 1e9 / (double)(now - keeping_up_since_);
        cap.store(in_force == 6 ? 3 : 1, std::memory_order_relaxed);
      }
      keeping_up_bytes_ = 0;
    }
  }

  // A capped level is worth trying again only once the link is seen to carry
  // less than this machine produced at it.
  window_bytes_ += count;
  window_ns_ += elapsed;
  if (state == Transport::saturated) window_saturated_ += count;
  if (window_bytes_ < WINDOW_BYTES) return;
  if (cap.load(std::memory_order_relaxed) < 6 && window_saturated_ * 2 >= window_bytes_ &&
      (double)window_bytes_ * 1e9 / (double)window_ns_ < 0.9 * sustained_)
    cap.store(6, std::memory_order_relaxed);
  window_bytes_ = window_ns_ = window_saturated_ = 0;
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
  if (!total) return std::to_string(last_level.load(std::memory_order_relaxed)) + " (automatic)";
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

int CompressionLink::level(bool explicit_level, int requested, uint64_t rate_limit) const {
  if (explicit_level) return requested;
  uint64_t count = bytes.load(std::memory_order_relaxed), elapsed = nanoseconds.load(std::memory_order_relaxed);
  if (count < 256 * 1024 || elapsed < 1000000) return std::min(3, cap.load(std::memory_order_relaxed));
  double rate = (double)count * 1e9 / elapsed;
  if (rate_limit) rate = std::min(rate, (double)rate_limit);
  int chosen = rate >= 64 * 1024 * 1024 ? 1 : rate < 8 * 1024 * 1024 ? 6 : 3;
  return std::min(chosen, cap.load(std::memory_order_relaxed));
}

bool CompressionLink::automatic_pays() const {
  uint64_t count = bytes.load(std::memory_order_relaxed), elapsed = nanoseconds.load(std::memory_order_relaxed);
  if (count < 256 * 1024 || elapsed < 1000000) return true;
  return (double)count * 1e9 / elapsed < AUTO_RATE;
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
