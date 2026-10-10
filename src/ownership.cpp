#include "ownership.h"
#include "common.h"
#include <algorithm>
#include <grp.h>
#include <pwd.h>

namespace {
bool numeric(std::string_view name, uint32_t& id) {
  if (name.empty() || !std::all_of(name.begin(), name.end(), [](char c) { return c >= '0' && c <= '9'; })) return false;
  uint64_t value = 0;
  for (char c : name) {
    value = value * 10 + (c - '0');
    if (value > UINT32_MAX) die(RERR_SYNTAX, "Invalid ID number: %.*s", (int)name.size(), name.data());
  }
  id = (uint32_t)value;
  return true;
}
}

bool parse_ownership(std::string_view text, OwnershipOverride& override) {
  size_t colon = text.find(':');
  auto user = text.substr(0, colon);
  auto group = colon == text.npos ? std::string_view() : text.substr(colon + 1);
  // Commas would introduce additional name-map clauses in rsync's shorthand.
  if (text.find(',') != text.npos || text.find('\0') != text.npos ||
      (!user.empty() && override.user_set) || (!group.empty() && override.group_set)) return false;
  if (!user.empty()) override.user = user, override.user_set = true;
  if (!group.empty()) override.group = group, override.group_set = true;
  return true;
}

void init_ownership() {
  auto& override = g_opt.ownership;
  override.uid_set = override.gid_set = false;
  if (override.user_set) {
    if (numeric(override.user, override.uid)) override.uid_set = true;
    else if (passwd* entry = getpwnam(override.user.c_str())) override.uid = entry->pw_uid, override.uid_set = true;
    else err_line(0, "Unknown --usermap name on receiver: %s", override.user.c_str());
  }
  if (override.group_set) {
    if (numeric(override.group, override.gid)) override.gid_set = true;
    else if (group* entry = getgrnam(override.group.c_str())) override.gid = entry->gr_gid, override.gid_set = true;
    else err_line(0, "Unknown --groupmap name on receiver: %s", override.group.c_str());
  }
}
uint32_t ownership_uid(uint32_t source) { return g_opt.ownership.uid_set ? g_opt.ownership.uid : source; }
uint32_t ownership_gid(uint32_t source) { return g_opt.ownership.gid_set ? g_opt.ownership.gid : source; }
void incoming_ownership(Entry& entry) { entry.uid = ownership_uid(entry.uid); entry.gid = ownership_gid(entry.gid); }
