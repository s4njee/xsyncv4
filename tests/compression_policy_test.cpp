#include "compression.h"
#include <cassert>
#include <cstdint>
#include <random>
#include <string>
#include <zstd.h>

int main() {
  CompressionSuffixes suffixes;
  assert(suffixes.matches("path.to/file.JPG"));
  assert(!suffixes.matches("path.gz/file"));
  assert(!suffixes.matches("file.txt"));
  assert(suffixes.assign("gz/jpg/mp[34]/literal*/q?/dash[a-]"));
  assert(suffixes.matches("file.MP3") && suffixes.matches("file.mp4"));
  assert(!suffixes.matches("file.mp5") && !suffixes.matches("file.literal-anything"));
  assert(suffixes.matches("file.literal*") && suffixes.matches("file.q?"));
  assert(suffixes.matches("file.dash-") && suffixes.matches("file.dasha"));
  for (auto invalid : {"[", "[]", "foo]", "[nested[x]"}) assert(!suffixes.assign(invalid));
  assert(suffixes.matches("file.mp4")); // Failed assignments retain the previous policy.
  assert(!suffixes.assign(std::string(65537, 'x')));
  assert(!suffixes.assign(std::string("gz\0jpg", 6)));
  assert(suffixes.assign("") && !suffixes.matches("file.mp4"));

  // The rate rule, unchanged: judged over everything written so far.
  constexpr uint64_t MiB = 1024 * 1024, second = 1000000000;
  constexpr Transport saturated = Transport::saturated, keeping_up = Transport::keeping_up, queued = Transport::queued;
  CompressionLink unknown;
  assert(unknown.level(false, 3, 0) == 3);
  unknown.observe(128 * 1024, second, saturated, second);
  assert(unknown.level(false, 3, 0) == 3); // Do not infer a rate from tiny acknowledgments.
  CompressionLink fast, medium, slow;
  fast.observe(16 * MiB, second / 10, saturated, second);
  medium.observe(4 * MiB, second / 10, saturated, second);
  slow.observe(1 * MiB, second, saturated, second);
  assert(fast.level(false, 3, 0) == 1);
  assert(medium.level(false, 3, 0) == 3);
  assert(slow.level(false, 3, 0) == 6);
  assert(fast.level(false, 3, 1024 * 1024) == 6);

  // Writes `megabytes` at a rate, in 1 MiB frames, with the queue in a given state.
  uint64_t clock = 0;
  auto write = [&clock](CompressionLink& link, uint64_t megabytes, uint64_t bytes_per_second, Transport state) {
    for (uint64_t i = 0; i < megabytes; ++i) {
      uint64_t elapsed = MiB * second / bytes_per_second;
      link.observe(MiB, elapsed, state, clock += elapsed);
    }
    return link.level(false, 3, 0);
  };

  // A machine too slow for level 3 on a fast link: its compressors take CPU from
  // the transport process, the link measures at 46 MiB/s, and the rate rule keeps
  // level 3. But the writer keeps up with everything produced, so after 16 MiB
  // of that the level is capped at 1.
  CompressionLink weak;
  assert(write(weak, 15, 46 * MiB, keeping_up) == 3);
  assert(write(weak, 1, 46 * MiB, keeping_up) == 1);
  // At level 1 it fills the link. However the rate rule reads the history, the cap holds.
  assert(write(weak, 64, 100 * MiB, saturated) == 1);
  assert(write(weak, 64, 50 * MiB, saturated) == 1); // Slower, but still more than level 3 could feed.
  // Once the link carries distinctly less than the machine produced at level 3, level 3 would fill it.
  CompressionLink slowing;
  write(slowing, 16, 30 * MiB, keeping_up);
  assert(slowing.level(false, 3, 0) == 1);
  assert(write(slowing, 8, 28 * MiB, saturated) == 1);  // 28 is not distinctly less than 30.
  assert(write(slowing, 8, 20 * MiB, saturated) == 3);  // 20 is: the cap lifts and the rate rule decides.

  // Level 6 is capped to 3 in the same way, and no further without new evidence.
  CompressionLink crawling;
  assert(write(crawling, 15, 4 * MiB, keeping_up) == 6 && write(crawling, 1, 4 * MiB, keeping_up) == 3);
  assert(write(crawling, 15, 4 * MiB, keeping_up) == 3 && write(crawling, 1, 4 * MiB, keeping_up) == 1);

  // Keeping up is a matter of data written, not time: a scan phase that writes
  // little for a long while proves nothing about compression.
  CompressionLink scanning;
  for (int i = 0; i < 60; ++i) scanning.observe(64 * 1024, second, keeping_up, clock += second);
  assert(scanning.cap.load() == 6);

  // A queue forming interrupts a run of keeping up, and a link that is the
  // bottleneck never caps anything.
  CompressionLink flickering, busy;
  for (int i = 0; i < 40; ++i) {
    write(flickering, 12, 46 * MiB, keeping_up);
    write(flickering, 1, 46 * MiB, queued);
  }
  assert(flickering.cap.load() == 6 && flickering.level(false, 3, 0) == 3);
  assert(write(busy, 256, 20 * MiB, saturated) == 3 && busy.cap.load() == 6);

  CompressionLink report;
  assert(report.summary() == "3 (automatic)");
  report.count(1, 600);
  assert(report.summary() == "1 (automatic)");
  report.count(3, 300), report.count(6, 2100);
  assert(report.summary() == "6 (automatic; level 1: 20%, level 3: 10%, level 6: 70% of compressed input)");

  for (int explicit_level : {-1000, -5, 0, 1, 9, 22})
    assert(fast.level(true, explicit_level, 0) == explicit_level && slow.level(true, explicit_level, 0) == explicit_level);

  auto* context = ZSTD_createCCtx();
  assert(context);
  std::string random(1 << 20, '\0');
  std::mt19937 generator(42);
  for (char& byte : random) byte = (char)generator();
  assert(!compression_worthwhile(random, context));
  assert(compression_worthwhile(std::string(1 << 20, 'x'), context));
  // A block with substantial compressible regions should still reach the codec.
  random.replace(0, 512 * 1024, 512 * 1024, 'x');
  assert(compression_worthwhile(random, context));
  assert(compression_worthwhile("small record", context));
  ZSTD_freeCCtx(context);
}
