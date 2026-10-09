#include "engine.h"
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <climits>
#include <deque>

SelectedDirectory SelectedSource::take(std::string_view relative) {
  auto found = directories.find(relative);
  if (found == directories.end()) die(RERR_PROTOCOL, "missing selected source directory: %s", std::string(relative).c_str());
  return std::move(found->second);
}

namespace {
struct Item {
  Entry attrs;
  std::string source, target;
  std::shared_ptr<const FilterList> context;
};
struct Directory {
  std::map<std::string, Item, std::less<>> entries;
  Entry attrs;
  std::string source;
  bool has_attrs = false, no_delete = true;
};
struct Scan {
  std::string logical, physical;
  Entry attrs;
  std::shared_ptr<const FilterList> context;
  bool recursive;
};

// The first /./ separates the physical source prefix from transmitted paths.
// Absolute paths lose their leading slash. Dot-dot is only allowed in the
// physical prefix; it can never become a receiver path component.
struct RelativePath {
  std::string base, logical, physical;
  bool contents = false, leading_dot = false, cut_prefix = false;
  explicit RelativePath(const std::string& argument) {
    contents = argument.empty() || argument == "." || argument.ends_with('/') || argument.ends_with("/.");
    std::string text = argument.empty() ? "." : argument;
    size_t cut = text.starts_with("./") ? 0 : text.find("/./");
    leading_dot = cut == 0;
    cut_prefix = cut != text.npos;
    if (cut != text.npos) {
      base = cut ? text.substr(0, cut) : ".";
      text.erase(0, cut + (cut ? 3 : 2));
    } else base = text.starts_with('/') ? "/" : ".";
    size_t start = 0;
    while (start <= text.size()) {
      size_t end = text.find('/', start);
      std::string part = text.substr(start, end == text.npos ? end : end - start);
      if (part == "..") die(RERR_SYNTAX, "found \"..\" dir in relative path: %s", argument.c_str());
      if (!part.empty() && part != ".") logical = rel_join(logical, part);
      if (end == text.npos) break;
      start = end + 1;
    }
    auto physical_base = cut_prefix ? path_join(base, ".") : base;
    physical = logical.empty() ? physical_base : path_join(physical_base, logical);
  }
};

bool read_entry(const std::string& path, bool follow, Entry& entry, std::string& target) {
  struct stat st;
  if ((follow ? stat(path.c_str(), &st) : lstat(path.c_str(), &st)) != 0) {
    g_source_io_error.store(true);
    err_line(RERR_PARTIAL, "link_stat \"%s\" failed: %s", path.c_str(), errstr(errno).c_str());
    return false;
  }
  entry_from_stat(st, entry);
  if (entry.type == T_LNK && (g_opt.links || g_opt.list_only)) {
    char buffer[PATH_MAX];
    ssize_t length = readlink(path.c_str(), buffer, sizeof buffer);
    if (length < 0) {
      g_source_io_error.store(true);
      err_line(RERR_PARTIAL, "readlink \"%s\" failed: %s", path.c_str(), errstr(errno).c_str());
      return false;
    }
    target.assign(buffer, (size_t)length);
  }
  return true;
}

void add_item(Directory& directory, const std::string& name, Item item) {
  auto [position, added] = directory.entries.try_emplace(name, std::move(item));
  // A requested descendant makes its implied parent a real directory, even
  // when another source argument explicitly selected the symlink at that name.
  if (!added && position->second.attrs.type != T_DIR && item.attrs.type == T_DIR)
    position->second = std::move(item);
}
}

