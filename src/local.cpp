// Local (same machine) sync: parallel scan + parallel copy, no wire protocol.
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <climits>
#include <filesystem>
#include <numeric>

#include "engine.h"
#include "progress.h"

#ifdef __APPLE__
#include <sys/clonefile.h>
#include <sys/sysctl.h>
#endif

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

// ---------------------------------------------------------------- shared setup

int default_jobs() {
  if (g_opt.jobs > 0) return (int)std::min<i64>(g_opt.jobs, MAX_WORKERS);
  int n = (int)std::thread::hardware_concurrency();
#ifdef __APPLE__
  // Prefer the performance cores: efficiency cores mostly add lock contention in the kernel.
  int p = 0;
  size_t len = sizeof p;
  if (sysctlbyname("hw.perflevel0.logicalcpu", &p, &len, nullptr, 0) == 0 && p > 0) n = p;
#endif
  return std::clamp(n, 1, 16);
}

SourceGuard::SourceGuard(const std::string& dest) {
  if (dest.empty()) return;
  std::error_code ec;
  path = std::filesystem::weakly_canonical(std::filesystem::absolute(dest, ec), ec).string();
  if (ec) die(RERR_FILESELECT, "cannot resolve destination \"%s\": %s", dest.c_str(), ec.message().c_str());
  while (path.size() > 1 && path.back() == '/') path.pop_back();
  struct stat st;
  if (stat(dest.c_str(), &st) == 0 && S_ISDIR(st.st_mode)) dev = st.st_dev, ino = st.st_ino;
}

bool SourceGuard::excludes(const std::string& source) const {
  if (path.empty()) return false;
  struct stat st;
  if (ino && stat(source.c_str(), &st) == 0 && (u64)st.st_dev == dev && (u64)st.st_ino == ino) return true;
  std::error_code ec;
  std::string p = std::filesystem::weakly_canonical(std::filesystem::absolute(source, ec), ec).string();
  return !ec && (p == path || (subtree && p.starts_with(path) && (path == "/" || p[path.size()] == '/')));
}

void SourceGuard::prepare(const std::vector<std::string>& sources) {
  subtree = false;
  for (const auto& source : sources) {
    std::error_code error;
    std::string root = std::filesystem::weakly_canonical(std::filesystem::absolute(source.empty() ? "." : source, error), error).string();
    while (root.size() > 1 && root.back() == '/') root.pop_back();
    if (!error && (path == root || (path.starts_with(root) && (root == "/" || path[root.size()] == '/')))) subtree = true;
  }
}

std::string machine_identity() {
  char host[256]{};
  struct stat st{};
  if (gethostname(host, sizeof host - 1) != 0 || stat("/", &st) != 0) return "";
  return std::string(host) + ":" + std::to_string(st.st_dev) + ":" + std::to_string(st.st_ino);
}

