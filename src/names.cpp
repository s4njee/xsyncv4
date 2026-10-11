// Destination filesystem name equivalence, checked before scheduling any writes.
#include "fs.h"

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <cctype>
#include <filesystem>
#include <unordered_map>
#include <unordered_set>

#include <unicode/uchar.h>
#include <unicode/unorm2.h>
#include <unicode/ustring.h>
#include <unicode/utf16.h>

#ifdef __APPLE__
#include <sys/attr.h>
#include <sys/mount.h>
#else
#include <linux/fs.h>
#include <sys/ioctl.h>
#include <sys/vfs.h>
#endif

namespace {
struct NameRules { bool fold = false, normalize = false, full_fold = true; };
std::mutex rules_mu;
std::unordered_map<std::string, NameRules> rule_cache;

NameRules destination_rules(const std::string& path) {
  std::string existing = path;
  struct stat st;
  while (destination_stat(existing.c_str(), &st) != 0) {
    std::string parent = std::filesystem::path(existing).parent_path().string();
    if (parent.empty()) parent = ".";
    if (parent == existing) return {};
    existing = std::move(parent);
  }
  int fd = destination_open_dir(existing.c_str());
  if (fd < 0) return {};
  NameRules rules;
#ifdef __APPLE__
  struct statfs fs;
  if (fstatfs(fd, &fs) != 0) { close(fd); return {}; }
  rules.normalize = strcmp(fs.f_fstypename, "apfs") == 0 || strcmp(fs.f_fstypename, "hfs") == 0;
  if (strcmp(fs.f_fstypename, "msdos") == 0 || strcmp(fs.f_fstypename, "exfat") == 0) rules.full_fold = false;
  attrlist al{};
  al.bitmapcount = ATTR_BIT_MAP_COUNT;
  al.volattr = ATTR_VOL_CAPABILITIES;
  struct { u32 length; vol_capabilities_attr_t caps; } result{};
  if (fgetattrlist(fd, &al, &result, sizeof result, 0) == 0 &&
      (result.caps.valid[VOL_CAPABILITIES_FORMAT] & VOL_CAP_FMT_CASE_SENSITIVE))
    rules.fold = !(result.caps.capabilities[VOL_CAPABILITIES_FORMAT] & VOL_CAP_FMT_CASE_SENSITIVE);
  close(fd);
  return rules;
#else
  unsigned flags = 0;
  if (ioctl(fd, FS_IOC_GETFLAGS, &flags) != 0) flags = 0;
  std::string key = std::to_string(st.st_dev) + ":" + std::to_string(flags & FS_CASEFOLD_FL);
  std::lock_guard<std::mutex> lock(rules_mu);
  auto found = rule_cache.find(key);
  if (found != rule_cache.end()) { close(fd); return found->second; }
  if (flags & FS_CASEFOLD_FL) rules.fold = rules.normalize = true;
  struct statfs fs{};
  if (fstatfs(fd, &fs) == 0 && (fs.f_type == 0x4d44 || fs.f_type == 0x2011BAB0)) rules.fold = true, rules.full_fold = false; // FAT/exFAT
  if (!g_opt.dry_run) {
    // Probe once per filesystem/casefold mode, without disturbing its directory time.
    static std::atomic<unsigned> sequence{0};
    std::string probe = ".xsync-nameprobe-a-\xc3\xa9-" + std::to_string(getpid()) + "-" + std::to_string(++sequence);
    int file = openat(fd, probe.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (file >= 0) {
      struct stat original, variant;
      if (fstat(file, &original) == 0) {
        std::string upper = probe;
        upper[upper.rfind("-a-") + 1] = 'A';
        rules.fold = fstatat(fd, upper.c_str(), &variant, AT_SYMLINK_NOFOLLOW) == 0 && variant.st_ino == original.st_ino && variant.st_dev == original.st_dev;
        std::string decomposed = probe;
        decomposed.replace(decomposed.rfind("\xc3\xa9"), 2, "e\xcc\x81");
        rules.normalize = fstatat(fd, decomposed.c_str(), &variant, AT_SYMLINK_NOFOLLOW) == 0 && variant.st_ino == original.st_ino && variant.st_dev == original.st_dev;
      }
      close(file);
      unlinkat(fd, probe.c_str(), 0);
      timespec times[2] = {{0, UTIME_OMIT}, st.st_mtim};
      check_attr(futimens(fd, times), existing.c_str(), "times after name probe");
    } else if (errno == ENOSPC || errno == EDQUOT) file_io_error(errno, existing.c_str(), "name probe");
  }
  close(fd);
  rule_cache[key] = rules;
  return rules;
#endif
}

std::string name_key(std::string_view name, NameRules rules) {
  UErrorCode error = U_ZERO_ERROR;
  std::vector<UChar> text(name.size() + 1);
  int32_t length = 0;
  u_strFromUTF8(text.data(), (int32_t)text.size(), &length, name.data(), (int32_t)name.size(), &error);
  if (U_FAILURE(error)) {
    // Invalid UTF-8 is still a valid byte name on Linux. Preserve its bytes.
    std::string key(name);
    if (rules.fold) for (char& c : key) if ((unsigned char)c < 128) c = (char)tolower((unsigned char)c);
    return "b" + key;
  }
  text.resize(length);
  if (rules.fold && rules.full_fold) {
    int32_t need = u_strFoldCase(nullptr, 0, text.data(), (int32_t)text.size(), U_FOLD_CASE_DEFAULT, &error);
    if (error == U_BUFFER_OVERFLOW_ERROR) error = U_ZERO_ERROR;
    std::vector<UChar> folded((size_t)need + 1);
    length = u_strFoldCase(folded.data(), (int32_t)folded.size(), text.data(), (int32_t)text.size(), U_FOLD_CASE_DEFAULT, &error);
    if (U_FAILURE(error)) die(RERR_FILEIO, "Unicode filename case folding failed");
    folded.resize(length);
    text = std::move(folded);
  } else if (rules.fold) {
    for (auto& character : text) character = (UChar)u_foldCase(character, U_FOLD_CASE_DEFAULT);
  }
  if (rules.normalize) {
    const UNormalizer2* normalizer = unorm2_getNFDInstance(&error);
    int32_t need = unorm2_normalize(normalizer, text.data(), (int32_t)text.size(), nullptr, 0, &error);
    if (error == U_BUFFER_OVERFLOW_ERROR) error = U_ZERO_ERROR;
    std::vector<UChar> normalized((size_t)need + 1);
    length = unorm2_normalize(normalizer, text.data(), (int32_t)text.size(), normalized.data(), (int32_t)normalized.size(), &error);
    if (U_FAILURE(error)) die(RERR_FILEIO, "Unicode filename normalization failed");
    normalized.resize(length);
    text = std::move(normalized);
  }
  // A binary UTF-16 key needs no conversion back to printable UTF-8.
  return "u" + std::string(reinterpret_cast<const char*>(text.data()), text.size() * sizeof(UChar));
}
}

void reject_name_collisions(DirWork& w) {
  if (g_app_conflict_plan) return;
  if (w.src.e.size() < 2 || !w.rename_to.empty()) return;
  NameRules rules = destination_rules(w.dst_path);
  if (!rules.fold && !rules.normalize) return;
  std::unordered_map<std::string, std::vector<u32>> names;
  for (u32 i = 0; i < w.src.e.size(); i++) {
    Entry& entry = w.src.e[i];
    if (entry.type == T_NONE || (entry.item_flags & IF_PRUNED)) continue;
    std::string_view name = w.src.name_sv(entry);
    auto& group = names[name_key(name, rules)];
    bool collision = false;
    std::unordered_set<std::string> reported;
    for (u32 previous : group) {
      std::string_view other = w.src.name_sv(w.src.e[previous]);
      if (name == other) continue; // duplicate directory arguments are deliberately merged
      if (reported.insert(std::string(other)).second)
        err_line(RERR_PARTIAL, "destination name collision: \"%s\" and \"%s\"", rel_join(w.rel, other).c_str(), rel_join(w.rel, name).c_str());
      w.src.e[previous].type = T_NONE;
      collision = true;
    }
    if (collision) entry.type = T_NONE, w.no_delete = true;
    group.push_back(i);
  }
}

bool destination_names_equivalent(const std::string& path, std::string_view a, std::string_view b) {
  if (a == b) return true;
  auto rules = destination_rules(path);
  return name_key(a, rules) == name_key(b, rules);
}
std::function<std::string(std::string_view)> destination_name_keyer(const std::string& path) {
  auto rules = destination_rules(path);
  return [rules](std::string_view name) { return name_key(name, rules); };
}
std::function<std::string(std::string_view)> observed_name_keyer(bool fold, bool normalize, bool full_fold) {
  return [rules = NameRules{fold,normalize,full_fold}](std::string_view name) { return name_key(name,rules); };
}
