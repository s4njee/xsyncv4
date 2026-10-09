#pragma once
#include "common.h"
#include <map>
#include <memory>

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
