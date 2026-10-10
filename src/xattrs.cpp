#include "xattrs.h"
#include "engine.h"
#include <sys/xattr.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <array>
#include <system_error>

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
  int set_value(const char* name, const XattrValue& value) const {
#ifdef __APPLE__
    if (std::string_view(name) == "com.apple.ResourceFork" && value.size() > XattrValue::INLINE_MAX) {
      int fork = openat(fd, "..namedfork/rsrc", O_WRONLY | O_CREAT | O_NOFOLLOW | O_CLOEXEC, 0600);
      if (fork < 0) return -1;
      bool ok = value.size() <= (u64)INT64_MAX && ftruncate(fork, (off_t)value.size()) == 0;
      std::array<char, 65536> bytes;
      for (u64 pos = 0; ok && pos < value.size();) {
        size_t n = (size_t)std::min<u64>(bytes.size(), value.size() - pos);
        ok = value.read(bytes.data(), n, pos);
        size_t done = 0;
        while (ok && done < n) {
          ssize_t k = pwrite(fork, bytes.data() + done, n - done, (off_t)(pos + done));
          if (k < 0 && errno == EINTR) continue;
          if (k <= 0) { if (!k) errno = EIO; ok = false; break; }
          done += (size_t)k;
        }
        pos += n;
      }
      int error = errno;
      if (close(fork) != 0 && ok) return -1;
      errno = error;
      return ok ? 0 : -1;
    }
#endif
    // Non-fork APIs require one contiguous value. Large source/destination
    // caches still stay on disk; materialize only this attribute for its call.
    if (!value.stored()) return set(name, value.inline_bytes().data(), value.inline_bytes().size());
    std::string bytes;
    if (!value.append_to(bytes)) return -1;
    return set(name, bytes.data(), bytes.size());
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
#ifdef __APPLE__
  if (source && name == "rsync.") return false;  // Empty disguised namespace.
#endif
#ifndef __APPLE__
  if (g_opt.acls && (name == "system.posix_acl_access" || name == "system.posix_acl_default")) return false;
  if (!filters.has_xattr_filters() && ((source || g_opt.am_root) ? name.starts_with("system.") : !name.starts_with("user."))) return false;
#endif
  return !source || !filters.xattr_excluded(name);
}
bool supported_type(u8 type) {
#ifdef __APPLE__
  // Darwin cannot set ordinary xattrs on device and special-file inodes.
  return type == T_REG || type == T_DIR || type == T_LNK;
#else
  // Privileged namespaces are also supported on links and special inodes.
  // O_PATH plus the /proc descriptor link addresses that inode without opening
  // a FIFO/device or following the physical symlink to its target.
  return type >= T_REG && type <= T_BLK;
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
    XattrValue stored;
    bool streamed = false;
    bool done = false;
    for (int attempt = 0; attempt < 4; ++attempt) {
      ssize_t count = a.get(name.c_str(), nullptr, 0);
      if (count < 0) { fail("read extended attribute"); return result; }
#ifdef __APPLE__
      if (name == "com.apple.ResourceFork" && count > (ssize_t)XattrValue::INLINE_MAX) {
        int source = a.fd;
        bool owned = source < 0;
        if (owned) {
          struct stat st;
          if (lstat(a.path.c_str(), &st) != 0) { fail("open resource fork attributes"); return result; }
          source = open(a.path.c_str(), O_EVTONLY | O_CLOEXEC | (S_ISLNK(st.st_mode) ? O_SYMLINK : O_NOFOLLOW));
        }
        int fork = source < 0 ? -1 : openat(source, "..namedfork/rsrc", O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
        int error = errno;
        if (owned && source >= 0) close(source);
        if (fork < 0) { errno = error; fail("open resource fork attributes"); return result; }
        bool ok = XattrValue::from_fd(fork, (u64)count, stored);
        error = errno;
        close(fork);
        if (!ok) { errno = error; fail("read resource fork attributes"); return result; }
        streamed = done = true;
        break;
      }
#endif
      value.resize((size_t)count);
      if (!count) { done = true; break; }
      count = a.get(name.c_str(), value.data(), value.size());
      if (count >= 0) { value.resize((size_t)count); done = true; break; }
      if (errno != ERANGE) break;
    }
    if (!done) { fail("read extended attribute"); return result; }
    // rsync applies later enumerated attributes last when physical names
    // collapse to the same protocol name (foo and rsync.user.foo on Darwin).
    try {
      if (!streamed) stored = XattrValue(std::move(value));
      result.values.insert_or_assign(source ? wire_name(name) : name, std::move(stored));
    } catch (const std::system_error& error) {
      errno = error.code().value(); fail("store extended attribute"); return result;
    }
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
using LocalValues = std::map<std::string, XattrValue, std::less<>>;
LocalValues desired(const XattrSet& source, const FilterList& filters) {
  LocalValues result;
  for (const auto& [name, value] : source.values) {
    if (g_opt.filters.xattr_excluded(name, true, g_opt.delete_excluded)) continue;
    auto local = local_name(name, filters);
    if (!local.empty() && !(g_opt.xattrs < 2 && internal(local)) && eligible(local, filters, false)) result.emplace(std::move(local), value);
  }
  return result;
}
bool update(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters, bool write, bool fresh = false, bool ownership_changed = false, bool* valid = nullptr) {
  if (valid) *valid = false;
  if (!source.complete) return false;
  if (!supported_type(type)) {
    if (valid) *valid = true;
    bool selected = !desired(source, filters).empty();
    if (selected && write) file_io_error(ENOTSUP, path.c_str(), "set extended attributes on unsupported file type");
    return selected;
  }
  auto access = access_fd(fd);
  auto before = read(access, path, filters, false);
  if (!before.complete) return false;
  auto wanted = desired(source, filters);
  // Keep physical destination names: disguised namespaces must still be trimmed.
  auto current = std::move(before.values);
  bool changed = false, opened_mode = false, checked_mode = false;
#ifndef __APPLE__
  // chown clears file capabilities even when their pre-change bytes match.
  // Report the necessary restoration and apply it after ownership changes.
  if (ownership_changed && wanted.count("security.capability")) changed = true;
#endif
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
    if (write) { prepare_write(); check_attr(access.set_value(name.c_str(), value), path.c_str(), "extended attribute"); }
  }
  for (const auto& [name, value] : current) {
    if (wanted.count(name) || (!fresh && (write ? g_opt.filters : filters).xattr_excluded(name, true, g_opt.delete_excluded))) continue;
    changed = true;
    if (write) { prepare_write(); check_attr(access.remove(name.c_str()), path.c_str(), "extended attribute"); }
  }
  if (opened_mode) check_attr(access.chmod(saved_mode), path.c_str(), "restore xattr permissions");
  if (valid) *valid = true;
  return changed;
}
}

