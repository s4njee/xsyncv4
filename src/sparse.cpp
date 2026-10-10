#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "sparse.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <climits>
#include <cstring>
#include <vector>
#ifndef __APPLE__
#include <linux/falloc.h>
#endif

namespace {
constexpr size_t BLOCK = 4096;
const char zero[BLOCK] = {};
bool write_bytes(int fd, const char* bytes, size_t size, int64_t offset) {
  while (size) {
    ssize_t done = pwrite(fd, bytes, size, offset);
    if (done < 0 && errno == EINTR) continue;
    if (done <= 0) { if (!done) errno = EIO; return false; }
    bytes += done, offset += done, size -= (size_t)done;
  }
  return true;
}


bool punch(int fd, int64_t offset, size_t size) {
#ifdef __APPLE__
  fpunchhole_t hole = {};
  hole.fp_offset = offset, hole.fp_length = size;
  return fcntl(fd, F_PUNCHHOLE, &hole) == 0;
#else
  return fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE, offset, size) == 0;
#endif
}
bool clear_existing(int fd, const char* bytes, size_t size, int64_t offset) {
  // Darwin requires aligned hole requests. Write partial edge blocks and
  // punch the complete interior without clearing bytes outside this range.
  size_t head = std::min<size_t>(size, (BLOCK - (offset % BLOCK)) % BLOCK);
  if (head && !write_bytes(fd, bytes, head, offset)) return false;
  size_t middle = ((size - head) / BLOCK) * BLOCK;
  if (middle && !punch(fd, offset + head, middle) &&
      !write_bytes(fd, bytes + head, middle, offset + head)) return false;
  size_t tail = size - head - middle;
  return !tail || write_bytes(fd, bytes + head + middle, tail, offset + head + middle);
}
}

bool sparse_write(int fd, const char* bytes, size_t size, int64_t offset, bool reused) {
  if (offset < 0 || size > (uint64_t)INT64_MAX - (uint64_t)offset) { errno = EINVAL; return false; }
  size_t position = 0;
  bool trailing_hole = false;
  while (position < size) {
    size_t count = std::min<size_t>(size - position, BLOCK - ((offset + position) % BLOCK));
    bool hole = memcmp(bytes + position, zero, count) == 0;
    size_t end = position + count;
    while (end < size) {
      size_t next = std::min(size - end, BLOCK);
      if ((memcmp(bytes + end, zero, next) == 0) != hole) break;
      end += next;
    }
    count = end - position;
    trailing_hole = hole;
    // A reused inode can contain nonzero bytes here. If hole punching is
    // unavailable, write zeroes instead of leaving its previous data intact.
    if (hole) {
      if (reused && !clear_existing(fd, bytes + position, count, offset + position)) return false;
      if (!reused) {
        // APFS may allocate skipped gaps when a later write reaches past EOF.
        // Establish this zero range first and deallocate its complete blocks.
        // Partial edge blocks already contain zeroes in a new output inode.
        struct stat st;
        if (fstat(fd, &st) != 0) return false;
        int64_t start = offset + position, end = start + count;
        if (st.st_size < end && ftruncate(fd, end) != 0) return false;
        size_t head = std::min<size_t>(count, (BLOCK - (start % BLOCK)) % BLOCK);
        size_t middle = ((count - head) / BLOCK) * BLOCK;
        if (middle) punch(fd, start + head, middle);
      }
    } else if (!write_bytes(fd, bytes + position, count, offset + position)) return false;
    position = end;
  }
  // Skipping trailing zeroes must still establish EOF, including before a
  // delta checksum or an interrupted transfer publishes its verified prefix.
  if (trailing_hole) {
    struct stat st;
    if (fstat(fd, &st) != 0) return false;
    int64_t end = offset + size;
    if (st.st_size < end && ftruncate(fd, end) != 0) return false;
  }
  return true;
}

bool sparse_compact(int fd, const std::atomic<int>* stop) {
  // Join zeroes split across unaligned delta blocks, and clear APFS holes
  // reallocated by growth. Revisit allocated extents with bounded scratch
  // space; file systems without hole enumeration get a full allocation pass.
  int flags = fcntl(fd, F_GETFL);
  if (flags < 0) return false;
  // A writable but unreadable --inplace file still accepts sparse writes;
  // allocation refinement must not turn a valid whole-file copy into failure.
  if ((flags & O_ACCMODE) == O_WRONLY) return true;
  struct stat st;
  if (fstat(fd, &st) != 0) return false;
  std::vector<char> bytes(65536);
  int64_t offset = 0;
  bool seek_holes = true;
  while (offset < st.st_size) {
    int64_t end = st.st_size;
    if (seek_holes) {
      off_t data = lseek(fd, offset, SEEK_DATA);
      if (data < 0) {
        if (errno == ENXIO) break;
        seek_holes = false;
      } else {
        offset = data;
        off_t hole = lseek(fd, offset, SEEK_HOLE);
        if (hole <= offset) seek_holes = false;
        else end = std::min<int64_t>(hole, st.st_size);
      }
    }
    while (offset < end) {
      if (stop && stop->load(std::memory_order_relaxed)) { errno = EINTR; return false; }
      size_t count = std::min<int64_t>(bytes.size(), end - offset);
      size_t got = 0;
      while (got < count) {
        ssize_t n = pread(fd, bytes.data() + got, count - got, offset + got);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { if (!n) errno = EIO; return false; }
        got += (size_t)n;
      }
      size_t position = (BLOCK - (offset % BLOCK)) % BLOCK;
      while (position + BLOCK <= got) {
        if (memcmp(bytes.data() + position, zero, BLOCK) != 0) { position += BLOCK; continue; }
        size_t start = position;
        do { position += BLOCK; }
        while (position + BLOCK <= got && memcmp(bytes.data() + position, zero, BLOCK) == 0);
        // These bytes were read as zeroes, so unsupported punching needs no
        // write fallback and does not change the file's contents.
        punch(fd, offset + start, position - start);
      }
      offset += got;
    }
  }
  return true;
}
