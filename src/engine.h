// Entry points of the sync engines and the pieces they share.
#pragma once
#include "fs.h"
#include "pool.h"
#include "selection.h"
#include <unordered_set>

// Pruning depends on file-list presence and global receiver protection, before
// transfer restrictions or per-directory receiver rules are applied.
struct EmptyDirectoryPruner {
  std::unordered_set<std::string> retained;
  void add(const Entry& entry, std::string path, std::string_view absolute);
  bool keep(std::string_view path) const { return retained.count(std::string(path)); }
};
void prune_empty_directories(const std::vector<DirWork*>& directories, std::string_view destination);

// The top-level listing built from the SRC arguments: directories given with a trailing slash
// contribute their contents, everything else contributes itself.
struct RootList {
  DirList list;
  std::vector<std::string> src_paths;  // parallel to list.e
  std::vector<std::shared_ptr<const FilterList>> source_contexts;
  Entry attrs;                         // attributes for the destination directory itself
  std::string attr_source;
  bool has_attrs = false;
  bool app_scan_failed = false;         // observed source listing failure, including partial listings
  bool single = false;                 // exactly one non-directory source argument
  bool no_delete = true;               // implied/partial parents do not own unlisted siblings
  std::shared_ptr<SelectedSource> selection;
};
// Immutable once scanning starts. Paths cover a destination not created yet;
// device/inode also catches aliases to an existing destination directory.
struct SourceGuard {
  std::string path;
  u64 dev = 0, ino = 0;
  bool subtree = false;
  explicit SourceGuard(const std::string& dest = "");
  void prepare(const std::vector<std::string>& sources);
  bool excludes(const std::string& source) const;
};
std::string machine_identity();
void build_root(const std::vector<std::string>& srcs, RootList& r, Worker& t, const SourceGuard& guard = SourceGuard());
void build_selected_root(const std::vector<std::string>& sources, RootList& root, Worker& worker, const SourceGuard& guard);
// Drop entries the sender must not transfer (filtered, unsupported or unrequested types).
void prune_source(DirList& l, std::string_view rel, u32 parent_dev, Worker& t, std::vector<std::string>* paths = nullptr,
                  const SourceGuard& guard = SourceGuard(), std::string_view base = "", const FilterList* filters = nullptr);
std::shared_ptr<const FilterList> directory_filters(const std::shared_ptr<const FilterList>& parent,
                                                   std::string_view path, bool receiver);
// Resolve DEST for the root listing held in `root.src`; creates the directory when needed.
// Returns false when there is nothing to do.
bool setup_dest(const std::string& dest, DirWork& root, bool single);

// Destination pools can apply a measured filesystem budget. Explicit -j wins.
int default_jobs(const std::string& destination = {});
// Drive the UI until the pool has finished; handles interruption.
void wait_pool(Pool& pool);

int run_local(const std::vector<std::string>& srcs, const std::string& dest);
struct AppStream {
  bool push;
  int read_fd, write_fd;  // Ownership passes to the engine; SSH lifetime stays with the adapter.
  std::function<void(std::string)> event;
  bool leased = false;
  bool recoverable = false;
  std::function<int()> receiver_preflight = {};
};
struct AppServer {
  bool receiving;
  std::vector<std::string> paths;
  std::function<int()> preflight;
  bool leased = false;
  bool recoverable = false;
  std::function<void(int)> finish = {};
};
int run_client(const std::vector<std::string>& srcs, const std::string& dest, u32 wire_version = PROTO_VERSION,
               const AppStream* app = nullptr);
int run_server(const AppServer* app = nullptr);
void send_app_event(std::string fields);
void send_app_control(std::string payload);
void cancel_remote_peer();
void print_summary(u64 t0);
