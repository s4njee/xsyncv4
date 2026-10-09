#include "filter.h"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <system_error>
#include <utility>

namespace {

using uchar = unsigned char;
std::atomic<uint64_t> next_merge_id{1};

enum : int { kFalse = 0, kTrue = 1, kAbortAll = -1, kAbortToStarStar = -2 };

// ASCII-only, locale-independent. Returns -1 for an unknown class name.
int posix_class(std::string_view name, uchar c) {
  const bool lower = c >= 'a' && c <= 'z', upper = c >= 'A' && c <= 'Z';
  const bool digit = c >= '0' && c <= '9', graph = c > 32 && c < 127;
  if (name == "alnum") return lower || upper || digit;
  if (name == "alpha") return lower || upper;
  if (name == "blank") return c == ' ' || c == '\t';
  if (name == "cntrl") return c < 32 || c == 127;
  if (name == "digit") return digit;
  if (name == "graph") return graph;
  if (name == "lower") return lower;
  if (name == "print") return graph || c == ' ';
  if (name == "punct") return graph && !(lower || upper || digit);
  if (name == "space") return c == ' ' || (c >= '\t' && c <= '\r');
  if (name == "upper") return upper;
  if (name == "xdigit") return digit || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
  return -1;
}

// Port of rsync's lib/wildmatch.c dowild(), including its abort codes: kAbortAll means the text
// ran out (no later start can match), kAbortToStarStar means a '*' hit a '/' (only an enclosing
// "**" can recover).
int dowild(const uchar* p, const uchar* pe, const uchar* t, const uchar* te) {
  const auto at = [pe](const uchar* q) -> uchar { return q < pe ? *q : 0; };
  for (; p < pe; ++p, ++t) {
    uchar pc = *p;
    if (t == te && pc != '*') return kAbortAll;
    const uchar tc = t < te ? *t : 0;
    switch (pc) {
      case '\\':
        if (++p == pe) return kFalse;  // a trailing backslash matches nothing
        pc = *p;
        [[fallthrough]];
      default:
        if (tc != pc) return kFalse;
        continue;
      case '?':
        if (tc == '/') return kFalse;
        continue;
      case '*': {
        bool starstar = false;
        if (at(++p) == '*') {
          while (at(++p) == '*') {}
          starstar = true;
        }
        if (p == pe) return starstar || !std::memchr(t, '/', static_cast<size_t>(te - t));
        // When a plain char follows the star(s), skip text positions that cannot start a match.
        const uchar lit = *p != '?' && *p != '[' && *p != '\\' ? *p : 0;
        for (; t < te; ++t) {
          if (lit && *t != lit) {
            if (!starstar) {
              if (*t == '/') return kAbortToStarStar;
              continue;
            }
            t = static_cast<const uchar*>(std::memchr(t, lit, static_cast<size_t>(te - t)));
            if (!t) break;
          }
          const int m = dowild(p, pe, t, te);
          if (m != kFalse) {
            if (!starstar || m != kAbortToStarStar) return m;
          } else if (!starstar && *t == '/') {
            return kAbortToStarStar;
          }
        }
        return kAbortAll;
      }
      case '[': {
        pc = at(++p);
        const bool negated = pc == '!' || pc == '^';
        if (negated) pc = at(++p);
        uchar prev = 0;
        bool matched = false;
        do {  // do-while: a ']' right after the opening bracket is a literal member
          if (!pc) return kAbortAll;
          if (pc == '\\') {
            if (!(pc = at(++p))) return kAbortAll;
            if (tc == pc) matched = true;
          } else if (pc == '-' && prev && at(p + 1) && p[1] != ']') {
            pc = *++p;
            if (pc == '\\' && !(pc = at(++p))) return kAbortAll;
            if (tc <= pc && tc >= prev) matched = true;
            pc = 0;  // a range end cannot start another range
          } else if (pc == '[' && at(p + 1) == ':') {
            const uchar* s = p += 2;
            while (p < pe && *p != ']') ++p;
            if (p == pe) return kAbortAll;
            const ptrdiff_t len = p - s - 1;
            if (len < 0 || p[-1] != ':') {  // no ":]", so the '[' is an ordinary member
              p = s - 2;
              pc = '[';
              if (tc == pc) matched = true;
              continue;
            }
            const int in = posix_class({reinterpret_cast<const char*>(s), static_cast<size_t>(len)}, tc);
            if (in < 0) return kAbortAll;
            if (in) matched = true;
            pc = 0;
          } else if (tc == pc) {
            matched = true;
          }
        } while (prev = pc, (pc = at(++p)) != ']');
        if (matched == negated || tc == '/') return kFalse;
        continue;
      }
    }
  }
  return t == te ? kTrue : kFalse;
}

// where > 0: match against the last `where` path components (fails if there are fewer);
// where < 0: also retry after every '/'; where == 0: match at the start of the text only.
bool wildmatch(std::string_view pat, std::string_view text, int where) {
  const auto* p = reinterpret_cast<const uchar*>(pat.data());
  const uchar* pe = p + pat.size();
  const auto* t = reinterpret_cast<const uchar*>(text.data());
  const uchar* e = t + text.size();
  if (where > 0) {
    const uchar* s = e;
    while (s > t && !(s[-1] == '/' && --where == 0)) --s;
    if (s == t && where != 1) return false;
    t = s;
    where = 0;
  }
  int m = dowild(p, pe, t, e);
  if (where < 0) {
    while (m == kFalse || m == kAbortToStarStar) {
      t = static_cast<const uchar*>(std::memchr(t, '/', static_cast<size_t>(e - t)));
      if (!t) return false;
      m = dowild(p, pe, ++t, e);
    }
  }
  return m == kTrue;
}

void set_err(std::string* err, std::string msg) {
  if (err) *err = std::move(msg);
}

bool is_space(char c) { return c == ' ' || (c >= '\t' && c <= '\r'); }

}  // namespace

