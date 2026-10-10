// Live progress display: one row per active file plus a whole-transfer bar.
#pragma once
#include "common.h"
#include <mutex>

constexpr int MAX_WORKERS = 64;

// A file in flight. Metadata is protected by mutex; byte updates are atomic.
struct alignas(128) Slot {
  std::mutex mutex;
  std::atomic<bool> active{false};
  std::atomic<i64> done{0};
  i64 size = 0;
  u64 started = 0;
  bool cloning = false;
  u16 len = 0;
  char name[200];
};
extern Slot g_slots[MAX_WORKERS];
extern std::atomic<bool> g_progress_on;

void slot_begin(int wid, std::string_view dir, std::string_view name, i64 size, bool cloning = false);
// Receivers claim a record for the file's full lifetime, across worker/chunk changes.
int slot_claim(std::string_view dir, std::string_view name, i64 size);
inline void slot_add(int wid, i64 n) {
  if (g_progress_on && wid >= 0) g_slots[wid].done.fetch_add(n, std::memory_order_relaxed);
}
inline void slot_set(int wid, i64 n) {
  if (g_progress_on && wid >= 0) g_slots[wid].done.store(n, std::memory_order_relaxed);
}
void slot_end(int wid, bool completed = false);

void progress_start(int nworkers);
void progress_tick();
void progress_stop(bool ok);
// Print text (complete lines) above the live region.
void ui_write(bool is_err, std::string_view text);

// Optional remote profiling; counters measure accumulated service time.
struct StageTimer {
  std::atomic<u64>& counter;
  u64 started;
  explicit StageTimer(std::atomic<u64>& target) : counter(target), started(g_opt.peer_features & PF_STAGE_METRICS ? now_ns() : 0) {}
  ~StageTimer() { if (started) counter.fetch_add(now_ns() - started, std::memory_order_relaxed); }
};
const char* limiting_stage();
