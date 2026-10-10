// Filesystem primitives and the receiver-side "generator" shared by local and remote sync.
#pragma once
#include <mutex>
#include <memory>

#include "common.h"
#include "destination.h"
#include "xattrs.h"

struct stat;
struct SelectedSource;

// Per-thread scratch state.
struct Worker {
  int id = 0;
  u64 deleted_entries = 0; // Per-worker count, also detects partial subtree changes.
  std::vector<char> buf;  // file data buffer
  DirList dl;             // destination listing scratch
  std::string p1, p2;     // path scratch
  std::string log;        // pending out_line text (flushed in batches)
  u64 rng = 0;
  void* zc = nullptr;     // ZSTD_CCtx
  void* zd = nullptr;     // ZSTD_DCtx
  std::string block;      // sender: pending data records
  u32 block_files = 0;
  bool block_raw = false; // File suffix policy isolates raw DATA blocks.
  void flush_log();
  void logf(std::string_view s) {
    log.append(s);
    log.push_back('\n');
    if (log.size() > 8192) flush_log();
  }
};

enum { LD_LINKS = 1, LD_FOLLOW = 2, LD_SUMS = 4 };
// List a directory with attributes (sorted by name). Returns 0 or errno.
int list_dir(const char* path, DirList& out, unsigned flags);
int destination_list_dir(const char* path, DirList& out, unsigned flags);
void entry_from_stat(const struct stat& st, Entry& e);
bool same_entry_time(const Entry& source, const Entry& destination, bool exact = false);
u32 execution_mode(u32 source, u32 destination);
Entry source_snapshot(const Entry& scanned, const struct stat& st, bool receiver = true);
bool source_unchanged(int fd, const std::string& path, const struct stat& before);
std::string item_code(const char* code, const Entry& entry);
void set_fileflags(const char* path, const Entry& entry);
bool hash_file(const char* path, u64 out[2]);
bool destination_hash_file(const char* path, u64 out[2]);
struct ResumePrefix {
  i64 size = 0;
  u64 sum[2] = {};
};
bool hash_prefix_fd(int fd, i64 size, u64 out[2]);
ResumePrefix destination_resume_prefix(const char* path, i64 limit);

struct ReceiverFilterNode {
  std::string path;
  std::shared_ptr<const ReceiverFilterNode> parent;
  bool load;
};

// One directory being synchronised, as seen from the destination side.
struct DirWork {
  std::string dst_path;  // destination directory
  std::string rel;       // path relative to the transfer root ("" for the root)
  std::string src_path;  // local mode: source directory
  std::vector<std::string> src_paths;  // per-entry source path (root listing only)
  std::vector<std::shared_ptr<const FilterList>> source_contexts;
  std::shared_ptr<const FilterList> source_filter, receiver_filter;
  std::shared_ptr<const ReceiverFilterNode> receiver_filter_node;
  std::vector<std::string> output_sources;  // Display-only paths supplied by a remote sender.
  std::string attr_source;  // Display-only source path for this directory's attributes.
  DirList src;           // source entries, sorted by name
  std::vector<std::unique_ptr<DirWork>> prepared_children;  // Full source walk for -m.
  std::shared_ptr<SelectedSource> selection;
  bool scan_failed = false, file_ranges = true;
  XattrSet attrs_xattrs;
  std::vector<XattrSet> src_xattrs;  // Parallel to the filtered source entries.
  bool xattrs_loaded = false, attrs_xattrs_loaded = false;
  Entry attrs;           // source directory attributes
  bool has_attrs = false;
  bool created = false;   // destination directory was just created: nothing to compare against
  bool mode_ok = false, time_ok = false;
  bool directory_reported = false;
  bool no_delete = false;
  bool lazy_children = false;  // leave creating new subdirectories to their own sync step
  bool lazy = false;           // this directory still has to be created
  DirWork* waiter = nullptr;   // parent that must not be finished before we exist
  std::atomic<bool> modified{false};
  std::string rename_to;  // single-file transfer to an explicit destination name
  std::vector<u32> need;  // indices of regular files that must be transferred
  std::atomic<int> pending{0};
  u32 dgid = 0;  // group new children of the destination directory get

  const char* dst_name(u32 i) const { return rename_to.empty() ? src.name(src.e[i]) : rename_to.c_str(); }
};

// Compare `w.src` against the destination directory: create directories, symlinks and
// specials, fix attributes of up-to-date files, delete extraneous entries, and collect the
// regular files that need their data transferred into `w.need`.
void generate(DirWork& w, Worker& t);
void reject_name_collisions(DirWork& w);
void skip_unsafe_links(DirWork& w, Worker& t);
// Apply final directory attributes once everything inside is in place.
void finish_dir(DirWork& w);
// Delete extras only after all sender reads succeeded, then restore directories.
void finalize_tree();

// Destination file being written.
struct OutputProgress;
struct OutFile {
  int fd = -1;
  int dir_fd = -1;
  bool temp = false;
  bool existed = false;
  u32 created_mode = 0;
  bool basis_identity = false;
  u32 basis_uid = 0, basis_gid = 0;  // Original destination for fresh-source itemization.
  bool cloned_flags = false;
  u32 clone_fileflags = 0;
  i64 size = -1;  // final length when known (needed to truncate --inplace updates)
  i64 sparse_size_hint = 0;
  bool sparse_prepared = false;
  std::string path, tmp;
  std::string name, tmp_name;
  std::shared_ptr<OutputProgress> progress;
};
bool out_open(OutFile& f, DirWork& w, u32 idx, Worker& t, bool force_temp = false, bool readable = false);
bool out_finish(OutFile& f, DirWork& w, u32 idx, Worker& t, bool ok, const Entry* attrs = nullptr, const XattrSet* xattrs = nullptr);
void out_abort(OutFile& f, bool keep_partial = false);
void cleanup_open_outputs();
bool out_write(OutFile& f, const char* bytes, size_t size, i64 offset);
bool out_restore_prefix(OutFile& f, const ResumePrefix& prefix);
// Kernel operations require a non-sparse output and bypass bandwidth limiting.
// Clone callers must provide an empty private/new output, never an existing inode.
int out_clone_data(OutFile& f, int source, i64 size); // 1 copied, 0 unsupported, -1 error
ssize_t out_copy_range(OutFile& f, int source, size_t size, i64 offset);
bool native_copy_ranges(int source, int destination);
void large_file_cache_policy(int fd, i64 size);
bool parallel_file_ranges(const DirList& list, const std::vector<u32>& needed);
bool clone_copy(DirWork& w, u32 idx, const char* source, unsigned flags, Worker& t);
// Whole small file from memory.
bool write_whole(DirWork& w, u32 idx, const char* data, size_t len, Worker& t);
// Report a completed transfer (-v / -i output and counters).
void note_transferred(DirWork& w, u32 idx, i64 bytes, Worker& t, i64 final_size = -1);
void note_item(DirWork& w, u32 idx, const char* code, i64 bytes, Worker& t, i64 size = -1);
void note_directory(DirWork& w, const Entry* before, bool created, Worker& t, bool alternate = false);

void src_path_of(const DirWork& w, u32 i, std::string& out);
bool write_all(int fd, const char* p, size_t n);
std::string errstr(int e);
bool check_attr(int result, const char* path, const char* attribute);
void file_io_error(int error, const char* path, const char* operation);
void init_ids();
bool can_set_gid(u32 gid);
int read_time_flags();
bool preserve_atime(const Entry& entry);
bool preserve_crtime(const Entry& entry);
char extra_time_code(const Entry& source, const Entry& dest);