void build_selected_root(const std::vector<std::string>& sources, RootList& root, Worker& worker, const SourceGuard& guard) {
  const auto& options = g_opt;
  std::map<std::string, Directory, std::less<>> directories;
  directories[""];
  std::deque<Scan> scans;
  bool any_contents = false;
  for (const auto& argument : sources) {
    RelativePath path(argument);
    Entry entry;
    std::string target;
    if (!read_entry(path.physical, options.copy_links || path.contents, entry, target)) continue;
    if (entry.type == T_DIR && !options.recursive && !options.dirs) {
      if (!options.quiet) worker.logf("skipping directory " + (path.logical.empty() ? "." : path.logical));
      continue;
    }
    auto absolute = options.filters.has_absolute() ? FilterList::absolute_path(path.physical) : "";
    // Explicit source selection bypasses filters on implied ancestors. A
    // globally excluded explicit leaf does not introduce those ancestors.
    if (!path.logical.empty() && options.filters.excluded(path.logical, entry.type == T_DIR, absolute)) continue;
    if (entry.type == T_DIR && guard.excludes(path.physical)) {
      err_line(RERR_FILESELECT, "source directory is inside the destination: \"%s\"", path.physical.c_str());
      continue;
    }
    auto context = directory_filters({}, path.base, false);
    if (path.leading_dot && (options.recursive || options.dirs)) {
      auto& top = directories[""];
      std::string ignored;
      if (!top.has_attrs && read_entry(path.base, true, top.attrs, ignored)) {
        top.has_attrs = true;
        top.source = path_join(path.base, ".");
      }
    }
    std::string logical, physical = path.cut_prefix ? path_join(path.base, ".") : path.base;
    size_t start = 0;
    while (start < path.logical.size()) {
      size_t slash = path.logical.find('/', start);
      if (slash == path.logical.npos) break;
      std::string name = path.logical.substr(start, slash - start);
      physical = path_join(physical, name);
      Entry implied;
      std::string ignored;
      if (!read_entry(physical, true, implied, ignored) || implied.type != T_DIR) break;
      implied.item_flags |= IF_SELECTED_CHILD;
      add_item(directories[logical], name, {implied, physical, "", context});
      logical = rel_join(logical, name);
      auto& directory = directories[logical];
      if (!directory.has_attrs) directory.attrs = implied, directory.source = physical, directory.has_attrs = true;
      context = directory_filters(context, physical, false);
      start = slash + 1;
    }
    if (!path.logical.empty() && logical != path.logical.substr(0, path.logical.rfind('/') == path.logical.npos ? 0 : path.logical.rfind('/')))
      continue;
    std::string name = path.logical.substr(start);
    if (name.empty()) {
      auto& top = directories[""];
      if (!top.has_attrs) top.attrs = entry, top.source = path_join(path.physical, "."), top.has_attrs = true;
      any_contents = true;
      scans.push_back({"", path.physical, entry, context, options.recursive});
      continue;
    }
    DirList one;
    entry.name_off = one.add_str(name);
    entry.name_len = (u16)name.size();
    if (entry.type == T_LNK) entry.link_off = one.add_str(target);
    one.e.push_back(entry);
    prune_source(one, logical, 0, worker, nullptr, guard,
                 path.logical.find('/') == path.logical.npos ? path.base : physical, context.get());
    if (one.e.empty()) continue;
    entry = one.e.front();
    if (entry.type == T_DIR) {
      entry.item_flags |= IF_SELECTED_CHILD;
      auto& directory = directories[path.logical];
      if (!directory.has_attrs) directory.attrs = entry, directory.source = path.physical, directory.has_attrs = true;
      if (options.recursive || path.contents) scans.push_back({path.logical, path.physical, entry, context, options.recursive});
    }
    add_item(directories[logical], name, {entry, path.physical, target, context});
    any_contents |= path.contents;
  }
  while (!scans.empty() && !g_stop.load()) {
    auto scan = std::move(scans.front());
    scans.pop_front();
    auto context = directory_filters(scan.context, scan.physical, false);
    DirList list;
    int error = list_dir(scan.physical.c_str(), list, options.copy_links ? LD_FOLLOW : options.links || options.list_only ? LD_LINKS : 0);
    auto& directory = directories[scan.logical];
    if (error || list.incomplete) {
      g_source_io_error.store(true);
      err_line(RERR_PARTIAL, "list source directory \"%s\": %s", scan.physical.c_str(),
               error ? errstr(error).c_str() : "incomplete source listing");
    } else directory.no_delete = false;
    prune_source(list, scan.logical, scan.attrs.dev, worker, nullptr, guard, scan.physical, context.get());
    for (Entry entry : list.e) {
      std::string name(list.name_sv(entry)), physical = path_join(scan.physical, name);
      if (entry.type == T_DIR) {
        auto logical = rel_join(scan.logical, name);
        entry.item_flags |= IF_SELECTED_CHILD;
        auto& child = directories[logical];
        if (!child.has_attrs) child.attrs = entry, child.source = physical, child.has_attrs = true;
        if (scan.recursive && entry.rdev != 1) scans.push_back({logical, physical, entry, context, true});
      }
      add_item(directory, name, {entry, physical, entry.type == T_LNK ? list.link(entry) : "", context});
    }
  }
  root.selection = std::make_shared<SelectedSource>();
  for (auto& [logical, directory] : directories) {
    auto& output = root.selection->directories[logical];
    output.attrs = directory.attrs;
    output.source = std::move(directory.source);
    output.has_attrs = directory.has_attrs;
    output.no_delete = directory.no_delete;
    for (auto& [name, item] : directory.entries) {
      Entry entry = item.attrs;
      entry.name_off = output.list.add_str(name);
      entry.name_len = (u16)name.size();
      if (entry.type == T_LNK) entry.link_off = output.list.add_str(item.target);
      output.list.e.push_back(entry);
      output.paths.push_back(std::move(item.source));
      output.contexts.push_back(std::move(item.context));
    }
  }
  auto top = root.selection->take("");
  root.list = std::move(top.list);
  root.src_paths = std::move(top.paths);
  root.source_contexts = std::move(top.contexts);
  root.attrs = top.attrs;
  root.attr_source = std::move(top.source);
  root.has_attrs = top.has_attrs;
  root.no_delete = top.no_delete;
  root.single = sources.size() == 1 && !any_contents && root.list.e.size() == 1 && root.list.e[0].type != T_DIR;
}
