#include "item.h"
#include "fs.h"
#include "destination.h"
#include "app_partials.h"

void (*g_item_sink)(const TransferEvent&) = nullptr;
bool (*g_app_destination_check)() = nullptr;
bool (*g_app_conflict_plan)(DirWork&, u32, Entry&, bool&, std::string_view) = nullptr;
bool (*g_app_conflict_recheck)(const ItemPtr&, const DestinationRevision&) = nullptr;
std::function<bool(const ItemPtr&,const DestinationRevision&)> g_app_preview_source_check, g_app_preview_destination_check;
bool g_app_preview_remote_source=false;
std::map<std::string, std::string> g_app_selection_names;
std::string app_selection_name(std::string_view source, std::string_view fallback) {
  auto found = g_app_selection_names.find(std::string(source));
  return found == g_app_selection_names.end() ? std::string(fallback) : found->second;
}
namespace {
thread_local ItemPtr active_item;
std::atomic<u64> outstanding{0};
}
TransferItem::TransferItem(std::string relative, std::string source, std::string destination,
                           const Entry& entry, bool owned)
  : relative(std::move(relative)), source(std::move(source)), destination(std::move(destination)),
    type(entry.type), size(entry.size), owned(owned), source_mode(entry.mode) {}

ItemPtr transfer_item(std::string relative, std::string source, std::string destination,
                      const Entry& entry, bool owned) {
  if (!g_item_sink) return {};
  while (source.size() > 1 && source.back() == '/') source.pop_back();
  if (source.ends_with("/.")) source.resize(source.size()-2);
  if (source.empty()) source = "/";
  auto item = std::make_shared<TransferItem>(std::move(relative), std::move(source),
                                            std::move(destination), entry, owned);
  if (owned) {
    outstanding.fetch_add(1);
    g_item_sink({*item, "item_discovered", {}, {}});
  }
  return item;
}
void item_stage(const ItemPtr& item, std::string_view stage) {
  if (!item || !g_item_sink || item->terminal.load()) return;
  std::lock_guard<std::mutex> lock(item->mutex);
  if (item->stage == stage) return;
  item->stage = stage;
  g_item_sink({*item, "item_stage", stage, {}, item->staged, item->reused, item->attempt});
}
void item_progress(const ItemPtr& item, u64 bytes, u64 reused) {
  if (!item || !g_item_sink || item->terminal.load()) return;
  std::lock_guard<std::mutex> lock(item->mutex);
  item->staged += bytes; item->reused += reused;
  u64 now = now_ns();
  if (now - item->last_progress < 100000000) return;
  item->last_progress = now;
  g_item_sink({*item, "item_progress", {}, {}, item->staged, item->reused, item->attempt});
}
void item_retry(const ItemPtr& item, u32 attempt, std::string_view reason) {
  if (!item || !g_item_sink || item->terminal.load()) return;
  std::lock_guard<std::mutex> lock(item->mutex);
  item->attempt = attempt; item->staged = item->reused = 0;
  item->last_progress = 0;
  g_item_sink({*item, "item_retry", {}, reason, 0, 0, attempt});
}
void item_finish(const ItemPtr& item, std::string_view status, std::string_view reason) {
  if (!item || !item->owned || !g_item_sink || item->terminal.exchange(true)) return;
  app_partials::finish_entry(item);
  std::lock_guard<std::mutex> lock(item->mutex);
  if (g_stop.load()) status = "cancellation";
  else if (item->failed.load()) {
    if (status == "success") reason = {};
    status = "failure";
  }
  if (status == "failure" && reason.empty()) reason = item->preview_stale.load() ? "stale_preview" : item->temporary_changed.load() ? "temporary_output_changed" : item->destination_changed.load() ? "destination_changed" : item->metadata_failed.load() ? "metadata_error" : item->source_failed.load() ? "source_error" : "filesystem_error";
  item->skipped.store(status == "skipped");
  g_item_sink({*item, "item_result", status, reason, item->staged, item->reused, item->attempt});
  outstanding.fetch_sub(1);
}
u64 pending_items() { return outstanding.load(); }
ItemPtr current_item() { return active_item; }
void item_error(bool metadata, bool source) {
  if (!active_item) return;
  active_item->failed.store(true);
  if (metadata) active_item->metadata_failed.store(true);
  if (source) active_item->source_failed.store(true);
}
ItemScope::ItemScope(const ItemPtr& item) : previous(std::move(active_item)) { active_item = item; }
ItemScope::~ItemScope() { active_item = std::move(previous); }

