#include "app_partials.h"
#include "app_actions.h"
#include "fs.h"
#include <dirent.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <mutex>
#include <set>
#define XXH_INLINE_ALL
#include <xxhash.h>

namespace app_partials {
using app_json::Value;
using app_json::quote;
namespace {
constexpr size_t LIMIT = 1024*1024, ITEMS = 100000;
constexpr const char* VAULT = ".xsync-app-partials";
constexpr std::string_view MAGIC = "xsync app private partials 1\n";
Value text(std::string s) { return {Value::String, std::move(s), {}, {}}; }
Value object() { return {Value::Object, {}, {}, {}}; }
std::string join(const std::string& p, std::string_view n) { return p + (p == "/" ? "" : "/") + std::string(n); }
struct FD {
  int fd = -1;
  FD() = default;
  explicit FD(int fd): fd(fd) {}
  ~FD() { if (fd >= 0) close(fd); }
  FD(const FD&) = delete;
  FD& operator=(const FD&) = delete;
};
[[noreturn]] void fail(const std::string& p, const std::string& operation, int error = 0) {
  throw Error(p, operation, error, error ? std::string(strerror(error)) : operation);
}
DestinationRevision observation(int fd) {
  struct stat st;
  if (fstat(fd, &st)) fail({}, "recovery_stat", errno);
  return DestinationRevision::from(st);
}
Value revision(const DestinationRevision& r) {
  if (!r.known) return {};
  if (!r.exists) return app_json::parse("{\"exists\":false}");
  auto v = object();
  v.object = {{"exists",{Value::Bool,"true",{}, {}}}, {"device",text(std::to_string(r.device))}, {"inode",text(std::to_string(r.inode))},
    {"links",text(std::to_string(r.links))}, {"mode",text(std::to_string(r.mode))}, {"uid",text(std::to_string(r.uid))}, {"gid",text(std::to_string(r.gid))},
    {"flags",text(std::to_string(r.flags))}, {"size",text(std::to_string(r.size))}, {"mtime_seconds",text(std::to_string(r.mtime))},
    {"mtime_nanoseconds",text(std::to_string(r.mtime_ns))}, {"ctime_seconds",text(std::to_string(r.ctime))}, {"ctime_nanoseconds",text(std::to_string(r.ctime_ns))}};
  return v;
}
DestinationRevision named(int parent, const std::string& name) {
  struct stat st;
  if (!fstatat(parent, name.c_str(), &st, AT_SYMLINK_NOFOLLOW)) return DestinationRevision::from(st);
  if (errno == ENOENT) return DestinationRevision::absent();
  fail(name, "recovery_stat", errno);
}
void private_directory(int fd, const std::string& p) {
  auto r = observation(fd);
  if (!S_ISDIR(r.mode) || r.uid != geteuid() || (r.mode & 0777) != 0700) fail(p,"recovery_directory_not_private");
}
Value read_json(int parent, const std::string& name, const std::string& p) {
  FD file(openat(parent,name.c_str(),O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK));
  if (file.fd < 0) fail(p,"recovery_read",errno);
  auto before = observation(file.fd);
  if (!S_ISREG(before.mode) || before.uid != geteuid() || before.links != 1 || (before.mode & 0077) || before.size < 0 || before.size > i64(LIMIT))
    fail(p,"recovery_metadata_not_private");
  std::string data; char bytes[8192];
  for (;;) {
    ssize_t n = read(file.fd,bytes,sizeof bytes);
    if (n < 0 && errno == EINTR) continue;
    if (n < 0) fail(p,"recovery_read",errno);
    if (!n) break;
    data.append(bytes,size_t(n)); if (data.size() > LIMIT) fail(p,"recovery_metadata_limit");
  }
  if (!(before == observation(file.fd)) || !before.same_object(named(parent,name))) fail(p,"recovery_metadata_changed");
  try { return app_json::parse(data); } catch (...) { fail(p,"recovery_metadata_invalid"); }
}
void write_all(int fd, std::string_view bytes, const std::string& p) {
  while (!bytes.empty()) {
    ssize_t n = write(fd,bytes.data(),bytes.size());
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) fail(p,"recovery_write",n ? errno : EIO);
    bytes.remove_prefix(size_t(n));
  }
}
void write_json(int parent, const std::string& name, const Value& value, const std::string& p) {
  auto data = app_json::serialize(value);
  if (data.size() > LIMIT) fail(p,"recovery_metadata_limit");
  auto temporary = ".pending-" + new_id();
  FD file(openat(parent,temporary.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
  if (file.fd < 0) fail(p,"recovery_create",errno);
  auto identity = observation(file.fd);
  try {
    write_all(file.fd,data,p);
    int fd = file.fd; file.fd = -1;
    if (close(fd)) fail(p,"recovery_close",errno);
    if (!identity.same_object(named(parent,temporary))) fail(p,"recovery_metadata_changed");
    // Existing metadata is replaced only inside our pinned private job directory.
    auto current = named(parent,name);
    if (current.exists && (!S_ISREG(current.mode) || current.uid != geteuid() || current.links != 1 || (current.mode & 0077)))
      fail(p,"recovery_metadata_not_private");
    if (renameat(parent,temporary.c_str(),parent,name.c_str())) fail(p,"recovery_publish_metadata",errno);
  } catch (...) {
    if (identity.same_object(named(parent,temporary))) unlinkat(parent,temporary.c_str(),0);
    throw;
  }
}
bool marker(int vault) {
  FD fd(openat(vault,".owner",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC));
  if (fd.fd < 0) return false;
  auto st = observation(fd.fd);
  if (!S_ISREG(st.mode) || st.uid != geteuid() || st.links != 1 || (st.mode & 0077) || st.size != i64(MAGIC.size())) return false;
  char data[64]; ssize_t n = pread(fd.fd,data,sizeof data,0);
  return n == ssize_t(MAGIC.size()) && std::string_view(data,size_t(n)) == MAGIC && st == observation(fd.fd);
}
struct Store {
  std::string root, id, vault_path, job_path;
  FD root_fd, vault_fd, job_fd;
  DestinationRevision root_identity, vault_identity, job_identity;
  Value header;
  bool provisional = false;
  Store(const std::string& root, const std::string& id, bool create): root(root), id(id), vault_path(join(root,VAULT)), job_path(join(vault_path,id)) {
    if (!valid_id(id)) fail(root,"invalid_recovery_id");
    root_fd.fd = open(root.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (root_fd.fd < 0) fail(root,"recovery_open_root",errno);
    root_identity = observation(root_fd.fd);
    struct stat logical;
    if (lstat(root.c_str(),&logical) || !root_identity.same_object(DestinationRevision::from(logical))) fail(root,"recovery_root_changed");
    bool created = false;
    if (create) {
      if (!mkdirat(root_fd.fd,VAULT,0700)) created = true;
      else if (errno != EEXIST) fail(vault_path,"recovery_mkdir",errno);
    }
    vault_fd.fd = openat(root_fd.fd,VAULT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (vault_fd.fd < 0) fail(vault_path,"recovery_open_vault",errno);
    private_directory(vault_fd.fd,vault_path); vault_identity = observation(vault_fd.fd);
    if (created) {
      FD own(openat(vault_fd.fd,".owner",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600));
      if (own.fd < 0) fail(vault_path,"recovery_create_marker",errno);
      write_all(own.fd,MAGIC,vault_path);
      int fd = own.fd; own.fd = -1;
      if (close(fd)) fail(vault_path,"recovery_close_marker",errno);
    }
    if (!marker(vault_fd.fd)) fail(vault_path,"recovery_foreign_vault");
    if (create && mkdirat(vault_fd.fd,id.c_str(),0700)) fail(job_path,"recovery_job_exists",errno);
    provisional = create;
    job_fd.fd = openat(vault_fd.fd,id.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (job_fd.fd < 0) fail(job_path,"recovery_open_job",errno);
    private_directory(job_fd.fd,job_path); job_identity = observation(job_fd.fd);
    if (!create) {
      header = read_json(job_fd.fd,".job.json",job_path);
      if (header.at("format").string() != "1" || header.at("recovery_id").string() != id ||
          !root_identity.same_object(app_actions::parse_revision(header.at("root_revision")))) fail(job_path,"recovery_binding_changed");
      const auto& state = header.at("state").string();
      if (state != "active" && state != "completed" && state != "interrupted" && state != "stopped" && state != "unknown" && state != "paused")
        fail(job_path,"recovery_metadata_invalid");
    }
    check();
  }
  ~Store() {
    // A failed initial metadata write leaves no usable recovery record. Remove
    // only our still-named, empty directory; never recursively remove a scope.
    if (provisional && job_fd.fd >= 0 && vault_fd.fd >= 0) {
      try {
        if (job_identity.same_object(named(vault_fd.fd,id))) unlinkat(vault_fd.fd,id.c_str(),AT_REMOVEDIR);
      } catch (...) {}
    }
  }
  void check() const {
    struct stat st;
    if (lstat(root.c_str(),&st) || !root_identity.same_object(DestinationRevision::from(st)) ||
        !vault_identity.same_object(named(root_fd.fd,VAULT)) || !job_identity.same_object(named(vault_fd.fd,id))) fail(job_path,"recovery_directory_changed");
    private_directory(vault_fd.fd,vault_path); private_directory(job_fd.fd,job_path);
  }
  std::vector<std::pair<std::string,DestinationRevision>> files() {
    check();
    FD fd(openat(job_fd.fd,".",O_RDONLY|O_DIRECTORY|O_CLOEXEC));
    if (fd.fd < 0) fail(job_path,"recovery_open_job",errno);
    DIR* directory = fdopendir(fd.fd); if (!directory) fail(job_path,"recovery_list",errno);
    fd.fd = -1;
    std::vector<std::pair<std::string,DestinationRevision>> result;
    int error = 0;
    try {
      for (;;) {
        errno = 0; auto entry = readdir(directory);
        if (!entry) { error = errno; break; }
        std::string name = entry->d_name;
        if (name == "." || name == "..") continue;
        if (result.size() >= 3*ITEMS+1024) fail(job_path,"recovery_inventory_limit");
        auto r = named(job_fd.fd,name);
        if (!r.exists) fail(job_path,"recovery_inventory_changed");
        result.emplace_back(name,r);
      }
    } catch (...) { closedir(directory); throw; }
    if (closedir(directory) && !error) error = errno;
    if (error) fail(job_path,"recovery_list",error);
    check();
    std::sort(result.begin(),result.end(),[](const auto& a,const auto& b) { return a.first < b.first; });
    return result;
  }
};
std::string key(const std::string& path) {
  auto digest = XXH3_128bits(path.data(),path.size()); XXH128_canonical_t encoded;
  XXH128_canonicalFromHash(&encoded,digest);
  return app_json::hex(std::string_view(reinterpret_cast<char*>(encoded.digest),sizeof encoded.digest));
}
std::string inventory_token(const std::vector<std::pair<std::string,DestinationRevision>>& files) {
  XXH3_state_t state; XXH3_128bits_reset(&state);
  for (const auto& [name,r] : files) {
    auto row = app_json::path(name)+app_json::serialize(revision(r))+'\n';
    XXH3_128bits_update(&state,row.data(),row.size());
  }
  XXH128_canonical_t encoded; XXH128_canonicalFromHash(&encoded,XXH3_128bits_digest(&state));
  return app_json::hex(std::string_view(reinterpret_cast<char*>(encoded.digest),sizeof encoded.digest));
}
bool record_name(const std::string& name) {
  return name.size() == 37 && name.ends_with(".json") && valid_id(std::string_view(name).substr(0,32));
}
bool choice_name(const std::string& name) {
  return name.size() == 44 && name.starts_with("choice-") && record_name(name.substr(7));
}
bool data_name(const std::string& name) {
  return name.size() == 37 && name.ends_with(".part") && valid_id(std::string_view(name).substr(0,32));
}
std::string record_path(const Value& row,const char* field) {
  return app_json::unhex(row.at(field).at("bytes_hex").string());
}
void reject_reserved_destination(const Store& store,const std::string& path);
std::string choice_key(const std::string& source,const std::string& original) { return key(source+'\0'+original); }
void target_path(Store& store,const std::string& p) {
  if (p.empty() || p == store.root || (store.root != "/" ? !p.starts_with(store.root+'/') : p[0] != '/') || p.find('\0') != p.npos)
    fail(p,"recovery_record_changed");
  auto relative = std::string_view(p).substr(store.root == "/" ? 1 : store.root.size()+1);
  while (!relative.empty()) {
    auto slash = relative.find('/'); auto component = relative.substr(0,slash);
    if (component.empty() || component == "." || component == "..") fail(p,"recovery_record_changed");
    if (slash == relative.npos) break;
    relative.remove_prefix(slash+1);
    if (relative.empty()) fail(p,"recovery_record_changed");
  }
  reject_reserved_destination(store,p);
}
bool directory_attributes_match(const DestinationRevision& expected,const DestinationRevision& actual) {
  return expected.same_object(actual) && S_ISDIR(actual.mode) && expected.mode == actual.mode &&
    expected.uid == actual.uid && expected.gid == actual.gid && expected.flags == actual.flags;
}
void reject_reserved_destination(const Store& store,const std::string& path) {
  if (path == store.vault_path || path.starts_with(store.vault_path+'/')) fail(path,"recovery_reserved_destination");
}
void emit_error(const Emit& emit, const Error& error, const std::string& id) {
  const char* category = !error.native ? "conflict" : error.native == EACCES || error.native == EPERM ? "permission" :
    error.native == ENOSPC || error.native == EDQUOT ? "disk_full" : error.native == ENOENT ? "missing" : "filesystem";
  emit("\"type\":\"error\",\"category\":" + quote(category) + ",\"operation\":" + quote(error.operation) + ",\"endpoint\":\"local\",\"path\":" + app_json::path(error.path) +
    ",\"recovery_id\":" + quote(id) + ",\"native_code\":" + (error.native ? quote(std::to_string(error.native)) : "null") +
    ",\"side\":\"destination\",\"stage\":\"recovery\",\"retryable\":false,\"message\":" + quote(error.what()));
  err_line(RERR_PARTIAL,"private recovery operation failed");
}
std::string content_digest(int fd,const DestinationRevision& before,const std::string& path) {
  u64 sum[2];
  if (before.size < 0 || !hash_prefix_fd(fd,before.size,sum)) fail(path,"recovery_publication_read",errno ? errno : EIO);
  if (!(before == observation(fd))) fail(path,"recovery_publication_changed");
  XXH128_canonical_t encoded; XXH128_canonicalFromHash(&encoded,XXH128_hash_t{sum[0],sum[1]});
  return app_json::hex(std::string_view(reinterpret_cast<char*>(encoded.digest),sizeof encoded.digest));
}
// A crash may leave a pre-rename intent after the inode has moved. Resolve it
// without writes. Rename changes ctime; all other recorded attributes and the
// complete content digest must match, and the private name must have vanished.
Value publication_record(Store& store,const Value& input) {
  if (input.at("state").string() != "publishing") return input;
  auto row = input;
  auto path = record_path(row,"destination_path"); target_path(store,path);
  auto name = row.at("data_name").string();
  auto saved = app_actions::parse_revision(row.at("publication_identity"));
  auto digest = row.at("publication_digest").string();
  if (!data_name(name) || !valid_id(digest) || row.at("entry_type").string() != "regular" ||
      !S_ISREG(saved.mode) || saved.uid != geteuid() || saved.links != 1 || saved.size < 0 ||
      !saved.same_object(app_actions::parse_revision(row.at("data_identity")))) fail(path,"recovery_record_changed");
  auto data = named(store.job_fd.fd,name);
  if (data.exists) {
    if (!(data == saved)) fail(path,"recovery_data_changed");
    row.object["state"] = text("retained"); row.object["data_identity"] = revision(data);
    row.object["bytes_retained"] = text(std::to_string(data.size));
    return row;
  }
  auto target = destination_path(path);
  if (target.fd < 0) fail(path,"recovery_destination_changed",errno);
  auto actual = named(target.fd,target.name);
  auto renamed = saved; renamed.ctime = actual.ctime; renamed.ctime_ns = actual.ctime_ns;
  if (!(actual == renamed)) fail(path,"recovery_destination_changed");
  FD file(openat(target.fd,target.name.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC));
  if (file.fd < 0) fail(path,"recovery_publication_read",errno);
  if (!(actual == observation(file.fd)) || content_digest(file.fd,actual,path) != digest ||
      !(actual == named(target.fd,target.name)) || named(store.job_fd.fd,name).exists) fail(path,"recovery_publication_changed");
  store.check();
  row.object["state"] = text("published"); row.object["published_revision"] = revision(actual);
  row.object["bytes_retained"] = text("0");
  return row;
}
void validate_record(Store& store,const Value& input) {
  const auto row = publication_record(store,input);
  const auto& state = row.at("state").string();
  bool entry = state == "entry_prepared" || state == "entry_owned" || state == "directory_active" || state == "entry_published" || state == "entry_checkpoint";
  if (!entry && state != "active" && state != "retained" && state != "published" && state != "discarded") fail(store.job_path,"recovery_metadata_invalid");
  auto p = app_json::unhex(row.at("destination_path").at("bytes_hex").string());
  reject_reserved_destination(store,p);
  if (p == store.root) {
    if (!entry || row.at("entry_type").string() != "directory") fail(p,"recovery_record_changed");
  } else target_path(store,p);
  auto expected = app_actions::parse_revision(row.at(state == "published" || (entry && state != "entry_prepared") ? "published_revision" : "expected_destination"));
  struct stat target;
  DestinationRevision actual;
  if (!destination_named_stat(p.c_str(),&target)) actual = DestinationRevision::from(target);
  else if (errno == ENOENT) actual = DestinationRevision::absent();
  else fail(p,"recovery_destination_changed",errno);
  // While children are being written, directory timestamps, size and link
  // count are expected to change. Its inode and access attributes are not.
  bool matches = state == "directory_active" ? directory_attributes_match(expected,actual) : expected == actual;
  if (!matches) fail(p,"recovery_destination_changed");
  if (entry && state != "entry_prepared") {
    const auto& type = row.at("entry_type").string();
    if ((type == "directory" ? !S_ISDIR(actual.mode) : type == "symlink" ? !S_ISLNK(actual.mode) : type == "regular" ? !S_ISREG(actual.mode) : true))
      fail(p,"recovery_record_changed");
  }
  auto data = row.at("data_name").string();
  if (!data_name(data)) fail(p,"recovery_record_changed");
  auto file = named(store.job_fd.fd,data);
  if (state == "active" || state == "retained") {
    auto identity = app_actions::parse_revision(row.at("data_identity"));
    if (!identity.same_object(file) || !S_ISREG(file.mode) || file.uid != geteuid() || file.links != 1) fail(p,"recovery_data_changed");
  } else if (file.exists) fail(p,"recovery_record_changed");
}
using Records = std::map<std::string,Value>;
bool policy_kind(const std::string& kind) {
  return kind == "file_file" || kind == "directory_merge" || kind == "symlink" || kind == "type_mismatch" || kind == "name_collision";
}
void validate_policies(Store& store) {
  if (!store.header.object.count("conflict_policies")) return;
  const auto& policies = store.header.at("conflict_policies");
  if (store.header.at("binding").at("on_conflict").string() != "ask" || policies.kind != Value::Array || policies.array.size() > 128)
    fail(store.job_path,"recovery_metadata_invalid");
  for (const auto& row : policies.array) {
    const auto& action = row.at("action").string();
    if (!policy_kind(row.at("kind").string()) || (action != "replace" && action != "skip" && action != "keep_both")) fail(store.job_path,"recovery_metadata_invalid");
    auto directory = record_path(row,"directory");
    if (!directory.empty() && directory != store.root) target_path(store,directory);
  }
}
void validate_choice(Store& store,const Value& row,const Records& records) {
  if (row.at("format").string() != "1" || row.at("recovery_id").string() != store.id || row.at("record_kind").string() != "conflict_choice" ||
      store.header.at("binding").at("on_conflict").string() != "ask") fail(store.job_path,"recovery_metadata_invalid");
  const auto& decision = row.at("decision").string();
  if (decision != "copy" && decision != "replace" && decision != "skip" && decision != "keep_both") fail(store.job_path,"recovery_metadata_invalid");
  auto source = record_path(row,"source_path"), original = record_path(row,"original_destination_path"), resolved = record_path(row,"destination_path");
  if (source.empty() || source.find('\0') != source.npos) fail(store.job_path,"recovery_source_mapping_changed");
  target_path(store,original); target_path(store,resolved);
  if (original.substr(0,original.rfind('/')) != resolved.substr(0,resolved.rfind('/'))) fail(resolved,"recovery_record_changed");
  auto found = records.find(resolved);
  if (found != records.end()) {
    if (decision != "skip" && found->second.at("source_path").at("bytes_hex").string() != row.at("source_path").at("bytes_hex").string())
      fail(resolved,"recovery_source_mapping_changed");
    validate_record(store,found->second);
  } else {
    struct stat st; DestinationRevision actual;
    if (!destination_named_stat(resolved.c_str(),&st)) actual = DestinationRevision::from(st);
    else if (errno == ENOENT) actual = DestinationRevision::absent();
    else fail(resolved,"recovery_destination_changed",errno);
    if (!(actual == app_actions::parse_revision(row.at("expected_destination")))) {
      bool owned_alias = false;
      if (decision == "skip") for (const auto& [path,entry] : records) {
        if (entry.at("source_path").at("bytes_hex").string() == row.at("source_path").at("bytes_hex").string()) continue;
        const auto& state = entry.at("state").string();
        bool published = state == "published" || state == "entry_owned" || state == "directory_active" || state == "entry_published" || state == "entry_checkpoint";
        auto guard = app_actions::parse_revision(entry.at(published ? "published_revision" : "expected_destination"));
        if (guard.same_object(actual) && actual.exists) { validate_record(store,entry); owned_alias = true; break; }
      }
      if (!owned_alias) fail(resolved,"recovery_destination_changed");
    }
  }
}
void validate_data_mapping(Store& store,const Records& records) {
  std::set<std::string> names;
  for (const auto& [p,row] : records) {
    const auto& state = row.at("state").string();
    if ((state == "active" || state == "retained" || state == "publishing") && !names.insert(row.at("data_name").string()).second) fail(p,"recovery_data_mapping_changed");
  }
}
void validate_private_inventory(Store& store,const Records& records) {
  std::set<std::string> referenced;
  for (const auto& [path,row] : records) {
    const auto& state = row.at("state").string();
    if (state == "active" || state == "retained" || state == "publishing") referenced.insert(row.at("data_name").string());
  }
  for (const auto& [name,r] : store.files()) {
    if (!S_ISREG(r.mode) || r.uid != geteuid() || r.links != 1 || (!data_name(name) && (r.mode & 0077)) ||
        (name != ".job.json" && !data_name(name) && !record_name(name) && !choice_name(name)))
      fail(join(store.job_path,name),"recovery_verification_scope");
    if (data_name(name) && !referenced.count(name)) fail(join(store.job_path,name),"recovery_unrecorded_data");
  }
}
Value checkpoint_directory(Store& store,Value row) {
  if (row.at("state").string() != "directory_active") return row;
  validate_record(store,row);
  auto p = app_json::unhex(row.at("destination_path").at("bytes_hex").string());
  struct stat st;
  if (destination_named_stat(p.c_str(),&st)) fail(p,"recovery_destination_changed",errno);
  auto actual = DestinationRevision::from(st);
  if (!directory_attributes_match(app_actions::parse_revision(row.at("published_revision")),actual)) fail(p,"recovery_destination_changed");
  row.object["published_revision"] = revision(actual);
  row.object["state"] = text("entry_checkpoint");
  return row;
}
Session::Impl* current = nullptr;
}
struct Session::Impl {
  Store store;
  Emit emit;
  std::recursive_mutex mutex;
  Records records, choices;
  bool failed = false;
  Impl(const std::string& root,const std::string& id,const Value& binding,bool resume,const Emit& emit,const Value& actor): store(root,id,!resume), emit(emit) {
    if (resume) {
      std::vector<std::pair<std::string,Value>> publications;
      if (app_json::serialize(store.header.at("binding")) != app_json::serialize(binding)) fail(store.job_path,"recovery_binding_changed");
      for (const auto& [name,identity] : store.files()) if (record_name(name)) {
        if (records.size() >= ITEMS) fail(store.job_path,"recovery_inventory_limit");
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        auto target = app_json::unhex(row.at("destination_path").at("bytes_hex").string());
        if (key(target)+".json" != name || row.at("format").string() != "1" || row.at("recovery_id").string() != id) fail(store.job_path,"recovery_record_changed");
        bool publishing = row.at("state").string() == "publishing";
        row = publication_record(store,row);
        if (publishing) publications.emplace_back(name,row);
        validate(row); records.emplace(target,std::move(row));
      }
      validate_data_mapping(store,records); validate_policies(store);
      for (const auto& [name,identity] : store.files()) if (choice_name(name)) {
        if (choices.size() >= ITEMS) fail(store.job_path,"recovery_inventory_limit");
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        auto id = choice_key(record_path(row,"source_path"),record_path(row,"original_destination_path"));
        if (name != "choice-"+id+".json") fail(store.job_path,"recovery_record_changed");
        validate_choice(store,row,records); choices.emplace(id,std::move(row));
      }
      validate_private_inventory(store,records);
      // Freeze full post-rename revisions only after all original records and
      // choices validate. Read-only verification never changes the inventory.
      for (const auto& [name,row] : publications) {
        validate_record(store,row); write_json(store.job_fd.fd,name,row,store.job_path);
      }
    } else {
      store.header = object(); store.header.object = {{"format",text("1")},{"recovery_id",text(id)},{"binding",binding},{"root_revision",revision(store.root_identity)}};
    }
    if (actor.kind != Value::Null) {
      auto& actors = store.header.object["actors"];
      if (actors.kind == Value::Null) actors.kind = Value::Array;
      if (actors.kind != Value::Array || actors.array.size() >= 256) fail(store.job_path,"recovery_actor_inventory_limit");
      actors.array.push_back(actor);
    }
    state("active");
    store.provisional = false;
  }
  void state(const std::string& status) {
    store.check(); store.header.object["state"] = text(status);
    write_json(store.job_fd.fd,".job.json",store.header,store.job_path);
  }
  void validate(const Value& row) { validate_record(store,row); }
  void save(const std::string& p, Value row) {
    store.check();
    if (!records.count(p) && records.size() >= ITEMS) fail(p,"recovery_inventory_limit");
    write_json(store.job_fd.fd,key(p)+".json",row,store.job_path);
    records[p] = std::move(row);
  }
  void notice(const std::string& type,const Value* row = nullptr) {
    std::string fields = "\"type\":" + quote(type) + ",\"recovery_id\":" + quote(store.id) + ",\"endpoint\":\"local\",\"root_path\":" + app_json::path(store.root);
    if (row) fields += ",\"source_path\":" + app_json::serialize(row->at("source_path")) + ",\"destination_path\":" + app_json::serialize(row->at("destination_path")) +
      ",\"state\":" + quote(row->at("state").string()) + ",\"bytes_retained\":" + app_json::serialize(row->at("bytes_retained"));
    emit(std::move(fields));
  }
};
Error::Error(std::string p,std::string operation,int native,std::string message): std::runtime_error(std::move(message)),path(std::move(p)),operation(std::move(operation)),native(native) {}
bool valid_id(std::string_view id) { return id.size() == 32 && std::all_of(id.begin(),id.end(),[](char c){return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');}); }
std::string new_id() {
  FD fd(open("/dev/urandom",O_RDONLY|O_CLOEXEC));
  if (fd.fd < 0) fail({},"recovery_random",errno);
  char bytes[16]; size_t offset = 0;
  while (offset < sizeof bytes) {
    ssize_t n = read(fd.fd,bytes+offset,sizeof bytes-offset);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) fail({},"recovery_random",n ? errno : EIO);
    offset += size_t(n);
  }
  return app_json::hex(std::string_view(bytes,sizeof bytes));
}
Session::Session(const std::string& root,const std::string& id,const Value& binding,bool resume,const Emit& emit,const Value& actor) {
  if (current) fail(root,"nested_recovery_session");
  try {
    if (app_json::serialize(binding).size() > LIMIT-1024) fail(root,"recovery_metadata_limit");
    emit("\"type\":\"recovery_preparing\",\"recovery_id\":" + quote(id) + ",\"endpoint\":\"local\",\"root_path\":" + app_json::path(root));
    impl = std::make_unique<Impl>(root,id,binding,resume,emit,actor);
  }
  catch (const Error& error) { emit_error(emit,error,id); throw; }
  catch (const std::runtime_error&) {
    Error error(root,"recovery_metadata_invalid",0,"invalid recovery metadata");
    emit_error(emit,error,id); throw error;
  }
  current = impl.get(); impl->notice(resume ? "recovery_resuming" : "recovery_created");
}
Session::~Session() { if (current == impl.get()) current = nullptr; }
void Session::finish(int code) {
  std::lock_guard lock(impl->mutex);
  try {
    validate_data_mapping(impl->store,impl->records); validate_policies(impl->store);
    validate_private_inventory(impl->store,impl->records);
    for (const auto& [p,row] : impl->records) impl->validate(row);
    for (const auto& [p,row] : impl->choices) validate_choice(impl->store,row,impl->records);
    for (const auto& [p,row] : impl->records)
      if (row.at("state").string() == "directory_active") impl->save(p,checkpoint_directory(impl->store,row));
    impl->state(!code && !impl->failed ? "completed" : "interrupted");
  }
  catch (const Error& error) { impl->failed = true; emit_error(impl->emit,error,impl->store.id); }
}
bool active() { return current != nullptr; }
namespace {
template<class F> bool entry_change(const std::shared_ptr<TransferItem>& item,F action) {
  if (!current || !item) return true;
  auto& s = *current; std::lock_guard lock(s.mutex);
  try { s.store.check(); action(s); return true; }
  catch (const Error& error) {
    item->failed.store(true); s.failed = true; emit_error(s.emit,error,s.store.id); return false;
  }
}
Value entry_row(Session::Impl& s,const TransferItem& item) {
  auto row = object();
  row.object = {{"format",text("1")},{"recovery_id",text(s.store.id)},
    {"source_path",app_json::parse(app_json::path(item.source))},{"destination_path",app_json::parse(app_json::path(item.destination))},
    {"entry_type",text(item.type == T_DIR ? "directory" : item.type == T_LNK ? "symlink" : "regular")},
    {"expected_destination",revision(item.expected_destination)},{"data_name",text(key(item.destination)+".part")},
    {"state",text("entry_prepared")},{"bytes_retained",text("0")}};
  return row;
}
}
bool prepare_entry(const std::shared_ptr<TransferItem>& item) {
  return entry_change(item,[&](auto& s) {
    reject_reserved_destination(s.store,item->destination);
    auto found = s.records.find(item->destination);
    if (found != s.records.end()) {
      s.validate(found->second);
      if (found->second.at("source_path").at("bytes_hex").string() != app_json::hex(item->source)) fail(item->destination,"recovery_source_mapping_changed");
      auto row = found->second;
      const auto state = row.at("state").string();
      if (state == "active" || state == "retained") {
        // A new source type (or an up-to-date file) makes the old byte prefix
        // obsolete. Delete only the recorded private inode and retain its
        // destination guard before replacing the receipt.
        auto name = row.at("data_name").string();
        auto identity = app_actions::parse_revision(row.at("data_identity"));
        if (!identity.same_object(named(s.store.job_fd.fd,name))) fail(item->destination,"recovery_data_changed");
        if (unlinkat(s.store.job_fd.fd,name.c_str(),0)) fail(item->destination,"recovery_remove_data",errno);
        row.object["state"] = text("discarded"); row.object["bytes_retained"] = text("0");
        s.save(item->destination,row);
      }
    }
    s.save(item->destination,entry_row(s,*item));
  });
}
int restore_choice(const std::shared_ptr<TransferItem>& item,Choice& choice) {
  if (!current || !item) return 0;
  bool restored = false;
  bool ok = entry_change(item,[&](auto& s) {
    auto found = s.choices.find(choice_key(item->source,item->recovery_original));
    if (found == s.choices.end()) return;
    validate_choice(s.store,found->second,s.records);
    choice.decision = found->second.at("decision").string();
    choice.destination = record_path(found->second,"destination_path"); restored = true;
    choice.recovery_id = s.store.id;
  });
  return !ok ? -1 : restored ? 1 : 0;
}
bool conflict_policy(const std::shared_ptr<TransferItem>& item,const std::string& kind,const std::string& directory,std::string& action) {
  return entry_change(item,[&](auto& s) {
    if (!s.store.header.object.count("conflict_policies")) return;
    const auto& policies = s.store.header.at("conflict_policies").array;
    for (auto i = policies.rbegin(); i != policies.rend(); ++i) {
      auto path = record_path(*i,"directory");
      if (i->at("kind").string() == kind && (path.empty() || path == directory)) { action = i->at("action").string(); return; }
    }
  });
}
bool remember_choice(const std::shared_ptr<TransferItem>& item,const std::string& decision,const std::string& scope,
                     const std::string& kind,const std::string& directory) {
  return entry_change(item,[&](auto& s) {
    target_path(s.store,item->recovery_original); target_path(s.store,item->destination);
    auto id = choice_key(item->source,item->recovery_original);
    auto previous = s.choices.find(id);
    auto old_path = previous == s.choices.end() ? item->recovery_original : record_path(previous->second,"destination_path");
    auto old = s.records.find(old_path);
    if (old != s.records.end() && old->second.at("source_path").at("bytes_hex").string() == app_json::hex(item->source)) {
      auto row = old->second; const auto state = row.at("state").string();
      bool pending = state == "active" || state == "retained" || state == "publishing";
      if (pending || old_path == item->destination) {
        if (pending) {
          auto data = named(s.store.job_fd.fd,row.at("data_name").string());
          if (!app_actions::parse_revision(row.at("data_identity")).same_object(data) || !S_ISREG(data.mode) || data.uid != geteuid() || data.links != 1)
            fail(old_path,"recovery_data_changed");
          row.object["state"] = text("retained");
        } else row = entry_row(s,*item);
        row.object["destination_path"] = app_json::parse(app_json::path(item->destination));
        row.object["expected_destination"] = revision(item->expected_destination);
        if (old_path == item->destination) s.save(old_path,row);
        else {
          if (s.records.count(item->destination)) fail(item->destination,"recovery_data_mapping_changed");
          auto name = key(old_path)+".json";
          auto identity = named(s.store.job_fd.fd,name);
          s.save(item->destination,row);
          if (!(identity == named(s.store.job_fd.fd,name)) || !S_ISREG(identity.mode) || identity.uid != geteuid() || identity.links != 1)
            fail(old_path,"recovery_metadata_changed");
          if (unlinkat(s.store.job_fd.fd,name.c_str(),0)) fail(old_path,"recovery_remove_metadata",errno);
          s.records.erase(old_path);
        }
      }
    }
    if (!s.choices.count(id) && s.choices.size() >= ITEMS) fail(item->destination,"recovery_inventory_limit");
    auto row = object();
    row.object = {{"format",text("1")},{"recovery_id",text(s.store.id)},{"record_kind",text("conflict_choice")},
      {"source_path",app_json::parse(app_json::path(item->source))},{"original_destination_path",app_json::parse(app_json::path(item->recovery_original))},
      {"destination_path",app_json::parse(app_json::path(item->destination))},{"expected_destination",revision(item->expected_destination)},
      {"decision",text(decision)}};
    write_json(s.store.job_fd.fd,"choice-"+id+".json",row,s.store.job_path); s.choices[id] = std::move(row);
    if (scope != "item") {
      auto& policies = s.store.header.object["conflict_policies"];
      if (policies.kind == Value::Null) policies.kind = Value::Array;
      if (policies.kind != Value::Array || policies.array.size() >= 128) fail(s.store.job_path,"recovery_policy_inventory_limit");
      auto policy = object();
      policy.object = {{"kind",text(kind)},{"action",text(decision)},{"directory",app_json::parse(app_json::path(scope == "directory" ? directory : std::string()))}};
      policies.array.push_back(std::move(policy));
      write_json(s.store.job_fd.fd,".job.json",s.store.header,s.store.job_path);
    }
  });
}
bool own_entry(const std::shared_ptr<TransferItem>& item) {
  return entry_change(item,[&](auto& s) {
    auto found = s.records.find(item->destination);
    if (found == s.records.end()) fail(item->destination,"recovery_record_missing");
    DestinationRevision actual;
    if (!item_observe_destination(item,actual) || !item->expected_destination.same_object(actual)) fail(item->destination,"recovery_destination_changed");
    if (item->type == T_DIR ? !S_ISDIR(actual.mode) : item->type == T_LNK ? !S_ISLNK(actual.mode) : !S_ISREG(actual.mode))
      fail(item->destination,"recovery_destination_changed");
    auto row = found->second;
    row.object["published_revision"] = revision(actual);
    row.object["state"] = text(item->type == T_DIR ? "directory_active" : "entry_owned");
    s.save(item->destination,row);
  });
}
bool removed_entry(const std::shared_ptr<TransferItem>& item) {
  return entry_change(item,[&](auto& s) {
    auto found = s.records.find(item->destination);
    if (found == s.records.end() || found->second.at("state").string() != "entry_prepared") fail(item->destination,"recovery_record_missing");
    DestinationRevision actual;
    if (!item_observe_destination(item,actual) || actual.exists) fail(item->destination,"recovery_destination_changed");
    auto row = found->second; row.object["expected_destination"] = revision(actual); s.save(item->destination,row);
  });
}
bool validate_entry(const std::shared_ptr<TransferItem>& item) {
  return entry_change(item,[&](auto& s) {
    auto found = s.records.find(item->destination);
    if (found != s.records.end()) s.validate(found->second);
  });
}
void finish_entry(const std::shared_ptr<TransferItem>& item) {
  (void)entry_change(item,[&](auto& s) {
    auto found = s.records.find(item->destination); if (found == s.records.end()) return;
    auto row = found->second; const auto state = row.at("state").string();
    if (state != "directory_active" && state != "entry_owned") return;
    s.validate(row);
    DestinationRevision actual;
    if (!item_observe_destination(item,actual)) fail(item->destination,"recovery_destination_changed");
    auto expected = app_actions::parse_revision(row.at("published_revision"));
    if (state == "directory_active" ? !directory_attributes_match(expected,actual) : !(expected == actual))
      fail(item->destination,"recovery_destination_changed");
    row.object["published_revision"] = revision(actual); row.object["state"] = text("entry_published");
    s.save(item->destination,row);
  });
}
bool open_stage(OutFile& file) {
  auto& session = *current; std::lock_guard lock(session.mutex);
  try {
    session.store.check();
    reject_reserved_destination(session.store,file.path);
    auto found = session.records.find(file.path);
    Value row;
    bool reuse = found != session.records.end() && (found->second.at("state").string() == "active" || found->second.at("state").string() == "retained");
    if (found != session.records.end()) {
      session.validate(found->second);
      if (found->second.at("source_path").at("bytes_hex").string() != app_json::hex(file.item->source)) fail(file.path,"recovery_source_mapping_changed");
      row = found->second;
    }
    auto data = reuse ? row.at("data_name").string() : new_id()+".part";
    file.stage_fd = fcntl(session.store.job_fd.fd,F_DUPFD_CLOEXEC,0);
    if (file.stage_fd < 0) fail(file.path,"recovery_duplicate_stage",errno);
    file.tmp_name = data; file.tmp = join(session.store.job_path,data);
    file.fd = openat(file.stage_fd,data.c_str(),O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC|(reuse ? 0 : O_CREAT|O_EXCL),0600);
    if (file.fd < 0) fail(file.path,"recovery_open_data",errno);
    auto identity = observation(file.fd);
    if (reuse && !identity.same_object(app_actions::parse_revision(row.at("data_identity")))) fail(file.path,"recovery_data_changed");
    if (!S_ISREG(identity.mode) || identity.uid != geteuid() || identity.links != 1) fail(file.path,"recovery_data_changed");
    row = object(); row.object = {{"format",text("1")},{"recovery_id",text(session.store.id)},{"source_path",app_json::parse(app_json::path(file.item->source))},
      {"destination_path",app_json::parse(app_json::path(file.path))},{"expected_destination",revision(file.item->expected_destination)},
      {"entry_type",text("regular")},
      {"data_name",text(data)},{"data_identity",revision(identity)},{"state",text("active")},{"bytes_retained",text("0")}};
    session.save(file.path,row);
    file.temp = true; file.created_mode = 0600;
    return true;
  } catch (const Error& error) {
    session.failed = true; emit_error(session.emit,error,session.store.id);
    if (file.fd >= 0) close(file.fd);
    if (file.stage_fd >= 0) close(file.stage_fd);
    file.fd = file.stage_fd = -1; return false;
  }
}
ResumePrefix prefix(const char* path,i64 limit) {
  ResumePrefix result; auto& session = *current; std::lock_guard lock(session.mutex);
  try {
    session.store.check();
    auto found = session.records.find(path); if (found == session.records.end() || limit <= 0) return result;
    session.validate(found->second);
    const auto& state = found->second.at("state").string();
    if (state != "active" && state != "retained" && state != "published") return result;
    FD fd;
    if (found->second.at("state").string() == "published") {
      auto p = destination_path(path);
      if (p.fd < 0) fail(path,"recovery_destination_changed",errno);
      fd.fd = openat(p.fd,p.name.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    } else fd.fd = openat(session.store.job_fd.fd,found->second.at("data_name").string().c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if (fd.fd < 0) fail(path,"recovery_open_prefix",errno);
    auto before = observation(fd.fd);
    if (!S_ISREG(before.mode) || before.size <= 0) return result;
    result.size = std::min<i64>(before.size,limit);
    if (!hash_prefix_fd(fd.fd,result.size,result.sum) || !(before == observation(fd.fd))) {
      if (!g_stop.load()) fail(path,"recovery_prefix_changed");
      return {};
    }
    session.validate(found->second); session.store.check();
    result.basis = std::make_shared<ResumePrefix::Basis>();
    result.basis->identity = before; result.basis->path = path;
    result.basis->published = found->second.at("state").string() == "published";
    return result;
  } catch (const Error& error) { session.failed = true; emit_error(session.emit,error,session.store.id); return {}; }
}
int open_prefix(const std::string& path,bool published,const DestinationRevision& expected) {
  if (!current) { errno = ESTALE; return -1; }
  auto& session = *current; std::lock_guard lock(session.mutex);
  try {
    session.store.check();
    auto found = session.records.find(path);
    if (found == session.records.end()) fail(path,"recovery_record_missing");
    session.validate(found->second);
    FD fd;
    // out_open may already have replaced a published receipt with a new active
    // staging record. The snapshot remembers which inode supplied its bytes.
    if (published) {
      auto p = destination_path(path);
      if (p.fd < 0) fail(path,"recovery_destination_changed",errno);
      fd.fd = openat(p.fd,p.name.c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    } else {
      const auto& state = found->second.at("state").string();
      if (state != "active" && state != "retained") fail(path,"recovery_prefix_changed");
      fd.fd = openat(session.store.job_fd.fd,found->second.at("data_name").string().c_str(),O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    }
    if (fd.fd < 0) fail(path,"recovery_open_prefix",errno);
    if (!(expected == observation(fd.fd))) fail(path,"recovery_prefix_changed");
    session.validate(found->second); session.store.check();
    int result = fd.fd; fd.fd = -1; return result;
  } catch (const Error& error) {
    session.failed = true; emit_error(session.emit,error,session.store.id);
    errno = error.native ? error.native : ESTALE; return -1;
  }
}
namespace {
template<class F> void change(const std::string& name,F action) {
  if (!current) return;
  auto& s = *current; std::lock_guard lock(s.mutex);
  try {
    s.store.check();
    auto row = std::find_if(s.records.begin(),s.records.end(),[&](const auto& entry){return entry.second.at("data_name").string() == name;});
    if (row == s.records.end()) fail(s.store.job_path,"recovery_record_missing");
    action(s,row->first,row->second);
  } catch (const Error& error) { s.failed = true; emit_error(s.emit,error,s.store.id); }
}
}
void retained(int stage,const std::string& name,const DestinationRevision& identity) {
  change(name,[&](auto& s,const std::string& p,Value row) {
    auto current = named(stage,name);
    if (!identity.same_object(current)) fail(p,"recovery_data_changed");
    row.object["state"] = text("retained"); row.object["bytes_retained"] = text(std::to_string(current.size)); row.object["data_identity"] = revision(current);
    s.save(p,row); s.notice("partial_retained",&row);
  });
}
void discarded(int stage,const std::string& name,const DestinationRevision& identity) {
  change(name,[&](auto& s,const std::string& p,Value row) {
    auto current = named(stage,name);
    if (current.exists && !identity.same_object(current)) fail(p,"recovery_data_changed");
    if (current.exists && unlinkat(stage,name.c_str(),0)) fail(p,"recovery_remove_data",errno);
    auto record = key(p)+".json";
    auto metadata = named(stage,record);
    if (!metadata.exists || !S_ISREG(metadata.mode) || metadata.uid != geteuid() || metadata.links != 1 || (metadata.mode & 0077)) fail(p,"recovery_metadata_changed");
    // Removing an unusable prefix must not erase its destination guard. A
    // later retry still cannot adopt an independently edited good destination.
    row.object["state"] = text("discarded"); row.object["bytes_retained"] = text("0");
    s.save(p,row);
  });
}
bool preparing_publication(const OutFile& file) {
  if (!current) return true;
  auto& s = *current; std::lock_guard lock(s.mutex);
  try {
    s.store.check();
    auto found = s.records.find(file.path);
    if (found == s.records.end() || found->second.at("data_name").string() != file.tmp_name || !file.item)
      fail(file.path,"recovery_record_missing");
    auto row = found->second;
    s.validate(row);
    auto identity = observation(file.ownership_fd);
    if (!file.output_identity.same_object(identity) || !S_ISREG(identity.mode) || identity.uid != geteuid() || identity.links != 1 ||
        !(identity == named(file.stage_fd,file.tmp_name))) fail(file.path,"recovery_data_changed");
    auto digest = content_digest(file.ownership_fd,identity,file.path);
    if (!(identity == named(file.stage_fd,file.tmp_name))) fail(file.path,"recovery_data_changed");
    row.object["expected_destination"] = revision(file.item->expected_destination);
    row.object["data_identity"] = revision(identity);
    row.object["state"] = text("publishing"); row.object["publication_identity"] = revision(identity);
    row.object["publication_digest"] = text(digest); row.object["bytes_retained"] = text(std::to_string(identity.size));
    s.save(file.path,row);
    return true;
  } catch (const Error& error) { s.failed = true; emit_error(s.emit,error,s.store.id); return false; }
}
void published(const OutFile& file) {
  change(file.tmp_name,[&](auto& s,const std::string& p,Value row) {
    auto target = destination_path(file.path);
    if (target.fd < 0) fail(p,"recovery_destination_changed",errno);
    auto current = named(target.fd,target.name);
    if (!file.output_identity.same_object(current) || named(file.stage_fd,file.tmp_name).exists) fail(p,"recovery_destination_changed");
    row.object["state"] = text("published"); row.object["published_revision"] = revision(current); row.object["bytes_retained"] = text("0");
    s.save(p,row); s.notice("partial_published",&row);
  });
}
void stopped() {
  if (!current) return;
  std::lock_guard lock(current->mutex);
  try { current->state(current->failed ? "unknown" : "stopped"); }
  catch (const Error& error) { current->failed = true; emit_error(current->emit,error,current->store.id); }
}
bool hidden(int parent,std::string_view name) {
  if (name != VAULT) return false;
  try {
    FD fd(openat(parent,VAULT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC));
    if (fd.fd < 0) return false;
    private_directory(fd.fd,VAULT); return marker(fd.fd);
  } catch (...) { return false; }
}
int inspect(const std::string& root,const std::string& id,const Emit& emit) {
  try {
    Store store(root,id,false); auto files = store.files(); auto job_revision = observation(store.job_fd.fd);
    emit("\"type\":\"recovery_state\",\"recovery_id\":" + quote(id) + ",\"endpoint\":\"local\",\"root_path\":" + app_json::path(root) +
      ",\"job_revision\":" + app_json::serialize(revision(job_revision)) + ",\"inventory_token\":" + quote(inventory_token(files)) + ",\"state\":" + quote(store.header.at("state").string()) +
      ",\"binding\":" + app_json::serialize(store.header.at("binding")) + ",\"actors\":" +
      (store.header.object.count("actors") ? app_json::serialize(store.header.at("actors")) : "[]") + ",\"conflict_policies\":" +
      (store.header.object.count("conflict_policies") ? app_json::serialize(store.header.at("conflict_policies")) : "[]") + ",\"files_total\":" + quote(std::to_string(files.size())));
    for (const auto& [name,r] : files) if (name != ".job.json") {
      Value row;
      if (record_name(name) || choice_name(name)) row = read_json(store.job_fd.fd,name,join(store.job_path,name));
      emit("\"type\":\"recovery_entry\",\"recovery_id\":" + quote(id) + ",\"endpoint\":\"local\",\"name\":" + app_json::path(name) +
        ",\"revision\":" + app_json::serialize(revision(r)) + ",\"record\":" + app_json::serialize(row) + ",\"verification_required\":true");
    }
    store.check();
    if (!(job_revision == observation(store.job_fd.fd))) fail(store.job_path,"recovery_inventory_changed");
    return 0;
  } catch (const Error& error) { emit_error(emit,error,id); return RERR_FILESELECT; }
  catch (const std::runtime_error&) { emit_error(emit,Error(root,"recovery_metadata_invalid",0,"invalid recovery metadata"),id); return RERR_FILESELECT; }
}
int verify(const std::string& root,const std::string& id,const Value& binding,const DestinationRevision& expected_job,const std::string& expected_inventory,const Emit& emit) {
  try {
    Store store(root,id,false);
    auto job_revision = observation(store.job_fd.fd);
    if (!(expected_job == job_revision)) fail(store.job_path,"recovery_verification_stale");
    if (app_json::serialize(store.header.at("binding")) != app_json::serialize(binding)) fail(store.job_path,"recovery_binding_changed");
    auto files = store.files();
    if (inventory_token(files) != expected_inventory) fail(store.job_path,"recovery_inventory_changed");
    Records records; std::vector<Value> choices;
    auto selected_source = [&](const std::string& source) {
      if (source.empty() || source.find('\0') != source.npos) return false;
      for (const auto& selection : binding.at("sources").array) {
        auto parent = record_path(selection,"path");
        while (parent.size() > 1 && parent.back() == '/') parent.pop_back();
        if (source == parent || source.starts_with(parent == "/" ? parent : parent+'/')) return true;
      }
      return false;
    };
    for (const auto& [name,r] : files) {
      if (g_stop.load()) fail(store.job_path,"recovery_verification_cancelled");
      if (!S_ISREG(r.mode) || r.uid != geteuid() || r.links != 1 || (!data_name(name) && (r.mode & 0077))) fail(join(store.job_path,name),"recovery_verification_scope");
      if (record_name(name)) {
        if (records.size() >= ITEMS) fail(store.job_path,"recovery_inventory_limit");
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        auto target = record_path(row,"destination_path");
        if (key(target)+".json" != name || row.at("format").string() != "1" || row.at("recovery_id").string() != id)
          fail(store.job_path,"recovery_record_changed");
        if (!selected_source(record_path(row,"source_path"))) fail(target,"recovery_source_mapping_changed");
        row = publication_record(store,row);
        validate_record(store,row); records.emplace(target,std::move(row));
      } else if (choice_name(name)) {
        if (choices.size() >= ITEMS) fail(store.job_path,"recovery_inventory_limit");
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        if (name != "choice-"+choice_key(record_path(row,"source_path"),record_path(row,"original_destination_path"))+".json")
          fail(store.job_path,"recovery_record_changed");
        if (!selected_source(record_path(row,"source_path"))) fail(store.job_path,"recovery_source_mapping_changed");
        choices.push_back(std::move(row));
      } else if (name != ".job.json" && !data_name(name)) fail(join(store.job_path,name),"recovery_verification_scope");
    }
    validate_data_mapping(store,records); validate_policies(store);
    for (const auto& row : choices) validate_choice(store,row,records);
    std::set<std::string> referenced;
    u64 pending = 0, published = 0, prepared = 0, bytes = 0;
    for (const auto& [path,row] : records) {
      const auto& state = row.at("state").string();
      if (state == "active" || state == "retained") {
        auto name = row.at("data_name").string(); referenced.insert(name);
        auto data = named(store.job_fd.fd,name); if (data.size < 0 || u64(data.size) > UINT64_MAX-bytes) fail(path,"recovery_metadata_invalid");
        bytes += u64(data.size); ++pending;
      } else if (state == "entry_prepared" || state == "discarded") ++prepared;
      else ++published;
    }
    for (const auto& [name,r] : files) if (data_name(name) && !referenced.count(name)) fail(join(store.job_path,name),"recovery_unrecorded_data");
    auto unchanged = [&] {
      store.check();
      if (!(job_revision == observation(store.job_fd.fd))) fail(store.job_path,"recovery_inventory_changed");
      for (const auto& [name,r] : files) if (!(r == named(store.job_fd.fd,name))) fail(join(store.job_path,name),"recovery_inventory_changed");
      for (const auto& [path,row] : records) validate_record(store,row);
      for (const auto& row : choices) validate_choice(store,row,records);
    };
    unchanged();
    for (const auto& [path,row] : records) {
      if (g_stop.load()) fail(store.job_path,"recovery_verification_cancelled");
      emit("\"type\":\"recovery_verified_entry\",\"recovery_id\":"+quote(id)+",\"endpoint\":\"local\",\"record\":"+app_json::serialize(row)+
        ",\"destination_guard_verified\":true,\"source_verification_required\":true");
    }
    unchanged();
    emit("\"type\":\"recovery_verified\",\"recovery_id\":"+quote(id)+",\"endpoint\":\"local\",\"job_revision\":"+app_json::serialize(revision(job_revision))+
      ",\"inventory_token\":"+quote(expected_inventory)+",\"state\":"+app_json::serialize(store.header.at("state"))+",\"records_total\":"+quote(std::to_string(records.size()))+
      ",\"pending_records\":"+quote(std::to_string(pending))+",\"published_records\":"+quote(std::to_string(published))+",\"prepared_records\":"+quote(std::to_string(prepared))+
      ",\"choices_total\":"+quote(std::to_string(choices.size()))+",\"bytes_retained\":"+quote(std::to_string(bytes))+
      ",\"destination_guard_verified\":true,\"source_verification_required\":true,\"operation_completion_proven\":false");
    return 0;
  } catch (const Error& error) { emit_error(emit,error,id); return RERR_FILESELECT; }
  catch (const std::runtime_error&) { emit_error(emit,Error(root,"recovery_metadata_invalid",0,"invalid recovery metadata"),id); return RERR_FILESELECT; }
}
int checkpoint(const std::string& root,const std::string& id,const Value& binding,const Emit& emit,const std::string& closed_attempt) {
  try {
    Store store(root,id,false);
    if (app_json::serialize(store.header.at("binding")) != app_json::serialize(binding)) fail(store.job_path,"recovery_binding_changed");
    auto files = store.files();
    std::vector<std::pair<std::string,Value>> directories;
    Records records;
    std::vector<Value> choices;
    for (const auto& [name,r] : files) {
      if (!S_ISREG(r.mode) || r.uid != geteuid() || r.links != 1) fail(join(store.job_path,name),"recovery_checkpoint_scope");
      if (record_name(name)) {
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        auto target = app_json::unhex(row.at("destination_path").at("bytes_hex").string());
        if (key(target)+".json" != name || row.at("format").string() != "1" || row.at("recovery_id").string() != id)
          fail(store.job_path,"recovery_record_changed");
        bool publishing = row.at("state").string() == "publishing";
        row = publication_record(store,row);
        validate_record(store,row);
        records.emplace(target,row);
        if (publishing) directories.emplace_back(name,row);
        if (row.at("state").string() == "directory_active") directories.emplace_back(name,std::move(row));
      } else if (choice_name(name)) {
        auto row = read_json(store.job_fd.fd,name,join(store.job_path,name));
        if (name != "choice-"+choice_key(record_path(row,"source_path"),record_path(row,"original_destination_path"))+".json") fail(store.job_path,"recovery_record_changed");
        choices.push_back(std::move(row));
      }
    }
    validate_data_mapping(store,records); validate_policies(store);
    for (const auto& row : choices) validate_choice(store,row,records);
    // Freeze full directory observations only after the entire destination
    // inventory passes validation. Active timestamps may reflect our children;
    // subsequent resume checks the resulting checkpoint in full.
    for (const auto& [name,row] : directories)
      write_json(store.job_fd.fd,name,checkpoint_directory(store,row),store.job_path);
    if (!closed_attempt.empty()) {
      if (!valid_id(closed_attempt) || !store.header.object.count("actors") || store.header.at("actors").kind != Value::Array)
        fail(store.job_path,"recovery_actor_inventory_changed");
      bool found = false;
      for (auto& actor : store.header.object["actors"].array) if (actor.at("attempt_id").string() == closed_attempt) {
        actor.object["cleaned"] = {Value::Bool,"true",{}, {}}; found = true;
      }
      if (!found) fail(store.job_path,"recovery_actor_inventory_changed");
    }
    store.check(); store.header.object["state"] = text("paused");
    write_json(store.job_fd.fd,".job.json",store.header,store.job_path);
    store.check();
    emit("\"type\":\"pause_checkpoint\",\"recovery_id\":" + quote(id) + ",\"endpoint\":\"local\",\"root_path\":" + app_json::path(root) +
      ",\"job_revision\":" + app_json::serialize(revision(observation(store.job_fd.fd))) + ",\"verification_required\":true");
    return 0;
  } catch (const Error& error) { emit_error(emit,error,id); return RERR_FILESELECT; }
  catch (const std::runtime_error&) { emit_error(emit,Error(root,"recovery_metadata_invalid",0,"invalid recovery metadata"),id); return RERR_FILESELECT; }
}
int cleanup(const std::string& root,const std::string& id,const DestinationRevision& expected,const Emit& emit) {
  try {
    Store store(root,id,false);
    if (!(expected == observation(store.job_fd.fd))) fail(store.job_path,"recovery_cleanup_stale");
    auto files = store.files();
    for (const auto& [name,r] : files) if (!S_ISREG(r.mode) || r.uid != geteuid() || r.links != 1) fail(join(store.job_path,name),"recovery_cleanup_unexpected_entry");
    if (!(expected == observation(store.job_fd.fd))) fail(store.job_path,"recovery_cleanup_stale");
    std::stable_sort(files.begin(),files.end(),[](const auto& a,const auto& b) { return a.first != ".job.json" && b.first == ".job.json"; });
    bool removed_header = false;
    try {
    for (const auto& [name,r] : files) {
      if (g_stop.load()) return RERR_SIGNAL;
      store.check();
      if (!(r == named(store.job_fd.fd,name))) fail(join(store.job_path,name),"recovery_cleanup_stale");
      if (unlinkat(store.job_fd.fd,name.c_str(),0)) fail(join(store.job_path,name),"recovery_cleanup_remove",errno);
      if (name == ".job.json") removed_header = true;
    }
    store.check();
    if (unlinkat(store.vault_fd.fd,id.c_str(),AT_REMOVEDIR)) fail(store.job_path,"recovery_cleanup_directory",errno);
    } catch (...) {
      // Keep a failed cleanup inspectable even when an external writer added
      // a child between the final manifest unlink and empty-only rmdir.
      if (removed_header) {
        try {
          store.check();
          if (!named(store.job_fd.fd,".job.json").exists) write_json(store.job_fd.fd,".job.json",store.header,store.job_path);
        } catch (...) {}
      }
      throw;
    }
    emit("\"type\":\"recovery_cleaned\",\"recovery_id\":" + quote(id) + ",\"endpoint\":\"local\",\"root_path\":" + app_json::path(root)); return 0;
  } catch (const Error& error) { emit_error(emit,error,id); return RERR_PARTIAL; }
  catch (const std::runtime_error&) { emit_error(emit,Error(root,"recovery_metadata_invalid",0,"invalid recovery metadata"),id); return RERR_PARTIAL; }
}
}
