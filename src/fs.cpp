#include "fs.h"

#include <dirent.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <climits>
#include <map>
#include <shared_mutex>
#include <unordered_map>

#include "progress.h"
#include "output.h"
#include "hardlink.h"
#include "rate_limit.h"
#include "engine.h"

#ifdef __APPLE__
#include <sys/attr.h>
#include <sys/vnode.h>
#include <sys/clonefile.h>
#endif

#define XXH_INLINE_ALL
#include <xxhash.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

std::string errstr(int e) { return std::string(strerror(e)) + " (" + std::to_string(e) + ")"; }

static std::atomic<bool> disk_full{false};
void file_io_error(int error, const char* path, const char* operation) {
  if (disk_full.load()) return;
  if (error == ENOSPC || error == EDQUOT) {
    if (!disk_full.exchange(true)) die(RERR_FILEIO, "%s failed on \"%s\": %s", operation, path, errstr(error).c_str());
    return;
  }
  err_line(RERR_PARTIAL, "%s failed on \"%s\": %s", operation, path, errstr(error).c_str());
}

bool check_attr(int result, const char* path, const char* attribute) {
  if (result == 0) return true;
  int e = errno;
  if (e == ENOSPC || e == EDQUOT || disk_full.load()) { file_io_error(e, path, attribute); return false; }
  err_line(RERR_PARTIAL, "failed to set %s on \"%s\": %s", attribute, path, errstr(e).c_str());
  return false;
}

void Worker::flush_log() {
  if (log.empty()) return;
  if (g_msg_sink) {
    log.pop_back();
    g_msg_sink(0, 0, log);
  } else {
    output_text(log);
  }
  log.clear();
}

bool write_all(int fd, const char* p, size_t n) {
  while (n) {
    ssize_t k = write(fd, p, n);
    if (k < 0) {
      if (errno == EINTR) continue;
      return false;
    }
    p += k;
    n -= (size_t)k;
  }
  return true;
}

// ---------------------------------------------------------------- ids

static std::vector<gid_t> my_groups;
static uid_t my_uid;

void init_ids() {
  my_uid = geteuid();
  g_opt.am_root = my_uid == 0;
  int n = getgroups(0, nullptr);
  if (n > 0) {
    my_groups.resize((size_t)n);
    n = getgroups(n, my_groups.data());
    my_groups.resize(n > 0 ? (size_t)n : 0);
  }
  my_groups.push_back(getegid());
}

bool can_set_gid(u32 gid) {
  if (g_opt.am_root) return true;
  return std::find(my_groups.begin(), my_groups.end(), (gid_t)gid) != my_groups.end();
}

// ---------------------------------------------------------------- listing

void entry_from_stat(const struct stat& st, Entry& e) {
  switch (st.st_mode & S_IFMT) {
    case S_IFREG: e.type = T_REG; break;
    case S_IFDIR: e.type = T_DIR; break;
    case S_IFLNK: e.type = T_LNK; break;
    case S_IFIFO: e.type = T_FIFO; break;
    case S_IFSOCK: e.type = T_SOCK; break;
    case S_IFCHR: e.type = T_CHR; break;
    case S_IFBLK: e.type = T_BLK; break;
    default: e.type = T_NONE;
  }
  e.mode = st.st_mode & 07777;
  e.uid = st.st_uid;
  e.gid = st.st_gid;
  e.size = (i64)st.st_size;  // Includes directory/link lengths for formatted output.
#ifdef __APPLE__
  e.mtime = st.st_mtimespec.tv_sec;
  e.mtime_ns = (u32)st.st_mtimespec.tv_nsec;
#else
  e.mtime = st.st_mtim.tv_sec;
  e.mtime_ns = (u32)st.st_mtim.tv_nsec;
#endif
  e.rdev = (e.type == T_CHR || e.type == T_BLK) ? (u32)st.st_rdev : 0;
  e.dev = (u32)st.st_dev;
  e.hdev = (u64)st.st_dev, e.ino = (u64)st.st_ino, e.nlink = (u64)st.st_nlink;
#ifdef __APPLE__
  e.ctime = st.st_ctimespec.tv_sec, e.ctime_ns = (u32)st.st_ctimespec.tv_nsec;
#else
  e.ctime = st.st_ctim.tv_sec, e.ctime_ns = (u32)st.st_ctim.tv_nsec;
#endif
}

Entry source_snapshot(const Entry& scanned, const struct stat& st) {
  Entry e;
  entry_from_stat(st, e);
  e.name_off = scanned.name_off, e.name_len = scanned.name_len;
  e.link_off = scanned.link_off, e.flags = scanned.flags;
  e.item_flags = scanned.item_flags;
  if (!g_opt.perms) e.mode = scanned.mode;
  return e;
}

bool source_unchanged(int fd, const std::string& path, const struct stat& before) {
  struct stat after, named;
  if (fstat(fd, &after) != 0 || stat(path.c_str(), &named) != 0) return false;
  auto same = [&](const struct stat& st) {
#ifdef __APPLE__
    bool times = st.st_mtimespec.tv_sec == before.st_mtimespec.tv_sec && st.st_mtimespec.tv_nsec == before.st_mtimespec.tv_nsec &&
                 st.st_ctimespec.tv_sec == before.st_ctimespec.tv_sec && st.st_ctimespec.tv_nsec == before.st_ctimespec.tv_nsec;
#else
    bool times = st.st_mtim.tv_sec == before.st_mtim.tv_sec && st.st_mtim.tv_nsec == before.st_mtim.tv_nsec &&
                 st.st_ctim.tv_sec == before.st_ctim.tv_sec && st.st_ctim.tv_nsec == before.st_ctim.tv_nsec;
#endif
    return times && st.st_size == before.st_size && st.st_dev == before.st_dev && st.st_ino == before.st_ino && S_ISREG(st.st_mode);
  };
  return same(after) && same(named);
}

static void resolve_links(int fd, DirList& out, size_t first, unsigned flags) {
  char buf[PATH_MAX];
  for (size_t i = first; i < out.e.size(); i++) {
    if (out.e[i].type != T_LNK) continue;
    if (flags & LD_FOLLOW) {
      struct stat st;
      u32 off = out.e[i].name_off;
      u16 len = out.e[i].name_len;
      if (fstatat(fd, out.names.c_str() + off, &st, 0) == 0) {
        entry_from_stat(st, out.e[i]);
        out.e[i].name_off = off, out.e[i].name_len = len;
      } else {
        out.e[i].flags |= EF_DANGLING;
      }
    } else if (flags & LD_LINKS) {
      ssize_t n = readlinkat(fd, out.names.c_str() + out.e[i].name_off, buf, sizeof buf - 1);
      if (n < 0) n = 0, out.incomplete = true;
      out.e[i].link_off = out.add_str({buf, (size_t)n});
    }
  }
}

static int list_dir_generic(int fd, DirList& out) {
  DIR* dir = fdopendir(fd);
  if (!dir) {
    int e = errno;
    close(fd);
    return e;
  }
  for (;;) {
    errno = 0;
    dirent* de = readdir(dir);
    if (!de) {
      if (errno) out.incomplete = true;
      break;
    }
    const char* nm = de->d_name;
    if (nm[0] == '.' && (!nm[1] || (nm[1] == '.' && !nm[2]))) continue;
    struct stat st;
    if (fstatat(dirfd(dir), nm, &st, AT_SYMLINK_NOFOLLOW) != 0) {
      out.incomplete = true;
      continue;
    }
    Entry e;
    entry_from_stat(st, e);
    size_t len = strlen(nm);
    e.name_off = out.add_str({nm, len});
    e.name_len = (u16)len;
    out.e.push_back(e);
  }
  closedir(dir);  // owns the duplicated descriptor passed to fdopendir
  return 0;
}

