#include "listing.h"
#include "engine.h"
#include "output.h"
#include <algorithm>
#include <ctime>
#include <numeric>
#include <tuple>
#include <sys/stat.h>

namespace {
void count(const Entry& e) {
  switch (e.type) {
    case T_REG: g_stats.files_seen.fetch_add(1); g_stats.bytes_seen.fetch_add((u64)e.size); break;
    case T_DIR: g_stats.dirs_seen.fetch_add(1); break;
    case T_LNK: g_stats.links_seen.fetch_add(1); break;
    default: g_stats.specials_seen.fetch_add(1); break;
  }
}
}

bool listing_path_valid(std::string_view path) {
  if (path == ".") return true;
  if (path.empty() || path.size() > (1 << 20) || path.find('\0') != path.npos) return false;
  while (!path.empty()) {
    size_t slash = path.find('/');
    auto part = path.substr(0, slash);
    if (part.empty() || part == "." || part == "..") return false;
    if (slash == path.npos) return true;
    path.remove_prefix(slash + 1);
    if (path.empty()) return false;
  }
  return false;
}

void listing_output(const ListingEntry& item) {
  count(item.attrs);
  if (g_opt.quiet) return;
  const Entry& e = item.attrs;
  const char types[] = "?-dlpscb";
  std::string mode(10, '-');
  mode[0] = e.type <= T_BLK ? types[e.type] : '?';
  for (int i = 0; i < 9; ++i) if (e.mode & (1 << (8-i))) mode[i+1] = "rwx"[i%3];
  if (e.mode & S_ISUID) mode[3] = e.mode & S_IXUSR ? 's' : 'S';
  if (e.mode & S_ISGID) mode[6] = e.mode & S_IXGRP ? 's' : 'S';
  if (e.mode & S_ISVTX) mode[9] = e.mode & S_IXOTH ? 't' : 'T';
  std::string size = g_opt.human_ungrouped ? std::to_string(e.size) : fmt_num((u64)e.size);
  size_t width = g_opt.human_ungrouped ? 11 : 14;
  time_t seconds = (time_t)e.mtime;
  struct tm date;
  char time[64] = {};
  if ((i64)seconds != e.mtime || !localtime_r(&seconds, &date) || !strftime(time, sizeof time, "%Y/%m/%d %H:%M:%S", &date)) {
    err_line(RERR_PARTIAL, "cannot represent listing modification time for \"%s\"", item.path.c_str());
    return;
  }
  std::string line = mode + " " + std::string(width > size.size() ? width - size.size() : 0, ' ') + size + " " + time + " " + output_escape(item.path);
  if (e.type == T_LNK && g_opt.links) line += " -> " + output_escape(item.target);
  output_text(line + '\n');
}

int run_listing(const std::vector<std::string>& sources, const ListingSink& emit) {
  auto source_path = [](std::string_view path) {
    return g_opt.am_server && (g_opt.peer_features & PF_CVS_FILTERS) ? FilterList::absolute_path(path) : std::string();
  };
  Worker worker;
  RootList root;
  auto normalized = sources;
  for (auto& source : normalized)
    if (source == ".." || source.ends_with("/..")) source += '/';
  build_root(normalized, root, worker);
  worker.flush_log();
  if (root.has_attrs) emit({root.attrs, ".", "", source_path(root.attr_source)});
  struct Frame {
    DirList list;
    std::vector<std::string> paths;
    std::string base, rel;
    size_t index = 0;
    bool files_done = false;
    std::vector<std::shared_ptr<const FilterList>> contexts;
  };
  std::vector<Frame> stack;
  stack.push_back({std::move(root.list), std::move(root.src_paths), "", "", 0, false, std::move(root.source_contexts)});
  while (!stack.empty() && !g_stop.load()) {
    Frame& frame = stack.back();
    if (!frame.files_done) {
      for (size_t i = 0; i < frame.list.e.size(); ++i) {
        const Entry& e = frame.list.e[i];
        if (g_stop.load()) break;
        if (e.type != T_DIR) emit({e, rel_join(frame.rel, frame.list.name_sv(e)), e.type == T_LNK ? frame.list.link(e) : "",
                                  source_path(frame.paths.empty() ? path_join(frame.base, frame.list.name_sv(e)) : frame.paths[i])});
      }
      frame.files_done = true;
    }
    while (frame.index < frame.list.e.size() && frame.list.e[frame.index].type != T_DIR) ++frame.index;
    if (frame.index == frame.list.e.size()) { stack.pop_back(); continue; }
    size_t i = frame.index++;
    const Entry e = frame.list.e[i];
    std::string rel = rel_join(frame.rel, frame.list.name_sv(e));
    std::vector<std::tuple<std::string, Entry, std::shared_ptr<const FilterList>>> source_dirs;
    source_dirs.emplace_back(frame.paths.empty() ? path_join(frame.base, frame.list.name_sv(e)) : frame.paths[i], e,
                             frame.contexts.empty() ? nullptr : frame.contexts[i]);
    while (frame.index < frame.list.e.size() && frame.list.e[frame.index].type == T_DIR &&
           frame.list.name_sv(frame.list.e[frame.index]) == frame.list.name_sv(e)) {
      size_t next = frame.index++;
      source_dirs.emplace_back(frame.paths.empty() ? path_join(frame.base, frame.list.name_sv(e)) : frame.paths[next], frame.list.e[next],
                               frame.contexts.empty() ? nullptr : frame.contexts[next]);
    }
    emit({e, rel, "", source_path(std::get<0>(source_dirs.front()))});
    if (!g_opt.recursive) continue;
    Frame child;
    child.rel = rel;
    for (const auto& [source, attrs, inherited] : source_dirs) {
      if (attrs.rdev == 1) continue;
      DirList list;
      int error = list_dir(source.c_str(), list, g_opt.copy_links ? LD_FOLLOW : LD_LINKS);
      if (error || list.incomplete) {
        err_line(RERR_PARTIAL, "list source directory \"%s\": %s", source.c_str(), error ? errstr(error).c_str() : "incomplete source listing");
        if (error) continue;
      }
      auto context = directory_filters(inherited, source, false);
      prune_source(list, rel, attrs.dev, worker, nullptr, SourceGuard(), source, context.get());
      for (Entry item : list.e) {
        auto name = list.name_sv(item);
        child.paths.push_back(path_join(source, name));
        if (g_opt.filters.has_merges()) child.contexts.push_back(context);
        if (item.type == T_LNK) item.link_off = child.list.add_str(list.link(item));
        item.name_off = child.list.add_str(name);
        child.list.e.push_back(item);
      }
    }
    std::vector<size_t> order(child.list.e.size());
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) {
      return name_cmp(child.list.name_sv(child.list.e[a]), child.list.name_sv(child.list.e[b])) < 0;
    });
    auto entries = std::move(child.list.e);
    auto paths = std::move(child.paths);
    auto contexts = std::move(child.contexts);
    for (size_t index : order) {
      const Entry& item = entries[index];
      if (!child.list.e.empty() && child.list.name_sv(child.list.e.back()) == child.list.name_sv(item) &&
          !(child.list.e.back().type == T_DIR && item.type == T_DIR)) continue;
      child.list.e.push_back(item), child.paths.push_back(std::move(paths[index]));
      if (!contexts.empty()) child.contexts.push_back(std::move(contexts[index]));
    }
    worker.flush_log();
    stack.push_back(std::move(child));
  }
  g_stats.scan_done.store(true);
  return g_stop.load() ? RERR_SIGNAL : g_exit_code.load();
}
