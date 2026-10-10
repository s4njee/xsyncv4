#include "sparse.h"
#include <algorithm>
#include <cassert>
#include <cerrno>
#include <climits>
#include <cstdio>
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

int main() {
  FILE* file = tmpfile();
  assert(file);
  int fd = fileno(file);
  std::vector<char> bytes(65536, 'Q');
  assert(pwrite(fd, bytes.data(), bytes.size(), 0) == (ssize_t)bytes.size());
  std::vector<char> zero(32771);
  // Unaligned in-place zeroing must not erase either neighboring byte.
  assert(sparse_write(fd, zero.data(), zero.size(), 3, true));
  assert(pread(fd, bytes.data(), bytes.size(), 0) == (ssize_t)bytes.size());
  assert(bytes[2] == 'Q' && bytes[3 + zero.size()] == 'Q');
  assert(std::all_of(bytes.begin() + 3, bytes.begin() + 3 + zero.size(), [](char b) { return b == 0; }));
  // Zero tails establish EOF even when no write reaches their final byte.
  assert(sparse_write(fd, zero.data(), zero.size(), 65536, false));
  struct stat st;
  assert(fstat(fd, &st) == 0 && st.st_size == 65536 + (off_t)zero.size());
  assert(!sparse_write(fd, zero.data(), 1, -1, false) && errno == EINVAL);
  assert(!sparse_write(fd, zero.data(), 2, INT64_MAX, false) && errno == EINVAL);
  // Exercise offsets past 4 GiB without allocating or scanning that gap.
  assert(ftruncate(fd, 0) == 0);
  int64_t large = (int64_t(1) << 32) + 123;
  assert(sparse_write(fd, "marker", 6, large, false));
  assert(sparse_write(fd, zero.data(), zero.size(), large + 6, false));
  assert(fstat(fd, &st) == 0 && st.st_size == large + 6 + (off_t)zero.size());
  assert(pread(fd, bytes.data(), 6, large) == 6 && memcmp(bytes.data(), "marker", 6) == 0);
  // APFS growth can reallocate preceding holes. The final pass retains data.
  assert(ftruncate(fd, 0) == 0);
  bytes.assign(65536, 0);
  constexpr int64_t size = 8 * 1024 * 1024;
  for (int64_t offset = 0; offset < size; offset += bytes.size()) {
    bytes[0] = offset % (1024 * 1024) == 0 ? 'M' : 0;
    assert(sparse_write(fd, bytes.data(), bytes.size(), offset, false));
  }
  assert(sparse_compact(fd));
  assert(fsync(fd) == 0);
  assert(fstat(fd, &st) == 0 && st.st_size == size && st.st_blocks * 512 < size / 8);
  for (int64_t offset = 0; offset < size; offset += bytes.size()) {
    assert(pread(fd, bytes.data(), bytes.size(), offset) == (ssize_t)bytes.size());
    assert(bytes[0] == (offset % (1024 * 1024) == 0 ? 'M' : 0));
    assert(std::all_of(bytes.begin() + 1, bytes.end(), [](char b) { return b == 0; }));
  }
  assert(fclose(file) == 0);
}
