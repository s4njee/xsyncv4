// xsync — shared types, options, global state and small helpers.
#pragma once
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>

#include "filter.h"

using u8 = uint8_t;
using u16 = uint16_t;
using u32 = uint32_t;
using u64 = uint64_t;
using i64 = int64_t;

#define XSYNC_VERSION "0.1.0"
constexpr u32 PROTO_VERSION = 4;
constexpr u32 PROTO_MIN_VERSION = PROTO_VERSION - 1;
constexpr u64 PF_CORE = 1, PF_ZSTD = 2, PF_IDMAP = 4, PF_SAFE_LINKS = 8, PF_RESUME = 16, PF_OUTPUT = 32;
constexpr u64 PF_DIR_OUTPUT = 64, PF_HLINK = 128, PF_DELTA = 256;
constexpr u64 PF_LIST = 512;
constexpr u64 PF_IO_CONTROL = 1024;
#ifndef XSYNC_PROTOCOL_FEATURES
#define XSYNC_PROTOCOL_FEATURES 2047
#endif
constexpr u64 PROTO_FEATURES = XSYNC_PROTOCOL_FEATURES;
constexpr u64 LEGACY_V3_FEATURES = 15;

// ---------------------------------------------------------------- options

#define WIRE_V3_BOOL_OPTS(X)                                                               \
  X(recursive) X(dirs) X(links) X(copy_links) X(perms) X(times) X(group) X(owner)         \
  X(devices) X(specials) X(compress) X(dry_run) X(del) X(delete_excluded) X(force)        \
  X(update) X(checksum) X(size_only) X(ignore_times) X(ignore_existing) X(existing)       \
  X(one_fs) X(inplace) X(omit_dir_times) X(omit_link_times) X(numeric_ids) X(itemize)     \
  X(partial) X(clone) X(direct_new) X(ignore_errors) X(safe_links)
#define WIRE_V3_INT_OPTS(X) \
  X(verbose) X(compress_level) X(max_size) X(min_size) X(modify_window) X(jobs) X(max_delete)
#define BOOL_OPTS(X) WIRE_V3_BOOL_OPTS(X)
#define INT_OPTS(X) WIRE_V3_INT_OPTS(X)

struct Options {
#define X(n) bool n = false;
  BOOL_OPTS(X)
#undef X
#define X(n) i64 n = 0;
  INT_OPTS(X)
#undef X
  bool quiet = false, progress = false, stats = false, mkpath = false;
  int human = 0;
  std::string rsh, rsync_path;
  bool rsh_set = false;  // Client-only; an explicit empty command is an error.
  bool whole_file = false;  // Client controls resume feature negotiation.
  std::string out_format, log_file;
  bool out_format_set = false;  // An explicitly empty format suppresses file lines.
  bool raw_names = false;  // -8: retain invalid high bytes; escape unsafe control bytes.
  int itemize_level = 0;
  bool output_attrs = false, output_unchanged = false;  // Configured before workers start.
  bool hard_links = false;  // Negotiated separately from the frozen v3 options.
  bool delete_before = false;  // Deletion is still deferred for sender-read safety.
  bool list_only = false, dirs_explicit = false, human_ungrouped = false;
  u64 bwlimit = 0;  // Bytes/second; outside the frozen v3 option layout.
  u32 timeout = 0;  // Remote idle seconds; zero disables the deadline.
  FilterList filters;
  // Set at runtime, not parsed.
  bool am_root = false;
  bool am_server = false;
  bool pushing = false;  // client is sending to a remote receiver (itemize prints '<')
  bool receiving = false;  // Client-only: short %f and recv %o for remote pulls.
  u32 wire_version = PROTO_VERSION;
  u64 peer_features = PROTO_FEATURES;
};

extern Options g_opt;
extern u32 g_umask;

// ---------------------------------------------------------------- entries

enum : u8 { T_NONE = 0, T_REG, T_DIR, T_LNK, T_FIFO, T_SOCK, T_CHR, T_BLK };

enum : u8 {
  EF_EXISTS = 1,     // destination already has something at this name
  EF_DESCEND = 2,    // directory is ready to be synced into
  EF_CREATED = 4,    // directory was created by us (destination listing can be skipped)
  EF_MODE_OK = 8,    // directory mode already matches
  EF_TIME_OK = 16,   // directory mtime already matches
  EF_LAZY = 32,      // directory: creation left to whoever syncs into it (shares the bit below)
  EF_DIFF_SIZE = 32, // regular file: for itemize
  EF_DIFF_TIME = 64,
  EF_DANGLING = 128, // symlink without referent under --copy-links
  EF_INPLACE_SAFE = 128, // regular file: generator saw a regular destination
};

