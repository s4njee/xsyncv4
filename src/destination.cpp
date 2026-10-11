#include "destination.h"
#include <fcntl.h>
#include <filesystem>
#include <cerrno>
#include <algorithm>
#include <atomic>
#include <sys/resource.h>
#include <cstdio>
#ifdef __linux__
#include <sys/syscall.h>
#endif
#ifdef __APPLE__
#include <sys/clonefile.h>
#include <sys/attr.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <atomic>
#include <cstring>
#include <cstddef>
#endif

namespace {
int root_fd = -1;
std::string root_path;
thread_local DestinationDirectory* directory_pin = nullptr;
std::atomic<unsigned> retained_parents{0};
unsigned parent_budget() {
  static const unsigned budget = [] {
    rlimit limit{};
    if (getrlimit(RLIMIT_NOFILE, &limit) != 0 || limit.rlim_cur < 512) return 0u;
    return (unsigned)std::min<rlim_t>(256, limit.rlim_cur / 8);
  }();
  return budget;
}
std::string absolute(const std::string& path) {
  // Already-normalized engine paths need no filesystem::path component objects.
  if (!path.empty() && path.front() == '/') {
    bool normalized = true;
    for (size_t start = 1; start < path.size();) {
      size_t end = path.find('/', start);
      if (end == std::string::npos) end = path.size();
      size_t length = end - start;
      if (!length || (length == 1 && path[start] == '.') ||
          (length == 2 && path[start] == '.' && path[start + 1] == '.')) {
        normalized = false;
        break;
      }
      start = end + 1;
    }
    if (normalized) {
      std::string result = path;
      while (result.size() > 1 && result.back() == '/') result.pop_back();
      return result;
    }
  }
  std::error_code error;
  auto p = std::filesystem::absolute(path.empty() ? "." : path, error);
  if (error) { errno = error.value(); return {}; }
  auto result = p.lexically_normal().string();
  while (result.size() > 1 && result.back() == '/') result.pop_back();
  return result;
}
int walk(int fd, std::string_view rel) {
  for (size_t start = 0; start < rel.size();) {
    size_t end = rel.find('/', start);
    if (end == std::string_view::npos) end = rel.size();
    std::string name(rel.substr(start, end - start));
    start = end + 1;
    if (name.empty() || name == ".") continue;
    if (name == "..") { close(fd); errno = EPERM; return -1; }
    int next = openat(fd, name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    int error = errno;
    close(fd);
    if (next < 0) { errno = error; return -1; }
    fd = next;
  }
  return fd;
}
}

bool anchor_destination(const std::string& path) {
  if (root_fd >= 0) return true;
  std::string existing = absolute(path);
  if (existing.empty()) return false;
  struct stat st;
  while (stat(existing.c_str(), &st) != 0 || !S_ISDIR(st.st_mode)) {
    auto parent = std::filesystem::path(existing).parent_path().string();
    if (parent.empty() || parent == existing) return false;
    existing = std::move(parent);
  }
  for (;;) {
    std::error_code error;
    auto resolved = std::filesystem::canonical(existing, error);
    if (error) { errno = error.value(); return false; }
    int fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (fd < 0) return false;
    fd = walk(fd, resolved.relative_path().native());
    if (fd >= 0) {
      root_path = existing;
      root_fd = fd;
      return true;
    }
    // A mode-000 destination can be repaired through its accessible parent.
    // Descendant operations still use NOFOLLOW from that pinned parent.
    if (errno != EACCES) return false;
    auto parent = std::filesystem::path(existing).parent_path().string();
    if (parent.empty() || parent == existing) return false;
    existing = std::move(parent);
  }
}

DestPath destination_path_impl(const std::string& path, bool owned) {
  auto p = absolute(path);
  if (root_fd < 0 || p.empty() || (p != root_path &&
      !(p.starts_with(root_path) && (root_path == "/" || p[root_path.size()] == '/')))) {
    errno = EPERM;
    return {};
  }
  auto suffix = [&](const std::string& path) -> std::string_view {
    size_t offset = path == "/" ? 1 : p == path ? p.size() : path.size() + 1;
    return std::string_view(p).substr(offset);
  };
  std::string_view rel = suffix(root_path);
  int base = root_fd;
  if (directory_pin && (p == directory_pin->path_ ||
      (p.starts_with(directory_pin->path_) &&
       (directory_pin->path_ == "/" || p[directory_pin->path_.size()] == '/')))) {
    base = directory_pin->fd_;
    rel = suffix(directory_pin->path_);
  }
  size_t slash = rel.find_last_of('/');
  std::string name(slash == std::string_view::npos ? rel : rel.substr(slash + 1));
  if (name.empty()) name = ".";
  // Synchronous operations can use an existing pin directly. The public
  // lookup still owns its descriptor, and descendant walks still use NOFOLLOW.
  if (!owned && slash == std::string_view::npos)
    return {base, std::move(name), false};
  int fd = dup(base);
  if (fd < 0) return {};
  fd = walk(fd, slash == std::string_view::npos ? std::string_view() : rel.substr(0, slash));
  if (fd < 0) return {};
  return {fd, std::move(name)};
}

DestPath destination_path(const std::string& path) {
  return destination_path_impl(path, true);
}

int destination_open_dir(const char* path) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : openat(p.fd, p.name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
}
DestinationParent::~DestinationParent() {
  close(fd_);
  retained_parents.fetch_sub(1, std::memory_order_relaxed);
}
DestinationDirectory::DestinationDirectory(const std::string& path,
                                           const std::shared_ptr<const DestinationParent>& parent) {
  path_ = absolute(path);
  if (path_.empty()) return;
  if (parent && (path_ == parent->path_ || (path_.starts_with(parent->path_) &&
      (parent->path_ == "/" || path_[parent->path_.size()] == '/')))) {
    size_t offset = parent->path_ == "/" ? 1 : path_ == parent->path_ ? path_.size() : parent->path_.size() + 1;
    fd_ = fcntl(parent->fd_, F_DUPFD_CLOEXEC, 0);
    if (fd_ >= 0) fd_ = walk(fd_, std::string_view(path_).substr(offset));
  } else fd_ = destination_open_dir(path_.c_str());
  if (fd_ < 0) return;
  previous_ = directory_pin;
  directory_pin = this;
}
std::shared_ptr<const DestinationParent> DestinationDirectory::share() const {
  if (fd_ < 0) return {};
  unsigned count = retained_parents.load(std::memory_order_relaxed);
  do {
    if (count >= parent_budget()) return {};
  } while (!retained_parents.compare_exchange_weak(count, count + 1, std::memory_order_relaxed));
  int fd = fcntl(fd_, F_DUPFD_CLOEXEC, 0);
  if (fd < 0) {
    retained_parents.fetch_sub(1, std::memory_order_relaxed);
    return {};
  }
  return std::shared_ptr<const DestinationParent>(new DestinationParent(fd, path_));
}
DestinationDirectory::~DestinationDirectory() {
  if (fd_ >= 0) {
    directory_pin = previous_;
    close(fd_);
  }
}
int destination_stat(const char* path, struct stat* st) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : fstatat(p.fd, p.name.c_str(), st, AT_SYMLINK_NOFOLLOW);
}
int destination_named_stat(const char* path, struct stat* st) {
  struct Restore {
    DestinationDirectory* saved = directory_pin;
    ~Restore() { directory_pin = saved; }
  } restore;
  directory_pin = nullptr;
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : fstatat(p.fd, p.name.c_str(), st, AT_SYMLINK_NOFOLLOW);
}
int destination_publish_noreplace(int parent, const char* staged, const char* final) {
  return destination_rename_noreplace(parent, staged, parent, final);
}
int destination_rename_noreplace(int source_parent, const char* source, int destination_parent, const char* destination) {
#ifdef __APPLE__
  return renameatx_np(source_parent, source, destination_parent, destination, RENAME_EXCL);
#elif defined(__linux__) && defined(SYS_renameat2)
  return (int)syscall(SYS_renameat2, source_parent, source, destination_parent, destination, 1u /* RENAME_NOREPLACE */);
#else
  errno = ENOTSUP;
  return -1;
#endif
}
int destination_chmod(const char* path, mode_t mode) {
  auto p = destination_path_impl(path, false);
  if (p.fd < 0) return -1;
  if (p.name == ".") return fchmod(p.fd, mode);
#ifndef __APPLE__
  // Linux fchmodat(AT_SYMLINK_NOFOLLOW) is not available on older kernels.
  // Pin regular files/directories with O_NOFOLLOW, then change that object.
  struct stat st;
  if (fstatat(p.fd, p.name.c_str(), &st, AT_SYMLINK_NOFOLLOW) != 0) return -1;
  if (S_ISLNK(st.st_mode)) return 0; // Linux symlink modes are always 0777.
  int fd = openat(p.fd, p.name.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0) return -1;
  if (fstat(fd, &st) != 0 || S_ISLNK(st.st_mode)) { close(fd); errno = ELOOP; return -1; }
  // /proc/self/fd names the pinned object, including mode-000 files and devices,
  // and does not re-resolve the receiver-owned pathname.
  std::string pinned = "/proc/self/fd/" + std::to_string(fd);
  int result = chmod(pinned.c_str(), mode), error = errno;
  close(fd);
  errno = error;
  return result;
#else
  return fchmodat(p.fd, p.name.c_str(), mode, AT_SYMLINK_NOFOLLOW);
#endif
}
int destination_chown(const char* path, uid_t uid, gid_t gid) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : p.name == "." ? fchown(p.fd, uid, gid) :
    fchownat(p.fd, p.name.c_str(), uid, gid, AT_SYMLINK_NOFOLLOW);
}
int destination_times(const char* path, const timespec times[2]) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : p.name == "." ? futimens(p.fd, times) :
    utimensat(p.fd, p.name.c_str(), times, AT_SYMLINK_NOFOLLOW);
}
uint32_t blocking_fileflags(uint32_t flags) {
#ifdef __APPLE__
  return flags & (UF_IMMUTABLE | UF_APPEND | SF_IMMUTABLE | SF_APPEND | SF_NOUNLINK);
#else
  return 0;
#endif
}
int fd_fileflags(int fd, uint32_t flags, bool delay) {
#ifdef __APPLE__
  struct stat st;
  if (fstat(fd, &st) != 0) return -1;
  if (S_ISLNK(st.st_mode)) { errno = ELOOP; return -1; }
  // Existing immutable objects stay immutable unless the requested flags clear
  // them. New immutable bits wait until hard-link aliases have been published.
  if (delay) flags = (flags & ~blocking_fileflags(flags)) | blocking_fileflags(st.st_flags & flags);
  if (st.st_flags == flags) return 0;
  if (fchflags(fd, flags) != 0 || fstat(fd, &st) != 0) return -1;
  // Darwin silently ignores some storage/synthetic bits. Do not report that
  // the requested flags were preserved when the filesystem did not apply them.
  if (st.st_flags != flags) { errno = ENOTSUP; return -1; }
  return 0;
#else
  errno = ENOTSUP;
  return -1;
#endif
}
int destination_fileflags(const char* path, uint32_t flags, bool delay,
                          uint64_t expected_dev, uint64_t expected_ino) {
#ifdef __APPLE__
  auto p = destination_path_impl(path, false);
  if (p.fd < 0) return -1;
  struct stat socket_stat;
  if (fstatat(p.fd, p.name.c_str(), &socket_stat, AT_SYMLINK_NOFOLLOW) == 0 && S_ISSOCK(socket_stat.st_mode)) {
    if (expected_ino && ((uint64_t)socket_stat.st_dev != expected_dev || (uint64_t)socket_stat.st_ino != expected_ino)) {
      errno = ESTALE; return -1;
    }
    if (socket_stat.st_flags == flags) return 0;
  }
  int fd = p.name == "." ? p.release() :
    openat(p.fd, p.name.c_str(), O_EVTONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) return -1;
  struct stat st;
  int result = fstat(fd, &st);
  if (!result && expected_ino && ((uint64_t)st.st_dev != expected_dev || (uint64_t)st.st_ino != expected_ino))
    errno = ESTALE, result = -1;
  if (!result) result = fd_fileflags(fd, flags, delay);
  int error = errno;
  close(fd);
  errno = error;
  return result;
#else
  errno = ENOTSUP;
  return -1;
#endif
}

