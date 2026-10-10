#include "compression.h"
#include <cassert>
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

  CompressionLink unknown;
  assert(unknown.level(false, 3, 0) == 3);
  unknown.observe(128 * 1024, 1000000000);
  assert(unknown.level(false, 3, 0) == 3); // Do not infer a rate from tiny acknowledgments.
  CompressionLink fast, medium, slow;
  fast.observe(16 * 1024 * 1024, 100000000);
  medium.observe(4 * 1024 * 1024, 100000000);
  slow.observe(1024 * 1024, 1000000000);
  assert(fast.level(false, 3, 0) == 1);
  assert(medium.level(false, 3, 0) == 3);
  assert(slow.level(false, 3, 0) == 6);
  assert(fast.level(false, 3, 1024 * 1024) == 6);
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