// Mirrors rsync's add_rule() classification and rule_matches() dispatch (exclude.c).
void FilterList::add_rule(std::string_view pat, bool include, bool negate) {
  Rule r;
  r.text = pat;
  r.include = include;
  r.prefix = include ? '+' : '-';
  r.negate = negate;
  if (negate) r.modifiers = "!";
  if (pat.size() > 1 && pat.back() == '/') {  // exactly one trailing slash is stripped
    pat.remove_suffix(1);
    r.dir_only = true;
  }
  const auto slashes = std::count(pat.begin(), pat.end(), '/');  // counts a leading '/' too
  const bool wild = pat.find_first_of("*[?") != pat.npos;
  const size_t ss = pat.find("**");
  const bool wild2 = ss != pat.npos;
  const bool anchored = !pat.empty() && pat.front() == '/';
  if (anchored) pat.remove_prefix(1);

  const auto plain = [](std::string_view s) { return s.find_first_of("*?[\\") == s.npos; };
  if (!slashes && !wild2) {
    if (!wild) {
      r.kind = Kind::NameLit;
    } else if (pat.front() == '*' && plain(pat.substr(1))) {
      r.kind = Kind::NameSuffix;
      pat.remove_prefix(1);
    } else if (pat.back() == '*' && plain(pat.substr(0, pat.size() - 1))) {
      r.kind = Kind::NamePrefix;
      pat.remove_suffix(1);
    } else {
      r.kind = Kind::NameWild;
    }
  } else if (!wild) {
    r.kind = anchored ? Kind::PathLit : Kind::PathLitTail;
  } else {
    r.kind = Kind::PathWild;
    r.lead_slash = ss == 0;  // lets "**/foo" match "foo" at the root
    r.trail_slash = wild2 && pat.ends_with("***");  // lets "dir/***" match "dir" itself
    r.where = anchored ? 0 : !wild2 ? static_cast<int>(slashes) + 1 : ss != 0 ? -1 : 0;
  }
  if (r.kind == Kind::NameWild || r.kind == Kind::PathWild) {
    // Plain chars before the first / after the last special char must match the text verbatim.
    // (']' counts as special so the tail can never start inside a character class.)
    r.tail = static_cast<uint32_t>(pat.size() - 1 - pat.find_last_of("*?[]\\"));
    if (r.kind == Kind::NameWild || anchored) r.head = static_cast<uint32_t>(pat.find_first_of("*?[\\"));
  }
  r.pat = pat;
  rules_.push_back(std::move(r));
}

