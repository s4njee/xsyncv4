#pragma once
#include "app_json.h"
#include <functional>

namespace app_move {
using Emit = std::function<void(std::string)>;
// Each invocation completes a supervised endpoint operation before returning.
// Snapshot operations may consume their events privately; mutation results
// always pass through the enclosing move's public event stream.
using Execute = std::function<int(const app_json::Value&, const Emit&)>;
// Local native rename returns EXDEV when copy-then-remove is required. It must
// never replace a target unless its submitted revision still matches.
struct RenameResult { int error = 0; bool renamed = false, stale = false; };
using Rename = std::function<RenameResult(const app_json::Value&, const app_json::Value&,
                                         const app_json::Value&, const app_json::Value&, bool)>;
int run(const app_json::Value& request, const Execute& execute,
        const Rename& rename, const Emit& emit);
void not_started(const app_json::Value& request, const std::string& reason, const Emit& emit);
}
