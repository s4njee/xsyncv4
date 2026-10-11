#include "app.h"
#include "app_json.h"
#include "app_ssh.h"
#include "app_conflict.h"
#include "app_actions.h"
#include "app_move.h"
#include "app_partials.h"
#include "app_actor.h"
#include "app_preflight.h"
#include "app_preview.h"
#include "app_preview_guard.h"
#include "app_preview_manifest.h"
#include "engine.h"
#include "output.h"
#include "progress.h"
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <mutex>
#include <set>
#include <stdexcept>
#include <system_error>
#include <thread>
#include <chrono>
#include <optional>
#include <algorithm>
#define XXH_INLINE_ALL
#include <xxhash.h>

namespace {
using app_json::Value;
using app_json::quote;
constexpr size_t FRAME_LIMIT = 1024*1024;
constexpr u64 CANCEL_NS = 2000000000ULL;
volatile sig_atomic_t interrupted = 0;
struct RequestError : std::runtime_error {
  std::string category;
  RequestError(std::string category, const std::string& message)
    : std::runtime_error(message), category(std::move(category)) {}
};
void parent_signal(int) { interrupted = 1; }
void child_signal(int) { g_stop.store(1); }
void nonblocking(int fd) { int flags = fcntl(fd, F_GETFL); if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) throw std::runtime_error("cannot configure pipe"); }

bool send_frame(int fd, std::string_view frame) {
  u64 deadline = now_ns() + CANCEL_NS;
  while (!frame.empty()) {
    ssize_t n = write(fd, frame.data(), frame.size());
    if (n > 0) { frame.remove_prefix((size_t)n); continue; }
    if (n < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) return false;
    if (now_ns() > deadline) return false;
    pollfd p{fd, POLLOUT, 0}; poll(&p, 1, 50);
  }
  return true;
}
struct Reader {
  int fd;
  std::string pending;
  bool eof = false;
  void read_ready() {
    char buffer[8192];
    ssize_t n = read(fd, buffer, sizeof buffer);
    if (n > 0) {
      pending.append(buffer, (size_t)n);
      // Permit several short frames in one read without accepting an oversized frame.
      size_t start = 0, end;
      while ((end = pending.find('\n', start)) != std::string::npos) {
        if (end - start > FRAME_LIMIT) throw std::runtime_error("frame exceeds 1 MiB");
        start = end+1;
      }
      if (pending.size() - start > FRAME_LIMIT) throw std::runtime_error("frame exceeds 1 MiB");
    } else if (!n) eof = true;
    else if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) throw std::runtime_error("pipe read failed");
  }
  bool pop(std::string& frame) {
    size_t end = pending.find('\n'); if (end == std::string::npos) return false;
    frame = pending.substr(0, end); pending.erase(0, end+1); return true;
  }
  bool next(std::string& frame) {
    while (!pop(frame)) {
      if (eof && !pending.empty()) throw std::runtime_error("truncated request frame");
      if (eof || interrupted) return false;
      pollfd p{fd, POLLIN, 0}; if (poll(&p, 1, 100) > 0) read_ready();
    }
    return true;
  }
};
struct Writer {
  std::string id;
  u64 sequence = 0;
  std::function<void(std::string,std::string)> route;
  void emit(std::string fields, std::string_view request = {}) {
    auto rid = request.empty() ? std::string_view(id) : request;
    if (route) { route(std::move(fields),std::string(rid)); return; }
    std::string line = "{\"schema\":\"1\",\"id\":" + quote(rid) + ",\"seq\":" + quote(std::to_string(sequence+1)) + ',' + fields + "}\n";
    if (line.size() > FRAME_LIMIT+1) throw std::runtime_error("event exceeds 1 MiB");
    ++sequence;
    if (!send_frame(STDOUT_FILENO, line)) throw std::runtime_error("event consumer closed or stalled for two seconds");
  }
  void error(std::string_view category, std::string_view message) {
    emit("\"type\":\"error\",\"category\":" + quote(category) + ",\"operation\":\"request\",\"endpoint\":null,\"native_code\":null,\"retryable\":false,\"message\":" + quote(message));
  }
  void result(std::string_view status, int code, bool clean = true) {
    emit("\"type\":\"result\",\"status\":" + quote(status) + ",\"code\":" + quote(std::to_string(code)) + ",\"cleanup\":" + quote(clean ? "finished" : "unknown") + ",\"durability\":\"filesystem-completion\"");
  }
};
std::string request_id(const Value& v) {
  std::string id = v.at("id").string();
  if (id.empty() || id.size() > 128) throw std::runtime_error("id must be 1 to 128 ASCII characters");
  for (unsigned char c : id) if (c < 33 || c > 126) throw std::runtime_error("id must be printable ASCII without spaces");
  return id;
}
std::string endpoint_path(const Value& endpoint) {
  std::string p = app_json::unhex(endpoint.at("path").at("bytes_hex").string());
  if (p.empty() || p[0] != '/' || p.find('\0') != p.npos) throw std::runtime_error("path must be absolute, nonempty, and contain no NUL bytes");
  while (p.size() > 1 && p.back() == '/') p.pop_back();
  return p;
}
std::string local_path(const Value& endpoint) {
  if (endpoint.at("kind").string() != "local") throw RequestError("unsupported_feature", "this operation requires a local endpoint");
  return endpoint_path(endpoint);
}
u64 unsigned_decimal(const Value& v, u64 max) {
  auto s = v.string(); if (s.empty() || s.size() > 20) throw std::runtime_error("invalid unsigned decimal string");
  u64 n = 0;
  for (char c : s) { if (c < '0' || c > '9' || n > max/10 || (n == max/10 && (u64)(c-'0') > max%10)) throw std::runtime_error("decimal value out of range"); n = n*10+c-'0'; }
  return n;
}
std::string capabilities() {
  bool bridge = (PROTO_FEATURES & APP_TRANSFER_FEATURES) == APP_TRANSFER_FEATURES;
  auto result = "\"type\":\"capabilities\",\"engine\":\"xs\",\"private_partials\":\"1\",\"recovery_endpoint_kinds\":[\"local\"],\"version\":" + quote(XSYNC_VERSION) +
    ",\"revision\":" + quote(XSYNC_GIT_HASH) + ",\"backend\":\"native-local\",\"peer_version\":null,\"operations\":[\"probe\",\"list\",\"stat\",\"lstat\",\"fingerprint\",\"resolve\",\"copy\",\"resume\",\"recovery_state\",\"cleanup_partials\",\"move\",\"mkdir\",\"rename\",\"delete\",\"metadata\",\"cancel\"],\"endpoint_kinds\":[\"local\",\"ssh\"],\"transfer_bridge\":" + (bridge ? "\"3\"" : "null") + ",\"copy_endpoint_kinds\":" + (bridge ? "[\"local\",\"ssh\"]" : "[\"local\"]") + ",\"ssh_operations\":" + (bridge ? "[\"probe\",\"list\",\"stat\",\"lstat\",\"fingerprint\",\"resolve\",\"copy\",\"move\",\"mkdir\",\"rename\",\"delete\",\"metadata\"]" : "[\"probe\",\"list\",\"stat\",\"lstat\",\"fingerprint\",\"resolve\",\"mkdir\",\"rename\",\"delete\",\"metadata\"]") + ",\"conflict_policies\":[\"replace\",\"skip\",\"ask\"],\"interactive_conflicts\":true,\"conflict_bridge\":" + ((PROTO_FEATURES & PF_APP_CONTROLS) ? "\"1\"" : "null") + ",\"destination_revision_checks\":true,\"typed_transfer_errors\":true,\"selection_mappings\":true,\"ssh\":true,\"safe_move\":\"1\",\"move_lease\":" + ((PROTO_FEATURES & PF_APP_LEASE) ? "\"1\"" : "null") + ",\"filesystem_actions\":\"1\",\"delete\":true,\"permanent_delete\":true,\"trash\":false,\"undo_delete\":false,\"move\":true,\"fallback\":false,\"one_job_per_process\":true,\"max_frame_bytes\":\"1048576\",\"list_batch_entries\":\"128\",\"cancel_grace_ms\":\"2000\",\"consumer_stall_ms\":\"2000\"";
  bool recoverable = bridge && (PROTO_FEATURES & (PF_RESUME | PF_APP_PARTIALS)) == (PF_RESUME | PF_APP_PARTIALS);
  auto caps = app_json::parse('{'+result+'}');
  caps.object["recovery_entries"] = {Value::String,"1",{}, {}};
  caps.object["recovery_conflicts"] = {Value::String,"1",{}, {}};
  caps.object["recovery_verification"] = {Value::String,"1",{}, {}};
  caps.object["copy_reconnect"] = {Value::String,"1",{}, {}};
  caps.object["copy_recovery_identity"] = {Value::String,"1",{}, {}};
  caps.object["recovery_publication"] = {Value::String,"1",{}, {}};
  caps.object["destination_preflight"] = {Value::String,"1",{}, {}};
  caps.object["copy_invalidation"] = {Value::String,"1",{}, {}};
  caps.object["transfer_preview"] = {Value::String,"1",{}, {}};
  caps.object["preview_revision_binding"] = {Value::String,"1",{}, {}};
  caps.object["preview_bridge"] = bridge && (PROTO_FEATURES & PF_APP_CONTROLS) ? Value{Value::String,"1",{}, {}} : Value{};
  caps.object["preview_source_checks"] = bridge && (PROTO_FEATURES & PF_APP_CONTROLS) ? Value{Value::String,"1",{}, {}} : Value{};
  caps.object["preview_revision_binding_endpoint_kinds"] = app_json::parse(bridge && (PROTO_FEATURES & PF_APP_CONTROLS) ? "[\"local\",\"ssh\"]" : "[\"local\"]");
  caps.object["preview_modes"] = app_json::parse("[\"selected_copy\",\"mirror\"]");
  caps.object["preview_execution_modes"] = app_json::parse("[\"selected_copy\"]");
  caps.object["preview_endpoint_kinds"] = caps.at("copy_endpoint_kinds");
  caps.object["preview_max_entries"] = {Value::String,"100000",{}, {}};
  caps.object["preview_max_depth"] = {Value::String,"256",{}, {}};
  caps.object["operations"].array.push_back({Value::String,"preview",{}, {}});
  caps.object["operations"].array.push_back({Value::String,"preflight",{}, {}});
  caps.object["ssh_operations"].array.push_back({Value::String,"preflight",{}, {}});
  caps.object["recovery_bridge"] = recoverable ? Value{Value::String,"1",{}, {}} : Value{};
  caps.object["safe_pause"] = {Value::String,"1",{}, {}};
  caps.object["pause_bridge"] = recoverable ? Value{Value::String,"1",{}, {}} : Value{};
  for (const auto& op : {"pause","recovery_quiescence","_pause_checkpoint","verify_recovery","_verify_recovery"}) caps.object["operations"].array.push_back({Value::String,op,{}, {}});
  if (recoverable) {
    caps.object["recovery_endpoint_kinds"].array.push_back({Value::String,"ssh",{}, {}});
    for (const auto& op : {"resume","recovery_state","cleanup_partials","pause","recovery_quiescence","verify_recovery"}) caps.object["ssh_operations"].array.push_back({Value::String,op,{}, {}});
  }
  result = app_json::serialize(caps);
  return result.substr(1,result.size()-2);
}