// rsync's XFLG_OLD_PREFIXES parsing, used for --include/--exclude and the *-from files.
bool FilterList::add_old_style(std::string_view pat, bool include, std::string* err) {
  if (pat.empty()) return true;
  const std::string_view whole = pat;
  if (pat.starts_with("- ")) {
    include = false;
    pat.remove_prefix(2);
  } else if (pat.starts_with("+ ")) {
    include = true;
    pat.remove_prefix(2);
  } else if (pat == "!") {
    rules_.clear();
    cleared_ = true;
    return true;
  }
  if (pat.empty()) {
    set_err(err, "unexpected end of filter rule: " + std::string(whole));
    return false;
  }
  add_rule(pat, include, false);
  return true;
}

void FilterList::add_pattern(std::string_view pat, bool include) { add_old_style(pat, include, nullptr); }

// Port of rsync's parse_rule_tok() for command-line -f rules (no word splitting).
bool FilterList::add_filter(std::string_view rule, std::string* err, bool read_merge_files, bool allow_cvs) {
  if (rule.empty()) return true;
  const auto fail = [&](std::string what) {
    set_err(err, std::move(what) + ": " + std::string(rule));
    return false;
  };
  const auto at = [&](size_t i) { return i < rule.size() ? rule[i] : '\0'; };

  static constexpr struct { std::string_view name; char ch; } kWords[] = {
      {"clear", '!'}, {"dir-merge", ':'}, {"exclude", '-'}, {"hide", 'H'}, {"include", '+'},
      {"merge", '.'}, {"protect", 'P'},   {"risk", 'R'},    {"show", 'S'},
  };
  char ch = rule[0];
  size_t i = at(1) == ',' ? 1 : 0;  // index of the char before the modifiers / separator
  if (ch >= 'a' && ch <= 'z') {
    ch = 0;
    for (const auto& w : kWords) {
      if (!rule.starts_with(w.name)) continue;
      const char next = at(w.name.size());
      if (next == ',') i = w.name.size(), ch = w.ch;
      else if (!next || next == '_' || is_space(next)) i = w.name.size() - 1, ch = w.ch;
      break;
    }
  }
  switch (ch) {
    case '+': case '-': case '!': case 'H': case 'S': case 'P': case 'R': case '.': case ':': break;
    default: return fail("unknown filter rule");
  }

  bool negate = false;
  std::string modifiers;
  uint8_t sides = ch == 'H' || ch == 'S' ? 1 : ch == 'P' || ch == 'R' ? 2 : 0;
  const bool side_prefix = sides != 0;
  const bool merge = ch == '.' || ch == ':';
  bool no_prefix = false;
  if (ch != '!') {
    for (char m; (m = at(++i)) && m != ' ' && m != '_';) {
      if ((side_prefix && std::strchr("srC", m)) || (!merge && std::strchr("enw+-", m)) ||
          (merge && m == '!') || ((m == '+' || m == '-' || m == 'C') && no_prefix))
        return fail(std::string("invalid modifier '") + m + "' in filter rule");
      if (m == '+' || m == '-' || m == 'C') no_prefix = true;
      if (!std::strchr("!/sprxCenw+-", m)) {
        return fail(std::string(std::strchr("/Cenprswx", m) ? "unsupported" : "invalid") + " modifier '" + m +
                    "' in filter rule");
      }
      modifiers += m;
      if (m == '!') negate = true;
      if (m == 's') sides |= 1;
      if (m == 'r') sides |= 2;
    }
  }
  const std::string_view pat = rule.substr(std::min(i + 1, rule.size()));
  if (ch == '!') {
    if (!pat.empty()) return fail("'!' rule has trailing characters");
    rules_.clear();
    cleared_ = true;
    return true;
  }
  const bool cvs = modifiers.find('C') != std::string::npos;
  if (pat.empty() && !cvs) return fail("unexpected end of filter rule");
  if (cvs && !merge) {
    if (!allow_cvs) return fail("unnegotiated global CVS filter");
    Rule marker;
    marker.kind = Kind::Cvs;
    marker.prefix = ch;
    marker.include = ch == '+';
    marker.text = pat;
    marker.modifiers = modifiers;
    marker.sides = sides;
    marker.negate = negate;
    marker.absolute = modifiers.find('/') != modifiers.npos;
    marker.perishable = modifiers.find('p') != modifiers.npos;
    if (!defer_cvs_ && !load_cvs(marker, err)) return false;
    rules_.push_back(std::move(marker));
    return true;
  }
  if (merge) {
    if (ch == '.' && !read_merge_files) return fail("single-instance merge rules are not allowed on the wire");
    Rule spec;
    spec.kind = Kind::Merge;
    spec.merge_id = next_merge_id.fetch_add(1, std::memory_order_relaxed);
    spec.text = pat.empty() ? ".cvsignore" : std::string(pat);
    auto filename = std::filesystem::path(spec.text);
    if (!filename.is_absolute() && ch == '.' && !parse_scope_.empty())
      spec.text = (std::filesystem::path(parse_scope_) / filename).string();
    spec.prefix = ch;
    spec.modifiers = modifiers;
    spec.sides = sides;
    spec.absolute = modifiers.find('/') != std::string::npos;
    spec.perishable = modifiers.find('p') != std::string::npos;
    spec.xattr = modifiers.find('x') != std::string::npos;
    if (modifiers.find('e') != std::string::npos) {
      auto slash = spec.text.rfind('/');
      add_rule(slash == std::string::npos ? spec.text : spec.text.substr(slash + 1), false, false);
      spec.modifiers.erase(std::remove(spec.modifiers.begin(), spec.modifiers.end(), 'e'), spec.modifiers.end());
    }
    if (ch == '.') return load_merge(spec.text, spec, parse_scope_, err, false);
    trusts_sender_filters_ = true;
    if (!cvs_cache_) cvs_cache_ = std::make_shared<CvsCache>();
    rules_.push_back(std::move(spec));
    return true;
  }
  add_rule(pat, ch == '+' || ch == 'S' || ch == 'R', negate);
  Rule& added = rules_.back();
  added.prefix = ch;
  added.modifiers = std::move(modifiers);
  added.sides = sides;
  added.absolute = added.modifiers.find('/') != std::string::npos;
  added.perishable = added.modifiers.find('p') != std::string::npos;
  added.xattr = added.modifiers.find('x') != std::string::npos;
  return true;
}

