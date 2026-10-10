#include "xattr_value.h"
#include <fcntl.h>
#include <unistd.h>
#include <filesystem>
#include <map>
#include <mutex>
#include <vector>
#include <cerrno>
#include <climits>

namespace {
constexpr size_t CHUNK = 65536;
bool io(int fd, char* bytes, size_t n, u64 offset, bool write) {
  while (n) {
    ssize_t done = write ? pwrite(fd, bytes, n, (off_t)offset) : pread(fd, bytes, n, (off_t)offset);
    if (done < 0 && errno == EINTR) continue;
    if (done <= 0) { if (!done) errno = EIO; return false; }
    bytes += done, offset += done, n -= (size_t)done;
  }
  return true;
}
struct Store {
  int fd = -1;
  u64 end = 0;
  std::mutex mu;
  std::map<u64, u64> free;
  ~Store() { if (fd >= 0) close(fd); }
  bool allocate(u64 length, u64& start) {
    std::lock_guard<std::mutex> lock(mu);
    for (auto it = free.begin(); it != free.end(); ++it) {
      if (it->second < length) continue;
      start = it->first;
      u64 remaining = it->second - length;
      free.erase(it);
      if (remaining) free.emplace(start + length, remaining);
      return true;
    }
    if (length > (u64)INT64_MAX - end) { errno = EFBIG; return false; }
    start = end, end += length;
    return true;
  }
  void release(u64 start, u64 length) {
    std::lock_guard<std::mutex> lock(mu);
    auto next = free.lower_bound(start);
    if (next != free.begin()) {
      auto previous = std::prev(next);
      if (previous->first + previous->second == start) {
        start = previous->first, length += previous->second;
        free.erase(previous);
      }
    }
    if (next != free.end() && start + length == next->first) {
      length += next->second;
      free.erase(next);
    }
    if (start + length == end) {
      end = start;
      (void)ftruncate(fd, (off_t)end);
    } else free.emplace(start, length);
  }
};
std::shared_ptr<Store> store() {
  static std::mutex mu;
  static std::weak_ptr<Store> current;
  std::lock_guard<std::mutex> lock(mu);
  if (auto value = current.lock()) return value;
  std::error_code error;
  auto directory = std::filesystem::temp_directory_path(error);
  if (error) { errno = error.value(); return {}; }
  auto name = (directory / "xsync-xattr-XXXXXX").string();
  int fd = mkstemp(name.data());
  if (fd < 0) return {};
  int saved = 0;
  if (fcntl(fd, F_SETFD, FD_CLOEXEC) != 0) saved = errno;
  if (unlink(name.c_str()) != 0 && !saved) saved = errno;
  if (saved) { close(fd); errno = saved; return {}; }
  auto value = std::make_shared<Store>();
  value->fd = fd;
  current = value;
  return value;
}
}

namespace {
std::atomic<size_t> inline_used{0};
constexpr size_t INLINE_BUDGET = 8 << 20;
}
struct XattrInline {
  std::string bytes;
  ~XattrInline() { inline_used.fetch_sub(bytes.size(), std::memory_order_relaxed); }
};
struct XattrBlob {
  std::shared_ptr<Store> store;
  u64 offset = 0, size = 0;
  ~XattrBlob() { if (store) store->release(offset, size); }
};

XattrValue::XattrValue(std::string bytes) {
  if (bytes.empty()) return;
  if (bytes.size() <= INLINE_MAX) {
    size_t used = inline_used.load(std::memory_order_relaxed);
    while (used <= INLINE_BUDGET - bytes.size()) {
      if (inline_used.compare_exchange_weak(used, used + bytes.size(), std::memory_order_relaxed)) {
        try { bytes_ = std::make_shared<XattrInline>(); }
        catch (...) { inline_used.fetch_sub(bytes.size(), std::memory_order_relaxed); throw; }
        bytes_->bytes = std::move(bytes);
        return;
      }
    }
  }
  auto backing = store();
  u64 offset;
  if (!backing || !backing->allocate(bytes.size(), offset)) throw std::system_error(errno, std::generic_category(), "xattr temporary storage");
  auto blob = std::make_shared<XattrBlob>();
  blob->store = backing, blob->offset = offset, blob->size = bytes.size();
  if (!io(backing->fd, bytes.data(), bytes.size(), offset, true)) throw std::system_error(errno, std::generic_category(), "write xattr temporary storage");
  blob_ = std::move(blob);
}

