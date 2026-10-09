#include "acls.h"
#include "engine.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cerrno>
#include <system_error>
#include <algorithm>
#include <grp.h>
#include <pwd.h>
#include <map>
#include <mutex>
#ifdef __APPLE__
#include <sys/acl.h>
#include <membership.h>
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

namespace {
bool named(const AclRecord& entry) {
  return ACL_STYLE == 2 || entry.tag == 2 || entry.tag == 8;
}
bool group_entry(const AclRecord& entry) {
  return ACL_STYLE == 2 ? entry.tag >= 3 : entry.tag == 8;
}
std::mutex names_mutex;
std::map<std::pair<bool, u32>, std::string> source_names;
std::map<std::pair<bool, std::string>, u32> destination_names;
std::string principal_name(bool group, u32 id) {
  if (g_opt.numeric_ids) return {};
  std::lock_guard<std::mutex> lock(names_mutex);
  auto key = std::make_pair(group, id);
  if (auto found = source_names.find(key); found != source_names.end()) return found->second;
  std::string name;
  for (size_t size = 16384; size <= 131072; size *= 2) {
    std::vector<char> buffer(size);
    int error;
    if (group) {
      struct group record, *result = nullptr;
      error = getgrgid_r(id, &record, buffer.data(), buffer.size(), &result);
      if (!error && result) name = result->gr_name;
    } else {
      struct passwd record, *result = nullptr;
      error = getpwuid_r(id, &record, buffer.data(), buffer.size(), &result);
      if (!error && result) name = result->pw_name;
    }
    if (error != ERANGE) break;
  }
  // An absent or unrepresentable name retains the numeric identity.
  if (name.size() > 255) name.clear();
  if (source_names.size() >= 4096) source_names.clear();
  source_names.emplace(std::move(key), name);
  return name;
}
u32 principal_id(bool group, u32 id, const std::string& name) {
  if (g_opt.numeric_ids || name.empty()) return id;
  std::lock_guard<std::mutex> lock(names_mutex);
  auto key = std::make_pair(group, name);
  if (auto found = destination_names.find(key); found != destination_names.end())
    return found->second == UINT32_MAX ? id : found->second;
  u32 mapped = UINT32_MAX;
  for (size_t size = 16384; size <= 131072; size *= 2) {
    std::vector<char> buffer(size);
    int error;
    if (group) {
      struct group record, *result = nullptr;
      error = getgrnam_r(name.c_str(), &record, buffer.data(), buffer.size(), &result);
      if (!error && result) mapped = result->gr_gid;
    } else {
      struct passwd record, *result = nullptr;
      error = getpwnam_r(name.c_str(), &record, buffer.data(), buffer.size(), &result);
      if (!error && result) mapped = result->pw_uid;
    }
    if (error != ERANGE) break;
  }
  if (destination_names.size() >= 4096) destination_names.clear();
  destination_names.emplace(std::move(key), mapped);
  return mapped == UINT32_MAX ? id : mapped;
}
#ifdef __APPLE__
struct AclHandle {
  acl_t value = nullptr;
  ~AclHandle() { if (value) acl_free(value); }
};
[[noreturn]] void acl_error() { throw std::system_error(errno ? errno : EINVAL, std::generic_category(), "ACL conversion"); }
u32 flags_of(void* object, u32 allowed) {
  acl_flagset_t flags;
  if (acl_get_flagset_np(object, &flags)) acl_error();
  u32 result = 0;
  for (u32 bit = 1; bit <= allowed; bit <<= 1) {
    if (!(allowed & bit)) continue;
    int set = acl_get_flag_np(flags, (acl_flag_t)bit);
    if (set < 0) acl_error();
    if (set) result |= bit;
  }
  return result;
}
void set_flags(void* object, u32 mask) {
  acl_flagset_t flags;
  if (acl_get_flagset_np(object, &flags) || acl_clear_flags_np(flags)) acl_error();
  for (u32 bit = 1; bit <= mask; bit <<= 1)
    if ((mask & bit) && acl_add_flag_np(flags, (acl_flag_t)bit)) acl_error();
  if (acl_set_flagset_np(object, flags)) acl_error();
}
#else
u32 identifier(const std::string& data, size_t offset) {
  u32 value = 0;
  for (int byte = 0; byte < 4; ++byte) value |= (u32)(u8)data[offset + byte] << (byte * 8);
  return value;
}
std::vector<AclRecord> linux_records(const XattrValue& value) {
  auto data = bytes(value);
  std::vector<AclRecord> result;
  for (size_t offset = 4; offset + 8 <= data.size(); offset += 8) {
    AclRecord record{tag(data, offset), tag(data, offset + 2), 0, identifier(data, offset + 4), {}};
    if (named(record)) record.name = principal_name(group_entry(record), record.id);
    result.push_back(std::move(record));
  }
  return result;
}
XattrValue linux_value(std::vector<AclRecord> records) {
  if (records.empty()) return {};
  std::sort(records.begin(), records.end(), [](const auto& a, const auto& b) {
    return a.tag == b.tag ? a.id < b.id : a.tag < b.tag;
  });
  std::string data(4, '\0'); data[0] = 2;
  for (const auto& record : records) {
    data.push_back((char)record.tag), data.push_back(0);
    data.push_back((char)record.permissions), data.push_back(0);
    for (int byte = 0; byte < 4; ++byte) data.push_back((char)(record.id >> (byte * 8)));
  }
  return XattrValue(std::move(data));
}
#endif
}

