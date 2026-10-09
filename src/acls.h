#pragma once
#include "common.h"
#include "xattr_value.h"

// Transport records contain validated fields, never an opaque acl_copy_int blob.
struct AclRecord {
  // Darwin tags 5/6 retain an unresolved UUID as exactly 16 name-field bytes;
  // their ID is UINT32_MAX. All other names are ordinary account names.
  u32 tag = 0, permissions = 0, flags = 0, id = UINT32_MAX;
  std::string name;
};
struct AclRecords {
  bool complete = true;
  u32 flags = 0;
  std::vector<AclRecord> access, defaults;
};
#ifdef __APPLE__
constexpr u8 ACL_STYLE = 2;
#else
constexpr u8 ACL_STYLE = 1;
#endif
constexpr size_t ACL_MAX_RECORDS = ACL_STYLE == 2 ? 128 : 8191;

// Native ACL values are cached separately from -X's attribute-name filters.
// Metadata copies and large directory caches use the shared value budget.
// These local kernel-provided values are not a portable or validated wire format.
struct AclSet {
  XattrValue access, defaults;
  bool complete = true;
};
AclSet source_acls(const std::string& path, u8 type);
AclSet source_fd_acls(int fd, const std::string& path, u8 type);
bool acls_differ(const AclSet& source, const std::string& path, u8 type);
bool apply_acls(const AclSet& source, const std::string& path, u8 type, u32 mode);
bool apply_fd_acls(const AclSet& source, int fd, const std::string& path, u8 type, u32 mode);
AclRecords export_acls(const AclSet& source);
bool valid_acl_records(const AclRecords& records, u8 type);
AclSet import_acls(AclRecords records);