void prune_source(DirList& l, std::string_view rel, u32 parent_dev, Worker& t, std::vector<std::string>* paths,
                  const SourceGuard& guard, std::string_view base) {
  const Options& o = g_opt;
  size_t k = 0;
  std::string r;
  for (size_t i = 0; i < l.e.size(); i++) {
    Entry& e = l.e[i];
    auto full = [&]() -> const std::string& {
      r.assign(rel);
      if (!r.empty()) r.push_back('/');
      r.append(l.name_sv(e));
      return r;
    };
    if (e.type == T_NONE) continue;
    if (e.type == T_DIR && guard.excludes(paths ? (*paths)[i] : path_join(base, l.name_sv(e)))) continue;
    if (e.flags & EF_DANGLING) {
      g_source_io_error.store(true);
      err_line(RERR_PARTIAL, "symlink has no referent: \"%s\"", full().c_str());
      continue;
    }
    if (!o.filters.empty() && o.filters.excluded(full(), e.type == T_DIR)) continue;
    bool skip = false;
    switch (e.type) {
      case T_DIR:
        if (!o.recursive && !o.dirs) {
          if (!o.quiet) t.logf("skipping directory " + full());
          continue;
        }
        if (o.one_fs && parent_dev) {
          // getattrlistbulk may report the underlying mount-point directory's
          // device. Resolve it through the namespace before deciding to descend.
          std::string path = paths ? (*paths)[i] : path_join(base, l.name_sv(e));
          struct stat st;
          int result = o.copy_links ? stat(path.c_str(), &st) : lstat(path.c_str(), &st);
          if (result != 0 || !S_ISDIR(st.st_mode)) {
            g_source_io_error.store(true);
            err_line(RERR_PARTIAL, "failed to stat source directory \"%s\": %s", path.c_str(), errstr(result ? errno : ENOTDIR).c_str());
            continue;
          }
          entry_from_stat(st, e);
          if (e.dev != parent_dev) e.rdev = 1;
        }
        break;
      case T_LNK:
        skip = !o.links;
        break;
      case T_FIFO:
      case T_SOCK: skip = !o.specials; break;
      case T_CHR:
      case T_BLK: skip = !o.devices; break;
      default: break;
    }
    if (skip) {
      if (!o.quiet) t.logf("skipping non-regular file \"" + full() + "\"");
      continue;
    }
    if (k != i) {
      l.e[k] = e;
      if (paths) (*paths)[k] = std::move((*paths)[i]);
    }
    k++;
  }
  l.e.resize(k);
  if (paths) paths->resize(k);
}

void build_root(const std::vector<std::string>& srcs, RootList& r, Worker& t, const SourceGuard& guard) {
  const Options& o = g_opt;
  unsigned lflags = o.copy_links ? LD_FOLLOW : o.links ? LD_LINKS : 0;
  DirList merged;
  std::vector<std::string> paths;
  bool any_slash = false;
  for (const std::string& arg : srcs) {
    bool slash = arg.empty() || arg.back() == '/' || arg == "." || (arg.size() >= 2 && arg.compare(arg.size() - 2, 2, "/.") == 0);
    struct stat st;
    const char* a = arg.empty() ? "." : arg.c_str();
    if ((slash || o.copy_links ? stat(a, &st) : lstat(a, &st)) != 0) {
      g_source_io_error.store(true);
      err_line(RERR_PARTIAL, "link_stat \"%s\" failed: %s", a, errstr(errno).c_str());
      continue;
    }
    Entry e;
    entry_from_stat(st, e);
    if (e.type == T_DIR && guard.excludes(a)) {
      err_line(RERR_FILESELECT, "source directory is inside the destination: \"%s\"", a);
      continue;
    }
    if (e.type == T_DIR && slash) {
      any_slash = true;
      if (!o.recursive && !o.dirs) {
        if (!o.quiet) t.logf("skipping directory .");
        continue;
      }
      DirList l;
      int err = list_dir(a, l, lflags);
      if (err) {
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", a, errstr(err).c_str());
        continue;
      }
      if (l.incomplete) {
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "incomplete source listing: \"%s\"", a);
      }
      prune_source(l, "", e.dev, t, nullptr, guard, a);
      for (Entry c : l.e) {
        std::string_view nm = l.name_sv(c);
        paths.push_back(path_join(a, nm));
        const char* target = c.type == T_LNK ? l.link(c) : nullptr;
        c.name_off = merged.add_str(nm);
        if (target) c.link_off = merged.add_str(target);
        merged.e.push_back(c);
      }
      if (!r.has_attrs) r.attrs = e, r.has_attrs = true;
    } else {
      std::string trimmed = arg;
      while (trimmed.size() > 1 && trimmed.back() == '/') trimmed.pop_back();
      size_t sl = trimmed.rfind('/');
      std::string nm = sl == std::string::npos ? trimmed : trimmed.substr(sl + 1);
      if (nm.empty() || nm == "..") {
        err_line(RERR_PARTIAL, "cannot use \"%s\" as a source without a trailing slash", a);
        continue;
      }
      DirList one;
      e.name_off = one.add_str(nm);
      e.name_len = (u16)nm.size();
      if (e.type == T_LNK && o.links) {
        char buf[PATH_MAX];
        ssize_t n = readlink(a, buf, sizeof buf - 1);
        e.link_off = one.add_str({buf, n > 0 ? (size_t)n : 0});
      }
      one.e.push_back(e);
      prune_source(one, "", 0, t);
      if (one.e.empty()) continue;
      Entry c = one.e[0];
      c.rdev = (c.type == T_CHR || c.type == T_BLK) ? c.rdev : 0;
      const char* target = c.type == T_LNK ? one.link(c) : nullptr;
      c.name_off = merged.add_str(nm);
      if (target) c.link_off = merged.add_str(target);
      merged.e.push_back(c);
      paths.push_back(trimmed);
    }
  }
  r.single = srcs.size() == 1 && !any_slash && merged.e.size() == 1 && merged.e[0].type != T_DIR;
  // Sort by name (stable: first argument wins on duplicates) and drop duplicates.
  std::vector<u32> ord(merged.e.size());
  std::iota(ord.begin(), ord.end(), 0u);
  std::stable_sort(ord.begin(), ord.end(), [&](u32 x, u32 y) { return name_cmp(merged.name_sv(merged.e[x]), merged.name_sv(merged.e[y])) < 0; });
  r.list.names = std::move(merged.names);
  for (u32 x : ord) {
    // Same name from two arguments: directories are merged, otherwise the first one wins.
    if (!r.list.e.empty() && r.list.name_sv(r.list.e.back()) == r.list.name_sv(merged.e[x]) &&
        !(r.list.e.back().type == T_DIR && merged.e[x].type == T_DIR))
      continue;
    r.list.e.push_back(merged.e[x]);
    r.src_paths.push_back(std::move(paths[x]));
  }
}

