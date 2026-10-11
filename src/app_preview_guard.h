#pragma once
#include "app_preview.h"
#include "item.h"

namespace app_preview {
// Owns expectations until native workers join. SSH halves require negotiated
// handoff before installing this guard on their helper.
class NativeGuard {
  std::shared_ptr<const Inventory> inventory;
  Emit emit;
  bool root_checks;
  decltype(g_app_preview_source_check) previous_source, previous_destination;
  bool stale(const ItemPtr&,std::string_view,bool);
  bool source(const ItemPtr&,const DestinationRevision&);
  bool destination(const ItemPtr&,const DestinationRevision&);
 public:
  NativeGuard(Inventory,Emit);
  NativeGuard(std::shared_ptr<const Inventory>,Emit,bool source=true,bool destination=true);
  NativeGuard(const NativeGuard&) = delete;
  NativeGuard& operator=(const NativeGuard&) = delete;
  ~NativeGuard();
  bool root_valid();
};
}
