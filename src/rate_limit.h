#pragma once
#include <functional>
#include <mutex>
#include "common.h"

// One token bucket per connection writer, or shared by all local copy workers.
// At most 0.1 seconds (and 16 KiB) can accumulate, even after a long idle period.
class RateLimiter {
  std::mutex mu;
  u64 rate = 0, last = 0;
  double tokens = 0, capacity = 0;
 public:
  void configure(u64 bytes_per_second);
  size_t acquire(size_t wanted, const std::function<void()>& check = {});
};
extern RateLimiter g_local_limiter;
