#pragma once
#include <cstdint>
#include <string>
#include <string_view>

struct OwnershipOverride {
  std::string user, group;
  bool user_set = false, group_set = false;
  bool uid_set = false, gid_set = false;
  uint32_t uid = 0, gid = 0;
  bool requested() const { return user_set || group_set; }
};
bool parse_ownership(std::string_view text, OwnershipOverride& override);
void init_ownership();
uint32_t ownership_uid(uint32_t source);
uint32_t ownership_gid(uint32_t source);
struct Entry;
void incoming_ownership(Entry& entry);
