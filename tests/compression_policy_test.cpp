#include "compression.h"
#include <cassert>
#include <cstdint>
#include <random>
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

  // One window of transport writes at a given rate, with or without a queue behind them.
  constexpr uint64_t MiB = 1024 * 1024, second = 1000000000;
  uint64_t clock = 0;
  auto window = [&clock](CompressionLink& link, uint64_t bytes_per_second, bool backlogged) {
    uint64_t count = CompressionLink::WINDOW_BYTES, elapsed = count * second / bytes_per_second;
    clock += elapsed;
    link.observe(count, elapsed, backlogged, clock);
    return link.level(false, 3);
  };

  CompressionLink unknown;
  assert(unknown.level(false, 3) == 1); // Start cheap: a costly first block can hide a fast link.
  unknown.observe(128 * 1024, second, true, second);
  assert(unknown.level(false, 3) == 1); // Do not infer a rate from tiny acknowledgments.

  CompressionLink fast, medium, slow;
  for (int i = 0; i < 4; ++i) assert(window(fast, 100 * MiB, true) == 1);
  assert(window(medium, 20 * MiB, true) == 3 && window(medium, 20 * MiB, true) == 3);
  assert(window(slow, 4 * MiB, true) == 3 && window(slow, 4 * MiB, true) == 6); // One step per window.
  assert(window(slow, 4 * MiB, true) == 6);
  assert(window(slow, 20 * MiB, true) == 3 && window(slow, 100 * MiB, true) == 1); // And back as the link speeds up.

  // A machine that cannot keep the link busy at a level is limited by compression,
  // whatever rate its writes measure at: with the compressors holding every core
  // the transport process drains slowly, but nothing queues behind it.
  CompressionLink starved;
  for (int i = 0; i < 8; ++i) assert(window(starved, 46 * MiB, false) == 1);

  // A slow spell on a busy link raises the level; if that makes this machine the
  // bottleneck, the level drops back and is held there instead of flapping.
  CompressionLink trapped;
  assert(window(trapped, 30 * MiB, true) == 3);
  assert(window(trapped, 46 * MiB, false) == 1);
  uint64_t dropped = clock;
  while (clock - dropped < CompressionLink::HOLD_NS - second) assert(window(trapped, 30 * MiB, true) == 1);
  clock = dropped + CompressionLink::HOLD_NS;
  assert(window(trapped, 30 * MiB, true) == 3); // After the hold a genuinely slow link is believed again.

  // A window counts as transport-bound only if most of its bytes had a queue behind them.
  CompressionLink mixed;
  mixed.observe(3 * MiB, 3 * second / 20, false, clock);
  mixed.observe(1 * MiB, 1 * second / 20, true, clock);
  assert(mixed.level(false, 3) == 1);

  // A slow window of time also decides, without waiting for a full window of bytes.
  CompressionLink crawling;
  crawling.observe(512 * 1024, second, true, clock);
  assert(crawling.level(false, 3) == 3);

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