// Child events are bounded pipe frames. The supervisor adds public IDs and ordering.
int event_fd = -1;
std::mutex event_mutex;
bool event_wire = false;
bool copy_push = false, copy_pull = false;
u64 items_discovered = 0, items_results = 0;
thread_local bool native_error_reported = false;
std::function<void(std::string)> event_route;
void public_event(std::string fields) {
  std::lock_guard<std::mutex> lock(event_mutex);
  if (fields.find("\"type\":\"error\"") != fields.npos) native_error_reported = true;
  if (fields.find("\"type\":\"item_") != fields.npos) {
    auto type = app_json::parse('{'+fields+'}').at("type").string();
    if (type == "item_discovered") ++items_discovered;
    if (type == "item_result") ++items_results;
  }
  if (event_wire) { send_app_event(std::move(fields)); return; }
  if (fields.size() > FRAME_LIMIT || !send_frame(event_fd, fields + '\n')) _Exit(RERR_MESSAGEIO);
}
void child_event(std::string fields) {
  if (event_route) event_route(std::move(fields));
  else public_event(std::move(fields));
}
std::string destination_root;
DestinationRevision root_revision;
thread_local DestinationRevision observed_root_revision;
std::string revision_json(const DestinationRevision& revision) {
  if (!revision.known) return "null";
  if (!revision.exists) return "{\"exists\":false}";
  return "{\"exists\":true,\"device\":" + quote(std::to_string(revision.device)) +
    ",\"inode\":" + quote(std::to_string(revision.inode)) + ",\"links\":" + quote(std::to_string(revision.links)) +
    ",\"mode\":" + quote(std::to_string(revision.mode)) + ",\"uid\":" + quote(std::to_string(revision.uid)) +
    ",\"gid\":" + quote(std::to_string(revision.gid)) + ",\"flags\":" + quote(std::to_string(revision.flags)) +
    ",\"size\":" + quote(std::to_string(revision.size)) + ",\"mtime_seconds\":" + quote(std::to_string(revision.mtime)) +
    ",\"mtime_nanoseconds\":" + quote(std::to_string(revision.mtime_ns)) + ",\"ctime_seconds\":" + quote(std::to_string(revision.ctime)) +
    ",\"ctime_nanoseconds\":" + quote(std::to_string(revision.ctime_ns)) + '}';
}
const char* native_category(int code) {
  if (code == ENOTSUP || code == ENOSYS) return "unsupported_feature";
  switch (code) {
    case EACCES: case EPERM: return "permission";
    case ENOSPC: case EDQUOT: return "disk_full";
    case ENOENT: return "missing";
    case ENOTDIR: return "not_directory";
    case EEXIST: case ENOTEMPTY: case EISDIR: return "conflict";
    case EIO: case EBADMSG: return "content";
    default: return "filesystem";
  }
}
void native_error(int code, std::string_view path, std::string_view operation) {
  int saved_errno = errno;
  bool transport = operation == "read_transport" || operation == "configure_transport";
  bool overlap = operation == "source_destination_overlap";
  bool source = operation.ends_with("_source") || operation == "source_preflight" || overlap;
  bool metadata = operation == "times" || operation == "permissions" || operation == "ownership" ||
    operation == "open directory for final attributes" || operation == "creation time" || operation == "file flags";
  bool changed = source && ((operation == "revalidate_source" && (code == ESTALE || !code)) || (operation == "open_source" && code == ESTALE));
  bool collision = operation == "name_collision";
  bool root_changed = operation == "destination_root_changed";
  bool temporary_changed = operation == "temporary_output_changed";
  bool destination_changed = root_changed || operation == "destination_changed" || operation == "destination_ancestor_changed" || temporary_changed;
  bool incomplete = operation.starts_with("scan_") && code == 0;
  bool synthetic = changed || incomplete || overlap || collision || (destination_changed && code == 0);
  bool content = operation == "read_source" || operation == "seek_source" || operation == "write" ||
    operation == "reconstruct delta" || operation == "verify reconstructed delta" || operation == "verify_transfer_stream" ||
    operation == "copy file range" || operation == "close";
  const char* category = operation == "read_transport" ? "network" : collision || destination_changed || overlap ? "conflict" : changed ? "content" : source && code == ENOENT && operation != "source_preflight" ? "vanished_source" : native_category(code);
  item_error(metadata, source);
  auto observed = current_item();
  child_event("\"type\":\"error\",\"category\":" + quote(category) +
    ",\"operation\":" + quote(operation) + ",\"endpoint\":\"local\",\"path\":" + (path.empty() ? "null" : app_json::path(path)) +
    ",\"side\":" + (transport ? "null" : quote(source ? "source" : "destination")) +
    ",\"stage\":" + quote(transport ? "transport" : destination_changed ? "destination_revalidation" : metadata ? "metadata" :
      operation.starts_with("scan_") || operation == "stat_source" || operation == "readlink_source" ? "scanning" :
      content || (source && operation != "source_preflight" && !overlap) ? "content" : "filesystem") +
    ",\"item_id\":" + (observed ? quote(app_json::hex(observed->relative)) : "null") +
    ",\"native_code\":" + (synthetic ? "null" : quote(std::to_string(code))) +
    (destination_changed ? ",\"reason\":" + quote(temporary_changed ? "temporary_output_changed" : root_changed ? "destination_root_changed" : operation == "destination_ancestor_changed" ? "destination_ancestor_changed" : "destination_changed") +
      ",\"expected_revision\":" + revision_json(root_changed ? root_revision : observed ? observed->expected_conflict : DestinationRevision{}) +
      ",\"observed_revision\":" + revision_json(root_changed ? observed_root_revision : observed ? observed->observed_conflict : DestinationRevision{}) :
      synthetic ? ",\"reason\":" + quote(overlap ? "source_destination_overlap" : collision ? "name_collision" : changed ? "source_changed" : "incomplete_listing") : "") +
    ",\"retryable\":" + (code == EIO || code == EINTR || synthetic || destination_changed ? "true" : "false") + ",\"message\":" +
    quote(overlap ? "source directory overlaps the destination" : destination_changed ? "destination identity or metadata changed during transfer" : collision ? "selected names collide on the destination filesystem" : changed ? "source identity or content changed during transfer" : synthetic ? "filesystem listing was incomplete" : strerror(code)));
  errno = saved_errno;
}
bool destination_root_valid() {
  struct stat st;
  if (lstat(destination_root.c_str(), &st) == 0) observed_root_revision = DestinationRevision::from(st);
  else if (errno == ENOENT) observed_root_revision = DestinationRevision::absent();
  else {
    int code = errno;
    native_error(code, destination_root, "stat_destination_root");
    err_line(RERR_PARTIAL, "cannot revalidate destination root: %s", errstr(code).c_str());
    return false;
  }
  if (root_revision.same_object(observed_root_revision)) return true;
  native_error(0, destination_root, "destination_root_changed");
  err_line(RERR_PARTIAL, "destination root changed during transfer");
  return false;
}
void diagnostic(int kind, int code, std::string_view text) {
  if (!kind) return;
  bool reported = std::exchange(native_error_reported, false);
  if (code > 0) item_error();
  if (code > 0 && !reported) {
    const char* type = code == RERR_STREAMIO ? "network" : code == RERR_TIMEOUT ? "network_timeout" :
      code == RERR_PROTOCOL ? "protocol" : code == RERR_UNSUPPORTED ? "unsupported_feature" :
      code == RERR_VANISHED ? "vanished_source" : code == RERR_FILESELECT ? "selection" :
      code == RERR_SIGNAL ? "cancelled" : "filesystem";
    auto item = current_item();
    bool destination = item && !item->destination.empty();
    child_event("\"type\":\"error\",\"category\":" + quote(type) + ",\"operation\":\"transfer\",\"endpoint\":null," +
      "\"path\":" + (item ? app_json::path(destination ? item->destination : item->source) : "null") +
      ",\"item_id\":" + (item ? quote(app_json::hex(item->relative)) : "null") +
      ",\"side\":" + (item ? quote(destination ? "destination" : "source") : "null") +
      ",\"stage\":\"engine_transfer\",\"native_code\":null,\"engine_code\":" + quote(std::to_string(code)) +
      ",\"retryable\":" + (code == RERR_STREAMIO || code == RERR_TIMEOUT ? "true" : "false") + ",\"message\":" + quote(text));
  }
  const char* category = code == RERR_VANISHED ? "vanished_source" : code == RERR_UNSUPPORTED ? "unsupported_feature" : code == RERR_FILESELECT ? "selection" : "engine_io";
  child_event("\"type\":\"diagnostic\",\"category\":" + quote(category) + ",\"code\":" + quote(std::to_string(code)) + ",\"message\":" + quote(text));
  native_error_reported = false;
}
void item_event(const OutputEvent& e) {
  // Native directory events can precede final directory metadata. They are updates,
  // never promises of item success; the supervisor's result is authoritative.
  child_event("\"type\":\"item_update\",\"item_id\":" + quote(app_json::hex(e.path)) + ",\"path\":" + app_json::path(e.path) +
    ",\"code\":" + quote(e.code) + ",\"size\":" + quote(std::to_string(e.size)) + ",\"bytes\":" + quote(std::to_string(e.bytes)));
}
void transfer_event(const TransferEvent& event) {
  const auto& item = event.item;
  const char* types[] = {"unknown", "file", "directory", "symlink", "fifo", "socket", "character", "block"};
  std::string fields = "\"type\":" + quote(event.kind) + ",\"item_id\":" + quote(app_json::hex(item.relative)) +
    ",\"path\":" + app_json::path(item.relative) + ",\"source_path\":" + app_json::path(item.source) +
    ",\"destination_path\":" + (item.destination.empty() ? "null" : app_json::path(item.destination)) +
    ",\"source_endpoint\":" + quote(copy_pull ? "ssh" : "local") + ",\"destination_endpoint\":" + quote(copy_push ? "ssh" : "local") +
    ",\"entry_type\":" + quote(types[item.type <= T_BLK ? item.type : 0]) + ",\"size\":" + (item.type == T_NONE ? "null" : quote(std::to_string(item.size.load()))) +
    ",\"side\":" + quote(item.destination.empty() ? "source" : "destination") + ",\"attempt\":" + quote(std::to_string(event.attempt)) +
    ",\"bytes_processed\":" + quote(std::to_string(event.bytes)) + ",\"reused_bytes\":" + quote(std::to_string(event.reused));
  if (event.kind == "item_stage") fields += ",\"stage\":" + quote(event.value);
  if (event.kind == "item_retry" || event.kind == "item_result") fields += ",\"reason\":" + (event.reason.empty() ? "null" : quote(event.reason));
  if (event.kind == "item_result") {
    fields += ",\"status\":" + quote(event.value) + ",\"content_published\":" + (item.published.load() ? "true" : "false") +
      ",\"metadata_complete\":" + (event.value == "skipped" ? "null" : item.applied.load() && !item.metadata_failed.load() ? "true" : "false");
  }
  child_event(std::move(fields));
}
std::mutex progress_mutex;
u64 last_progress = 0;
std::atomic<bool> copy_progress_enabled{false};
void progress_event() {
  if (!copy_progress_enabled.load()) return;
  std::lock_guard<std::mutex> lock(progress_mutex);
  u64 now = now_ns(); if (now - last_progress < 100000000) return; last_progress = now;
  auto& s = g_stats;
  const char* phase = s.conflict_active.load() || (s.peer_phase.load() & 8) ? "waiting_conflict" : s.metadata_active.load() || (s.peer_phase.load() & 4) ? "applying_metadata" : s.verifying_active.load() || (s.peer_phase.load() & 2) ? "hashing" : s.waiting_peer.load() ? "waiting_receiver" : s.deleting_active.load() ? "deleting" : !s.scan_done.load() ? "scanning" : "transferring";
  bool remote_receiver = copy_push;
  child_event("\"type\":\"progress\",\"phase\":" + quote(phase) + ",\"logical_bytes_completed\":" + quote(std::to_string(s.receiver_completed_bytes.load())) +
    ",\"logical_bytes_total\":" + (s.scan_done.load() ? quote(std::to_string(s.xfer_bytes_total.load())) : "null") +
    ",\"files_completed\":" + quote(std::to_string(remote_receiver ? s.acknowledged_files.load() : s.xfer_files.load())) +
    ",\"receiver_bytes_written\":" + (remote_receiver ? quote(std::to_string(s.acknowledged_bytes.load())) : "null") +
    ",\"source_bytes_read\":" + (copy_pull ? "null" : quote(std::to_string(s.xfer_bytes.load()))) +
    ",\"wire_bytes\":" + quote(std::to_string(s.wire_sent.load()+s.wire_recv.load())) + ",\"reused_bytes\":" + quote(std::to_string(s.delta_matched_bytes.load())));
}
struct ProgressSampler {
  std::atomic<bool> done{false};
  std::thread thread{[this] {
    while (!done.load()) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
      if (!done.load()) progress_event();
    }
  }};
  void stop() { done.store(true); if (thread.joinable()) thread.join(); }
  ~ProgressSampler() { stop(); }
};
std::string metadata(const std::string& path, const std::string& name, const struct stat& st, int parent_fd = -1) {
  Entry e; entry_from_stat(st, e);
  const char* types[] = {"unknown", "file", "directory", "symlink", "fifo", "socket", "character", "block"};
  std::string target = "null";
  if (S_ISLNK(st.st_mode)) {
    char bytes[4096]; ssize_t n = parent_fd < 0 ? readlink(path.c_str(), bytes, sizeof bytes) : readlinkat(parent_fd, name.c_str(), bytes, sizeof bytes);
    if (n < 0) { native_error(errno, path, "readlink"); return {}; }
    if (n == sizeof bytes) { native_error(ENAMETOOLONG, path, "readlink"); return {}; }
    target = app_json::path(std::string_view(bytes, (size_t)n));
  }
  return "{\"path\":" + app_json::path(path) + ",\"name\":" + app_json::path(name) + ",\"type\":" + quote(types[e.type <= T_BLK ? e.type : 0]) +
    ",\"size\":" + quote(std::to_string(e.size)) + ",\"mode\":" + quote(std::to_string(e.mode)) +
    ",\"mtime_seconds\":" + quote(std::to_string(e.mtime)) + ",\"mtime_nanoseconds\":" + quote(std::to_string(e.mtime_ns)) +
    ",\"device\":" + quote(std::to_string((u64)st.st_dev)) + ",\"inode\":" + quote(std::to_string((u64)st.st_ino)) + ",\"revision\":" + revision_json(DestinationRevision::from(st)) + ",\"link_target\":" + target + "}";
}
int browse(const std::string& op, const std::string& path) {
  if (op != "list") {
    struct stat st;
    int rc = op == "stat" ? stat(path.c_str(), &st) : lstat(path.c_str(), &st);
    if (rc) { native_error(errno, path, op); return RERR_FILESELECT; }
    auto entry = metadata(path, path.substr(path.rfind('/')+1), st);
    if (entry.empty()) return RERR_PARTIAL;
    child_event("\"type\":\"entry\",\"entry\":" + entry); return 0;
  }
  DIR* dir = opendir(path.c_str());
  if (!dir) { native_error(errno, path, "list"); return RERR_FILESELECT; }
  std::string batch; size_t count = 0; int rc = 0;
  auto flush = [&] { if (count) child_event("\"type\":\"entries\",\"entries\":[" + batch + ']'); batch.clear(); count = 0; };
  while (!g_stop.load()) {
    errno = 0; dirent* ent = readdir(dir);
    if (!ent) { if (errno) { native_error(errno, path, "readdir"); rc = RERR_PARTIAL; } break; }
    std::string name = ent->d_name; if (name == "." || name == "..") continue;
    if (app_partials::hidden(dirfd(dir), name)) continue;
    struct stat st; auto full = path_join(path, name);
    if (fstatat(dirfd(dir), name.c_str(), &st, AT_SYMLINK_NOFOLLOW)) { native_error(errno, full, "lstat"); rc = RERR_PARTIAL; continue; }
    auto entry = metadata(full, name, st, dirfd(dir));
    if (entry.empty()) { rc = RERR_PARTIAL; continue; }
    if (batch.size() + entry.size() > FRAME_LIMIT/2) flush();
    if (count++) batch += ',';
    batch += entry;
    if (count == 128) flush();
  }
  flush(); closedir(dir); return g_stop.load() ? RERR_SIGNAL : rc;
}