bool FilterList::add_from_file(const std::string& path, bool include, std::string* err) {
  if (path.empty()) return true;
  const bool use_stdin = path == "-";
  std::FILE* fp = use_stdin ? stdin : std::fopen(path.c_str(), "rb");
  const auto io_fail = [&](const char* what) {
    const int e = errno;
    set_err(err, std::string(what) + (include ? " include file " : " exclude file ") + path + ": " +
                     std::generic_category().message(e));
    return false;
  };
  if (!fp) return io_fail("failed to open");

  // NUL mode preserves CR and LF as pattern bytes. Empty records and
  // records starting with ';' or '#' are skipped in either delimiter mode.
  // No whitespace is trimmed (rsync keeps it as part of the pattern).
  std::string line;
  bool ok = true;
  const auto flush = [&] {
    // In line mode rsync's parser stops at the first NUL in a record.
    const auto nul = line.find('\0');
    if (nul != line.npos) line.resize(nul);
    if (ok && !line.empty() && line[0] != ';' && line[0] != '#') ok = add_old_style(line, include, err);
    line.clear();
  };
  char buf[1 << 14];
  for (;;) {
    const size_t n = std::fread(buf, 1, sizeof buf, fp);
    for (size_t k = 0; k < n; ++k) {
      if (from0_ ? buf[k] == '\0' : buf[k] == '\n' || buf[k] == '\r') flush();
      else line += buf[k];
    }
    if (n == sizeof buf) continue;
    if (std::ferror(fp) && errno == EINTR) {
      std::clearerr(fp);
      continue;
    }
    break;
  }
  flush();
  const bool read_err = std::ferror(fp);
  if (read_err) io_fail("failed to read");
  if (!use_stdin) std::fclose(fp);
  return ok && !read_err;
}

bool FilterList::load_merge(const std::string& path, const Rule& defaults, std::string_view scope,
                            std::string* err, bool optional) {
  if (merge_depth_ >= 64) { set_err(err, "failed to read merge file " + path + ": nesting exceeds 64"); return false; }
  bool use_stdin = path == "-";
  std::FILE* fp = use_stdin ? stdin : std::fopen(path.c_str(), "rb");
  if (!fp) {
    if (optional) return true;
    set_err(err, "failed to open merge file " + path + ": " + std::generic_category().message(errno));
    return false;
  }
  std::string content;
  char buffer[16384];
  for (;;) {
    size_t count = std::fread(buffer, 1, sizeof buffer, fp);
    content.append(buffer, count);
    if (content.size() > 16 * 1024 * 1024) {
      if (!use_stdin) std::fclose(fp);
      set_err(err, "failed to read merge file " + path + ": size exceeds 16 MiB");
      return false;
    }
    if (count == sizeof buffer) continue;
    if (std::ferror(fp) && errno == EINTR) { std::clearerr(fp); continue; }
    break;
  }
  bool failed = std::ferror(fp);
  int read_error = errno;
  if (!use_stdin) std::fclose(fp);
  if (failed) {
    set_err(err, "failed to read merge file " + path + ": " + std::generic_category().message(read_error));
    return false;
  }
  return merge_content(content, defaults, scope, err);
}

