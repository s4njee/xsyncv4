// Bounded streaming block matching shared by local copies and negotiated remote deltas.
#pragma once
#include <functional>
#include <memory>
#include "fs.h"

constexpr i64 DELTA_THRESHOLD = 1 << 20;
constexpr u32 DELTA_MAX_BLOCK = 1 << 18;
constexpr u32 DELTA_MAX_BLOCKS = 1 << 22;

struct DeltaBlock { u32 weak = 0; u64 strong = 0; };
struct DeltaSignature {
  i64 size = 0;
  u32 block_size = 0;
  std::vector<DeltaBlock> blocks;
  bool valid() const;
  i64 length(u32 first, u32 count = 1) const;
};
struct DeltaBasis {
  int fd = -1;
  DeltaSignature signature;
  ~DeltaBasis();
  DeltaBasis() = default;
  DeltaBasis(const DeltaBasis&) = delete;
};
// The basis is anchored and opened without following a receiver-owned symlink.
// Inplace writes require an anonymous snapshot so moved blocks remain readable.
std::shared_ptr<DeltaBasis> destination_delta_basis(const std::string& path, bool snapshot);
// Takes ownership of an already anchored read-only descriptor.
std::shared_ptr<DeltaBasis> readonly_delta_basis(int fd);

struct DeltaOp {
  i64 offset = 0;
  u32 first = 0, count = 0;  // count != 0: consecutive blocks in the basis
  std::string_view literal; // count == 0: new source bytes, valid during emit()
};
struct DeltaResult {
  bool ok = false;
  i64 processed = 0, literal_bytes = 0;
  u64 sum[2] = {};
};
// Keeps at most one block plus 1 MiB of source bytes, independent of file size.
DeltaResult delta_match_fd(int fd, i64 size, const DeltaSignature& signature,
                          const std::function<bool(const DeltaOp&)>& emit);
// Every copied basis block is rechecked against its advertised strong checksum.
bool delta_copy_blocks(OutFile& output, const DeltaBasis& basis, u32 first, u32 count,
                       i64 offset, std::vector<char>& scratch);
bool delta_verify_fd(int fd, i64 size, const u64 sum[2]);
