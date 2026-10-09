#include "acls.h"
#include "engine.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>
#include <system_error>
#ifdef __APPLE__
#include <sys/acl.h>
#else
#include <sys/xattr.h>
#endif

namespace {
constexpr size_t MAX_ACL_BYTES = 65536;
bool supported(u8 type) { return type >= T_REG && type <= T_BLK && type != T_LNK; }
void failure(AclSet& acl, const std::string& path, const char* operation, bool source) {
  acl = {}; acl.complete = false;
  if (source) g_source_io_error.store(true);
  file_io_error(errno, path.c_str(), operation);
}
struct Pin {
  int fd = -1;
  ~Pin() { if (fd >= 0) close(fd); }
  void open(const std::string& path, u8 type, bool source) {
#ifdef __APPLE__
    int flags = O_EVTONLY | O_NONBLOCK | O_CLOEXEC;
#else
    int flags = O_PATH | O_CLOEXEC;
#endif
    if (!source || !g_opt.copy_links) flags |= O_NOFOLLOW;
    if (source) fd = ::open(path.c_str(), flags);
    else {
      auto parent = destination_path(path);
      if (parent.fd >= 0) fd = openat(parent.fd, parent.name.c_str(), flags);
    }
    if (fd >= 0) {
      struct stat st;
      Entry entry;
      if (fstat(fd, &st) == 0) { entry_from_stat(st, entry); if (entry.type == type) return; }
      close(fd); fd = -1; errno = ESTALE;
    }
  }
};
std::string bytes(const XattrValue& value) {
  if (!value.stored()) return value.inline_bytes();
  std::string result;
  if (!value.append_to(result)) throw std::system_error(errno, std::generic_category(), "read stored ACL");
  return result;
}
#ifndef __APPLE__
const char* ACCESS = "system.posix_acl_access";
const char* DEFAULT = "system.posix_acl_default";
std::string pinned(int fd) { return "/proc/self/fd/" + std::to_string(fd); }
bool absent(int error) { return error == ENODATA || error == ENOTSUP || error == EOPNOTSUPP; }
bool read_value(int fd, const char* name, XattrValue& value) {
  auto path = pinned(fd);
  for (int attempt = 0; attempt < 4; ++attempt) {
    ssize_t size = getxattr(path.c_str(), name, nullptr, 0);
    if (size < 0) return absent(errno);
    if (size > (ssize_t)MAX_ACL_BYTES) { errno = E2BIG; return false; }
    std::string data((size_t)size, '\0');
    size = getxattr(path.c_str(), name, data.data(), data.size());
    if (size >= 0) { data.resize((size_t)size); value = XattrValue(std::move(data)); return true; }
    if (errno != ERANGE) return absent(errno);
  }
  errno = EAGAIN; return false;
}
u16 tag(const std::string& data, size_t offset) { return (u8)data[offset] | (u16)(u8)data[offset + 1] << 8; }
// Access ACL owner/other/mask permissions are represented by mode bits. ACL
// itemization compares the independent named entries and owning-group access.
std::string independent(std::string data) {
  bool mask = false;
  for (size_t i = 4; i + 8 <= data.size(); i += 8) if (tag(data, i) == 16) mask = true;
  for (size_t i = 4; i + 8 <= data.size(); i += 8) {
    u16 t = tag(data, i);
    if (t == 1 || t == 32 || t == 16 || (t == 4 && !mask)) data[i + 2] = data[i + 3] = 0;
  }
  return data;
}
std::string with_mode(std::string data, u32 mode) {
  bool mask = false;
  for (size_t i = 4; i + 8 <= data.size(); i += 8) if (tag(data, i) == 16) mask = true;
  for (size_t i = 4; i + 8 <= data.size(); i += 8) {
    u16 t = tag(data, i);
    int perm = t == 1 ? (mode >> 6) & 7 : t == 32 ? mode & 7 : t == 16 || (t == 4 && !mask) ? (mode >> 3) & 7 : -1;
    if (perm >= 0) data[i + 2] = (char)perm, data[i + 3] = 0;
  }
  return data;
}
bool write_value(int fd, const char* name, const std::string& value, const std::string& path) {
  auto held = pinned(fd);
  int result = value.empty() ? removexattr(held.c_str(), name) : setxattr(held.c_str(), name, value.data(), value.size(), 0);
  if (result == 0 || (value.empty() && absent(errno))) return true;
  return check_attr(result, path.c_str(), "ACL");
}
#endif
AclSet read(int fd, const std::string& path, u8 type, bool source) {
  AclSet result;
  try {
#ifdef __APPLE__
    acl_t acl = acl_get_fd_np(fd, ACL_TYPE_EXTENDED);
    if (!acl) {
      if (errno != ENOENT && errno != ENOTSUP) failure(result, path, "read ACL", source);
      return result;
    }
    ssize_t size = acl_size(acl);
    if (size < 0 || size > (ssize_t)MAX_ACL_BYTES) {
      int error = size < 0 ? errno : E2BIG;
      acl_free(acl); errno = error; failure(result, path, "size ACL", source); return result;
    }
    std::string data((size_t)size, '\0');
    ssize_t copied = acl_copy_ext(data.data(), acl, size);
    int error = errno;
    acl_free(acl);
    if (copied < 0) { errno = error; failure(result, path, "serialize ACL", source); return result; }
    data.resize((size_t)copied);
    result.access = XattrValue(std::move(data));
#else
    if (!read_value(fd, ACCESS, result.access) || (type == T_DIR && !read_value(fd, DEFAULT, result.defaults)))
      failure(result, path, "read ACL", source);
#endif
  } catch (const std::system_error& error) {
    errno = error.code().value(); failure(result, path, "store ACL", source);
  }
  return result;
}
bool same(const AclSet& a, const AclSet& b) {
#ifdef __APPLE__
  return a.access == b.access;
#else
  return independent(bytes(a.access)) == independent(bytes(b.access)) && a.defaults == b.defaults;
#endif
}
bool apply(const AclSet& source, int fd, const std::string& path, u8 type, u32 mode) {
  if (!source.complete || !supported(type) || g_opt.dry_run) return false;
  auto current = read(fd, path, type, false);
  if (!current.complete) return false;
  bool changed = !same(source, current);
#ifdef __APPLE__
  if (changed) {
    auto data = bytes(source.access);
    acl_t acl = data.empty() ? acl_init(0) : acl_copy_int(data.data());
    if (!acl) { file_io_error(errno, path.c_str(), "deserialize ACL"); return false; }
    int result = acl_set_fd_np(fd, acl, ACL_TYPE_EXTENDED), error = errno;
    acl_free(acl); errno = error;
    check_attr(result, path.c_str(), "ACL");
  }
#else
  // Apply mode-linked permissions too, even when only the mode changed.
  if (type == T_DIR) {
    // Directory modes may be opened temporarily while children are populated.
    // Final chmod restores the source mode and its linked access-ACL bits.
    struct stat st;
    if (fstat(fd, &st) == 0) mode = st.st_mode & 07777;
  }
  auto desired = with_mode(bytes(source.access), mode);
  if (desired != bytes(current.access)) write_value(fd, ACCESS, desired, path);
  if (type == T_DIR && source.defaults != current.defaults) write_value(fd, DEFAULT, bytes(source.defaults), path);
#endif
  return changed;
}
}
AclSet source_fd_acls(int fd, const std::string& path, u8 type) {
  return supported(type) ? read(fd, path, type, true) : AclSet{};
}
AclSet source_acls(const std::string& path, u8 type) {
  if (!supported(type)) return {};
  Pin pin; pin.open(path, type, true);
  if (pin.fd >= 0) return read(pin.fd, path, type, true);
  AclSet result; failure(result, path, "open ACL", true); return result;
}
bool acls_differ(const AclSet& source, const std::string& path, u8 type) {
  if (!source.complete || !supported(type)) return false;
  Pin pin; pin.open(path, type, false);
  if (pin.fd < 0) { file_io_error(errno, path.c_str(), "open ACL"); return false; }
  try { auto current = read(pin.fd, path, type, false); return current.complete && !same(source, current); }
  catch (const std::system_error& error) { g_source_io_error.store(true); file_io_error(error.code().value(), path.c_str(), "read stored ACL"); return false; }
}
bool apply_fd_acls(const AclSet& source, int fd, const std::string& path, u8 type, u32 mode) {
  try { return apply(source, fd, path, type, mode); }
  catch (const std::system_error& error) { g_source_io_error.store(true); file_io_error(error.code().value(), path.c_str(), "read stored ACL"); return false; }
}
bool apply_acls(const AclSet& source, const std::string& path, u8 type, u32 mode) {
  if (g_opt.dry_run || !source.complete || !supported(type)) return false;
  Pin pin; pin.open(path, type, false);
  if (pin.fd < 0) { file_io_error(errno, path.c_str(), "open ACL"); return false; }
  return apply_fd_acls(source, pin.fd, path, type, mode);
}
