// Test-only libc interposition. It never ships in the xsync binary.
#include <atomic>
#include <cstdarg>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <string_view>
#include <string>
#include <cstdio>
#include <dlfcn.h>
#include <fcntl.h>
#include <limits.h>
#include <unistd.h>
#include <pthread.h>
#include <cstdint>
#include <time.h>
#include <dirent.h>
#ifdef __APPLE__
#include <sys/attr.h>
#include <sys/clonefile.h>
#include <sys/socket.h>
#include <sys/un.h>
static int fault_bind(int fd, const sockaddr* address, socklen_t length) {
  const char* error = getenv("XSYNC_FAULT_BIND_ERROR");
  if (error && address->sa_family == AF_UNIX &&
      strncmp(((const sockaddr_un*)address)->sun_path, ".xsync-socket-", 14) == 0) {
    errno = atoi(error); return -1;
  }
  return bind(fd, address, length);
}
static int fault_lstat(const char* path, struct stat* st) {
  int result = lstat(path, st);
  const char* prefix = getenv("XSYNC_FAULT_PATH");
  if (!result && prefix && strncmp(path, prefix, strlen(prefix)) == 0 &&
      ((getenv("XSYNC_FAULT_DATALESS") && S_ISREG(st->st_mode)) ||
       (getenv("XSYNC_FAULT_DATALESS_DIRECTORY") && S_ISDIR(st->st_mode)))) st->st_flags |= SF_DATALESS;
  return result;
}
#endif

static bool selected(int fd) {
  const char* prefix = getenv("XSYNC_FAULT_PATH");
  if (!prefix) return false;
  char path[PATH_MAX]{};
#ifdef __APPLE__
  if (fcntl(fd, F_GETPATH, path) < 0) return false;
#else
  char link[64];
  snprintf(link, sizeof link, "/proc/self/fd/%d", fd);
  ssize_t n = readlink(link, path, sizeof path - 1);
  if (n < 0) return false;
  path[n] = 0;
#endif
  return strncmp(path, prefix, strlen(prefix)) == 0;
}
static bool selected_suffix(int fd,const char* suffix) {
  if (!suffix) return true;
  char path[PATH_MAX]{};
#ifdef __APPLE__
  if (fcntl(fd,F_GETPATH,path) < 0) return false;
#else
  char link[64]; snprintf(link,sizeof link,"/proc/self/fd/%d",fd);
  ssize_t n = readlink(link,path,sizeof path-1); if (n < 0) return false; path[n] = 0;
#endif
  return std::string_view(path).ends_with(suffix);
}
static int fault_fstatvfs(int fd,struct statvfs* state) {
#ifdef __APPLE__
  auto original = fstatvfs;
#else
  static auto original = (int (*)(int,struct statvfs*))dlsym(RTLD_NEXT,"fstatvfs");
#endif
  if (selected(fd)) {
    if (const char* error = getenv("XSYNC_FAULT_STATVFS_ERROR")) { errno = atoi(error); return -1; }
  }
  int result = original(fd,state);
  if (!result && selected(fd)) {
    if (getenv("XSYNC_FAULT_STATVFS_OVERFLOW")) {
      // macOS block counters are narrower than uint64_t; overflow the byte
      // product using a representable count on both supported 64-bit hosts.
      state->f_frsize = UINT64_C(1) << 63; state->f_blocks = state->f_bfree = state->f_bavail = 2;
    }
    if (getenv("XSYNC_FAULT_STATVFS_READ_ONLY")) state->f_flag |= ST_RDONLY;
    if (const char* notify = getenv("XSYNC_FAULT_STATVFS_NOTIFY")) {
      int marker = open(notify,O_WRONLY|O_CREAT|O_TRUNC,0600); if (marker >= 0) close(marker);
      std::string release = std::string(notify)+".release";
      while (access(release.c_str(),F_OK)) usleep(1000);
    }
  }
  return result;
}
static long fault_fpathconf(int fd,int name) {
#ifdef __APPLE__
  auto original = fpathconf;
#else
  static auto original = (long (*)(int,int))dlsym(RTLD_NEXT,"fpathconf");
#endif
  if (name == _PC_NAME_MAX && selected(fd)) {
    if (const char* error = getenv("XSYNC_FAULT_NAME_MAX_ERROR")) { errno = atoi(error); return -1; }
    if (getenv("XSYNC_FAULT_NAME_MAX_UNBOUNDED")) { errno = 0; return -1; }
  }
  return original(fd,name);
}

