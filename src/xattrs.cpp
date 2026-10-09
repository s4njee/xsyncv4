#include "xattrs.h"
#include "engine.h"
#include <sys/xattr.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>

namespace {
struct Access {
  int fd = -1;
  std::string path;
  bool link = false;
  ssize_t list(char* data, size_t size) const {
#ifdef __APPLE__
    return fd >= 0 ? flistxattr(fd, data, size, 0) : listxattr(path.c_str(), data, size, link ? XATTR_NOFOLLOW : 0);
#else
    return link ? llistxattr(path.c_str(), data, size) : listxattr(path.c_str(), data, size);
#endif
  }
  ssize_t get(const char* name, void* data, size_t size) const {
#ifdef __APPLE__
    return fd >= 0 ? fgetxattr(fd, name, data, size, 0, 0) : getxattr(path.c_str(), name, data, size, 0, link ? XATTR_NOFOLLOW : 0);
#else
    return link ? lgetxattr(path.c_str(), name, data, size) : getxattr(path.c_str(), name, data, size);
#endif
  }
  int set(const char* name, const void* data, size_t size) const {
#ifdef __APPLE__
    return fsetxattr(fd, name, data, size, 0, 0);
#else
    return setxattr(path.c_str(), name, data, size, 0);
#endif
  }
  int chmod(mode_t mode) const {
#ifdef __APPLE__
    return fchmod(fd, mode);
#else
    return ::chmod(path.c_str(), mode);
#endif
  }
  int remove(const char* name) const {
#ifdef __APPLE__
    return fremovexattr(fd, name, 0);
#else
    return removexattr(path.c_str(), name);
#endif
  }
};
Access access_fd(int fd) {
  Access a;
  a.fd = fd;
#ifndef __APPLE__
  a.path = "/proc/self/fd/" + std::to_string(fd);
#endif
  return a;
}
std::string wire_name(std::string_view name) {
#ifdef __APPLE__
  if (name.starts_with("rsync.") && name.size() > 6 && name[6] != '%') return std::string(name.substr(6));
  return "user." + std::string(name);
#else
  return std::string(name);
#endif
}
std::string local_name(std::string_view name, const FilterList& filters) {
#ifdef __APPLE__
  if (name.starts_with("user.")) return std::string(name.substr(5));
  return g_opt.am_root ? "rsync." + std::string(name) : "";
#else
  if (g_opt.am_root || name.starts_with("user.")) return std::string(name);
  return filters.has_xattr_filters() ? "user.rsync." + std::string(name) : "";
#endif
}
bool internal(std::string_view name) {
#ifdef __APPLE__
  return name.starts_with("rsync.%");
#else
  return name.starts_with("user.rsync.%");
#endif
}
bool eligible(std::string_view name, const FilterList& filters, bool source) {
  if (source && g_opt.xattrs < 2 && internal(name)) return false;
#ifndef __APPLE__
  if (!filters.has_xattr_filters() && ((source || g_opt.am_root) ? name.starts_with("system.") : !name.starts_with("user."))) return false;
#endif
  return !source || !filters.xattr_excluded(name);
}
bool supported_type(u8 type) {
#ifdef __APPLE__
  // Darwin cannot set ordinary xattrs on device and special-file inodes.
  return type == T_REG || type == T_DIR || type == T_LNK;
#else
  // Linux user attributes are unavailable on symlinks and special files.
  return type == T_REG || type == T_DIR;
#endif
}
XattrSet read(const Access& a, const std::string& display, const FilterList& filters, bool source) {
  XattrSet result;
  auto fail = [&](const char* operation) {
    result.values.clear(); result.complete = false;
    if (source) g_source_io_error.store(true);
    file_io_error(errno, display.c_str(), operation);
  };
  std::vector<char> names;
  for (int attempt = 0; attempt < 4; ++attempt) {
    ssize_t count = a.list(nullptr, 0);
    if (count < 0) {
      if (errno == ENOTSUP || errno == EOPNOTSUPP) return result;
      fail("list extended attributes"); return result;
    }
    names.resize((size_t)count);
    if (!count) return result;
    count = a.list(names.data(), names.size());
    if (count >= 0) { names.resize((size_t)count); break; }
    if (errno != ERANGE || attempt == 3) { fail("list extended attributes"); return result; }
  }
  for (size_t start = 0; start < names.size();) {
    auto end = std::find(names.begin() + start, names.end(), '\0');
    if (end == names.end() || end == names.begin() + start) { errno = EIO; fail("list extended attributes"); return result; }
    std::string name(names.begin() + start, end);
    start = (size_t)(end - names.begin()) + 1;
    if (!eligible(name, filters, source)) continue;
    std::string value;
    bool done = false;
    for (int attempt = 0; attempt < 4; ++attempt) {
      ssize_t count = a.get(name.c_str(), nullptr, 0);
      if (count < 0) { fail("read extended attribute"); return result; }
      value.resize((size_t)count);
      if (!count) { done = true; break; }
      count = a.get(name.c_str(), value.data(), value.size());
      if (count >= 0) { value.resize((size_t)count); done = true; break; }
      if (errno != ERANGE) break;
    }
    if (!done) { fail("read extended attribute"); return result; }
    result.values.emplace(source ? wire_name(name) : name, std::move(value));
  }
  return result;
}
struct Target {
  int fd = -1;
  explicit Target(const std::string& path, u8 type) {
    if (!supported_type(type)) return;
    auto parent = destination_path(path);
    if (parent.fd < 0) return;
#ifdef __APPLE__
    fd = openat(parent.fd, parent.name.c_str(), O_EVTONLY | O_NONBLOCK | O_CLOEXEC | (type == T_LNK ? O_SYMLINK : O_NOFOLLOW));
#else
    fd = openat(parent.fd, parent.name.c_str(), O_PATH | O_NOFOLLOW | O_CLOEXEC);
#endif
    if (fd >= 0) {
      struct stat st;
      Entry entry;
      if (fstat(fd, &st) == 0) { entry_from_stat(st, entry); if (entry.type == type) return; }
      close(fd); fd = -1; errno = ELOOP;
    }
  }
  ~Target() { if (fd >= 0) close(fd); }
};
using LocalValues = std::map<std::string, std::string, std::less<>>;
LocalValues desired(const XattrSet& source, const FilterList& filters) {
  LocalValues result;
  for (const auto& [name, value] : source.values) {
    if (g_opt.filters.xattr_excluded(name, true, g_opt.delete_excluded)) continue;
    auto local = local_name(name, filters);
    if (!local.empty() && !(g_opt.xattrs < 2 && internal(local)) && eligible(local, filters, false)) result.emplace(std::move(local), value);
  }
  return result;
}
bool update(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters, bool write, bool fresh = false) {
  if (!source.complete || !supported_type(type)) return false;
  auto access = access_fd(fd);
  auto before = read(access, path, filters, false);
  if (!before.complete) return false;
  auto wanted = desired(source, filters);
  // Keep physical destination names: disguised namespaces must still be trimmed.
  auto current = std::move(before.values);
  bool changed = false, opened_mode = false, checked_mode = false;
  mode_t saved_mode = 0;
  auto prepare_write = [&] {
    if (!write || checked_mode) return;
    checked_mode = true;
    struct stat st;
    if (!g_opt.am_root && (type == T_REG || type == T_DIR) && fstat(fd, &st) == 0 &&
        st.st_uid == geteuid() && !(st.st_mode & S_IWUSR)) {
      saved_mode = st.st_mode & 07777;
      opened_mode = check_attr(access.chmod(saved_mode | S_IWUSR), path.c_str(), "xattr write permissions");
    }
  };
  for (const auto& [name, value] : wanted) {
    auto found = current.find(name);
    if (found != current.end() && found->second == value) continue;
    changed = true;
    if (write) { prepare_write(); check_attr(access.set(name.c_str(), value.data(), value.size()), path.c_str(), "extended attribute"); }
  }
  for (const auto& [name, value] : current) {
    if (wanted.count(name) || (!fresh && (write ? g_opt.filters : filters).xattr_excluded(name, true, g_opt.delete_excluded))) continue;
    changed = true;
    if (write) { prepare_write(); check_attr(access.remove(name.c_str()), path.c_str(), "extended attribute"); }
  }
  if (opened_mode) check_attr(access.chmod(saved_mode), path.c_str(), "restore xattr permissions");
  return changed;
}
}

