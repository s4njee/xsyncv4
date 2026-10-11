#pragma once
#include "common.h"
#include <sys/stat.h>

// A native observation, not a cryptographic/content hash. Access time is
// excluded so reads do not invalidate a replacement decision.
struct DestinationRevision {
  bool known = false, exists = false;
  u64 device = 0, inode = 0, links = 0;
  u32 mode = 0, uid = 0, gid = 0, flags = 0;
  i64 size = 0, mtime = 0, ctime = 0;
  u32 mtime_ns = 0, ctime_ns = 0;
  bool operator==(const DestinationRevision&) const = default;
  bool same_object(const DestinationRevision& other) const {
    return known && other.known && exists == other.exists &&
      (!exists || (device == other.device && inode == other.inode && (mode & S_IFMT) == (other.mode & S_IFMT)));
  }
  static DestinationRevision absent() { DestinationRevision r; r.known = true; return r; }
  static DestinationRevision from(const Entry& e) {
    const u32 types[] = {0, S_IFREG, S_IFDIR, S_IFLNK, S_IFIFO, S_IFSOCK, S_IFCHR, S_IFBLK};
    return {true, true, e.hdev, e.ino, e.nlink, e.mode | types[e.type <= T_BLK ? e.type : 0],
            e.uid, e.gid, e.fileflags, e.size, e.mtime, e.ctime, e.mtime_ns, e.ctime_ns};
  }
  static DestinationRevision from(const struct stat& st) {
    DestinationRevision r;
    r.known = r.exists = true; r.device = st.st_dev; r.inode = st.st_ino; r.links = st.st_nlink;
    r.mode = st.st_mode; r.uid = st.st_uid; r.gid = st.st_gid; r.size = st.st_size;
#ifdef __APPLE__
    r.flags = st.st_flags;
    r.mtime = st.st_mtimespec.tv_sec; r.mtime_ns = st.st_mtimespec.tv_nsec;
    r.ctime = st.st_ctimespec.tv_sec; r.ctime_ns = st.st_ctimespec.tv_nsec;
#else
    r.mtime = st.st_mtim.tv_sec; r.mtime_ns = st.st_mtim.tv_nsec;
    r.ctime = st.st_ctim.tv_sec; r.ctime_ns = st.st_ctim.tv_nsec;
#endif
    return r;
  }
};