bool XattrValue::from_fd(int fd, u64 size, XattrValue& out) {
  if (size > (u64)INT64_MAX) { errno = EFBIG; return false; }
  XattrValue value;
  if (size <= INLINE_MAX) {
    std::string bytes((size_t)size, '\0');
    if (!io(fd, bytes.data(), bytes.size(), 0, false)) return false;
    try { value = XattrValue(std::move(bytes)); }
    catch (const std::system_error& error) { errno = error.code().value(); return false; }
  } else {
    auto backing = store();
    u64 offset;
    if (!backing || !backing->allocate(size, offset)) return false;
    auto blob = std::make_shared<XattrBlob>();
    blob->store = backing, blob->offset = offset, blob->size = size;
    std::vector<char> bytes(CHUNK);
    for (u64 pos = 0; pos < size;) {
      size_t n = (size_t)std::min<u64>(bytes.size(), size - pos);
      if (!io(fd, bytes.data(), n, pos, false) || !io(backing->fd, bytes.data(), n, offset + pos, true)) return false;
      pos += n;
    }
    value.blob_ = std::move(blob);
  }
  out = std::move(value);
  return true;
}
bool XattrValue::allocate(u64 size, XattrValue& out) {
  if (!size || size > (u64)INT64_MAX) { errno = EINVAL; return false; }
  auto backing = store();
  u64 offset;
  if (!backing || !backing->allocate(size, offset)) return false;
  auto blob = std::make_shared<XattrBlob>();
  blob->store = backing, blob->offset = offset, blob->size = size;
  out.bytes_.reset();
  out.blob_ = std::move(blob);
  return true;
}
bool XattrValue::write(const char* bytes, size_t n, u64 offset) {
  if (!blob_ || offset > size() || n > size() - offset) { errno = EINVAL; return false; }
  return io(blob_->store->fd, const_cast<char*>(bytes), n, blob_->offset + offset, true);
}
const std::string& XattrValue::inline_bytes() const {
  static const std::string empty;
  return bytes_ ? bytes_->bytes : empty;
}
u64 XattrValue::size() const { return blob_ ? blob_->size : inline_bytes().size(); }
bool XattrValue::read(char* bytes, size_t n, u64 offset) const {
  if (offset > size() || n > size() - offset) { errno = EINVAL; return false; }
  if (blob_) return io(blob_->store->fd, bytes, n, blob_->offset + offset, false);
  if (n) memcpy(bytes, inline_bytes().data() + offset, n);
  return true;
}
bool XattrValue::append_to(std::string& output) const {
  std::vector<char> bytes(CHUNK);
  for (u64 pos = 0; pos < size();) {
    size_t n = (size_t)std::min<u64>(bytes.size(), size() - pos);
    if (!read(bytes.data(), n, pos)) return false;
    output.append(bytes.data(), n);
    pos += n;
  }
  return true;
}
bool XattrValue::operator==(const XattrValue& other) const {
  if (size() != other.size()) return false;
  if (!blob_ && !other.blob_) return bytes_ == other.bytes_ || inline_bytes() == other.inline_bytes();
  if (blob_ && blob_ == other.blob_) return true;
  // musl workers have a small default stack. Reserve these comparison buffers
  // only for stored values, on the heap; two 64 KiB arrays exceed that stack.
  std::vector<char> buffers(2 * CHUNK);
  char* a = buffers.data();
  char* b = a + CHUNK;
  for (u64 pos = 0; pos < size();) {
    size_t n = (size_t)std::min<u64>(CHUNK, size() - pos);
    if (!read(a, n, pos) || !other.read(b, n, pos)) throw std::system_error(errno, std::generic_category(), "read xattr temporary storage");
    if (memcmp(a, b, n)) return false;
    pos += n;
  }
  return true;
}
