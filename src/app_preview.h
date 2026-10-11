#pragma once
#include "app_json.h"
#include "revision.h"
#include <functional>
#include <map>

namespace app_preview {
using Emit = std::function<void(std::string)>;
using Execute = std::function<int(const app_json::Value&,const Emit&)>;
struct Inventory {
  std::map<std::string,DestinationRevision> sources, destinations;
  std::map<std::string,DestinationRevision> destination_inventory, deletions;
  std::map<std::string,std::string> targets;
  std::string destination_root;
  DestinationRevision root_revision;
};
// A complete read-only inventory is required for a guard; partial plans cannot
// authorize execution or deletion. Callbacks expose only read-only operations.
int run(const app_json::Value& request,const Execute& execute,const Emit& emit,
        const app_json::Value& expected_guard = {}, Inventory* inventory = nullptr);
}
