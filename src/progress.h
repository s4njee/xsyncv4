// Live progress display: one row per active file plus a whole-transfer bar.
#pragma once
#include "common.h"

constexpr int MAX_WORKERS = 64;

// What a worker is currently transferring. Written by the worker, sampled by the UI thread
// (seqlock: odd seq = being written).
struct alignas(128) Slot {
  std::atomic<u32> seq{0};
  std::atomic<bool> active{false};
  std::atomic<i64> done{0};
  i64 size = 0;
  u16 len = 0;
  char name[200];
};
extern Slot g_slots[MAX_WORKERS];
extern bool g_progress_on;

inline void slot_begin(int wid, std::string_view dir, std::string_view name, i64 size) {
  if (!g_progress_on) return;
  Slot& s = g_slots[wid];
  u32 q = s.seq.load(std::memory_order_relaxed);
  s.seq.store(q + 1, std::memory_order_release);
  size_t n = 0, cap = sizeof s.name;
  if (!dir.empty()) {
    if (dir.size() + 1 + name.size() > cap) dir.remove_prefix(std::min(dir.size(), dir.size() + 1 + name.size() - cap));
    memcpy(s.name, dir.data(), dir.size());
    n = dir.size();
    if (n < cap) s.name[n++] = '/';
  }
  size_t m = std::min(name.size(), cap - n);
  memcpy(s.name + n, name.data(), m);
  s.len = (u16)(n + m);
  s.size = size;
  s.done.store(0, std::memory_order_relaxed);
  s.active.store(true, std::memory_order_relaxed);
  s.seq.store(q + 2, std::memory_order_release);
}
inline void slot_add(int wid, i64 n) {
  if (g_progress_on) g_slots[wid].done.fetch_add(n, std::memory_order_relaxed);
}
inline void slot_end(int wid) {
  if (g_progress_on) g_slots[wid].active.store(false, std::memory_order_relaxed);
}

void progress_start(int nworkers);
void progress_tick();
void progress_stop(bool ok);
// Print text (complete lines) above the live region.
void ui_write(bool is_err, std::string_view text);
