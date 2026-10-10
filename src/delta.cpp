#include "delta.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <cmath>
#include <unordered_map>
#include <unordered_set>
#define XXH_INLINE_ALL
#include <xxhash.h>

namespace {
constexpr size_t READ_BUFFER = 1 << 20, LITERAL_BUFFER = 1 << 16;
constexpr i64 COPY_RUN = 8 << 20;

u32 weak_sum(const char* bytes, size_t size) {
  u32 a = 0, b = 0;
  for (size_t i = 0; i < size; ++i) { a += (u8)bytes[i]; b += a; }
  return (a & 65535) | (b << 16);
}
u32 roll(u32 sum, u8 old, u8 next, u32 size) {
  u32 a = ((sum & 65535) - old + next) & 65535;
  u32 b = ((sum >> 16) - size * old + a) & 65535;
  return a | (b << 16);
}
bool read_exact(int fd, char* bytes, size_t size, i64 offset) {
  while (size) {
    if (g_stop.load()) { errno = EINTR; return false; }
    ssize_t n = pread(fd, bytes, size, offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { if (!n) errno = ESTALE; return false; }
    bytes += n, size -= (size_t)n, offset += n;
  }
  return true;
}
bool write_exact(int fd, const char* bytes, size_t size, i64 offset) {
  while (size) {
    if (g_stop.load()) { errno = EINTR; return false; }
    ssize_t n = pwrite(fd, bytes, size, offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { if (!n) errno = EIO; return false; }
    bytes += n, size -= (size_t)n, offset += n;
  }
  return true;
}
struct StrongKey {
  u64 weak_length, strong;
  bool operator==(const StrongKey&) const = default;
};
struct KeyHash {
  size_t operator()(StrongKey key) const { return (size_t)(key.strong ^ (key.weak_length * 0x9e3779b97f4a7c15ULL)); }
};
}

bool DeltaSignature::valid() const {
  return size > 0 && block_size >= 1024 && block_size <= DELTA_MAX_BLOCK &&
         !blocks.empty() && blocks.size() <= DELTA_MAX_BLOCKS &&
         (u64)((size - 1) / block_size + 1) == blocks.size();
}
i64 DeltaSignature::length(u32 first, u32 count) const {
  if (!count || first >= blocks.size() || count > blocks.size() - first) return 0;
  i64 start = (i64)first * block_size;
  return std::min<i64>(size - start, (i64)count * block_size);
}
DeltaBasis::~DeltaBasis() { if (fd >= 0) close(fd); }

std::shared_ptr<DeltaBasis> destination_delta_basis(const std::string& path, bool snapshot) {
  auto parent = destination_path(path);
  if (parent.fd < 0) return {};
  int fd = openat(parent.fd, parent.name.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK | read_time_flags());
  if (fd < 0) return {};
  auto basis = std::make_shared<DeltaBasis>();
  basis->fd = fd;
  struct stat before;
  if (fstat(fd, &before) != 0 || !S_ISREG(before.st_mode) || before.st_size < 1024) return {};
  auto& signature = basis->signature;
  signature.size = before.st_size;
  // Larger blocks trade a little literal data around edits for fewer reverse signatures.
  signature.block_size = (u32)std::clamp<double>(2 * std::sqrt((double)signature.size), 1024, DELTA_MAX_BLOCK) & ~u32(7);
  u64 count = (u64)((signature.size - 1) / signature.block_size + 1);
  if (count > DELTA_MAX_BLOCKS) { errno = EFBIG; return {}; }
  int copy = -1;
  if (snapshot) {
    for (unsigned attempt = 0; attempt < 100; ++attempt) {
      std::string name = ".xsync-basis-" + std::to_string(getpid()) + "-" + std::to_string(now_ns()) + "-" + std::to_string(attempt);
      copy = openat(parent.fd, name.c_str(), O_RDWR | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
      if (copy >= 0) {
        if (unlinkat(parent.fd, name.c_str(), 0) != 0) { close(copy); return {}; }
        break;
      }
      if (errno != EEXIST) return {};
    }
    if (copy < 0) return {};
  }
  signature.blocks.resize((size_t)count);
  std::vector<char> bytes(signature.block_size);
  bool ok = true;
  for (u32 i = 0; i < count; ++i) {
    size_t size = (size_t)signature.length(i);
    i64 offset = (i64)i * signature.block_size;
    if (!read_exact(fd, bytes.data(), size, offset) || (copy >= 0 && !write_exact(copy, bytes.data(), size, offset))) { ok = false; break; }
    signature.blocks[i] = {weak_sum(bytes.data(), size), XXH3_64bits(bytes.data(), size)};
  }
  if (ok) ok = source_unchanged(fd, path, before);
  int error = errno;
  if (!ok) { if (copy >= 0) close(copy); errno = error; return {}; }
  if (copy >= 0) { close(basis->fd); basis->fd = copy; }
  return basis;
}

std::shared_ptr<DeltaBasis> readonly_delta_basis(int fd) {
  if (fd < 0) return {};
  auto basis = std::make_shared<DeltaBasis>();
  basis->fd = fd;
  struct stat before;
  if (fstat(fd, &before) != 0 || !S_ISREG(before.st_mode) || before.st_size < 1024) return {};
  auto& signature = basis->signature;
  signature.size = before.st_size;
  signature.block_size = (u32)std::clamp<double>(2 * std::sqrt((double)signature.size), 1024, DELTA_MAX_BLOCK) & ~u32(7);
  u64 count = (u64)((signature.size - 1) / signature.block_size + 1);
  if (count > DELTA_MAX_BLOCKS) { errno = EFBIG; return {}; }
  signature.blocks.resize((size_t)count);
  std::vector<char> bytes(signature.block_size);
  for (u32 index = 0; index < count; ++index) {
    size_t size = (size_t)signature.length(index);
    if (!read_exact(fd, bytes.data(), size, (i64)index * signature.block_size)) return {};
    signature.blocks[index] = {weak_sum(bytes.data(), size), XXH3_64bits(bytes.data(), size)};
  }
  struct stat after;
  Entry first, last;
  entry_from_stat(before, first);
  if (fstat(fd, &after) != 0) return {};
  entry_from_stat(after, last);
  if (first.size != last.size || first.mtime != last.mtime || first.mtime_ns != last.mtime_ns ||
      first.ctime != last.ctime || first.ctime_ns != last.ctime_ns) { errno = ESTALE; return {}; }
  return basis;
}

DeltaResult delta_match_fd(int fd, i64 size, const DeltaSignature& signature,
                          const std::function<bool(const DeltaOp&)>& emit) {
  DeltaResult result;
  if (size < 0 || !signature.valid()) { errno = EINVAL; return result; }
  std::unordered_set<u64> weak_keys;
  std::unordered_map<StrongKey, std::vector<u32>, KeyHash> matches;
  for (u32 i = 0; i < signature.blocks.size(); ++i) {
    const auto& block = signature.blocks[i];
    u64 key = ((u64)signature.length(i) << 32) | block.weak;
    weak_keys.insert(key);
    matches[{key, block.strong}].push_back(i);
  }
  std::vector<char> bytes(READ_BUFFER + signature.block_size + 1);
  size_t begin = 0, end = 0;
  i64 position = 0;
  auto ensure = [&](size_t wanted) {
    if (end - begin >= wanted) return true;
    size_t left = end - begin;
    memmove(bytes.data(), bytes.data() + begin, left);
    begin = 0, end = left;
    size_t want = (size_t)std::min<i64>((i64)bytes.size() - (i64)left, size - position - (i64)left);
    if (want && !read_exact(fd, bytes.data() + end, want, position + (i64)left)) return false;
    end += want;
    return end >= wanted;
  };
  XXH3_state_t digest;
  XXH3_128bits_reset(&digest);
  std::string literal;
  literal.reserve(LITERAL_BUFFER);
  DeltaOp copy;
  u32 next_index = 0;
  bool emitter_failed = false;
  auto flush_literal = [&] {
    if (literal.empty()) return true;
    DeltaOp op{position - (i64)literal.size(), 0, 0, literal};
    if (!emit(op)) { emitter_failed = true; return false; }
    XXH3_128bits_update(&digest, literal.data(), literal.size());
    result.processed += (i64)literal.size();
    result.literal_bytes += (i64)literal.size();
    literal.clear();
    return true;
  };
  auto flush_copy = [&] {
    if (!copy.count) return true;
    if (!emit(copy)) { emitter_failed = true; return false; }
    result.processed += signature.length(copy.first, copy.count);
    copy.count = 0;
    return true;
  };
  u32 full_sum = 0, tail_sum = 0;
  u32 tail = (u32)(signature.size % signature.block_size);
  bool sums_ready = false, failed = false;
  while (position < size) {
    u32 full = (u32)std::min<i64>(signature.block_size, size - position);
    if (!ensure((size_t)full + (position + full < size))) { failed = true; break; }
    const char* window = bytes.data() + begin;
    if (!sums_ready) {
      full_sum = weak_sum(window, full);
      if (tail && tail <= full) tail_sum = weak_sum(window, tail);
    }
    u32 index = 0, length = 0;
    for (u32 len : {full, tail}) {
      if (!len || len > full) continue;
      u32 weak = len == full ? full_sum : tail_sum;
      u64 key = ((u64)len << 32) | weak;
      if (!weak_keys.contains(key)) continue;
      auto match = matches.find({key, XXH3_64bits(window, len)});
      if (match == matches.end()) continue;
      const auto& indices = match->second;
      index = std::binary_search(indices.begin(), indices.end(), next_index) ? next_index : indices.front();
      length = len;
      break;
    }
    if (length) {
      if (!flush_literal()) { failed = true; break; }
      if (copy.count && (copy.first + copy.count != index || signature.length(copy.first, copy.count) + length > COPY_RUN))
        if (!flush_copy()) { failed = true; break; }
      if (!copy.count) copy = {position, index, 0, {}};
      copy.count++;
      XXH3_128bits_update(&digest, window, length);
      position += length, begin += length;
      next_index = index + 1;
      sums_ready = false;
    } else {
      if (!flush_copy()) { failed = true; break; }
      literal.push_back(window[0]);
      if (position + full < size) {
        full_sum = roll(full_sum, (u8)window[0], (u8)window[full], full);
        if (tail) tail_sum = roll(tail_sum, (u8)window[0], (u8)window[tail], tail);
        sums_ready = true;
      } else {
        u32 a = ((full_sum & 65535) - (u8)window[0]) & 65535;
        u32 b = ((full_sum >> 16) - full * (u8)window[0]) & 65535;
        full_sum = a | (b << 16);
        if (tail && tail < full) tail_sum = roll(tail_sum, (u8)window[0], (u8)window[tail], tail);
        sums_ready = true;
      }
      position++, begin++;
      if (literal.size() >= LITERAL_BUFFER && !flush_literal()) { failed = true; break; }
    }
    if (g_stop.load()) { errno = EINTR; failed = true; break; }
  }
  int error = failed ? errno : 0;
  // A short source read still reports a contiguous prefix that the receiver can drain.
  bool emitted = !emitter_failed && flush_copy() && flush_literal();
  if (!emitted && !error) error = errno;
  auto sum = XXH3_128bits_digest(&digest);
  result.sum[0] = sum.low64, result.sum[1] = sum.high64;
  result.ok = !failed && emitted && result.processed == size;
  if (!result.ok) errno = error ? error : EIO;
  return result;
}

bool delta_copy_blocks(OutFile& output, const DeltaBasis& basis, u32 first, u32 count,
                       i64 offset, std::vector<char>& scratch) {
  if (offset < 0 || !basis.signature.length(first, count)) { errno = EINVAL; return false; }
  scratch.resize(basis.signature.block_size);
  for (u32 i = first; i < first + count; ++i) {
    size_t size = (size_t)basis.signature.length(i);
    if (!read_exact(basis.fd, scratch.data(), size, (i64)i * basis.signature.block_size)) return false;
    if (XXH3_64bits(scratch.data(), size) != basis.signature.blocks[i].strong) { errno = ESTALE; return false; }
    if (!out_write(output, scratch.data(), size, offset)) return false;
    offset += (i64)size;
  }
  return true;
}

bool delta_verify_fd(int fd, i64 size, const u64 sum[2]) {
  u64 actual[2];
  if (!hash_prefix_fd(fd, size, actual)) return false;
  if (actual[0] == sum[0] && actual[1] == sum[1]) return true;
  errno = EBADMSG;
  return false;
}