bool FilterList::merge_content(std::string_view content, const Rule& defaults, std::string_view scope, std::string* err) {
  const bool cvs = defaults.modifiers.find('C') != std::string::npos;
  const bool words = cvs || defaults.modifiers.find('w') != std::string::npos;
  const bool no_prefix = cvs || defaults.modifiers.find_first_of("+-") != std::string::npos;
  auto consume = [&](std::string_view text) {
    text = text.substr(0, text.find('\0'));
    if (text.empty() || (!words && (text.front() == '#' || text.front() == ';'))) return true;
    FilterList entry;
    entry.from0_ = from0_;
    entry.merge_depth_ = merge_depth_ + 1;
    entry.parse_scope_ = scope;
    entry.cvs_cache_ = cvs_cache_;
    entry.directory_cvs_ = directory_cvs_;
    entry.receiver_cvs_ = receiver_cvs_;
    entry.defer_cvs_ = true;
    if (no_prefix && !(cvs && text == "!")) {
      entry.add_rule(text, defaults.include || defaults.modifiers.find('+') != std::string::npos, defaults.negate);
    } else if (!entry.add_filter(text, err)) return false;
    if (entry.cvs_cache_) cvs_cache_ = entry.cvs_cache_;
    trusts_sender_filters_ |= entry.trusts_sender_filters_;
    if (entry.cleared_) { rules_.clear(); cleared_ = true; }
    for (Rule& rule : entry.rules_) {
      if (defaults.sides && rule.sides) {
        set_err(err, "specified-side merge file contains specified-side filter: " + std::string(text));
        return false;
      }
      auto add_modifier = [&](char modifier) {
        if (rule.modifiers.find(modifier) == std::string::npos) rule.modifiers += modifier;
      };
      if (defaults.sides & 1) add_modifier('s');
      if (defaults.sides & 2) add_modifier('r');
      rule.sides |= defaults.sides;
      if (defaults.absolute) rule.absolute = true, add_modifier('/');
      if (defaults.negate) rule.negate = true, add_modifier('!');
      if (defaults.perishable) rule.perishable = true, add_modifier('p');
      if (defaults.xattr) rule.xattr = true, add_modifier('x');
      if (!scope.empty()) rule.scope = scope;
      if (rule.kind == Kind::Cvs && !rule.merged && !defer_cvs_ && !load_cvs(rule, err)) return false;
      rules_.push_back(std::move(rule));
    }
    return true;
  };
  std::string_view input(content);
  const auto separator = [&](char ch) { return is_space(ch) || (from0_ && ch == '\0'); };
  while (!input.empty()) {
    if (words) {
      while (!input.empty() && separator(input.front())) input.remove_prefix(1);
      if (input.empty()) break;
      size_t end = 0;
      while (end < input.size() && !separator(input[end])) ++end;
      std::string text(input.substr(0, end));
      input.remove_prefix(end);
      // Prefix and pattern have one syntactic separator even in word mode.
      if (!no_prefix && text != "!" && text != "clear" && text.find('_') == text.npos) {
        while (!input.empty() && is_space(input.front())) input.remove_prefix(1);
        size_t pattern_end = 0;
        while (pattern_end < input.size() && !separator(input[pattern_end])) ++pattern_end;
        if (pattern_end) text += ' ', text.append(input.substr(0, pattern_end));
        input.remove_prefix(pattern_end);
      }
      if (!consume(text)) return false;
    } else {
      size_t end = from0_ ? input.find('\0') : input.find_first_of("\r\n");
      if (!consume(input.substr(0, end))) return false;
      if (end == input.npos) break;
      input.remove_prefix(end + 1);
    }
  }
  return true;
}

