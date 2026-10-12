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

  // One window of transport writes at a given rate, in a given state of the send queue.
  constexpr uint64_t MiB = 1024 * 1024, second = 1000000000;
  constexpr Transport saturated = Transport::saturated, starved = Transport::starved, neutral = Transport::neutral;
  uint64_t clock = 0;
  auto window = [&clock](CompressionLink& link, uint64_t bytes_per_second, Transport state) {
    uint64_t count = CompressionLink::WINDOW_BYTES, elapsed = count * second / bytes_per_second;
    clock += elapsed;
    link.observe(count, elapsed, state, clock);
    return link.level(false, 3);
  };
  // Writes until the level changes or `seconds` of write time have passed; returns the level.
  auto sustain = [&](CompressionLink& link, uint64_t bytes_per_second, Transport state, double seconds) {
    int before = link.level(false, 3);
    for (uint64_t start = clock; clock - start < (uint64_t)(seconds * second);)
      if (window(link, bytes_per_second, state) != before) break;
    return link.level(false, 3);
  };

  CompressionLink unknown;
  assert(unknown.level(false, 3) == 3);
  unknown.observe(128 * 1024, second, saturated, second);
  assert(unknown.level(false, 3) == 3); // Do not infer a rate from tiny acknowledgments.

  // While the transport is the bottleneck its rate decides, as it always did.
  CompressionLink fast, medium, slow;
  assert(window(fast, 100 * MiB, saturated) == 1 && sustain(fast, 100 * MiB, saturated, 5) == 1);
  assert(sustain(medium, 20 * MiB, saturated, 5) == 3);
  assert(window(slow, 4 * MiB, saturated) == 6);        // One window here is a full second of slow writing.
  assert(sustain(slow, 4 * MiB, saturated, 5) == 6);
  assert(window(slow, 20 * MiB, saturated) == 3 && window(slow, 100 * MiB, saturated) == 1); // Falling is immediate.

  // A higher level needs a full second of slow writing, so a stall on a fast link does not buy one.
  CompressionLink stalling;
  assert(window(stalling, 100 * MiB, saturated) == 1);
  for (int i = 0; i < 6; ++i) {
    assert(sustain(stalling, 20 * MiB, saturated, 0.6) == 1);
    assert(window(stalling, 100 * MiB, saturated) == 1);
  }
  assert(sustain(stalling, 20 * MiB, saturated, 0.7) == 1 && sustain(stalling, 20 * MiB, saturated, 0.5) == 3);

  // A machine that cannot keep the link busy is limited by compression, whatever
  // rate its writes measure at: its compressors take CPU from the transport
  // process, so a fast link measures as a slow one while the writer runs dry.
  CompressionLink weak;
  assert(sustain(weak, 46 * MiB, starved, 0.4) == 3);   // Not on the first dry spell,
  assert(sustain(weak, 46 * MiB, starved, 0.3) == 1);   // but after half a second of it.
  assert(sustain(weak, 100 * MiB, saturated, 30) == 1); // At level 1 it fills the link and stays there.

  // The same machine on a link slow enough to ask for level 3: the level that
  // starved it is not tried again at that link rate, only if the link gets distinctly slower.
  CompressionLink remembered;
  assert(sustain(remembered, 30 * MiB, saturated, 2) == 3);
  assert(sustain(remembered, 30 * MiB, starved, 1) == 1);
  assert(sustain(remembered, 30 * MiB, saturated, 30) == 1);
  assert(sustain(remembered, 25 * MiB, saturated, 30) == 1);
  assert(window(remembered, 15 * MiB, saturated) == 3); // It has been slow and saturated for long enough already.

  // Frames waiting without producers held up says nothing either way, and
  // starvation that comes and goes is not a verdict.
  CompressionLink idle, flickering;
  assert(sustain(idle, 46 * MiB, neutral, 30) == 3);
  for (int i = 0; i < 40; ++i) {
    assert(window(flickering, 46 * MiB, starved) == 3);
    assert(sustain(flickering, 46 * MiB, neutral, 0.3) == 3);
  }

  // A window is saturated only if most of its bytes were, and one saturated byte rules out starvation.
  CompressionLink mostly_neutral, crawling;
  mostly_neutral.observe(3 * MiB, 3 * second / 100, neutral, clock);
  mostly_neutral.observe(1 * MiB, 1 * second / 100, saturated, clock);
  assert(mostly_neutral.level(false, 3) == 3);
  // A slow window of time also decides, without waiting for a full window of bytes.
  crawling.observe(512 * 1024, second, saturated, clock += second);
  assert(crawling.level(false, 3) == 6);
  crawling.observe(128 * 1024, second, saturated, clock += second);
  assert(crawling.level(false, 3) == 6); // Still too few bytes to judge.

  CompressionLink report;
  assert(report.summary() == "3 (automatic)");
  report.count(1, 600);
  assert(report.summary() == "1 (automatic)");
  report.count(3, 300), report.count(6, 2100);
  assert(report.summary() == "6 (automatic; level 1: 20%, level 3: 10%, level 6: 70% of compressed input)");

  for (int explicit_level : {-1000, -5, 0, 1, 9, 22})
    assert(fast.level(true, explicit_level) == explicit_level && slow.level(true, explicit_level) == explicit_level);

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
