#include "app_actions.h"
#include "destination.h"
#include <charconv>
#include <dirent.h>
#include <set>
#include <stdexcept>
#include <cerrno>

namespace app_actions {
using app_json::Value;
using app_json::quote;
namespace {
template<class T> T decimal(const Value& value) {
  auto s = value.string(); T n{};
  auto [end, error] = std::from_chars(s.data(), s.data()+s.size(), n);
  if (error != std::errc{} || end != s.data()+s.size() || s.empty())
    throw std::runtime_error("invalid action decimal string");
  return n;
}
void fields(const Value& v, std::initializer_list<std::string_view> allowed) {
  if (v.kind != Value::Object) throw std::runtime_error("action object required");
  for (const auto& [key, value] : v.object) {
    bool found = false;
    for (auto name : allowed) if (name == key) found = true;
    if (!found) throw std::runtime_error("unsupported action field: " + key);
  }
}
DestinationRevision revision(const Value& v) {
  fields(v, {"exists", "device", "inode", "links", "mode", "uid", "gid", "flags", "size",
             "mtime_seconds", "mtime_nanoseconds", "ctime_seconds", "ctime_nanoseconds"});
  if (!v.at("exists").boolean()) {
    if (v.object.size() != 1) throw std::runtime_error("absent revision only accepts exists");
    return DestinationRevision::absent();
  }
  DestinationRevision r; r.known = r.exists = true;
  r.device = decimal<u64>(v.at("device")); r.inode = decimal<u64>(v.at("inode"));
  r.links = decimal<u64>(v.at("links")); r.mode = decimal<u32>(v.at("mode"));
  r.uid = decimal<u32>(v.at("uid")); r.gid = decimal<u32>(v.at("gid")); r.flags = decimal<u32>(v.at("flags"));
  r.size = decimal<i64>(v.at("size")); r.mtime = decimal<i64>(v.at("mtime_seconds"));
  r.ctime = decimal<i64>(v.at("ctime_seconds")); r.mtime_ns = decimal<u32>(v.at("mtime_nanoseconds"));
  r.ctime_ns = decimal<u32>(v.at("ctime_nanoseconds"));
  if (r.mtime_ns >= 1000000000 || r.ctime_ns >= 1000000000) throw std::runtime_error("invalid revision nanoseconds");
  return r;
}
std::string component(const Value& v) {
  auto s = app_json::unhex(v.at("bytes_hex").string());
  if (s.empty() || s.size() > 255 || s == "." || s == ".." || s.find('/') != s.npos || s.find('\0') != s.npos)
    throw std::runtime_error("action name must be a literal component of 1 to 255 bytes");
  return s;
}
struct FD {
  int value = -1;
  explicit FD(int fd) : value(fd) {}
  ~FD() { if (value >= 0) close(value); }
};
struct Node { std::string relative; DestinationRevision expected; };
struct Context {
  const Request& request;
  int root;
  const std::function<bool()>& root_valid;
  const std::function<void(std::string)>& emit;
  u64 changed = 0, failed = 0;
  std::string path(const std::string& name) { return request.root + (request.root == "/" ? "" : "/") + name; }
  void error(const std::string& name, int code, const std::string& reason = {}) {
    const char* category = !reason.empty() || code == EEXIST || code == ENOTEMPTY || code == EISDIR ? "conflict" :
      code == ENOENT ? "missing" : code == EPERM || code == EACCES ? "permission" :
      code == ENOSPC || code == EDQUOT ? "disk_full" : code == ENOTSUP || code == ENOSYS ? "unsupported_feature" : "filesystem";
    emit("\"type\":\"error\",\"category\":" + quote(category) + ",\"operation\":" + quote(request.operation) +
      ",\"endpoint\":\"local\",\"path\":" + app_json::path(path(name)) + ",\"item_id\":" + quote(app_json::hex(name)) +
      ",\"stage\":\"action\",\"native_code\":" + (code ? quote(std::to_string(code)) : "null") +
      ",\"reason\":" + (reason.empty() ? "null" : quote(reason)) + ",\"retryable\":false,\"message\":" +
      quote(reason.empty() ? strerror(code) : reason));
  }
  void result(const std::string& name, bool success, bool modified, const std::string& destination = {}) {
    if (!success) ++failed;
    if (modified) ++changed;
    emit("\"type\":\"action_result\",\"operation\":" + quote(request.operation) +
      ",\"item_id\":" + quote(app_json::hex(name)) + ",\"endpoint\":\"local\",\"path\":" + app_json::path(path(name)) +
      ",\"destination_path\":" + (destination.empty() ? "null" : app_json::path(path(destination))) +
      ",\"status\":" + quote(success ? "success" : modified ? "partial_failure" : "failure") +
      ",\"changed\":" + (modified ? "true" : "false") + ",\"removed\":" + (modified && request.operation == "delete" ? "true" : "false") +
      ",\"metadata_complete\":" + (request.operation == "metadata" ? success ? "true" : "false" : "null") +
      ",\"undoable\":false");
    auto parent_path = path(name).substr(0, path(name).rfind('/'));
    if (modified) emit("\"type\":\"invalidate\",\"endpoint\":\"local\",\"path\":" + app_json::path(path(name)) +
      ",\"parent_path\":" + app_json::path(parent_path.empty() ? "/" : parent_path) + ",\"destination_path\":" +
      (destination.empty() ? "null" : app_json::path(path(destination))));
  }
  bool observe(int parent, const std::string& name, DestinationRevision& observed, const std::string& relative) {
    struct stat st;
    if (fstatat(parent, name.c_str(), &st, AT_SYMLINK_NOFOLLOW) == 0) observed = DestinationRevision::from(st);
    else if (errno == ENOENT) observed = DestinationRevision::absent();
    else { error(relative, errno); return false; }
    return true;
  }
  bool check(int parent, const std::string& name, const DestinationRevision& expected,
             const std::string& relative, bool identity = false) {
    if (g_stop.load() || !root_valid()) return false;
    DestinationRevision current;
    if (!observe(parent, name, current, relative)) return false;
    if (identity ? expected.same_object(current) : expected == current) return true;
    error(relative, 0, "stale_entry"); return false;
  }
  // Complete the bounded inventory before removing anything. Symlinks are leaves.
  bool scan(int parent, const std::string& name, const std::string& relative,
            const DestinationRevision& expected, std::vector<Node>& nodes, unsigned depth = 0) {
    if (nodes.size() >= 100000 || depth >= 256) { error(relative, E2BIG); return false; }
    if (!check(parent, name, expected, relative)) return false;
    nodes.push_back({relative, expected});
    if (!S_ISDIR(expected.mode)) return true;
    FD fd(openat(parent, name.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (fd.value < 0) { error(relative, errno); return false; }
    struct stat st;
    if (fstat(fd.value, &st)) { error(relative, errno); return false; }
    if (!(expected == DestinationRevision::from(st))) { error(relative, 0, "stale_entry"); return false; }
    DIR* dir = fdopendir(dup(fd.value));
    if (!dir) { error(relative, errno); return false; }
    bool ok = true;
    while (ok && !g_stop.load()) {
      errno = 0; auto entry = readdir(dir);
      if (!entry) { if (errno) { error(relative, errno); ok = false; } break; }
      std::string child = entry->d_name;
      if (child == "." || child == "..") continue;
      auto child_path = relative + '/' + child;
      DestinationRevision rev;
      ok = observe(fd.value, child, rev, child_path);
      if (ok && !rev.exists) { error(child_path, 0, "incomplete_listing"); ok = false; }
      if (ok) ok = scan(fd.value, child, child_path, rev, nodes, depth+1);
    }
    closedir(dir);
    return ok && check(parent, name, expected, relative);
  }
  // Rewalk every ancestor from the pinned root and compare its identity. Never
  // follow symlinks or mutate a detached ancestor retained from the inventory.
  int parent(const Node& node, const std::map<std::string, DestinationRevision>& dirs, std::string& name) {
    int fd = dup(root);
    if (fd < 0) { error(node.relative, errno); return -1; }
    size_t start = 0, slash; std::string prefix;
    while ((slash = node.relative.find('/', start)) != std::string::npos) {
      auto part = node.relative.substr(start, slash-start);
      prefix += (prefix.empty() ? "" : "/") + part;
      auto found = dirs.find(prefix);
      if (found == dirs.end() || !check(fd, part, found->second, prefix, true)) { close(fd); return -1; }
      int next = openat(fd, part.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
      if (next < 0) { error(prefix, errno); close(fd); return -1; }
      struct stat st;
      if (fstat(next, &st) || !found->second.same_object(DestinationRevision::from(st))) {
        error(prefix, 0, "stale_ancestor"); close(next); close(fd); return -1;
      }
      close(fd); fd = next; start = slash+1;
    }
    name = node.relative.substr(start); return fd;
  }
  bool remove(const Item& item) {
    std::vector<Node> nodes;
    if (request.recursive && S_ISDIR(item.expected.mode)) {
      emit("\"type\":\"phase\",\"phase\":\"scanning_delete\"");
      if (!scan(root, item.name, item.name, item.expected, nodes)) return false;
    } else nodes.push_back({item.name, item.expected});
    std::map<std::string, DestinationRevision> dirs;
    for (const auto& node : nodes) if (S_ISDIR(node.expected.mode)) dirs.emplace(node.relative, node.expected);
    // Revalidate the whole inventory before the first destructive operation.
    for (const auto& node : nodes) {
      std::string name; FD fd(parent(node, dirs, name));
      if (fd.value < 0 || !check(fd.value, name, node.expected, node.relative)) return false;
    }
    bool ok = true;
    emit("\"type\":\"phase\",\"phase\":\"deleting\"");
    for (auto i = nodes.rbegin(); i != nodes.rend(); ++i) {
      if (g_stop.load()) return false;
      std::string name; FD fd(parent(*i, dirs, name));
      bool removed = fd.value >= 0 && check(fd.value, name, i->expected, i->relative, S_ISDIR(i->expected.mode));
      if (removed && unlinkat(fd.value, name.c_str(), S_ISDIR(i->expected.mode) ? AT_REMOVEDIR : 0)) {
        error(i->relative, errno); removed = false;
      }
      bool valid = removed && root_valid();
      result(i->relative, valid, removed);
      ok = ok && valid;
    }
    return ok;
  }
};
}
bool operation(std::string_view op) { return op == "mkdir" || op == "rename" || op == "delete" || op == "metadata"; }
DestinationRevision parse_revision(const Value& value) { return revision(value); }
Request parse(const Value& v, const std::string& root) {
  fields(v, {"id", "op", "endpoint", "parent_revision", "items", "recursive", "replace", "mode", "mtime"});
  Request r; r.operation = v.at("op").string(); r.root = root; r.parent = revision(v.at("parent_revision"));
  if (!r.parent.exists || !S_ISDIR(r.parent.mode)) throw std::runtime_error("parent_revision must describe a real directory");
  if (v.object.count("recursive")) {
    if (r.operation != "delete") throw std::runtime_error("recursive only applies to delete");
    r.recursive = v.at("recursive").boolean();
  }
  if (r.operation == "delete" && !v.object.count("recursive")) throw std::runtime_error("delete requires explicit recursive scope");
  if (v.object.count("replace")) {
    if (r.operation != "rename") throw std::runtime_error("replace only applies to rename");
    r.replace = v.at("replace").boolean();
  }
  if (r.operation == "rename" && !v.object.count("replace")) throw std::runtime_error("rename requires explicit replace policy");
  if (v.object.count("mode")) {
    if (r.operation != "mkdir" && r.operation != "metadata") throw std::runtime_error("mode not applicable");
    auto mode = decimal<u32>(v.at("mode"));
    if (mode > 07777) throw std::runtime_error("mode out of range");
    r.mode = mode;
  }
  if (v.object.count("mtime")) {
    if (r.operation != "metadata") throw std::runtime_error("mtime not applicable");
    const auto& t = v.at("mtime"); fields(t, {"seconds", "nanoseconds"});
    auto ns = decimal<u32>(t.at("nanoseconds"));
    if (ns >= 1000000000) throw std::runtime_error("mtime nanoseconds out of range");
    r.mtime = timespec{decimal<time_t>(t.at("seconds")), (long)ns};
  }
  if (r.operation == "metadata" && !r.mode && !r.mtime) throw std::runtime_error("metadata requires mode or mtime");
  const auto& items = v.at("items");
  if (items.kind != Value::Array || items.array.empty() || items.array.size() > 1024) throw std::runtime_error("actions require 1 to 1024 items");
  std::set<std::string> names, destinations;
  for (const auto& value : items.array) {
    fields(value, r.operation == "rename" ? std::initializer_list<std::string_view>{"name", "expected_revision", "destination_name", "destination_revision"} :
      std::initializer_list<std::string_view>{"name", "expected_revision"});
    Item item; item.name = component(value.at("name")); item.expected = revision(value.at("expected_revision"));
    if (!names.insert(item.name).second) throw std::runtime_error("action selections must be distinct");
    if (item.expected.exists == (r.operation == "mkdir")) throw std::runtime_error("mkdir requires absent revision; other actions require existing revision");
    if (r.operation == "rename") {
      item.destination = component(value.at("destination_name")); item.destination_expected = revision(value.at("destination_revision"));
      if (item.destination == item.name || !destinations.insert(item.destination).second) throw std::runtime_error("rename targets must be distinct new names");
      if (!r.replace && item.destination_expected.exists) throw std::runtime_error("no-replace rename requires an absent target revision");
    }
    r.items.push_back(std::move(item));
  }
  for (const auto& destination : destinations) if (names.count(destination)) throw std::runtime_error("rename targets cannot be other selected sources");
  // Byte-distinct names can be aliases on the filesystem. Do not overwrite
  // another selected source through case folding, normalization or hard links.
  if (r.operation == "rename") for (const auto& target : r.items) for (const auto& source : r.items) {
    if (&target != &source && target.destination_expected.exists &&
        target.destination_expected.same_object(source.expected))
      throw std::runtime_error("rename target aliases another selected source");
  }
  return r;
}
int run(const Request& r, int root, const std::function<bool()>& root_valid, const std::function<void(std::string)>& emit) {
  Context c{r, root, root_valid, emit};
  struct stat parent;
  bool ready = fstat(root, &parent) == 0 && r.parent == DestinationRevision::from(parent) && root_valid();
  for (const auto& item : r.items) {
    if (g_stop.load()) return RERR_SIGNAL;
    bool ok = ready, changed = false;
    if (!ready) c.error(item.name, 0, root < 0 ? "root_unavailable" : "stale_parent");
    else ok = c.check(root, item.name, item.expected, item.name);
    if (ok && r.operation == "delete") {
      u64 before = c.failed;
      ok = c.remove(item);
      // remove emits each observed outcome; an inventory failure emits none.
      if (!ok && before == c.failed) c.result(item.name, false, false);
      continue;
    }
    if (ok && r.operation == "mkdir") {
      if (mkdirat(root, item.name.c_str(), r.mode.value_or(0777))) { c.error(item.name, errno); ok = false; }
      else changed = true;
    } else if (ok && r.operation == "rename") {
      ok = c.check(root, item.destination, item.destination_expected, item.destination) && c.check(root, item.name, item.expected, item.name);
      if (ok && S_ISREG(item.expected.mode) && item.expected.links > 1 && item.expected.same_object(item.destination_expected)) {
        c.error(item.name, 0, "same_object_target"); ok = false;
      }
      if (ok) {
        int rc = r.replace && item.destination_expected.exists ? renameat(root, item.name.c_str(), root, item.destination.c_str()) :
          destination_publish_noreplace(root, item.name.c_str(), item.destination.c_str());
        if (rc) { c.error(item.name, errno); ok = false; }
        else changed = true;
      }
    } else if (ok && r.operation == "metadata") {
      if (!S_ISREG(item.expected.mode) && !S_ISDIR(item.expected.mode)) { c.error(item.name, ENOTSUP); ok = false; }
      else {
        FD fd(openat(root, item.name.c_str(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC));
        struct stat st;
        if (fd.value < 0 || fstat(fd.value, &st)) { c.error(item.name, errno); ok = false; }
        else if (!(item.expected == DestinationRevision::from(st)) || !c.check(root, item.name, item.expected, item.name)) {
          c.error(item.name, 0, "stale_entry"); ok = false;
        } else {
          if (r.mode) {
            if (fchmod(fd.value, *r.mode)) { c.error(item.name, errno); ok = false; }
            else changed = true;
          }
          if (ok && r.mtime) {
            timespec times[2]{{0, UTIME_OMIT}, *r.mtime};
            if (futimens(fd.value, times)) { c.error(item.name, errno); ok = false; }
            else changed = true;
          }
        }
      }
    }
    if (changed) {
      ok = root_valid() && ok;
      if (ok && r.operation == "metadata") ok = c.check(root, item.name, item.expected, item.name, true);
      if (ok && r.operation == "rename") ok = c.check(root, item.destination, item.expected, item.destination, true);
    }
    c.result(item.name, ok, changed, item.destination);
  }
  emit("\"type\":\"summary\",\"items_changed\":" + quote(std::to_string(c.changed)) + ",\"items_failed\":" + quote(std::to_string(c.failed)));
  return c.failed ? RERR_PARTIAL : 0;
}
}
