#pragma once
#include "app_preview.h"
#include <set>

namespace app_mirror {
struct Receipts {
  const app_preview::Inventory& inventory;
  std::set<std::string> protected_paths, outputs;
  std::map<std::string,std::string> directory_sources;
  explicit Receipts(const app_preview::Inventory& value) : inventory(value) {}
  void accept(const app_json::Value&);
};
// Called only after authoritative successful native copy and while local/SSH
// destination leases remain held. Every deletion is nonrecursive and guarded.
int finish(const app_json::Value&,const app_preview::Inventory&,const Receipts&,
           const app_preview::Execute&,const app_preview::Emit&);
void validate_root_times(const app_json::Value&);
int root_times(const app_json::Value&,const std::function<bool()>&,const app_preview::Emit&);
}