static int list_dir_fd(int fd, DirList& out, unsigned flags) {
  if (fd < 0) return errno;
  size_t first = out.e.size();
#ifdef __APPLE__
  struct attrlist al {};
  al.bitmapcount = ATTR_BIT_MAP_COUNT;
  al.commonattr = ATTR_CMN_RETURNED_ATTRS | ATTR_CMN_ERROR | ATTR_CMN_NAME | ATTR_CMN_DEVID | ATTR_CMN_OBJTYPE |
                  ATTR_CMN_MODTIME | ATTR_CMN_OWNERID | ATTR_CMN_GRPID | ATTR_CMN_ACCESSMASK;
  al.fileattr = ATTR_FILE_DEVTYPE | ATTR_FILE_DATALENGTH;
  static thread_local std::vector<char> abuf(128 * 1024);
  bool fallback = false;
  for (;;) {
    int n = getattrlistbulk(fd, &al, abuf.data(), abuf.size(), 0);
    if (n < 0) {
      if (errno == EINTR) continue;
      if (first == out.e.size() && (errno == ENOTSUP || errno == EINVAL)) {
        fallback = true;
        break;
      }
      int e = errno;
      close(fd);
      return e;
    }
    if (n == 0) break;
    const char* p = abuf.data();
    for (int i = 0; i < n; i++) {
      u32 len;
      memcpy(&len, p, 4);
      const char* f = p + 4;
      attribute_set_t ret;
      memcpy(&ret, f, sizeof ret);
      f += sizeof ret;
      u32 err = 0;
      if (ret.commonattr & ATTR_CMN_ERROR) memcpy(&err, f, 4), f += 4;
      const char* nm = nullptr;
      size_t nlen = 0;
      if (ret.commonattr & ATTR_CMN_NAME) {
        attrreference_t ar;
        memcpy(&ar, f, sizeof ar);
        nm = f + ar.attr_dataoffset;
        nlen = ar.attr_length ? ar.attr_length - 1 : 0;
        f += sizeof ar;
      }
      Entry e;
      u32 objtype = 0, v32;
      if (ret.commonattr & ATTR_CMN_DEVID) memcpy(&v32, f, 4), e.dev = v32, f += 4;
      if (ret.commonattr & ATTR_CMN_OBJTYPE) memcpy(&objtype, f, 4), f += 4;
      if (ret.commonattr & ATTR_CMN_MODTIME) {
        timespec ts;
        memcpy(&ts, f, sizeof ts);
        e.mtime = ts.tv_sec, e.mtime_ns = (u32)ts.tv_nsec;
        f += sizeof ts;
      }
      if (ret.commonattr & ATTR_CMN_OWNERID) memcpy(&e.uid, f, 4), f += 4;
      if (ret.commonattr & ATTR_CMN_GRPID) memcpy(&e.gid, f, 4), f += 4;
      if (ret.commonattr & ATTR_CMN_ACCESSMASK) memcpy(&v32, f, 4), e.mode = v32 & 07777, f += 4;
      if (ret.fileattr & ATTR_FILE_DEVTYPE) memcpy(&e.rdev, f, 4), f += 4;
      if (ret.fileattr & ATTR_FILE_DATALENGTH) memcpy(&e.size, f, 8), f += 8;
      p += len;
      if (!nm) {
        out.incomplete = true;
        continue;
      }
      switch (objtype) {
        case VREG: e.type = T_REG; break;
        case VDIR: e.type = T_DIR; break;
        case VLNK: e.type = T_LNK; break;
        case VFIFO: e.type = T_FIFO; break;
        case VSOCK: e.type = T_SOCK; break;
        case VCHR: e.type = T_CHR; break;
        case VBLK: e.type = T_BLK; break;
        default: e.type = T_NONE;
      }
      const u32 want = ATTR_CMN_OBJTYPE | ATTR_CMN_MODTIME | ATTR_CMN_ACCESSMASK;
      if (g_opt.hard_links || err || (ret.commonattr & want) != want || (e.type == T_REG && !(ret.fileattr & ATTR_FILE_DATALENGTH))) {
        // Attributes missing for this entry: fall back to a plain lstat.
        struct stat st;
        std::string tmp(nm, nlen);
        if (fstatat(fd, tmp.c_str(), &st, AT_SYMLINK_NOFOLLOW) != 0) {
          out.incomplete = true;
          continue;
        }
        entry_from_stat(st, e);
      }
      if (e.type != T_REG) {
        e.size = 0;
        if (output_enabled() || g_opt.list_only) {
          struct stat st;
          std::string name(nm, nlen);
          if (fstatat(fd, name.c_str(), &st, AT_SYMLINK_NOFOLLOW) == 0) e.size = st.st_size;
          else out.incomplete = true;
        }
      }
      if (e.type != T_CHR && e.type != T_BLK) e.rdev = 0;
      e.name_off = out.add_str({nm, nlen});
      e.name_len = (u16)nlen;
      out.e.push_back(e);
    }
  }
  if (fallback) {
    int fd2 = dup(fd);
    if (fd2 < 0 || list_dir_generic(fd2, out) != 0) {
      int e = errno;
      close(fd);
      return e ? e : EIO;
    }
  }
#else
  {
    int fd2 = dup(fd);
    int e = fd2 < 0 ? errno : list_dir_generic(fd2, out);
    if (e) {
      close(fd);
      return e;
    }
  }
#endif
  if (flags & (LD_LINKS | LD_FOLLOW)) resolve_links(fd, out, first, flags);
  close(fd);
  out.sort();
  return 0;
}

int list_dir(const char* path, DirList& out, unsigned flags) {
  return list_dir_fd(open(path, O_RDONLY | O_DIRECTORY | O_CLOEXEC), out, flags);
}
int destination_list_dir(const char* path, DirList& out, unsigned flags) {
  return list_dir_fd(destination_open_dir(path), out, flags);
}

static bool hash_fd(int fd, u64 out[2]) {
  if (fd < 0) return false;
  static thread_local std::vector<char> hb(256 * 1024);
  XXH3_state_t st;
  XXH3_128bits_reset(&st);
  for (;;) {
    ssize_t n = read(fd, hb.data(), hb.size());
    if (n < 0 && errno == EINTR) continue;
    if (n < 0) {
      close(fd);
      return false;
    }
    if (n == 0) break;
    XXH3_128bits_update(&st, hb.data(), (size_t)n);
  }
  close(fd);
  XXH128_hash_t h = XXH3_128bits_digest(&st);
  out[0] = h.low64, out[1] = h.high64;
  return true;
}

bool hash_file(const char* path, u64 out[2]) {
  return hash_fd(open(path, O_RDONLY | O_CLOEXEC), out);
}
bool destination_hash_file(const char* path, u64 out[2]) {
  auto p = destination_path(path);
  if (p.fd < 0) return false;
  int fd = openat(p.fd, p.name.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  struct stat st;
  if (fd >= 0 && (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode))) {
    close(fd);
    errno = EINVAL;
    return false;
  }
  return hash_fd(fd, out);
}