static bool mkdir_p(const std::string& path, mode_t mode) {
  if (destination_mkdir(path.c_str(), mode) == 0 || errno == EEXIST) return true;
  if (errno != ENOENT || !g_opt.mkpath) return false;
  size_t sl = path.find_last_not_of('/');
  sl = path.rfind('/', sl);
  if (sl == std::string::npos || sl == 0) return false;
  if (!mkdir_p(path.substr(0, sl), mode)) return false;
  return destination_mkdir(path.c_str(), mode) == 0 || errno == EEXIST;
}

bool setup_dest(const std::string& dest_arg, DirWork& root, bool single) {
  const Options& o = g_opt;
  std::string dest = dest_arg.empty() ? "." : dest_arg;
  bool dest_slash = dest.back() == '/';
  while (dest.size() > 1 && dest.back() == '/') dest.pop_back();
  if (root.src.e.empty() && !root.has_attrs) return false;
  if (!anchor_destination(dest)) die(RERR_FILESELECT, "cannot open destination anchor: %s", errstr(errno).c_str());
  struct stat st;
  bool exists = destination_stat(dest.c_str(), &st) == 0;
  bool is_dir = exists && S_ISDIR(st.st_mode);
  if (single && !dest_slash && !is_dir) {
    size_t sl = dest.rfind('/');
    root.dst_path = sl == std::string::npos ? "." : sl == 0 ? "/" : dest.substr(0, sl);
    root.rename_to = sl == std::string::npos ? dest : dest.substr(sl + 1);
    root.has_attrs = false;
    root.no_delete = true;
    return true;
  }
  if (exists && !is_dir) die(RERR_FILESELECT, "ERROR: destination must be a directory when copying more than 1 file");
  if (!exists) {
    if (!o.dry_run && !mkdir_p(dest, 0777 & ~g_umask)) die(RERR_FILEIO, "mkdir \"%s\" failed: %s", dest.c_str(), errstr(errno).c_str());
    if (o.verbose > 0) out_line("created directory " + dest);
    root.created = true;
    exists = !o.dry_run && destination_stat(dest.c_str(), &st) == 0;
  }
  root.dst_path = dest;
  if (root.has_attrs) {
    Entry d;
    if (exists) entry_from_stat(st, d);
    u32 final_mode = o.perms ? root.attrs.mode : root.created ? (root.attrs.mode & 0777 & ~g_umask) : d.mode;
    root.attrs.mode = final_mode;
    root.mode_ok = exists && d.mode == final_mode;
    if (exists && !o.am_root && (d.mode & 0300) != 0300 && !o.dry_run && check_attr(destination_chmod(dest.c_str(), d.mode | 0700), dest.c_str(), "permissions")) root.mode_ok = false;
    if (exists && !o.dry_run) {
      bool changed_owner = false;
      if (o.group && d.gid != root.attrs.gid && can_set_gid(root.attrs.gid)) {
        check_attr(destination_chown(dest.c_str(), (uid_t)-1, root.attrs.gid), dest.c_str(), "ownership");
        changed_owner = true;
      }
      if (o.owner && o.am_root && d.uid != root.attrs.uid) {
        check_attr(destination_chown(dest.c_str(), root.attrs.uid, (gid_t)-1), dest.c_str(), "ownership");
        changed_owner = true;
      }
      if (changed_owner && (final_mode & 06000)) root.mode_ok = false;
    }
    root.time_ok = exists && d.mtime == root.attrs.mtime;
  }
  return true;
}

