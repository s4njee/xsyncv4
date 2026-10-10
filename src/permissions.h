#pragma once
#include <cstdint>
#include <string_view>
#include <vector>

struct PermissionRule {
  uint32_t classes = 0, bits = 0, special = 0, special_classes = 0;
  char operation = 0, only = 0;
  bool numeric = false, conditional_x = false;
};

bool parse_permissions(std::string_view text, std::vector<PermissionRule>& rules);
uint32_t incoming_mode(uint32_t mode, uint8_t type);
