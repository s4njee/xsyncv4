// Scanner admission must park without finishing the pool, and reads must wake it.
#include "pool.h"
#include <cassert>
#include <chrono>

void Worker::flush_log() {}

int main() {
  {
    Pool pool;
    std::atomic<bool> allowed{false};
    std::atomic<int> scans{0}, reads{0}, idle_calls{0};
    pool.scan_ready = [&] { return allowed.load(); };
    pool.on_idle = [&](Worker&) { ++idle_calls; return false; };
    Task scan; scan.kind = 1;
    pool.push(0, std::move(scan));
    pool.start(1, [&](Task& task, Worker&) {
      if (task.kind == 2) {
        ++reads;
        pool.update([&] { allowed.store(true); });
      } else {
        assert(reads.load() == 1);
        ++scans;
      }
    });
    assert(!pool.wait_done(50));
    assert(scans.load() == 0);
    // Generous enough for spurious wakeups; catches a parked-queue busy loop.
    assert(idle_calls.load() < 1000);
    Task read; read.kind = 2;
    pool.push(1, std::move(read));
    assert(pool.wait_done(2000));
    pool.join();
    assert(scans.load() == 1 && reads.load() == 1);
  }
  {
    Pool pool;
    bool allowed = false;
    int scans = 0;
    pool.scan_ready = [&] { return allowed; };
    // An idle writer can flush buffered DATA before waiting for a peer reply.
    pool.on_idle = [&](Worker&) {
      bool flushed = false;
      pool.update([&] {
        if (!allowed) allowed = flushed = true;
      });
      return flushed;
    };
    Task scan;
    pool.push(0, std::move(scan));
    pool.start(1, [&](Task&, Worker&) { ++scans; });
    assert(pool.wait_done(2000));
    pool.join();
    assert(scans == 1);
  }
  {
    Pool pool;
    pool.max_bytes = 64;
    std::atomic<bool> second_queued{false}, producer_started{false};
    std::atomic<int> consumed{0};
    pool.idle_check = [&] { return second_queued.load(); };
    Task first;
    first.s = "x"; first.charge = 64;
    pool.push_bounded(1, std::move(first));
    std::thread producer([&] {
      Task second;
      second.s = "y"; second.charge = 64;
      producer_started = true;
      pool.push_bounded(1, std::move(second));
      pool.update([&] { second_queued = true; });
    });
    while (!producer_started.load()) std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    assert(!second_queued.load());
    pool.start(1, [&](Task&, Worker&) { ++consumed; });
    assert(pool.wait_done(2000));
    pool.join(); producer.join();
    assert(consumed.load() == 2);
  }
  {
    Pool pool;
    std::atomic<int> scans{0};
    pool.scan_ready = [] { return false; };
    Task scan;
    pool.push(0, std::move(scan));
    pool.start(1, [&](Task&, Worker&) { ++scans; });
    assert(!pool.wait_done(50));
    pool.abort();
    pool.join();
    assert(scans.load() == 0);
  }
}
