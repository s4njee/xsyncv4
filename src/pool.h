// Worker pool with two task queues (0 = scan/generate, 1 = transfer).
#pragma once
#include <atomic>
#include <condition_variable>
#include <deque>
#include <functional>
#include <mutex>
#include <thread>

#include "fs.h"

struct Task {
  int kind = 0;
  void* ptr = nullptr;
  u32 a = 0, b = 0;
  std::string s;
};

class Pool {
 public:
  using Fn = std::function<void(Task&, Worker&)>;

  int scan_workers = 1 << 30;      // workers [0, scan_workers) prefer queue 0, the rest queue 1
  size_t q1_soft_limit = SIZE_MAX; // above this backlog everyone prefers queue 1
  size_t max_bytes = SIZE_MAX;     // push_bounded() blocks above this many queued payload bytes
  bool lifo0 = false;
  std::function<bool()> idle_check;        // locked; nothing queued or running: true = finished
  std::function<bool(Worker&)> on_idle;    // unlocked, before a worker sleeps; true = did work
  std::function<void(Worker&)> on_exit;

  void push(int q, Task&& t) {
    std::lock_guard<std::mutex> lk(mu_);
    bytes_ += t.s.size();
    q_[q].push_back(std::move(t));
    cv_.notify_one();
  }
  void push_bounded(int q, Task&& t) {
    std::unique_lock<std::mutex> lk(mu_);
    cv_space_.wait(lk, [&] { return bytes_ < max_bytes || done_; });
    bytes_ += t.s.size();
    q_[q].push_back(std::move(t));
    cv_.notify_one();
  }
  // Run `f` under the pool lock and wake the workers (used to change state idle_check reads).
  template <class F>
  void update(F&& f) {
    std::lock_guard<std::mutex> lk(mu_);
    f();
    cv_.notify_all();
  }
  void start(int n, Fn fn) {
    fn_ = std::move(fn);
    worker_count_ = n;
    for (int i = 0; i < n; i++) threads_.emplace_back([this, i] { run(i); });
  }
  // Called by a pool worker, with callbacks that do not themselves call
  // parallel(). Waiting producers help only range tickets, never recursively
  // start another file. Thus all workers may produce ranges without deadlock.
  void parallel(size_t count, Worker& worker, std::function<void(size_t, Worker&)> fn) {
    if (!count) return;
    ParallelWork work(count, std::move(fn));
    int tickets = (int)std::min<size_t>(worker_count_, count);
    work.remaining = tickets;
    {
      std::lock_guard<std::mutex> lock(mu_);
      for (int i = 1; i < tickets; ++i) ranges_.push_back(&work);
      cv_.notify_all();
    }
    run_parallel(work, worker);
    while (work.remaining.load(std::memory_order_acquire)) {
      ParallelWork* other = nullptr;
      {
        std::unique_lock<std::mutex> lock(mu_);
        if (ranges_.empty()) {
          cv_.wait_for(lock, std::chrono::milliseconds(1), [&] {
            return !ranges_.empty() || !work.remaining.load(std::memory_order_acquire);
          });
        }
        if (!ranges_.empty()) { other = ranges_.front(); ranges_.pop_front(); }
      }
      if (other) run_parallel(*other, worker);
    }
  }
  // Wait up to `ms` for completion.
  bool wait_done(int ms) {
    std::unique_lock<std::mutex> lk(mu_);
    return cv_done_.wait_for(lk, std::chrono::milliseconds(ms), [&] { return done_; });
  }
  void abort() {
    std::lock_guard<std::mutex> lk(mu_);
    done_ = true;
    cv_.notify_all();
    cv_done_.notify_all();
    cv_space_.notify_all();
  }
  void join() {
    for (auto& t : threads_) t.join();
    threads_.clear();
  }

 private:
  struct ParallelWork {
    size_t count;
    std::function<void(size_t, Worker&)> fn;
    std::atomic<size_t> next{0};
    std::atomic<int> remaining{0};
    ParallelWork(size_t count, std::function<void(size_t, Worker&)> fn) : count(count), fn(std::move(fn)) {}
  };
  void run_parallel(ParallelWork& work, Worker& worker) {
    for (;;) {
      size_t index = work.next.fetch_add(1, std::memory_order_relaxed);
      if (index >= work.count) break;
      work.fn(index, worker);
    }
    work.remaining.fetch_sub(1, std::memory_order_release);
    cv_.notify_all();
  }
  void run(int id) {
    Worker w;
    w.id = id;
    w.buf.resize(1 << 20);
    std::unique_lock<std::mutex> lk(mu_);
    for (;;) {
      if (done_) break;
      int pref = (id < scan_workers && q_[1].size() < q1_soft_limit) ? 0 : 1;
      int k = !q_[pref].empty() ? pref : !q_[1 - pref].empty() ? 1 - pref : -1;
      if (k < 0 && ranges_.empty()) {
        lk.unlock();
        bool did = on_idle && on_idle(w);
        w.flush_log();
        lk.lock();
        if (did || !q_[0].empty() || !q_[1].empty() || !ranges_.empty()) continue;
        if (active_ == 0 && (!idle_check || idle_check())) {
          done_ = true;
          cv_.notify_all();
          cv_done_.notify_all();
          cv_space_.notify_all();
          break;
        }
        cv_.wait(lk);
        continue;
      }
      Task t;
      ParallelWork* range = nullptr;
      if (!ranges_.empty()) {
        range = ranges_.front();
        ranges_.pop_front();
      } else if (k == 0 && lifo0) {
        t = std::move(q_[0].back());
        q_[0].pop_back();
      } else {
        t = std::move(q_[k].front());
        q_[k].pop_front();
      }
      bool was_full = bytes_ >= max_bytes;
      bytes_ -= t.s.size();
      if (was_full && bytes_ < max_bytes) cv_space_.notify_all();
      active_++;
      lk.unlock();
      if (range) run_parallel(*range, w);
      else fn_(t, w);
      t = Task();
      lk.lock();
      active_--;
    }
    lk.unlock();
    if (on_exit) on_exit(w);
    w.flush_log();
  }

  std::mutex mu_;
  std::condition_variable cv_, cv_done_, cv_space_;
  std::deque<Task> q_[2];
  std::deque<ParallelWork*> ranges_;
  int worker_count_ = 1;
  size_t bytes_ = 0;
  int active_ = 0;
  bool done_ = false;
  Fn fn_;
  std::vector<std::thread> threads_;
};
