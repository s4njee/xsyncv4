#include "hardlink.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <map>
#include <optional>
#include <tuple>
#include <unordered_map>

namespace {
struct Member {
  std::string path, rel, parent, source, target;
  Entry attrs, before;
  bool existed = false, ready = false, restore_flags = false;
  u64 dest_dev = 0, dest_ino = 0;
  std::optional<OutputEvent> event;
};
std::mutex mutex;
std::unordered_map<std::string, Member> members;

std::string key(const DirWork& w, u32 i) { return path_join(w.dst_path, w.dst_name(i)); }
char kind(u8 type) { return type == T_REG ? 'f' : type == T_LNK ? 'L' : type == T_CHR || type == T_BLK ? 'D' : 'S'; }
bool matches(const Member& member, const struct stat& st) {
  Entry entry; entry_from_stat(st, entry);
  return member.dest_dev == (u64)st.st_dev && member.dest_ino == (u64)st.st_ino && entry.type == member.attrs.type;
}

// Pin both parents, make a temporary link, then verify the inode before publishing.
// linkat without AT_SYMLINK_FOLLOW links the symlink itself, never its referent.
bool publish(const Member& anchor, const Member& member) {
  DestPath from = destination_path(anchor.path), to = destination_path(member.path);
  if (from.fd < 0 || to.fd < 0) return false;
  struct stat source, target;
#ifdef __APPLE__
  int pin_flags = O_EVTONLY | O_CLOEXEC | O_NONBLOCK | (anchor.attrs.type == T_LNK ? O_SYMLINK : O_NOFOLLOW);
#else
  int pin_flags = O_PATH | O_CLOEXEC | O_NOFOLLOW;
#endif
  DestPath pinned(openat(from.fd, from.name.c_str(), pin_flags), {});
  if (pinned.fd < 0 || fstat(pinned.fd, &source) != 0 || !matches(anchor, source)) {
    errno = ESTALE; return false;
  }
  if (fstatat(to.fd, to.name.c_str(), &target, AT_SYMLINK_NOFOLLOW) != 0 || !matches(member, target)) {
    errno = ESTALE; return false;
  }
  std::string temp;
  for (unsigned attempt = 0; attempt < 100; ++attempt) {
    temp = ".xsync-hardlink-" + std::to_string(getpid()) + "-" + std::to_string(now_ns()) + "-" + std::to_string(attempt);
    if (linkat(from.fd, from.name.c_str(), to.fd, temp.c_str(), 0) == 0) break;
    if (errno != EEXIST || attempt == 99) return false;
  }
  struct stat linked;
  bool ok = fstatat(to.fd, temp.c_str(), &linked, AT_SYMLINK_NOFOLLOW) == 0 && matches(anchor, linked);
  if (ok) ok = fstatat(to.fd, to.name.c_str(), &target, AT_SYMLINK_NOFOLLOW) == 0 && matches(member, target);
  if (!ok) errno = ESTALE;
  if (ok) ok = renameat(to.fd, temp.c_str(), to.fd, to.name.c_str()) == 0;
  int error = errno;
  if (!ok) unlinkat(to.fd, temp.c_str(), 0);
  errno = error;
  return ok;
}

OutputEvent linked_event(const Member& member, const Member& anchor, bool already, bool shared_xattrs) {
  OutputEvent event = member.event.value_or(OutputEvent{});
  event.path = member.rel;
  event.source = member.source;
  event.type = member.attrs.type;
  event.size = member.attrs.size;
  event.target = already ? member.target : anchor.rel;
  event.hardlink_target = !already;
  if (!member.existed || member.before.type != member.attrs.type) event.code = "hf+++++++++";
  else if (event.code.empty()) event.code = ".f         ";
  if (already && g_opt.dry_run) {
    // No anchor metadata has been written yet. Retain the alias's planned
    // changes instead of replacing them with the post-write shared-inode row.
    event.code = item_code(event.code.c_str(), member.attrs);
    event.code[0] = 'h';
    event.code[1] = kind(member.attrs.type);
    return event;
  }
  if (already) event.code = shared_xattrs ? "hf........x" : "hf         ";
  event.code = item_code(event.code.c_str(), member.attrs);
  event.code[0] = 'h';
  event.code[1] = kind(member.attrs.type);
  // The alias inherits these attributes from the completed anchor. rsync
  // itemizes their writes on the anchor, not again on the published hard link.
  if (event.code[9] == 'a') event.code[9] = '.';
  if (!shared_xattrs && event.code[10] == 'x') event.code[10] = '.';
  if (event.code.size() == 12 && event.code[11] == 'f') event.code[11] = '.';
  if (event.code[8] == 'n') event.code[8] = '.';
  else if (event.code[8] == 'b') event.code[8] = 'u';
  return event;
}
}

bool hardlink_participant(const DirWork& w, u32 index) {
  if (!g_opt.hard_links) return false;
  std::lock_guard<std::mutex> lock(mutex);
  return members.contains(key(w, index));
}

