#pragma once
#include "app_json.h"
#include <string>

namespace app_preflight {
// Validate caller-supplied budget inputs before any endpoint operation.
app_json::Value parse(const app_json::Value& request);
// Read-only observation; endpoint/open failures throw std::system_error.
app_json::Value inspect(const std::string& path, const app_json::Value& space);
}