AclRecords export_acls(const AclSet& source) {
  AclRecords records; records.complete = source.complete;
  if (!records.complete) return records;
  try {
#ifdef __APPLE__
    if (!source.access.size()) return records;
    auto data = bytes(source.access);
    AclHandle acl{acl_copy_int(data.data())};
    if (!acl.value) acl_error();
    records.flags = flags_of(acl.value, (u32)ACL_FLAG_DEFER_INHERIT | ACL_FLAG_NO_INHERIT);
    acl_entry_t entry;
    int next = ACL_FIRST_ENTRY;
    for (;;) {
      if (acl_get_entry(acl.value, next, &entry)) {
        if (errno == EINVAL) break;
        acl_error();
      }
      next = ACL_NEXT_ENTRY;
      acl_tag_t tag;
      acl_permset_mask_t permissions;
      if (acl_get_tag_type(entry, &tag) || acl_get_permset_mask_np(entry, &permissions)) acl_error();
      auto qualifier = (uuid_t*)acl_get_qualifier(entry);
      if (!qualifier) acl_error();
      id_t id; int kind;
      int error = mbr_uuid_to_id(*qualifier, &id, &kind);
      acl_free(qualifier);
      if (error || (kind != ID_TYPE_UID && kind != ID_TYPE_GID)) { errno = error ? error : EINVAL; acl_error(); }
      AclRecord record;
      record.tag = (kind == ID_TYPE_GID ? 2 : 0) + (tag == ACL_EXTENDED_ALLOW ? 1 : 2);
      record.permissions = (u32)permissions;
      record.flags = flags_of(entry, 0x1f0);
      record.id = (u32)id;
      record.name = principal_name(kind == ID_TYPE_GID, record.id);
      records.access.push_back(std::move(record));
    }
#else
    records.access = linux_records(source.access);
    records.defaults = linux_records(source.defaults);
#endif
    if (!valid_acl_records(records, T_DIR)) throw std::system_error(EINVAL, std::generic_category(), "source ACL fields");
  } catch (const std::system_error& error) {
    g_source_io_error.store(true);
    file_io_error(error.code().value(), "source ACL", "serialize ACL");
    records = {}; records.complete = false;
  }
  return records;
}

bool valid_acl_records(const AclRecords& records, u8 type) {
  if ((!supported(type) || !records.complete) && (records.flags || !records.access.empty() || !records.defaults.empty())) return false;
  if (type != T_DIR && !records.defaults.empty()) return false;
  if (records.access.size() > ACL_MAX_RECORDS || records.defaults.size() > ACL_MAX_RECORDS) return false;
  if (ACL_STYLE == 2) {
    if (!records.defaults.empty() || (records.flags & ~0x20001u)) return false;
  } else if (records.flags) return false;
  for (const auto* list : {&records.access, &records.defaults}) {
    bool owner = false, group = false, other = false, mask = false, have_names = false;
    u32 previous_tag = 0, previous_id = 0;
    for (const auto& record : *list) {
      if (record.name.size() > 255 || record.name.find('\0') != record.name.npos) return false;
      if (ACL_STYLE == 2) {
        if (record.tag < 1 || record.tag > 4 || record.id == UINT32_MAX ||
            (record.permissions & ~0x103ffeu) || (record.flags & ~0x1f0u)) return false;
      } else {
        if (record.permissions > 7 || record.flags || record.tag < previous_tag) return false;
        if (named(record)) {
          if (record.id == UINT32_MAX || (record.tag == previous_tag && record.id <= previous_id)) return false;
          have_names = true;
        } else {
          if (record.id != UINT32_MAX || !record.name.empty()) return false;
          switch (record.tag) {
            case 1: if (owner) return false; owner = true; break;
            case 4: if (group) return false; group = true; break;
            case 16: if (mask) return false; mask = true; break;
            case 32: if (other) return false; other = true; break;
            default: return false;
          }
        }
        previous_tag = record.tag, previous_id = record.id;
      }
    }
    if (ACL_STYLE == 1 && !list->empty() && (!owner || !group || !other || (have_names && !mask))) return false;
  }
  return true;
}

AclSet import_acls(AclRecords records) {
  AclSet result; result.complete = records.complete;
  if (!result.complete) return result;
  for (auto* list : {&records.access, &records.defaults})
    for (auto& record : *list)
      if (named(record)) record.id = principal_id(group_entry(record), record.id, record.name);
#ifdef __APPLE__
  if (records.access.empty() && !records.flags) return result;
  AclHandle acl{acl_init((int)records.access.size())};
  if (!acl.value) acl_error();
  set_flags(acl.value, records.flags);
  for (const auto& record : records.access) {
    acl_entry_t entry;
    if (acl_create_entry(&acl.value, &entry)) acl_error();
    uuid_t qualifier;
    int error = group_entry(record) ? mbr_gid_to_uuid(record.id, qualifier) : mbr_uid_to_uuid(record.id, qualifier);
    if (error) { errno = error; acl_error(); }
    if (acl_set_tag_type(entry, (record.tag & 1) ? ACL_EXTENDED_ALLOW : ACL_EXTENDED_DENY) ||
        acl_set_qualifier(entry, qualifier) || acl_set_permset_mask_np(entry, record.permissions)) acl_error();
    set_flags(entry, record.flags);
  }
  if (acl_valid(acl.value)) acl_error();
  ssize_t size = acl_size(acl.value);
  if (size < 0 || size > (ssize_t)MAX_ACL_BYTES) { errno = E2BIG; acl_error(); }
  std::string data((size_t)size, '\0');
  ssize_t copied = acl_copy_ext(data.data(), acl.value, size);
  if (copied < 0) acl_error();
  data.resize((size_t)copied); result.access = XattrValue(std::move(data));
#else
  result.access = linux_value(std::move(records.access));
  result.defaults = linux_value(std::move(records.defaults));
#endif
  return result;
}
