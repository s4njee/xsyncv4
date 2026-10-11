#include "app_preview_guard.h"
#include "output.h"

namespace app_preview {
NativeGuard::NativeGuard(Inventory value,Emit output) : NativeGuard(std::make_shared<Inventory>(std::move(value)),std::move(output)) {}
NativeGuard::NativeGuard(std::shared_ptr<const Inventory> value,Emit output,bool src,bool dst) : inventory(std::move(value)),emit(std::move(output)),root_checks(dst && inventory->root_revision.known),
  previous_source(std::move(g_app_preview_source_check)),previous_destination(std::move(g_app_preview_destination_check)) {
  if (src && !inventory->sources.empty()) g_app_preview_source_check=[this](const ItemPtr& item,const DestinationRevision& revision) { return source(item,revision); };
  if (dst && inventory->root_revision.known) g_app_preview_destination_check=[this](const ItemPtr& item,const DestinationRevision& revision) { return destination(item,revision); };
}
NativeGuard::~NativeGuard() {
  g_app_preview_source_check=std::move(previous_source);
  g_app_preview_destination_check=std::move(previous_destination);
}
bool NativeGuard::stale(const ItemPtr& item,std::string_view path,bool src) {
  if (item) {
    item->failed.store(true);
    if (item->preview_stale.exchange(true)) return false;
    if (src) item->source_failed.store(true); else item->destination_changed.store(true);
  }
  emit("\"type\":\"error\",\"operation\":\"preview_execution\",\"category\":\"conflict\",\"endpoint\":\"local\",\"side\":"+app_json::quote(src ? "source" : "destination")+
    ",\"stage\":\"preview_execution\",\"reason\":\"stale_preview\",\"path\":"+app_json::path(path)+
    ",\"item_id\":"+(item ? app_json::quote(app_json::hex(item->relative)) : "null")+
    ",\"native_code\":null,\"retryable\":false,\"message\":\"filesystem entry changed after preview admission\"");
  err_line(RERR_PARTIAL,"filesystem entry changed after preview admission: \"%s\"",std::string(path).c_str());
  return false;
}
bool NativeGuard::root_valid() {
  if (!root_checks) return true;
  struct stat st;
  return (lstat(inventory->destination_root.c_str(),&st)==0 && inventory->root_revision==DestinationRevision::from(st)) || stale({},inventory->destination_root,false);
}
bool NativeGuard::source(const ItemPtr& item,const DestinationRevision& revision) {
  auto find=[&](std::string path) {
    while (path.ends_with("/.")) path.resize(path.size()-2);
    if (path.empty()) path="/";
    return inventory->sources.find(path);
  };
  auto expected=find(item->source);
  if (expected==inventory->sources.end() || !(expected->second==revision)) return stale(item,item->source,true);
  auto path=item->source;
  while (path.size()>1) {
    auto slash=path.rfind('/'); path=slash==0 ? "/" : path.substr(0,slash);
    auto ancestor=find(path);
    if (ancestor==inventory->sources.end()) continue;
    struct stat st;
    if (lstat(path.c_str(),&st) || !(ancestor->second==DestinationRevision::from(st))) return stale(item,path,true);
  }
  return true;
}
bool NativeGuard::destination(const ItemPtr& item,const DestinationRevision& revision) {
  if (item->preview_stale.load()) return false;
  bool root_item=false;
  for (auto ancestor=item; ancestor; ancestor=ancestor->parent) root_item|=ancestor->relative.empty();
  if (!root_item) {
    // Entry selections have a virtual root without a TransferItem. Bind its
    // metadata too; only child-mutation fields may change during this copy.
    struct stat st;
    if (lstat(inventory->destination_root.c_str(),&st)) return stale(item,inventory->destination_root,false);
    auto root=DestinationRevision::from(st); const auto& expected=inventory->root_revision;
    if (!expected.same_object(root) || expected.mode!=root.mode || expected.uid!=root.uid || expected.gid!=root.gid || expected.flags!=root.flags)
      return stale(item,inventory->destination_root,false);
  }
  auto expected=item->expected_destination;
  if (!item->preview_destination_bound) {
    bool mapped=false;
    for (auto ancestor=item->parent; ancestor; ancestor=ancestor->parent) mapped|=ancestor->renamed;
    auto row=inventory->destinations.find(item->relative);
    if (item->relative.empty()) expected=inventory->root_revision;
    else if (mapped) expected=DestinationRevision::absent();
    else if (row!=inventory->destinations.end()) expected=row->second;
    else return stale(item,item->destination,false);
  }
  auto observed=revision;
  if (item->type==T_DIR && (item->preview_destination_bound || item->relative.empty())) {
    // Our children change these fields; retain object and metadata fences.
    observed.links=expected.links; observed.size=expected.size;
    observed.mtime=expected.mtime; observed.mtime_ns=expected.mtime_ns;
    observed.ctime=expected.ctime; observed.ctime_ns=expected.ctime_ns;
  }
  if (!(expected==observed)) return stale(item,item->destination,false);
  if (!item->preview_destination_bound) { item->expected_destination=revision; item->preview_destination_bound=true; }
  return true;
}
}