static void publication_pause() {
  const char* notify = getenv("XSYNC_FAULT_PUBLICATION_NOTIFY");
  if (notify) {
    int marker = open(notify,O_WRONLY|O_CREAT|O_TRUNC,0600);
    if (marker >= 0) {
      char pid[32]; int size = snprintf(pid,sizeof pid,"%d",getpid());
      write(marker,pid,size); close(marker);
    }
    if (getenv("XSYNC_FAULT_PUBLICATION_HOLD")) {
      std::string release = std::string(notify)+".release";
      while (access(release.c_str(),F_OK)) usleep(1000);
    }
  }
}
static int fault_renameat(int from_fd,const char* from,int to_fd,const char* to) {
#ifdef __APPLE__
  auto original = renameat;
#else
  static auto original = (int (*)(int,const char*,int,const char*))dlsym(RTLD_NEXT,"renameat");
#endif
  bool selected_publication = getenv("XSYNC_FAULT_PUBLICATION_NOTIFY") && !getenv("XSYNC_FAULT_PUBLICATION_STAT") &&
    selected(from_fd) && std::string_view(from).ends_with(".part");
  bool before = getenv("XSYNC_FAULT_PUBLICATION_BEFORE");
  if (selected_publication && before) publication_pause();
  int result = original(from_fd,from,to_fd,to);
  if (!result && selected_publication && !before) publication_pause();
  return result;
}

static int fault_fstatat(int fd, const char* path, struct stat* st, int flags) {
#ifdef __APPLE__
  auto original = fstatat;
#else
  static auto original = (int (*)(int, const char*, struct stat*, int))dlsym(RTLD_NEXT, "fstatat");
#endif
  const char* missing = getenv("XSYNC_FAULT_STAT_NAME");
  if (missing && selected(fd) && strcmp(path, missing) == 0) { errno = ENOENT; return -1; }
  int result = original(fd, path, st, flags);
  const char* publication = getenv("XSYNC_FAULT_PUBLICATION_STAT");
  const char* size = getenv("XSYNC_FAULT_PUBLICATION_SIZE");
  if (!result && publication && size && selected(fd) && strcmp(path,publication) == 0 &&
      S_ISREG(st->st_mode) && st->st_size == atoll(size)) publication_pause();
#ifdef __APPLE__
  if (!result && selected(fd) && ((getenv("XSYNC_FAULT_DATALESS") && S_ISREG(st->st_mode)) ||
      (getenv("XSYNC_FAULT_DATALESS_DIRECTORY") && S_ISDIR(st->st_mode)))) st->st_flags |= SF_DATALESS;
#endif
  return result;
}