void wait_pool(Pool& pool) {
  while (!pool.wait_done(66)) {
    progress_tick();
    if (g_stop.load()) {
      // Give workers a moment to finish or roll back the file they are on.
      pool.wait_done(300);
      pool.abort();
      break;
    }
  }
}

// ---------------------------------------------------------------- local engine

namespace {

enum { K_SCAN = 1, K_COPY = 2 };

std::atomic<bool> clone_ok{true};

struct Local {
  Pool pool;
  SourceGuard guard;
  std::atomic<int> scans{0};

  void push_scan(DirWork* d, bool prelisted) {
    scans.fetch_add(1);
    Task t;
    t.kind = K_SCAN;
    t.ptr = d;
    t.a = prelisted;
    pool.push(0, std::move(t));
  }

  bool lazy_ok = false;  // new directories may be created by their own scan step

  void release(DirWork* d) {
    if (d->pending.fetch_sub(1) != 1) return;
    if (!g_stop.load()) finish_dir(*d);
    delete d;
  }

#ifdef __APPLE__
  // A new directory holding only files and symlinks is cloned with a single call: one
  // metadata transaction instead of one per file.
  bool clone_leaf(DirWork* d, size_t listed, Worker& w) {
    const Options& o = g_opt;
    const DirList& l = d->src;
    if (!clone_ok.load(std::memory_order_relaxed) || l.e.size() != listed || l.e.empty() || l.e.size() > 4096 || l.incomplete) return false;
    if ((d->attrs.mode & 07000) || (d->attrs.mode & 0700) != 0700) return false;
    u32 gid = d->waiter ? d->waiter->dgid : d->attrs.gid;
    if (o.group && d->attrs.gid != gid) return false;
    for (const Entry& e : l.e) {
      if (e.type != T_REG && e.type != T_LNK) return false;
      if ((e.mode & 07000) || (o.group && e.gid != gid)) return false;
    }
    if (destination_clone(d->src_path.c_str(), d->dst_path.c_str(), CLONE_NOFOLLOW | (o.owner && o.am_root ? 0 : CLONE_NOOWNERCOPY)) != 0) {
      if (errno == ENOSPC || errno == EDQUOT) file_io_error(errno, d->dst_path.c_str(), "clonefile");
      if (errno == EXDEV || errno == ENOTSUP) clone_ok.store(false, std::memory_order_relaxed);
      return false;
    }
    u64 nf = 0, nl = 0, nb = 0;
    bool names = o.itemize || o.verbose > 0;
    std::string line;
    for (const Entry& e : l.e) {
      if (e.type == T_REG) nf++, nb += (u64)e.size;
      else nl++;
      if (!names) continue;
      line = o.itemize ? (e.type == T_REG ? ">f+++++++++ " : "cL+++++++++ ") : "";
      line.append(d->rel).push_back('/');
      line.append(l.name_sv(e));
      if (e.type == T_LNK) line.append(" -> ").append(l.link(e));
      w.logf(line);
    }
    g_stats.files_seen.fetch_add(nf, std::memory_order_relaxed);
    g_stats.links_seen.fetch_add(nl, std::memory_order_relaxed);
    g_stats.bytes_seen.fetch_add(nb, std::memory_order_relaxed);
    g_stats.xfer_files_total.fetch_add(nf, std::memory_order_relaxed);
    g_stats.xfer_bytes_total.fetch_add(nb, std::memory_order_relaxed);
    g_stats.xfer_files.fetch_add(nf, std::memory_order_relaxed);
    g_stats.xfer_bytes.fetch_add(nb, std::memory_order_relaxed);
    g_stats.created_files.fetch_add(nf, std::memory_order_relaxed);
    g_stats.created_links.fetch_add(nl, std::memory_order_relaxed);
    return true;
  }
#else
  bool clone_leaf(DirWork*, size_t, Worker&) { return false; }
#endif