namespace {
bool observe_destination(const ItemPtr& item, DestinationRevision& revision) {
  struct stat st;
  if (destination_named_stat(item->destination.c_str(), &st) == 0) revision = DestinationRevision::from(st);
  else if (errno == ENOENT) revision = DestinationRevision::absent();
  else {
    int code = errno;
    if (g_fs_error_sink) g_fs_error_sink(code, item->destination, "stat_destination_revision");
    err_line(RERR_PARTIAL, "cannot revalidate destination \"%s\": %s", item->destination.c_str(), errstr(code).c_str());
    return false;
  }
  return true;
}
}
bool item_expect_destination(const ItemPtr& item) {
  if (!item) return true;
  ItemScope scope(item);
  return observe_destination(item, item->expected_destination);
}
bool item_observe_destination(const ItemPtr& item, DestinationRevision& revision) {
  ItemScope scope(item);
  return observe_destination(item, revision);
}
bool item_preview_source_valid(const ItemPtr& item,const DestinationRevision* observed) {
  if (!item || !g_app_preview_source_check) return true;
  if (g_app_preview_remote_source) return g_app_preview_source_check(item,{});
  if (observed) return g_app_preview_source_check(item,*observed);
  struct stat st;
  DestinationRevision revision;
  if (lstat(item->source.c_str(),&st)==0) revision=DestinationRevision::from(st);
  else if (errno==ENOENT) revision=DestinationRevision::absent();
  return g_app_preview_source_check(item,revision);
}
void item_destination_changed(const ItemPtr& item, int code) {
  if (!item) return;
  ItemScope scope(item);
  item->destination_changed.store(true); item->failed.store(true);
  item->expected_conflict = item->expected_destination;
  (void)observe_destination(item, item->observed_conflict);
  if (g_fs_error_sink) g_fs_error_sink(code, item->destination, "destination_changed");
  err_line(RERR_PARTIAL, "destination changed during transfer: \"%s\"", item->destination.c_str());
}
bool item_destination_valid(const ItemPtr& item, bool identity_only, bool absent_publication) {
  if (!item) return true;
  ItemScope scope(item);
  if (g_app_destination_check && !g_app_destination_check()) {
    item->destination_changed.store(true); item->failed.store(true);
    return false;
  }
  std::vector<ItemPtr> ancestors;
  for (auto current = item; current; current = current->parent) ancestors.push_back(current);
  for (auto i = ancestors.rbegin(); i != ancestors.rend(); ++i) {
    const auto& current = *i;
    if (!current->expected_destination.known) return false;
    // The kernel's exclusive publish checks an absent leaf atomically. Its
    // parents still need validation after closing the staged file.
    if (absent_publication && current == item && !current->expected_destination.exists) continue;
    DestinationRevision observed;
    if (!observe_destination(current, observed)) return false;
    if (g_app_preview_destination_check && !g_app_preview_destination_check(current,observed)) {
      if (current->preview_stale.load()) { item->preview_stale.store(true); item->failed.store(true); item->destination_changed.store(true); }
      return false;
    }
    bool identity = identity_only || current != item;
    if (identity ? current->expected_destination.same_object(observed)
                 : current->expected_destination == observed) continue;
    if (!identity && current == item && item->type == T_REG && g_app_conflict_recheck)
      return g_app_conflict_recheck(item, observed);
    item->destination_changed.store(true); item->failed.store(true);
    item->expected_conflict = current->expected_destination; item->observed_conflict = observed;
    if (g_fs_error_sink) g_fs_error_sink(0, current->destination,
      current == item ? "destination_changed" : "destination_ancestor_changed");
    err_line(RERR_PARTIAL, "destination changed during transfer: \"%s\"", current->destination.c_str());
    return false;
  }
  return true;
}
