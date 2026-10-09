#pragma once
#include "common.h"
#include <map>

// Names use Linux-style protocol namespaces on every OS. Source read failures
// remain distinguishable from an empty list, so they cannot erase attributes.
struct XattrSet {
  std::map<std::string, std::string, std::less<>> values;
  bool complete = true;
};
XattrSet source_xattrs(const std::string& path, u8 type, const FilterList& filters);
XattrSet source_fd_xattrs(int fd, const std::string& path, u8 type, const FilterList& filters);
bool xattrs_differ(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters);
bool apply_xattrs(const XattrSet& source, const std::string& path, u8 type, const FilterList& filters);
bool apply_fd_xattrs(const XattrSet& source, int fd, const std::string& path, u8 type, const FilterList& filters, bool fresh = false);
struct DirWork;
void collect_source_xattrs(DirWork& work);