  void scan(DirWork* d, bool prelisted, Worker& w) {
    const Options& o = g_opt;
    int list_err = 0;
    size_t listed = 0;
    if (!prelisted) {
      list_err = list_dir(d->src_path.c_str(), d->src, o.copy_links ? LD_FOLLOW : o.links ? LD_LINKS : 0);
      if (list_err || d->src.incomplete) g_source_io_error.store(true);
      if (d->src.incomplete && !list_err) err_line(RERR_PARTIAL, "incomplete source listing: \"%s\"", d->src_path.c_str());
      if (list_err) err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", d->src_path.c_str(), errstr(list_err).c_str());
      if (d->src.incomplete) d->no_delete = true;
      listed = d->src.e.size();
      prune_source(d->src, d->rel, d->attrs.dev, w, nullptr, guard, d->src_path);
    }
    if (d->lazy) {
      skip_unsafe_links(*d, w);
      reject_name_collisions(*d);
      // Our directory does not exist yet: clone it whole if we can, else create it.
      bool cloned = !list_err && clone_leaf(d, listed, w);
      bool made = cloned;
      if (!cloned) {
        made = destination_mkdir(d->dst_path.c_str(), d->attrs.mode | 0700) == 0;
        if (!made && errno == EEXIST) made = true, d->created = false;
        if (!made) file_io_error(errno, d->dst_path.c_str(), "recv_generator: mkdir");
      }
      release(d->waiter);
      if (cloned) {
        d->mode_ok = true;
        finish_dir(*d);
      }
      if (cloned || !made) {
        delete d;
        return;
      }
    }
    if (list_err) {
      finish_dir(*d);
      delete d;
      return;
    }
    d->pending.store(1);
    d->lazy_children = lazy_ok;
    generate(*d, w);
    if (o.recursive) {
      for (size_t i = 0; i < d->src.e.size(); i++) {
        const Entry& s = d->src.e[i];
        if (s.type != T_DIR || !(s.flags & EF_DESCEND)) continue;
        DirWork* c = new DirWork;
        std::string_view nm = d->src.name_sv(s);
        if (d->src_paths.empty()) c->src_path = path_join(d->src_path, nm);
        else c->src_path = d->src_paths[i];
        c->dst_path = path_join(d->dst_path, nm);
        c->rel = rel_join(d->rel, nm);
        c->attrs = s;
        c->has_attrs = true;
        c->created = s.flags & EF_CREATED;
        c->mode_ok = s.flags & EF_MODE_OK;
        c->time_ok = s.flags & EF_TIME_OK;
        // The same name coming from two source arguments is merged, so neither may delete.
        if (!d->src_paths.empty() && ((i > 0 && d->src.name_sv(d->src.e[i - 1]) == nm) || (i + 1 < d->src.e.size() && d->src.name_sv(d->src.e[i + 1]) == nm)))
          c->no_delete = true;
        if (s.flags & EF_LAZY) {
          c->lazy = true;
          c->waiter = d;
          d->pending.fetch_add(1);
        }
        push_scan(c, false);
      }
    }
    size_t n = d->need.size();
    if (n == 0) return release(d);
    // Split into batches so large directories and large files spread over the workers.
    std::vector<std::pair<u32, u32>> batches;
    u32 start = 0;
    i64 bytes = 0;
    for (u32 i = 0; i < n; i++) {
      bytes += d->src.e[d->need[i]].size;
      if (i + 1 - start >= 64 || bytes >= (8 << 20)) {
        batches.emplace_back(start, i + 1);
        start = i + 1, bytes = 0;
      }
    }
    if (start < n) batches.emplace_back(start, (u32)n);
    d->pending.fetch_add((int)batches.size());
    for (auto [a, b] : batches) {
      Task t;
      t.kind = K_COPY;
      t.ptr = d;
      t.a = a, t.b = b;
      pool.push(1, std::move(t));
    }
    release(d);
  }