bool FilterList::load_cvs(Rule& marker, std::string* err) {
  if (!cvs_cache_) cvs_cache_ = std::make_shared<CvsCache>();
  std::lock_guard<std::mutex> lock(cvs_cache_->mutex);
  auto& list = cvs_cache_->lists[directory_cvs_ && receiver_cvs_ ? 1 : 0];
  if (!list) {
    FilterList contents;
    contents.from0_ = from0_;
    Rule defaults = marker;
    defaults.xattr = false;  // CVS containers do not pass xattr defaults to children.
    defaults.perishable = true;
    // rsync's built-in CVS list; VCS directories have directory-only patterns.
    constexpr std::string_view patterns = "RCS SCCS CVS CVS.adm RCSLOG cvslog.* tags TAGS .make.state .nse_depinfo "
        "*~ #* .#* ,* _$* *$ *.old *.bak *.BAK *.orig *.rej .del-* *.a *.olb *.o *.obj *.so *.exe *.Z *.elc *.ln core "
        ".svn/ .git/ .hg/ .bzr/";
    if (!contents.merge_content(patterns, defaults, {}, err)) return false;
    defaults.perishable = marker.perishable;
    if (const char* home = std::getenv("HOME"))
      if (!contents.load_merge((std::filesystem::path(home) / ".cvsignore").string(), defaults, {}, err, true)) return false;
    if (const char* value = std::getenv("CVSIGNORE"))
      if (!contents.merge_content(value, defaults, {}, err)) return false;
    list = std::make_shared<const FilterList>(std::move(contents));
  }
  if (!directory_cvs_) cvs_cache_->lists[1] = list;
  marker.merged = list;
  return true;
}

bool FilterList::add_cvs_option(std::string* err) {
  cvs_option_start_ = rules_.size();
  return add_filter(":C", err) && add_filter("-C", err);
}

void FilterList::prepare_pull() {
  if (!cvs_cache_ || !cvs_cache_->lists[0]) return;
  const size_t end = std::min(cvs_option_start_, rules_.size());
  for (size_t i = 0; i < end; ++i)
    if (rules_[i].kind == Kind::Cvs && rules_[i].sides != 2) return;
  FilterList unelided = *cvs_cache_->lists[0];
  for (Rule& rule : unelided.rules_) rule.sides = 3;
  auto list = std::make_shared<const FilterList>(std::move(unelided));
  cvs_cache_->lists[0] = cvs_cache_->lists[1] = list;
  for (Rule& rule : rules_)
    if (rule.kind == Kind::Cvs) rule.merged = list;
}

FilterList FilterList::in_directory(std::string_view path, bool receiver, std::string* err) const {
  if (err) err->clear();
  std::error_code error;
  auto dir = std::filesystem::weakly_canonical(std::filesystem::absolute(std::filesystem::path(path), error), error);
  if (error) dir = std::filesystem::path(path).lexically_normal();
  MergeRegistry registry;
  registered_merges(registry, true);
  return directory_impl(dir.string(), receiver, err, 0, registry);
}

void FilterList::registered_merges(MergeRegistry& registry, bool inheriting) const {
  for (const Rule& rule : rules_) {
    if (rule.kind != Kind::Merge) continue;
    auto name = std::filesystem::path(rule.text).filename().string();
    auto found = std::find_if(registry.begin(), registry.end(), [&](const auto& item) { return item.first == name; });
    if (found == registry.end()) registry.emplace_back(std::move(name), rule.merge_id);
    else found->second = std::min(found->second, rule.merge_id);
    if (rule.merged && (!inheriting || rule.modifiers.find_first_of("nC") == std::string::npos))
      rule.merged->registered_merges(registry, inheriting);
  }
}

