#include "permissions.h"
#include "common.h"

bool parse_permissions(std::string_view text, std::vector<PermissionRule>& rules) {
  std::vector<PermissionRule> parsed;
  do {
    size_t comma = text.find(',');
    auto clause = text.substr(0, comma);
    if (clause.empty()) return false;
    PermissionRule rule;
    size_t i = 0;
    for (; i < clause.size(); ++i) {
      char c = clause[i];
      if (c == '+' || c == '-' || c == '=' || (c >= '0' && c <= '7')) break;
      switch (c) {
        case 'D': case 'F':
          if (rule.only && rule.only != c) return false;
          rule.only = c; break;
        case 'u': rule.classes |= 0100; rule.special_classes |= 04000; break;
        case 'g': rule.classes |= 0010; rule.special_classes |= 02000; break;
        case 'o': rule.classes |= 0001; break;
        case 'a': rule.classes |= 0111; break;
        default: return false;
      }
    }
    if (i == clause.size()) return false;
    rule.operation = clause[i++];
    if (rule.operation >= '0' && rule.operation <= '7') {
      if (rule.classes) return false;
      rule.numeric = true;
      --i;
      for (; i < clause.size(); ++i) {
        char c = clause[i];
        if (c < '0' || c > '7') return false;
        rule.bits = rule.bits * 8 + (c - '0');
        if (rule.bits > 07777) return false;
      }
    } else {
      for (; i < clause.size(); ++i) {
        switch (clause[i]) {
          case 'r': rule.bits |= 4; break;
          case 'w': rule.bits |= 2; break;
          case 'X': rule.conditional_x = true; [[fallthrough]];
          case 'x': rule.bits |= 1; break;
          case 's': rule.special |= rule.special_classes ? rule.special_classes : 04000; break;
          case 't': rule.special |= 01000; break;
          default: return false;
        }
      }
    }
    parsed.push_back(rule);
    if (comma == text.npos) break;
    text.remove_prefix(comma + 1);
  } while (true);
  rules.insert(rules.end(), parsed.begin(), parsed.end());
  return true;
}

uint32_t incoming_mode(uint32_t mode, uint8_t type) {
  if (type == T_LNK || type == T_NONE) return mode;
  bool executable = mode & 0111;
  for (const auto& rule : g_opt.chmod_rules) {
    if ((rule.only == 'D' && type != T_DIR) || (rule.only == 'F' && type == T_DIR)) continue;
    if (rule.numeric) { mode = rule.bits; continue; }
    uint32_t classes = rule.classes ? rule.classes : 0111;
    uint32_t bits = classes * rule.bits;
    if (!rule.classes) bits &= ~g_umask;
    uint32_t added = bits;
    if (rule.conditional_x && !executable && type != T_DIR) added &= ~0111u;
    switch (rule.operation) {
      case '+': mode |= added | rule.special; break;
      case '-': mode &= ~(bits | rule.special); break;
      case '=':
        mode &= ~(classes * 7 | (rule.special ? rule.special_classes : 0));
        mode |= added | rule.special;
        break;
    }
  }
  return mode;
}