  void copy_one(DirWork& d, u32 idx, Worker& w) {
    const Options& o = g_opt;
    Entry& s = d.src.e[idx];
    if (g_stop.load(std::memory_order_relaxed)) return;
    if (o.dry_run) {
      g_stats.xfer_bytes.fetch_add((u64)s.size, std::memory_order_relaxed);
      note_transferred(d, idx, s.size, w);
      return;
    }
    src_path_of(d, idx, w.p2);
    slot_begin(w.id, d.rel, d.src.name_sv(s), s.size);
    auto fail = [&](i64 done) {
      g_stats.xfer_files_total.fetch_sub(1, std::memory_order_relaxed);
      g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - done), std::memory_order_relaxed);
      slot_end(w.id);
    };

#ifdef __APPLE__
    // A clone carries data, mode and mtime in one metadata operation. Not for set-id files:
    // the kernel strips those bits when ownership is not copied.
    if (o.clone && o.perms && o.times && !o.inplace && !(s.mode & 07000) && clone_ok.load(std::memory_order_relaxed)) {
      u32 fl = (o.copy_links ? 0 : CLONE_NOFOLLOW) | (o.owner && o.am_root ? 0 : CLONE_NOOWNERCOPY);
      if (clone_copy(d, idx, w.p2.c_str(), fl, w)) {
        g_stats.xfer_bytes.fetch_add((u64)s.size, std::memory_order_relaxed);
        note_transferred(d, idx, s.size, w);
        slot_end(w.id);
        return;
      }
      if (errno == EXDEV || errno == ENOTSUP) clone_ok.store(false, std::memory_order_relaxed);
    }
#endif