int fingerprint(const std::string& path) {
  auto slash = path.rfind('/');
  std::string folder = slash == 0 ? "/" : path.substr(0, slash), name = path.substr(slash+1);
  if (name.empty()) { native_error(ENOTSUP, path, "fingerprint"); return RERR_UNSUPPORTED; }
  int parent = open(folder.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
  if (parent < 0) { native_error(errno, path, "fingerprint_parent"); return RERR_FILESELECT; }
  struct Close { int fd; ~Close() { if (fd >= 0) close(fd); } } parent_guard{parent};
  struct stat before, after;
  struct stat parent_stat, named_parent;
  if (fstat(parent, &parent_stat) || lstat(folder.c_str(), &named_parent)) { native_error(errno, folder, "fingerprint_parent"); return RERR_FILESELECT; }
  auto parent_revision = DestinationRevision::from(parent_stat);
  if (!parent_revision.same_object(DestinationRevision::from(named_parent))) { native_error(0, folder, "destination_ancestor_changed"); return RERR_PARTIAL; }
  if (fstatat(parent, name.c_str(), &before, AT_SYMLINK_NOFOLLOW)) { native_error(errno, path, "fingerprint_stat"); return RERR_FILESELECT; }
  auto revision = DestinationRevision::from(before);
  XXH3_state_t hash; XXH3_128bits_reset(&hash);
  u64 total = 0;
  if (S_ISREG(before.st_mode)) {
    int fd = openat(parent, name.c_str(), O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) { native_error(errno, path, "fingerprint_open"); return RERR_FILESELECT; }
    Close guard{fd}; struct stat opened;
    if (fstat(fd, &opened)) { native_error(errno, path, "fingerprint_stat"); return RERR_PARTIAL; }
    if (!(revision == DestinationRevision::from(opened))) { native_error(0, path, "revalidate_source"); return RERR_PARTIAL; }
    std::vector<char> bytes(256*1024);
    while (!g_stop.load()) {
      ssize_t count = read(fd, bytes.data(), bytes.size());
      if (count < 0 && errno == EINTR) continue;
      if (count < 0) { native_error(errno, path, "fingerprint_read"); return RERR_PARTIAL; }
      if (!count) break;
      total += (u64)count; XXH3_128bits_update(&hash, bytes.data(), (size_t)count);
    }
    if (g_stop.load()) return RERR_SIGNAL;
    if (fstat(fd, &after)) { native_error(errno, path, "fingerprint_stat"); return RERR_PARTIAL; }
    if (!(revision == DestinationRevision::from(after))) { native_error(0, path, "revalidate_source"); return RERR_PARTIAL; }
    guard.fd = -1;
    if (close(fd)) { native_error(errno, path, "fingerprint_close"); return RERR_PARTIAL; }
  } else if (S_ISLNK(before.st_mode)) {
    char bytes[4096]; ssize_t count = readlinkat(parent, name.c_str(), bytes, sizeof bytes);
    if (count < 0) { native_error(errno, path, "fingerprint_readlink"); return RERR_PARTIAL; }
    if (count == sizeof bytes) { native_error(ENAMETOOLONG, path, "fingerprint_readlink"); return RERR_PARTIAL; }
    total = (u64)count; XXH3_128bits_update(&hash, bytes, (size_t)count);
  } else { native_error(ENOTSUP, path, "fingerprint"); return RERR_UNSUPPORTED; }
  if (fstatat(parent, name.c_str(), &after, AT_SYMLINK_NOFOLLOW)) { native_error(errno, path, "fingerprint_stat"); return RERR_PARTIAL; }
  if (!(revision == DestinationRevision::from(after))) { native_error(0, path, "revalidate_source"); return RERR_PARTIAL; }
  if (lstat(folder.c_str(), &named_parent)) { native_error(errno, folder, "fingerprint_parent"); return RERR_PARTIAL; }
  if (!parent_revision.same_object(DestinationRevision::from(named_parent))) { native_error(0, folder, "destination_ancestor_changed"); return RERR_PARTIAL; }
  auto entry = metadata(path, name, after, parent);
  if (entry.empty()) return RERR_PARTIAL;
  XXH128_canonical_t canonical; XXH128_canonicalFromHash(&canonical, XXH3_128bits_digest(&hash));
  entry.pop_back();
  entry += ",\"fingerprint\":{\"algorithm\":\"xxh3-128\",\"hex\":" + quote(app_json::hex(std::string_view((char*)canonical.digest, sizeof canonical.digest))) +
    ",\"bytes_hashed\":" + quote(std::to_string(total)) + "}}";
  child_event("\"type\":\"entry\",\"entry\":" + entry); return 0;
}

struct Job {
  std::string op, path, policy;
  std::vector<std::string> sources;
  std::map<std::string, std::string> selection_names;
  bool times = false, perms = false;
  bool contents = false, push = false, native = false, native_receiver = false;
  bool native_move_lease = false;
  u32 timeout = 0, conflict_timeout = 120;
  u64 jobs = 0, bwlimit = 0;
  std::optional<app_ssh::Connection> connection;
  std::string remote_request;
  std::optional<app_actions::Request> action;
  std::optional<Value> move_request;
  bool retain_partials = false, resuming = false;
  std::string recovery_id, attempt_id, actor_role;
  std::string recovery_inventory;
  bool actor_cleanup = false;
  Value recovery_binding;
  Value preflight_space;
  Value preview_request, preview_guard;
  Value native_preview_header;
  DestinationRevision recovery_revision;
};
Job validate(const Value& v) {
  Job j; j.op = v.at("op").string();
  if (j.op == "preview") {
    for (const auto& [key,value] : v.object)
      if (key != "id" && key != "op" && key != "mode" && key != "sources" && key != "destination" && key != "options")
        throw std::runtime_error("unsupported preview field");
    const auto mode = v.at("mode").string();
    if (mode != "selected_copy" && mode != "mirror") throw RequestError("unsupported_feature","unsupported preview mode");
    if (v.at("sources").kind!=Value::Array) throw std::runtime_error("preview sources must be an array");
    for (const auto& selected:v.at("sources").array) for (const auto& [key,value]:selected.object)
      if (key!="endpoint" && key!="mode" && key!="destination_name") throw std::runtime_error("unsupported preview selection field");
    for (const auto& [key,value] : v.at("options").object)
      if (key != "on_conflict" && key != "preserve_times" && key != "preserve_permissions" && key != "conflict_timeout_seconds" && key != "jobs" && key != "bandwidth_bytes_per_second" && key != "retain_partials")
        throw std::runtime_error("unsupported preview option");
    auto copy = v; copy.object.erase("mode"); copy.object["op"] = {Value::String,"copy",{}, {}};
    j = validate(copy);
    if (mode == "mirror" && !j.contents) throw std::runtime_error("mirror preview requires one contents selection");
    j.op = "preview"; j.preview_request = v;
    j.preview_request.object["destination"].object["path"] = app_json::parse(app_json::path(j.path));
    for (size_t i=0; i<j.sources.size(); ++i) {
      auto p=j.sources[i]; while (p.size()>1 && p.back()=='/') p.pop_back();
      j.preview_request.object["sources"].array[i].object["endpoint"].object["path"] = app_json::parse(app_json::path(p));
    }
    j.preview_request.object["options"].object = {
      {"on_conflict",{Value::String,j.policy,{}, {}}},{"preserve_times",{Value::Bool,j.times ? "true" : "false",{}, {}}},
      {"preserve_permissions",{Value::Bool,j.perms ? "true" : "false",{}, {}}},
      {"retain_partials",{Value::Bool,j.retain_partials ? "true" : "false",{}, {}}},
      {"jobs",{Value::String,std::to_string(j.jobs ? j.jobs : MAX_WORKERS),{}, {}}},
      {"conflict_timeout_seconds",{Value::String,std::to_string(j.conflict_timeout),{}, {}}},
      {"bandwidth_bytes_per_second",{Value::String,std::to_string(j.bwlimit),{}, {}}}};
    return j;
  }
  if (j.op == "copy" && v.object.count("expected_preview")) {
    const auto& guard=v.at("expected_preview");
    if (guard.kind != Value::Object || guard.object.size()!=3 || guard.at("version").kind != Value::String || guard.at("version").string()!="1")
      throw RequestError("unsupported_feature","unsupported preview guard");
    if (guard.at("mode").string()!="selected_copy") throw RequestError("unsupported_feature","mirror execution is not available");
    if (!app_partials::valid_id(guard.at("token").string())) throw std::runtime_error("invalid preview token");
    auto preview=v; preview.object.erase("expected_preview"); preview.object.erase("recovery_id");
    preview.object["op"]={Value::String,"preview",{}, {}}; preview.object["mode"]={Value::String,"selected_copy",{}, {}};
    auto plan=validate(preview);
    auto copy=v; copy.object.erase("expected_preview"); j=validate(copy);
    j.preview_request=plan.preview_request; j.preview_guard=guard; return j;
  }
  if (j.op == "preflight") {
    j.preflight_space = app_preflight::parse(v);
    const auto& endpoint = v.at("endpoint"); auto kind = endpoint.at("kind").string();
    if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature","unsupported preflight endpoint");
    j.path = endpoint_path(endpoint);
    if (kind == "ssh") {
      j.connection = app_ssh::parse_connection(endpoint);
      auto remote = v; remote.object["id"] = {Value::String,"remote-operation",{}, {}};
      remote.object["endpoint"] = app_json::parse("{\"kind\":\"local\",\"path\":"+app_json::path(j.path)+"}");
      j.remote_request = app_json::serialize(remote);
    }
    return j;
  }
  if (j.op == "recovery_quiescence" || j.op == "_pause_checkpoint") {
    for (const auto& [key,value] : v.object)
      if (key != "id" && key != "op" && key != "endpoint" && key != "recovery_id" &&
          !(j.op == "recovery_quiescence" && (key == "attempt_id" || key == "role" || key == "expected_actor_revision" || key == "cleanup")) &&
          !(j.op == "_pause_checkpoint" && (key == "binding" || key == "closed_attempt_id"))) throw std::runtime_error("unsupported pause evidence field");
    const auto& endpoint = v.at("endpoint");
    auto kind = endpoint.at("kind").string();
    if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature","unsupported pause evidence endpoint");
    j.path = endpoint_path(endpoint); j.recovery_id = v.at("recovery_id").string();
    if (!app_partials::valid_id(j.recovery_id)) throw std::runtime_error("invalid recovery_id");
    if (j.op == "recovery_quiescence") {
      j.attempt_id = v.at("attempt_id").string(); j.actor_role = v.at("role").string();
      if (!app_actor::valid_path(j.path) || !app_partials::valid_id(j.attempt_id) || (j.actor_role != "sender" && j.actor_role != "receiver"))
        throw std::runtime_error("invalid recovery actor evidence");
      j.recovery_revision = app_actions::parse_revision(v.at("expected_actor_revision"));
      if (!j.recovery_revision.exists || !S_ISREG(j.recovery_revision.mode)) throw std::runtime_error("actor evidence requires a file revision");
      j.actor_cleanup = v.at("cleanup").boolean();
    } else {
      j.recovery_binding = v.at("binding");
      if (j.recovery_binding.kind != Value::Object) throw std::runtime_error("pause checkpoint requires its original binding");
      if (v.object.count("closed_attempt_id")) {
        j.attempt_id = v.at("closed_attempt_id").string();
        if (!app_partials::valid_id(j.attempt_id)) throw std::runtime_error("invalid closed attempt ID");
      }
    }
    if (kind == "ssh") {
      j.connection = app_ssh::parse_connection(endpoint); Value remote = v;
      remote.object["id"] = {Value::String,"remote-operation",{}, {}};
      remote.object["endpoint"] = app_json::parse("{\"kind\":\"local\",\"path\":" + app_json::path(j.path) + "}");
      j.remote_request = app_json::serialize(remote);
    }
    return j;
  }
  if (j.op == "verify_recovery" || j.op == "_verify_recovery") {
    const auto operation = j.op;
    if (operation == "verify_recovery") {
      for (const auto& [key,value] : v.object)
        if (key != "id" && key != "op" && key != "sources" && key != "destination" && key != "options" && key != "recovery_id" && key != "expected_job_revision" && key != "expected_inventory_token")
          throw std::runtime_error("unsupported recovery verification field");
      Value copy = v; copy.object.erase("recovery_id"); copy.object.erase("expected_job_revision"); copy.object.erase("expected_inventory_token");
      copy.object["op"] = {Value::String,"copy",{}, {}};
      if (copy.at("options").object.count("retain_partials") && !copy.at("options").at("retain_partials").boolean())
        throw std::runtime_error("recovery verification requires retain_partials");
      copy.object["options"].object["retain_partials"] = {Value::Bool,"true",{}, {}};
      j = validate(copy); j.op = operation;
    } else {
      for (const auto& [key,value] : v.object)
        if (key != "id" && key != "op" && key != "endpoint" && key != "binding" && key != "recovery_id" && key != "expected_job_revision" && key != "expected_inventory_token")
          throw std::runtime_error("unsupported native recovery verification field");
      j.path = local_path(v.at("endpoint")); j.recovery_binding = v.at("binding");
      if (j.recovery_binding.kind != Value::Object) throw std::runtime_error("recovery verification requires original binding");
    }
    j.recovery_id = v.at("recovery_id").string();
    if (!app_partials::valid_id(j.recovery_id)) throw std::runtime_error("invalid recovery_id");
    j.recovery_inventory = v.at("expected_inventory_token").string();
    if (!app_partials::valid_id(j.recovery_inventory)) throw std::runtime_error("invalid expected_inventory_token");
    j.recovery_revision = app_actions::parse_revision(v.at("expected_job_revision"));
    if (!j.recovery_revision.exists || !S_ISDIR(j.recovery_revision.mode)) throw std::runtime_error("verification requires an existing job directory revision");
    if (j.connection && j.push) {
      j.remote_request = "{\"id\":\"remote-operation\",\"op\":\"_verify_recovery\",\"endpoint\":{\"kind\":\"local\",\"path\":" + app_json::path(j.path) +
        "},\"recovery_id\":" + quote(j.recovery_id) + ",\"binding\":" + app_json::serialize(j.recovery_binding) +
        ",\"expected_job_revision\":" + app_json::serialize(v.at("expected_job_revision")) + ",\"expected_inventory_token\":" + quote(j.recovery_inventory) + '}';
    }
    return j;
  }
  if (j.op == "resume") {
    for (const auto& [key, value] : v.object)
      if (key != "id" && key != "op" && key != "sources" && key != "destination" && key != "options" && key != "recovery_id")
        throw std::runtime_error("unsupported resume field: " + key);
    auto id = v.at("recovery_id").string();
    if (!app_partials::valid_id(id)) throw std::runtime_error("invalid recovery_id");
    Value copy = v; copy.object.erase("recovery_id");
    copy.object["op"] = {Value::String,"copy",{}, {}};
    if (copy.at("options").object.count("retain_partials") && !copy.at("options").at("retain_partials").boolean())
      throw std::runtime_error("resume requires retain_partials");
    copy.object["options"].object["retain_partials"] = {Value::Bool,"true",{}, {}};
    j = validate(copy); j.resuming = true; j.recovery_id = id;
    if (j.connection) {
      auto header = app_json::parse(j.remote_request);
      header.object["recovery_id"] = {Value::String,id,{}, {}};
      header.object["resume"] = {Value::Bool,"true",{}, {}};
      j.remote_request = app_json::serialize(header);
    }
    return j;
  }
  if (j.op == "recovery_state" || j.op == "cleanup_partials") {
    for (const auto& [key, value] : v.object)
      if (key != "id" && key != "op" && key != "endpoint" && key != "recovery_id" &&
          !(j.op == "cleanup_partials" && key == "expected_job_revision"))
        throw std::runtime_error("unsupported recovery field: " + key);
    const auto& endpoint = v.at("endpoint");
    auto kind = endpoint.at("kind").string();
    if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature","unsupported recovery endpoint");
    j.path = endpoint_path(endpoint);
    j.recovery_id = v.at("recovery_id").string();
    if (!app_partials::valid_id(j.recovery_id)) throw std::runtime_error("invalid recovery_id");
    if (j.op == "cleanup_partials") {
      j.recovery_revision = app_actions::parse_revision(v.at("expected_job_revision"));
      if (!j.recovery_revision.exists || !S_ISDIR(j.recovery_revision.mode)) throw std::runtime_error("cleanup requires an existing job directory revision");
    }
    if (kind == "ssh") {
      j.connection = app_ssh::parse_connection(endpoint);
      Value remote = v;
      remote.object["id"] = {Value::String,"remote-operation",{}, {}};
      remote.object["endpoint"] = app_json::parse("{\"kind\":\"local\",\"path\":" + app_json::path(j.path) + "}");
      j.remote_request = app_json::serialize(remote);
    }
    return j;
  }
  if (j.op == "move") {
    auto allowed = [](const Value& object, std::initializer_list<std::string_view> names) {
      if (object.kind != Value::Object) throw std::runtime_error("move object required");
      for (const auto& [key, value] : object.object) {
        if (std::find(names.begin(), names.end(), key) == names.end()) throw std::runtime_error("unsupported move field: " + key);
      }
    };
    allowed(v, {"id", "op", "sources", "destination", "destination_parent_revision", "options"});
    allowed(v.at("options"), {"on_conflict", "preserve_times", "preserve_permissions", "conflict_timeout_seconds", "jobs", "bandwidth_bytes_per_second"});
    Value copy = v; copy.object["op"] = {Value::String, "copy", {}, {}};
    j = validate(copy);
    const auto& parent = v.at("destination_parent_revision");
    auto expected = app_actions::parse_revision(parent);
    if (!expected.exists || !S_ISDIR(expected.mode)) throw std::runtime_error("move destination requires a directory revision");
    for (const auto& selected : v.at("sources").array) {
      allowed(selected, {"endpoint", "mode", "expected_revision", "destination_name"});
      if (!app_actions::parse_revision(selected.at("expected_revision")).exists) throw std::runtime_error("move selections require existing revisions");
    }
    Value normalized = v;
    normalized.object["destination"].object["path"] = app_json::parse(app_json::path(j.path));
    for (auto& selected : normalized.object["sources"].array)
      selected.object["endpoint"].object["path"] = app_json::parse(app_json::path(endpoint_path(selected.at("endpoint"))));
    j.op = "move"; j.move_request = std::move(normalized); return j;
  }
  if (j.op == "_native_transfer") {
    bool retain = v.at("options").object.count("retain_partials") && v.at("options").at("retain_partials").boolean();
    if (retain && (PROTO_FEATURES & (PF_RESUME | PF_APP_PARTIALS)) != (PF_RESUME | PF_APP_PARTIALS))
      throw RequestError("unsupported_feature", "private recovery is unavailable on the native bridge");
    if ((PROTO_FEATURES & APP_TRANSFER_FEATURES) != APP_TRANSFER_FEATURES) throw RequestError("unsupported_feature", "native app bridge is unavailable");
    auto role = v.at("role").string();
    if (role != "receiver" && role != "sender") throw std::runtime_error("invalid native transfer role");
    Value translated = v;
    translated.object["op"] = {Value::String, "copy", {}, {}};
    if (role == "receiver") {
      translated.object["sources"] = app_json::parse("[{\"endpoint\":{\"kind\":\"local\",\"path\":{\"bytes_hex\":\"2f\"}},\"mode\":\"contents\"}]");
    } else translated.object["destination"] = app_json::parse("{\"kind\":\"local\",\"path\":{\"bytes_hex\":\"2f\"}}");
    j = validate(translated);
    if (j.connection) throw std::runtime_error("native bridge paths must be local to the helper");
    j.op = "_native_transfer"; j.native = true; j.native_receiver = role == "receiver";
    if (v.object.count("preview_binding")) j.native_preview_header=v.at("preview_binding");
    j.native_move_lease = v.object.count("move_lease") && v.at("move_lease").boolean();
    if (retain) {
      if (j.native_move_lease) throw std::runtime_error("private recovery cannot be combined with a move lease");
      j.recovery_id = v.at("recovery_id").string();
      if (!app_partials::valid_id(j.recovery_id)) throw std::runtime_error("invalid native recovery ID");
      j.resuming = v.at("resume").boolean();
      if (v.object.count("attempt_id")) {
        j.attempt_id = v.at("attempt_id").string();
        if (!app_partials::valid_id(j.attempt_id)) throw std::runtime_error("invalid native attempt ID");
      }
      j.recovery_binding = v.at("recovery_binding");
      if (j.recovery_binding.kind != Value::Object) throw std::runtime_error("invalid native recovery binding");
      const auto& binding = j.recovery_binding;
      for (const auto& [key,value] : binding.object)
        if (key != "sources" && key != "destination" && key != "on_conflict" && key != "preserve_times" && key != "preserve_permissions" &&
            key != "source_kind" && key != "destination_kind" && key != "peer") throw std::runtime_error("unsupported native recovery binding field");
      const auto& peer = binding.at("peer");
      if (peer.kind != Value::Object) throw std::runtime_error("invalid native recovery peer");
      for (const auto& [key,value] : peer.object)
        if (key != "host" && key != "user" && key != "port") throw std::runtime_error("unsupported native recovery peer field");
      if (peer.at("host").string().empty() || peer.at("host").string().size() > 1024 || peer.at("user").string().size() > 1024)
        throw std::runtime_error("invalid native recovery peer");
      (void)unsigned_decimal(peer.at("port"),65535);
      if (binding.at("on_conflict").string() != j.policy || binding.at("preserve_times").boolean() != j.times ||
          binding.at("preserve_permissions").boolean() != j.perms || binding.at("source_kind").string() != (j.native_receiver ? "local" : "ssh") ||
          binding.at("destination_kind").string() != (j.native_receiver ? "ssh" : "local")) throw std::runtime_error("native recovery semantics differ from transfer request");
      if (j.native_receiver && app_json::unhex(binding.at("destination").at("bytes_hex").string()) != j.path)
        throw std::runtime_error("native recovery destination differs from transfer request");
      if (!j.native_receiver) {
        const auto& selected = binding.at("sources");
        if (selected.kind != Value::Array || selected.array.size() != j.sources.size()) throw std::runtime_error("native recovery sources differ from transfer request");
        for (size_t i = 0; i < j.sources.size(); ++i) {
          const auto& row = selected.array[i];
          auto mapped = j.selection_names.find(j.sources[i]);
          const auto& name = row.at("destination_name");
          if (app_json::unhex(row.at("path").at("bytes_hex").string()) != j.sources[i] || row.at("mode").string() != (j.contents ? "contents" : "entry") ||
              (mapped == j.selection_names.end() ? name.kind != Value::Null : app_json::unhex(name.at("bytes_hex").string()) != mapped->second))
            throw std::runtime_error("native recovery selection differs from transfer request");
        }
      }
    }
    j.timeout = (u32)unsigned_decimal(v.at("idle_timeout_seconds"), 3600);
    return j;
  }
  if (app_actions::operation(j.op)) {
    const auto& endpoint = v.at("endpoint");
    auto kind = endpoint.at("kind").string();
    if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature", "unsupported action endpoint");
    j.path = endpoint_path(endpoint);
    j.action = app_actions::parse(v, j.path);
    if (kind == "ssh") {
      j.connection = app_ssh::parse_connection(endpoint);
      Value remote = v;
      remote.object["id"] = {Value::String, "remote-operation", {}, {}};
      remote.object["endpoint"] = app_json::parse("{\"kind\":\"local\",\"path\":" + app_json::path(j.path) + "}");
      j.remote_request = app_json::serialize(remote);
    }
    return j;
  }
  if (j.op == "list" || j.op == "stat" || j.op == "lstat" || j.op == "fingerprint" || j.op == "resolve" || j.op == "probe") {
    if (v.object.count("endpoint")) {
      auto kind = v.at("endpoint").at("kind").string();
      if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature", "unsupported endpoint kind");
    }
    if (v.object.count("endpoint") && v.at("endpoint").at("kind").string() == "ssh") {
      j.connection = app_ssh::parse_connection(v.at("endpoint"));
      j.remote_request = "{\"id\":\"remote-operation\",\"op\":" + quote(j.op);
      if (j.op == "resolve") {
        auto location = v.at("location").string();
        if (location != "home" && location != "root") throw std::runtime_error("location must be home or root");
        j.remote_request += ",\"location\":" + quote(location);
      } else if (j.op != "probe") {
        j.path = endpoint_path(v.at("endpoint"));
        j.remote_request += ",\"endpoint\":{\"kind\":\"local\",\"path\":" + app_json::path(j.path) + "}";
      }
      j.remote_request += '}';
      return j;
    }
  }
  if (j.op == "resolve") {
    auto location = v.at("location").string();
    if (location == "root") j.path = "/";
    else if (location == "home") { const char* h = getenv("HOME"); if (!h || h[0] != '/') throw std::runtime_error("home directory unavailable"); j.path = h; }
    else throw std::runtime_error("location must be home or root");
    return j;
  }
  if (j.op == "list" || j.op == "stat" || j.op == "lstat" || j.op == "fingerprint") { j.path = local_path(v.at("endpoint")); return j; }
  if (j.op != "copy") throw RequestError("unsupported_feature", "unsupported operation");
  const auto& destination = v.at("destination");
  auto destination_kind = destination.at("kind").string();
  if (destination_kind != "local" && destination_kind != "ssh") throw RequestError("unsupported_feature", "unsupported destination endpoint");
  j.path = endpoint_path(destination);
  j.push = destination_kind == "ssh";
  if (j.push) j.connection = app_ssh::parse_connection(destination);
  const auto& sources = v.at("sources");
  if (sources.kind != Value::Array || sources.array.empty() || sources.array.size() > 1024) throw std::runtime_error("sources must contain 1 to 1024 selections");
  std::set<std::string> names, selected_paths;
  std::string source_kind;
  for (const auto& s : sources.array) {
    const auto& endpoint = s.at("endpoint");
    auto kind = endpoint.at("kind").string();
    if (kind != "local" && kind != "ssh") throw RequestError("unsupported_feature", "unsupported source endpoint");
    if (source_kind.empty()) source_kind = kind;
    if (kind != source_kind) throw RequestError("unsupported_feature", "selections must share an endpoint");
    if (kind == "ssh") {
      if (j.push) throw RequestError("unsupported_feature", "remote-to-remote copies are unavailable");
      auto connection = app_ssh::parse_connection(endpoint);
      if (j.connection && *j.connection != connection) throw RequestError("unsupported_feature", "SSH selections must share a connection profile");
      j.connection = std::move(connection);
    }
    auto p = endpoint_path(endpoint); auto mode = s.at("mode").string();
    if (!selected_paths.insert(p).second) throw std::runtime_error("source paths must be distinct selections");
    if (mode != "entry" && mode != "contents") throw std::runtime_error("selection mode must be entry or contents");
    if (mode == "contents") {
      if (sources.array.size() != 1) throw std::runtime_error("contents selection must be the only source");
      if (s.object.count("destination_name")) throw std::runtime_error("contents selections cannot specify destination_name");
      j.contents = true;
      if (p.back() != '/') p += '/';
    } else {
      auto name = p.substr(p.rfind('/')+1);
      if (name.empty() || name == "." || name == "..") throw std::runtime_error("root/dot entries require contents mode");
      if (s.object.count("destination_name")) {
        name = app_json::unhex(s.at("destination_name").at("bytes_hex").string());
        if (name.empty() || name.size() > 255 || name == "." || name == ".." || name.find_first_of("/\0", 0, 2) != name.npos)
          throw std::runtime_error("destination_name must be a single literal component of 1 to 255 bytes");
        j.selection_names.emplace(p, name);
      }
      if (!names.insert(name).second) throw std::runtime_error("entry selections need distinct destination names");
    }
    j.sources.push_back(std::move(p));
  }
  const auto& options = v.at("options");
  j.policy = options.at("on_conflict").string();
  if (j.policy != "replace" && j.policy != "skip" && j.policy != "ask") throw RequestError("unsupported_feature", "unsupported conflict policy");
  if (options.object.count("conflict_timeout_seconds")) {
    j.conflict_timeout = (u32)unsigned_decimal(options.at("conflict_timeout_seconds"), 3600);
    if (!j.conflict_timeout) throw std::runtime_error("conflict timeout must be positive");
  }
  if (j.policy == "ask" && j.connection && !(PROTO_FEATURES & PF_APP_CONTROLS))
    throw RequestError("unsupported_feature", "native conflict bridge is unavailable");
  // These are the entire schema-1 option allowlist; no CLI strings are accepted.
  j.times = options.at("preserve_times").boolean(); j.perms = options.at("preserve_permissions").boolean();
  if (options.object.count("jobs")) j.jobs = unsigned_decimal(options.at("jobs"), MAX_WORKERS);
  if (options.object.count("bandwidth_bytes_per_second")) j.bwlimit = unsigned_decimal(options.at("bandwidth_bytes_per_second"), INT64_MAX);
  if (options.object.count("retain_partials")) j.retain_partials = options.at("retain_partials").boolean();
  if (v.object.count("recovery_id")) {
    if (!j.retain_partials) throw std::runtime_error("copy recovery_id requires retain_partials");
    j.recovery_id = v.at("recovery_id").string();
    if (!app_partials::valid_id(j.recovery_id)) throw std::runtime_error("invalid recovery_id");
  }
  if (j.retain_partials) {
    if (j.connection && (PROTO_FEATURES & (PF_RESUME | PF_APP_PARTIALS)) != (PF_RESUME | PF_APP_PARTIALS))
      throw RequestError("unsupported_feature", "private recovery bridge is unavailable");
    for (const auto& [key, value] : options.object)
      if (key != "on_conflict" && key != "preserve_times" && key != "preserve_permissions" && key != "conflict_timeout_seconds" &&
          key != "jobs" && key != "bandwidth_bytes_per_second" && key != "retain_partials")
        throw std::runtime_error("unsupported recovery option: " + key);
    if (j.recovery_id.empty()) j.recovery_id = app_partials::new_id();
    j.recovery_binding = app_json::parse("{\"sources\":[],\"destination\":" + app_json::path(j.path) +
      ",\"on_conflict\":" + quote(j.policy) + ",\"preserve_times\":" + (j.times ? "true" : "false") +
      ",\"preserve_permissions\":" + (j.perms ? "true" : "false") + "}");
    for (const auto& p : j.sources) {
      auto mapped = j.selection_names.find(p);
      j.recovery_binding.object["sources"].array.push_back(app_json::parse("{\"path\":" + app_json::path(p) +
        ",\"mode\":" + quote(j.contents ? "contents" : "entry") + ",\"destination_name\":" +
        (mapped == j.selection_names.end() ? "null" : app_json::path(mapped->second)) + "}"));
    }
    if (j.connection) {
      j.recovery_binding.object["source_kind"] = {Value::String,source_kind,{}, {}};
      j.recovery_binding.object["destination_kind"] = {Value::String,destination_kind,{}, {}};
      j.recovery_binding.object["peer"] = app_json::parse("{\"host\":" + quote(j.connection->host) +
        ",\"user\":" + quote(j.connection->user) + ",\"port\":" + quote(std::to_string(j.connection->port)) + "}");
    }
  }
  if (j.connection) {
    if ((PROTO_FEATURES & APP_TRANSFER_FEATURES) != APP_TRANSFER_FEATURES) throw RequestError("unsupported_feature", "native app bridge is unavailable");
    j.timeout = j.connection->idle_seconds;
    j.remote_request = "{\"id\":\"remote-operation\",\"op\":\"_native_transfer\",\"role\":" + quote(j.push ? "receiver" : "sender") +
      ",\"idle_timeout_seconds\":" + quote(std::to_string(j.timeout)) + ",\"options\":{\"on_conflict\":" + quote(j.policy) + ",\"conflict_timeout_seconds\":" + quote(std::to_string(j.conflict_timeout)) +
      ",\"preserve_times\":" + (j.times ? "true" : "false") + ",\"preserve_permissions\":" + (j.perms ? "true" : "false") +
      ",\"jobs\":" + quote(std::to_string(j.jobs)) + ",\"bandwidth_bytes_per_second\":" + quote(std::to_string(j.bwlimit)) + "}";
    if (j.push) j.remote_request += ",\"destination\":{\"kind\":\"local\",\"path\":{\"bytes_hex\":" + quote(app_json::hex(j.path)) + "}}";
    else {
      j.remote_request += ",\"sources\":[";
      for (size_t i = 0; i < j.sources.size(); ++i) {
        if (i) j.remote_request += ',';
        j.remote_request += "{\"endpoint\":{\"kind\":\"local\",\"path\":{\"bytes_hex\":" + quote(app_json::hex(j.sources[i])) + "}},\"mode\":" + quote(j.contents ? "contents" : "entry");
        auto mapped = j.selection_names.find(j.sources[i]);
        if (mapped != j.selection_names.end()) j.remote_request += ",\"destination_name\":{\"bytes_hex\":" + quote(app_json::hex(mapped->second)) + '}';
        j.remote_request += '}';
      }
      j.remote_request += ']';
    }
    j.remote_request += '}';
    if (j.retain_partials) {
      auto header = app_json::parse(j.remote_request);
      header.object["options"].object["retain_partials"] = {Value::Bool,"true",{}, {}};
      header.object["recovery_id"] = {Value::String,j.recovery_id,{}, {}};
      j.attempt_id = app_partials::new_id();
      header.object["attempt_id"] = {Value::String,j.attempt_id,{}, {}};
      header.object["resume"] = {Value::Bool,"false",{}, {}};
      header.object["recovery_binding"] = j.recovery_binding;
      j.remote_request = app_json::serialize(header);
      if (j.remote_request.size() > FRAME_LIMIT) throw std::runtime_error("recoverable selection exceeds native request frame limit");
    }
  }
  return j;
}

// Advisory locks on existing canonical directory inodes: shared ancestors and an
// exclusive destination serialize overlapping app jobs, including path aliases.
std::map<std::string, int> move_lock_fds;
std::set<std::string> move_lock_roots;
std::map<std::pair<u64, u64>, std::pair<int, bool>> move_inode_fds;
bool move_locks_valid() {
  for (const auto& [path, fd] : move_lock_fds) {
    struct stat held, named;
    if (fstat(fd, &held) || lstat(path.c_str(), &named) || !DestinationRevision::from(held).same_object(DestinationRevision::from(named))) {
      native_error(0, path, "destination_ancestor_changed"); return false;
    }
  }
  return true;
}
std::vector<int> destination_locks(const std::string& path) {
  struct stat st;
  if (lstat(path.c_str(), &st)) { native_error(errno, path, "destination_preflight"); return {}; }
  if (!S_ISDIR(st.st_mode)) { native_error(ENOTDIR, path, "destination_preflight"); return {}; }
  char resolved[PATH_MAX];
  if (!realpath(path.c_str(), resolved)) { native_error(errno, path, "destination_preflight"); return {}; }
  std::string canonical = resolved;
  std::vector<std::string> paths;
  for (std::string p = canonical;;) { paths.push_back(p); if (p == "/") break; p = p.substr(0, p.rfind('/')); if (p.empty()) p = "/"; }
  std::vector<int> fds;
  for (auto i = paths.rbegin(); i != paths.rend(); ++i) {
    auto held = move_lock_fds.find(*i);
    int fd = held != move_lock_fds.end() ? fcntl(held->second, F_DUPFD_CLOEXEC, 0) : open(i->c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    bool reused = false;
    if (fd >= 0 && !move_inode_fds.empty()) {
      struct stat node;
      if (fstat(fd, &node) == 0) {
        auto lease = move_inode_fds.find({node.st_dev, node.st_ino});
        if (lease != move_inode_fds.end()) {
          int duplicate = fcntl(lease->second.first, F_DUPFD_CLOEXEC, 0);
          close(fd); fd = duplicate;
          reused = *i != canonical || lease->second.second;
        }
      }
    }
    if (fd < 0 || (!reused && flock(fd, (*i == canonical ? LOCK_EX : LOCK_SH) | LOCK_NB))) {
      int code = errno;
      if (fd >= 0) close(fd);
      for (int held : fds) close(held);
      if (code == EWOULDBLOCK || code == EAGAIN) {
        child_event("\"type\":\"error\",\"category\":\"conflict\",\"operation\":\"destination_lock\",\"endpoint\":\"local\",\"path\":" + app_json::path(path) + ",\"native_code\":" + quote(std::to_string(code)) + ",\"retryable\":true,\"message\":\"overlapping destination is busy\"");
      } else native_error(code, path, "destination_lock");
      return {};
    }
    fds.push_back(fd);
  }
  // Catch a changed final path before starting the engine.
  struct stat pinned, current;
  if (fstat(fds.back(), &pinned) || lstat(path.c_str(), &current) || pinned.st_dev != current.st_dev || pinned.st_ino != current.st_ino) {
    for (int fd : fds) close(fd);
    native_error(ESTALE, path, "destination_preflight");
    return {};
  }
  destination_root = path;
  root_revision = DestinationRevision::from(pinned);
  g_app_destination_check = destination_root_valid;
  return fds;
}
struct MoveLocks {
  std::vector<int> fds;
  ~MoveLocks() {
    move_lock_fds.clear(); move_lock_roots.clear(); move_inode_fds.clear();
    for (int fd : fds) close(fd);
  }
  bool acquire(const Value& request) {
    std::set<std::string> paths;
    auto add = [&](const Value& endpoint, bool source) {
      if (endpoint.at("kind").string() != "local") return true;
      auto p = endpoint_path(endpoint);
      if (source) { p = p.substr(0, p.rfind('/')); if (p.empty()) p = "/"; }
      char resolved[PATH_MAX];
      if (!realpath(p.c_str(), resolved)) { native_error(errno, p, "move_preflight"); return false; }
      paths.emplace(resolved); return true;
    };
    if (!add(request.at("destination"), false)) return false;
    for (const auto& selected : request.at("sources").array) if (!add(selected.at("endpoint"), true)) return false;
    // Ancestor roots cover descendants. Disjoint roots retain shared ancestors,
    // so a move never turns the whole filesystem into an exclusive lease.
    for (const auto& root : paths) {
      bool covered = false;
      for (const auto& prior : move_lock_roots) if (root == prior || prior == "/" || root.starts_with(prior + '/')) covered = true;
      struct stat root_stat;
      if (lstat(root.c_str(), &root_stat) == 0) {
        auto existing = move_inode_fds.find({root_stat.st_dev, root_stat.st_ino});
        if (existing != move_inode_fds.end() && existing->second.second) covered = true;
      }
      if (covered) continue;
      auto acquired = destination_locks(root);
      if (acquired.empty()) return false;
      std::string p = root;
      for (auto i = acquired.rbegin(); i != acquired.rend(); ++i) {
        move_lock_fds.try_emplace(p, *i);
        struct stat node;
        if (fstat(*i, &node) == 0) {
          auto [entry, inserted] = move_inode_fds.try_emplace({node.st_dev, node.st_ino}, std::pair<int, bool>{*i, p == root});
          if (!inserted && p == root) entry->second.second = true;
        }
        p = p.substr(0, p.rfind('/')); if (p.empty()) p = "/";
      }
      move_lock_roots.insert(root);
      fds.insert(fds.end(), acquired.begin(), acquired.end());
    }
    return move_locks_valid();
  }
};
app_move::RenameResult rename_move(const Value& source, const Value& destination,
                                  const Value& source_revision, const Value& destination_revision, bool replace) {
  std::string src = endpoint_path(source), dst = endpoint_path(destination);
  auto src_slash = src.rfind('/'), dst_slash = dst.rfind('/');
  auto src_parent = src_slash == 0 ? "/" : src.substr(0, src_slash);
  auto dst_parent = dst_slash == 0 ? "/" : dst.substr(0, dst_slash);
  char src_real[PATH_MAX], dst_real[PATH_MAX];
  if (!realpath(src_parent.c_str(), src_real) || !realpath(dst_parent.c_str(), dst_real)) return {errno};
  std::string common = src_real, target_parent = dst_real;
  while (common != "/" && common != target_parent && !target_parent.starts_with(common + '/')) {
    common = common.substr(0, common.rfind('/')); if (common.empty()) common = "/";
  }
  std::vector<int> locks;
  if (move_lock_fds.empty()) {
    locks = destination_locks(common);
    if (locks.empty()) return {0, false, true};
  } else if (!move_locks_valid()) return {0, false, true};
  struct Locks { std::vector<int>& fds; ~Locks() { for (int fd : fds) close(fd); } } guard{locks};
  int from = open(src_parent.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
  int to = open(dst_parent.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
  struct FD { int fd; ~FD() { if (fd >= 0) close(fd); } } from_guard{from}, to_guard{to};
  if (from < 0 || to < 0) return {errno};
  auto expected_source = app_actions::parse_revision(source_revision), expected_target = app_actions::parse_revision(destination_revision);
  auto expected_from = app_actions::parse_revision(source.at("parent_revision")), expected_to = app_actions::parse_revision(destination.at("parent_revision"));
  struct stat st;
  auto parent_valid = [&](int fd, const std::string& path, const DestinationRevision& expected) {
    return fstat(fd, &st) == 0 && expected == DestinationRevision::from(st) &&
      lstat(path.c_str(), &st) == 0 && expected == DestinationRevision::from(st);
  };
  auto leaf_valid = [&](int fd, const std::string& name, const DestinationRevision& expected) {
    DestinationRevision actual;
    if (fstatat(fd, name.c_str(), &st, AT_SYMLINK_NOFOLLOW) == 0) actual = DestinationRevision::from(st);
    else if (errno == ENOENT) actual = DestinationRevision::absent();
    else return false;
    return expected == actual;
  };
  auto src_name = src.substr(src_slash+1), dst_name = dst.substr(dst_slash+1);
  if (src_name == dst_name && expected_from.same_object(expected_to)) return {0, false, true};
  if (g_stop.load() || !destination_root_valid() || !parent_valid(from, src_parent, expected_from) || !parent_valid(to, dst_parent, expected_to) ||
      !leaf_valid(from, src_name, expected_source) || !leaf_valid(to, dst_name, expected_target)) return {0, false, true};
  if (S_ISREG(expected_source.mode) && expected_source.links > 1 && expected_source.same_object(expected_target)) return {EEXIST};
  int rc = replace ? renameat(from, src_name.c_str(), to, dst_name.c_str()) : destination_rename_noreplace(from, src_name.c_str(), to, dst_name.c_str());
  if (rc) return {errno};
  auto named_parent = [&](int fd, const std::string& path, const DestinationRevision& expected) {
    return fstat(fd, &st) == 0 && expected.same_object(DestinationRevision::from(st)) &&
      lstat(path.c_str(), &st) == 0 && expected.same_object(DestinationRevision::from(st));
  };
  bool valid = move_locks_valid() && destination_root_valid() &&
    named_parent(from, src_parent, expected_from) && named_parent(to, dst_parent, expected_to) &&
    fstatat(to, dst_name.c_str(), &st, AT_SYMLINK_NOFOLLOW) == 0 && expected_source.same_object(DestinationRevision::from(st));
  return {0, true, !valid};
}
int source_preflight(const Job& j) {
  struct Ready { std::string path, relative; Entry entry; };
  std::vector<Ready> ready;
  int result = 0;
  for (auto path : j.sources) {
    while (path.size() > 1 && path.back() == '/') path.pop_back();
    struct stat st;
    std::string relative = j.contents ? "" : path.substr(path.rfind('/') + 1);
    auto mapped = j.selection_names.find(path);
    if (mapped != j.selection_names.end()) relative = mapped->second;
    if (lstat(path.c_str(), &st)) {
      int error = errno;
      auto item = transfer_item(relative, path, {}, Entry{});
      ItemScope scope(item);
      native_error(error, path, "source_preflight");
      item_finish(item, "failure", "source_preflight");
      if (!result) result = RERR_FILESELECT;
      continue;
    }
    Entry entry; entry_from_stat(st, entry);
    if (g_app_preview_source_check) {
      auto observed=transfer_item(relative,path,{},entry,false);
      auto revision=DestinationRevision::from(st);
      if (!item_preview_source_valid(observed,&revision)) {
        auto failed=transfer_item(relative,path,{},entry);
        failed->failed.store(true); failed->source_failed.store(true); failed->preview_stale.store(true);
        item_finish(failed,"failure","stale_preview");
        if (!result) result=RERR_PARTIAL;
        continue;
      }
    }
    if ((j.contents && !S_ISDIR(st.st_mode)) ||
        (!S_ISREG(st.st_mode) && !S_ISLNK(st.st_mode) && !S_ISDIR(st.st_mode))) {
      auto item = transfer_item(relative, path, {}, entry);
      ItemScope scope(item); item_error(false, true);
      child_event("\"type\":\"error\",\"category\":\"unsupported_feature\",\"operation\":\"source_preflight\",\"endpoint\":\"local\",\"path\":" + app_json::path(path) +
        ",\"side\":\"source\",\"stage\":\"preflight\",\"item_id\":" + quote(app_json::hex(relative)) + ",\"native_code\":null,\"retryable\":false,\"message\":\"unsupported source type or contents selection\"");
      item_finish(item, "failure", "unsupported_selection");
      if (!result) result = RERR_UNSUPPORTED;
      continue;
    }
    ready.push_back({std::move(path), std::move(relative), entry});
  }
  if (result) for (const auto& selected : ready)
    item_finish(transfer_item(selected.relative, selected.path, {}, selected.entry), "skipped", "preflight_failed");
  return result;
}
void copy_options(const Job& j) {
  g_app_selection_names = j.selection_names;
  g_opt = Options{};
  g_opt.recursive = g_opt.links = true;
  g_opt.perms = j.perms; g_opt.times = j.times;
  g_opt.ignore_existing = j.policy == "skip";
  g_opt.jobs = (i64)j.jobs; g_opt.bwlimit = j.bwlimit; g_opt.timeout = j.timeout;
  g_opt.clone = false; g_opt.ignore_times = true;
  g_opt.partial = j.retain_partials;
  g_opt.itemize = true; g_opt.itemize_level = 2; g_opt.am_root = geteuid() == 0;
  output_configure();
  g_umask = umask(0); init_ids();
}
app_ssh::RemoteLease* current_move_lease = nullptr;
int execute(const Job& j, const app_ssh::AuthContext& auth, int control_fd) {
  g_msg_sink = diagnostic; g_output_sink = item_event; g_fs_error_sink = native_error;
  std::unique_ptr<app_preview::NativeGuard> preview_native;
  std::shared_ptr<const app_preview::Inventory> admitted_preview;
  if (j.preview_request.kind == Value::Object) {
    auto read = [&](const Value& request,const app_preview::Emit& emit) -> int {
      const auto op=request.at("op").string();
      if (op!="lstat" && op!="list" && op!="preflight") throw std::runtime_error("non-read operation in preview");
      struct Route { std::function<void(std::string)> previous; ~Route() { event_route=std::move(previous); } } route{std::exchange(event_route,emit)};
      return execute(validate(request),auth,control_fd);
    };
    app_preview::Inventory inventory;
    int rc=app_preview::run(j.preview_request,read,public_event,j.preview_guard,&inventory);
    if (j.op=="preview" || rc) return rc;
    admitted_preview=std::make_shared<app_preview::Inventory>(std::move(inventory));
    preview_native=std::make_unique<app_preview::NativeGuard>(admitted_preview,public_event,!j.connection || j.push,!j.push);
  }
  if (j.move_request) {
    MoveLocks locks;
    if (!locks.acquire(*j.move_request)) {
      app_move::not_started(*j.move_request, "move_lock_unavailable", public_event);
      return RERR_FILESELECT;
    }
    app_ssh::RemoteLease remote;
    struct LeaseContext {
      app_ssh::RemoteLease* previous;
      ~LeaseContext() { current_move_lease = previous; }
    } context{std::exchange(current_move_lease, &remote)};
    auto step = [&](const Value& request, const app_move::Emit& emit) -> int {
      struct Route {
        std::function<void(std::string)> previous;
        ~Route() { event_route = std::move(previous); }
      } route{std::exchange(event_route, emit)};
      if (!move_locks_valid()) return RERR_PARTIAL;
      return execute(validate(request), auth, control_fd);
    };
    int code = app_move::run(*j.move_request, step, rename_move, public_event);
    int lease_code = remote.finish(public_event);
    return code ? code : lease_code;
  }
  if (j.connection && j.op != "copy" && !(j.op == "verify_recovery" && !j.push)) {
    if (current_move_lease && current_move_lease->active())
      return current_move_lease->run(app_json::parse(j.remote_request), child_event);
    return app_ssh::run(*j.connection, j.op, j.remote_request, auth, control_fd, child_event);
  }
  if (j.op == "fingerprint") return fingerprint(j.path);
  if (j.op == "preflight") {
    try {
      auto value = app_json::serialize(app_preflight::inspect(j.path,j.preflight_space));
      child_event(value.substr(1,value.size()-2)); return 0;
    } catch (const std::system_error& error) {
      native_error(error.code().value(),j.path,"destination_preflight"); return RERR_FILESELECT;
    }
  }
  if (j.op == "recovery_quiescence")
    return app_actor::quiescence(j.path,j.recovery_id,j.attempt_id,j.actor_role,j.recovery_revision,j.actor_cleanup,child_event);
  if (j.op == "recovery_state" || j.op == "cleanup_partials" || j.op == "_pause_checkpoint" || j.op == "verify_recovery" || j.op == "_verify_recovery") {
    auto locks = destination_locks(j.path);
    if (locks.empty()) return RERR_FILESELECT;
    bool verify = j.op == "verify_recovery" || j.op == "_verify_recovery";
    if ((j.op == "_pause_checkpoint" || verify) && !anchor_destination(j.path+'/')) {
      native_error(errno,j.path,"anchor_destination");
      for (int fd : locks) close(fd);
      return RERR_FILESELECT;
    }
    int rc = verify ? app_partials::verify(j.path,j.recovery_id,j.recovery_binding,j.recovery_revision,j.recovery_inventory,child_event) :
      j.op == "_pause_checkpoint" ? app_partials::checkpoint(j.path,j.recovery_id,j.recovery_binding,child_event,j.attempt_id) :
      j.op == "recovery_state" ? app_partials::inspect(j.path,j.recovery_id,child_event) :
      app_partials::cleanup(j.path,j.recovery_id,j.recovery_revision,child_event);
    for (int fd : locks) close(fd);
    return rc;
  }
  if (j.action) {
    auto locks = destination_locks(j.path);
    int rc = app_actions::run(*j.action, locks.empty() ? -1 : locks.back(), destination_root_valid, child_event);
    for (int fd : locks) close(fd);
    return rc;
  }
  if (j.op == "resolve") { child_event("\"type\":\"resolved\",\"endpoint\":{\"kind\":\"local\",\"path\":" + app_json::path(j.path) + "}"); return 0; }
  if (j.op != "copy") return browse(j.op, j.path);
  g_item_sink = transfer_event;
  copy_push = j.push; copy_pull = j.connection && !j.push;
  if (!j.connection || j.push) { int code = source_preflight(j); if (code) return code; }
  std::vector<int> locks;
  if (!j.push) { locks = destination_locks(j.path); if (locks.empty()) return RERR_FILESELECT; }
  if (preview_native && !preview_native->root_valid()) { for (int fd:locks) close(fd); return RERR_PARTIAL; }
  copy_options(j);
  std::unique_ptr<app_partials::Session> recovery;
  Value peer_actor;
  auto prepare_recovery = [&]() -> int {
    if (!anchor_destination(j.path + '/')) {
      native_error(errno,j.path,"anchor_destination");
      return RERR_FILESELECT;
    }
    try { recovery = std::make_unique<app_partials::Session>(j.path,j.recovery_id,j.recovery_binding,j.resuming,child_event,peer_actor); }
    catch (const app_partials::Error&) { return RERR_PARTIAL; }
    return 0;
  };
  if (j.retain_partials && !j.connection) {
    int code = prepare_recovery();
    if (code) { for (int fd : locks) close(fd); return code; }
  }
  app_conflict::configure(j.policy == "ask", j.conflict_timeout, child_event);
  app_conflict::ControlReader local_controls(j.connection ? -1 : control_fd);
  copy_push = j.push; copy_pull = j.connection && !j.push;
  copy_progress_enabled.store(!j.connection);
  g_phase_sink = progress_event;
  ProgressSampler sampler;
  if (!j.connection) { child_event("\"type\":\"phase\",\"phase\":\"scanning\""); progress_event(); }
  int rc;
  if (j.connection) {
    bool submitted = false;
    app_ssh::Copy copy{j.push, !j.selection_names.empty(), j.policy == "ask", j.sources, j.path + '/', [] { copy_progress_enabled.store(true); }, nullptr, false, {}, {}, {}, {}};
    copy.on_submitted = [&] { submitted = true; };
    copy.preview_inventory=admitted_preview;
    copy.recoverable = j.retain_partials;
    copy.attempt_id = j.attempt_id;
    copy.actor_ready = [&](Value value) { peer_actor = std::move(value); };
    if (j.retain_partials) {
      child_event("\"type\":\"recovery_preparing\",\"recovery_id\":" + quote(j.recovery_id) + ",\"endpoint\":" + quote(j.push ? "ssh" : "local") + ",\"root_path\":" + app_json::path(j.path));
      if (!j.push) copy.receiver_preflight = prepare_recovery;
    }
    auto request = j.remote_request;
    if (admitted_preview) {
      auto header=app_json::parse(request);
      header.object["preview_binding"]=app_preview::ManifestSender(*admitted_preview,j.push).header();
      request=app_json::serialize(header);
    }
    if (current_move_lease) {
      copy.lease = current_move_lease;
      auto header = app_json::parse(request);
      header.object["move_lease"] = {Value::Bool, "true", {}, {}};
      request = app_json::serialize(header);
    }
    rc = app_ssh::run(*j.connection, j.op, request, auth, control_fd, child_event, &copy);
    // Before submission, neither the remote job nor the local pull receiver can
    // have started. A missing receipt after an abrupt exit proves nothing.
    if (rc && !submitted)
      child_event("\"type\":\"copy_not_submitted\",\"operation\":\"copy\",\"endpoint\":\"ssh\",\"remote_request_submitted\":false,\"transfer_started\":false");
  } else rc = run_local(j.sources, j.path + '/');
  sampler.stop(); g_phase_sink = nullptr;
  if (recovery) { recovery->finish(rc); if (!rc) rc = g_exit_code.load(); }
  if (rc == 0 && (pending_items() || items_discovered != items_results))
    die(RERR_PROTOCOL, "incomplete app item outcomes after transfer completion");
  for (int fd : locks) close(fd);
  if (g_stop.load()) return RERR_SIGNAL;
  child_event("\"type\":\"summary\",\"logical_bytes_completed\":" + quote(std::to_string(g_stats.receiver_completed_bytes.load())) +
    ",\"files_completed\":" + quote(std::to_string(j.push ? g_stats.acknowledged_files.load() : g_stats.xfer_files.load())) + ",\"reused_bytes\":" + quote(std::to_string(g_stats.delta_matched_bytes.load())) +
    ",\"items_discovered\":" + quote(std::to_string(items_discovered)) + ",\"items_results\":" + quote(std::to_string(items_results)));
  return rc;
}

// Internal handoff on the already authenticated app channel. The public client
// continues using JSON; only the two engines exchange native data frames.
int supervise(const Job&, Reader&, Writer&, std::set<std::string>&, u64 deadline = 0);
int supervise_native(const Job& job, Reader& input, Writer& output) {
  if (!input.pending.empty() || input.eof) throw std::runtime_error("unexpected input before native handoff");
  std::shared_ptr<const app_preview::Inventory> native_preview;
  if (job.native_preview_header.kind!=Value::Null) {
    app_preview::ManifestReceiver manifest(job.native_receiver,job.native_preview_header,job.path);
    while (!manifest.complete()) {
      output.emit("\"type\":\"preview_binding_ready\",\"next_sequence\":"+quote(std::to_string(manifest.next_sequence())));
      std::string frame; u64 deadline=now_ns()+(u64)(job.timeout ? job.timeout : 30)*1000000000ULL;
      while (!input.pop(frame)) {
        if (input.eof || interrupted || now_ns()>deadline) throw std::runtime_error("preview binding disconnected or timed out");
        pollfd p{input.fd,POLLIN,0}; if (poll(&p,1,50)>0) input.read_ready();
      }
      manifest.append(app_json::parse(frame),frame.size());
    }
    if (!input.pending.empty()) throw std::runtime_error("unexpected input after preview binding");
    native_preview=std::make_shared<app_preview::Inventory>(manifest.release());
  }
  std::unique_ptr<app_actor::Lease> actor;
  if (!job.attempt_id.empty()) actor = std::make_unique<app_actor::Lease>(job.recovery_id,job.attempt_id,job.native_receiver ? "receiver" : "sender");
  Value actor_record;
  if (actor) actor_record = app_json::parse("{\"type\":\"recovery_actor\",\"recovery_id\":" + quote(job.recovery_id) + ",\"attempt_id\":" + quote(job.attempt_id) +
    ",\"role\":" + quote(job.native_receiver ? "receiver" : "sender") + ",\"endpoint\":\"local\",\"actor_path\":" + app_json::path(actor->path) +
    ",\"actor_revision\":" + revision_json(actor->revision) + '}');
  MoveLocks lease;
  if (job.native_move_lease) {
    if (!(PROTO_FEATURES & PF_APP_LEASE)) throw RequestError("unsupported_feature", "move leases are unavailable");
    auto selected = app_json::parse("{\"sources\":[],\"destination\":{\"kind\":\"local\"}}");
    auto folder = [](const std::string& p) { auto end = p.rfind('/'); return end == 0 ? std::string("/") : p.substr(0, end); };
    selected.object["destination"].object["path"] = app_json::parse(app_json::path(job.native_receiver ? job.path : folder(job.sources.front())));
    if (!job.native_receiver) for (const auto& p : job.sources)
      selected.object["sources"].array.push_back(app_json::parse("{\"endpoint\":{\"kind\":\"local\",\"path\":" + app_json::path(p) + "}}"));
    bool acquired;
    {
      auto previous = std::exchange(event_route, [&](std::string fields) { output.emit(std::move(fields)); });
      try { acquired = lease.acquire(selected); }
      catch (...) { event_route = std::move(previous); throw; }
      event_route = std::move(previous);
    }
    if (!acquired) { output.result("failure", RERR_FILESELECT); return RERR_FILESELECT; }
  }
  sigset_t blocked, previous;
  sigemptyset(&blocked); sigaddset(&blocked, SIGTERM); sigaddset(&blocked, SIGINT); sigaddset(&blocked, SIGHUP);
  sigprocmask(SIG_BLOCK, &blocked, &previous);
  pid_t supervisor = getpid(), child = fork();
  if (child < 0) { sigprocmask(SIG_SETMASK, &previous, nullptr); throw std::runtime_error("cannot start native transfer"); }
  if (!child) {
    setpgid(0, 0);
    struct sigaction sa{}; sa.sa_handler = child_signal;
    sigaction(SIGTERM, &sa, nullptr); sigaction(SIGINT, &sa, nullptr); sigaction(SIGHUP, &sa, nullptr);
    sigprocmask(SIG_SETMASK, &previous, nullptr);
    std::thread([supervisor] {
      while (getppid() == supervisor) std::this_thread::sleep_for(std::chrono::milliseconds(50));
      g_stop.store(1); kill(0, SIGTERM);
      std::this_thread::sleep_for(std::chrono::seconds(2)); kill(0, SIGKILL);
    }).detach();
    event_wire = true;
    g_fs_error_sink = native_error;
    g_item_sink = transfer_event;
    std::unique_ptr<app_preview::NativeGuard> preview_guard;
    if (native_preview) preview_guard=std::make_unique<app_preview::NativeGuard>(native_preview,child_event);
    copy_options(job);
    app_conflict::configure(job.policy == "ask", job.conflict_timeout, child_event);
    std::vector<int> locks;
    std::unique_ptr<app_partials::Session> recovery;
    AppServer server{job.native_receiver, job.native_receiver ? std::vector<std::string>{job.path + '/'} : job.sources, [&]() -> int {
      if (!job.native_receiver) return source_preflight(job);
      locks = destination_locks(job.path);
      if (locks.empty()) return RERR_FILESELECT;
      if (preview_guard && !preview_guard->root_valid()) return RERR_PARTIAL;
      if (job.retain_partials) {
        if (!anchor_destination(job.path + '/')) { native_error(errno,job.path,"anchor_destination"); return RERR_FILESELECT; }
        try { recovery = std::make_unique<app_partials::Session>(job.path,job.recovery_id,job.recovery_binding,job.resuming,child_event,actor_record); }
        catch (const app_partials::Error&) { return RERR_PARTIAL; }
      }
      return 0;
    }, job.native_move_lease, job.retain_partials, [&](int code) { if (recovery) recovery->finish(code); }};
    int code = run_server(&server);
    for (int fd : locks) close(fd);
    _Exit(code);
  }
  setpgid(child, child); sigprocmask(SIG_SETMASK, &previous, nullptr);
  int status = 0; u64 lost_at = 0, cancel_at = 0;
  try {
    output.emit("\"type\":\"started\",\"operation\":\"copy\",\"job_id\":" + quote(output.id));
    if (actor) output.emit("\"type\":\"recovery_actor\",\"recovery_id\":" + quote(job.recovery_id) + ",\"attempt_id\":" + quote(job.attempt_id) +
      ",\"role\":" + quote(job.native_receiver ? "receiver" : "sender") + ",\"endpoint\":\"local\",\"actor_path\":" + app_json::path(actor->path) +
      ",\"actor_revision\":" + revision_json(actor->revision));
    output.emit("\"type\":\"transfer_ready\",\"native_wire\":\"4\"");
    for (;;) {
      pid_t result = waitpid(child, &status, WNOHANG);
      if (result == child) break;
      if (result < 0 && errno != EINTR) throw std::runtime_error("native transfer wait failed");
      pollfd p{lost_at ? -1 : STDIN_FILENO, 0, 0}; poll(&p, 1, 50);
      if ((p.revents & (POLLHUP | POLLERR)) && !lost_at) lost_at = now_ns();
      // EOF can follow the native receiver's completed F_DONE acknowledgement.
      // Give normal teardown two seconds; then stop and bound any remaining IO.
      if (!cancel_at && (interrupted || (lost_at && now_ns()-lost_at >= CANCEL_NS))) {
        kill(-child, SIGTERM); cancel_at = now_ns();
      }
      if (cancel_at && now_ns()-cancel_at >= CANCEL_NS) kill(-child, SIGKILL);
    }
  } catch (...) {
    kill(-child, SIGKILL); while (waitpid(child, &status, 0) < 0 && errno == EINTR) {}
    throw;
  }
  int code = WIFEXITED(status) ? WEXITSTATUS(status) : RERR_SIGNAL;
  if (!job.native_move_lease || !WIFEXITED(status) || interrupted) return code;
  // Both engines end native reads at the negotiated F_APP_END boundary. The
  // parent owns these locks before the worker starts and throughout this tail.
  output.emit("\"type\":\"move_lease_ready\",\"code\":" + quote(std::to_string(code)));
  auto within = [](const std::string& p, const std::string& root) {
    return p == root || root == "/" || p.starts_with(root + '/');
  };
  std::string frame;
  u64 call = 0, last_activity = now_ns();
  while (!interrupted) {
    while (!input.pop(frame)) {
      if (input.eof) return RERR_SIGNAL;
      // Bound abandoned sessions while permitting a long local fingerprint.
      if (now_ns()-last_activity > 3600000000000ULL) return RERR_TIMEOUT;
      pollfd p{input.fd, POLLIN, 0};
      if (poll(&p, 1, 50) > 0) input.read_ready();
      if (interrupted) return RERR_SIGNAL;
    }
    last_activity = now_ns();
    auto request = app_json::parse(frame);
    auto id = request_id(request), op = request.at("op").string();
    if (id != "lease-call-" + std::to_string(++call) || call > 1000000)
      throw std::runtime_error("invalid move lease request sequence");
    output.id = id;
    if (op == "_move_release") {
      bool valid = move_locks_valid();
      if (!valid) output.error("conflict", "leased move directory changed before release");
      output.result(valid ? "success" : "partial_failure", valid ? 0 : RERR_PARTIAL);
      return valid ? 0 : RERR_PARTIAL;
    }
    bool read = op == "lstat" || op == "list" || op == "fingerprint";
    bool remove = op == "delete" && !job.native_receiver && !request.at("recursive").boolean() &&
      request.at("items").kind == Value::Array && request.at("items").array.size() == 1;
    if (!read && !remove) throw std::runtime_error("unsupported move lease operation");
    auto p = local_path(request.at("endpoint"));
    auto target = p;
    if (remove) {
      auto leaf = app_json::unhex(request.at("items").array.front().at("name").at("bytes_hex").string());
      if (leaf.empty() || leaf == "." || leaf == ".." || leaf.find('/') != leaf.npos || leaf.find('\0') != leaf.npos)
        throw std::runtime_error("unsafe move lease removal name");
      target += (p == "/" ? "" : "/") + leaf;
    }
    bool allowed = job.native_receiver && read && within(p, job.path);
    if (!job.native_receiver) for (auto source : job.sources) {
      while (source.size() > 1 && source.back() == '/') source.pop_back();
      auto end = source.rfind('/'); auto parent = end == 0 ? "/" : source.substr(0, end);
      allowed |= read ? within(p, source) || (op == "lstat" && p == parent) : within(target, source) && !(job.contents && target == source);
    }
    if (!allowed) throw std::runtime_error("move lease request leaves its selection");
    if (!move_locks_valid()) {
      output.error("conflict", "leased move directory changed"); output.result("partial_failure", RERR_PARTIAL); continue;
    }
    std::set<std::string> ids{id};
    (void)supervise(validate(request), input, output, ids);
    last_activity = now_ns();
  }
  return RERR_SIGNAL;
}

// Cache invalidation is a conservative observation, never a completion receipt.
// The supervisor can still invalidate the destination scope when a fatal worker
// or disconnected helper loses all per-item receipts. Resume validates as copy.
struct CopyInvalidation {
  bool enabled, finished = false;
  std::string root, endpoint;
  explicit CopyInvalidation(const Job& job) : enabled(job.op == "copy"),
    root(job.path), endpoint(job.push ? "ssh" : "local") {}
  static std::string parent(const std::string& path) {
    auto at = path.rfind('/'); return at == 0 || at == path.npos ? "/" : path.substr(0,at);
  }
  void emit(Writer& output,const std::string& path,bool recursive,std::string_view reason,const Value& item_id = {}) {
    output.emit("\"type\":\"invalidate\",\"endpoint\":" + quote(endpoint) + ",\"path\":" + app_json::path(path) +
      ",\"parent_path\":" + app_json::path(parent(path)) + ",\"recursive\":" + (recursive ? "true" : "false") +
      ",\"reason\":" + quote(reason) + ",\"item_id\":" + app_json::serialize(item_id));
  }
  void forward(const std::string& fields,Writer& output) {
    if (!enabled) { output.emit(fields); return; }
    auto event = app_json::parse('{'+fields+'}');
    // Preserve summary/result adjacency. Native copy emits its summary only
    // after destination IO and recovery finalization; missing summaries use
    // the post-reap fallback below instead.
    if (event.at("type").string() == "summary") finish(output);
    output.emit(fields);
    if (event.at("type").string() != "item_result" || event.at("status").string() == "skipped" ||
        event.at("destination_path").kind != Value::Object) return;
    auto path = app_json::unhex(event.at("destination_path").at("bytes_hex").string());
    // Hints stay in the request's selected destination scope, even if an old
    // helper returns an unexpected path. The scope hint still covers the job.
    if (path != root && !(root == "/" ? path.starts_with('/') : path.starts_with(root+'/'))) return;
    emit(output,path,event.at("entry_type").string() == "directory","transfer_item",event.at("item_id"));
  }
  void finish(Writer& output) {
    if (!enabled || finished) return;
    emit(output,root,true,"transfer_attempt"); finished = true;
  }
};

// The engine can exit from a worker on a fatal syscall. Retain the coordinator's
// inventory outside that process so absence of a receipt remains explicit.
struct MoveRecovery {
  std::map<std::string, Value> items;
  std::set<std::string> reported;
  explicit MoveRecovery(const Job& job) {
    if (!job.move_request) return;
    const auto& request = *job.move_request;
    for (const auto& selected : request.at("sources").array) {
      auto p = endpoint_path(selected.at("endpoint"));
      bool contents = selected.at("mode").string() == "contents";
      auto relative = contents ? "" : selected.object.count("destination_name") ? app_json::unhex(selected.at("destination_name").at("bytes_hex").string()) : p.substr(p.rfind('/')+1);
      auto record = app_json::parse("{\"item_id\":" + quote(app_json::hex(relative)) + ",\"scope_root\":" + (contents ? "true" : "false") + "}");
      record.object["source_path"] = selected.at("endpoint").at("path");
      record.object["source_endpoint"] = selected.at("endpoint").at("kind");
      record.object["destination_endpoint"] = request.at("destination").at("kind");
      items.emplace(app_json::hex(p), std::move(record));
    }
  }
  void accept(const std::string& fields) {
    auto event = app_json::parse('{'+fields+'}'); auto type = event.at("type").string();
    if (type != "move_discovered" && type != "move_result" && type != "item_result") return;
    auto key = event.at("source_path").at("bytes_hex").string();
    if (type == "move_discovered") items[key] = std::move(event);
    else if (type == "move_result") { reported.insert(key); items[key] = std::move(event); }
    else {
      auto found = items.find(key); if (found == items.end() || reported.count(key)) return;
      auto& item = found->second;
      bool complete = event.at("status").string() == "success" && event.at("metadata_complete").kind == Value::Bool && event.at("metadata_complete").boolean();
      item.object["copied"] = {Value::Bool, complete || event.at("content_published").boolean() ? "true" : "false", {}, {}};
      item.object["destination_completed"] = {Value::Bool, complete ? "true" : "false", {}, {}};
      item.object["content_published"] = event.at("content_published");
      item.object["destination_path"] = event.at("destination_path");
    }
  }
  void finish(Writer& output) {
    u64 copied = 0, removed = 0, remaining = 0, unknown = 0, renamed = 0;
    for (auto& [key, item] : items) {
      if (!reported.count(key)) {
        item.object["type"] = {Value::String, "move_result", {}, {}};
        item.object["status"] = {Value::String, "unknown", {}, {}};
        item.object["reason"] = {Value::String, "move_outcome_unknown", {}, {}};
        for (const auto* field : {"removed", "remaining", "renamed"}) item.object[field] = Value{};
        for (const auto* field : {"copied", "destination_completed", "content_published", "destination_path"}) item.object.try_emplace(field, Value{});
        auto encoded = app_json::serialize(item); output.emit(encoded.substr(1, encoded.size()-2));
      }
      auto yes = [&](const char* field) { auto found = item.object.find(field); return found != item.object.end() && found->second.kind == Value::Bool && found->second.boolean(); };
      copied += yes("copied"); removed += yes("removed"); renamed += yes("renamed"); remaining += yes("remaining");
      unknown += !reported.count(key) || item.at("remaining").kind == Value::Null;
    }
    output.emit("\"type\":\"move_summary\",\"items_copied\":" + quote(std::to_string(copied)) + ",\"items_removed\":" + quote(std::to_string(removed)) +
      ",\"items_remaining\":" + quote(std::to_string(remaining)) + ",\"items_unknown\":" + quote(std::to_string(unknown)) +
      ",\"items_renamed\":" + quote(std::to_string(renamed)) + ",\"items_total\":" + quote(std::to_string(items.size())) + ",\"recovered\":true");
  }
};

int supervise(const Job& job, Reader& input, Writer& output, std::set<std::string>& ids, u64 deadline) {
  CopyInvalidation invalidation(job);
  MoveRecovery move_recovery(job);
  app_ssh::AuthContext auth;
  int controls[2] = {-1, -1};
  if (job.connection) auth.start();
  if (job.connection || job.policy == "ask") {
    if (pipe(controls)) throw std::runtime_error("cannot create job control pipe");
    for (int fd : controls) fcntl(fd, F_SETFD, FD_CLOEXEC);
    nonblocking(controls[1]);
  }
  int fds[2]; if (pipe(fds)) throw std::runtime_error("cannot create job pipe");
  for (int fd : fds) fcntl(fd, F_SETFD, FD_CLOEXEC);
  pid_t supervisor = getpid();
  // The child must install its cancellation handler before a pending signal runs.
  sigset_t blocked, previous;
  sigemptyset(&blocked); sigaddset(&blocked, SIGTERM); sigaddset(&blocked, SIGINT); sigaddset(&blocked, SIGHUP);
  sigprocmask(SIG_BLOCK, &blocked, &previous);
  pid_t child = fork();
  if (child < 0) { sigprocmask(SIG_SETMASK, &previous, nullptr); close(fds[0]); close(fds[1]); throw std::runtime_error("cannot start job"); }
  if (!child) {
    setpgid(0, 0);
    close(fds[0]);
    if (controls[1] >= 0) close(controls[1]);
    int null = open("/dev/null", O_RDWR);
    if (null < 0 || dup2(null, STDIN_FILENO) < 0 || dup2(null, STDOUT_FILENO) < 0) _Exit(RERR_IPC);
    if (null > 2) close(null);
    event_fd = fds[1];
    struct sigaction sa{}; sa.sa_handler = child_signal; sigaction(SIGTERM, &sa, nullptr); sigaction(SIGINT, &sa, nullptr); sigaction(SIGHUP, &sa, nullptr);
    sigprocmask(SIG_SETMASK, &previous, nullptr);
    try {
      nonblocking(event_fd);
      // Portable parent-death supervision also works on macOS. A hard supervisor
      // crash cannot leave a writer behind, even if it is blocked in file IO.
      std::thread([supervisor, auth_directory = auth.directory] {
        while (getppid() == supervisor) std::this_thread::sleep_for(std::chrono::milliseconds(50));
        g_stop.store(1);
        kill(0, SIGTERM);
        app_ssh::cleanup_directory(auth_directory);
        std::this_thread::sleep_for(std::chrono::seconds(2));
        kill(0, SIGKILL);  // Also stops SSH and askpass descendants.
        _Exit(RERR_SIGNAL);
      }).detach();
      int rc = execute(job, auth, controls[0]);
      if (getppid() != supervisor) auth.cleanup();
      _Exit(rc);
    }
    catch (const std::exception& e) { diagnostic(2, RERR_FILEIO, e.what()); _Exit(RERR_FILEIO); }
  }
  setpgid(child, child);
  sigprocmask(SIG_SETMASK, &previous, nullptr);
  auth.close_listener();
  if (controls[0] >= 0) close(controls[0]);
  close(fds[1]); nonblocking(fds[0]); Reader events{fds[0], {}, false};
  bool cancelled = false, forced = false, child_done = false, summary = job.op != "copy" && job.op != "move";
  bool pause_requested = false, recovery_ready = false;
  Value actor;
  u64 cancel_at = 0; int status = 0;
  auto cancel = [&] { if (!cancelled && !child_done) { cancelled = true; cancel_at = now_ns(); kill(-child, SIGTERM); } };
  auto reap = [&] {
    if (child_done) return;
    siginfo_t info{};
    if (waitid(P_PID, (id_t)child, &info, WEXITED | WNOHANG | WNOWAIT) < 0) {
      if (errno != EINTR) throw std::runtime_error("job wait failed");
      return;
    }
    // Some hosts report a stopped child despite WEXITED. Never enter a
    // blocking reap until the observation actually proves terminal state.
    if (info.si_pid != child || (info.si_code != CLD_EXITED && info.si_code != CLD_KILLED && info.si_code != CLD_DUMPED)) return;
    // Stop any remaining SSH/askpass descendants before releasing the child's
    // PID, so group signalling can never target a recycled, unrelated job ID.
    kill(-child, SIGTERM);
    while (waitpid(child, &status, 0) < 0) { if (errno != EINTR) throw std::runtime_error("job reap failed"); }
    child_done = true;
  };
  try {
    output.emit("\"type\":\"started\",\"operation\":" + quote(job.op) + ",\"job_id\":" + quote(output.id));
    while (!child_done || !events.eof) {
      std::string frame;
      while (input.pop(frame)) {
        auto request = app_json::parse(frame); auto id = request_id(request);
        if (request.at("job_id").string() != output.id) throw std::runtime_error("control request targets a different job");
        if (request.at("op").string() == "conflict_response" && job.policy == "ask") {
          if (id != "decision-" + request.at("conflict_id").string()) throw std::runtime_error("invalid conflict response id");
          if (!send_frame(controls[1], frame + '\n')) throw std::runtime_error("job conflict control disconnected");
          continue;
        }
        if (ids.size() >= 32) throw std::runtime_error("session request limit exceeded");
        if (!ids.insert(id).second) throw std::runtime_error("duplicate request id");
        if (request.at("op").string() == "auth_response" && job.connection) {
          (void)request.at("prompt_id").string();
          bool cancelled_prompt = request.object.count("cancelled") && request.at("cancelled").boolean();
          if (!cancelled_prompt) {
            auto answer = request.at("answer").string();
            if (answer.size() > 4096 || answer.find_first_of("\r\n\0", 0, 3) != answer.npos) throw std::runtime_error("invalid authentication answer");
          }
          if (!send_frame(controls[1], frame + '\n')) throw std::runtime_error("job authentication control disconnected");
          continue;
        }
        if (request.at("op").string() == "pause") {
          for (const auto& [key,value] : request.object)
            if (key != "id" && key != "op" && key != "job_id") throw std::runtime_error("unsupported pause control field");
          bool accepted = job.op == "copy" && job.retain_partials && recovery_ready &&
            (!job.connection || actor.kind == Value::Object) && !cancelled && !child_done;
          const char* reason = accepted ? "stopping" : child_done ? "already_finished" : cancelled ? "already_stopping" :
            !job.retain_partials || job.op != "copy" ? "unsupported_job" : !recovery_ready ? "not_ready" : "peer_pause_unavailable";
          if (accepted) { pause_requested = true; cancel(); }
          output.emit("\"type\":\"pause_ack\",\"job_id\":" + quote(output.id) + ",\"accepted\":" + (accepted ? "true" : "false") +
            ",\"reason\":" + quote(reason) + ",\"recovery_id\":" + (job.retain_partials ? quote(job.recovery_id) : "null"),id);
          continue;
        }
        if (request.at("op").string() != "cancel") throw std::runtime_error("unsupported active-job control request");
        pause_requested = false;
        cancel();
        output.emit("\"type\":\"cancel_ack\",\"job_id\":" + quote(output.id) + ",\"accepted\":" + (child_done ? "false" : "true"), id);
      }
      if (input.eof || interrupted || (deadline && now_ns() >= deadline)) { pause_requested = false; cancel(); }
      while (events.pop(frame)) {
        if (job.retain_partials) {
          auto event = app_json::parse('{'+frame+'}'); auto type = event.at("type").string();
          if ((type == "recovery_created" || type == "recovery_resuming") && event.at("recovery_id").string() == job.recovery_id) recovery_ready = true;
          if (type == "recovery_actor") actor = std::move(event);
        }
        if (job.move_request) move_recovery.accept(frame);
        if (frame.find(job.op == "move" ? "\"type\":\"move_summary\"" : "\"type\":\"summary\"") == 0) summary = true;
        invalidation.forward(frame,output);
      }
      reap();
      if (cancelled && !child_done && now_ns() - cancel_at >= CANCEL_NS) { kill(-child, SIGKILL); forced = true; }
      if (child_done && events.eof) break;
      pollfd p[2] = {{input.eof ? -1 : input.fd, POLLIN, 0}, {events.eof ? -1 : events.fd, POLLIN, 0}};
      if (poll(p, 2, 50) > 0) {
        if (p[0].revents & (POLLIN | POLLHUP | POLLERR)) input.read_ready();
        if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) events.read_ready();
      }
    }
    if (!events.pending.empty()) throw std::runtime_error("truncated job event");
    if (job.move_request && !summary) move_recovery.finish(output);
    close(fds[0]);
    if (controls[1] >= 0) { close(controls[1]); controls[1] = -1; }
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : RERR_SIGNAL;
    invalidation.finish(output);
    if (pause_requested && !input.eof && !interrupted) {
      output.emit("\"type\":\"pause_pending\",\"job_id\":" + quote(output.id) + ",\"recovery_id\":" + quote(job.recovery_id) + ",\"stage\":\"checking_quiescence\"");
      const u64 pause_deadline = now_ns()+30000000000ULL;
      bool aborted = false;
      std::vector<std::string> evidence;
      std::string failure;
      auto check = [&](Job probe,const char* expected_type) {
        if (probe.connection) {
          probe.connection->connect_seconds = std::min(probe.connection->connect_seconds,3u);
          probe.connection->idle_seconds = std::min(probe.connection->idle_seconds,3u);
        }
        for (;;) {
          if (input.eof || interrupted || aborted || now_ns() >= pause_deadline) return false;
          bool proved = false, retryable = false;
          std::string proof;
          Writer capture; capture.id = output.id;
          capture.route = [&](std::string fields,std::string rid) {
            auto event = app_json::parse('{'+fields+'}'); auto type = event.at("type").string();
            if (type == expected_type && event.at("recovery_id").string() == job.recovery_id) { proved = true; proof = fields; }
            if (type == "error") {
              retryable = event.object.count("retryable") && event.at("retryable").boolean();
              failure = fields;
            }
            if (type == "cancel_ack" && event.at("accepted").boolean()) aborted = true;
            if (type == "auth_prompt" || type == "auth_response_ack" || type == "auth_response_rejected" || type == "cancel_ack" || type == "pause_ack") output.emit(std::move(fields),rid);
          };
          int result = supervise(probe,input,capture,ids,pause_deadline);
          if (!result && proved && !aborted && !input.eof && !interrupted) { evidence.push_back(std::move(proof)); return true; }
          if (!retryable || now_ns() >= pause_deadline) return false;
          poll(nullptr,0,100);
        }
      };
      bool safe = true;
      if (job.connection) {
        Job probe; probe.op = "recovery_quiescence"; probe.connection = job.connection;
        auto request = actor;
        for (const auto& key : {"type","endpoint","actor_revision"}) request.object.erase(key);
        request.object["id"] = {Value::String,"remote-operation",{}, {}};
        request.object["op"] = {Value::String,"recovery_quiescence",{}, {}};
        request.object["endpoint"] = app_json::parse("{\"kind\":\"local\",\"path\":" + app_json::serialize(actor.at("actor_path")) + "}");
        request.object.erase("actor_path");
        request.object["expected_actor_revision"] = actor.at("actor_revision");
        request.object["cleanup"] = {Value::Bool,"true",{}, {}};
        probe.remote_request = app_json::serialize(request);
        safe = check(std::move(probe),"recovery_quiescent");
      }
      if (safe) {
        Job probe; probe.op = "_pause_checkpoint"; probe.path = job.path;
        probe.recovery_id = job.recovery_id; probe.recovery_binding = job.recovery_binding; probe.attempt_id = job.connection ? job.attempt_id : "";
        if (job.connection && job.push) {
          probe.connection = job.connection;
          probe.remote_request = "{\"id\":\"remote-operation\",\"op\":\"_pause_checkpoint\",\"endpoint\":{\"kind\":\"local\",\"path\":" + app_json::path(job.path) +
            "},\"recovery_id\":" + quote(job.recovery_id) + ",\"binding\":" + app_json::serialize(job.recovery_binding) + ",\"closed_attempt_id\":" + quote(job.attempt_id) + '}';
        }
        safe = check(std::move(probe),"pause_checkpoint");
      }
      // Drain already-arrived controls before publishing the terminal decision.
      input.read_ready();
      std::string pending;
      while (input.pop(pending)) {
        auto control = app_json::parse(pending); auto id = request_id(control);
        if (control.at("job_id").string() != output.id || !ids.insert(id).second) throw std::runtime_error("invalid pause control");
        auto op = control.at("op").string();
        if (op == "cancel") { aborted = true; output.emit("\"type\":\"cancel_ack\",\"job_id\":" + quote(output.id) + ",\"accepted\":true",id); }
        else if (op == "pause") output.emit("\"type\":\"pause_ack\",\"job_id\":" + quote(output.id) + ",\"accepted\":false,\"reason\":\"already_stopping\"",id);
        else if (op == "auth_response") output.emit("\"type\":\"auth_response_rejected\",\"reason\":\"stale_prompt\"");
        else throw std::runtime_error("unsupported pause control");
      }
      if (aborted || input.eof || interrupted) { output.result("cancellation",RERR_SIGNAL,false); return RERR_SIGNAL; }
      if (safe) {
        for (auto& fields : evidence) output.emit(std::move(fields));
        output.emit("\"type\":\"paused\",\"job_id\":" + quote(output.id) + ",\"recovery_id\":" + quote(job.recovery_id) +
          ",\"endpoint\":" + quote(job.connection && job.push ? "ssh" : "local") + ",\"root_path\":" + app_json::path(job.path) +
          ",\"receiver_quiescent\":true,\"peer_quiescent\":" + (job.connection ? "true" : "null") + ",\"verification_required\":true");
        output.emit("\"type\":\"result\",\"status\":\"paused\",\"code\":\"0\",\"cleanup\":\"finished\",\"durability\":\"filesystem-completion\",\"recovery_id\":" + quote(job.recovery_id));
        return 0;
      }
      if (!failure.empty()) output.emit(std::move(failure));
      output.error("interrupted","pause could not be confirmed; reconcile recovery state before resuming");
      output.result("failure",RERR_SIGNAL,false); return RERR_SIGNAL;
    }
    if (cancelled) { output.result("cancellation", RERR_SIGNAL, !job.connection && !forced && WIFEXITED(status)); return RERR_SIGNAL; }
    if (!WIFEXITED(status)) { output.error("interrupted", "job exited without an authoritative outcome"); output.result("failure", code, false); return code; }
    if (!code && !summary) { output.error("interrupted", "job exited before completion summary"); code = RERR_IPC; }
    bool remote_lost = job.connection && (code == RERR_STREAMIO || code == RERR_TIMEOUT || code == RERR_PROTOCOL || code == 255);
    output.result(code == 0 ? "success" : code == RERR_SIGNAL ? "cancellation" : code == RERR_PARTIAL || code == RERR_VANISHED ? "partial_failure" : "failure", code, !remote_lost && code != RERR_MESSAGEIO && (code != RERR_SIGNAL || !job.connection) && (!job.connection || job.op != "copy" || summary));
    return code;
  } catch (...) {
    if (!child_done) kill(-child, SIGTERM);
    u64 deadline = now_ns() + CANCEL_NS;
    while (!child_done && now_ns() < deadline) {
      reap();
      if (child_done) break;
      poll(nullptr, 0, 20);
    }
    if (!child_done) { kill(-child, SIGKILL); while (waitpid(child, &status, 0) < 0 && errno == EINTR) {} }
    if (controls[1] >= 0) close(controls[1]);
    close(fds[0]);
    try { invalidation.finish(output); } catch (...) {} // A closed reader cannot receive a hint.
    throw;
  }
}
}

int run_app() {
  signal(SIGPIPE, SIG_IGN);
  struct sigaction sa{}; sa.sa_handler = parent_signal;
  sigaction(SIGTERM, &sa, nullptr); sigaction(SIGINT, &sa, nullptr); sigaction(SIGHUP, &sa, nullptr);
  Writer output;
  try {
    nonblocking(STDIN_FILENO); nonblocking(STDOUT_FILENO);
    Reader input{STDIN_FILENO, {}, false}; std::string frame;
    if (!input.next(frame)) return 0;
    auto hello = app_json::parse(frame); output.id = request_id(hello);
    const auto& schema = hello.at("schema");
    if (hello.at("op").string() != "hello" || schema.kind != Value::String || schema.text != "1") {
      output.error("incompatible_schema", "first request must negotiate schema 1 using hello"); output.result("failure", RERR_PROTOCOL); return RERR_PROTOCOL;
    }
    output.emit(capabilities());
    std::set<std::string> ids{output.id};
    while (input.next(frame)) {
      if (ids.size() >= 32) throw std::runtime_error("session request limit exceeded");
      auto request = app_json::parse(frame); output.id = request_id(request);
      if (!ids.insert(output.id).second) throw std::runtime_error("duplicate request id");
      auto op = request.at("op").string();
      if (op == "probe") {
        if (request.object.count("endpoint") && request.at("endpoint").at("kind").string() == "ssh")
          return supervise(validate(request), input, output, ids);
        if (request.object.count("endpoint")) (void)local_path(request.at("endpoint"));
        output.emit(capabilities()); continue;
      }
      if (op == "shutdown") { output.result("success", 0); return 0; }
      Job job = validate(request);
      if (job.native) return supervise_native(job, input, output);
      return supervise(job, input, output, ids);
    }
    return 0;
  } catch (const std::exception& e) {
    auto request_error = dynamic_cast<const RequestError*>(&e);
    auto recovery_error = dynamic_cast<const app_partials::Error*>(&e);
    if (recovery_error) {
      try {
        output.emit("\"type\":\"error\",\"category\":" + quote(recovery_error->native ? native_category(recovery_error->native) : "conflict") +
          ",\"operation\":" + quote(recovery_error->operation) + ",\"endpoint\":\"local\",\"path\":" + app_json::path(recovery_error->path) +
          ",\"native_code\":" + (recovery_error->native ? quote(std::to_string(recovery_error->native)) : "null") + ",\"retryable\":false,\"message\":" + quote(e.what()));
        output.result("failure",RERR_FILESELECT,false);
      } catch (...) {}
      return RERR_FILESELECT;
    }
    int code = request_error ? RERR_UNSUPPORTED : RERR_SYNTAX;
    try { output.error(request_error ? request_error->category : "invalid_request", e.what()); output.result("failure", code, false); } catch (...) {}
    return code;
  }
}
