#include "link_dest.h"
#include "hardlink.h"
#include "acls.h"
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <sys/stat.h>
#include <unistd.h>

namespace {
struct Root {
  int fd = -1;
  std::string display;
  ~Root() { if (fd >= 0) close(fd); }
};
std::vector<std::unique_ptr<Root>> roots;
bool initialized = false;
DestPath path_at(size_t root, const std::string& relative) {
  if (root >= roots.size() || roots[root]->fd < 0) return {};
  std::filesystem::path path(relative);
  int fd = fcntl(roots[root]->fd, F_DUPFD_CLOEXEC, 0);
  if (fd < 0) return {};
  for (const auto& component : path.parent_path()) {
    auto name = component.string();
    if (name == "." || name.empty()) continue;
    if (name == ".." || component.is_absolute()) { close(fd); errno = EPERM; return {}; }
    int next = openat(fd, name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    int error = errno;
    close(fd);
    if (next < 0) { errno = error; return {}; }
    fd = next;
  }
  return {fd, path.filename().string()};
}
std::string relative_name(const DirWork& work, u32 index) {
  return rel_join(work.rel, work.dst_name(index));
}
bool attrs_match(DirWork& work, u32 index, const Entry& before, int fd, const std::string& path) {
  const auto& source = work.src.e[index];
  const auto& o = g_opt;
  if ((o.perms && source.mode != before.mode) ||
      (o.executability && !o.perms && execution_mode(source.mode, before.mode) != before.mode) ||
      (o.owner && o.am_root && source.uid != before.uid) ||
      (o.group && can_set_gid(source.gid) && source.gid != before.gid) ||
      (o.times && !(source.type == T_LNK && o.omit_link_times) &&
       !same_entry_time(source, before, o.checksum && source.type == T_REG)) ||
      (preserve_atime(source) && source.atime != before.atime) ||
      (preserve_crtime(source) && source.crtime != before.crtime) ||
      (o.fileflags && source.type != T_LNK && source.fileflags != before.fileflags)) return false;
  const auto& filters = work.receiver_filter ? *work.receiver_filter : o.filters;
  if (o.xattrs && !xattrs_fd_match(work.src_xattrs[index], fd, path, source.type, filters)) return false;
  if (o.acls && !acls_fd_match(work.src_xattrs[index].acl(), fd, path, source.type)) return false;
  return true;
}
bool quick_match(DirWork& work, u32 index, const Entry& before, const DestPath& path) {
  const auto& source = work.src.e[index];
  if (source.size != before.size) return false;
  if (g_opt.checksum) {
    u64 expected[2], actual[2];
    if (!work.src.sums.empty()) expected[0] = work.src.sums[2 * index], expected[1] = work.src.sums[2 * index + 1];
    else {
      std::string source_path;
      src_path_of(work, index, source_path);
      if (!hash_file(source_path.c_str(), expected)) return false;
    }
    int fd = openat(path.fd, path.name.c_str(), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC | read_time_flags());
    if (fd < 0) return false;
    bool same = hash_prefix_fd(fd, before.size, actual) && expected[0] == actual[0] && expected[1] == actual[1];
    close(fd);
    return same;
  }
  if (g_opt.ignore_times) return false;
  return g_opt.size_only || same_entry_time(source, before);
}
void compare(Entry& source, const Entry& before) {
  source.basis_mode = before.mode;
  if (source.size != before.size) source.flags |= EF_DIFF_SIZE;
  if (!same_entry_time(source, before)) source.flags |= EF_DIFF_TIME;
  if ((g_opt.perms && source.mode != before.mode) ||
      (g_opt.executability && !g_opt.perms && execution_mode(source.mode, before.mode) != before.mode)) source.item_flags |= IF_PERMS;
  if (g_opt.owner && g_opt.am_root && source.uid != before.uid) source.item_flags |= IF_OWNER;
  if (g_opt.group && can_set_gid(source.gid) && source.gid != before.gid) source.item_flags |= IF_GROUP;
  if (preserve_atime(source) && source.atime != before.atime) source.time_flags |= 1;
  if (preserve_crtime(source) && source.crtime != before.crtime) source.time_flags |= 2;
  source.fileflags_differ = g_opt.fileflags && source.type != T_LNK && source.fileflags != before.fileflags;
}
bool publish(DirWork& work, u32 index, const DestPath& basis, const struct stat& expected) {
  const std::string destination = path_join(work.dst_path, work.dst_name(index));
  auto target = destination_path(destination);
  if (target.fd < 0) return false;
  std::string temp;
  for (unsigned attempt = 0; attempt < 100; ++attempt) {
    temp = ".xsync-link-dest-" + std::to_string(getpid()) + "-" + std::to_string(now_ns()) + "-" + std::to_string(attempt);
    if (linkat(basis.fd, basis.name.c_str(), target.fd, temp.c_str(), 0) == 0) break;
    if (errno != EEXIST || attempt == 99) return false;
  }
  struct stat linked;
  bool ok = fstatat(target.fd, temp.c_str(), &linked, AT_SYMLINK_NOFOLLOW) == 0 &&
    linked.st_dev == expected.st_dev && linked.st_ino == expected.st_ino && linked.st_mode == expected.st_mode &&
    linked.st_uid == expected.st_uid && linked.st_gid == expected.st_gid && linked.st_size == expected.st_size;
  if (ok) {
    Entry original, current;
    entry_from_stat(expected, original);
    entry_from_stat(linked, current);
    ok = same_entry_time(original, current, true);
#ifdef __APPLE__
    int fd = openat(target.fd, temp.c_str(), O_EVTONLY | O_NONBLOCK | O_CLOEXEC |
                    (current.type == T_LNK ? O_SYMLINK : O_NOFOLLOW));
#else
    int fd = openat(target.fd, temp.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
#endif
    ok = ok && fd >= 0 && attrs_match(work, index, current, fd, destination);
    if (fd >= 0) close(fd);
  }
  if (!ok) errno = ESTALE;
  if (ok) ok = renameat(target.fd, temp.c_str(), target.fd, target.name.c_str()) == 0;
  int error = errno;
  if (!ok) unlinkat(target.fd, temp.c_str(), 0);
  errno = error;
  return ok;
}
bool copy_basis(DirWork& work, u32 index, Worker& worker, const DestPath& basis, const Entry& before) {
  int fd = openat(basis.fd, basis.name.c_str(), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC | read_time_flags());
  if (fd < 0) return false;
  struct stat stat;
  if (fstat(fd, &stat) != 0 || !S_ISREG(stat.st_mode) || (u64)stat.st_dev != before.hdev || (u64)stat.st_ino != before.ino) { close(fd); return false; }
  OutFile output;
  bool ok = out_open(output, work, index, worker, true);
  worker.buf.resize(1 << 20);
  for (i64 offset = 0; ok && offset < before.size;) {
    if (g_stop.load()) { errno = EINTR; ok = false; break; }
    ssize_t n = pread(fd, worker.buf.data(), std::min<i64>(worker.buf.size(), before.size - offset), offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { ok = false; break; }
    ok = out_write(output, worker.buf.data(), (size_t)n, offset);
    offset += n;
  }
  struct stat after;
  Entry current;
  if (fstat(fd, &after) != 0) ok = false;
  else {
    entry_from_stat(after, current);
    ok &= current.size == before.size && current.mtime == before.mtime && current.mtime_ns == before.mtime_ns &&
          current.ctime == before.ctime && current.ctime_ns == before.ctime_ns;
  }
  close(fd);
  output.size = before.size;
  if (!ok) { out_abort(output); return false; }
  return out_finish(output, work, index, worker, true);
}
}

void init_link_dest(const std::string& destination) {
  if (initialized) return;
  initialized = true;
  for (const auto& input : g_opt.link_dest) {
    auto root = std::make_unique<Root>();
    if (input.empty()) {
      err_line(0, "--link-dest directory unavailable: empty path");
      roots.push_back(std::move(root));
      continue;
    }
    std::filesystem::path path(input);
    if (!path.is_absolute()) {
      std::error_code base_error;
      auto absolute = std::filesystem::absolute(destination, base_error);
      auto base = base_error ? std::filesystem::path(destination) : std::filesystem::weakly_canonical(absolute, base_error);
      if (base_error) base = std::filesystem::path(destination);
      path = base / path;
    }
    path = path.lexically_normal();
    std::error_code error;
    auto canonical = std::filesystem::canonical(path, error);
    root->display = path.lexically_normal().string();
    if (!error) {
      root->fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
      for (const auto& component : canonical.relative_path()) {
        if (root->fd < 0) break;
        int next = openat(root->fd, component.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        close(root->fd); root->fd = next;
      }
    }
    if (root->fd < 0) err_line(0, "--link-dest directory unavailable: %s", root->display.c_str());
    roots.push_back(std::move(root));
  }
}

DestPath link_dest_path(const DirWork& work, u32 index) {
  return path_at(work.src.e[index].link_basis, relative_name(work, index));
}

std::optional<Entry> link_dest_directory(const std::string& relative, Entry& source, const XattrSet& attrs, const FilterList& filters) {
  std::optional<Entry> selected;
  u8 metadata = 0;
  for (size_t root = 0; root < roots.size(); ++root) {
    auto basis = path_at(root, relative.empty() ? "." : relative);
    if (basis.fd < 0) continue;
    int fd = openat(basis.fd, basis.name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) continue;
    struct stat stat;
    if (fstat(fd, &stat) != 0) { close(fd); continue; }
    Entry before; entry_from_stat(stat, before);
    u8 changed = 0;
    if (g_opt.xattrs && !xattrs_fd_match(attrs, fd, roots[root]->display, T_DIR, filters)) changed |= IF_XATTR;
    if (g_opt.acls && !acls_fd_match(attrs.acl(), fd, roots[root]->display, T_DIR)) changed |= IF_ACL;
    close(fd);
    bool same = !changed && (!g_opt.perms || source.mode == before.mode) &&
      (!(g_opt.owner && g_opt.am_root) || source.uid == before.uid) &&
      (!(g_opt.group && can_set_gid(source.gid)) || source.gid == before.gid) &&
      (!(g_opt.times && !g_opt.omit_dir_times) || same_entry_time(source, before)) &&
      (!preserve_crtime(source) || source.crtime == before.crtime) &&
      (!g_opt.fileflags || source.fileflags == before.fileflags);
    if (!selected || same) { selected = before; metadata = changed; }
    if (same) break;
  }
  source.item_flags |= metadata;
  return selected;
}

bool link_dest_regular(DirWork& work, u32 index, Worker& worker, const Entry* actual) {
  auto& source = work.src.e[index];
  size_t selected = roots.size();
  int level = 0;
  Entry before;
  struct stat stat;
  for (size_t root = 0; root < roots.size(); ++root) {
    auto basis = path_at(root, relative_name(work, index));
    struct stat candidate;
    if (basis.fd < 0 || fstatat(basis.fd, basis.name.c_str(), &candidate, AT_SYMLINK_NOFOLLOW) != 0 || !S_ISREG(candidate.st_mode)) continue;
    Entry entry; entry_from_stat(candidate, entry);
    int score = 1;
    if (quick_match(work, index, entry, basis)) {
      score = 2;
#ifdef __APPLE__
      int fd = openat(basis.fd, basis.name.c_str(), O_EVTONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
#else
      int fd = openat(basis.fd, basis.name.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
#endif
      if (fd >= 0) {
        struct stat pinned;
        if (fstat(fd, &pinned) == 0 && pinned.st_dev == candidate.st_dev && pinned.st_ino == candidate.st_ino &&
            attrs_match(work, index, entry, fd, roots[root]->display + "/" + relative_name(work, index))) score = 3;
        close(fd);
      }
    }
    if (score > level) { selected = root; before = entry; stat = candidate; level = score; }
    if (score == 3) break;
  }
  if (!level) return false;
  auto basis = path_at(selected, relative_name(work, index));
  if (level == 3) {
    if (actual && actual->hdev == before.hdev && actual->ino == before.ino) return false;
    if (g_opt.dry_run || publish(work, index, basis, stat)) {
      if (!g_opt.perms) source.mode = before.mode;
      hardlink_prepare(work, index, actual ? actual : &before, !actual);
      hardlink_complete(work, index, source, &stat);
      if (!actual) g_stats.created_files.fetch_add(1);
      work.modified = true;
      if (g_opt.output_unchanged) note_item(work, index, "hf         ", 0, worker);
      return true;
    }
    // Cross-device or unavailable hard links still allow an independent copy.
    level = 2;
  }
  if (actual) return false;
  source.link_basis = (u8)selected;
  compare(source, before);
  if (!g_opt.perms) {
    if (level == 1) source.mode = g_opt.executability ? execution_mode(source.mode, before.mode) : before.mode;
    else source.mode &= 0777 & ~g_umask;
  }
  if (g_opt.xattrs || g_opt.acls) {
    int fd = openat(basis.fd, basis.name.c_str(), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd >= 0) {
      const auto& filters = work.receiver_filter ? *work.receiver_filter : g_opt.filters;
      if (g_opt.xattrs && !xattrs_fd_match(work.src_xattrs[index], fd, roots[selected]->display, T_REG, filters)) source.item_flags |= IF_XATTR;
      if (g_opt.acls && !acls_fd_match(work.src_xattrs[index].acl(), fd, roots[selected]->display, T_REG)) source.item_flags |= IF_ACL;
      close(fd);
    }
  }
  if (level == 1) return false;
  hardlink_prepare(work, index, &before, true);
  if (g_opt.dry_run || copy_basis(work, index, worker, basis, before)) {
    if (g_opt.dry_run) hardlink_complete(work, index, source);
    char code[12] = "cf.........";
    if (source.flags & EF_DIFF_TIME) code[4] = 't';
    if (source.item_flags & IF_PERMS) code[5] = 'p';
    if (source.item_flags & IF_OWNER) code[6] = 'o';
    if (source.item_flags & IF_GROUP) code[7] = 'g';
    code[8] = source.time_flags == 3 ? 'b' : source.time_flags == 1 ? 'u' : source.time_flags == 2 ? 'n' : '.';
    if (source.item_flags & IF_ACL) code[9] = 'a';
    if (source.item_flags & IF_XATTR) code[10] = 'x';
    if (!actual) g_stats.created_files.fetch_add(1);
    work.modified = true;
    note_item(work, index, code, 0, worker);
    return true;
  }
  return false;
}

std::shared_ptr<DeltaBasis> link_dest_delta_basis(const DirWork& work, u32 index) {
  auto basis = link_dest_path(work, index);
  if (basis.fd < 0) return {};
  int fd = openat(basis.fd, basis.name.c_str(), O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC | read_time_flags());
  return readonly_delta_basis(fd);
}

bool link_dest_nonregular(DirWork& work, u32 index, Worker& worker, std::optional<Entry>& before) {
  auto& source = work.src.e[index];
  size_t selected = roots.size();
  int level = 0;
  struct stat expected;
  for (size_t root = 0; root < roots.size(); ++root) {
    auto basis = path_at(root, relative_name(work, index));
    struct stat stat;
    if (basis.fd < 0 || fstatat(basis.fd, basis.name.c_str(), &stat, AT_SYMLINK_NOFOLLOW) != 0) continue;
    Entry candidate; entry_from_stat(stat, candidate);
    if (candidate.type != source.type) continue;
    int score = 1;
    bool same = true;
    if (source.type == T_LNK) {
      std::vector<char> text(strlen(work.src.link(source)) + 1);
      ssize_t length = readlinkat(basis.fd, basis.name.c_str(), text.data(), text.size());
      same = length >= 0 && (size_t)length == text.size() - 1 &&
        memcmp(text.data(), work.src.link(source), (size_t)length) == 0;
    } else if (source.type == T_CHR || source.type == T_BLK) same = candidate.rdev == source.rdev;
    if (same) {
      score = 2;
#ifdef __APPLE__
      int fd = openat(basis.fd, basis.name.c_str(), O_EVTONLY | O_NONBLOCK | O_CLOEXEC | (source.type == T_LNK ? O_SYMLINK : O_NOFOLLOW));
#else
      int fd = openat(basis.fd, basis.name.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
#endif
      if (fd >= 0) {
        struct stat pinned;
        if (fstat(fd, &pinned) == 0 && pinned.st_dev == stat.st_dev && pinned.st_ino == stat.st_ino &&
            attrs_match(work, index, candidate, fd, roots[root]->display)) score = 3;
        close(fd);
      }
    }
    if (score > level) { selected = root; before = candidate; expected = stat; level = score; }
    if (score == 3) break;
  }
  if (!level) return false;
  auto basis = path_at(selected, relative_name(work, index));
  if (level == 3 && (g_opt.dry_run || publish(work, index, basis, expected))) {
    if (!g_opt.perms) source.mode = before->mode;
    hardlink_prepare(work, index, &*before, true);
    hardlink_complete(work, index, source, &expected);
    work.modified = true;
    if (source.type == T_LNK) g_stats.created_links.fetch_add(1);
    else g_stats.created_specials.fetch_add(1);
    if (g_opt.output_unchanged) {
      char code[12] = "hL         ";
      code[1] = source.type == T_LNK ? 'L' : source.type == T_CHR || source.type == T_BLK ? 'D' : 'S';
      note_item(work, index, code, 0, worker);
    }
    return true;
  }
  source.link_basis = (u8)selected;
  compare(source, *before);
  if (level == 1) source.flags |= EF_DIFF_SIZE;
  if (g_opt.xattrs || g_opt.acls) {
#ifdef __APPLE__
    int fd = openat(basis.fd, basis.name.c_str(), O_EVTONLY | O_NONBLOCK | O_CLOEXEC | (source.type == T_LNK ? O_SYMLINK : O_NOFOLLOW));
#else
    int fd = openat(basis.fd, basis.name.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
#endif
    if (fd >= 0) {
      const auto& filters = work.receiver_filter ? *work.receiver_filter : g_opt.filters;
      if (g_opt.xattrs && !xattrs_fd_match(work.src_xattrs[index], fd, roots[selected]->display, source.type, filters)) source.item_flags |= IF_XATTR;
      if (g_opt.acls && !acls_fd_match(work.src_xattrs[index].acl(), fd, roots[selected]->display, source.type)) source.item_flags |= IF_ACL;
      close(fd);
    }
  }
  return false;
}
