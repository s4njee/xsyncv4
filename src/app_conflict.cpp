#include "app_conflict.h"
#include "destination.h"
#include "progress.h"
#include "app_partials.h"
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <stdexcept>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>

namespace app_conflict {
namespace {
using app_json::Value;
using app_json::quote;
struct Answer { std::string action, scope = "item", name, token; };
struct Pending { std::string token; bool replace = false; bool ready = false; Answer answer; std::condition_variable condition; };
struct Policy { std::string kind, directory, action; };
std::mutex mutex;
std::map<std::string, std::shared_ptr<Pending>> pending;
std::vector<Policy> policies;
std::function<void(std::string)> emit;
std::string nonce;
u64 sequence = 0;
unsigned timeout_seconds = 120;
bool enabled = false;

std::string revision(const DestinationRevision& r) {
  if (!r.known) return "null";
  if (!r.exists) return "{\"exists\":false}";
  return "{\"exists\":true,\"device\":"+quote(std::to_string(r.device))+",\"inode\":"+quote(std::to_string(r.inode))+
    ",\"links\":"+quote(std::to_string(r.links))+",\"mode\":"+quote(std::to_string(r.mode))+",\"uid\":"+quote(std::to_string(r.uid))+
    ",\"gid\":"+quote(std::to_string(r.gid))+",\"flags\":"+quote(std::to_string(r.flags))+",\"size\":"+quote(std::to_string(r.size))+
    ",\"mtime_seconds\":"+quote(std::to_string(r.mtime))+",\"mtime_nanoseconds\":"+quote(std::to_string(r.mtime_ns))+
    ",\"ctime_seconds\":"+quote(std::to_string(r.ctime))+",\"ctime_nanoseconds\":"+quote(std::to_string(r.ctime_ns))+"}";
}
bool observe(const ItemPtr& item, Entry& entry, bool& exists, DestinationRevision& r) {
  struct stat st;
  if (destination_named_stat(item->destination.c_str(), &st) == 0) {
    exists = true; entry_from_stat(st, entry); r = DestinationRevision::from(st); return true;
  }
  int error = errno;
  if (error == ENOENT) { exists = false; entry = {}; r = DestinationRevision::absent(); return true; }
  if (g_fs_error_sink) g_fs_error_sink(error, item->destination, "stat_destination_revision");
  err_line(RERR_PARTIAL, "cannot inspect conflict destination: %s", errstr(error).c_str());
  return false;
}
bool component(std::string_view name) {
  return !name.empty() && name.size() <= 255 && name != "." && name != ".." && name.find_first_of("/\0", 0, 2) == name.npos;
}
bool selected_collision(DirWork& w, u32 index, std::string_view name) {
  auto group = w.conflict_names.find(w.conflict_name_key(name));
  if (group == w.conflict_names.end()) return false;
  for (u32 i : group->second) {
    if (i == index || w.src.e[i].type == T_NONE || (w.src.e[i].item_flags & IF_PRUNED) ||
        (!w.app_items.empty() && w.app_items[i]->skipped.load())) continue;
    return true;
  }
  return false;
}
bool can_replace(const ItemPtr& item, const Entry& destination, bool exists, bool collision) {
  if (collision) return false;
  if (!exists || destination.type != T_DIR || item->type == T_DIR) return true;
  int fd = destination_open_dir(item->destination.c_str());
  if (fd < 0) return false;
  DIR* directory = fdopendir(fd);
  if (!directory) { close(fd); return false; }
  bool empty = true;
  errno = 0;
  while (auto entry = readdir(directory)) {
    if (strcmp(entry->d_name, ".") && strcmp(entry->d_name, "..")) { empty = false; break; }
  }
  if (errno) empty = false;
  closedir(directory);
  return empty;
}
Answer ask(const ItemPtr& item, std::string_view kind, std::string_view reason,
           const DestinationRevision& current, const std::string& directory, bool replace, std::string_view existing_name) {
  std::unique_lock lock(mutex);
  if (reason.empty()) {
    std::string saved;
    if (!app_partials::conflict_policy(item,std::string(kind),directory,saved)) return {"error", "item", {}, {}};
    if (!saved.empty() && (saved != "replace" || replace)) return {saved, "item", {}, {}};
    for (auto i = policies.rbegin(); i != policies.rend(); ++i)
      if (i->kind == kind && (i->directory.empty() || i->directory == directory) && (i->action != "replace" || replace))
        return {i->action, "item", {}, {}};
  }
  auto request = std::make_shared<Pending>();
  request->replace = replace;
  request->token = "conflict-" + nonce + "-" + std::to_string(++sequence);
  pending.emplace(request->token, request);
  item_stage(item, "waiting_conflict");
  g_stats.conflict_active.fetch_add(1); progress_tick();
  emit("\"type\":\"conflict\",\"conflict_id\":"+quote(request->token)+",\"revision_token\":"+quote(request->token)+
       ",\"item_id\":"+quote(app_json::hex(item->relative))+",\"kind\":"+quote(kind)+",\"reason\":"+quote(reason.empty()?"existing_target":reason)+
       ",\"path\":"+app_json::path(item->destination)+",\"source_path\":"+app_json::path(item->source)+
       ",\"endpoint\":\"local\",\"side\":\"destination\",\"stage\":\"waiting_conflict\",\"expected_revision\":"+revision(item->expected_destination)+
       ",\"existing_name\":"+(current.exists ? app_json::path(existing_name) : "null")+
       ",\"destination_revision\":"+revision(current)+",\"allowed_actions\":["+(replace?std::string("\"replace\","):std::string())+
       "\"skip\",\"keep_both\",\"cancel\"],\"scopes\":[\"item\",\"directory\",\"job\"],\"timeout_seconds\":"+quote(std::to_string(timeout_seconds)));
  u64 deadline = now_ns() + (u64)timeout_seconds * 1000000000ULL;
  while (!request->ready && !g_stop.load() && now_ns() < deadline) request->condition.wait_for(lock, std::chrono::milliseconds(50));
  Answer answer = request->ready ? request->answer : Answer{g_stop.load() ? "cancel" : "timeout", "item", {}, {}};
  pending.erase(request->token);
  g_stats.conflict_active.fetch_sub(1); progress_tick();
  if (answer.action == "replace" && !replace) answer.action = "invalid";
  answer.token = request->token;
  return answer;
}
void applied(const ItemPtr& item, const Answer& answer, std::string_view kind, const std::string& directory) {
  std::lock_guard lock(mutex);
  if (answer.action != "cancel" && answer.scope != "item" && policies.size() < 128)
    policies.push_back({std::string(kind), answer.scope == "directory" ? directory : std::string(), answer.action});
  if (!answer.token.empty()) emit("\"type\":\"conflict_resolved\",\"conflict_id\":"+quote(answer.token)+",\"item_id\":"+quote(app_json::hex(item->relative))+
       ",\"decision\":"+quote(answer.action)+",\"scope\":"+quote(answer.scope));
}
void rejected(std::string_view token, std::string_view reason) {
  emit("\"type\":\"conflict_response_rejected\",\"conflict_id\":"+quote(token)+",\"reason\":"+quote(reason));
}
}
void configure(bool active, unsigned timeout, std::function<void(std::string)> output) {
  enabled = active; emit = std::move(output); timeout_seconds = timeout;
  if (!active) return;
  char bytes[16]; int fd = open("/dev/urandom", O_RDONLY | O_CLOEXEC);
  if (fd < 0) throw std::runtime_error("cannot create conflict tokens");
  size_t count = 0;
  while (count < sizeof bytes) {
    ssize_t n = read(fd, bytes+count, sizeof bytes-count);
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) { close(fd); throw std::runtime_error("cannot create conflict tokens"); }
    count += (size_t)n;
  }
  close(fd); nonce = app_json::hex({bytes,sizeof bytes});
  g_app_conflict_plan = plan;
  g_app_conflict_recheck = recheck;
}
void response(std::string_view payload) {
  std::lock_guard lock(mutex);
  std::string token;
  try {
    auto v = app_json::parse(payload); token = v.at("conflict_id").string();
    auto found = pending.find(token);
    if (!enabled || found == pending.end()) { rejected(token, "stale_conflict"); return; }
    auto request = found->second;
    if (v.at("revision_token").string() != request->token) { rejected(token, "revision_mismatch"); return; }
    if (request->ready) { rejected(token, "duplicate_response"); return; }
    Answer answer; answer.action = v.at("decision").string();
    if (answer.action != "replace" && answer.action != "skip" && answer.action != "keep_both" && answer.action != "cancel") { rejected(token, "invalid_decision"); return; }
    if (answer.action == "replace" && !request->replace) { rejected(token, "decision_not_available"); return; }
    if (v.object.count("scope")) answer.scope = v.at("scope").string();
    if (answer.scope != "item" && answer.scope != "directory" && answer.scope != "job") { rejected(token, "invalid_scope"); return; }
    if (v.object.count("destination_name")) {
      answer.name = app_json::unhex(v.at("destination_name").at("bytes_hex").string());
      if (answer.action != "keep_both" || answer.scope != "item" || !component(answer.name)) { rejected(token, "invalid_name"); return; }
    }
    if (answer.scope != "item" && policies.size() >= 128) { rejected(token, "policy_limit"); return; }
    request->answer = std::move(answer); request->ready = true; request->condition.notify_all();
  } catch (const std::exception&) { rejected(token, "invalid_response"); }
}
bool plan(DirWork& w, u32 index, Entry& destination, bool& exists, std::string_view initial_reason) {
  std::lock_guard directory_lock(w.conflict_mutex);
  if (!w.conflict_name_key) {
    w.conflict_name_key = destination_name_keyer(w.dst_path);
    for (u32 i = 0; i < w.src.e.size(); ++i) w.conflict_names[w.conflict_name_key(w.dst_name(i))].push_back(i);
  }
  auto item = w.app_items[index];
  ItemScope scope(item);
  std::string reason(initial_reason);
  auto map_destination = [&](const std::string& target) {
    if (target == item->destination) return;
    auto candidate = target.substr(target.rfind('/')+1);
    if (w.destination_names.empty()) w.destination_names.resize(w.src.e.size());
    auto& previous = w.conflict_names[w.conflict_name_key(w.dst_name(index))];
    previous.erase(std::remove(previous.begin(), previous.end(), index), previous.end());
    w.conflict_names[w.conflict_name_key(candidate)].push_back(index);
    w.destination_names[index] = candidate;
    std::lock_guard lock(item->mutex);
    item->destination = target; item->renamed = true;
    g_item_sink({*item,"item_mapping",{}, {}});
  };
  auto replayed = [&](const app_partials::Choice& saved) {
    emit("\"type\":\"conflict_replayed\",\"recovery_id\":"+quote(saved.recovery_id)+
      ",\"decision\":"+quote(saved.decision)+",\"item_id\":"+quote(app_json::hex(item->relative))+",\"endpoint\":\"local\",\"source_path\":"+app_json::path(item->source)+
      ",\"original_destination_path\":"+app_json::path(item->recovery_original)+",\"destination_path\":"+app_json::path(item->destination));
  };
  if (item->recovery_original.empty()) {
    item->recovery_original = item->destination;
    app_partials::Choice saved;
    int restored = app_partials::restore_choice(item,saved);
    if (restored < 0) return false;
    if (restored) {
      map_destination(saved.destination);
      DestinationRevision current;
      if (!observe(item,destination,exists,current)) return false;
      item->expected_destination = current;
      if (saved.decision == "skip") {
        w.src.e[index].flags &= (u8)~EF_DESCEND; replayed(saved);
        item_finish(item,"skipped","recovery_skip"); return false;
      }
      bool collision = selected_collision(w,index,w.dst_name(index));
      if (can_replace(item,destination,exists,collision)) { replayed(saved); return true; }
      reason = collision ? "recovery_name_collision" : "recovery_type_changed";
    }
  }
  for (;;) {
    if (g_stop.load() || (g_app_destination_check && !g_app_destination_check())) return false;
    DestinationRevision current;
    if (!observe(item, destination, exists, current)) return false;
    if (g_app_preview_destination_check && !g_app_preview_destination_check(item,current)) { w.src.e[index].flags &= (u8)~EF_DESCEND; return false; }
    if (g_app_preview_destination_check && !g_app_preview_destination_check(item,current)) { w.src.e[index].flags &= (u8)~EF_DESCEND; return false; }
    bool collision = selected_collision(w, index, w.dst_name(index));
    if (!exists && !collision && reason.empty()) {
      item->expected_destination = current;
      return app_partials::remember_choice(item,"copy","item","none",w.dst_path);
    }
    auto key = w.conflict_name_key(w.dst_name(index));
    if (exists && (reason == "destination_changed" || !w.conflict_existing_names.count(key))) {
      DirList names;
      int error = destination_list_dir(w.dst_path.c_str(), names, 0);
      if (error || names.incomplete) {
        if (g_fs_error_sink) g_fs_error_sink(error, w.dst_path, "scan_destination");
        err_line(RERR_PARTIAL, "cannot inspect conflict destination names"); return false;
      }
      w.conflict_existing_names.clear();
      for (const auto& entry : names.e) {
        auto name = names.name_sv(entry);
        w.conflict_existing_names.emplace(w.conflict_name_key(name), name);
      }
    }
    auto actual = w.conflict_existing_names.find(key);
    std::string_view existing_name = actual == w.conflict_existing_names.end() ? std::string_view(w.dst_name(index)) : std::string_view(actual->second);
    bool alias = exists && existing_name != w.dst_name(index);
    const char* kind = collision || alias ? "name_collision" : exists && item->type == T_DIR && destination.type == T_DIR ? "directory_merge" :
      exists && (item->type == T_LNK || destination.type == T_LNK) ? "symlink" : exists && item->type != destination.type ? "type_mismatch" : "file_file";
    Answer answer = ask(item, kind, reason, current, w.dst_path, can_replace(item,destination,exists,collision), existing_name);
    if (answer.action == "error") return false;
    if (answer.action == "invalid") { reason = "decision_not_available"; continue; }
    if (answer.action == "cancel") { applied(item, answer, kind, w.dst_path); g_stop.store(1); return false; }
    if (answer.action == "timeout") {
      item_finish(item, "failure", "conflict_timeout");
      emit("\"type\":\"error\",\"category\":\"conflict_timeout\",\"operation\":\"conflict_response\",\"endpoint\":\"local\",\"side\":\"destination\",\"stage\":\"waiting_conflict\",\"path\":"+app_json::path(item->destination)+",\"item_id\":"+quote(app_json::hex(item->relative))+",\"native_code\":null,\"retryable\":false,\"message\":\"Conflict decision deadline expired\"");
      err_line(RERR_PARTIAL, "conflict decision deadline expired"); return false;
    }
    Entry fresh; bool fresh_exists; DestinationRevision revalidated;
    if (!observe(item, fresh, fresh_exists, revalidated)) return false;
    if (g_app_preview_destination_check && !g_app_preview_destination_check(item,revalidated)) {
      { std::lock_guard lock(mutex); rejected(answer.token,"stale_preview"); }
      w.src.e[index].flags &= (u8)~EF_DESCEND; return false;
    }
    if (current != revalidated) {
      { std::lock_guard lock(mutex); rejected(answer.token, "destination_changed"); }
      reason = "destination_changed"; continue;
    }
    if (answer.action == "skip") {
      item->expected_destination = revalidated;
      if (!app_partials::remember_choice(item,answer.action,answer.scope,kind,w.dst_path)) return false;
      w.src.e[index].flags &= (u8)~EF_DESCEND;
      
      applied(item, answer, kind, w.dst_path);
      item_finish(item, "skipped", "user_skip"); return false;
    }
    if (answer.action == "keep_both") {
      std::string original = w.dst_name(index), candidate;
      bool chosen = false;
      for (unsigned attempt = 1; attempt <= 10000; ++attempt) {
        if (!answer.name.empty()) candidate = answer.name;
        else {
          auto suffix = " (copy " + std::to_string(attempt) + ')';
          size_t keep = std::min(original.size(), 255-suffix.size());
          while (keep && keep < original.size() && ((unsigned char)original[keep] & 0xc0) == 0x80) --keep;
          candidate = original.substr(0, keep)+suffix;
        }
        if (selected_collision(w,index,candidate)) { if (!answer.name.empty()) break; else continue; }
        auto target = path_join(w.dst_path,candidate); struct stat st;
        if (destination_named_stat(target.c_str(),&st) == 0) { if (!answer.name.empty()) break; else continue; }
        if (errno != ENOENT) { if (g_fs_error_sink) g_fs_error_sink(errno,target,"stat_destination_revision"); err_line(RERR_PARTIAL,"cannot inspect keep-both name"); return false; }
        map_destination(target);
        item->expected_destination = DestinationRevision::absent();
        destination = {}; exists = false; chosen = true; break;
      }
      if (!chosen) { reason = "name_unavailable"; continue; }
    } else { destination = fresh; exists = fresh_exists; item->expected_destination = revalidated; }
    if (!app_partials::remember_choice(item,answer.action,answer.scope,kind,w.dst_path)) return false;
    applied(item, answer, kind, w.dst_path);
    item_stage(item,"planning"); return true;
  }
}
bool recheck(const ItemPtr& item, const DestinationRevision&) {
  if (!item || !item->plan_owner) return false;
  Entry destination; bool exists;
  return plan(*item->plan_owner,item->plan_index,destination,exists,"destination_changed");
}
ControlReader::ControlReader(int fd) {
  if (fd < 0) return;
  thread = std::thread([this,fd] {
    std::string input;
    while (!done.load() && !g_stop.load()) {
      pollfd p{fd,POLLIN,0}; if (poll(&p,1,50) <= 0) continue;
      char bytes[4096]; ssize_t n = read(fd,bytes,sizeof bytes);
      if (n <= 0) { if (n < 0 && (errno == EINTR || errno == EAGAIN)) continue; g_stop.store(1); break; }
      input.append(bytes,(size_t)n);
      if (input.size() > 1024*1024) { g_stop.store(1); break; }
      for (;;) { auto end=input.find('\n'); if (end==input.npos) break; auto frame=input.substr(0,end); input.erase(0,end+1); response(frame); }
    }
  });
}
ControlReader::~ControlReader() { done.store(true); if (thread.joinable()) thread.join(); }
}
