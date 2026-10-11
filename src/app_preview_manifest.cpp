#include "app_preview_manifest.h"
#include "app_actions.h"

namespace app_preview {
namespace {
using app_json::Value;
using app_json::quote;
u64 number(const Value& value,u64 maximum) {
  auto s=value.string(); u64 n=0;
  if (s.empty() || s.size()>20) throw std::runtime_error("invalid preview manifest integer");
  for (char c:s) {
    if (c<'0' || c>'9' || n>maximum/10 || (n==maximum/10 && (u64)(c-'0')>maximum%10)) throw std::runtime_error("invalid preview manifest integer");
    n=n*10+c-'0';
  }
  return n;
}
std::string revision(const DestinationRevision& r) {
  if (!r.known) return "null";
  if (!r.exists) return "{\"exists\":false}";
  return "{\"exists\":true,\"device\":"+quote(std::to_string(r.device))+",\"inode\":"+quote(std::to_string(r.inode))+
    ",\"links\":"+quote(std::to_string(r.links))+",\"mode\":"+quote(std::to_string(r.mode))+",\"uid\":"+quote(std::to_string(r.uid))+
    ",\"gid\":"+quote(std::to_string(r.gid))+",\"flags\":"+quote(std::to_string(r.flags))+",\"size\":"+quote(std::to_string(r.size))+
    ",\"mtime_seconds\":"+quote(std::to_string(r.mtime))+",\"mtime_nanoseconds\":"+quote(std::to_string(r.mtime_ns))+
    ",\"ctime_seconds\":"+quote(std::to_string(r.ctime))+",\"ctime_nanoseconds\":"+quote(std::to_string(r.ctime_ns))+"}";
}
void exact(const Value& value,std::initializer_list<const char*> keys) {
  if (value.kind!=Value::Object || value.object.size()!=keys.size()) throw std::runtime_error("invalid preview manifest fields");
  for (const char* key:keys) if (!value.object.count(key)) throw std::runtime_error("invalid preview manifest fields");
}
}
Value revision_value(const DestinationRevision& value) { return app_json::parse(revision(value)); }
ManifestSender::ManifestSender(const Inventory& value,bool receiving) : inventory(value),receiver(receiving),
  position((receiving ? inventory.destinations : inventory.sources).begin()) {}
Value ManifestSender::header() const {
  auto count=(receiver ? inventory.destinations : inventory.sources).size();
  if (!count || count>100000) throw std::runtime_error("invalid preview manifest size");
  return app_json::parse("{\"version\":\"1\",\"entries\":"+quote(std::to_string(count))+
    ",\"root_revision\":"+(receiver ? revision(inventory.root_revision) : "null")+"}");
}
bool ManifestSender::complete() const { return position==(receiver ? inventory.destinations : inventory.sources).end(); }
std::string ManifestSender::next(u64 requested_sequence) {
  if (requested_sequence!=sequence+1 || complete()) throw std::runtime_error("invalid preview manifest acknowledgement");
  std::string rows; size_t count=0;
  const auto& entries=receiver ? inventory.destinations : inventory.sources;
  while (position!=entries.end() && count<1024) {
    auto row="{\"path\":"+app_json::path(position->first)+",\"revision\":"+revision(position->second)+"}";
    if (row.size()>768*1024) throw std::runtime_error("preview manifest row exceeds limit");
    if (!rows.empty() && rows.size()+row.size()+1>768*1024) break;
    if (!rows.empty()) rows+=',';
    rows+=row; ++position; ++count;
  }
  return "{\"sequence\":"+quote(std::to_string(++sequence))+",\"rows\":["+rows+"]}";
}
ManifestReceiver::ManifestReceiver(bool receiving,const Value& header,std::string root) : receiver(receiving) {
  exact(header,{"version","entries","root_revision"});
  if (header.at("version").string()!="1") throw std::runtime_error("unsupported preview manifest version");
  entries=number(header.at("entries"),100000);
  if (!entries) throw std::runtime_error("empty preview manifest");
  if (receiver) {
    inventory.destination_root=std::move(root);
    inventory.root_revision=app_actions::parse_revision(header.at("root_revision"));
    if (!inventory.root_revision.exists || (inventory.root_revision.mode&S_IFMT)!=S_IFDIR) throw std::runtime_error("preview manifest requires a real destination root");
  } else if (header.at("root_revision").kind!=Value::Null) throw std::runtime_error("sender preview manifest cannot bind a destination root");
}
void ManifestReceiver::append(const Value& chunk,size_t frame_bytes) {
  exact(chunk,{"sequence","rows"});
  const auto& rows=chunk.at("rows");
  if (complete() || number(chunk.at("sequence"),100000)!=sequence+1 || rows.kind!=Value::Array || rows.array.empty() || rows.array.size()>1024 || rows.array.size()>entries-received)
    throw std::runtime_error("invalid preview manifest chunk");
  if (frame_bytes>1048576 || frame_bytes>(1ULL<<32)-bytes) throw std::runtime_error("preview manifest exceeds byte limit");
  bytes+=frame_bytes;
  auto& entries=receiver ? inventory.destinations : inventory.sources;
  for (const auto& row:rows.array) {
    exact(row,{"path","revision"});
    const auto& encoded=row.at("path");
    // Human-readable path display is optional observation, never an identity.
    if (encoded.kind!=Value::Object || !encoded.object.count("bytes_hex") || encoded.object.size()>2 || (encoded.object.size()==2 && (!encoded.object.count("display") || encoded.at("display").kind!=Value::String))) throw std::runtime_error("invalid preview manifest path");
    auto path=app_json::unhex(encoded.at("bytes_hex").string());
    if (path.size()>(receiver ? 8192u : 4096u) || path.find('\0')!=path.npos || (!receiver && (path.empty() || path.front()!='/')) || (receiver && !path.empty() && path.front()=='/')) throw std::runtime_error("unsafe preview manifest path");
    if (receiver && !path.empty()) {
      size_t begin=0;
      for (;;) {
        auto end=path.find('/',begin); auto component=path.substr(begin,end==path.npos ? path.size()-begin : end-begin);
        if (component.empty() || component=="." || component==".." || component.size()>255) throw std::runtime_error("unsafe preview manifest component");
        if (end==path.npos) break;
        begin=end+1;
      }
    }
    auto revision=app_actions::parse_revision(row.at("revision"));
    if (!receiver && !revision.exists) throw std::runtime_error("source preview manifest requires existing entries");
    if (!entries.emplace(std::move(path),revision).second) throw std::runtime_error("duplicate preview manifest path");
  }
  received+=rows.array.size(); ++sequence;
}
Inventory ManifestReceiver::release() {
  if (!complete()) throw std::runtime_error("incomplete preview manifest");
  return std::move(inventory);
}
}
