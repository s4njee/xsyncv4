#pragma once
#include "common.h"
#include <map>
#include <memory>
#include <functional>
#include <set>

// A selected logical directory can contain entries from different physical
// source directories. Each logical node is consumed exactly once by the walk.
struct SelectedDirectory {
  DirList list;
  std::vector<std::string> paths;
  std::vector<std::shared_ptr<const FilterList>> contexts;
  Entry attrs;
  std::string source;
  bool has_attrs = false, no_delete = true;
};
struct SelectedSource {
  std::map<std::string, SelectedDirectory, std::less<>> directories;
  SelectedDirectory take(std::string_view relative);
};

// Streaming framing keeps large lists independent of protocol frame limits.
struct FileListParser {
  bool from0, forwarded, overflow = false, discard_remainder = false;
  std::string record;
  std::vector<std::string>* names;
  FileListParser(bool nul, std::vector<std::string>* output, bool forwarding = false)
      : from0(nul), forwarded(forwarding), names(output) {}
  void feed(std::string_view bytes, bool final = false);
};
void read_file_chunks(const std::string& path, bool allow_stdin,
                      const std::function<void(std::string_view)>& consume, bool forwarded = false);
void load_local_file_list();

struct FileListRequests {
  std::set<std::string, std::less<>> exact, parents, roots;
  bool recursive = false, dirs = false;
  explicit FileListRequests(const Options& options);
  bool permits(std::string_view path, bool directory) const;
};