namespace {
void include_acls(XattrSet& attrs, AclSet acl) {
  attrs.complete &= acl.complete;
  if (!acl.complete || acl.access.size() || acl.defaults.size()) attrs.acls = std::make_shared<AclSet>(std::move(acl));
}
}
XattrSet source_xattrs(const std::string& path, u8 type, const FilterList& filters) {
  XattrSet attrs;
  if (g_opt.xattrs && supported_type(type)) {
    Access access; access.path = path; access.link = true;
    attrs = read(access, path, filters, true);
  }
  if (g_opt.acls) { include_acls(attrs, source_acls(path, type)); }
  return attrs;
}
XattrSet source_fd_xattrs(int fd, const std::string& path, u8 type, const FilterList& filters) {
  XattrSet attrs;
  if (g_opt.xattrs && supported_type(type)) {
    struct stat leaf;
    if (lstat(path.c_str(), &leaf) == 0 && S_ISLNK(leaf.st_mode)) {
      Access access; access.path = path; access.link = true;
      attrs = read(access, path, filters, true);
      Entry entry; entry_from_stat(leaf, entry);
      attrs.guarded_link = true;
      attrs.link_dev = leaf.st_dev, attrs.link_ino = leaf.st_ino;
      attrs.link_ctime = entry.ctime, attrs.link_ctime_ns = entry.ctime_ns;
    } else attrs = read(access_fd(fd), path, filters, true);
  }
  if (g_opt.acls) { include_acls(attrs, source_fd_acls(fd, path, type)); }
  return attrs;
}
bool source_xattrs_unchanged(const XattrSet& attrs, const std::string& path) {
  if (!attrs.guarded_link) return true;
  struct stat leaf;
  if (lstat(path.c_str(), &leaf) != 0 || !S_ISLNK(leaf.st_mode)) return false;
  Entry entry; entry_from_stat(leaf, entry);
  return (u64)leaf.st_dev == attrs.link_dev && (u64)leaf.st_ino == attrs.link_ino &&
         entry.ctime == attrs.link_ctime && entry.ctime_ns == attrs.link_ctime_ns;
}
bool xattrs_differ(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters, bool ownership_changed) {
  if (!source.complete) return false;
  if (!supported_type(type)) return !desired(source, filters).empty();
  Target target(path, type);
  if (target.fd < 0) { file_io_error(errno, path.c_str(), "open extended attributes"); return false; }
  try { return update(source, target.fd, path, type, filters, false, false, ownership_changed); }
  catch (const std::system_error& error) { g_source_io_error.store(true); file_io_error(error.code().value(), path.c_str(), "read stored extended attributes"); return false; }
}
bool xattrs_fd_match(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters) {
  try {
    bool valid = false;
    bool differs = update(source, fd, path, type, filters, false, false, false, &valid);
    return valid && !differs;
  } catch (const std::system_error&) { return false; }
}
bool apply_fd_xattrs(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters, bool fresh) {
  try { return update(source, fd, path, type, filters, !g_opt.dry_run, fresh); }
  catch (const std::system_error& error) { g_source_io_error.store(true); file_io_error(error.code().value(), path.c_str(), "read stored extended attributes"); return false; }
}
bool apply_xattrs(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters) {
  if (g_opt.dry_run || !source.complete) return false;
  if (!supported_type(type)) {
    bool selected = !desired(source, filters).empty();
    if (selected) file_io_error(ENOTSUP, path.c_str(), "set extended attributes on unsupported file type");
    return selected;
  }
  Target target(path, type);
  if (target.fd < 0) { file_io_error(errno, path.c_str(), "open extended attributes"); return false; }
  try { return update(source, target.fd, path, type, filters, true); }
  catch (const std::system_error& error) { g_source_io_error.store(true); file_io_error(error.code().value(), path.c_str(), "read stored extended attributes"); return false; }
}
void collect_source_xattrs(DirWork& work) {
  if (!metadata_enabled() || work.xattrs_loaded) return;
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