XattrSet source_xattrs(const std::string& path, u8 type, const FilterList& filters) {
  if (!supported_type(type)) return {};
  Access a; a.path = path; a.link = true;
  return read(a, path, filters, true);
}
XattrSet source_fd_xattrs(int fd, const std::string& path, u8 type, const FilterList& filters) {
  if (!supported_type(type)) return {};
  struct stat leaf;
  if (lstat(path.c_str(), &leaf) == 0 && S_ISLNK(leaf.st_mode)) return source_xattrs(path, type, filters);
  return read(access_fd(fd), path, filters, true);
}
bool xattrs_differ(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters) {
  if (!source.complete || !supported_type(type)) return false;
  Target target(path, type);
  if (target.fd < 0) { file_io_error(errno, path.c_str(), "open extended attributes"); return false; }
  return update(source, target.fd, path, type, filters, false);
}
bool apply_fd_xattrs(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters, bool fresh) {
  return update(source, fd, path, type, filters, !g_opt.dry_run, fresh);
}
bool apply_xattrs(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters) {
  if (g_opt.dry_run || !source.complete || !supported_type(type)) return false;
  Target target(path, type);
  if (target.fd < 0) { file_io_error(errno, path.c_str(), "open extended attributes"); return false; }
  return update(source, target.fd, path, type, filters, true);
}
void collect_source_xattrs(DirWork& work) {
  if (!g_opt.xattrs || work.xattrs_loaded) return;
  const FilterList& base = work.source_filter ? *work.source_filter : g_opt.filters;
  if (work.has_attrs && !work.attrs_xattrs_loaded) {
    auto path = work.attr_source.empty() ? work.src_path : work.attr_source;
    work.attrs_xattrs = source_xattrs(path, T_DIR, base);
    work.attrs_xattrs_loaded = true;
  }
  work.src_xattrs.resize(work.src.e.size());
  for (size_t i = 0; i < work.src.e.size(); ++i) {
    const auto& entry = work.src.e[i];
    if (entry.item_flags & IF_PRUNED) continue;
    const FilterList& context = work.source_contexts.empty() || !work.source_contexts[i] ? base : *work.source_contexts[i];
    std::string path; src_path_of(work, (u32)i, path);
    work.src_xattrs[i] = source_xattrs(path, entry.type, context);
  }
  work.xattrs_loaded = true;
}