FilterList FilterList::directory_impl(std::string_view path, bool receiver, std::string* err, unsigned depth,
                                     MergeRegistry& registry) const {
  FilterList result = *this;
  result.directory_cvs_ = true;
  result.receiver_cvs_ = receiver;
  if (depth >= 64) { set_err(err, "dir-merge nesting exceeds 64: " + std::string(path)); return result; }
  for (Rule& rule : result.rules_) {
    if (rule.kind != Kind::Merge) continue;
    auto name = std::filesystem::path(rule.text).filename().string();
    auto registered = std::find_if(registry.begin(), registry.end(), [&](const auto& item) { return item.first == name; });
    if (registered != registry.end() && registered->second != rule.merge_id) { rule.merged.reset(); continue; }
    if (registered == registry.end()) registry.emplace_back(name, rule.merge_id);
    if (rule.sides && !(rule.sides & (receiver ? 2 : 1))) continue;
    std::vector<std::string> directories;
    if (!rule.merge_ready) {
      std::filesystem::path name(rule.text), current(path);
      rule.merge_name = name.filename().string();
      // rsync removes '.' components but keeps '..' during its textual
      // ancestor check. Collapsing '..' can incorrectly enable a parent scan.
      std::filesystem::path first;
      for (const auto& component : current / name.parent_path())
        if (component != ".") first /= component;
      auto start = first.string(), current_name = current.string();
      const bool ancestor = start == "/" || current_name == start || current_name.starts_with(start + '/');
      if (name.has_parent_path() && ancestor) {
        while (current != first) { directories.push_back(current.string()); current = current.parent_path(); }
        directories.push_back(first.string());
        std::reverse(directories.begin(), directories.end());
      }
      rule.merge_ready = true;
    }
    if (directories.empty()) directories.emplace_back(path);
    for (const auto& directory : directories) {
      FilterList inherited;
      if (rule.merged && rule.modifiers.find_first_of("nC") == std::string::npos) inherited = *rule.merged;
      FilterList local;
      local.from0_ = from0_;
      local.merge_depth_ = depth;
      local.cvs_cache_ = result.cvs_cache_;
      local.directory_cvs_ = true;
      local.receiver_cvs_ = receiver;
      if (!local.load_merge((std::filesystem::path(directory) / rule.merge_name).string(), rule, directory, err, true)) return result;
      if (local.cleared_) {
        MergeRegistry discarded;
        inherited.registered_merges(discarded, false);
        std::erase_if(registry, [&](const auto& item) { return std::any_of(discarded.begin(), discarded.end(),
          [&](const auto& old) { return old.second == item.second; }); });
      }
      if (!local.cleared_) local.rules_.insert(local.rules_.end(), inherited.rules_.begin(), inherited.rules_.end());
      auto merged = local.directory_impl(directory, receiver, err, depth + 1, registry);
      if (err && !err->empty()) return result;
      rule.merged = std::make_shared<const FilterList>(std::move(merged));
    }
  }
  return result;
}

int FilterList::match(std::string_view relative, bool is_dir, bool receiver, bool delete_excluded,
                       bool deleting_directory, std::string_view absolute) const {
  std::string_view path = relative;
  if (path.empty()) return false;

  // Reuse the virtual slash framing until switching between relative and absolute paths.
  char stack[4096];
  std::string heap;
  const char* framed = nullptr;
  std::string_view framed_path;

  for (const Rule& r : rules_) {
    // A CVS marker reuses the first imported global list. Its pattern and later
    // side/xattr modifiers do not alter that list; perishable still gates it.
    if (r.kind == Kind::Cvs) {
      if (!(receiver && deleting_directory && r.perishable) && r.merged) {
        int result = r.merged->match(relative, is_dir, receiver, delete_excluded, deleting_directory, absolute);
        if (result) return result;
      }
      continue;
    }
    if (receiver && deleting_directory && r.perishable) continue;
    uint8_t sides = r.sides ? r.sides : delete_excluded && r.kind != Kind::Merge ? 1 : 3;
    if (!(sides & (receiver ? 2 : 1))) continue;
    if (r.kind == Kind::Merge) {
      if (r.merged) {
        int result = r.merged->match(relative, is_dir, receiver, delete_excluded, deleting_directory, absolute);
        if (result) return result;
      }
      continue;
    }
    if (r.xattr) continue;
    path = r.absolute ? absolute : relative;
    if (r.absolute && path.starts_with('/')) path.remove_prefix(1);
    if (!r.absolute && !r.scope.empty()) {
      path = absolute;
      if (r.scope == "/") { if (!path.starts_with('/')) continue; path.remove_prefix(1); }
      else {
        if (!path.starts_with(r.scope) || path.size() <= r.scope.size() || path[r.scope.size()] != '/') continue;
        path.remove_prefix(r.scope.size() + 1);
      }
    }
    if (path.empty()) continue;
    const size_t n = path.size(), slash = path.rfind('/');
    const std::string_view base = slash == path.npos ? path : path.substr(slash + 1);
    if (path != framed_path) framed = nullptr, framed_path = path;
    bool m = false;
    if (is_dir || !r.dir_only) {
      const std::string_view pat = r.pat;
      switch (r.kind) {
        case Kind::Merge: case Kind::Cvs: break;  // Handled before pathname matching.
        case Kind::NameLit: m = base == pat; break;
        case Kind::NameSuffix: m = base.ends_with(pat); break;
        case Kind::NamePrefix: m = base.starts_with(pat); break;
        case Kind::NameWild:
          m = base.starts_with(pat.substr(0, r.head)) && base.ends_with(pat.substr(pat.size() - r.tail)) &&
              wildmatch(pat, base, 0);
          break;
        case Kind::PathLit: m = path == pat; break;
        case Kind::PathLitTail:
          m = path.ends_with(pat) && (n == pat.size() || path[n - pat.size() - 1] == '/');
          break;
        case Kind::PathWild: {
          const bool trail = r.trail_slash && is_dir;
          std::string_view text = path;
          if (r.lead_slash || trail) {
            if (!framed) {
              char* dst = stack;
              if (n + 2 > sizeof stack) {
                heap.resize(n + 2);
                dst = heap.data();
              }
              dst[0] = dst[n + 1] = '/';
              std::memcpy(dst + 1, path.data(), n);
              framed = dst;
            }
            text = {framed + (r.lead_slash ? 0 : 1), n + (r.lead_slash ? 1 : 0) + (trail ? 1 : 0)};
          }
          m = text.starts_with(pat.substr(0, r.head)) && text.ends_with(pat.substr(pat.size() - r.tail)) &&
              wildmatch(pat, text, r.where);
          break;
        }
      }
    }
    if (m != r.negate) return r.include ? 1 : -1;
  }
  return 0;
}

