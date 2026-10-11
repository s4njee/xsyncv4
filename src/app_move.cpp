#include "app_move.h"
#include "app_actions.h"
#include "common.h"
#include <algorithm>
#include <cerrno>
#include <map>
#include <mutex>
#include <set>
#include <stdexcept>

namespace app_move {
using app_json::Value;
using app_json::quote;
namespace {
Value string(std::string value) { return {Value::String, std::move(value), {}, {}}; }
Value boolean(bool value) { return {Value::Bool, value ? "true" : "false", {}, {}}; }
Value object() { return {Value::Object, {}, {}, {}}; }
std::string path(const Value& endpoint) { return app_json::unhex(endpoint.at("path").at("bytes_hex").string()); }
std::string parent(const std::string& p) { auto end = p.rfind('/'); return end == 0 ? "/" : p.substr(0, end); }
std::string name(const std::string& p) { return p.substr(p.rfind('/')+1); }
std::string join(const std::string& p, const std::string& n) { return p + (p == "/" ? "" : "/") + n; }
Value at(Value endpoint, const std::string& p) { endpoint.object["path"] = app_json::parse(app_json::path(p)); return endpoint; }
struct Node {
  Value endpoint, revision, destination;
  std::string relative;
  bool directory = false, scope_root = false, copied = false, renamed = false, removed = false;
  std::string reason;
  bool reported = false;
  bool source_known = true;
  bool complete = false, content_published = false;
  Value removal_revision;
};
struct Move {
  const Value& request;
  const Execute& execute;
  const Rename& rename;
  const Emit& emit;
  std::map<std::string, Node> nodes;
  std::map<std::string, Value> parents;
  std::map<std::pair<u64, u64>, u64> removed_links;
  std::set<std::pair<u64, u64>> renamed_inodes;
  std::mutex mutex;
  bool failed = false;
  bool source_matches(const Value& original, const Value& observed) {
    auto expected = app_actions::parse_revision(original), current = app_actions::parse_revision(observed);
    if (expected == current) return true;
    auto key = std::pair<u64, u64>{expected.device, expected.inode};
    auto removed = removed_links.find(key);
    u64 count = removed == removed_links.end() ? 0 : removed->second;
    if (!count && !renamed_inodes.count(key)) return false;
    // Removing/renaming one hard link changes the same inode's ctime and link
    // count at its other names. Data, mtime, permissions and ownership must
    // still match; copy/remove also verifies the actual bytes at both ends.
    return expected.same_object(current) && expected.links >= count && current.links == expected.links-count &&
      expected.mode == current.mode && expected.uid == current.uid && expected.gid == current.gid && expected.flags == current.flags &&
      expected.size == current.size && expected.mtime == current.mtime && expected.mtime_ns == current.mtime_ns;
  }
  Value command(const std::string& op, const Value& endpoint) {
    auto v = object(); v.object = {{"id",string("move-step")}, {"op",string(op)}, {"endpoint",endpoint}}; return v;
  }
  void error(const Value& endpoint, const std::string& reason, int native = 0, bool destination = false) {
    bool unsupported = reason == "unsupported_move_entry" || reason == "remote_safe_move_unavailable";
    bool inventory_limit = reason == "move_inventory_limit";
    if (unsupported || inventory_limit) native = 0;
    const char* category = native == ENOTSUP || native == ENOSYS ? "unsupported_feature" : native == EPERM || native == EACCES ? "permission" :
      native == ENOSPC || native == EDQUOT ? "disk_full" : native == ENOENT ? "missing" : native == ENOTDIR ? "not_directory" :
      !native || native == EEXIST || native == ENOTEMPTY || native == EISDIR ? "conflict" : "filesystem";
    if (unsupported) category = "unsupported_feature";
    if (inventory_limit) category = "selection";
    emit("\"type\":\"error\",\"category\":" + quote(category) +
      ",\"operation\":\"move\",\"endpoint\":" + quote(endpoint.at("kind").string()) + ",\"path\":" + app_json::path(path(endpoint)) +
      ",\"side\":" + quote(destination ? "destination" : "source") + ",\"stage\":\"move\",\"native_code\":" + (native ? quote(std::to_string(native)) : "null") +
      ",\"reason\":" + quote(reason) + ",\"retryable\":false,\"message\":" + quote(reason));
    failed = true;
  }
  void forward_error(std::string fields, bool source = true) {
    auto event = app_json::parse('{'+fields+'}');
    if (event.at("type").string() == "error") {
      event.object["side"] = string(source ? "source" : "destination");
      auto encoded = app_json::serialize(event);
      emit(encoded.substr(1, encoded.size()-2));
    } else if (event.at("type").string() == "auth_prompt" || event.at("type").string() == "diagnostic") emit(std::move(fields));
  }
  bool entry(const Value& endpoint, Value& found, bool missing = false, const std::string& operation = "lstat", bool source = true) {
    bool absent = false;
    int rc = execute(command(operation, endpoint), [&](std::string fields) {
      auto event = app_json::parse('{'+fields+'}'); auto type = event.at("type").string();
      if (type == "entry") found = event.at("entry");
      else if (missing && type == "error" && event.at("category").string() == "missing") absent = true;
      else forward_error(std::move(fields), source);
    });
    if (missing && absent && found.kind == Value::Null) {
      found = object(); found.object["revision"] = app_json::parse("{\"exists\":false}"); return true;
    }
    return rc == 0 && found.kind == Value::Object;
  }
  bool remember_parent(const Value& endpoint) {
    auto p = parent(path(endpoint));
    if (parents.count(p)) return true;
    Value found;
    if (!entry(at(endpoint, p), found) || found.at("type").string() != "directory") return false;
    parents.emplace(p, found.at("revision")); return true;
  }
  bool inventory(const Value& endpoint, const std::string& relative, bool scope_root, unsigned depth = 0, const Value* observed = nullptr) {
    if (g_stop.load()) return false;
    if (nodes.size() >= 100000 || depth >= 256) { error(endpoint, "move_inventory_limit", E2BIG); return false; }
    auto p = path(endpoint);
    if (nodes.count(p)) { error(endpoint, "overlapping_move_selections"); return false; }
    Value found = observed ? *observed : Value{};
    if (!observed && !entry(endpoint, found)) return false;
    auto type = found.at("type").string();
    Node node; node.endpoint = endpoint; node.revision = found.at("revision");
    node.relative = relative; node.directory = type == "directory"; node.scope_root = scope_root;
    nodes.emplace(p, std::move(node));
    if (type != "file" && type != "directory" && type != "symlink") { error(endpoint, "unsupported_move_entry", ENOTSUP); return false; }
    if (scope_root && type != "directory") { error(endpoint, "contents_requires_directory"); return false; }
    if (!remember_parent(endpoint)) return false;
    if (type != "directory") return true;
    parents[p] = found.at("revision");
    std::vector<Value> children; bool oversized = false;
    int rc = execute(command("list", endpoint), [&](std::string fields) {
      auto event = app_json::parse('{'+fields+'}');
      if (event.at("type").string() == "entries") for (const auto& child : event.at("entries").array) {
        if (children.size() + nodes.size() >= 100000) oversized = true;
        else children.push_back(child);
      }
      else forward_error(std::move(fields));
    });
    if (rc != 0) return false;
    if (oversized) { error(endpoint, "move_inventory_limit", E2BIG); return false; }
    for (const auto& child : children) {
      auto child_name = app_json::unhex(child.at("name").at("bytes_hex").string());
      if (child_name.empty() || child_name == "." || child_name == ".." || child_name.find('/') != child_name.npos || child_name.find('\0') != child_name.npos)
        throw std::runtime_error("unsafe move inventory name");
      auto child_path = join(p, child_name);
      if (!inventory(at(endpoint, child_path), relative.empty() ? child_name : join(relative, child_name), false, depth+1, &child)) return false;
      if (!(app_actions::parse_revision(nodes.at(child_path).revision) == app_actions::parse_revision(child.at("revision")))) {
        error(endpoint, "source_changed_during_inventory"); return false;
      }
    }
    Value after;
    if (!entry(endpoint, after) || !(app_actions::parse_revision(found.at("revision")) == app_actions::parse_revision(after.at("revision")))) {
      error(endpoint, "source_changed_during_inventory"); return false;
    }
    return true;
  }
  bool verify(Node& node) {
    Value source, destination;
    if (!entry(node.endpoint, source, false, "fingerprint")) {
      node.source_known = false; node.reason = "source_verification_failed"; return false;
    }
    if (!source_matches(node.revision, source.at("revision"))) {
      node.reason = "source_changed_after_copy"; return false;
    }
    if (!entry(node.destination, destination, false, "fingerprint", false) ||
        source.at("fingerprint").at("hex").string() != destination.at("fingerprint").at("hex").string() ||
        source.at("type").string() != destination.at("type").string()) {
      node.complete = false; node.reason = "destination_verification_failed"; return false;
    }
    for (const auto* entry : {&source, &destination}) {
      const auto& digest = entry->at("fingerprint");
      if (digest.at("algorithm").string() != "xxh3-128" || digest.at("hex").string().size() != 32 || app_json::unhex(digest.at("hex").string()).size() != 16) {
        node.reason = "invalid_move_fingerprint"; return false;
      }
    }
    // The receiver's terminal result also confirms the requested metadata.
    if ((request.at("options").at("preserve_permissions").boolean() && source.at("mode").string() != destination.at("mode").string()) ||
        (request.at("options").at("preserve_times").boolean() && (source.at("mtime_seconds").string() != destination.at("mtime_seconds").string() ||
        source.at("mtime_nanoseconds").string() != destination.at("mtime_nanoseconds").string()))) {
      node.complete = false; node.reason = "destination_metadata_changed"; return false;
    }
    node.removal_revision = source.at("revision");
    return true;
  }
  bool remove(Node& node) {
    if (g_stop.load()) { node.reason = "cancelled_before_remove"; return false; }
    if (!node.directory) {
      emit("\"type\":\"phase\",\"phase\":\"verifying_move\"");
      if (!verify(node)) { error(node.endpoint, node.reason); return false; }
    } else {
      Value destination;
      if (!entry(node.destination, destination, false, "lstat", false) || destination.at("type").string() != "directory") {
        node.complete = false; node.reason = "destination_directory_changed"; error(node.destination, node.reason, 0, true); return false;
      }
      auto original = app_actions::parse_revision(node.revision), current = app_actions::parse_revision(destination.at("revision"));
      if ((request.at("options").at("preserve_permissions").boolean() && (original.mode & 07777) != (current.mode & 07777)) ||
          (request.at("options").at("preserve_times").boolean() && (original.mtime != current.mtime || original.mtime_ns != current.mtime_ns))) {
        node.complete = false; node.reason = "destination_metadata_changed"; error(node.destination, node.reason, 0, true); return false;
      }
    }
    auto p = path(node.endpoint), folder = parent(p);
    Value directory, source;
    if (!entry(at(node.endpoint, folder), directory) || !entry(node.endpoint, source)) return false;
    auto expected_parent = app_actions::parse_revision(parents.at(folder));
    auto actual_parent = app_actions::parse_revision(directory.at("revision"));
    auto expected = app_actions::parse_revision(node.revision), actual = app_actions::parse_revision(source.at("revision"));
    bool valid = expected_parent.same_object(actual_parent);
    if (node.directory) valid = valid && expected.same_object(actual) && expected.mode == actual.mode && expected.uid == actual.uid && expected.gid == actual.gid && expected.flags == actual.flags;
    else valid = valid && app_actions::parse_revision(node.removal_revision) == actual;
    if (!valid) { node.reason = "source_changed_before_remove"; error(node.endpoint, node.reason); return false; }
    auto request = command("delete", at(node.endpoint, folder));
    request.object["parent_revision"] = directory.at("revision");
    request.object["recursive"] = boolean(false);
    auto item = object(); item.object = {{"name",app_json::parse(app_json::path(name(p)))}, {"expected_revision",source.at("revision")}};
    request.object["items"] = {Value::Array, {}, {item}, {}};
    bool removed = false;
    int rc = execute(request, [&](std::string fields) {
      auto event = app_json::parse('{'+fields+'}'); auto type = event.at("type").string();
      if (type == "action_result") removed = event.at("removed").boolean() && event.at("status").string() == "success";
      else if (type == "error" || type == "invalidate" || type == "auth_prompt" || type == "diagnostic") emit(std::move(fields));
    });
    node.removed = removed;
    if (removed && !node.directory) ++removed_links[{expected.device, expected.inode}];
    if (rc || !removed) { node.reason = "source_removal_failed"; failed = true; return false; }
    return true;
  }
  void outcome(Node& node) {
    if (node.reported) return;
    node.reported = true;
    bool remaining = !node.removed && !node.scope_root;
    emit("\"type\":\"move_result\",\"item_id\":" + quote(app_json::hex(node.relative)) +
      ",\"source_path\":" + app_json::path(path(node.endpoint)) + ",\"source_endpoint\":" + quote(node.endpoint.at("kind").string()) +
      ",\"destination_path\":" + (node.destination.kind == Value::Null ? "null" : app_json::path(path(node.destination))) +
      ",\"destination_endpoint\":" + quote(request.at("destination").at("kind").string()) +
      ",\"status\":" + quote(node.removed ? node.reason.empty() ? "success" : "partial_failure" : node.scope_root && node.copied ? "success" : node.copied ? "partial_failure" : "failure") +
      ",\"copied\":" + (node.copied ? "true" : "false") + ",\"renamed\":" + (node.renamed ? "true" : "false") +
      ",\"destination_completed\":" + (node.complete ? "true" : "false") + ",\"content_published\":" + (node.content_published ? "true" : "false") +
      ",\"removed\":" + (node.removed ? "true" : "false") + ",\"remaining\":" + (!node.source_known && remaining ? "null" : remaining ? "true" : "false") +
      ",\"scope_root\":" + (node.scope_root ? "true" : "false") + ",\"reason\":" + (node.reason.empty() ? "null" : quote(node.reason)));
  }
};
}
void not_started(const Value& request, const std::string& reason, const Emit& emit) {
  for (const auto& selected : request.at("sources").array) {
    bool contents = selected.at("mode").string() == "contents";
    auto relative = contents ? "" : selected.object.count("destination_name") ? app_json::unhex(selected.at("destination_name").at("bytes_hex").string()) : name(path(selected.at("endpoint")));
    emit("\"type\":\"move_result\",\"item_id\":" + quote(app_json::hex(relative)) +
      ",\"source_path\":" + app_json::serialize(selected.at("endpoint").at("path")) + ",\"source_endpoint\":" + quote(selected.at("endpoint").at("kind").string()) +
      ",\"destination_path\":null,\"destination_endpoint\":" + quote(request.at("destination").at("kind").string()) +
      ",\"status\":\"failure\",\"copied\":false,\"renamed\":false,\"removed\":false,\"remaining\":null,\"destination_completed\":false,\"content_published\":false,\"scope_root\":" +
      (contents ? "true" : "false") + ",\"reason\":" + quote(reason));
  }
  auto total = quote(std::to_string(request.at("sources").array.size()));
  emit("\"type\":\"move_summary\",\"items_copied\":\"0\",\"items_removed\":\"0\",\"items_remaining\":\"0\",\"items_unknown\":" + total + ",\"items_renamed\":\"0\",\"items_total\":" + total);
}
int run(const Value& request, const Execute& execute, const Rename& rename, const Emit& emit) {
  Move move{request, execute, rename, emit, {}, {}, {}, {}, {}};
  const auto& selections = request.at("sources").array;
  const auto& destination = request.at("destination");
  Value destination_info;
  bool ready = move.entry(destination, destination_info, false, "lstat", false) && destination_info.at("type").string() == "directory" &&
    app_actions::parse_revision(request.at("destination_parent_revision")) == app_actions::parse_revision(destination_info.at("revision"));
  if (!ready) move.error(destination, "stale_destination_parent", 0, true);
  for (const auto& selected : selections) {
    auto endpoint = selected.at("endpoint"); bool contents = selected.at("mode").string() == "contents";
    auto relative = contents ? "" : selected.object.count("destination_name") ? app_json::unhex(selected.at("destination_name").at("bytes_hex").string()) : name(path(endpoint));
    if (!move.inventory(endpoint, relative, contents)) {
      ready = false;
      if (!move.nodes.count(path(endpoint))) {
        Node unknown; unknown.endpoint = endpoint; unknown.relative = relative; unknown.revision = selected.at("expected_revision");
        unknown.source_known = false; unknown.reason = "source_preflight_failed";
        move.nodes.emplace(path(endpoint), std::move(unknown));
      }
    }
    auto found = move.nodes.find(path(endpoint));
    if (found != move.nodes.end() && !(app_actions::parse_revision(selected.at("expected_revision")) == app_actions::parse_revision(found->second.revision))) {
      move.error(endpoint, "stale_move_selection"); ready = false;
    }
  }
  // Reject physical directory aliases and destinations inside the selected
  // tree before any native rename or copy can change the plan.
  if (ready && destination.at("kind").string() == selections.front().at("endpoint").at("kind").string()) {
    auto target = app_actions::parse_revision(destination_info.at("revision"));
    std::set<std::pair<u64, u64>> directories;
    for (const auto& [p, node] : move.nodes) if (node.directory) {
      auto revision = app_actions::parse_revision(node.revision);
      if (!directories.emplace(revision.device, revision.inode).second || revision.same_object(target)) {
        move.error(node.endpoint, "overlapping_move_selections"); ready = false; break;
      }
    }
    for (const auto& selected : selections) {
      if (!ready) break;
      const auto& source = selected.at("endpoint");
      const auto& node = move.nodes.at(path(source));
      if (node.scope_root) continue;
      auto target_endpoint = at(destination, join(path(destination), node.relative));
      Value observed;
      if (!move.entry(target_endpoint, observed, true, "lstat", false)) { ready = false; break; }
      auto revision = app_actions::parse_revision(observed.at("revision"));
      for (const auto& [p, other] : move.nodes) if (path(target_endpoint) == p ||
          (p != path(source) && revision.same_object(app_actions::parse_revision(other.revision)))) {
        move.error(target_endpoint, "move_target_aliases_selected_source", 0, true); ready = false; break;
      }
    }
  }
  if (ready) {
    const Value* remote = destination.at("kind").string() == "ssh" ? &destination : nullptr;
    for (const auto& selected : selections) if (selected.at("endpoint").at("kind").string() == "ssh") remote = &selected.at("endpoint");
    if (remote) {
      bool supported = false;
      int code = execute(move.command("probe", *remote), [&](std::string fields) {
        auto event = app_json::parse('{'+fields+'}');
        if (event.at("type").string() == "capabilities") {
          auto feature = event.object.find("safe_move");
          supported = feature != event.object.end() && feature->second.kind == Value::String && feature->second.string() == "1";
        } else move.forward_error(std::move(fields), remote != &destination);
      });
      if (code || !supported) { move.error(*remote, "remote_safe_move_unavailable", ENOTSUP, remote == &destination); ready = false; }
    }
  }
  for (const auto& [p, node] : move.nodes) {
    emit("\"type\":\"move_discovered\",\"item_id\":" + quote(app_json::hex(node.relative)) +
      ",\"source_path\":" + app_json::path(p) + ",\"source_endpoint\":" + quote(node.endpoint.at("kind").string()) +
      ",\"destination_path\":" + app_json::path(node.relative.empty() ? path(destination) : join(path(destination), node.relative)) +
      ",\"destination_endpoint\":" + quote(destination.at("kind").string()) + ",\"scope_root\":" + (node.scope_root ? "true" : "false"));
  }
  Value copy = request; copy.object["op"] = string("copy");
  if (ready && destination.at("kind").string() == "local" && request.at("options").at("on_conflict").string() != "ask") {
    std::vector<Value> pending;
    for (const auto& selected : selections) {
      auto endpoint = selected.at("endpoint"); auto source_path = path(endpoint);
      auto& node = move.nodes.at(source_path);
      if (endpoint.at("kind").string() != "local" || node.scope_root) { pending.push_back(selected); continue; }
      auto target = at(destination, join(path(destination), node.relative));
      if (path(target) == source_path) { move.error(endpoint, "source_destination_overlap"); ready = false; break; }
      Value target_info, source_parent, destination_parent;
      if (!move.entry(target, target_info, true, "lstat", false) || !move.entry(at(endpoint, parent(source_path)), source_parent) ||
          !move.entry(destination, destination_parent, false, "lstat", false)) { ready = false; break; }
      auto target_revision = app_actions::parse_revision(target_info.at("revision"));
      bool exists = target_revision.exists;
      bool alias = false;
      for (const auto& [p, other] : move.nodes) if (p != source_path && target_revision.same_object(app_actions::parse_revision(other.revision))) alias = true;
      if (alias) { move.error(target, "move_target_aliases_selected_source", 0, true); ready = false; break; }
      auto source_revision = app_actions::parse_revision(node.revision);
      Value current_source;
      if (!move.entry(endpoint, current_source) || !move.source_matches(node.revision, current_source.at("revision"))) {
        move.error(endpoint, "source_changed_before_rename"); ready = false; break;
      }
      if (!app_actions::parse_revision(move.parents.at(parent(source_path))).same_object(app_actions::parse_revision(source_parent.at("revision"))) ||
          !app_actions::parse_revision(destination_info.at("revision")).same_object(app_actions::parse_revision(destination_parent.at("revision")))) {
        move.error(endpoint, "move_parent_changed"); ready = false; break;
      }
      if (exists && (request.at("options").at("on_conflict").string() == "skip" || node.directory ||
          (source_revision.mode & S_IFMT) != (target_revision.mode & S_IFMT))) {
        pending.push_back(selected); continue;
      }
      endpoint.object["parent_revision"] = source_parent.at("revision");
      target.object["parent_revision"] = destination_parent.at("revision");
      auto result = rename(endpoint, target, current_source.at("revision"), target_info.at("revision"), exists);
      if (!result.renamed && (result.error == EXDEV || result.error == ENOTSUP || result.error == ENOSYS)) { pending.push_back(selected); continue; }
      if (!result.renamed && (result.error || result.stale)) {
        move.error(endpoint, result.stale ? "native_move_stale" : "native_move_failed", result.error);
        node.reason = result.stale ? "native_move_stale" : "native_move_failed";
        // A native error must not turn into an unrequested overwrite retry.
        continue;
      }
      if (!node.directory) move.renamed_inodes.emplace(source_revision.device, source_revision.inode);
      for (auto& [p, descendant] : move.nodes) if (p == source_path || (node.directory && p.starts_with(source_path + '/'))) {
        descendant.renamed = descendant.removed = true;
        descendant.complete = !result.error && !result.stale;
        if (result.error || result.stale) descendant.reason = "native_move_changed_after_rename";
        descendant.destination = at(destination, join(path(destination), descendant.relative));
        move.outcome(descendant);
      }
      if (result.error || result.stale) move.error(endpoint, "native_move_changed_after_rename", result.error);
      emit("\"type\":\"invalidate\",\"endpoint\":\"local\",\"path\":" + app_json::serialize(endpoint.at("path")) +
        ",\"parent_path\":" + app_json::path(parent(source_path)) + ",\"destination_path\":" + app_json::serialize(target.at("path")));
      emit("\"type\":\"invalidate\",\"endpoint\":\"local\",\"path\":" + app_json::serialize(target.at("path")) + ",\"parent_path\":" + app_json::serialize(destination.at("path")));
    }
    copy.object["sources"].array = std::move(pending);
  }
  int rc = ready && copy.at("sources").array.empty() ? 0 : ready ? execute(copy, [&](std::string fields) {
    auto event = app_json::parse('{'+fields+'}');
    if (event.at("type").string() == "item_result") {
      auto p = app_json::unhex(event.at("source_path").at("bytes_hex").string());
      std::lock_guard<std::mutex> guard(move.mutex);
      auto found = move.nodes.find(p);
      if (found != move.nodes.end()) {
        auto& node = found->second;
        node.complete = event.at("status").string() == "success" && event.at("metadata_complete").kind == Value::Bool && event.at("metadata_complete").boolean();
        node.content_published = event.at("content_published").boolean();
        node.copied = node.complete || node.content_published;
        if (event.at("destination_path").kind != Value::Null) {
          node.destination = destination; node.destination.object["path"] = event.at("destination_path");
        }
        if (!node.complete) node.reason = "destination_not_completed";
      }
    }
    emit(std::move(fields));
  }) : RERR_FILESELECT;
  // A failed/cancelled copy never grants any source-removal permission.
  if (rc == 0 && !g_stop.load()) {
    emit("\"type\":\"phase\",\"phase\":\"removing_move_sources\"");
    std::vector<Node*> ordered;
    for (auto& [path, node] : move.nodes) ordered.push_back(&node);
    std::sort(ordered.begin(), ordered.end(), [](const Node* a, const Node* b) {
      auto pa = path(a->endpoint), pb = path(b->endpoint);
      return std::count(pa.begin(), pa.end(), '/') > std::count(pb.begin(), pb.end(), '/');
    });
    for (auto node : ordered) {
      if (!node->removed && !node->scope_root && node->complete && !g_stop.load()) move.remove(*node);
      move.outcome(*node);
    }
  } else for (auto& [path, node] : move.nodes) {
    node.reason = g_stop.load() ? "cancelled_before_remove" : ready ? "copy_job_failed" : "move_preflight_failed";
    move.outcome(node);
  }
  u64 copied = 0, removed = 0, remaining = 0, unknown = 0, renamed = 0;
  for (auto& [path, node] : move.nodes) {
    copied += node.copied; removed += node.removed; renamed += node.renamed;
    remaining += !node.removed && !node.scope_root && node.source_known;
    unknown += !node.removed && !node.scope_root && !node.source_known;
  }
  emit("\"type\":\"move_summary\",\"items_copied\":" + quote(std::to_string(copied)) + ",\"items_removed\":" + quote(std::to_string(removed)) +
    ",\"items_remaining\":" + quote(std::to_string(remaining)) + ",\"items_unknown\":" + quote(std::to_string(unknown)) +
    ",\"items_renamed\":" + quote(std::to_string(renamed)) + ",\"items_total\":" + quote(std::to_string(move.nodes.size())));
  if (g_stop.load()) return RERR_SIGNAL;
  return rc ? removed ? RERR_PARTIAL : rc : remaining || unknown || move.failed ? RERR_PARTIAL : 0;
}
}
