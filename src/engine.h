// Entry points of the sync engines and the pieces they share.
#pragma once
#include "fs.h"
#include "pool.h"

// The top-level listing built from the SRC arguments: directories given with a trailing slash
// contribute their contents, everything else contributes itself.
struct RootList {
  DirList list;
  std::vector<std::string> src_paths;  // parallel to list.e
  Entry attrs;                         // attributes for the destination directory itself
  bool has_attrs = false;
  bool single = false;                 // exactly one non-directory source argument
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
// Drop entries the sender must not transfer (filtered, unsupported or unrequested types).
void prune_source(DirList& l, std::string_view rel, u32 parent_dev, Worker& t, std::vector<std::string>* paths = nullptr,
                  const SourceGuard& guard = SourceGuard(), std::string_view base = "");
// Resolve DEST for the root listing held in `root.src`; creates the directory when needed.
// Returns false when there is nothing to do.
bool setup_dest(const std::string& dest, DirWork& root, bool single);

int default_jobs();
// Drive the UI until the pool has finished; handles interruption.
void wait_pool(Pool& pool);

int run_local(const std::vector<std::string>& srcs, const std::string& dest);
int run_client(const std::vector<std::string>& srcs, const std::string& dest);
int run_server();
void print_summary(u64 t0);