int fd_crtime(int fd, time_t seconds) {
#ifdef __APPLE__
  attrlist attributes{};
  attributes.bitmapcount = ATTR_BIT_MAP_COUNT;
  attributes.commonattr = ATTR_CMN_CRTIME;
  timespec time{seconds, 0};
  return fsetattrlist(fd, &attributes, &time, sizeof time, 0);
#else
  errno = ENOTSUP;
  return -1;
#endif
}
int destination_crtime(const char* path, time_t seconds) {
#ifdef __APPLE__
  auto p = destination_path_impl(path, false);
  if (p.fd < 0) return -1;
  if (p.name == ".") return fd_crtime(p.fd, seconds);
  // O_SYMLINK opens a link itself; combining it with O_NOFOLLOW rejects links.
  int fd = openat(p.fd, p.name.c_str(), O_EVTONLY | O_SYMLINK | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0) return -1;
  int result = fd_crtime(fd, seconds), error = errno;
  close(fd);
  errno = error;
  return result;
#else
  errno = ENOTSUP;
  return -1;
#endif
}
int destination_mkdir(const char* path, mode_t mode) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : mkdirat(p.fd, p.name.c_str(), mode);
}
int destination_unlink(const char* path) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : unlinkat(p.fd, p.name.c_str(), 0);
}
int destination_rmdir(const char* path) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : unlinkat(p.fd, p.name.c_str(), AT_REMOVEDIR);
}
int destination_symlink(const char* target, const char* path) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : symlinkat(target, p.fd, p.name.c_str());
}
ssize_t destination_readlink(const char* path, char* buf, size_t size) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : readlinkat(p.fd, p.name.c_str(), buf, size);
}
int destination_mknod(const char* path, mode_t mode, dev_t dev) {
  auto p = destination_path_impl(path, false);
  if (p.fd < 0) return -1;
#ifdef __APPLE__
  if (S_ISSOCK(mode)) {
    // Darwin has no bindat and /dev/fd cannot name a directory's children.
    // Only the child changes cwd; the threaded receiver keeps its cwd intact.
    // All child operations are async-signal-safe after fork.
    static std::atomic<unsigned long> sequence{0};
    std::string temp = ".xsync-socket-" + std::to_string(getpid()) + "-" + std::to_string(sequence.fetch_add(1));
    int reservation = openat(p.fd, temp.c_str(), O_CREAT | O_EXCL | O_WRONLY | O_CLOEXEC, 0600);
    if (reservation < 0) return -1;
    close(reservation);
    if (unlinkat(p.fd, temp.c_str(), 0) != 0) return -1;
    int socket_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (socket_fd < 0) return -1;
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    memcpy(address.sun_path, temp.c_str(), temp.size() + 1);
    address.sun_len = (unsigned char)(offsetof(sockaddr_un, sun_path) + temp.size() + 1);
    pid_t child = fork();
    if (child == 0) {
      int result = fchdir(p.fd) == 0 ? bind(socket_fd, (sockaddr*)&address, address.sun_len) : -1;
      int error = result == 0 ? 0 : errno;
      _exit(error < 256 ? error : EIO);
    }
    int error = errno;
    close(socket_fd);
    if (child < 0) { errno = error; return -1; }
    int status;
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    if (waited < 0 || !WIFEXITED(status) || WEXITSTATUS(status)) {
      error = waited < 0 ? errno : WIFEXITED(status) ? WEXITSTATUS(status) : EIO;
      if (error != EADDRINUSE) unlinkat(p.fd, temp.c_str(), 0);
      errno = error;
      return -1;
    }
    struct stat created;
    if (fstatat(p.fd, temp.c_str(), &created, AT_SYMLINK_NOFOLLOW) != 0 || !S_ISSOCK(created.st_mode)) {
      error = errno ? errno : ESTALE;
      unlinkat(p.fd, temp.c_str(), 0);
      errno = error;
      return -1;
    }
    if (fchmodat(p.fd, temp.c_str(), mode & 07777, AT_SYMLINK_NOFOLLOW) != 0) {
      error = errno;
      unlinkat(p.fd, temp.c_str(), 0);
      errno = error;
      return -1;
    }
    if (renameat(p.fd, temp.c_str(), p.fd, p.name.c_str()) != 0) {
      error = errno;
      unlinkat(p.fd, temp.c_str(), 0);
      errno = error;
      return -1;
    }
    return 0;
  }
#endif
  return mknodat(p.fd, p.name.c_str(), mode, dev);
}
int destination_mkfifo(const char* path, mode_t mode) {
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : mkfifoat(p.fd, p.name.c_str(), mode);
}
int destination_clone(const char* source, const char* path, unsigned flags) {
#ifdef __APPLE__
  auto p = destination_path_impl(path, false);
  return p.fd < 0 ? -1 : clonefileat(AT_FDCWD, source, p.fd, p.name.c_str(), flags);
#else
  errno = ENOTSUP;
  return -1;
#endif
}

bool unsafe_link(std::string_view target, std::string_view parent) {
  if (target.empty() || target.front() == '/') return true;
  int depth = parent.empty() ? 0 : 1 + std::count(parent.begin(), parent.end(), '/');
  size_t start = 0;
  while (start <= target.size()) {
    size_t end = target.find('/', start);
    if (end == std::string_view::npos) end = target.size();
    auto component = target.substr(start, end - start);
    if (component == "..") { if (!depth) return true; depth--; }
    else if (!component.empty() && component != ".") depth++;
    start = end + 1;
  }
  return false;
}
