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
#include "output.h"
#include "delta.h"
#include "rate_limit.h"
#include "link_dest.h"
#include "app_partials.h"

#ifdef __APPLE__
#include <sys/clonefile.h>
#include <sys/mount.h>
#include <sys/sysctl.h>
#endif

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

// ---------------------------------------------------------------- shared setup

int default_jobs(const std::string& destination) {
  if (g_opt.jobs > 0) return (int)std::min<i64>(g_opt.jobs, MAX_WORKERS);
  int n = (int)std::thread::hardware_concurrency();
#ifdef __APPLE__
  // Prefer the performance cores: efficiency cores mostly add lock contention in the kernel.
  int p = 0;
  size_t len = sizeof p;
  if (sysctlbyname("hw.perflevel0.logicalcpu", &p, &len, nullptr, 0) == 0 && p > 0) n = p;
  if (!destination.empty()) {
    // A missing destination inherits its nearest existing ancestor's filesystem.
    // Four APFS workers match eight on measured byte creation with lower CPU.
    std::filesystem::path probe(destination);
    struct statfs fs;
    for (;;) {
      if (statfs(probe.c_str(), &fs) == 0) {
        if (std::string_view(fs.f_fstypename) == "apfs") n = std::min(n, 4);
        break;
      }
      if (errno != ENOENT && errno != ENOTDIR) break;
      auto parent = probe.parent_path();
      if (parent.empty()) parent = ".";
      if (parent == probe) break;
      probe = std::move(parent);
    }
  }
#endif
  return std::clamp(n, 1, 16);
}

int receiver_jobs(const std::string& destination) {
  int n = default_jobs(destination);
  // On many-core receivers, four automatic workers beat sixteen on small-file
  // no-ops and fresh copies, and match them on byte-bound trees (T1e).
  return g_opt.jobs > 0 ? n : std::min(n, 4);
}

SourceGuard::SourceGuard(const std::string& dest) {
  if (dest.empty()) return;
  std::error_code ec;
  path = std::filesystem::weakly_canonical(std::filesystem::absolute(dest, ec), ec).string();
  if (ec) {
    if (g_fs_error_sink) g_fs_error_sink(ec.value(), dest, "resolve_destination");
    die(RERR_FILESELECT, "cannot resolve destination \"%s\": %s", dest.c_str(), ec.message().c_str());
  }
  while (path.size() > 1 && path.back() == '/') path.pop_back();
  struct stat st;
  if (stat(dest.c_str(), &st) == 0 && S_ISDIR(st.st_mode)) dev = st.st_dev, ino = st.st_ino;
}

