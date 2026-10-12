#pragma once
#include <atomic>
#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

// Slash-separated suffixes, with rsync's literal character-class syntax.
inline constexpr std::string_view DEFAULT_SKIP_COMPRESS =
  "3g2/3gp/7z/aac/ace/apk/avi/bz2/deb/dmg/ear/f4v/flac/flv/gpg/gz/iso/jar/jpeg/jpg/"
  "lrz/lz/lz4/lzma/lzo/m1a/m1v/m2a/m2ts/m2v/m4a/m4b/m4p/m4r/m4v/mka/mkv/mov/mp1/mp2/"
  "mp3/mp4/mpa/mpeg/mpg/mpv/mts/odb/odf/odg/odi/odm/odp/ods/odt/oga/ogg/ogm/ogv/ogx/"
  "opus/otg/oth/otp/ots/ott/oxt/png/qt/rar/rpm/rz/rzip/spx/squashfs/sxc/sxd/sxg/sxm/sxw/"
  "sz/tbz/tbz2/tgz/tlz/ts/txz/tzo/vob/war/webm/webp/xz/z/zip/zst";

class CompressionSuffixes {
 public:
  CompressionSuffixes() = default; // Non-compressing transfers avoid suffix-table allocation.
  bool assign(std::string_view list);
  bool matches(std::string_view name) const;
 private:
  std::unordered_set<std::string> literals_;
  std::vector<std::string> classes_;
  bool initialized_ = false;
};

// What the send queue said about the transport while some bytes were written.
enum class Transport {
  saturated,   // producers had to wait for room in the queue: the transport is the bottleneck
  queued,      // a deep queue was waiting, though producers were not held up
  keeping_up,  // little was waiting: the writer is keeping up with what is produced
};

// Chooses the zstd level between 1, 3 and 6, starting at 3.
//
// While the transport is the bottleneck, the measured write rate is the link's
// rate and decides the level as before: 1 at 64 MiB/s or faster, 6 below
// 8 MiB/s, 3 in between. A lower target takes effect at once; a higher one
// needs a second of such writing, so a short stall does not raise it.
//
// While the writer keeps up with what is produced, compression or reading is
// the bottleneck and the level drops, whatever the writes measure at. This is
// what the rate alone gets wrong: on a small machine the compressor threads
// take CPU from the transport process, a gigabit link then measures as a slow
// one, and a policy that trusts the measurement stays at a level that halves
// the transfer's speed. Keeping up is judged over data written, not time, so
// an idle scan phase proves nothing. The link rate at which the higher level
// proved too costly is remembered, and that level is not tried again unless
// the link gets distinctly slower.
//
// Only active transport writes are measured, so idle source or scan time cannot
// make a fast link look slow. Bandwidth limiting is part of the write.
struct CompressionLink {
  static constexpr uint64_t WINDOW_BYTES = 4ull << 20, WINDOW_NS = 250'000'000ull, MIN_BYTES = 256ull << 10;
  static constexpr uint64_t FAST = 64ull << 20, SLOW = 8ull << 20;  // bytes per second
  static constexpr uint64_t RAISE_NS = 1'000'000'000ull;            // slow, saturated writing before a raise
  static constexpr uint64_t DROP_BYTES = 16ull << 20;               // written while keeping up, before a drop

  std::atomic<int> current{3}, last_level{3};
  std::atomic<bool> used{false};
  std::atomic<uint64_t> compressed_input[3] = {};  // raw bytes compressed at levels 1, 3 and 6
  // Writer thread only: `count` bytes took `elapsed` ns to write.
  void observe(uint64_t count, uint64_t elapsed, Transport state);
  int level(bool explicit_level, int requested) const;
  // Record that a worker compressed `raw` bytes at an automatic level.
  void count(int level, uint64_t raw) {
    compressed_input[level >= 6 ? 2 : level >= 3 ? 1 : 0].fetch_add(raw, std::memory_order_relaxed);
  }
  // "3 (automatic)", or "1 (automatic; level 1: 62%, level 3: 38% of compressed input)"
  // when more than one level was used: the level that compressed the most comes first.
  std::string summary() const;

 private:
  uint64_t bytes_ = 0, nanoseconds_ = 0, saturated_bytes_ = 0;
  uint64_t slow_ns_ = 0, keeping_up_bytes_ = 0;
  double ceiling_ = 0;  // link rate at which the level above this one proved too costly
  bool awaiting_ceiling_ = false;
};

// Sample four spaced regions before spending CPU on an entire large block.
// A false prediction affects wire size only; frame checksums remain unchanged.
bool compression_worthwhile(std::string_view raw, void* context);