bool FilterList::excluded(std::string_view path, bool is_dir, std::string_view absolute) const {
  return match(path, is_dir, false, false, false, absolute) < 0;
}

bool FilterList::protected_from_deletion(std::string_view path, bool is_dir, bool delete_excluded,
                                        bool deleting_directory, std::string_view absolute) const {
  return match(path, is_dir, true, delete_excluded, deleting_directory, absolute) < 0;
}

bool FilterList::needs_extended() const {
  return std::any_of(rules_.begin(), rules_.end(), [](const Rule& r) {
    return r.kind == Kind::Merge || r.kind == Kind::Cvs || r.sides || r.absolute || r.perishable || r.xattr;
  });
}

bool FilterList::has_absolute() const {
  return std::any_of(rules_.begin(), rules_.end(), [](const Rule& r) {
    return r.absolute || !r.scope.empty() || (r.merged && r.merged->has_absolute());
  });
}

bool FilterList::has_merges() const {
  return std::any_of(rules_.begin(), rules_.end(), [](const Rule& r) { return r.kind == Kind::Merge; });
}

bool FilterList::has_cvs() const {
  return std::any_of(rules_.begin(), rules_.end(), [](const Rule& r) { return r.kind == Kind::Cvs; });
}

std::string FilterList::absolute_path(std::string_view path) {
  // Resolve directories as getcwd() would, retaining the final named entry even
  // when it is a symlink. Excludes match the named link, not its referent.
  std::error_code error;
  auto value = std::filesystem::absolute(std::filesystem::path(path), error).lexically_normal();
  if (error) return std::string(path);
  auto parent = std::filesystem::weakly_canonical(value.parent_path(), error);
  return (error ? value : parent / value.filename()).string();
}

std::vector<std::string> FilterList::to_strings(bool expand_cvs, bool delete_excluded, bool omit_cvs_option,
                                               bool pulling) const {
  std::vector<std::string> out;
  out.reserve(rules_.size());
  const size_t end = omit_cvs_option ? std::min(cvs_option_start_, rules_.size()) : rules_.size();
  for (size_t i = 0; i < end; ++i) {
    const Rule& r = rules_[i];
    // A receiver-only marker cannot initialize the remote sender's CVS cache.
    if (pulling && r.kind == Kind::Cvs && r.sides == 2) continue;
    if (expand_cvs && r.kind == Kind::Cvs) {
      if (r.sides == 1 || (!r.sides && delete_excluded)) continue;
      if (r.merged) {
        for (Rule child : r.merged->rules_) {
          if (r.perishable && !child.perishable) child.perishable = true, child.modifiers += 'p';
          out.push_back(std::string(1, child.prefix) + child.modifiers + ' ' + child.text);
        }
      }
      continue;
    }
    std::string s(1, r.prefix);
    s += r.modifiers;
    s += ' ';
    s += r.text;
    out.push_back(std::move(s));
  }
  return out;
}