bool SourceGuard::excludes(const std::string& source) const {
  if (path.empty()) return false;
  struct stat st;
  if (ino && stat(source.c_str(), &st) == 0 && (u64)st.st_dev == dev && (u64)st.st_ino == ino) return true;
  // Without -L the walk descends real directories, so a directory under a source resolves under it,
  // and when no source contains the destination only the same inode can be it, checked above.
  // Resolving every directory's path cost one failing readlinkat per component (musl's realpath):
  // millions on a tree with as many directories as files.
  if (!subtree && !g_opt.copy_links && !g_opt.files_from_set) return false;
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

std::shared_ptr<const FilterList> directory_filters(const std::shared_ptr<const FilterList>& parent,
                                                   std::string_view path, bool receiver) {
  const FilterList& filters = parent ? *parent : g_opt.filters;
  if (!filters.has_merges()) return parent;
  std::string error;
  auto context = std::make_shared<const FilterList>(filters.in_directory(path, receiver, &error));
  if (!error.empty()) die(error.starts_with("failed to ") ? RERR_FILEIO : RERR_SYNTAX, "%s", error.c_str());
  return context;
}

void EmptyDirectoryPruner::add(const Entry& entry, std::string path, std::string_view absolute) {
  if (entry.type == T_NONE) return;
  if (entry.type == T_DIR) {
    if (!g_opt.filters.protected_from_deletion(path, true, g_opt.delete_excluded, false, absolute)) return;
    retained.insert(path);
  }
  for (;;) {
    size_t slash = path.rfind('/');
    if (slash == path.npos) break;
    path.resize(slash);
    if (!retained.insert(path).second) break;
  }
}

void prune_empty_directories(const std::vector<DirWork*>& directories, std::string_view destination) {
  EmptyDirectoryPruner pruner;
  for (const auto* directory : directories) {
    for (const auto& entry : directory->src.e) {
      std::string rel = rel_join(directory->rel, directory->src.name_sv(entry));
      std::string absolute = g_opt.filters.has_absolute() ? FilterList::absolute_path(path_join(destination, rel)) : "";
      pruner.add(entry, std::move(rel), absolute);
    }
  }
  for (auto* directory : directories)
    for (auto& entry : directory->src.e)
      if (entry.type == T_DIR && !pruner.keep(rel_join(directory->rel, directory->src.name_sv(entry))))
        entry.item_flags |= IF_PRUNED;
}

void prune_source(DirList& l, std::string_view rel, u32 parent_dev, Worker& t, std::vector<std::string>* paths,
                  const SourceGuard& guard, std::string_view base, const FilterList* context) {
  const Options& o = g_opt;
  const FilterList& filters = context ? *context : o.filters;
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
    if (!filters.empty()) {
      std::string absolute;
      if (filters.has_absolute()) absolute = FilterList::absolute_path(paths ? (*paths)[i] : path_join(base, l.name_sv(e)));
      if (filters.excluded(full(), e.type == T_DIR, absolute)) continue;
    }
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
    if (skip && !o.list_only) {
      auto item = transfer_item(full(), paths ? (*paths)[i] : path_join(base, l.name_sv(e)), {}, e);
      item_finish(item, "skipped", "unsupported_type");
      if (!o.quiet) t.logf("skipping non-regular file \"" + full() + "\"");
      if (!o.del) continue;
      // rsync retains skipped source names in its deletion comparison. Keep a
      // placeholder without transferring metadata or following a symlink.
      e.type = T_NONE;
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
  if (o.files_from_set && !o.files_from_loaded) load_local_file_list();
  if (o.relative || o.files_from_set) return build_selected_root(srcs, r, t, guard);
  unsigned lflags = o.copy_links ? LD_FOLLOW : o.links || o.list_only ? LD_LINKS : 0;
  DirList merged;
  std::vector<std::string> paths;
  std::vector<std::shared_ptr<const FilterList>> contexts;
  bool any_slash = false;
  for (const std::string& arg : srcs) {
    bool slash = arg.empty() || arg.back() == '/' || arg == "." || (arg.size() >= 2 && arg.compare(arg.size() - 2, 2, "/.") == 0);
    struct stat st;
    const char* a = arg.empty() ? "." : arg.c_str();
    if ((slash || o.copy_links ? stat(a, &st) : lstat(a, &st)) != 0) {
      int error = errno;
      std::string selected = arg;
      while (selected.size() > 1 && selected.back() == '/') selected.pop_back();
      auto item = transfer_item(slash ? "" : app_selection_name(selected, selected.substr(selected.rfind('/') + 1)), a, {}, Entry{});
      ItemScope scope(item);
      source_error(error, a, "stat_source");
      g_source_io_error.store(true);
      err_line(RERR_PARTIAL, "link_stat \"%s\" failed: %s", a, errstr(error).c_str());
      item_finish(item, "failure", "source_error");
      continue;
    }
    Entry e;
    entry_from_stat(st, e);
    if (g_app_preview_source_check) {
      std::string selected=arg; while (selected.size()>1 && selected.back()=='/') selected.pop_back();
      auto relative=slash ? std::string() : app_selection_name(selected,selected.substr(selected.rfind('/')+1));
      auto observed=transfer_item(relative,a,{},e,false);
      auto revision=DestinationRevision::from(st);
      if (!item_preview_source_valid(observed,&revision)) {
        r.app_scan_failed=true;
        auto failed=transfer_item(relative,a,{},e);
        failed->failed.store(true); failed->source_failed.store(true); failed->preview_stale.store(true);
        item_finish(failed,"failure","stale_preview");
        continue;
      }
    }
    if (e.type == T_DIR && guard.excludes(a)) {
      std::string selected = arg;
      while (selected.size() > 1 && selected.back() == '/') selected.pop_back();
      auto item = transfer_item(slash ? "" : app_selection_name(selected, selected.substr(selected.rfind('/') + 1)), a, {}, e);
      ItemScope scope(item);
      if (g_fs_error_sink) g_fs_error_sink(0, a, "source_destination_overlap");
      err_line(RERR_FILESELECT, "source directory is inside the destination: \"%s\"", a);
      item_finish(item, "failure", "source_destination_overlap");
      continue;
    }
    if (e.type == T_DIR && slash) {
      ItemScope source_directory(transfer_item("", a, {}, e, false));
      if (g_item_sink && !r.has_attrs) r.attrs = e, r.has_attrs = true, r.attr_source = path_join(a, ".");
      any_slash = true;
      if (!o.recursive && !o.dirs) {
        if (!o.quiet) t.logf("skipping directory .");
        continue;
      }
      DirList l;
      int err = list_dir(a, l, lflags);
      if (err) {
        r.app_scan_failed = true;
        source_error(err, a, "scan_source");
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", a, errstr(err).c_str());
        continue;
      }
      if (l.incomplete) {
        r.app_scan_failed = true;
        source_error(0, a, "scan_source");
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "incomplete source listing: \"%s\"", a);
      }
      auto context = directory_filters({}, a, false);
      if (!item_preview_source_valid(current_item())) { r.app_scan_failed=true; l.clear(); }
      prune_source(l, "", e.dev, t, nullptr, guard, a, context.get());
      for (Entry c : l.e) {
        std::string_view nm = l.name_sv(c);
        paths.push_back(path_join(a, nm));
        if (o.filters.has_merges()) contexts.push_back(context);
        const char* target = c.type == T_LNK ? l.link(c) : nullptr;
        c.name_off = merged.add_str(nm);
        if (target) c.link_off = merged.add_str(target);
        merged.e.push_back(c);
      }
      if (!r.has_attrs) r.attrs = e, r.has_attrs = true, r.attr_source = path_join(a, ".");
    } else {
      std::string trimmed = arg;
      while (trimmed.size() > 1 && trimmed.back() == '/') trimmed.pop_back();
      size_t sl = trimmed.rfind('/');
      std::string nm = sl == std::string::npos ? trimmed : trimmed.substr(sl + 1);
      if (nm.empty() || nm == "..") {
        err_line(RERR_PARTIAL, "cannot use \"%s\" as a source without a trailing slash", a);
        continue;
      }
      nm = app_selection_name(trimmed, nm);
      DirList one;
      e.name_off = one.add_str(nm);
      e.name_len = (u16)nm.size();
      if (e.type == T_LNK && (o.links || o.list_only)) {
        char buf[PATH_MAX];
        ssize_t n = readlink(a, buf, sizeof buf - 1);
        if (n < 0) {
          int error = errno;
          auto item = transfer_item(nm, a, {}, e);
          ItemScope scope(item);
          source_error(error, a, "readlink_source");
          err_line(RERR_PARTIAL, "readlink \"%s\" failed: %s", a, errstr(error).c_str());
          item_finish(item, "failure", "source_error");
          continue;
        }
        e.link_off = one.add_str({buf, n > 0 ? (size_t)n : 0});
      }
      one.e.push_back(e);
      std::string parent = sl == std::string::npos ? "." : sl ? trimmed.substr(0, sl) : "/";
      std::shared_ptr<const FilterList> context;
      std::vector<std::string> exact_paths;
      if (g_item_sink) exact_paths.push_back(trimmed);
      prune_source(one, "", 0, t, g_item_sink ? &exact_paths : nullptr, guard, parent, context.get());
      if (one.e.empty()) continue;
      Entry c = one.e[0];
      c.rdev = (c.type == T_CHR || c.type == T_BLK) ? c.rdev : 0;
      const char* target = c.type == T_LNK ? one.link(c) : nullptr;
      c.name_off = merged.add_str(nm);
      if (target) c.link_off = merged.add_str(target);
      merged.e.push_back(c);
      paths.push_back(trimmed);
      if (o.filters.has_merges()) contexts.push_back(context);
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
    if (!contexts.empty()) r.source_contexts.push_back(std::move(contexts[x]));
  }
  r.no_delete = !r.has_attrs;
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
  if (!root.has_attrs && std::none_of(root.src.e.begin(), root.src.e.end(),
                                    [](const Entry& e) { return !(e.item_flags & IF_PRUNED); })) return false;
  auto reject_root = [&](std::string_view reason) {
    root.dst_path = dest;
    prepare_items(root);
    if (root.app_directory) {
      root.app_directory->applied.store(false);
      item_finish(root.app_directory, "failure", reason);
    }
    for (auto& item : root.app_items) item_finish(item, "failure", reason);
    return false;
  };
  // App roots are existing objects, never implicit mkdir targets.
  if (g_app_destination_check && !g_app_destination_check()) return reject_root("destination_changed");
  if (!anchor_destination(dest)) {
    if (g_fs_error_sink) g_fs_error_sink(errno, dest, "anchor_destination");
    die(RERR_FILESELECT, "cannot open destination anchor: %s", errstr(errno).c_str());
  }
  struct stat st;
  bool exists = destination_stat(dest.c_str(), &st) == 0;
  int stat_error = exists ? 0 : errno;
  if (!exists && g_app_destination_check) {
    if (!g_app_destination_check()) return reject_root("destination_changed");
    if (g_fs_error_sink) g_fs_error_sink(stat_error, dest, "stat_destination_root");
    err_line(RERR_PARTIAL, "cannot stat destination root during setup: %s", errstr(stat_error).c_str());
    return reject_root("destination_unavailable");
  }
  bool is_dir = exists && S_ISDIR(st.st_mode);
  if (single && !dest_slash && !is_dir) {
    size_t sl = dest.rfind('/');
    root.dst_path = sl == std::string::npos ? "." : sl == 0 ? "/" : dest.substr(0, sl);
    root.rename_to = sl == std::string::npos ? dest : dest.substr(sl + 1);
    root.has_attrs = false;
    root.no_delete = true;
    init_link_dest(root.dst_path);
    return true;
  }
  if (exists && !is_dir) {
    if (g_fs_error_sink) g_fs_error_sink(ENOTDIR, dest, "destination_preflight");
    die(RERR_FILESELECT, "ERROR: destination must be a directory when copying more than 1 file");
  }
  if (!exists) {
    if (!o.dry_run && !mkdir_p(dest, 0777 & ~g_umask)) {
      if (g_fs_error_sink) g_fs_error_sink(errno, dest, "mkdir_destination");
      die(RERR_FILEIO, "mkdir \"%s\" failed: %s", dest.c_str(), errstr(errno).c_str());
    }
    if (o.verbose > 0 || (!o.link_dest.empty() && output_enabled())) out_line("created directory " + dest);
    root.created = true;
    exists = !o.dry_run && destination_stat(dest.c_str(), &st) == 0;
  }
  root.dst_path = dest;
  init_link_dest(root.dst_path);
  if (root.has_attrs) {
    if (g_app_preview_destination_check) {
      prepare_items(root);
      if (!item_preview_source_valid(root.app_directory) || !item_destination_valid(root.app_directory,true)) return reject_root("stale_preview");
    }
    if (app_partials::active()) {
      prepare_items(root);
      if (!app_partials::prepare_entry(root.app_directory)) return false;
    }
    root.attrs.mode = incoming_mode(root.attrs.mode, root.attrs.type);
    incoming_ownership(root.attrs);
    Entry d;
    if (exists) entry_from_stat(st, d);
    else if (root.created && o.mkpath) {
      d.type = T_DIR;
      d.mode = 0777 & ~g_umask;
      d.uid = geteuid(), d.gid = getegid();
      d.mtime = (i64)time(nullptr);
    }
    auto xattr_filters = o.xattrs ? directory_filters(root.receiver_filter, dest, true) : root.receiver_filter;
    const FilterList& metadata_filters = xattr_filters ? *xattr_filters : o.filters;
    if (o.xattrs && exists && !root.created && xattrs_differ(root.attrs_xattrs, dest, T_DIR, metadata_filters)) root.attrs.item_flags |= IF_XATTR;
    if (o.acls && exists && !root.created && acls_differ(root.attrs_xattrs.acl(), dest, T_DIR, &root.attrs.access_acl_differ)) root.attrs.item_flags |= IF_ACL;
    Worker worker;
    auto alternate = root.created && !o.mkpath ? link_dest_directory("", root.attrs, root.attrs_xattrs, metadata_filters) : std::nullopt;
    note_directory(root, alternate ? &*alternate : (exists && !root.created) || (root.created && o.mkpath) ? &d : nullptr,
                   root.created && !o.mkpath && !alternate, worker, (bool)alternate);
    worker.flush_log();
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
    if (o.acls && exists) apply_acls(root.attrs_xattrs.acl(), dest, T_DIR, final_mode);
    if (o.xattrs && exists && (root.created || (root.attrs.item_flags & IF_XATTR))) apply_xattrs(root.attrs_xattrs, dest, T_DIR, metadata_filters);
    root.time_ok = exists && d.mtime == root.attrs.mtime && !(root.attrs.item_flags & IF_XATTR);
    if (g_app_preview_destination_check) item_expect_destination(root.app_directory);
    if (app_partials::active() && root.app_directory && item_expect_destination(root.app_directory))
      if (!app_partials::own_entry(root.app_directory)) return false;
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
  // Bound one clone transaction by the complete scanned descendant inventory.
  // Oversized, deep, filtered or special-file trees use the ordinary walk.
  bool clone_tree(DirWork* d, size_t listed, Worker& w) {
    const Options& o = g_opt;
    const DirList& l = d->src;
    constexpr size_t max_entries = 4096;
    constexpr unsigned max_depth = 32;
    if (metadata_enabled() || o.hard_links || !clone_ok.load(std::memory_order_relaxed) || l.e.size() != listed || l.e.empty() || l.e.size() > max_entries || l.incomplete) return false;
    std::vector<std::unique_ptr<DirWork>> owned;
    std::vector<DirWork*> directories{d};
    std::vector<unsigned> depths{0};
    size_t entries = l.e.size();
    u64 nf = 0, nl = 0, nb = 0, nd = 0;
    for (size_t i = 0; i < directories.size(); ++i) {
      DirWork& dir = *directories[i];
      if ((dir.attrs.fileflags & SF_DATALESS) || blocking_fileflags(dir.attrs.fileflags) ||
          (dir.attrs.mode & 07000) || (dir.attrs.mode & 0700) != 0700) return false;
      for (const Entry& e : dir.src.e) {
        if (e.type != T_REG && e.type != T_LNK && e.type != T_DIR) return false;
        if ((e.fileflags & SF_DATALESS) || blocking_fileflags(e.fileflags) || (e.mode & 07000)) return false;
        if (e.type == T_REG) nf++, nb += (u64)e.size;
        else if (e.type == T_LNK) nl++;
        else {
          if (depths[i] >= max_depth || (e.mode & 0700) != 0700) return false;
          auto child = std::make_unique<DirWork>();
          child->src_path = path_join(dir.src_path, dir.src.name_sv(e));
          child->dst_path = path_join(dir.dst_path, dir.src.name_sv(e));
          child->rel = rel_join(dir.rel, dir.src.name_sv(e));
          child->attrs = e;
          child->attrs.mode = o.perms ? e.mode : e.mode & 0777 & ~g_umask;
          child->has_attrs = child->created = true;
          int error = list_dir(child->src_path.c_str(), child->src, o.links ? LD_LINKS : 0);
          if (error || child->src.incomplete || child->src.e.size() > max_entries - entries) return false;
          size_t child_listed = child->src.e.size();
          prune_source(child->src, child->rel, e.dev, w, nullptr, guard, child->src_path);
          skip_unsafe_links(*child, w);
          reject_name_collisions(*child);
          if (child->src.e.size() != child_listed) return false;
          entries += child->src.e.size();
          directories.push_back(child.get());
          depths.push_back(depths[i] + 1);
          owned.push_back(std::move(child));
          nd++;
        }
      }
    }
    g_stats.xfer_files_total.fetch_add(nf, std::memory_order_relaxed);
    g_stats.xfer_bytes_total.fetch_add(nb, std::memory_order_relaxed);
    g_stats.clone_dirs_total.fetch_add(1, std::memory_order_relaxed);
    slot_begin(w.id, {}, d->rel.empty() ? "./" : d->rel + "/", (i64)nb, true);
    progress_tick();
    auto destination = destination_path(d->dst_path);
    if (destination.fd < 0 || clonefileat(AT_FDCWD, d->src_path.c_str(), destination.fd,
                                        destination.name.c_str(), CLONE_NOFOLLOW | CLONE_NOOWNERCOPY) != 0) {
      int error = errno;
      g_stats.xfer_files_total.fetch_sub(nf, std::memory_order_relaxed);
      g_stats.xfer_bytes_total.fetch_sub(nb, std::memory_order_relaxed);
      g_stats.clone_dirs_total.fetch_sub(1, std::memory_order_relaxed);
      slot_end(w.id);
      errno = error;
      if (errno == ENOSPC || errno == EDQUOT) file_io_error(errno, d->dst_path.c_str(), "clonefile");
      if (errno == EXDEV || errno == ENOTSUP) clone_ok.store(false, std::memory_order_relaxed);
      return false;
    }
    // APFS directory clones leave the parent mtime unchanged. Match creation
    // through mkdir, using the same pinned parent that received the clone.
    timespec parent_times[2] = {{0, UTIME_OMIT}, {0, UTIME_NOW}};
    check_attr(futimens(destination.fd, parent_times), d->waiter->dst_path.c_str(), "times");
    // The clone transaction is complete. Independent directories can now fix
    // their selected attributes in parallel, with a bounded APFS worker budget.
    pool.parallel(directories.size(), w, [&](size_t index, Worker& worker) {
      DirWork* dir = directories[index];
      const DirList& listing = dir->src;
      int fd = destination_open_dir(dir->dst_path.c_str());
      struct stat cloned{};
      dir->mode_ok = false;
      if (fd < 0 || fstat(fd, &cloned) != 0) {
        file_io_error(errno, dir->dst_path.c_str(), "open cloned directory");
      } else {
        // Children were created with this directory's initial group. Correct
        // selected identities independently rather than copying both uid/gid.
        const u32 inherited_gid = cloned.st_gid;
        for (const Entry& e : listing.e) {
          if (e.type == T_DIR) continue; // corrected through its own pinned fd below
          const char* name = listing.name(e);
          std::string path = path_join(dir->dst_path, listing.name_sv(e));
          if (o.group && e.gid != inherited_gid && can_set_gid(e.gid))
            check_attr(fchownat(fd, name, (uid_t)-1, e.gid, AT_SYMLINK_NOFOLLOW), path.c_str(), "ownership");
          if (o.owner && o.am_root && e.uid != (u32)geteuid())
            check_attr(fchownat(fd, name, e.uid, (gid_t)-1, AT_SYMLINK_NOFOLLOW), path.c_str(), "ownership");
          u32 mode = o.perms ? e.mode : e.mode & 0777 & ~g_umask;
          if (mode != e.mode)
            check_attr(fchmodat(fd, name, mode, AT_SYMLINK_NOFOLLOW), path.c_str(), "permissions");
        }
        if (o.group && dir->attrs.gid != inherited_gid && can_set_gid(dir->attrs.gid))
          check_attr(fchown(fd, (uid_t)-1, dir->attrs.gid), dir->dst_path.c_str(), "ownership");
        if (o.owner && o.am_root && dir->attrs.uid != (u32)geteuid())
          check_attr(fchown(fd, dir->attrs.uid, (gid_t)-1), dir->dst_path.c_str(), "ownership");
        dir->mode_ok = (cloned.st_mode & 07777) == dir->attrs.mode ||
                      check_attr(fchmod(fd, dir->attrs.mode), dir->dst_path.c_str(), "permissions");
      }
      if (fd >= 0) close(fd);
      for (u32 i = 0; i < listing.e.size(); ++i) {
        const Entry& e = listing.e[i];
        note_item(*dir, i, e.type == T_REG ? ">f+++++++++" : e.type == T_DIR ? "cd+++++++++" : "cL+++++++++", 0, worker);
      }
      if (dir != d) finish_dir(*dir);
    }, 4);
    g_stats.files_seen.fetch_add(nf, std::memory_order_relaxed);
    g_stats.dirs_seen.fetch_add(nd, std::memory_order_relaxed);
    g_stats.links_seen.fetch_add(nl, std::memory_order_relaxed);
    g_stats.bytes_seen.fetch_add(nb, std::memory_order_relaxed);
    g_stats.xfer_files.fetch_add(nf, std::memory_order_relaxed);
    g_stats.xfer_bytes.fetch_add(nb, std::memory_order_relaxed);
    g_stats.created_files.fetch_add(nf, std::memory_order_relaxed);
    g_stats.created_links.fetch_add(nl, std::memory_order_relaxed);
    g_stats.created_dirs.fetch_add(nd, std::memory_order_relaxed);
    g_stats.cloned_dirs.fetch_add(1, std::memory_order_relaxed);
    slot_end(w.id);
    progress_tick();
    return true;
  }
#else
  bool clone_tree(DirWork*, size_t, Worker&) { return false; }
#endif

  void scan(DirWork* d, bool prelisted, Worker& w) {
    prepare_items(*d);
    ItemScope directory_item(d->app_directory);
    item_stage(d->app_directory, "scanning");
    const Options& o = g_opt;
    int list_err = 0;
    size_t listed = 0;
    if (!prelisted) {
      list_err = list_dir(d->src_path.c_str(), d->src, o.copy_links ? LD_FOLLOW : o.links ? LD_LINKS : 0);
      if (list_err || d->src.incomplete) g_source_io_error.store(true);
      if (list_err || d->src.incomplete) source_error(list_err, d->src_path, "scan_source");
      if (d->src.incomplete && !list_err) err_line(RERR_PARTIAL, "incomplete source listing: \"%s\"", d->src_path.c_str());
      if (list_err) err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", d->src_path.c_str(), errstr(list_err).c_str());
      if (d->src.incomplete) d->no_delete = true;
      listed = d->src.e.size();
      d->source_filter = directory_filters(d->source_filter, d->src_path, false);
      prune_source(d->src, d->rel, d->attrs.dev, w, nullptr, guard, d->src_path, d->source_filter.get());
    }
    collect_source_xattrs(*d);
    if (d->lazy) {
      skip_unsafe_links(*d, w);
      reject_name_collisions(*d);
      // Our directory does not exist yet: clone it whole if we can, else create it.
      bool cloned = !list_err && clone_tree(d, listed, w);
      bool made = cloned;
      if (!cloned) {
        made = destination_mkdir(d->dst_path.c_str(), d->attrs.mode | 0700) == 0;
        if (!made && errno == EEXIST) made = true, d->created = false;
        if (!made) file_io_error(errno, d->dst_path.c_str(), "recv_generator: mkdir");
      }
      release(d->waiter);
      if (cloned) {
        finish_dir(*d);
      }
      if (cloned || !made) {
        delete d;
        return;
      }
    }
    if (list_err || d->scan_failed) {
      finish_dir(*d);
      delete d;
      return;
    }
    d->pending.store(1);
    d->lazy_children = lazy_ok;
    generate(*d, w);
    if (o.recursive || d->selection) {
      for (size_t i = 0; i < d->src.e.size(); i++) {
        const Entry& s = d->src.e[i];
        if (s.type != T_DIR || !(s.flags & EF_DESCEND)) continue;
        DirWork* c = o.prune_empty ? d->prepared_children[i].release() : new DirWork;
        if (!c) continue;
        c->app_directory = d->app_items.empty() ? ItemPtr{} : d->app_items[i];
        std::string_view nm = d->src.name_sv(s);
        if (d->src_paths.empty()) c->src_path = path_join(d->src_path, nm);
        else c->src_path = d->src_paths[i];
        if (!o.prune_empty) c->source_filter = d->source_contexts.empty() ? d->source_filter : d->source_contexts[i];
        c->receiver_filter = d->receiver_filter;
        c->receiver_filter_node = d->receiver_filter_node;
        c->dst_path = path_join(d->dst_path, d->dst_name((u32)i));
        c->destination_parent = d->child_anchor;
        c->rel = rel_join(d->rel, nm);
        c->selection = d->selection;
        if (c->selection && !o.prune_empty) {
          auto selected = c->selection->take(c->rel);
          c->src = std::move(selected.list);
          c->src_paths = std::move(selected.paths);
          c->source_contexts = std::move(selected.contexts);
          c->no_delete = selected.no_delete;
          c->attr_source = std::move(selected.source);
        }
        if (metadata_enabled()) {
          c->attrs_xattrs = d->src_xattrs[i];
          c->attrs_xattrs_loaded = true;
        }
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
        push_scan(c, o.prune_empty || (bool)c->selection);
      }
    }
    size_t n = d->need.size();
    if (n == 0) return release(d);
    d->file_ranges = parallel_file_ranges(d->src, d->need);
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
    ItemPtr observed = d.app_items.empty() ? ItemPtr{} : d.app_items[idx];
    ItemScope observation(observed);
    ItemFinalizer outcome(observed);
    item_stage(observed, "transferring");
    const Options& o = g_opt;
    Entry& s = d.src.e[idx];
    if (g_stop.load(std::memory_order_relaxed)) return;
    if (o.dry_run) {
      g_stats.xfer_bytes.fetch_add((u64)s.size, std::memory_order_relaxed);
      note_transferred(d, idx, 0, w);
      return;
    }
    src_path_of(d, idx, w.p2);
    slot_begin(w.id, d.rel, d.src.name_sv(s), s.size);
    auto fail = [&](i64 done) {
      outcome.status = "failure";
      g_stats.xfer_files_total.fetch_sub(1, std::memory_order_relaxed);
      g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - done), std::memory_order_relaxed);
      slot_end(w.id);
    };

#ifdef __APPLE__
    // The output finalizer corrects a clone's mode and selected ownership,
    // including umask/new-file and existing-file modes when -p is omitted.
    if (o.clone && !o.sparse && o.times && !o.inplace && !(s.mode & 07000) && !(s.fileflags & SF_DATALESS) && clone_ok.load(std::memory_order_relaxed)) {
      u32 fl = (o.copy_links ? 0 : CLONE_NOFOLLOW) | CLONE_NOOWNERCOPY;
      if (clone_copy(d, idx, w.p2.c_str(), fl, w)) {
        g_stats.xfer_bytes.fetch_add((u64)s.size, std::memory_order_relaxed);
        note_transferred(d, idx, 0, w);
        slot_end(w.id, true);
        return;
      }
      if (errno == EXDEV || errno == ENOTSUP) clone_ok.store(false, std::memory_order_relaxed);
    }
#endif

    static thread_local OutFile f;
    for (int attempt = 0; attempt < 2; attempt++) {
      int in = open(w.p2.c_str(), O_RDONLY | O_CLOEXEC | read_time_flags() | (o.copy_links || !d.src_paths.empty() ? 0 : O_NOFOLLOW));
      struct stat before;
      int error = in < 0 || fstat(in, &before) != 0 ? errno : !S_ISREG(before.st_mode) ? ESTALE : 0;
      if (error) {
        if (in >= 0) close(in);
        source_error(error, w.p2, "open_source");
        g_source_io_error.store(true);
        if (error == ENOENT) err_line(RERR_VANISHED, "file has vanished: \"%s\"", w.p2.c_str());
        else err_line(RERR_PARTIAL, "send_files failed to open \"%s\": %s", w.p2.c_str(), errstr(error).c_str());
        return fail(0);
      }
      auto preview_source=DestinationRevision::from(before);
      if (!item_preview_source_valid(observed,&preview_source)) { close(in); return fail(0); }
      if (metadata_enabled()) {
        const auto& context = d.source_contexts.empty() ? d.source_filter : d.source_contexts[idx];
        d.src_xattrs[idx] = source_fd_xattrs(in, w.p2, T_REG, context ? *context : o.filters);
        if (!d.src_xattrs[idx].complete) { close(in); return fail(0); }
      }
      Entry fresh = source_snapshot(s, before);
      if (fresh.size >= s.size) g_stats.xfer_bytes_total.fetch_add((u64)(fresh.size - s.size));
      else g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - fresh.size));
      s = fresh;
      if (observed) observed->size.store(s.size);
      large_file_cache_policy(in, s.size);
      slot_begin(w.id, d.rel, d.src.name_sv(s), s.size);
      ResumePrefix prefix;
      if (o.partial && !o.whole_file && attempt == 0 && s.size > (512 << 10)) {
        prefix = destination_resume_prefix(path_join(d.dst_path, d.dst_name(idx)).c_str(), s.size);
        u64 digest[2];
        if (prefix.size && (!hash_prefix_fd(in, prefix.size, digest) || digest[0] != prefix.sum[0] || digest[1] != prefix.sum[1])) prefix = {};
      }
      auto basis = !prefix.size && !o.whole_file && s.size > DELTA_THRESHOLD
                       ? (s.link_basis != 255 ? link_dest_delta_basis(d, idx) :
                          destination_delta_basis(path_join(d.dst_path, d.dst_name(idx)), o.inplace)) : nullptr;
      item_stage(observed, "transferring");
      if (basis) {
        if (!out_open(f, d, idx, w, false, true)) { close(in); return fail(0); }
        bool output_ok = true;
        auto result = delta_match_fd(in, s.size, basis->signature, [&](const DeltaOp& op) {
          bool ok = op.count ? delta_copy_blocks(f, *basis, op.first, op.count, op.offset, w.buf)
                             : out_write(f, op.literal.data(), op.literal.size(), op.offset);
          if (!ok) {
            file_io_error(errno, f.path.c_str(), "reconstruct delta");
            g_source_io_error.store(true);
            output_ok = false;
            return false;
          }
          i64 size = op.count ? basis->signature.length(op.first, op.count) : (i64)op.literal.size();
          g_stats.xfer_bytes.fetch_add((u64)size);
          slot_add(w.id, size);
          return true;
        });
        errno = result.ok ? ESTALE : EIO;
        bool stable = result.ok && source_unchanged(in, w.p2, before) && (!metadata_enabled() || source_xattrs_unchanged(d.src_xattrs[idx], w.p2));
        int validation_error = errno;
        close(in);
        f.size = s.size;
        if (output_ok && !stable && attempt == 0) {
          out_abort(f);
          g_stats.xfer_bytes.fetch_sub((u64)result.processed);
          item_retry(observed, 1, "source_changed");
          continue;
        }
        if (output_ok && !stable) {
          source_error(validation_error, w.p2, "revalidate_source");
          g_source_io_error.store(true);
          err_line(RERR_PARTIAL, "source could not be read consistently during delta transfer: \"%s\"", w.p2.c_str());
          output_ok = false;
        }
        if (stable && output_ok && !delta_verify_fd(f.fd, s.size, result.sum)) {
          file_io_error(errno, f.path.c_str(), "verify reconstructed delta");
          g_source_io_error.store(true);
          out_abort(f);  // Never retain an output whose final checksum failed.
          return fail(result.processed);
        }
        if (!out_finish(f, d, idx, w, output_ok)) return fail(result.processed);
        g_stats.delta_files.fetch_add(1);
        g_stats.delta_literal_bytes.fetch_add((u64)result.literal_bytes);
        g_stats.delta_matched_bytes.fetch_add((u64)(s.size - result.literal_bytes));
        note_transferred(d, idx, result.literal_bytes, w);
        slot_end(w.id, true);
        return;
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
        if (prefix.basis) {
          g_stats.delta_matched_bytes.fetch_add((u64)prefix.size);
          item_progress(f.item,0,(u64)prefix.size);
        }
        g_stats.xfer_bytes.fetch_add((u64)total);
        slot_add(w.id, total);
      }
      bool kernel_copy = false;
#ifdef __linux__
      // Avoid probing unsupported ioctls for every tiny file. Sparse copies and
      // bandwidth-limited writes retain the existing userspace path.
      kernel_copy = o.clone && s.size >= (1 << 20) && !o.sparse && !o.bwlimit && native_copy_ranges(in, f.fd);
      if (!prefix.size && kernel_copy && o.clone && !o.inplace) {
        int result = out_clone_data(f, in, s.size);
        if (result > 0) {
          total = s.size;
          g_stats.xfer_bytes.fetch_add((u64)total);
          slot_add(w.id, total);
        } else if (result < 0) {
          file_io_error(errno, f.path.c_str(), "clone file data");
          ok = false;
        }
      }
      // Linux 5.3–5.18 could report false success on unsupported cross-filesystem
      // copies. Use the byte path across devices on every kernel version.
      struct stat output_stat;
      if (kernel_copy && (fstat(f.fd, &output_stat) != 0 || before.st_dev != output_stat.st_dev || !native_copy_ranges(in, f.fd))) kernel_copy = false;
#endif
      if (ok && total < s.size && s.size - total >= (32 << 20) && default_jobs() > 1 && !o.sparse && d.file_ranges) {
        i64 start = total;
        constexpr i64 span = 8 << 20;
        size_t ranges = (size_t)((s.size - start + span - 1) / span);
        std::atomic<i64> copied{0};
        std::atomic<bool> failed{false};
        const bool accelerate = kernel_copy;
        pool.parallel(ranges, w, [&, output = &f](size_t range, Worker& worker) {
          i64 offset = start + (i64)range * span;
          i64 end = std::min(s.size, offset + span);
          bool kernel = accelerate;
          while (offset < end && !g_stop.load() && !failed.load()) {
            ssize_t n = 0;
            bool already_written = false;
            if (kernel) {
              n = out_copy_range(*output, in, (size_t)(end - offset), offset);
              if (n < 0 && errno == EINTR) continue;
              if (n > 0) already_written = true;
              else if (!n || errno == EXDEV || errno == EOPNOTSUPP || errno == ENOSYS || errno == EINVAL || errno == EPERM) kernel = false;
              else {
                if (!failed.exchange(true)) file_io_error(errno, output->path.c_str(), "copy file range");
                break;
              }
            }
            if (!already_written) {
              size_t count = (size_t)std::min<i64>((i64)worker.buf.size(), end - offset);
              n = pread(in, worker.buf.data(), count, offset);
              if (n < 0 && errno == EINTR) continue;
              if (n <= 0) {
                if (n < 0 && !failed.exchange(true)) {
                  source_error(errno, w.p2, "read_source");
                  g_source_io_error.store(true);
                  err_line(RERR_PARTIAL, "read errors mapping \"%s\": %s", w.p2.c_str(), errstr(errno).c_str());
                }
                break;
              }
              if (!out_write(*output, worker.buf.data(), (size_t)n, offset)) {
                if (!failed.exchange(true)) file_io_error(errno, output->path.c_str(), "write");
                break;
              }
            }
            offset += n;
            copied.fetch_add(n);
            g_stats.xfer_bytes.fetch_add((u64)n);
            slot_add(w.id, n);
          }
        }, 2);
        total += copied.load();
        ok = !failed.load() && !g_stop.load();
        if (total != s.size && ok) {
          out_abort(f); close(in);
          g_stats.xfer_bytes.fetch_sub((u64)total);
          if (attempt == 0) { item_retry(observed, 1, "source_changed"); continue; }
          source_error(ESTALE, w.p2, "revalidate_source");
          g_source_io_error.store(true);
          err_line(RERR_PARTIAL, "file changed during ranged transfer: \"%s\"", w.p2.c_str());
          return fail(0);
        }
      }
      bool byte_positioned = !kernel_copy;
      while (ok && total < s.size) {
        if (g_stop.load()) { ok = false; break; }
        if (kernel_copy) {
          size_t count = (size_t)std::min<i64>(8 << 20, s.size - total);
          ssize_t n = out_copy_range(f, in, count, total);
          if (n < 0 && errno == EINTR) continue;
          if (n > 0) {
            total += n;
            g_stats.xfer_bytes.fetch_add((u64)n);
            slot_add(w.id, n);
            continue;
          }
          if (!n || errno == EXDEV || errno == EOPNOTSUPP || errno == ENOSYS || errno == EINVAL || errno == EPERM) kernel_copy = false;
          else {
            file_io_error(errno, f.path.c_str(), "copy file range");
            ok = false;
            break;
          }
        }
        if (!byte_positioned) {
          if (lseek(in, total, SEEK_SET) < 0) {
            source_error(errno, w.p2, "seek_source");
            g_source_io_error.store(true);
            err_line(RERR_PARTIAL, "failed to seek source \"%s\": %s", w.p2.c_str(), errstr(errno).c_str());
            ok = false;
            break;
          }
          byte_positioned = true;
        }
        size_t want = (size_t)std::min<i64>((i64)w.buf.size(), s.size - total);
        ssize_t n = read(in, w.buf.data(), want);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) {
          source_error(errno, w.p2, "read_source");
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
      errno = ESTALE;
      bool stable = total == s.size && source_unchanged(in, w.p2, before) && (!metadata_enabled() || source_xattrs_unchanged(d.src_xattrs[idx], w.p2));
      int validation_error = errno;
      close(in);
      f.size = total;
      if (ok && !stable && attempt == 0) {
        out_abort(f);
        g_stats.xfer_bytes.fetch_sub((u64)total);
        item_retry(observed, 1, "source_changed");
        continue;
      }
      if (ok && !stable) {
        source_error(validation_error, w.p2, "revalidate_source");
        g_source_io_error.store(true);
        err_line(RERR_PARTIAL, "file changed during transfer after retry: \"%s\"", w.p2.c_str());
        ok = false;
      }
      ok = out_finish(f, d, idx, w, ok) && ok;
      if (!ok) return fail(total);
      note_transferred(d, idx, total - prefix.size, w);
      slot_end(w.id, true);
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
    {
      DestinationDirectory directory(d->dst_path, d->destination_parent);
      for (u32 i = t.a; i < t.b; i++) copy_one(*d, d->need[i], w);
    }
    release(d);
  }
};

}  // namespace

