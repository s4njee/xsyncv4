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

// What the send queue showed when the writer took the bytes it then wrote.
enum class Transport {
  saturated,   // producers had to wait for room in the queue: the transport is the bottleneck
  queued,      // a deep queue was waiting, though producers were not held up
  keeping_up,  // little was waiting: the writer is keeping up with what is produced
};

// Chooses the zstd level from the rate of active transport writes: 3 until
// 256 KiB have been written, then 1 at 64 MiB/s or faster, 6 below 8 MiB/s
// and 3 in between. Idle source or scan time is not measured, so it cannot
// make a fast link look slow, and bandwidth limiting is part of the write.
//
// The rate alone cannot tell a slow link from a machine too slow for the
// level: compressor threads take CPU from the transport process, a gigabit
// link then measures as a 46 MiB/s one, and the level never leaves 3 although
// level 1 would fill the link. So when the writer has kept up with everything
// produced for DROP_BYTES in a row, the level in force is one this machine
// cannot sustain against this link, and the level is capped a step lower. The
// rate at which it was producing is kept: the cap lifts only when the link
// itself is seen to carry less than that, which is when the higher level
// would fill it.
struct CompressionLink {
  static constexpr uint64_t DROP_BYTES = 16ull << 20;   // written while keeping up, before the cap drops
  static constexpr uint64_t WINDOW_BYTES = 4ull << 20;  // saturated writing judged for lifting the cap

  std::atomic<uint64_t> bytes{0}, nanoseconds{0};
  std::atomic<int> cap{6}, last_level{3};
  std::atomic<bool> used{false};
  std::atomic<uint64_t> compressed_input[3] = {};  // raw bytes compressed at levels 1, 3 and 6
  // Writer thread only: `count` bytes took `elapsed` ns to write, finishing at `now`.
  void observe(uint64_t count, uint64_t elapsed, Transport state, uint64_t now, uint64_t rate_limit = 0);
  int level(bool explicit_level, int requested, uint64_t rate_limit) const;
  // Automatic compression (no -z) pays while the writer moves under AUTO_RATE: over an internet link that is the
  // link's rate, as the writer waits on ssh; on a local pipe or a fast LAN the writer's own rate turns it off.
  // From the start, until 256 KiB have been written, it is on.
  static constexpr double AUTO_RATE = 256.0 * 1024 * 1024;
  static constexpr int AUTO_MAX_LEVEL = 3;  // a transient writer stall must not push it to level 6
  bool automatic_pays() const;
  // Record that a worker compressed `raw` bytes at an automatic level.
  void count(int level, uint64_t raw) {
    compressed_input[level >= 6 ? 2 : level >= 3 ? 1 : 0].fetch_add(raw, std::memory_order_relaxed);
  }
  // "3 (automatic)", or "1 (automatic; level 1: 62%, level 3: 38% of compressed input)"
  // when more than one level was used: the level that compressed the most comes first.
  std::string summary() const;

 private:
  uint64_t keeping_up_bytes_ = 0, keeping_up_since_ = 0;
  uint64_t window_bytes_ = 0, window_ns_ = 0, window_saturated_ = 0;
  double sustained_ = 0;  // bytes per second this machine produced at the level it could not sustain
};

// Sample four spaced regions before spending CPU on an entire large block.
// A false prediction affects wire size only; frame checksums remain unchanged.
bool compression_worthwhile(std::string_view raw, void* context);
