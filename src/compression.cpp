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

void CompressionLink::observe(uint64_t count, uint64_t elapsed) {
  if (!count || !elapsed) return;
  nanoseconds.fetch_add(elapsed, std::memory_order_relaxed);
  bytes.fetch_add(count, std::memory_order_relaxed);
}

int CompressionLink::level(bool explicit_level, int requested, uint64_t rate_limit) const {
  if (explicit_level) return requested;
  uint64_t count = bytes.load(std::memory_order_relaxed), elapsed = nanoseconds.load(std::memory_order_relaxed);
  if (count < 256 * 1024 || elapsed < 1000000) return 3;
  double rate = (double)count * 1e9 / elapsed;
  if (rate_limit) rate = std::min(rate, (double)rate_limit);
  if (rate >= 64 * 1024 * 1024) return 1;
  if (rate < 8 * 1024 * 1024) return 6;
  return 3;
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
