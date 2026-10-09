#pragma once
#include "common.h"
#include "xattr_value.h"

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
