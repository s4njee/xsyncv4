// xsync — shared types, options, global state and small helpers.
#pragma once
#include "permissions.h"
#include "ownership.h"
#include "compression.h"
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <vector>
#include <memory>

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
constexpr u64 PF_FILTERS = 2048;
constexpr u64 PF_MERGE_FILTERS = 4096;
constexpr u64 PF_CVS_FILTERS = 8192;
constexpr u64 PF_DELETE_AFTER = 16384;
constexpr u64 PF_PRUNE_EMPTY = 32768;
constexpr u64 PF_RELATIVE = 65536;
constexpr u64 PF_FILES_FROM = 131072;
constexpr u64 PF_XATTRS = 262144;
constexpr u64 PF_XATTR_STREAM = 524288;
constexpr u64 PF_ACL_POSIX = 1048576, PF_ACL_DARWIN = 2097152;
constexpr u64 PF_ACLS = PF_ACL_POSIX | PF_ACL_DARWIN;
constexpr u64 PF_ACL_UUID = 4194304;
constexpr u64 PF_ATIMES = 8388608, PF_CRTIMES = 16777216, PF_OPEN_NOATIME = 33554432;
constexpr u64 PF_EXECUTABILITY = 67108864;
constexpr u64 PF_FILEFLAGS = 134217728;
constexpr u64 PF_CHOWN = 268435456;
constexpr u64 PF_SPARSE = 536870912;
constexpr u64 PF_LINK_DEST = 1073741824;
constexpr u64 PF_PROGRESS_ACK = 2147483648;
constexpr u64 PF_STAGE_METRICS = 4294967296ULL;
constexpr u64 PF_PROGRESS_PHASE = 8589934592ULL;
constexpr u64 PF_COMPRESS_POLICY = 17179869184ULL;
constexpr u64 PF_DIR_CHILDREN = 34359738368ULL;
constexpr u64 PF_APP_EVENTS = 68719476736ULL;  // App bridge: literal paths and typed events.
constexpr u64 PF_APP_CONTROLS = 137438953472ULL;
constexpr u64 PF_APP_LEASE = 274877906944ULL;
constexpr u64 PF_APP_PARTIALS = 549755813888ULL;
constexpr u64 APP_TRANSFER_FEATURES = PF_CORE | PF_OUTPUT | PF_DIR_OUTPUT | PF_IO_CONTROL |
                                     PF_PROGRESS_ACK | PF_DIR_CHILDREN | PF_APP_EVENTS;
#ifdef __APPLE__
constexpr u64 PF_NATIVE_ACL = PF_ACL_DARWIN;
constexpr u64 PF_UNSUPPORTED_NATIVE = PF_ACL_POSIX;
#else
constexpr u64 PF_NATIVE_ACL = PF_ACL_POSIX;
constexpr u64 PF_UNSUPPORTED_NATIVE = PF_ACL_DARWIN | PF_ACL_UUID | PF_CRTIMES | PF_FILEFLAGS;
#endif
#ifndef XSYNC_PROTOCOL_FEATURES
#define XSYNC_PROTOCOL_FEATURES 1099511627775ULL
#endif
constexpr u64 PROTO_FEATURES = XSYNC_PROTOCOL_FEATURES & ~PF_UNSUPPORTED_NATIVE;
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

