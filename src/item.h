// Optional, structured transfer observations. Ordinary CLI jobs leave the sink unset.
#pragma once
#include "common.h"
#include "revision.h"
#include <functional>
#include <map>
#include <memory>
#include <mutex>

struct DirWork;
struct TransferItem {
  std::string relative, source, destination;
  std::string recovery_original;
  u8 type;
  std::atomic<i64> size;
  bool owned;
  std::atomic<bool> failed{false}, metadata_failed{false}, source_failed{false}, applied{false}, published{false}, terminal{false}, skipped{false};
  std::atomic<bool> destination_changed{false}, temporary_changed{false};
  std::atomic<bool> preview_stale{false};
  bool preview_destination_bound = false;
  DestinationRevision expected_destination, expected_conflict, observed_conflict;
  std::shared_ptr<TransferItem> parent;
  std::mutex mutex;
  std::string stage;
  u64 staged = 0, reused = 0, last_progress = 0;
  u32 attempt = 0;
  DirWork* plan_owner = nullptr;
  u32 plan_index = 0, source_mode = 0;
  bool renamed = false;
  TransferItem(std::string relative, std::string source, std::string destination,
               const Entry& entry, bool owned);
};
using ItemPtr = std::shared_ptr<TransferItem>;
struct TransferEvent {
  const TransferItem& item;
  std::string_view kind, value, reason;
  u64 bytes = 0, reused = 0;
  u32 attempt = 0;
};
extern void (*g_item_sink)(const TransferEvent&);
extern bool (*g_app_destination_check)();
extern bool (*g_app_conflict_plan)(DirWork&, u32, Entry&, bool&, std::string_view);
extern bool (*g_app_conflict_recheck)(const ItemPtr&, const DestinationRevision&);
extern std::function<bool(const ItemPtr&,const DestinationRevision&)> g_app_preview_source_check, g_app_preview_destination_check;
extern bool g_app_preview_remote_source;
bool item_preview_source_valid(const ItemPtr& item, const DestinationRevision* observed = nullptr);
// Immutable explicit root-selection names; ordinary CLI leaves this empty.
extern std::map<std::string, std::string> g_app_selection_names;
std::string app_selection_name(std::string_view source, std::string_view fallback);
bool item_expect_destination(const ItemPtr& item);
bool item_observe_destination(const ItemPtr& item, DestinationRevision& revision);
bool item_destination_valid(const ItemPtr& item, bool identity_only = false, bool absent_publication = false);
void item_destination_changed(const ItemPtr& item, int code = 0);
ItemPtr transfer_item(std::string relative, std::string source, std::string destination,
                      const Entry& entry, bool owned = true);
void item_stage(const ItemPtr& item, std::string_view stage);
void item_progress(const ItemPtr& item, u64 bytes, u64 reused = 0);
void item_retry(const ItemPtr& item, u32 attempt, std::string_view reason);
void item_finish(const ItemPtr& item, std::string_view status = "success", std::string_view reason = {});
u64 pending_items();
ItemPtr current_item();
void item_error(bool metadata = false, bool source = false);

// Error attribution is thread-local, while item state survives worker changes.
struct ItemScope {
  ItemPtr previous;
  explicit ItemScope(const ItemPtr& item);
  ~ItemScope();
};
struct ItemFinalizer {
  ItemPtr item;
  bool deferred = false;
  std::string_view status = "success", reason;
  explicit ItemFinalizer(ItemPtr item) : item(std::move(item)) {}
  ~ItemFinalizer() { if (!deferred) item_finish(item, status, reason); }
};
