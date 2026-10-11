#include "app_preview.h"
#include "app_actions.h"
#include "fs.h"
#define XXH_INLINE_ALL
#include <xxhash.h>
#include <set>

namespace app_preview {
using app_json::Value;
namespace {
Value string(std::string_view s) { return {Value::String,std::string(s),{}, {}}; }
Value boolean(bool b) { return {Value::Bool,b ? "true" : "false",{}, {}}; }
Value object() { return {Value::Object,{},{},{}}; }
Value number(u64 n) { return string(std::to_string(n)); }
std::string path(const Value& endpoint) { auto p = app_json::unhex(endpoint.at("path").at("bytes_hex").string()); while (p.size()>1 && p.back()=='/') p.pop_back(); return p; }
std::string parent(const std::string& p) { auto at=p.rfind('/'); return at==0 ? "/" : p.substr(0,at); }
std::string name(const std::string& p) { return p.substr(p.rfind('/')+1); }
std::string join(const std::string& p,const std::string& n) { return n.empty() ? p : p.empty() ? n : p=="/" ? p+n : p+'/'+n; }
Value at(Value endpoint,const std::string& p) { endpoint.object["path"] = app_json::parse(app_json::path(p)); return endpoint; }
void send(const Emit& emit,Value event) { auto s=app_json::serialize(event); emit(s.substr(1,s.size()-2)); }
struct Node { Value endpoint,entry; std::string relative; bool source; };
struct Preview {
  const Value& request;
  const Execute& execute;
  const Emit& emit;
  std::map<std::string,Node> source,destination;
  std::map<std::string,Value> rules;
  std::map<std::string,u64> totals;
  std::vector<Value> rows;
  bool failed=false, names_unknown=false;
  std::string mode,policy;
  u64 selected_bytes=0;
  Value sizes{Value::Array,{}, {},{}}, root_preflight;
  Preview(const Value& request,const Execute& execute,const Emit& emit) : request(request),execute(execute),emit(emit) {}
  void error(const Value& endpoint,std::string_view reason,bool src) {
    failed=true;
    auto event=object(); event.object={{"type",string("error")},{"operation",string("preview")},
      {"category",string(reason.starts_with("unsupported_") ? "unsupported_feature" : reason=="preview_inventory_limit" || reason=="contents_requires_directory" || reason=="preview_budget_overflow" ? "selection" : "conflict")},
      {"endpoint",endpoint.at("kind")},{"path",endpoint.at("path")},{"side",string(src ? "source" : "destination")},
      {"stage",string("preview")},{"native_code",{}},{"retryable",boolean(false)},{"reason",string(reason)},{"message",string(reason)}};
    send(emit,std::move(event));
  }
  Value command(std::string_view op,const Value& endpoint) {
    auto v=object(); v.object={{"id",string("preview-read")},{"op",string(op)},{"endpoint",endpoint}}; return v;
  }
  void forward(Value event,bool src) {
    auto type=event.at("type").string();
    if (type=="error") { failed=true; event.object["side"]=string(src ? "source" : "destination"); event.object["stage"]=string("preview"); send(emit,std::move(event)); }
    else if (type=="auth_prompt" || type=="auth_response_ack" || type=="auth_response_rejected" || type=="diagnostic") send(emit,std::move(event));
  }
  bool entry(const Value& endpoint,Value& value,bool src) {
    int rc=execute(command("lstat",endpoint),[&](std::string fields) {
      auto event=app_json::parse('{'+fields+'}');
      if (event.at("type").string()=="entry") value=event.at("entry"); else forward(std::move(event),src);
    });
    if (rc || value.kind!=Value::Object) { failed=true; return false; } return true;
  }
  bool preflight(const Value& endpoint,Value& value,const Value& space={}) {
    auto v=command("preflight",endpoint); if (space.kind!=Value::Null) v.object["space"]=space;
    int rc=execute(v,[&](std::string fields) {
      auto event=app_json::parse('{'+fields+'}');
      if (event.at("type").string()=="destination_preflight") value=std::move(event); else forward(std::move(event),false);
    });
    if (rc || value.kind!=Value::Object) { failed=true; return false; } return true;
  }
  bool scan(const Value& endpoint,const std::string& relative,bool src,unsigned depth=0,const Value* observed=nullptr) {
    if (g_stop.load()) { failed=true; return false; }
    if (source.size()+destination.size()>=100000 || depth>=256) { error(endpoint,"preview_inventory_limit",src); return false; }
    Value found=observed ? *observed : Value{};
    if (!observed && !entry(endpoint,found,src)) return false;
    auto type=found.at("type").string();
    auto& nodes=src ? source : destination;
    if (!nodes.emplace(relative,Node{endpoint,found,relative,src}).second) { error(endpoint,"overlapping_preview_selections",src); return false; }
    if (src && type!="file" && type!="directory" && type!="symlink") { error(endpoint,"unsupported_preview_source",true); return false; }
    if (type!="directory") return true;
    if (!src) { Value value; if (!preflight(endpoint,value)) return false; rules[relative]=std::move(value); }
    std::vector<Value> children; bool oversized=false;
    int rc=execute(command("list",endpoint),[&](std::string fields) {
      auto event=app_json::parse('{'+fields+'}');
      if (event.at("type").string()=="entries") for (const auto& child:event.at("entries").array) {
        if (children.size()+source.size()+destination.size()>=100000) oversized=true; else children.push_back(child);
      } else forward(std::move(event),src);
    });
    if (rc) { failed=true; return false; }
    if (oversized) { error(endpoint,"preview_inventory_limit",src); return false; }
    bool complete=true;
    for (const auto& child:children) {
      auto n=app_json::unhex(child.at("name").at("bytes_hex").string());
      if (n.empty() || n=="." || n==".." || n.find_first_of("/\0",0,2)!=n.npos) throw std::runtime_error("unsafe preview inventory name");
      if (!scan(at(endpoint,join(path(endpoint),n)),join(relative,n),src,depth+1,&child)) complete=false;
    }
    Value after;
    if (!entry(endpoint,after,src) || !(app_actions::parse_revision(found.at("revision"))==app_actions::parse_revision(after.at("revision")))) {
      error(endpoint,"preview_inventory_changed",src); complete=false;
    }
    return complete;
  }
  bool stable() {
    bool complete=true;
    for (auto* nodes:{&source,&destination}) for (const auto& [key,node]:*nodes) {
      if (g_stop.load()) { failed=true; return false; }
      Value found;
      if (!entry(node.endpoint,found,node.source) || !(app_actions::parse_revision(node.entry.at("revision"))==app_actions::parse_revision(found.at("revision")))) {
        error(node.endpoint,"preview_inventory_changed",node.source); complete=false;
      }
    }
    return complete;
  }
  std::function<std::string(std::string_view)> keyer(const std::string& relative) {
    auto it=rules.find(relative);
    if (it==rules.end()) { names_unknown=true; return observed_name_keyer(false,false); }
    const auto& names=it->second.at("names"); const auto& sensitive=names.at("case_sensitive"); const auto& normalize=names.at("unicode_normalization");
    if (sensitive.kind==Value::Null || normalize.kind==Value::Null) names_unknown=true;
    auto type=it->second.at("filesystem_type");
    bool full=!(type.kind==Value::String && (type.text=="msdos" || type.text=="exfat" || type.text=="19780" || type.text=="538247665"));
    return observed_name_keyer(sensitive.kind==Value::Bool && !sensitive.boolean(),normalize.kind==Value::Bool && normalize.boolean(),full);
  }
  bool metadata_differs(const Value& src,const Value& dst) {
    const auto& options=request.at("options");
    return (options.at("preserve_permissions").boolean() && src.at("mode").string()!=dst.at("mode").string()) ||
      (options.at("preserve_times").boolean() && (src.at("mtime_seconds").string()!=dst.at("mtime_seconds").string() || src.at("mtime_nanoseconds").string()!=dst.at("mtime_nanoseconds").string()));
  }
  void row(const Node* src,const Node* dst,const std::string& target,std::string action,std::string reason,bool conditional=false) {
    auto v=object(); auto id=src ? src->relative : dst->relative;
    v.object={{"type",string("preview_item")},{"item_id",string(app_json::hex(id))},{"path",app_json::parse(app_json::path(id))},
      {"source_path",src ? src->endpoint.at("path") : Value{}},{"destination_path",app_json::parse(app_json::path(target))},
      {"source_endpoint",request.at("sources").array.front().at("endpoint").at("kind")},{"destination_endpoint",request.at("destination").at("kind")},
      {"source_revision",src ? src->entry.at("revision") : Value{}},{"destination_revision",dst ? dst->entry.at("revision") : app_json::parse("{\"exists\":false}")},
      {"entry_type",src ? src->entry.at("type") : dst->entry.at("type")},{"action",string(action)},{"reason",string(reason)},
      {"conditional",boolean(conditional)},{"execution_recheck_required",boolean(true)},
      {"logical_bytes",src && src->entry.at("type").string()=="file" ? src->entry.at("size") : number(0)}};
    rows.push_back(std::move(v));
  }
  void compare() {
    std::set<std::string> matched; std::map<std::string,std::string> targets, blocked;
    std::map<std::string,std::map<std::string,std::string>> planned_names;
    std::set<std::string> collisions;
    auto root=path(request.at("destination"));
    std::map<std::string,std::function<std::string(std::string_view)>> keyers;
    auto get_keyer=[&](const std::string& folder) -> const std::function<std::string(std::string_view)>& {
      auto found=keyers.find(folder); if (found==keyers.end()) found=keyers.emplace(folder,keyer(folder)).first; return found->second;
    };
    std::map<std::string,std::map<std::string,const Node*>> children;
    for (const auto& [candidate,value]:destination) if (!candidate.empty()) {
      auto folder=parent(candidate); if (folder==candidate) folder="";
      children[folder].emplace(get_keyer(folder)(name(candidate)),&value);
    }
    for (const auto& [relative,src]:source) {
      auto folder=relative.empty() ? "" : parent(relative);
      if (folder==relative) folder="";
      std::string actual_parent=targets.count(folder) ? targets[folder] : folder;
      const auto& make_key=get_keyer(actual_parent); std::string selected=relative.empty() ? "" : join(actual_parent,name(relative));
      const Node* dst=nullptr;
      if (relative.empty()) dst=&destination.at("");
      else {
        auto folder=children.find(actual_parent);
        if (folder!=children.end()) { auto child=folder->second.find(make_key(name(relative))); if (child!=folder->second.end()) { dst=child->second; selected=dst->relative; } }
      }
      targets[relative]=selected;
      if (dst) matched.insert(dst->relative);
      bool conditional=false; std::string action,reason;
      auto ancestor=blocked.find(folder);
      if (ancestor!=blocked.end()) { action=ancestor->second=="skip" ? "skip" : "conflict"; reason="ancestor_conflict"; conditional=action=="conflict"; blocked[relative]=ancestor->second; }
      else {
        auto key=make_key(name(relative)); auto& planned=planned_names[actual_parent];
        bool collision=!relative.empty() && planned.count(key) && planned[key]!=relative;
        if (collision) { collisions.insert(planned[key]); collisions.insert(relative); }
        planned[key]=relative;
        auto type=src.entry.at("type").string();
        if (type!="file" && type!="directory" && type!="symlink") { action="blocked"; reason="unsupported_source"; }
        else if (collision) { action="conflict"; reason="planned_name_collision"; conditional=true; blocked[relative]="conflict"; }
        else if (dst && src.endpoint.at("kind").string()==request.at("destination").at("kind").string() && type!="directory" && app_actions::parse_revision(src.entry.at("revision")).same_object(app_actions::parse_revision(dst->entry.at("revision")))) {
          action="conflict"; reason="source_destination_alias"; conditional=true;
        } else if (dst && policy=="skip" && !(type=="directory" && dst->entry.at("type").string()=="directory")) {
          action="skip"; reason="existing_destination"; blocked[relative]="skip";
        } else if (dst && (type!=dst->entry.at("type").string() || (policy=="ask" && type!="directory" && !(type=="symlink" && app_json::serialize(src.entry.at("link_target"))==app_json::serialize(dst->entry.at("link_target")))))) {
          action="conflict"; reason=type!=dst->entry.at("type").string() ? "type_conflict" : "existing_destination"; conditional=true; blocked[relative]="conflict";
        } else if (type=="file") { action="copy"; reason=dst ? "replace_regular_file" : "new_regular_file"; }
        else if (type=="directory") { action=dst ? metadata_differs(src.entry,dst->entry) ? "metadata_update" : "unchanged" : "create_directory"; reason=dst ? "directory_merge" : "new_directory"; }
        else { bool same=dst && app_json::serialize(src.entry.at("link_target"))==app_json::serialize(dst->entry.at("link_target"));
          action=same ? metadata_differs(src.entry,dst->entry) ? "metadata_update" : "unchanged" : "copy"; reason=same ? "same_link_target" : dst ? "replace_symlink" : "new_symlink"; }
      }
      row(&src,dst,join(root,selected),action,reason,conditional);
    }
    for (const auto& [relative,dst]:destination) if (!relative.empty() && !matched.count(relative))
      row(nullptr,&dst,path(dst.endpoint),mode=="mirror" ? "delete" : "skip",mode=="mirror" ? "destination_only" : "outside_selected_copy");
    for (auto& value:rows) if (value.at("source_path").kind!=Value::Null) {
      auto relative=app_json::unhex(value.at("path").at("bytes_hex").string()); auto p=relative;
      while (!p.empty()) {
        if (collisions.count(p)) {
          value.object["action"]=string("conflict"); value.object["reason"]=string(p==relative ? "planned_name_collision" : "ancestor_conflict"); value.object["conditional"]=boolean(true); break;
        }
        auto next=parent(p); if (next==p) break; p=std::move(next);
      }
    }
    // Child publication/deletion can require restoring a directory time even
    // when the initial source/destination metadata already matches.
    std::set<std::string> mutations;
    for (const auto& value:rows) {
      const auto action=value.at("action").string();
      if (action=="copy" || action=="create_directory" || action=="conflict" || action=="delete") mutations.insert(app_json::unhex(value.at("destination_path").at("bytes_hex").string()));
    }
    if (request.at("options").at("preserve_times").boolean()) for (auto& value:rows) {
      if (value.at("source_path").kind==Value::Null || value.at("entry_type").string()!="directory" || value.at("action").string()!="unchanged") continue;
      auto p=app_json::unhex(value.at("destination_path").at("bytes_hex").string());
      auto prefix=p=="/" ? p : p+'/'; auto child=mutations.lower_bound(prefix);
      if (child!=mutations.end() && child->starts_with(prefix)) {
        value.object["action"]=string("metadata_update"); value.object["reason"]=string("directory_children_may_change_times");
      }
    }
    for (const auto& value:rows) {
      auto action=value.at("action").string(); ++totals[action];
      if (value.at("source_path").kind!=Value::Null && value.at("entry_type").string()=="file" && (action=="copy" || action=="conflict")) {
        auto revision=app_actions::parse_revision(value.at("source_revision"));
        if (revision.size<0 || (u64)revision.size>UINT64_MAX-selected_bytes) error(request.at("sources").array.front().at("endpoint"),"preview_budget_overflow",true);
        else { selected_bytes+=(u64)revision.size; sizes.array.push_back(number((u64)revision.size)); }
      }
    }
  }
  std::string token() {
    XXH3_state_t hash; XXH3_128bits_reset(&hash);
    auto feed=[&](const Value& v) { auto s=app_json::serialize(v); u64 length=s.size(); XXH3_128bits_update(&hash,&length,sizeof length); XXH3_128bits_update(&hash,s.data(),s.size()); };
    auto binding=request; binding.object.erase("id"); binding.object.erase("op");
    auto hide=[&](Value& endpoint) { if (endpoint.object.count("connection")) { auto& connection=endpoint.object["connection"].object; connection.erase("identity_file"); connection.erase("known_hosts_file"); } };
    hide(binding.object["destination"]); for (auto& selected:binding.object["sources"].array) hide(selected.object["endpoint"]);
    feed(string("xsync-preview-1")); feed(binding);
    for (auto* nodes:{&source,&destination}) for (const auto& [key,node]:*nodes) {
      feed(string(node.source ? "source" : "destination")); feed(string(app_json::hex(key))); feed(node.endpoint.at("path")); feed(node.entry.at("revision")); feed(node.entry.at("link_target"));
    }
    for (const auto& [relative,observation]:rules) { feed(string(app_json::hex(relative))); feed(observation.at("names")); feed(observation.at("metadata")); }
    XXH128_canonical_t canonical; XXH128_canonicalFromHash(&canonical,XXH3_128bits_digest(&hash));
    return app_json::hex(std::string_view((char*)canonical.digest,sizeof canonical.digest));
  }
  int run(const Value& expected,Inventory* inventory) {
    mode=request.at("mode").string(); policy=request.at("options").at("on_conflict").string();
    auto phase=object(); phase.object={{"type",string("phase")},{"phase",string("scanning_preview")}}; send(emit,std::move(phase));
    Value root;
    if (!entry(request.at("destination"),root,false) || root.at("type").string()!="directory") { error(request.at("destination"),"preview_requires_destination_directory",false); }
    else scan(request.at("destination"),"",false,0,&root);
    for (const auto& selected:request.at("sources").array) {
      auto p=path(selected.at("endpoint")); bool contents=selected.at("mode").string()=="contents";
      auto relative=contents ? "" : selected.object.count("destination_name") ? app_json::unhex(selected.at("destination_name").at("bytes_hex").string()) : name(p);
      Value found;
      if (!entry(selected.at("endpoint"),found,true)) continue;
      if (contents && found.at("type").string()!="directory") { error(selected.at("endpoint"),"contents_requires_directory",true); continue; }
      scan(selected.at("endpoint"),relative,true,0,&found);
    }
    if (!destination.empty()) {
      auto dest_revision=app_actions::parse_revision(destination.at("").entry.at("revision"));
      for (const auto& [key,node]:source) if (node.endpoint.at("kind").string()==request.at("destination").at("kind").string() && node.entry.at("type").string()=="directory" && app_actions::parse_revision(node.entry.at("revision")).same_object(dest_revision))
        error(node.endpoint,"destination_inside_source",true);
      compare();
    }
    stable();
    Value guard; std::string digest;
    if (!failed) { digest=token(); guard=object(); guard.object={{"version",string("1")},{"mode",string(mode)},{"token",string(digest)}}; }
    if (expected.kind!=Value::Null) {
      if (failed || app_json::serialize(expected)!=app_json::serialize(guard)) { error(request.at("destination"),"stale_preview",false); return RERR_FILESELECT; }
      if (inventory) {
        inventory->destination_root=path(request.at("destination"));
        inventory->root_revision=app_actions::parse_revision(destination.at("").entry.at("revision"));
        for (const auto& [relative,node]:destination) inventory->destination_inventory.emplace(relative,app_actions::parse_revision(node.entry.at("revision")));
        for (const auto& [relative,node]:source) {
          auto p=path(node.endpoint); while (p.ends_with("/.")) p.resize(p.size()-2); if (p.empty()) p="/";
          inventory->sources.emplace(std::move(p),app_actions::parse_revision(node.entry.at("revision")));
        }
        for (const auto& row:rows) {
          auto relative=app_json::unhex(row.at("path").at("bytes_hex").string());
          if (row.at("source_path").kind!=Value::Null) {
            inventory->destinations.emplace(relative,app_actions::parse_revision(row.at("destination_revision")));
            inventory->targets.emplace(relative,app_json::unhex(row.at("destination_path").at("bytes_hex").string()));
          } else if (row.at("action").string()=="delete") inventory->deletions.emplace(relative,app_actions::parse_revision(row.at("destination_revision")));
        }
      }
      auto event=object(); event.object={{"type",string("preview_revalidated")},{"mode",string(mode)},{"token",string(digest)},{"snapshot_atomic",boolean(false)},{"deletion_authorized",boolean(false)}}; send(emit,std::move(event)); return 0;
    }
    for (auto& value:rows) send(emit,std::move(value));
    if (!failed) {
      auto space=object(); space.object={{"regular_file_sizes",sizes},{"jobs",request.at("options").at("jobs")}};
      if (preflight(request.at("destination"),root_preflight,space)) {
        stable();
        auto& budget=root_preflight.object["space"].object; budget["inputs_verified"]=boolean(true); budget["source_content_verified"]=boolean(false);
        budget["retained_logical_bytes"]=Value{}; budget["coexisting_data_logical_bytes"]=Value{}; budget["retained_data_inventory_complete"]=boolean(false);
        if (!failed) send(emit,root_preflight);
      }
    }
    auto summary=object(),counts=object(); for (const auto& [kind,total]:totals) counts.object[kind]=number(total);
    summary.object={{"type",string("preview_summary")},{"mode",string(mode)},{"direction",string(request.at("destination").at("kind").string()=="ssh" ? "push" : request.at("sources").array.front().at("endpoint").at("kind").string()=="ssh" ? "pull" : "local")},
      {"complete",boolean(!failed)},{"counts",counts},{"regular_data_upper_bound_bytes",number(selected_bytes)},{"names_require_execution_recheck",boolean(names_unknown)},
      {"source_entries",number(source.size())},{"destination_entries",number(destination.size())},{"token_algorithm",string("xxh3-128")},
      {"token",failed ? Value{} : string(digest)},{"execution_supported",boolean(!failed && mode=="selected_copy")},{"execution_guard",!failed && mode=="selected_copy" ? guard : Value{}},
      {"deletion_authorized",boolean(false)},{"snapshot_atomic",boolean(false)},{"source_content_verified",boolean(false)}};
    send(emit,std::move(summary)); return g_stop.load() ? RERR_SIGNAL : failed ? RERR_PARTIAL : 0;
  }
};
}
int run(const Value& request,const Execute& execute,const Emit& emit,const Value& expected_guard,Inventory* inventory) { return Preview{request,execute,emit}.run(expected_guard,inventory); }
}