    static thread_local OutFile f;
    for (int attempt = 0; attempt < 2; attempt++) {
      int in = open(w.p2.c_str(), O_RDONLY | O_CLOEXEC | (o.copy_links || !d.src_paths.empty() ? 0 : O_NOFOLLOW));
      struct stat before;
      if (in < 0 || fstat(in, &before) != 0 || !S_ISREG(before.st_mode)) {
        int error = in < 0 ? errno : EIO;
        if (in >= 0) close(in);
        g_source_io_error.store(true);
        if (error == ENOENT) err_line(RERR_VANISHED, "file has vanished: \"%s\"", w.p2.c_str());
        else err_line(RERR_PARTIAL, "send_files failed to open \"%s\": %s", w.p2.c_str(), errstr(error).c_str());
        return fail(0);
      }
      Entry fresh = source_snapshot(s, before);
      if (fresh.size >= s.size) g_stats.xfer_bytes_total.fetch_add((u64)(fresh.size - s.size));
      else g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - fresh.size));
      s = fresh;
      slot_begin(w.id, d.rel, d.src.name_sv(s), s.size);
      ResumePrefix prefix;
      if (o.partial && !o.whole_file && attempt == 0 && s.size > (512 << 10)) {
        prefix = destination_resume_prefix(path_join(d.dst_path, d.dst_name(idx)).c_str(), s.size);
        u64 digest[2];
        if (prefix.size && (!hash_prefix_fd(in, prefix.size, digest) || digest[0] != prefix.sum[0] || digest[1] != prefix.sum[1])) prefix = {};
      }
      if (!out_open(f, d, idx, w)) { close(in); return fail(0); }
      i64 total = 0;
      bool ok = true;
      if (prefix.size) {
        if (!out_restore_prefix(f, prefix) || lseek(in, prefix.size, SEEK_SET) < 0) {
          int error = errno;
          out_abort(f);
          close(in);
          file_io_error(error, f.path.c_str(), "reuse partial prefix");
          return fail(0);
        }
        total = prefix.size;
        g_stats.xfer_bytes.fetch_add((u64)total);
        slot_add(w.id, total);
      }
      while (total < s.size) {
        size_t want = (size_t)std::min<i64>((i64)w.buf.size(), s.size - total);
        ssize_t n = read(in, w.buf.data(), want);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) {
          g_source_io_error.store(true);
          err_line(RERR_PARTIAL, "read errors mapping \"%s\": %s", w.p2.c_str(), errstr(errno).c_str());
          ok = false;
        }
        if (n <= 0) break;
        if (!out_write(f, w.buf.data(), (size_t)n, total)) {
          file_io_error(errno, f.path.c_str(), "write");
          ok = false;
          break;
        }
        total += n;
        g_stats.xfer_bytes.fetch_add((u64)n);
        slot_add(w.id, n);
        if (g_stop.load()) { ok = false; break; }
      }
      bool stable = total == s.size && source_unchanged(in, w.p2, before);
      close(in);
      f.size = total;
      if (ok && !stable && attempt == 0) {
        out_abort(f);
        g_stats.xfer_bytes.fetch_sub((u64)total);
        continue;
      }
      if (ok && !stable) {
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "file changed during transfer after retry: \"%s\"", w.p2.c_str());
        ok = false;
      }
      ok = out_finish(f, d, idx, w, ok) && ok;
      if (!ok) return fail(total);
      note_transferred(d, idx, total, w);
      slot_end(w.id);
      return;
    }
  }

  void run_task(Task& t, Worker& w) {
    DirWork* d = (DirWork*)t.ptr;
    if (t.kind == K_SCAN) {
      scan(d, t.a != 0, w);
      if (scans.fetch_sub(1) == 1) g_stats.scan_done.store(true);
      return;
    }
    for (u32 i = t.a; i < t.b; i++) copy_one(*d, d->need[i], w);
    release(d);
  }
};

}  // namespace

int run_local(const std::vector<std::string>& srcs, const std::string& dest) {
  Local L;
  L.guard = SourceGuard(dest.empty() ? "." : dest);
  L.guard.prepare(srcs);
  Worker w0;
  RootList rl;
  build_root(srcs, rl, w0, L.guard);
  DirWork* root = new DirWork;
  root->src = std::move(rl.list);
  root->src_paths = std::move(rl.src_paths);
  root->attrs = rl.attrs;
  root->has_attrs = rl.has_attrs;
  root->no_delete = !rl.has_attrs;  // only the contents of "SRC/" own the destination directory
  if (g_opt.verbose > 0) w0.logf("sending incremental file list");
  w0.flush_log();
  if (!setup_dest(dest, *root, rl.single)) {
    delete root;
    return g_exit_code.load();
  }
#ifdef __APPLE__
  const Options& o = g_opt;
  // Whole-directory clones are only equivalent to a per-file sync when nothing could make us
  // treat any entry specially.
  L.lazy_ok = o.clone && o.recursive && o.links && !o.copy_links && o.perms && o.times && !o.omit_dir_times && !o.omit_link_times &&
              !o.dry_run && !o.inplace && !o.one_fs && !o.existing && o.max_size <= 0 && o.min_size <= 0 && o.filters.empty();
#endif
  int n = default_jobs();
  progress_start(n);
  // Scanning has priority so that totals are known before the bulk of the copying starts; the
  // backlog limit bounds memory on huge trees.
  L.pool.q1_soft_limit = 200000;
  L.pool.lifo0 = true;
  L.pool.idle_check = [] {
    g_stats.scan_done.store(true);
    return true;
  };
  L.push_scan(root, true);
  L.pool.start(n, [&L](Task& t, Worker& w) { L.run_task(t, w); });
  wait_pool(L.pool);
  if (g_stop.load()) exit_signal();
  L.pool.join();
  finalize_tree();
  return g_exit_code.load();
}
