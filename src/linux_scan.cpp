#include "linux_scan.h"
#ifdef __linux__
#include <array>
#include <atomic>
#include <cerrno>
#include <cstddef>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/sysmacros.h>
#include <unistd.h>

void entry_from_stat(const struct stat& st, Entry& entry);

namespace {
struct LinuxDirent {
  uint64_t ino;
  int64_t offset;
  uint16_t length;
  uint8_t type;
  char name[1];
};
static_assert(offsetof(LinuxDirent, name) == 19);
std::atomic<bool> statx_available{true};

bool entry_at(int fd, const char* name, Entry& entry) {
  struct stat st{};
  if (statx_available.load(std::memory_order_relaxed)) {
    struct statx sx{};
    // Match fstatat semantics: do not follow links or trigger a terminal
    // automount, and retain the filesystem's normal synchronization policy.
    int rc;
    do {
      rc = syscall(SYS_statx, fd, name,
                   AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT | AT_STATX_SYNC_AS_STAT,
                   STATX_BASIC_STATS, &sx);
    } while (rc < 0 && errno == EINTR);
    constexpr unsigned required = STATX_TYPE | STATX_MODE | STATX_NLINK |
      STATX_UID | STATX_GID | STATX_ATIME | STATX_MTIME | STATX_CTIME | STATX_INO | STATX_SIZE;
    if (rc == 0 && (sx.stx_mask & required) == required) {
      st.st_mode = sx.stx_mode;
      st.st_uid = sx.stx_uid, st.st_gid = sx.stx_gid;
      st.st_nlink = sx.stx_nlink, st.st_ino = sx.stx_ino;
      st.st_size = sx.stx_size;
      st.st_dev = makedev(sx.stx_dev_major, sx.stx_dev_minor);
      st.st_rdev = makedev(sx.stx_rdev_major, sx.stx_rdev_minor);
      st.st_mtim = {sx.stx_mtime.tv_sec, sx.stx_mtime.tv_nsec};
      st.st_atim = {sx.stx_atime.tv_sec, sx.stx_atime.tv_nsec};
      st.st_ctim = {sx.stx_ctime.tv_sec, sx.stx_ctime.tv_nsec};
    } else {
      if (rc != 0 && errno != ENOSYS && errno != EINVAL && errno != EOPNOTSUPP && errno != EPERM)
        return false;
      // ENOSYS also covers a seccomp policy hiding the syscall. Missing
      // filesystem fields fall back per entry, without disabling other mounts.
      if (rc != 0 && (errno == ENOSYS || errno == EPERM))
        statx_available.store(false, std::memory_order_relaxed);
      if (fstatat(fd, name, &st, AT_SYMLINK_NOFOLLOW) != 0) return false;
    }
  } else if (fstatat(fd, name, &st, AT_SYMLINK_NOFOLLOW) != 0) return false;
  entry_from_stat(st, entry);
  return true;
}
}

int list_dir_linux(int fd, DirList& out) {
  // A bounded buffer amortizes directory-entry reads without holding whole
  // subtrees. Never use d_type as a substitute for authoritative attributes.
  static thread_local std::array<char, 64 * 1024> bytes;
  for (;;) {
    ssize_t count = syscall(SYS_getdents64, fd, bytes.data(), bytes.size());
    if (count < 0) {
      if (errno == EINTR) continue;
      out.incomplete = true;
      return errno;
    }
    if (count == 0) return 0;
    if ((size_t)count > bytes.size()) { out.incomplete = true; return EIO; }
    size_t offset = 0;
    while (offset < (size_t)count) {
      constexpr size_t header = offsetof(LinuxDirent, name);
      if ((size_t)count - offset <= header) { out.incomplete = true; return EIO; }
      uint16_t length;
      memcpy(&length, bytes.data() + offset + offsetof(LinuxDirent, length), sizeof length);
      if (length <= header || length > (size_t)count - offset) { out.incomplete = true; return EIO; }
      const char* name = bytes.data() + offset + header;
      const char* end = (const char*)memchr(name, 0, length - header);
      if (!end || end == name) { out.incomplete = true; return EIO; }
      offset += length;
      if (name[0] == '.' && (!name[1] || (name[1] == '.' && !name[2]))) continue;
      Entry entry;
      if (!entry_at(fd, name, entry)) { out.incomplete = true; continue; }
      entry.name_len = end - name;
      entry.name_off = out.add_str({name, entry.name_len});
      out.e.push_back(entry);
    }
  }
}
#endif