bool hash_prefix_fd(int fd, i64 size, u64 out[2]) {
  if (size < 0) { errno = EINVAL; return false; }
  std::vector<char> bytes(256 * 1024);
  XXH3_state_t hash;
  XXH3_128bits_reset(&hash);
  for (i64 offset = 0; offset < size;) {
    if (g_stop.load()) { errno = EINTR; return false; }
    ssize_t n = pread(fd, bytes.data(), (size_t)std::min<i64>(bytes.size(), size - offset), offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { if (!n) errno = EIO; return false; }
    XXH3_128bits_update(&hash, bytes.data(), (size_t)n);
    offset += n;
  }
  auto digest = XXH3_128bits_digest(&hash);
  out[0] = digest.low64, out[1] = digest.high64;
  return true;
}

ResumePrefix destination_resume_prefix(const char* path, i64 limit) {
  ResumePrefix prefix;
  auto target = destination_path(path);
  if (target.fd < 0 || limit <= 0) return prefix;
  int fd = openat(target.fd, target.name.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  struct stat before;
  if (fd >= 0 && fstat(fd, &before) == 0 && S_ISREG(before.st_mode) && before.st_size > 0) {
    prefix.size = std::min<i64>(before.st_size, limit);
    if (!hash_prefix_fd(fd, prefix.size, prefix.sum) || !source_unchanged(fd, path, before)) prefix = {};
  }
  if (fd >= 0) close(fd);
  return prefix;
}

// ---------------------------------------------------------------- generator

void src_path_of(const DirWork& w, u32 i, std::string& out) {
  if (!w.src_paths.empty()) out = w.src_paths[i];
  else {
    out.assign(w.src_path);
    out.push_back('/');
    out.append(w.src.name_sv(w.src.e[i]));
  }
}

namespace {

struct DeleteCandidate { std::string path, rel, parent; u8 type; std::shared_ptr<const FilterList> filters; };
struct DeleteScan {
  std::string path, rel;
  std::vector<std::string> names;
  std::shared_ptr<const ReceiverFilterNode> node;
};
struct FinalDirectory {
  std::string path, rel, source;
  Entry attrs;
  bool mode_ok, time_ok, modified, reported;
};
std::mutex final_mu;
std::vector<DeleteCandidate> delete_candidates;
std::vector<DeleteScan> delete_scans;
std::vector<FinalDirectory> final_directories;
u64 deletion_count = 0;
bool deletion_limit_reported = false;

bool same_secs(const Entry& a, const Entry& b) {
  if (g_opt.modify_window == 0) return a.mtime == b.mtime;
  i64 d = a.mtime - b.mtime;
  return (d < 0 ? -d : d) <= g_opt.modify_window;
}
bool same_time_exact(const Entry& a, const Entry& b) {
  if (g_opt.modify_window != 0) return same_secs(a, b);
  return a.mtime == b.mtime && a.mtime_ns == b.mtime_ns;
}

void set_mtime(const char* path, const Entry& s, bool nofollow) {
  timespec ts[2];
  ts[0].tv_sec = 0, ts[0].tv_nsec = UTIME_OMIT;
  ts[1].tv_sec = s.mtime, ts[1].tv_nsec = s.mtime_ns;
  check_attr(destination_times(path, ts), path, "times");
}

void set_mode(const char* path, u32 mode, bool link) {
  if (!link) check_attr(destination_chmod(path, mode), path, "permissions");
#ifdef __APPLE__
  else check_attr(destination_chmod(path, mode), path, "permissions");  // symlinks carry their own permission bits on macOS
#endif
}

void item(Worker& t, const char* code, std::string_view rel, const Entry& entry,
          std::string_view source = {}, const char* target = nullptr, i64 bytes = 0, i64 size = -1) {
  if (!output_enabled()) return;
  if (!g_opt.am_server || g_output_sink) {
    output_event({code, std::string(rel), std::string(source), target ? target : "", entry.type, size < 0 ? entry.size : size, bytes});
    return;
  }
  bool is_dir = entry.type == T_DIR;
  std::string l;
  if (g_opt.itemize) l.append(code).push_back(' ');
  l.append(rel.empty() ? "." : rel);
  if (is_dir) l.push_back('/');
  if (target) l.append(" -> ").append(target);
  t.logf(l);
}

void item_delete(Worker& t, std::string_view rel, bool is_dir) {
  if (!output_enabled()) return;
  if (!g_opt.am_server || g_output_sink) {
    output_event({"*deleting  ", std::string(rel), {}, {}, (u8)(is_dir ? T_DIR : T_NONE)});
    return;
  }
  std::string l = g_opt.itemize ? "*deleting   " : "deleting ";
  l.append(rel);
  if (is_dir) l.push_back('/');
  t.logf(l);
}

void order_deletions(DirList& list) {
  if (!g_opt.delete_after && !g_opt.prune_empty) return;
  // The non-incremental file list used by delete-after and -m groups a directory's
  // files before its subdirectories. Deletion walks that list backwards.
  std::sort(list.e.begin(), list.e.end(), [&](const Entry& a, const Entry& b) {
    if ((a.type == T_DIR) != (b.type == T_DIR)) return a.type != T_DIR;
    return name_cmp(list.name_sv(a), list.name_sv(b)) < 0;
  });
}

bool remove_tree(const std::string& path, u8 type, const std::string& rel, Worker& t, bool limited = false, bool report = true,
                 std::shared_ptr<const FilterList> context = {}) {
  auto permit = [&] {
    if (!limited || g_opt.max_delete < 0 || deletion_count < (u64)g_opt.max_delete) return true;
    if (!deletion_limit_reported) {
      deletion_limit_reported = true;
      err_line(RERR_DEL_LIMIT, "Deletions stopped due to --max-delete limit (%lld)", (long long)g_opt.max_delete);
    }
    return false;
  };
  if (!permit()) return false;
  if (type == T_DIR) {
    context = directory_filters(context, path, true);
    const FilterList& filters = context ? *context : g_opt.filters;
    DirList l;
    int e = destination_list_dir(path.c_str(), l, 0);
    if (e == EACCES && check_attr(destination_chmod(path.c_str(), 0700), path.c_str(), "permissions")) e = destination_list_dir(path.c_str(), l, 0);
    if (e) {
      err_line(RERR_PARTIAL, "delete_file: opendir \"%s\" failed: %s", path.c_str(), errstr(e).c_str());
      return false;
    }
    order_deletions(l);
    bool ok = true;
    for (size_t i = l.e.size(); i > 0; i--) {
      const Entry& c = l.e[i - 1];
      std::string crel = rel_join(rel, l.name_sv(c));
      // Excluded files are protected from deletion, which keeps their directory alive too.
      std::string absolute;
      if (filters.has_absolute()) absolute = FilterList::absolute_path(path_join(path, l.name_sv(c)));
      if (filters.protected_from_deletion(crel, c.type == T_DIR, g_opt.delete_excluded, true, absolute)) {
        if (ok && !g_opt.quiet) t.logf("cannot delete non-empty directory: " + rel);
        ok = false;
        continue;
      }
      ok &= remove_tree(path_join(path, l.name_sv(c)), c.type, crel, t, limited, true, context);
    }
    if (!ok) return false;
    if (!permit()) return false;
    if (!g_opt.dry_run && destination_rmdir(path.c_str()) != 0) {
      err_line(RERR_PARTIAL, "delete_file: rmdir \"%s\" failed: %s", path.c_str(), errstr(errno).c_str());
      return false;
    }
  } else if (!g_opt.dry_run && destination_unlink(path.c_str()) != 0 && errno != ENOENT) {
    err_line(RERR_PARTIAL, "delete_file: unlink \"%s\" failed: %s", path.c_str(), errstr(errno).c_str());
    return false;
  }
  if (report) item_delete(t, rel, type == T_DIR);
  g_stats.deleted.fetch_add(1, std::memory_order_relaxed);
  if (limited) deletion_count++;
  return true;
}

// Remove whatever occupies `path` so that something of a different type can replace it.
bool make_way(const std::string& path, const Entry& d, const std::string& rel, const char* what, Worker& t,
              const std::shared_ptr<const FilterList>& context) {
  if (d.type == T_DIR && !g_opt.force && !g_opt.del) {
    // Without --force/--delete only an empty directory may be replaced.
    if (g_opt.dry_run || destination_rmdir(path.c_str()) == 0) return true;
    err_line(RERR_PARTIAL, "could not make way for new %s: %s", what, rel.c_str());
    return false;
  }
  return remove_tree(path, d.type, rel, t, false, false, context);
}

// Bring owner/group/mode/mtime of an existing, up-to-date destination entry in line.
void tweak_attrs(const char* path, const Entry& s, const Entry& d, std::string_view rel, char kind, Worker& t, DirWork& work, u32 index) {
  const Options& o = g_opt;
  bool link = s.type == T_LNK;
  bool time_same = (g_opt.checksum && kind == 'f') ? same_time_exact(s, d) : same_secs(s, d);
  char code[12] = ".f.........";
  code[1] = kind;
  bool changed = false;
  if (o.group && d.gid != s.gid && can_set_gid(s.gid)) {
    if (!o.dry_run) check_attr(destination_chown(path, (uid_t)-1, s.gid), path, "ownership");
    code[7] = 'g', changed = true;
  }
  if (o.owner && o.am_root && d.uid != s.uid) {
    if (!o.dry_run) check_attr(destination_chown(path, s.uid, (gid_t)-1), path, "ownership");
    code[6] = 'o', changed = true;
  }
  if (o.perms && (d.mode != s.mode || (changed && (s.mode & 06000)))) {
    if (!o.dry_run) set_mode(path, s.mode, link);
    if (d.mode != s.mode) code[5] = 'p';
    changed = true;
  }
  if (o.xattrs) {
    const FilterList& filters = work.receiver_filter ? *work.receiver_filter : o.filters;
    if (s.item_flags & IF_XATTR) code[10] = 'x', changed = true;
    if (s.item_flags & IF_XATTR) apply_xattrs(work.src_xattrs[index], path, s.type, filters);
  }
  if (o.times && !(link && o.omit_link_times) && (!time_same || (s.item_flags & IF_XATTR))) {
    if (!o.dry_run) set_mtime(path, s, link);
    if (!same_secs(s, d)) code[4] = 't', changed = true;
  }
  if (changed && o.output_attrs) note_item(work, index, code, 0, t);
  else if (!changed && o.output_unchanged) {
    memset(code + 2, ' ', 9);
    note_item(work, index, code, 0, t);
  }
}

}  // namespace

void skip_unsafe_links(DirWork& w, Worker& t) {
  if (!g_opt.safe_links) return;
  for (Entry& e : w.src.e) if (e.type == T_LNK && unsafe_link(w.src.link(e), w.rel)) {
    if (g_opt.verbose && !g_opt.quiet) t.logf("ignoring unsafe symlink \"" + rel_join(w.rel, w.src.name_sv(e)) + "\"");
    // Retain its name in the list so --delete protects an existing receiver entry.
    e.type = T_NONE;
  }
}

void generate(DirWork& w, Worker& t) {
  const Options& o = g_opt;
  bool load_filters = w.has_attrs || !w.rel.empty();
  if (o.delete_after)
    w.receiver_filter_node = std::make_shared<const ReceiverFilterNode>(ReceiverFilterNode{w.dst_path, w.receiver_filter_node, load_filters});
  else if (load_filters) w.receiver_filter = directory_filters(w.receiver_filter, w.dst_path, true);
  const FilterList& filters = w.receiver_filter ? *w.receiver_filter : o.filters;
  DirList& src = w.src;
  DirList& dl = t.dl;
  dl.clear();
  const size_t n = src.e.size();
  w.need.clear();
  skip_unsafe_links(w, t);
  reject_name_collisions(w);

  if (!w.created) {
    if (!w.rename_to.empty() || (!o.del && n <= 2)) {
      for (size_t i = 0; i < n; i++) {
        std::string_view nm = w.dst_name((u32)i);
        t.p1.assign(w.dst_path).push_back('/');
        t.p1.append(nm);
        struct stat st;
        if (destination_stat(t.p1.c_str(), &st) != 0) continue;
        Entry d;
        entry_from_stat(st, d);
        d.name_off = dl.add_str(nm);
        d.name_len = (u16)nm.size();
        dl.e.push_back(d);
      }
    } else {
      int e = destination_list_dir(w.dst_path.c_str(), dl, 0);
      if (e && !(e == ENOENT && o.dry_run)) {
        err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", w.dst_path.c_str(), errstr(e).c_str());
        for (Entry& s : src.e) s.flags &= (u8)~EF_DESCEND;
        return;
      }
      if (dl.incomplete) w.no_delete = true;
    }
  }
  if (o.del && o.delete_after && !w.no_delete && w.rename_to.empty()) {
    DeleteScan scan{w.dst_path, w.rel, {}, w.receiver_filter_node};
    scan.names.reserve(n);
    for (size_t i = 0; i < n; ++i)
      if (!(src.e[i].item_flags & IF_PRUNED)) scan.names.emplace_back(w.dst_name((u32)i));
    std::sort(scan.names.begin(), scan.names.end(), [](const auto& a, const auto& b) { return name_cmp(a, b) < 0; });
    std::lock_guard<std::mutex> lock(final_mu);
    delete_scans.push_back(std::move(scan));
  }
  // Group that newly created children will get: the directory's on BSD/macOS, ours on Linux
  // unless the directory is setgid. Only looked up when something is about to be created.
  w.dgid = getegid();
  bool dgid_known = !o.group;
  auto need_dgid = [&] {
    if (dgid_known) return;
    dgid_known = true;
    struct stat st;
    if (destination_stat(w.dst_path.c_str(), &st) != 0) return;
#ifdef __APPLE__
    w.dgid = st.st_gid;
#else
    if (st.st_mode & S_ISGID) w.dgid = st.st_gid;
#endif
  };

  u64 seen_files = 0, seen_dirs = 0, seen_links = 0, seen_spec = 0, seen_bytes = 0, plan_bytes = 0;
  std::string rel, path;
  auto set_names = [&](std::string_view nm) {
    path.assign(w.dst_path).push_back('/');
    path.append(nm);
    rel.assign(w.rel);
    if (!rel.empty()) rel.push_back('/');
    rel.append(nm);
  };
  auto extra = [&](const Entry& d) {
    if (!o.del || o.delete_after || w.no_delete || !w.rename_to.empty()) return;
    set_names(dl.name_sv(d));
    std::string absolute;
    if (filters.has_absolute()) absolute = FilterList::absolute_path(path);
    if (filters.protected_from_deletion(rel, d.type == T_DIR, o.delete_excluded, false, absolute)) return;
    std::lock_guard<std::mutex> lock(final_mu);
    delete_candidates.push_back({path, rel, w.dst_path, d.type, w.receiver_filter});
  };

  size_t j = 0;
  const size_t m = dl.e.size();
  for (size_t i = 0; i < n; i++) {
    Entry& s = src.e[i];
    std::string_view name = w.dst_name((u32)i);
    const Entry* d = nullptr;
    while (j < m) {
      int c = name_cmp(dl.name_sv(dl.e[j]), name);
      if (c < 0) {
        extra(dl.e[j++]);
        continue;
      }
      if (c == 0) d = &dl.e[j++];
      break;
    }
    if (s.item_flags & IF_PRUNED) { if (d) extra(*d); continue; }
    set_names(name);
    if (o.xattrs && !w.src_xattrs[i].complete) continue;

    auto compare_xattrs = [&] {
      if (o.xattrs && d && d->type == s.type && xattrs_differ(w.src_xattrs[i], path, s.type, filters)) s.item_flags |= IF_XATTR;
    };
    switch (s.type) {
      case T_DIR: {
        seen_dirs++;
        bool keep = d && d->type == T_DIR;
        compare_xattrs();
        if (keep && output_enabled()) {
          DirWork directory;
          directory.rel = rel;
          directory.attrs = s;
          if (!w.output_sources.empty()) directory.attr_source = w.output_sources[i];
          else src_path_of(w, (u32)i, directory.attr_source);
          note_directory(directory, d, false, t);
        }
        u32 final_mode = o.perms ? s.mode : keep ? d->mode : (s.mode & 0777 & ~g_umask);
        bool time_ok = false;
        if (keep) {
          s.flags |= EF_EXISTS | EF_DESCEND;
          if (d->mode == final_mode) s.flags |= EF_MODE_OK;
          if (same_secs(s, *d)) s.flags |= EF_TIME_OK, time_ok = true;
          // A directory we cannot write into is opened up while we work in it; finish_dir()
          // puts the final mode back.
          if (!o.am_root && (d->mode & 0300) != 0300 && !o.dry_run && check_attr(destination_chmod(path.c_str(), d->mode | 0700), path.c_str(), "permissions")) s.flags &= (u8)~EF_MODE_OK;
          if (o.group && d->gid != s.gid && can_set_gid(s.gid) && !o.dry_run) check_attr(destination_chown(path.c_str(), (uid_t)-1, s.gid), path.c_str(), "ownership");
          if (o.owner && o.am_root && d->uid != s.uid && !o.dry_run) check_attr(destination_chown(path.c_str(), s.uid, (gid_t)-1), path.c_str(), "ownership");
        } else {
          if (!d && o.existing) break;
          if (d && !make_way(path, *d, rel, "directory", t, w.receiver_filter)) break;
          need_dgid();
          if (!d && w.lazy_children && o.recursive && s.rdev != 1) {
            s.flags |= EF_CREATED | EF_DESCEND | EF_LAZY;
            if ((final_mode | 0700) == final_mode && !(final_mode & 07000)) s.flags |= EF_MODE_OK;
            w.modified = true;
            g_stats.created_dirs.fetch_add(1, std::memory_order_relaxed);
            note_item(w, (u32)i, "cd+++++++++", 0, t);
          } else if (!o.dry_run && destination_mkdir(path.c_str(), final_mode | 0700) != 0) {
            if (errno != EEXIST) {
              file_io_error(errno, path.c_str(), "recv_generator: mkdir");
              break;
            }
            s.flags |= EF_EXISTS | EF_DESCEND;
          } else {
            s.flags |= EF_CREATED | EF_DESCEND;
            if ((final_mode | 0700) == final_mode && !(final_mode & 07000)) s.flags |= EF_MODE_OK;
            w.modified = true;
            g_stats.created_dirs.fetch_add(1, std::memory_order_relaxed);
            note_item(w, (u32)i, "cd+++++++++", 0, t);
            if (!o.dry_run) {
              if (o.group && s.gid != w.dgid && can_set_gid(s.gid)) check_attr(destination_chown(path.c_str(), (uid_t)-1, s.gid), path.c_str(), "ownership");
              if (o.owner && o.am_root && s.uid != my_uid) check_attr(destination_chown(path.c_str(), s.uid, (gid_t)-1), path.c_str(), "ownership");
            }
          }
        }
        if (o.xattrs && (!keep || (s.item_flags & IF_XATTR)) && !(s.flags & EF_LAZY)) apply_xattrs(w.src_xattrs[i], path, T_DIR, filters);
        // Resource-fork and other metadata writes can change filesystem mtimes.
        if (s.item_flags & IF_XATTR) s.flags &= (u8)~EF_TIME_OK, time_ok = false;
        s.mode = final_mode;
        if ((!o.recursive && !(s.item_flags & IF_SELECTED_CHILD)) || s.rdev == 1) {
          // Not descended into: finish its attributes right away.
          if (!o.dry_run) {
            if (!(s.flags & EF_MODE_OK)) check_attr(destination_chmod(path.c_str(), final_mode), path.c_str(), "permissions");
            if (o.times && !o.omit_dir_times && !time_ok) set_mtime(path.c_str(), s, false);
          }
          s.flags &= (u8)~EF_DESCEND;
        }
        break;
      }

      case T_REG: {
        seen_files++;
        seen_bytes += (u64)s.size;
        if ((o.max_size > 0 && s.size > o.max_size) || (o.min_size > 0 && s.size < o.min_size)) break;
        bool transfer = false;
        if (!d) {
          if (o.existing) break;
          transfer = true;
        } else if (o.ignore_existing) {
          break;
        } else if (d->type != T_REG) {
          s.item_flags |= IF_NEW_TYPE;
          if (d->type == T_DIR) {
            if (!make_way(path, *d, rel, "regular file", t, w.receiver_filter)) break;
            w.modified = true;
            d = nullptr;
          } else {
            s.flags |= EF_EXISTS;
          }
          transfer = true;
        } else {
          if (o.update && (d->mtime > s.mtime || (d->mtime == s.mtime && d->mtime_ns > s.mtime_ns))) break;
          compare_xattrs();
          bool same;
          if (o.checksum) {
            same = d->size == s.size;
            if (same) {
              u64 hs[2], hd[2];
              if (!src.sums.empty()) hs[0] = src.sums[2 * i], hs[1] = src.sums[2 * i + 1];
              else {
                src_path_of(w, (u32)i, t.p2);
                if (!hash_file(t.p2.c_str(), hs)) {
                  hs[0] = hs[1] = 0, same = false;
                  g_source_io_error.store(true);
                  err_line(RERR_PARTIAL, "source checksum read failed on \"%s\": %s", t.p2.c_str(), errstr(errno).c_str());
                }
              }
              if (same) same = destination_hash_file(path.c_str(), hd) && hs[0] == hd[0] && hs[1] == hd[1];
            }
          } else if (o.ignore_times) {
            same = false;
          } else if (o.size_only) {
            same = d->size == s.size;
          } else {
            same = d->size == s.size && same_secs(s, *d);
          }
          if (same) {
            if (!o.perms) s.mode = d->mode;
            hardlink_prepare(w, (u32)i, d);
            hardlink_complete(w, (u32)i, s);
            tweak_attrs(path.c_str(), s, *d, rel, 'f', t, w, (u32)i);
            break;
          }
          s.flags |= EF_EXISTS | EF_INPLACE_SAFE;
          if (d->size != s.size) s.flags |= EF_DIFF_SIZE;
          if (!same_secs(s, *d)) s.flags |= EF_DIFF_TIME;
          if (o.perms && d->mode != s.mode) s.item_flags |= IF_PERMS;
          if (o.owner && o.am_root && d->uid != s.uid) s.item_flags |= IF_OWNER;
          if (o.group && d->gid != s.gid && can_set_gid(s.gid)) s.item_flags |= IF_GROUP;
          if (!o.perms) s.mode = d->mode;
          transfer = true;
        }
        if (transfer) {
          hardlink_prepare(w, (u32)i, d);
          if (o.dry_run) hardlink_complete(w, (u32)i, s);
          if (!o.perms && !(d && d->type == T_REG)) s.mode = s.mode & 0777 & ~g_umask;
          w.need.push_back((u32)i);
          plan_bytes += (u64)s.size;
        }
        break;
      }

      case T_LNK: {
        seen_links++;
        if (d && o.ignore_existing) break;
        const char* target = src.link(s);
        compare_xattrs();
        if (d && d->type == T_LNK) {
          char buf[PATH_MAX];
          ssize_t k = destination_readlink(path.c_str(), buf, sizeof buf - 1);
          if (k >= 0 && (size_t)k == strlen(target) && memcmp(buf, target, (size_t)k) == 0) {
            if (!o.perms) s.mode = d->mode;
            hardlink_prepare(w, (u32)i, d);
            hardlink_complete(w, (u32)i, s);
            tweak_attrs(path.c_str(), s, *d, rel, 'L', t, w, (u32)i);
            break;
          }
        }
        if (d ? o.ignore_existing : o.existing) break;
        hardlink_prepare(w, (u32)i, d);
        u32 lmode = o.perms ? s.mode : (d && d->type == T_LNK) ? d->mode : (s.mode & 0777 & ~g_umask);
        char link_code[12] = "cL+++++++++";
        if (d && d->type == T_LNK) {
          memcpy(link_code + 2, "c........", 9);
          if (!same_secs(s, *d) || !o.times || o.omit_link_times) link_code[4] = o.times && !o.omit_link_times ? 't' : 'T';
          if (o.perms && lmode != d->mode) link_code[5] = 'p';
          if (o.owner && o.am_root && d->uid != s.uid) link_code[6] = 'o';
          if (o.group && d->gid != s.gid && can_set_gid(s.gid)) link_code[7] = 'g';
          if (s.item_flags & IF_XATTR) link_code[10] = 'x';
        }
        if (d) {
          if (d->type == T_DIR) {
            if (!make_way(path, *d, rel, "symlink", t, w.receiver_filter)) break;
          } else if (!o.dry_run) {
            destination_unlink(path.c_str());
          }
        }
        need_dgid();
        if (!o.dry_run) {
          if (destination_symlink(target, path.c_str()) != 0) {
            file_io_error(errno, path.c_str(), "symlink");
            break;
          }
          if (lmode != 0777) set_mode(path.c_str(), lmode, true);
          if (o.group && s.gid != w.dgid && can_set_gid(s.gid)) check_attr(destination_chown(path.c_str(), (uid_t)-1, s.gid), path.c_str(), "ownership");
          if (o.owner && o.am_root && s.uid != my_uid) check_attr(destination_chown(path.c_str(), s.uid, (gid_t)-1), path.c_str(), "ownership");
          if (o.xattrs) apply_xattrs(w.src_xattrs[i], path, T_LNK, filters);
          if (o.times && !o.omit_link_times) set_mtime(path.c_str(), s, true);
        }
        w.modified = true;
        g_stats.created_links.fetch_add(1, std::memory_order_relaxed);
        hardlink_complete(w, (u32)i, s);
        note_item(w, (u32)i, link_code, 0, t);
        break;
      }

      case T_FIFO:
      case T_SOCK:
      case T_CHR:
      case T_BLK: {
        seen_spec++;
        if (d && o.ignore_existing) break;
        bool dev = s.type == T_CHR || s.type == T_BLK;
        compare_xattrs();
        u32 final_mode = o.perms ? s.mode : (s.mode & 0777 & ~g_umask);
        if (d && d->type == s.type && (!dev || d->rdev == s.rdev)) {
          if (!o.perms) s.mode = d->mode;
          hardlink_prepare(w, (u32)i, d);
          hardlink_complete(w, (u32)i, s);
          tweak_attrs(path.c_str(), s, *d, rel, dev ? 'D' : 'S', t, w, (u32)i);
          break;
        }
        if (d ? o.ignore_existing : o.existing) break;
        hardlink_prepare(w, (u32)i, d);
        if (d) {
          if (d->type == T_DIR) {
            if (!make_way(path, *d, rel, "special file", t, w.receiver_filter)) break;
          } else if (!o.dry_run) {
            destination_unlink(path.c_str());
          }
        }
        need_dgid();
        if (!o.dry_run) {
          int r;
          if (s.type == T_FIFO) r = destination_mkfifo(path.c_str(), final_mode);
          else r = destination_mknod(path.c_str(), (s.type == T_SOCK ? S_IFSOCK : s.type == T_CHR ? S_IFCHR : S_IFBLK) | final_mode, (dev_t)s.rdev);
          if (r != 0) {
            if (s.type != T_SOCK || errno == ENOSPC || errno == EDQUOT) file_io_error(errno, path.c_str(), "mknod");
            break;
          }
          if (o.perms) check_attr(destination_chmod(path.c_str(), final_mode), path.c_str(), "permissions");
          if (o.group && s.gid != w.dgid && can_set_gid(s.gid)) check_attr(destination_chown(path.c_str(), (uid_t)-1, s.gid), path.c_str(), "ownership");
          if (o.owner && o.am_root && s.uid != my_uid) check_attr(destination_chown(path.c_str(), s.uid, (gid_t)-1), path.c_str(), "ownership");
          if (o.xattrs) apply_xattrs(w.src_xattrs[i], path, s.type, filters);
          if (o.times) set_mtime(path.c_str(), s, false);
        }
        w.modified = true;
        g_stats.created_specials.fetch_add(1, std::memory_order_relaxed);
        hardlink_complete(w, (u32)i, s);
        note_item(w, (u32)i, dev ? "cD+++++++++" : "cS+++++++++", 0, t);
        break;
      }
      default: break;
    }
  }
  for (; j < m; j++) extra(dl.e[j]);

  g_stats.files_seen.fetch_add(seen_files, std::memory_order_relaxed);
  g_stats.dirs_seen.fetch_add(seen_dirs, std::memory_order_relaxed);
  g_stats.links_seen.fetch_add(seen_links, std::memory_order_relaxed);
  g_stats.specials_seen.fetch_add(seen_spec, std::memory_order_relaxed);
  g_stats.bytes_seen.fetch_add(seen_bytes, std::memory_order_relaxed);
  if (!w.need.empty()) {
    need_dgid();
    g_stats.xfer_files_total.fetch_add(w.need.size(), std::memory_order_relaxed);
    g_stats.xfer_bytes_total.fetch_add(plan_bytes, std::memory_order_relaxed);
  }
}

void finish_dir(DirWork& w) {
  const Options& o = g_opt;
  if (!w.has_attrs || o.dry_run) return;
  std::lock_guard<std::mutex> lock(final_mu);
  final_directories.push_back({w.dst_path, w.rel, w.attr_source.empty() ? w.src_path : w.attr_source,
                               w.attrs, w.mode_ok, w.time_ok, w.modified.load(), w.directory_reported});
}

void finalize_tree() {
  Worker worker;
  std::vector<std::string> dirty = hardlink_finalize();
  if (g_source_io_error.load() && !g_opt.ignore_errors && g_opt.del) {
    err_line(0, "IO error encountered -- skipping file deletion");
  } else {
    if (g_opt.delete_after) {
      // Load each logical parent once, preserving its rules even if a merge
      // file is itself removed before the deletion walk reaches a child.
      std::unordered_map<const ReceiverFilterNode*, std::shared_ptr<const FilterList>> contexts;
      auto refresh = [&](const std::shared_ptr<const ReceiverFilterNode>& node) {
        std::vector<const ReceiverFilterNode*> chain;
        auto current = node.get();
        while (current && !contexts.count(current)) { chain.push_back(current); current = current->parent.get(); }
        auto context = current ? contexts.at(current) : std::shared_ptr<const FilterList>();
        for (auto i = chain.rbegin(); i != chain.rend(); ++i) {
          if ((*i)->load) context = directory_filters(context, (*i)->path, true);
          contexts.emplace(*i, context);
        }
        return context;
      };
      std::sort(delete_scans.begin(), delete_scans.end(), [](const auto& a, const auto& b) { return name_cmp(a.rel, b.rel) < 0; });
      for (const auto& scan : delete_scans) {
        if (g_stop.load() || deletion_limit_reported) break;
        auto context = refresh(scan.node);
        const FilterList& filters = context ? *context : g_opt.filters;
        DirList listed;
        int error = destination_list_dir(scan.path.c_str(), listed, 0);
        if (error == ENOENT && g_opt.dry_run) continue;
        if (error || listed.incomplete) {
          err_line(RERR_PARTIAL, "delete-after: cannot list \"%s\": %s", scan.path.c_str(), error ? errstr(error).c_str() : "incomplete listing");
          continue;
        }
        order_deletions(listed);
        for (size_t i = listed.e.size(); i > 0; --i) {
          const Entry& entry = listed.e[i - 1];
          auto name = listed.name_sv(entry);
          auto found = std::lower_bound(scan.names.begin(), scan.names.end(), name,
                                       [](const auto& a, auto b) { return name_cmp(a, b) < 0; });
          if (found != scan.names.end() && name_cmp(*found, name) == 0) continue;
          std::string path = path_join(scan.path, name), rel = rel_join(scan.rel, name);
          std::string absolute = filters.has_absolute() ? FilterList::absolute_path(path) : "";
          if (filters.protected_from_deletion(rel, entry.type == T_DIR, g_opt.delete_excluded, false, absolute)) continue;
          u64 before = g_stats.deleted.load();
          remove_tree(path, entry.type, rel, worker, true, true, context);
          if (g_stats.deleted.load() != before) dirty.push_back(scan.path);
          if (g_stop.load() || deletion_limit_reported) break;
        }
      }
    }
    // rsync processes a directory's extras from the end of its sorted file list.
    std::sort(delete_candidates.begin(), delete_candidates.end(), [](const auto& a, const auto& b) {
      if (g_opt.prune_empty) {
        if (a.parent != b.parent) return name_cmp(a.parent, b.parent) < 0;
        if ((a.type == T_DIR) != (b.type == T_DIR)) return a.type == T_DIR;
      }
      return a.path > b.path;
    });
    for (const auto& candidate : delete_candidates) {
      if (g_stop.load()) break;
      u64 before = g_stats.deleted.load();
      remove_tree(candidate.path, candidate.type, candidate.rel, worker, true, true, candidate.filters);
      if (g_stats.deleted.load() != before) dirty.push_back(candidate.parent);
      if (deletion_limit_reported) break;
    }
  }
  worker.flush_log();
  std::sort(final_directories.begin(), final_directories.end(), [](const auto& a, const auto& b) {
    return std::count(a.path.begin(), a.path.end(), '/') > std::count(b.path.begin(), b.path.end(), '/');
  });
  for (const auto& dir : final_directories) {
    if (dir.rel.empty() && !dir.reported && g_opt.delete_before && g_opt.output_attrs && g_opt.times &&
        !g_opt.omit_dir_times && std::find(dirty.begin(), dirty.end(), dir.path) != dirty.end())
      item(worker, ".d..t......", dir.rel, dir.attrs, dir.source);
    if (!dir.mode_ok) check_attr(destination_chmod(dir.path.c_str(), dir.attrs.mode), dir.path.c_str(), "permissions");
    if (g_opt.times && !g_opt.omit_dir_times && (!dir.time_ok || dir.modified || std::find(dirty.begin(), dirty.end(), dir.path) != dirty.end()))
      set_mtime(dir.path.c_str(), dir.attrs, false);
  }
  worker.flush_log();
  delete_candidates.clear();
  delete_scans.clear();
  final_directories.clear();
}

// ---------------------------------------------------------------- writing files

struct OutputProgress {
  std::mutex mu;
  i64 prefix = 0;
  std::map<i64, i64> ranges;
};

namespace {
struct OpenOutput {
  int dir_fd;
  std::string name, tmp_name;
  bool temp, existed, partial, fd_open;
  std::shared_ptr<OutputProgress> progress;
};
std::recursive_mutex output_mu;
std::shared_mutex output_io_mu;
std::unordered_map<int, OpenOutput> open_outputs;
std::atomic<bool> output_shutdown{false};

void register_output(OutFile& f) {
  f.progress = g_opt.partial ? std::make_shared<OutputProgress>() : nullptr;
  open_outputs[f.fd] = {f.dir_fd, f.name, f.tmp_name, f.temp, f.existed, g_opt.partial, true, f.progress};
}

bool trim_partial(int fd, const OpenOutput& file) {
  if (!file.partial || (!file.temp && file.existed) || !file.fd_open) return true;
  std::lock_guard<std::mutex> lock(file.progress->mu);
  return ftruncate(fd, file.progress->prefix) == 0;
}
}

void cleanup_open_outputs() {
  std::lock_guard<std::recursive_mutex> lock(output_mu);
  output_shutdown.store(true);
  // Wait for writes to finish before trimming, closing and publishing a prefix.
  // Writes hold only the shared I/O lock and their own progress mutex.
  std::unique_lock<std::shared_mutex> io_lock(output_io_mu);
  for (const auto& [fd, f] : open_outputs) {
    bool keep = f.partial && trim_partial(fd, f);
    if (f.fd_open) close(fd);
    if (f.temp) {
      if (!keep || renameat(f.dir_fd, f.tmp_name.c_str(), f.dir_fd, f.name.c_str()) != 0)
        unlinkat(f.dir_fd, f.tmp_name.c_str(), 0);
    } else if (!f.existed && !keep) unlinkat(f.dir_fd, f.name.c_str(), 0);
    close(f.dir_fd);
  }
  open_outputs.clear();
}

bool out_write(OutFile& f, const char* bytes, size_t size, i64 offset) {
  std::shared_lock<std::shared_mutex> io_lock(output_io_mu);
  if (output_shutdown) { errno = ECANCELED; return false; }
  size_t done = 0;
  while (done < size) {
    size_t count = size - done;
    if (g_opt.bwlimit && !g_opt.am_server && !g_opt.pushing && !g_opt.receiving) {
      count = g_local_limiter.acquire(count);
      if (!count) { errno = ECANCELED; return false; }
    }
    ssize_t n = pwrite(f.fd, bytes + done, count, offset + (i64)done);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { if (!n) errno = EIO; return false; }
    done += (size_t)n;
  }
  if (g_opt.partial && size) {
    auto& progress = *f.progress;
    std::lock_guard<std::mutex> lock(progress.mu);
    i64 end = offset + (i64)size;
    auto next = progress.ranges.lower_bound(offset);
    if (next != progress.ranges.begin()) {
      auto previous = std::prev(next);
      if (previous->second >= offset) offset = previous->first, end = std::max(end, previous->second), next = progress.ranges.erase(previous);
    }
    while (next != progress.ranges.end() && next->first <= end) {
      end = std::max(end, next->second);
      next = progress.ranges.erase(next);
    }
    if (offset <= progress.prefix) progress.prefix = std::max(progress.prefix, end);
    else progress.ranges.emplace(offset, end);
    while (!progress.ranges.empty() && progress.ranges.begin()->first <= progress.prefix) {
      progress.prefix = std::max(progress.prefix, progress.ranges.begin()->second);
      progress.ranges.erase(progress.ranges.begin());
    }
  }
  return true;
}

bool out_restore_prefix(OutFile& f, const ResumePrefix& prefix) {
  int fd = openat(f.dir_fd, f.name.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  struct stat before;
  if (fd < 0) return false;
  if (fstat(fd, &before) != 0 || !S_ISREG(before.st_mode) || before.st_size < prefix.size) {
    close(fd);
    errno = ESTALE;
    return false;
  }
  std::vector<char> bytes(256 * 1024);
  XXH3_state_t hash;
  XXH3_128bits_reset(&hash);
  bool ok = true;
  struct stat output;
  bool inplace = fstat(f.fd, &output) == 0 && output.st_dev == before.st_dev && output.st_ino == before.st_ino;
  for (i64 offset = 0; offset < prefix.size;) {
    if (g_stop.load()) { errno = EINTR; ok = false; break; }
    ssize_t n = pread(fd, bytes.data(), (size_t)std::min<i64>(bytes.size(), prefix.size - offset), offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { if (!n) errno = ESTALE; ok = false; break; }
    XXH3_128bits_update(&hash, bytes.data(), (size_t)n);
    if (!inplace && !out_write(f, bytes.data(), (size_t)n, offset)) { ok = false; break; }
    offset += n;
  }
  auto digest = XXH3_128bits_digest(&hash);
  if (ok && (digest.low64 != prefix.sum[0] || digest.high64 != prefix.sum[1] || !source_unchanged(fd, f.path, before))) {
    errno = ESTALE;
    ok = false;
  }
  int error = errno;
  close(fd);
  errno = error;
  return ok;
}

static u64 next_rand(Worker& t) {
  if (!t.rng) t.rng = now_ns() ^ ((u64)getpid() << 32) ^ (u64)(uintptr_t)&t;
  t.rng ^= t.rng << 13, t.rng ^= t.rng >> 7, t.rng ^= t.rng << 17;
  return t.rng;
}

bool out_open(OutFile& f, DirWork& w, u32 idx, Worker& t, bool force_temp, bool readable) {
  std::lock_guard<std::recursive_mutex> lock(output_mu);
  if (output_shutdown || g_stop.load()) return false;
  const Options& o = g_opt;
  const Entry& s = w.src.e[idx];
  std::string_view name = w.dst_name(idx);
  f.path = path_join(w.dst_path, name);
  f.fd = f.dir_fd = -1;
  f.temp = false;
  f.size = -1;
  f.existed = s.flags & EF_EXISTS;
  auto p = destination_path(f.path);
  if (p.fd < 0) {
    file_io_error(errno, f.path.c_str(), "open destination parent");
    return false;
  }
  f.name = p.name;
  f.dir_fd = p.release();
  auto failed = [&](const char* operation) {
    int error = errno;
    close(f.dir_fd);
    f.dir_fd = -1;
    file_io_error(error, f.path.c_str(), operation);
    return false;
  };
  mode_t mode = s.mode & 0777;
  f.created_mode = mode;
  if (f.existed && o.inplace && (s.flags & EF_INPLACE_SAFE)) {
    f.fd = openat(f.dir_fd, f.name.c_str(), (readable ? O_RDWR : O_WRONLY) | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    if (f.fd < 0) return failed("open --inplace");
    struct stat st;
    if (fstat(f.fd, &st) != 0 || !S_ISREG(st.st_mode)) {
      close(f.fd);
      f.fd = -1;
      errno = EINVAL;
      return failed("open --inplace regular file");
    }
    register_output(f);
    return true;
  }
  if (!f.existed && (o.direct_new || o.inplace) && !force_temp) {
    f.fd = openat(f.dir_fd, f.name.c_str(), (readable ? O_RDWR : O_WRONLY) | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, mode);
    if (f.fd >= 0) { register_output(f); return true; }
    if (errno != EEXIST) return failed("open");
  }
  static const char al[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  for (int tries = 0; tries < 100; tries++) {
    f.tmp_name = "." + std::string(name.substr(0, std::min<size_t>(name.size(), 240))) + ".";
    u64 r = next_rand(t);
    for (int k = 0; k < 6; k++) f.tmp_name.push_back(al[r % 62]), r /= 62;
    f.tmp = path_join(w.dst_path, f.tmp_name);
    f.fd = openat(f.dir_fd, f.tmp_name.c_str(), (readable ? O_RDWR : O_WRONLY) | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, mode | 0600);
    if (f.fd >= 0) {
      f.temp = true;
      f.created_mode = mode | 0600;
      register_output(f);
      return true;
    }
    if (errno != EEXIST) break;
  }
  return failed("mkstemp");
}

void out_abort(OutFile& f, bool keep_partial) {
  std::lock_guard<std::recursive_mutex> lock(output_mu);
  if (output_shutdown) { f.fd = f.dir_fd = -1; return; }
  if (keep_partial && f.fd >= 0) {
    auto found = open_outputs.find(f.fd);
    if (found != open_outputs.end() && !trim_partial(f.fd, found->second)) keep_partial = false;
  }
  open_outputs.erase(f.fd);
  if (f.fd >= 0) close(f.fd);
  f.fd = -1;
  if (f.dir_fd < 0) return;
  if (f.temp) {
    if (keep_partial && renameat(f.dir_fd, f.tmp_name.c_str(), f.dir_fd, f.name.c_str()) != 0) {
      err_line(RERR_PARTIAL, "failed to keep partial \"%s\": %s", f.path.c_str(), errstr(errno).c_str());
      keep_partial = false;
    }
    if (!keep_partial) unlinkat(f.dir_fd, f.tmp_name.c_str(), 0);
  } else if (!f.existed && !keep_partial) unlinkat(f.dir_fd, f.name.c_str(), 0);
  close(f.dir_fd);
  f.dir_fd = -1;
}

bool out_finish(OutFile& f, DirWork& w, u32 idx, Worker&, bool ok, const Entry* attrs, const XattrSet* xattrs) {
  std::lock_guard<std::recursive_mutex> lock(output_mu);
  if (output_shutdown) { f.fd = f.dir_fd = -1; return false; }
  const Options& o = g_opt;
  const Entry& s = attrs ? *attrs : w.src.e[idx];
  if (!ok) { out_abort(f, o.partial); return false; }
  bool reused = !f.temp && f.existed;
  if (reused && f.size >= 0 && ftruncate(f.fd, f.size) != 0) {
    file_io_error(errno, f.path.c_str(), "truncate");
    out_abort(f);
    return false;
  }
  if (o.group && (reused || s.gid != w.dgid) && can_set_gid(s.gid)) check_attr(fchown(f.fd, (uid_t)-1, s.gid), f.path.c_str(), "ownership");
  if (o.owner && o.am_root && (reused || s.uid != my_uid)) check_attr(fchown(f.fd, s.uid, (gid_t)-1), f.path.c_str(), "ownership");
  if (reused || f.created_mode != s.mode) check_attr(fchmod(f.fd, s.mode), f.path.c_str(), "permissions");
  if (o.xattrs) apply_fd_xattrs(xattrs ? *xattrs : w.src_xattrs[idx], f.fd, f.path, T_REG,
                              w.receiver_filter ? *w.receiver_filter : o.filters, f.temp || !f.existed);
  if (o.times) {
    timespec ts[2] = {{0, UTIME_OMIT}, {s.mtime, (long)s.mtime_ns}};
    check_attr(futimens(f.fd, ts), f.path.c_str(), "times");
  }
  struct stat published;
  bool have_published = o.hard_links && fstat(f.fd, &published) == 0;
  int fd = f.fd;
  f.fd = -1;
  int closed = close(fd);
  open_outputs.at(fd).fd_open = false;
  if (closed != 0) {
    file_io_error(errno, f.path.c_str(), "close");
    open_outputs.erase(fd);
    out_abort(f);
    return false;
  }
  if (f.temp && renameat(f.dir_fd, f.tmp_name.c_str(), f.dir_fd, f.name.c_str()) != 0) {
    file_io_error(errno, f.path.c_str(), "rename");
    open_outputs.erase(fd);
    out_abort(f);
    return false;
  }
  open_outputs.erase(fd);
  close(f.dir_fd);
  f.dir_fd = -1;
  w.modified.store(true, std::memory_order_relaxed);
  if (have_published) hardlink_complete(w, idx, s, &published);
  return true;
}

bool clone_copy(DirWork& w, u32 idx, const char* source, unsigned flags, Worker& t) {
#ifdef __APPLE__
  std::lock_guard<std::recursive_mutex> lock(output_mu);
  OutFile f;
  Entry fresh;
  int source_fd = -1;
  struct stat before;
  if (g_opt.hard_links || g_opt.xattrs) {
    source_fd = open(source, O_RDONLY | O_CLOEXEC | (g_opt.copy_links || !w.src_paths.empty() ? 0 : O_NOFOLLOW));
    if (source_fd < 0 || fstat(source_fd, &before) != 0 || !S_ISREG(before.st_mode)) {
      if (source_fd >= 0) close(source_fd);
      return false;
    }
    fresh = source_snapshot(w.src.e[idx], before);
    if (g_opt.xattrs) {
      const auto& context = w.source_contexts.empty() ? w.source_filter : w.source_contexts[idx];
      w.src_xattrs[idx] = source_fd_xattrs(source_fd, source, T_REG, context ? *context : g_opt.filters);
      if (!w.src_xattrs[idx].complete) { close(source_fd); return false; }
    }
  }
  auto close_source = [&] { if (source_fd >= 0) close(source_fd); source_fd = -1; };
  if (!out_open(f, w, idx, t, true)) { close_source(); return false; }
  // Reserve a unique name and retain its directory while the clone replaces the
  // reservation. The kernel refuses any unexpected new occupant of that name.
  unlinkat(f.dir_fd, f.tmp_name.c_str(), 0);
  if (clonefileat(AT_FDCWD, source, f.dir_fd, f.tmp_name.c_str(), flags) != 0) {
    int error = errno;
    if (error == ENOSPC || error == EDQUOT) file_io_error(error, f.path.c_str(), "clonefile");
    out_abort(f);
    errno = error;
    close_source();
    return false;
  }
  if (source_fd >= 0 && (!source_unchanged(source_fd, source, before) ||
      (g_opt.xattrs && !source_xattrs_unchanged(w.src_xattrs[idx], source)))) {
    close_source();
    out_abort(f);
    errno = ESTALE;
    return false;
  }
  close_source();
  int fd = openat(f.dir_fd, f.tmp_name.c_str(), O_WRONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
  struct stat st;
  if (fd < 0 || fstat(fd, &st) != 0 || !S_ISREG(st.st_mode)) {
    if (fd >= 0) close(fd);
    out_abort(f);
    return false;
  }
  open_outputs.erase(f.fd);
  close(f.fd);
  f.fd = fd;
  f.created_mode = st.st_mode & 07777;
  register_output(f);
  return out_finish(f, w, idx, t, true, g_opt.hard_links || g_opt.xattrs ? &fresh : nullptr);
#else
  errno = ENOTSUP;
  return false;
#endif
}

bool write_whole(DirWork& w, u32 idx, const char* data, size_t len, Worker& t) {
  static thread_local OutFile o;  // reuse path buffers
  if (!out_open(o, w, idx, t)) return false;
  o.size = (i64)len;
  bool ok = out_write(o, data, len, 0);
  if (!ok) file_io_error(errno, o.path.c_str(), "write");
  return out_finish(o, w, idx, t, ok);
}

void note_item(DirWork& w, u32 idx, const char* code, i64 bytes, Worker& t, i64 size) {
  if (!output_enabled()) return;
  const Entry& entry = w.src.e[idx];
  std::string source;
  // A remote receiver has source paths only for logging, never for filesystem use.
  if (!w.output_sources.empty()) source = w.output_sources[idx];
  else if (!w.src_path.empty() || !w.src_paths.empty()) src_path_of(w, idx, source);
  if (hardlink_defer(w, idx, {code, rel_join(w.rel, w.src.name_sv(entry)), source,
       entry.type == T_LNK ? w.src.link(entry) : "", entry.type, size < 0 ? entry.size : size, bytes})) return;
  item(t, code, rel_join(w.rel, w.src.name_sv(entry)), entry, source,
       entry.type == T_LNK ? w.src.link(entry) : nullptr, bytes, size);
}

void note_directory(DirWork& w, const Entry* before, bool created, Worker& t) {
  if (!output_enabled()) return;
  const Options& o = g_opt;
  const Entry& source = w.attrs;
  char code[12] = ".d.........";
  bool changed = created;
  if (created) memcpy(code, "cd+++++++++", 11);
  else if (before) {
    if (o.times && !o.omit_dir_times && !same_secs(source, *before)) code[4] = 't', changed = true;
    if (o.perms && source.mode != before->mode) code[5] = 'p', changed = true;
    if (o.owner && o.am_root && source.uid != before->uid) code[6] = 'o', changed = true;
    if (o.group && source.gid != before->gid && can_set_gid(source.gid)) code[7] = 'g', changed = true;
    if (source.item_flags & IF_XATTR) code[10] = 'x', changed = true;
  }
  if (!changed && o.output_unchanged) memset(code + 2, ' ', 9);
  else if (!changed || (!created && !o.output_attrs)) return;
  item(t, code, w.rel, source, w.attr_source.empty() ? w.src_path : w.attr_source);
  w.directory_reported = true;
}

void note_transferred(DirWork& w, u32 idx, i64 bytes, Worker& t, i64 final_size) {
  const Options& o = g_opt;
  const Entry& s = w.src.e[idx];
  g_stats.xfer_files.fetch_add(1, std::memory_order_relaxed);
  if (!(s.flags & EF_EXISTS)) g_stats.created_files.fetch_add(1, std::memory_order_relaxed);
  if (!output_enabled()) return;
  char code[12] = ">f+++++++++";
  if (o.pushing) code[0] = '<';
  if ((s.flags & EF_EXISTS) && !(s.item_flags & IF_NEW_TYPE)) {
    memcpy(code + 2, ".........", 9);
    if (o.checksum) code[2] = 'c';
    if (s.flags & EF_DIFF_SIZE) code[3] = 's';
    if ((s.flags & EF_DIFF_TIME) || !o.times) code[4] = o.times ? 't' : 'T';
    if (s.item_flags & IF_PERMS) code[5] = 'p';
    if (s.item_flags & IF_OWNER) code[6] = 'o';
    if (s.item_flags & IF_GROUP) code[7] = 'g';
    if (s.item_flags & IF_XATTR) code[10] = 'x';
  }
  note_item(w, idx, code, bytes, t, final_size);
}