static dirent* fault_readdir(DIR* dir) {
#ifdef __APPLE__
  auto original = readdir;
#else
  static auto original = (dirent* (*)(DIR*))dlsym(RTLD_NEXT, "readdir");
#endif
  bool match = selected(dirfd(dir));
  static unsigned delivered = 0;
  const char* after = getenv("XSYNC_FAULT_LIST_AFTER");
  if (match && after && delivered >= strtoul(after, nullptr, 10)) { errno = EIO; return nullptr; }
  dirent* entry = original(dir);
  if (entry && match && strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..")) {
    ++delivered;
    if (const char* delay = getenv("XSYNC_FAULT_LIST_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
  }
  return entry;
}

static DIR* fault_opendir(const char* path) {
#ifdef __APPLE__
  auto original = opendir;
#else
  static auto original = (DIR* (*)(const char*))dlsym(RTLD_NEXT, "opendir");
#endif
  const char* prefix = getenv("XSYNC_FAULT_PATH");
  const char* code = getenv("XSYNC_FAULT_OPENDIR_ERROR");
  if (prefix && code && strncmp(path, prefix, strlen(prefix)) == 0) { errno = atoi(code); return nullptr; }
  return original(path);
}

// Native scans open a directory descriptor (including bulk scans), while app
// browsing uses opendir. Inject the same failure at both entry points.
static int fault_open(const char* path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args); }
#ifdef __APPLE__
  auto original = open;
#else
  static auto original = (int (*)(const char*, int, ...))dlsym(RTLD_NEXT, "open");
#endif
  const char* prefix = getenv("XSYNC_FAULT_PATH");
  const char* code = getenv("XSYNC_FAULT_OPENDIR_ERROR");
  if (prefix && code && (flags & O_DIRECTORY)) {
    char resolved[PATH_MAX];
    const char* actual = realpath(path, resolved) ? resolved : path;
    if (strncmp(actual, prefix, strlen(prefix)) == 0) { errno = atoi(code); return -1; }
  }
  int result = original(path, flags, mode);
  const char* scan_marker = getenv("XSYNC_FAULT_SCAN_NOTIFY");
  static std::atomic<bool> scan_paused{false};
  if (scan_marker && result >= 0 && (flags & O_DIRECTORY) && selected(result) && !scan_paused.exchange(true)) {
    int notify = original(scan_marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (notify >= 0) close(notify);
    if (const char* release = getenv("XSYNC_FAULT_SCAN_RELEASE")) {
      for (unsigned wait = 0; wait < 1000 && access(release, F_OK); ++wait) usleep(5000);
    }
  }
  return result;
}

static int fault_futimens(int fd, const timespec times[2]) {
#ifdef __APPLE__
  auto original = futimens;
#else
  static auto original = (int (*)(int, const timespec*))dlsym(RTLD_NEXT, "futimens");
#endif
  if (selected(fd)) {
    if (const char* marker = getenv("XSYNC_FAULT_FUTIMENS_NOTIFY")) {
      int notify = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
      if (notify >= 0) close(notify);
    }
    if (const char* delay = getenv("XSYNC_FAULT_FUTIMENS_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
    if (const char* release = getenv("XSYNC_FAULT_FUTIMENS_RELEASE")) {
      for (int i = 0; i < 1000 && access(release, F_OK) != 0; ++i) usleep(5000);
    }
    if (const char* code = getenv("XSYNC_FAULT_FUTIMENS_ERROR")) { errno = atoi(code); return -1; }
  }
  return original(fd, times);
}

#ifdef __APPLE__
static int fault_getattrlistbulk(int fd, struct attrlist* attrs, void* bytes, size_t size, uint64_t flags) {
  // Exercise the production fallback scanner with a synthetic dataless flag.
  if ((getenv("XSYNC_FAULT_DATALESS") || getenv("XSYNC_FAULT_DATALESS_DIRECTORY")) && selected(fd)) { errno = ENOTSUP; return -1; }
  return getattrlistbulk(fd, attrs, bytes, size, flags);
}
static int fault_clonefileat(int from_fd, const char* from, int to_fd, const char* to, int flags) {
  const char* prefix = getenv("XSYNC_FAULT_PATH");
  const char* marker = getenv("XSYNC_FAULT_CLONE_NOTIFY");
  if (prefix && marker && strncmp(from, prefix, strlen(prefix)) == 0) {
    int fd = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd >= 0) { write(fd, from, strlen(from)); close(fd); }
  }
  if (prefix && strncmp(from, prefix, strlen(prefix)) == 0) {
    if (const char* delay = getenv("XSYNC_FAULT_CLONE_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
    if (getenv("XSYNC_FAULT_CLONE_EXDEV")) { errno = EXDEV; return -1; }
  }
  return clonefileat(from_fd, from, to_fd, to, flags);
}
#endif

// Pause after the receiver has selected a directory descriptor, immediately
// before the requested syscall. Tests can replace that directory or final name.
static void at_pause(const char* operation, int fd, const char* name) {
  const char* op = getenv("XSYNC_FAULT_AT_OP");
  const char* match = getenv("XSYNC_FAULT_AT_NAME");
  const char* marker = getenv("XSYNC_FAULT_AT_NOTIFY");
  if (!op || !match || !marker || strcmp(op, operation) || !selected(fd)) return;
  bool prefix = getenv("XSYNC_FAULT_AT_PREFIX");
  if (prefix ? strncmp(name, match, strlen(match)) != 0 : strcmp(name, match) != 0) return;
  static std::atomic<bool> paused{false};
  if (paused.exchange(true)) return;
  int notify = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
  if (notify >= 0) close(notify);
  usleep(300000);
}

static int fault_openat(int fd, const char* name, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args); }
#ifdef __APPLE__
  auto original = openat;
#else
  static auto original = (int (*)(int, const char*, int, ...))dlsym(RTLD_NEXT, "openat");
#endif
  at_pause("open", fd, name);
  return original(fd, name, flags, mode);
}
static int fault_mkdirat(int fd, const char* name, mode_t mode) {
#ifdef __APPLE__
  auto original = mkdirat;
#else
  static auto original = (int (*)(int, const char*, mode_t))dlsym(RTLD_NEXT, "mkdirat");
#endif
  at_pause("mkdir", fd, name);
  return original(fd, name, mode);
}
static int fault_symlinkat(const char* target, int fd, const char* name) {
#ifdef __APPLE__
  auto original = symlinkat;
#else
  static auto original = (int (*)(const char*, int, const char*))dlsym(RTLD_NEXT, "symlinkat");
#endif
  at_pause("symlink", fd, name);
  return original(target, fd, name);
}
static int fault_unlinkat(int fd, const char* name, int flags) {
#ifdef __APPLE__
  auto original = unlinkat;
#else
  static auto original = (int (*)(int, const char*, int))dlsym(RTLD_NEXT, "unlinkat");
#endif
  if (const char* denied = getenv("XSYNC_FAULT_UNLINK_NAME")) {
    if (selected(fd) && !strcmp(name, denied)) { errno = EPERM; return -1; }
  }
  at_pause("unlink", fd, name);
  if (selected(fd)) {
    if (const char* delay = getenv("XSYNC_FAULT_UNLINK_DELAY_US")) {
      if (const char* marker = getenv("XSYNC_FAULT_UNLINK_NOTIFY")) {
        int notify = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (notify >= 0) close(notify);
      }
      usleep((useconds_t)strtoul(delay, nullptr, 10));
    }
  }
  return original(fd, name, flags);
}
static ssize_t fault_readlinkat(int fd, const char* name, char* bytes, size_t size) {
#ifdef __APPLE__
  auto original = readlinkat;
#else
  static auto original = (ssize_t (*)(int, const char*, char*, size_t))dlsym(RTLD_NEXT, "readlinkat");
#endif
  if (const char* denied = getenv("XSYNC_FAULT_READLINK_NAME")) {
    if (selected(fd) && !strcmp(name, denied)) { errno = EIO; return -1; }
  }
  return original(fd, name, bytes, size);
}
static int fault_linkat(int from_fd, const char* from, int to_fd, const char* to, int flags) {
#ifdef __APPLE__
  auto original = linkat;
#else
  static auto original = (int (*)(int, const char*, int, const char*, int))dlsym(RTLD_NEXT, "linkat");
#endif
  at_pause("link", from_fd, from);
  if (selected(from_fd) && getenv("XSYNC_FAULT_LINK_EXDEV")) { errno = EXDEV; return -1; }
  return original(from_fd, from, to_fd, to, flags);
}
static int fault_fchmodat(int fd, const char* name, mode_t mode, int flags) {
#ifdef __APPLE__
  auto original = fchmodat;
#else
  static auto original = (int (*)(int, const char*, mode_t, int))dlsym(RTLD_NEXT, "fchmodat");
#endif
  at_pause("chmod", fd, name);
  return original(fd, name, mode, flags);
}
static int fault_utimensat(int fd, const char* name, const timespec times[2], int flags) {
#ifdef __APPLE__
  auto original = utimensat;
#else
  static auto original = (int (*)(int, const char*, const timespec*, int))dlsym(RTLD_NEXT, "utimensat");
#endif
  at_pause("times", fd, name);
  return original(fd, name, times, flags);
}

static bool name_probe(int fd) {
  char path[PATH_MAX]{};
#ifdef __APPLE__
  if (fcntl(fd, F_GETPATH, path) < 0) return false;
#else
  char link[64]; snprintf(link, sizeof link, "/proc/self/fd/%d", fd);
  ssize_t n = readlink(link, path, sizeof path - 1);
  if (n < 0) return false;
  path[n] = 0;
#endif
  return strstr(path, "/.xsync-nameprobe-") != nullptr;
}
static int fault_ftruncate(int fd, off_t size) {
#ifdef __APPLE__
  auto original = ftruncate;
#else
  static auto original = (int (*)(int, off_t))dlsym(RTLD_NEXT, "ftruncate");
#endif
  if (selected(fd)) {
    if (const char* code = getenv("XSYNC_FAULT_TRUNCATE_ERROR")) { errno = atoi(code); return -1; }
  }
  return original(fd,size);
}
static int fault_close(int fd) {
#ifdef __APPLE__
  auto original = close;
#else
  static auto original = (int (*)(int))dlsym(RTLD_NEXT, "close");
#endif
  const char* marker = getenv("XSYNC_FAULT_CLOSE_NOTIFY");
  struct stat st;
  static std::atomic<bool> paused{false};
  if (marker && selected(fd) && selected_suffix(fd,getenv("XSYNC_FAULT_CLOSE_SUFFIX")) && !name_probe(fd) && fstat(fd, &st) == 0 && S_ISREG(st.st_mode) && !paused.exchange(true)) {
    int notify = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (notify >= 0) original(notify);
    if (const char* release = getenv("XSYNC_FAULT_CLOSE_RELEASE")) {
      for (unsigned wait = 0; wait < 1000 && access(release, F_OK); ++wait) usleep(5000);
    }
  }
  return original(fd);
}

static ssize_t fault_read(int fd, void* bytes, size_t len) {
#ifdef __APPLE__
  auto original = read;
#else
  static auto original = (ssize_t (*)(int, void*, size_t))dlsym(RTLD_NEXT, "read");
#endif
  if (selected(fd) && getenv("XSYNC_FAULT_READ_ERROR")) { errno = EIO; return -1; }
  if (selected(fd)) {
    if (const char* delay = getenv("XSYNC_FAULT_EACH_READ_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
  }
  if (selected(fd) && len && lseek(fd, 0, SEEK_CUR) == 0) {
    static std::atomic<unsigned> reads{0};
    unsigned attempt = ++reads;
    if (const char* notify = getenv("XSYNC_FAULT_READ_NOTIFY")) {
      char path[PATH_MAX];
      snprintf(path, sizeof path, "%s.%u", notify, attempt);
      int marker = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
      if (marker >= 0) close(marker);
    }
    if (const char* delay = getenv("XSYNC_FAULT_READ_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
  }
  return original(fd, bytes, len);
}

static void range_trace(int fd, const char* operation, bool start) {
  const char* path = getenv("XSYNC_FAULT_RANGE_TRACE");
  if (!path || !selected(fd)) return;
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  char line[192];
  int length = snprintf(line, sizeof line, "%llu %ld %llu %s %s\n",
    (unsigned long long)now.tv_sec * 1000000000 + now.tv_nsec, (long)getpid(),
    (unsigned long long)(uintptr_t)pthread_self(), operation, start ? "start" : "end");
  int log = open(path, O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0600);
  if (log >= 0) { (void)write(log, line, (size_t)length); close(log); }
  if (start) usleep(20000); // Make overlap observable without timing assertions.
}

static ssize_t fault_pread(int fd, void* bytes, size_t len, off_t offset) {
#ifdef __APPLE__
  auto original = pread;
#else
  static auto original = (ssize_t (*)(int, void*, size_t, off_t))dlsym(RTLD_NEXT, "pread");
#endif
  if (const char* error = getenv("XSYNC_FAULT_PREAD_WRITABLE_ERROR")) {
    if (selected(fd) && (fcntl(fd, F_GETFL) & O_ACCMODE) == O_RDWR) { errno = atoi(error); return -1; }
  }
  const char* marker = getenv("XSYNC_FAULT_PREAD_NOTIFY");
  const char* minimum = getenv("XSYNC_FAULT_PREAD_MIN_SIZE");
  const char* before = getenv("XSYNC_FAULT_PREAD_BEFORE_OFFSET");
  if (marker && selected(fd) && (!minimum || len >= strtoull(minimum, nullptr, 10)) &&
      (!before || offset < (off_t)strtoll(before, nullptr, 10))) {
    static std::atomic<bool> notified{false};
    if (!notified.exchange(true)) {
      int file = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
      if (file >= 0) close(file);
      if (const char* delay = getenv("XSYNC_FAULT_PREAD_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
    }
  }
  range_trace(fd, "read", true);
  ssize_t result = original(fd, bytes, len, offset);
  int error = errno;
  range_trace(fd, "read", false);
  errno = error;
  return result;
}

static ssize_t fault_pwrite(int fd, const void* bytes, size_t len, off_t offset) {
#ifdef __APPLE__
  auto original = pwrite;
#else
  static auto original = (ssize_t (*)(int, const void*, size_t, off_t))dlsym(RTLD_NEXT, "pwrite");
#endif
  const char* from = getenv("XSYNC_FAULT_WRITE_FROM_OFFSET");
  if (selected(fd) && (!from || offset >= (off_t)strtoll(from, nullptr, 10))) {
    if (const char* notify = getenv("XSYNC_FAULT_WRITE_NOTIFY")) {
      int marker = open(notify, O_WRONLY | O_CREAT | O_EXCL, 0600);
      if (marker >= 0) close(marker);
    }
    if (const char* delay = getenv("XSYNC_FAULT_WRITE_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
    if (const char* code = getenv("XSYNC_FAULT_WRITE_ERROR")) { errno = atoi(code); return -1; }
  }
  range_trace(fd, "write", true);
  ssize_t result = original(fd, bytes, len, offset);
  int error = errno;
  range_trace(fd, "write", false);
  errno = error;
  return result;
}

static ssize_t fault_write(int fd, const void* bytes, size_t len) {
#ifdef __APPLE__
  auto original = write;
#else
  static auto original = (ssize_t (*)(int, const void*, size_t))dlsym(RTLD_NEXT, "write");
#endif
  if (const char* code = getenv("XSYNC_FAULT_RECOVERY_PUBLICATION_ERROR")) {
    if (selected(fd) && std::string_view(static_cast<const char*>(bytes),len).find("\"state\":\"publishing\"") != std::string_view::npos) {
      errno = atoi(code); return -1;
    }
  }
  if (const char* code = getenv("XSYNC_FAULT_RECOVERY_FINALIZE_ERROR")) {
    if (selected(fd) && std::string_view(static_cast<const char*>(bytes),len).find("\"state\":\"completed\"") != std::string_view::npos) {
      errno = atoi(code); return -1;
    }
  }
  if (const char* code = getenv("XSYNC_FAULT_RECOVERY_PAUSE_ERROR")) {
    if (selected(fd) && std::string_view(static_cast<const char*>(bytes),len).find("\"state\":\"paused\"") != std::string_view::npos) {
      errno = atoi(code); return -1;
    }
  }
  if (const char* code = getenv("XSYNC_FAULT_RECOVERY_CHOICE_ERROR")) {
    if (selected(fd) && std::string_view(static_cast<const char*>(bytes),len).find("\"record_kind\":\"conflict_choice\"") != std::string_view::npos) {
      errno = atoi(code); return -1;
    }
  }
  ssize_t result = original(fd, bytes, len);
  if (result <= 0) return result;
  if (const char* notify = getenv("XSYNC_FAULT_DATA_END_NOTIFY")) {
    const unsigned char* p = (const unsigned char*)bytes;
    size_t left = (size_t)result;
    while (left >= 5) {
      unsigned size;
      memcpy(&size, p, 4);
      if (size > left - 5) break;
      if (p[4] == 6) {
        int marker = open(notify, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (marker >= 0) close(marker);
      }
      left -= size + 5;
      p += size + 5;
    }
  }
  return result;
}

#ifdef __APPLE__
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_bind __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_bind, (const void*)bind};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_lstat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_lstat, (const void*)lstat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_renameat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_renameat, (const void*)renameat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_fstatvfs __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_fstatvfs, (const void*)fstatvfs};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_fpathconf __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_fpathconf, (const void*)fpathconf};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_fstatat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_fstatat, (const void*)fstatat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_readdir __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_readdir, (const void*)readdir};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_opendir __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_opendir, (const void*)opendir};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_open __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_open, (const void*)open};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_futimens __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_futimens, (const void*)futimens};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_getattrlistbulk __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_getattrlistbulk, (const void*)getattrlistbulk};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_clonefileat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_clonefileat, (const void*)clonefileat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_read __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_read, (const void*)read};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_close __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_close, (const void*)close};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_pread __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_pread, (const void*)pread};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_pwrite __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_pwrite, (const void*)pwrite};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_ftruncate __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_ftruncate, (const void*)ftruncate};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_write __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_write, (const void*)write};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_openat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_openat, (const void*)openat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_mkdirat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_mkdirat, (const void*)mkdirat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_symlinkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_symlinkat, (const void*)symlinkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_unlinkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_unlinkat, (const void*)unlinkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_readlinkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_readlinkat, (const void*)readlinkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_linkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_linkat, (const void*)linkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_fchmodat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_fchmodat, (const void*)fchmodat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_utimensat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_utimensat, (const void*)utimensat};
#else
extern "C" int fstatat(int fd, const char* path, struct stat* st, int flags) { return fault_fstatat(fd, path, st, flags); }
extern "C" int renameat(int from_fd,const char* from,int to_fd,const char* to) { return fault_renameat(from_fd,from,to_fd,to); }
extern "C" int fstatvfs(int fd,struct statvfs* state) { return fault_fstatvfs(fd,state); }
extern "C" long fpathconf(int fd,int name) { return fault_fpathconf(fd,name); }
extern "C" dirent* readdir(DIR* dir) { return fault_readdir(dir); }
extern "C" DIR* opendir(const char* path) { return fault_opendir(path); }
extern "C" int open(const char* path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args); }
  return fault_open(path, flags, mode);
}
extern "C" int futimens(int fd, const timespec times[2]) { return fault_futimens(fd, times); }
extern "C" ssize_t read(int fd, void* bytes, size_t len) { return fault_read(fd, bytes, len); }
extern "C" int close(int fd) { return fault_close(fd); }
extern "C" int ftruncate(int fd, off_t size) { return fault_ftruncate(fd,size); }
extern "C" ssize_t pread(int fd, void* bytes, size_t len, off_t offset) { return fault_pread(fd, bytes, len, offset); }
extern "C" ssize_t pwrite(int fd, const void* bytes, size_t len, off_t offset) { return fault_pwrite(fd, bytes, len, offset); }
extern "C" ssize_t write(int fd, const void* bytes, size_t len) { return fault_write(fd, bytes, len); }
#endif

#ifndef __APPLE__
extern "C" int openat(int fd, const char* name, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) { va_list args; va_start(args, flags); mode = va_arg(args, int); va_end(args); }
  return fault_openat(fd, name, flags, mode);
}
extern "C" int mkdirat(int fd, const char* name, mode_t mode) { return fault_mkdirat(fd, name, mode); }
extern "C" int symlinkat(const char* target, int fd, const char* name) { return fault_symlinkat(target, fd, name); }
extern "C" int unlinkat(int fd, const char* name, int flags) { return fault_unlinkat(fd, name, flags); }
extern "C" ssize_t readlinkat(int fd, const char* name, char* bytes, size_t size) { return fault_readlinkat(fd, name, bytes, size); }
extern "C" int linkat(int from_fd, const char* from, int to_fd, const char* to, int flags) { return fault_linkat(from_fd, from, to_fd, to, flags); }
extern "C" int fchmodat(int fd, const char* name, mode_t mode, int flags) { return fault_fchmodat(fd, name, mode, flags); }
extern "C" int utimensat(int fd, const char* name, const timespec times[2], int flags) { return fault_utimensat(fd, name, times, flags); }
#endif
