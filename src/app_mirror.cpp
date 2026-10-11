#include "app_mirror.h"
#include "app_preview_manifest.h"
#include "app_actions.h"
#include <algorithm>
#include <fcntl.h>
#include <unistd.h>

namespace app_mirror {
using app_json::Value;
namespace {
Value text(std::string_view s) { return {Value::String,std::string(s),{}, {}}; }
Value flag(bool b) { return {Value::Bool,b ? "true" : "false",{}, {}}; }
Value object() { return {Value::Object,{},{},{}}; }
std::string path(const Value& v) { auto s=app_json::unhex(v.at("bytes_hex").string()); while (s.size()>1 && s.back()=='/') s.pop_back(); return s; }
std::string canonical(std::string s) { while(s.ends_with("/.")) s.resize(s.size()-2); return s.empty() ? "/" : s; }
std::string parent(const std::string& s) { auto at=s.rfind('/'); return at==0 ? "/" : s.substr(0,at); }
std::string join(const std::string& a,const std::string& b) { return b.empty() ? a : a=="/" ? a+b : a+'/'+b; }
bool within(const std::string& p,const std::string& root) { return p==root || root=="/" || p.starts_with(root+'/'); }
bool metadata_same(const DestinationRevision& a,const DestinationRevision& b) { return a.same_object(b) && a.mode==b.mode && a.uid==b.uid && a.gid==b.gid && a.flags==b.flags; }
void send(const app_preview::Emit& emit,Value v) { auto s=app_json::serialize(v); emit(s.substr(1,s.size()-2)); }
struct Finish {
  const Value& request;
  const app_preview::Inventory& inventory;
  const Receipts& receipts;
  const app_preview::Execute& execute;
  const app_preview::Emit& emit;
  std::map<std::string,DestinationRevision> directories;
  std::map<std::string,std::string> source_directories;
  std::set<std::string> dirty;
  u64 removed=0, protected_count=0;
  bool failed=false;
  Value source_endpoint,destination_endpoint;
  std::string source_root,destination_root;
  Finish(const Value& request,const app_preview::Inventory& inventory,const Receipts& receipts,const app_preview::Execute& execute,const app_preview::Emit& emit)
    : request(request),inventory(inventory),receipts(receipts),execute(execute),emit(emit) {}
  void error(const std::string& p,std::string_view reason,bool source=false) {
    failed=true; auto v=object();
    v.object={{"type",text("error")},{"operation",text("mirror")},{"category",text("conflict")},
      {"reason",text(reason)},{"path",app_json::parse(app_json::path(p))},{"endpoint",source ? source_endpoint.at("kind") : destination_endpoint.at("kind")},
      {"side",text(source ? "source" : "destination")},{"stage",text("mirror_revalidation")},
      {"native_code",{}},{"retryable",flag(false)},{"message",text(reason)}}; send(emit,std::move(v));
  }
  Value endpoint(bool source,const std::string& p) {
    auto v=source ? source_endpoint : destination_endpoint; v.object["path"]=app_json::parse(app_json::path(p)); return v;
  }
  bool observe(bool source,const std::string& p,DestinationRevision& revision,bool absent=false) {
    auto q=object(); q.object={{"id",text("mirror-read")},{"op",text("lstat")},{"endpoint",endpoint(source,p)}};
    Value entry; bool missing=false,other_error=false;
    int rc=execute(q,[&](std::string fields) {
      auto v=app_json::parse('{'+fields+'}'); auto type=v.at("type").string();
      if (type=="entry") entry=v.at("entry");
      else if (type=="error") {
        const auto& code=v.at("native_code");
        if (absent && code.kind==Value::String && (code.text==std::to_string(ENOENT) || code.text==std::to_string(ENOTDIR))) missing=true;
        else { other_error=true; v.object["side"]=text(source ? "source" : "destination"); v.object["stage"]=text("mirror_revalidation"); send(emit,std::move(v)); }
      } else if (type=="auth_prompt" || type=="auth_response_ack" || type=="auth_response_rejected" || type=="diagnostic") send(emit,std::move(v));
    });
    if (!other_error && missing && entry.kind==Value::Null) { revision=DestinationRevision::absent(); return true; }
    if (rc || entry.kind!=Value::Object || other_error) { failed=true; return false; }
    revision=app_actions::parse_revision(entry.at("revision")); return true;
  }
  std::string readable_source(const std::string& p) { return p==canonical(source_root) ? source_root : p; }
  bool verify_sources() {
    for (const auto& [p,expected]:inventory.sources) {
      if (g_stop.load()) return false;
      DestinationRevision current;
      if (!observe(true,readable_source(p),current)) return false;
      if (!(current==expected)) { error(p,"stale_preview",true); return false; }
    }
    return true;
  }
  bool protected_path(const std::string& p) const {
    for (const auto& root:receipts.protected_paths) if (within(p,root)) return true;
    return false;
  }
  bool prepare_directories() {
    for (const auto& [relative,expected]:inventory.destination_inventory) if ((expected.mode&S_IFMT)==S_IFDIR) {
      auto p=join(destination_root,relative); DestinationRevision current;
      if (!observe(false,p,current)) return false;
      auto source=receipts.directory_sources.find(p);
      auto wanted=expected;
      if (source!=receipts.directory_sources.end()) {
        auto found=inventory.sources.find(canonical(source->second));
        if (found==inventory.sources.end()) { error(p,"unconfirmed_directory_metadata"); return false; }
        if (request.at("options").at("preserve_permissions").boolean()) wanted.mode=found->second.mode;
        if (!metadata_same(wanted,current)) { error(p,"stale_preview"); return false; }
      } else if (!(current==expected) && !protected_path(p)) { error(p,"stale_preview"); return false; }
      directories.emplace(p,current);
    }
    for (const auto& [relative,target]:inventory.targets) {
      auto p=join(source_root,relative); auto found=inventory.sources.find(canonical(p));
      if (found!=inventory.sources.end() && (found->second.mode&S_IFMT)==S_IFDIR) source_directories.emplace(target,p);
    }
    return true;
  }
  bool source_still_absent(const std::string& target) {
    auto base=parent(target);
    while (!source_directories.count(base) && base!=destination_root) base=parent(base);
    auto found=source_directories.find(base);
    if (found==source_directories.end()) { error(target,"unconfirmed_source_scope",true); return false; }
    auto p=found->second;
    auto guard=p;
    for (;;) {
      auto expected=inventory.sources.find(canonical(guard));
      if (expected!=inventory.sources.end()) {
        DestinationRevision current;
        if (!observe(true,guard,current)) return false;
        if (!(current==expected->second)) { error(guard,"stale_preview",true); return false; }
      }
      if (canonical(guard)==canonical(source_root)) break;
      guard=parent(guard);
      if (!within(canonical(guard),canonical(source_root))) { error(guard,"unconfirmed_source_scope",true); return false; }
    }
    auto suffix=target.substr(base.size()+(base=="/" ? 0 : 1)); size_t begin=0;
    for (;;) {
      auto end=suffix.find('/',begin); auto component=suffix.substr(begin,end==suffix.npos ? suffix.size()-begin : end-begin);
      p=join(p,component); DestinationRevision current;
      if (!observe(true,p,current,true)) return false;
      if (!current.exists) return true;
      if (!inventory.sources.count(canonical(p))) { error(p,"source_entry_appeared",true); return false; }
      if (end==suffix.npos) { error(p,"source_entry_appeared",true); return false; }
      begin=end+1;
    }
  }
  bool remove(const std::string& relative,const DestinationRevision& original) {
    auto target=join(destination_root,relative);
    if (protected_path(target)) { ++protected_count; return true; }
    if (!source_still_absent(target)) return false;
    auto p=parent(target); auto expected=directories.find(p);
    if (expected==directories.end()) { error(p,"unconfirmed_destination_parent"); return false; }
    DestinationRevision current_parent,current;
    if (!observe(false,p,current_parent) || !observe(false,target,current)) return false;
    auto directory=directories.find(target); const auto& wanted=directory==directories.end() ? original : directory->second;
    if (!(current_parent==expected->second) || !(current==wanted)) { error(target,"stale_preview"); return false; }
    auto q=object(),item=object();
    item.object={{"name",app_json::parse(app_json::path(target.substr(target.rfind('/')+1)))},{"expected_revision",app_preview::revision_value(wanted)}};
    q.object={{"id",text("mirror-delete")},{"op",text("delete")},{"endpoint",endpoint(false,p)},
      {"parent_revision",app_preview::revision_value(current_parent)},{"recursive",flag(false)},
      {"items",{Value::Array,{}, {item},{}}}};
    int rc=execute(q,emit);
    if (rc) { failed=true; return false; }
    ++removed; dirty.insert(p);
    DestinationRevision after;
    if (!observe(false,p,after)) return false;
    if (!metadata_same(current_parent,after)) { error(p,"stale_preview"); return false; }
    expected->second=after; return true;
  }
  bool restore_times() {
    if (!request.at("options").at("preserve_times").boolean()) return true;
    std::vector<std::string> paths(dirty.begin(),dirty.end());
    std::sort(paths.begin(),paths.end(),[](const auto& a,const auto& b) { return std::count(a.begin(),a.end(),'/')>std::count(b.begin(),b.end(),'/'); });
    for (const auto& p:paths) {
      auto source=receipts.directory_sources.find(p);
      if (source==receipts.directory_sources.end()) continue;
      auto src=inventory.sources.find(canonical(source->second));
      if (src==inventory.sources.end()) { error(p,"unconfirmed_directory_metadata"); return false; }
      DestinationRevision current,source_current;
      if (!observe(false,p,current) || !observe(true,source->second,source_current)) return false;
      if (!(current==directories.at(p)) || !(source_current==src->second)) { error(p,"stale_preview"); return false; }
      auto time=object(); time.object={{"seconds",text(std::to_string(src->second.mtime))},{"nanoseconds",text(std::to_string(src->second.mtime_ns))}};
      auto q=object();
      if (p==destination_root) q.object={{"id",text("mirror-times")},{"op",text("_mirror_root_times")},{"endpoint",endpoint(false,p)},{"expected_revision",app_preview::revision_value(current)},{"mtime",time}};
      else {
        auto folder=parent(p); DestinationRevision parent_revision;
        if (!observe(false,folder,parent_revision)) return false;
        auto item=object(); item.object={{"name",app_json::parse(app_json::path(p.substr(p.rfind('/')+1)))},{"expected_revision",app_preview::revision_value(current)}};
        q.object={{"id",text("mirror-times")},{"op",text("metadata")},{"endpoint",endpoint(false,folder)},
          {"parent_revision",app_preview::revision_value(parent_revision)},{"items",{Value::Array,{}, {item},{}}},{"mtime",time}};
      }
      if (execute(q,emit)) { failed=true; return false; }
    }
    return true;
  }
  bool verify_destination(const std::string& p,unsigned depth=0) {
    if (depth>=256) { error(p,"mirror_inventory_limit"); return false; }
    auto q=object(); q.object={{"id",text("mirror-list")},{"op",text("list")},{"endpoint",endpoint(false,p)}};
    std::vector<Value> entries;
    int rc=execute(q,[&](std::string fields) {
      auto v=app_json::parse('{'+fields+'}');
      if (v.at("type").string()=="entries") for (const auto& entry:v.at("entries").array) entries.push_back(entry);
      else send(emit,std::move(v));
    });
    if (rc || entries.size()>100000) { failed=true; return false; }
    for (const auto& entry:entries) {
      auto target=join(p,app_json::unhex(entry.at("name").at("bytes_hex").string()));
      if (protected_path(target)) continue;
      if (!receipts.outputs.count(target)) { error(target,"destination_entry_appeared"); return false; }
      if (entry.at("type").string()=="directory" && !verify_destination(target,depth+1)) return false;
    }
    return true;
  }
  int run() {
    source_endpoint=request.at("sources").array.front().at("endpoint"); destination_endpoint=request.at("destination");
    source_root=path(source_endpoint.at("path")); destination_root=path(destination_endpoint.at("path"));
    auto phase=object(); phase.object={{"type",text("phase")},{"phase",text("revalidating_mirror")}}; send(emit,std::move(phase));
    bool ready=verify_sources() && prepare_directories();
    if (ready) {
      phase.object["phase"]=text("deleting_mirror"); send(emit,phase);
      std::vector<std::pair<std::string,DestinationRevision>> deletions(inventory.deletions.begin(),inventory.deletions.end());
      std::sort(deletions.begin(),deletions.end(),[](const auto& a,const auto& b) { return std::count(a.first.begin(),a.first.end(),'/')>std::count(b.first.begin(),b.first.end(),'/'); });
      for (const auto& [p,revision]:deletions) { if (g_stop.load() || !remove(p,revision)) break; }
      if (!failed && !g_stop.load()) ready=restore_times() && verify_sources() && verify_destination(destination_root);
    }
    auto summary=object(); summary.object={{"type",text("mirror_summary")},{"deleted_items",text(std::to_string(removed))},
      {"protected_items",text(std::to_string(protected_count))},{"complete",flag(ready && !failed && !g_stop.load())},
      {"deletion_authorized",flag(true)},{"snapshot_atomic",flag(false)}}; send(emit,std::move(summary));
    return g_stop.load() ? RERR_SIGNAL : ready && !failed ? 0 : RERR_PARTIAL;
  }
};
}
void Receipts::accept(const Value& event) {
  auto type=event.at("type").string();
  if (type!="item_mapping" && type!="item_result") return;
  auto relative=app_json::unhex(event.at("item_id").string()); auto original=inventory.targets.find(relative);
  if (original==inventory.targets.end()) return;
  if (type=="item_mapping" || event.at("status").string()=="skipped") protected_paths.insert(original->second);
  if (type=="item_result" && event.at("destination_path").kind==Value::Object) {
    auto p=path(event.at("destination_path")); outputs.insert(p);
    if (event.at("status").string()=="success" && event.at("entry_type").string()=="directory") directory_sources[p]=path(event.at("source_path"));
  }
}
int finish(const Value& request,const app_preview::Inventory& inventory,const Receipts& receipts,const app_preview::Execute& execute,const app_preview::Emit& emit) {
  return Finish{request,inventory,receipts,execute,emit}.run();
}
void validate_root_times(const Value& request) {
  if (request.kind!=Value::Object || request.object.size()!=5) throw std::runtime_error("invalid mirror root metadata fields");
  for (const char* key:{"id","op","endpoint","expected_revision","mtime"}) (void)request.at(key);
  auto revision=app_actions::parse_revision(request.at("expected_revision"));
  if (!revision.exists || (revision.mode&S_IFMT)!=S_IFDIR) throw std::runtime_error("mirror root metadata requires a real directory revision");
  auto translated=object(); translated.object={{"id",request.at("id")},{"op",text("metadata")},{"endpoint",request.at("endpoint")},
    {"parent_revision",request.at("expected_revision")},{"mtime",request.at("mtime")},
    {"items",app_json::parse("[{\"name\":{\"bytes_hex\":\"726f6f74\"},\"expected_revision\":"+app_json::serialize(request.at("expected_revision"))+"}]")}};
  (void)app_actions::parse(translated,path(request.at("endpoint").at("path")));
}
int root_times(const Value& request,const std::function<bool()>& lease_valid,const app_preview::Emit& emit) {
  auto p=path(request.at("endpoint").at("path")); auto expected=app_actions::parse_revision(request.at("expected_revision"));
  auto fail=[&](int code,std::string_view reason) {
    auto v=object(); v.object={{"type",text("error")},{"operation",text("mirror")},{"category",text(code ? "metadata" : "conflict")},
      {"reason",text(reason)},{"path",request.at("endpoint").at("path")},{"endpoint",text("local")},{"side",text("destination")},
      {"stage",text("mirror_metadata")},{"native_code",code ? text(std::to_string(code)) : Value{}},{"retryable",flag(false)},{"message",text(reason)}};
    send(emit,std::move(v)); return RERR_PARTIAL;
  };
  if (!lease_valid()) return fail(0,"stale_preview");
  int fd=open(p.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
  if (fd<0) return fail(errno,"open_mirror_root_metadata");
  struct stat held,named;
  bool valid=fstat(fd,&held)==0 && lstat(p.c_str(),&named)==0 && expected==DestinationRevision::from(held) && expected==DestinationRevision::from(named) && lease_valid();
  if (!valid) { close(fd); return fail(0,"stale_preview"); }
  const auto& time=request.at("mtime");
  timespec times[2]={{0,UTIME_OMIT},{std::stoll(time.at("seconds").string()),std::stol(time.at("nanoseconds").string())}};
  int rc=futimens(fd,times),code=errno; close(fd);
  if (rc) return fail(code,"mirror_root_times");
  if (!lease_valid()) return fail(0,"stale_preview");
  auto v=object(); v.object={{"type",text("mirror_metadata_result")},{"path",request.at("endpoint").at("path")},{"endpoint",text("local")},{"status",text("success")}};
  send(emit,std::move(v)); return 0;
}
}
