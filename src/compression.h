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

// Chooses the zstd level from how fast the transport drains, judged only over
// windows in which the transport was the bottleneck: the send queue was backed
// up. When it is not, something upstream limits the transfer, and a costlier
// level can only slow it, however slow the writes measure. That matters on a
// small machine, where compressor threads take CPU from the transport process
// and make a fast link measure as a slow one; a policy that trusts that
// measurement stays at the costly level for the whole transfer.
//
// The level starts at 1 and moves one step at a time between 1, 3 and 6. It
// rises only after the transport has been the slow bottleneck for a full
// second of writing, so a stall of a few hundred milliseconds on a fast link
// does not buy seconds of costlier compression; it falls after one window.
// Only active transport writes are measured, so idle source or scan time
// cannot make a fast link look slow. Bandwidth limiting is part of the write.
struct CompressionLink {
  static constexpr uint64_t WINDOW_BYTES = 4ull << 20, WINDOW_NS = 250'000'000ull, MIN_BYTES = 256ull << 10;
  static constexpr uint64_t FAST = 64ull << 20, SLOW = 8ull << 20;  // bytes per second
  static constexpr uint64_t RAISE_NS = 1'000'000'000ull;            // slow, backed-up writing before a raise
  static constexpr uint64_t HOLD_NS = 10'000'000'000ull;            // after a raise proved too costly

  std::atomic<int> current{1}, last_level{1};
  std::atomic<bool> used{false};
  // Writer thread only. `backlogged`: these bytes were written while frames were waiting behind them.
  void observe(uint64_t count, uint64_t elapsed, bool backlogged, uint64_t now);
  int level(bool explicit_level, int requested) const;

 private:
  uint64_t bytes_ = 0, nanoseconds_ = 0, backlogged_bytes_ = 0, slow_ns_ = 0, hold_until_ = 0;
};

// Sample four spaced regions before spending CPU on an entire large block.
// A false prediction affects wire size only; frame checksums remain unchanged.
bool compression_worthwhile(std::string_view raw, void* context);