int run_local(const std::vector<std::string>& srcs, const std::string& dest) {
  init_ownership();
  g_local_limiter.configure(g_opt.bwlimit);
  Local L;
  L.guard = SourceGuard(dest.empty() ? "." : dest);
  L.guard.prepare(srcs);
  Worker w0;
  RootList rl;
  build_root(srcs, rl, w0, L.guard);
  DirWork* root = new DirWork;
  root->src = std::move(rl.list);
  root->src_paths = std::move(rl.src_paths);
  root->source_contexts = std::move(rl.source_contexts);
  root->attrs = rl.attrs;
  root->attr_source = std::move(rl.attr_source);
  root->has_attrs = rl.has_attrs;
  root->no_delete = rl.no_delete;
  root->selection = std::move(rl.selection);
  if (g_opt.verbose > 0) w0.logf(g_opt.prune_empty ? "building file list" : "sending incremental file list");
  w0.flush_log();
  if (g_opt.prune_empty) {
    std::vector<DirWork*> directories{root};
    for (size_t index = 0; index < directories.size() && !g_stop.load(); ++index) {
      DirWork* directory = directories[index];
      directory->prepared_children.resize(directory->src.e.size());
      if (!g_opt.recursive && !directory->selection) continue;
      for (size_t i = 0; i < directory->src.e.size(); ++i) {
        const Entry& entry = directory->src.e[i];
        if (entry.type != T_DIR || entry.rdev == 1) continue;
        auto child = std::make_unique<DirWork>();
        auto name = directory->src.name_sv(entry);
        child->src_path = directory->src_paths.empty() ? path_join(directory->src_path, name) : directory->src_paths[i];
        child->rel = rel_join(directory->rel, name);
        child->attrs = entry;
        child->has_attrs = true;
        child->source_filter = directory->source_contexts.empty() ? directory->source_filter : directory->source_contexts[i];
        child->selection = directory->selection;
        if (child->selection) {
          auto selected = child->selection->take(child->rel);
          child->src = std::move(selected.list);
          child->src_paths = std::move(selected.paths);
          child->source_contexts = std::move(selected.contexts);
          child->no_delete = selected.no_delete;
          child->attr_source = std::move(selected.source);
          directories.push_back(child.get());
          directory->prepared_children[i] = std::move(child);
          continue;
        }
        int error = list_dir(child->src_path.c_str(), child->src, g_opt.copy_links ? LD_FOLLOW : g_opt.links ? LD_LINKS : 0);
        if (error || child->src.incomplete) {
          g_source_io_error.store(true);
          child->no_delete = true;
          child->scan_failed = error != 0;
          err_line(RERR_PARTIAL, "list source directory \"%s\": %s", child->src_path.c_str(),
                   error ? errstr(error).c_str() : "incomplete source listing");
        }
        child->source_filter = directory_filters(child->source_filter, child->src_path, false);
        prune_source(child->src, child->rel, entry.dev, w0, nullptr, L.guard, child->src_path, child->source_filter.get());
        directories.push_back(child.get());
        directory->prepared_children[i] = std::move(child);
      }
    }
    prune_empty_directories(directories, dest.empty() ? "." : dest);
  }
  collect_source_xattrs(*root);
  if (!setup_dest(dest, *root, rl.single)) {
    delete root;
    return g_exit_code.load();
  }
  if (g_item_sink && rl.app_scan_failed) {
    prepare_items(*root);
    if (root->app_directory) {
      root->app_directory->failed.store(true);
      root->app_directory->source_failed.store(true);
    }
  }
#ifdef __APPLE__
  const Options& o = g_opt;
  // Whole-directory clones are only equivalent to a per-file sync when nothing could make us
  // treat any entry specially.
  L.lazy_ok = o.clone && !o.sparse && o.link_dest.empty() && o.chmod_rules.empty() && !o.ownership.requested() && !o.atimes && !o.crtimes && !o.fileflags && o.recursive && !o.copy_links && o.times && !o.omit_dir_times && !o.omit_link_times &&
              !metadata_enabled() && !o.dry_run && !o.inplace && !o.one_fs && !o.existing && !o.prune_empty && !root->selection && o.max_size <= 0 && o.min_size <= 0 && o.filters.empty();
#endif
  int n = default_jobs(dest.empty() ? "." : dest);
  progress_start(n);
  // Scanning has priority so that totals are known before the bulk of the copying starts; the
  // backlog limit bounds memory on huge trees.
  L.pool.q1_soft_limit = 512;  // batches contain at most 64 files each
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
