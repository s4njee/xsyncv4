#include <algorithm>
#include <cmath>
#include <unistd.h>
#include "rate_limit.h"

RateLimiter g_local_limiter;

void RateLimiter::configure(u64 bytes_per_second) {
  std::lock_guard<std::mutex> lock(mu);
  rate = bytes_per_second;
  capacity = std::max(1.0, std::min(16384.0, (double)rate / 10.0));
  tokens = capacity;
  last = now_ns();
}

size_t RateLimiter::acquire(size_t wanted, const std::function<void()>& check) {
  for (;;) {
    if (g_stop.load()) return 0;
    if (check) check();
    u64 delay;
    {
      std::lock_guard<std::mutex> lock(mu);
      if (!rate) return wanted;
      u64 now = now_ns();
      tokens = std::min(capacity, tokens + (double)(now - last) * ((double)rate / 1e9));
      last = now;
      size_t n = std::min(wanted, (size_t)capacity);
      if (tokens >= n) { tokens -= n; return n; }
      delay = (u64)std::ceil((n - tokens) * 1e6 / (double)rate);
    }
    // Short waits bound SIGINT latency and permit transport deadline checks.
    usleep((useconds_t)std::clamp<u64>(delay, 1, 50000));
  }
}