struct Entry {
  u32 name_off = 0, link_off = 0;  // offsets of NUL-terminated strings in DirList::names
  u16 name_len = 0;
  u8 type = T_NONE, flags = 0;
  u8 item_flags = 0;  // Receiver-side comparison, kept separate from filesystem flags.
  u32 mode = 0;  // permission bits only (07777)
  u32 uid = 0, gid = 0, mtime_ns = 0, rdev = 0, dev = 0;
  i64 size = 0, mtime = 0;
  u64 hdev = 0, ino = 0, nlink = 0;
  i64 ctime = 0;
  u32 ctime_ns = 0;
};
enum : u8 { IF_PERMS = 1, IF_OWNER = 2, IF_GROUP = 4, IF_NEW_TYPE = 8 };

struct DirList {
  std::vector<Entry> e;
  std::string names;
  std::vector<u64> sums;  // 2 words per entry when --checksum (XXH3-128), else empty
  bool incomplete = false;

  void clear() {
    e.clear();
    names.clear();
    sums.clear();
    incomplete = false;
  }
  const char* name(const Entry& x) const { return names.data() + x.name_off; }
  std::string_view name_sv(const Entry& x) const { return {names.data() + x.name_off, x.name_len}; }
  const char* link(const Entry& x) const { return names.data() + x.link_off; }
  u32 add_str(std::string_view s) {
    u32 off = (u32)names.size();
    names.append(s);
    names.push_back('\0');
    return off;
  }
  void sort();
};

// ---------------------------------------------------------------- stats

struct Stats {
  std::atomic<u64> files_seen{0}, dirs_seen{0}, links_seen{0}, specials_seen{0}, bytes_seen{0};
  std::atomic<u64> xfer_files_total{0}, xfer_bytes_total{0};  // planned
  std::atomic<u64> xfer_files{0}, xfer_bytes{0};              // completed
  std::atomic<u64> created_files{0}, created_dirs{0}, created_links{0}, created_specials{0};
  std::atomic<u64> deleted{0};
  std::atomic<u64> wire_sent{0}, wire_recv{0};
  std::atomic<u64> delta_files{0}, delta_literal_bytes{0}, delta_matched_bytes{0};
  std::atomic<bool> scan_done{false};
};
extern Stats g_stats;
extern std::atomic<int> g_exit_code;
extern std::atomic<int> g_stop;
extern std::atomic<bool> g_source_io_error;

// ---------------------------------------------------------------- messages

// Informational line on stdout (file names, itemized changes). No trailing newline in `s`.
void out_line(std::string_view s);
// Error/warning on stderr, prefixed "xsync: ". code > 0 is recorded as the exit status.
void err_line(int code, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
void print_error_summary();
[[noreturn]] void die(int code, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
[[noreturn]] void exit_signal();
// When set (server mode) messages are routed here instead of the terminal. kind: 0=out 1=err.
extern void (*g_msg_sink)(int kind, int code, std::string_view s);

// rsync exit codes
enum { RERR_SYNTAX = 1, RERR_PROTOCOL = 2, RERR_FILESELECT = 3, RERR_UNSUPPORTED = 4,
       RERR_STARTCLIENT = 5, RERR_FILEIO = 11, RERR_STREAMIO = 12, RERR_IPC = 14,
       RERR_SIGNAL = 20, RERR_PARTIAL = 23, RERR_VANISHED = 24, RERR_DEL_LIMIT = 25, RERR_TIMEOUT = 30, RERR_CMD_FAILED = 124,
       RERR_CMD_NOTFOUND = 127 };

// ---------------------------------------------------------------- helpers

u64 now_ns();
std::string fmt_num(u64 v);         // 1,234,567 (or human-readable with -h)
std::string fmt_size(double v);     // 12.3M
std::string fmt_count(double v);    // 12.3k
inline std::string path_join(std::string_view a, std::string_view b) {
  std::string r;
  r.reserve(a.size() + b.size() + 1);
  r.append(a);
  if (!a.empty() && a.back() != '/') r.push_back('/');
  r.append(b);
  return r;
}
inline std::string rel_join(std::string_view a, std::string_view b) {
  if (a.empty()) return std::string(b);
  return path_join(a, b);
}
inline int name_cmp(std::string_view a, std::string_view b) {
  int c = memcmp(a.data(), b.data(), a.size() < b.size() ? a.size() : b.size());
  return c ? c : (a.size() < b.size() ? -1 : a.size() > b.size());
}