struct FileListRequests;
struct Options {
#define X(n) bool n = false;
  BOOL_OPTS(X)
#undef X
#define X(n) i64 n = 0;
  INT_OPTS(X)
#undef X
  bool quiet = false, progress = false, stats = false, mkpath = false;
  bool compress_level_explicit = false, skip_compress_set = false;
  std::string skip_compress{DEFAULT_SKIP_COMPRESS};
  CompressionSuffixes compression_suffixes;
  enum ProgressMode { Display, Progress2, Json } progress_mode = Display;
  int human = 0;
  std::string rsh, rsync_path;
  bool rsh_set = false;  // Client-only; an explicit empty command is an error.
  bool whole_file = false;  // Client controls resume feature negotiation.
  std::string out_format, log_file;
  bool out_format_set = false;  // An explicitly empty format suppresses file lines.
  bool raw_names = false;  // -8: retain invalid high bytes; escape unsafe control bytes.
  int itemize_level = 0;
  bool output_attrs = false, output_unchanged = false;  // Configured before workers start.
  bool acls = false;  // Outside the frozen v3 options.
  int atimes = 0;
  bool executability = false;
  bool fileflags = false;  // Darwin st_flags, negotiated outside v3 options.
  std::vector<PermissionRule> chmod_rules;  // Client-side incoming modes; no wire-layout change.
  OwnershipOverride ownership;  // Resolved on the destination host.
  bool crtimes = false, open_noatime = false;  // Negotiated outside v3 options.
  int xattrs = 0;  // 1: ordinary attributes; 2: include rsync internal attributes.
  bool hard_links = false;  // Negotiated separately from the frozen v3 options.
  bool sparse = false;  // Receiver allocation policy; outside the frozen v3 options.
  std::vector<std::string> link_dest;  // Receiver-local snapshot bases.
  bool delete_before = false;  // Deletion is still deferred for sender-read safety.
  bool delete_after = false;   // Scan extras and merge files after transfers finish.
  bool prune_empty = false;   // Receiver file-list pruning; outside the frozen hello.
  bool from0 = false;         // NUL-delimited list/merge files, outside the frozen hello.
  bool relative = false;      // Source path selection, outside the frozen hello.
  bool files_from_set = false, files_from_loaded = false;
  std::string files_from;
  std::vector<std::string> file_names;
  std::shared_ptr<const FileListRequests> file_requests;
  bool cvs_exclude = false;  // Added at the end of explicit rules, outside the frozen hello.
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
inline bool metadata_enabled() { return g_opt.xattrs || g_opt.acls; }
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
  u32 basis_mode = 0;  // Receiver-only original regular-file mode for -E refreshes.
  u32 fileflags = 0;
  u32 uid = 0, gid = 0, mtime_ns = 0, rdev = 0, dev = 0;
  i64 size = 0, mtime = 0;
  u64 hdev = 0, ino = 0, nlink = 0;
  i64 ctime = 0;
  u32 ctime_ns = 0;
  i64 atime = 0, crtime = 0;  // rsync transports these in whole seconds.
  u8 time_flags = 0;  // Compared access/create times; itemization slot 8.
  bool fileflags_differ = false;
  bool access_acl_differ = false;  // POSIX metadata-only itemization of mode-linked ACL writes.
  u8 link_basis = 255;  // Receiver-only alternate directory used for comparison/delta.
};
enum : u8 { IF_PERMS = 1, IF_OWNER = 2, IF_GROUP = 4, IF_NEW_TYPE = 8, IF_PRUNED = 16, IF_SELECTED_CHILD = 32, IF_XATTR = 64, IF_ACL = 128 };

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
  std::atomic<u64> acknowledged_bytes{0}, acknowledged_files{0};
  std::atomic<u64> receiver_completed_bytes{0};  // Published files, separate from read/staged bytes.
  std::atomic<u64> compression_raw{0}, compression_wire{0};
  std::atomic<u64> read_ns{0}, network_ns{0}, write_ns{0};
  std::atomic<u64> peer_read_ns{0}, peer_network_ns{0}, peer_write_ns{0};
  std::atomic<bool> receiver_done{false};
  std::atomic<u32> deleting_active{0}, verifying_active{0}, peer_phase{0};
  std::atomic<u32> metadata_active{0};
  std::atomic<u32> conflict_active{0};
  std::atomic<u64> verified{0}, peer_verified{0}, peer_deleted{0};
  std::atomic<bool> waiting_peer{false};
  std::atomic<u64> delta_files{0}, delta_literal_bytes{0}, delta_matched_bytes{0};
  std::atomic<u64> cloned_dirs{0}, clone_dirs_total{0};  // Local whole-directory clones.
  std::atomic<bool> scan_done{false};
};
extern Stats g_stats;
extern std::atomic<int> g_exit_code;
extern std::atomic<int> g_stop;
extern std::atomic<bool> g_source_io_error;

// ---------------------------------------------------------------- messages

// Informational line on stdout (file names, itemized changes). No trailing newline in `s`.
void out_line(std::string_view s);
// Error/warning on stderr, prefixed "xs: ". code > 0 is recorded as the exit status.
void err_line(int code, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
void print_error_summary();
[[noreturn]] void die(int code, const char* fmt, ...) __attribute__((format(printf, 2, 3)));
[[noreturn]] void exit_signal();
// When set (server mode) messages are routed here instead of the terminal. kind: 0=out 1=err.
extern void (*g_msg_sink)(int kind, int code, std::string_view s);
// Native filesystem errors, before human formatting; optional app event sink.
extern void (*g_fs_error_sink)(int error, std::string_view path, std::string_view operation);

// rsync exit codes
enum { RERR_SYNTAX = 1, RERR_PROTOCOL = 2, RERR_FILESELECT = 3, RERR_UNSUPPORTED = 4,
       RERR_STARTCLIENT = 5, RERR_FILEIO = 11, RERR_STREAMIO = 12, RERR_MESSAGEIO = 13, RERR_IPC = 14,
       RERR_SIGNAL = 20, RERR_PARTIAL = 23, RERR_VANISHED = 24, RERR_DEL_LIMIT = 25, RERR_TIMEOUT = 30, RERR_CMD_FAILED = 124,
       RERR_CMD_NOTFOUND = 127 };

// ---------------------------------------------------------------- helpers

u64 now_ns();
std::string fmt_num(u64 v);         // 1,234,567 (or human-readable with -h)
std::string fmt_size(double v);     // 12.3M
double human_base();               // 1000 by default/-h, 1024 with -hh.
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
