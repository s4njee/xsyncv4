#define _GNU_SOURCE 1
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <linux/magic.h>
#include <sys/vfs.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

extern "C" int ioctl(int fd, unsigned long request, ...) {
  if (request == FICLONE) { errno = EOPNOTSUPP; return -1; }
  va_list arguments;
  va_start(arguments, request);
  unsigned long argument = va_arg(arguments, unsigned long);
  va_end(arguments);
  using Function = int (*)(int, unsigned long, ...);
  static auto real = (Function)dlsym(RTLD_NEXT, "ioctl");
  return real(fd, request, argument);
}

extern "C" int fstatfs(int fd, struct statfs* result) {
  using Function = int (*)(int, struct statfs*);
  static auto real = (Function)dlsym(RTLD_NEXT, "fstatfs");
  int status = real(fd, result);
  const char* mode = getenv("XS_LARGE_COPY_FAULT");
  // Unit fault cases simulate a native range-copy filesystem to reach the
  // syscall error paths. Positive reflinks are tested on real btrfs/XFS.
  if (!status && mode) result->f_type = !strcmp(mode, "ext4") ? EXT4_SUPER_MAGIC : BTRFS_SUPER_MAGIC;
  return status;
}

extern "C" ssize_t copy_file_range(int in, off_t* input_offset, int out, off_t* output_offset, size_t length, unsigned flags) {
  using Function = ssize_t (*)(int, off_t*, int, off_t*, size_t, unsigned);
  static auto real = (Function)dlsym(RTLD_NEXT, "copy_file_range");
  static std::atomic<int> calls{0};
  int call = calls.fetch_add(1);
  const char* mode = getenv("XS_LARGE_COPY_FAULT");
  if (!mode) return real(in, input_offset, out, output_offset, length, flags);
  if (!strcmp(mode, "zero")) return 0;
  if (!strcmp(mode, "enosys")) { errno = ENOSYS; return -1; }
  if (!strcmp(mode, "eio") || !strcmp(mode, "ext4")) { errno = EIO; return -1; }
  if (!strcmp(mode, "partial-fallback") && call >= 3) { errno = EINVAL; return -1; }
  if (!strcmp(mode, "eintr") && call == 0) { errno = EINTR; return -1; }
  ssize_t count = real(in, input_offset, out, output_offset, std::min<size_t>(length, 65537), flags);
  if ((!strcmp(mode, "mutate") || !strcmp(mode, "grow") || !strcmp(mode, "shrink")) && call == 0 && count > 0) {
    const char* path = getenv("XS_LARGE_COPY_SOURCE");
    int changed = open(path, O_RDWR);
    char byte = 'X';
    if (changed >= 0) {
      if (!strcmp(mode, "shrink")) (void)ftruncate(changed, 32 * 1024 * 1024 + 313);
      else if (!strcmp(mode, "grow")) {
        struct stat st;
        char tail[128]{};
        if (fstat(changed, &st) == 0) (void)pwrite(changed, tail, sizeof tail, st.st_size);
      } else (void)pwrite(changed, &byte, 1, 0);
      close(changed);
    }
  }
  return count;
}