void hardlink_prepare(DirWork& w, u32 index, const Entry* before) {
  const Entry& entry = w.src.e[index];
  if (!g_opt.hard_links || entry.nlink < 2 || entry.type == T_DIR || entry.type == T_NONE) return;
  Member member;
  member.path = key(w, index);
  member.parent = w.dst_path;
  member.rel = rel_join(w.rel, w.src.name_sv(entry));
  member.attrs = entry;
  if (before) member.before = *before, member.existed = true;
  if (!w.output_sources.empty()) member.source = w.output_sources[index];
  else src_path_of(w, index, member.source);
  if (entry.type == T_LNK) member.target = w.src.link(entry);
  std::lock_guard<std::mutex> lock(mutex);
  members.emplace(member.path, std::move(member));
}

void hardlink_complete(DirWork& w, u32 index, const Entry& source, const struct stat* published, bool restore_flags) {
  if (!g_opt.hard_links) return;
  std::lock_guard<std::mutex> lock(mutex);
  auto it = members.find(key(w, index));
  if (it == members.end()) return;
  Member& member = it->second;
  member.attrs = source;
  member.restore_flags = restore_flags;
  if (!g_opt.dry_run) {
    struct stat st;
    if (!published) {
      if (destination_stat(member.path.c_str(), &st) != 0) return;
      published = &st;
    }
    Entry dest; entry_from_stat(*published, dest);
    if (dest.type != source.type) return;
    member.dest_dev = published->st_dev, member.dest_ino = published->st_ino;
  }
  member.ready = true;
}

bool hardlink_defer(DirWork& w, u32 index, OutputEvent event) {
  if (!g_opt.hard_links) return false;
  std::lock_guard<std::mutex> lock(mutex);
  auto it = members.find(key(w, index));
  if (it == members.end()) return false;
  it->second.event = std::move(event);
  return true;
}

std::vector<std::string> hardlink_finalize() {
  std::vector<std::string> dirty;
  using Identity = std::tuple<u64, u64, u8, i64, i64, u32, i64, u32, std::string>;
  std::map<Identity, std::vector<Member*>> groups;
  for (auto& [path, member] : members) {
    if (!member.ready) continue;
    const Entry& a = member.attrs;
    groups[{a.hdev, a.ino, a.type, a.size, a.mtime, a.mtime_ns, a.ctime, a.ctime_ns, member.target}].push_back(&member);
  }
  for (auto& [identity, group] : groups) {
    std::sort(group.begin(), group.end(), [](const auto* a, const auto* b) {
      auto dir = [](const std::string& path) { size_t slash = path.rfind('/'); return slash == std::string::npos ? std::string() : path.substr(0, slash); };
      return std::pair(dir(a->rel), a->rel) < std::pair(dir(b->rel), b->rel);
    });
    Member* anchor = group.front();
    if (anchor->attrs.type == T_REG) anchor = group.back();
    for (Member* member : group) if (member->existed && member->before.type == member->attrs.type) { anchor = member; break; }
    if (anchor->event) output_event(*anchor->event);
    for (Member* member : group) {
      if (member == anchor) continue;
      bool original = member->existed && anchor->existed && member->before.hdev == anchor->before.hdev && member->before.ino == anchor->before.ino;
      bool linked = !g_opt.dry_run && member->dest_dev == anchor->dest_dev && member->dest_ino == anchor->dest_ino;
      bool transferred = member->event && (member->event->code.starts_with(">") || member->event->code.starts_with("<"));
      bool already = original && (g_opt.dry_run ? (g_opt.inplace || !transferred) : linked);
      if (!linked && !g_opt.dry_run) {
        if (!publish(*anchor, *member)) {
          file_io_error(errno, member->path.c_str(), "hard link");
          if (member->event) output_event(*member->event);
          continue;
        }
        dirty.push_back(member->parent);
      }
      // rsync also reports already-linked aliases when a metadata-only anchor
      // changed xattrs. The aliases share the write even without a new link.
      bool shared_xattrs = already && anchor->event && anchor->event->code[0] == '.' && anchor->event->code[10] == 'x';
      bool preview_attrs = already && g_opt.dry_run && member->event &&
                           member->event->code.find_first_not_of(". ", 2) != std::string::npos;
      if (!already || shared_xattrs || preview_attrs || g_opt.output_unchanged)
        output_event(linked_event(*member, *anchor, already, shared_xattrs));
    }
    if ((g_opt.fileflags || anchor->restore_flags) && !g_opt.dry_run && anchor->attrs.type != T_LNK)
      check_attr(destination_fileflags(anchor->path.c_str(), anchor->attrs.fileflags, false,
                                      anchor->dest_dev, anchor->dest_ino), anchor->path.c_str(), "file flags");
  }
  members.clear();
  return dirty;
}
