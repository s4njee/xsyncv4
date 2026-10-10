// Test-only libc interposition. It never ships in the xsync binary.
#include <atomic>
#include <cstdarg>
#include <sys/stat.h>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <dlfcn.h>
#include <fcntl.h>
#include <limits.h>
#include <unistd.h>

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
static int fault_unlinkat(int fd, const char* name, int flags) {
#ifdef __APPLE__
  auto original = unlinkat;
#else
  static auto original = (int (*)(int, const char*, int))dlsym(RTLD_NEXT, "unlinkat");
#endif
  at_pause("unlink", fd, name);
  return original(fd, name, flags);
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

static ssize_t fault_pread(int fd, void* bytes, size_t len, off_t offset) {
#ifdef __APPLE__
  auto original = pread;
#else
  static auto original = (ssize_t (*)(int, void*, size_t, off_t))dlsym(RTLD_NEXT, "pread");
#endif
  const char* marker = getenv("XSYNC_FAULT_PREAD_NOTIFY");
  const char* minimum = getenv("XSYNC_FAULT_PREAD_MIN_SIZE");
  if (marker && selected(fd) && (!minimum || len >= strtoull(minimum, nullptr, 10))) {
    static std::atomic<bool> notified{false};
    if (!notified.exchange(true)) {
      int file = open(marker, O_WRONLY | O_CREAT | O_EXCL, 0600);
      if (file >= 0) close(file);
      if (const char* delay = getenv("XSYNC_FAULT_PREAD_DELAY_US")) usleep((useconds_t)strtoul(delay, nullptr, 10));
    }
  }
  return original(fd, bytes, len, offset);
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
  }
  return original(fd, bytes, len, offset);
}

static ssize_t fault_write(int fd, const void* bytes, size_t len) {
#ifdef __APPLE__
  auto original = write;
#else
  static auto original = (ssize_t (*)(int, const void*, size_t))dlsym(RTLD_NEXT, "write");
#endif
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
interpose_read __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_read, (const void*)read};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_pread __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_pread, (const void*)pread};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_pwrite __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_pwrite, (const void*)pwrite};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_write __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_write, (const void*)write};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_openat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_openat, (const void*)openat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_unlinkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_unlinkat, (const void*)unlinkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_linkat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_linkat, (const void*)linkat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_fchmodat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_fchmodat, (const void*)fchmodat};
__attribute__((used)) static struct { const void* replacement; const void* original; }
interpose_utimensat __attribute__((section("__DATA,__interpose"))) = {(const void*)fault_utimensat, (const void*)utimensat};
#else
extern "C" ssize_t read(int fd, void* bytes, size_t len) { return fault_read(fd, bytes, len); }
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
extern "C" int unlinkat(int fd, const char* name, int flags) { return fault_unlinkat(fd, name, flags); }
extern "C" int linkat(int from_fd, const char* from, int to_fd, const char* to, int flags) { return fault_linkat(from_fd, from, to_fd, to, flags); }
extern "C" int fchmodat(int fd, const char* name, mode_t mode, int flags) { return fault_fchmodat(fd, name, mode, flags); }
extern "C" int utimensat(int fd, const char* name, const timespec times[2], int flags) { return fault_utimensat(fd, name, times, flags); }
#endif
