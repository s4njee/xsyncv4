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

// Only active transport writes contribute, so idle source/scan time cannot
// make a fast link look slow. Bandwidth limiting is part of the measured write.
struct CompressionLink {
  std::atomic<uint64_t> bytes{0}, nanoseconds{0};
  std::atomic<int> last_level{3};
  std::atomic<bool> used{false};
  void observe(uint64_t count, uint64_t elapsed);
  int level(bool explicit_level, int requested, uint64_t rate_limit) const;
};

// Sample four spaced regions before spending CPU on an entire large block.
// A false prediction affects wire size only; frame checksums remain unchanged.
bool compression_worthwhile(std::string_view raw, void* context);
