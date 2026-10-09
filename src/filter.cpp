#include "filter.h"

#include <algorithm>
#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <system_error>
#include <utility>

namespace {

using uchar = unsigned char;

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
  r.negate = negate;
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
bool FilterList::add_filter(std::string_view rule, std::string* err) {
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
    case '+': case '-': case '!': break;
    case '.': return fail("unsupported filter rule (merge)");
    case ':': return fail("unsupported filter rule (dir-merge)");
    case 'H': return fail("unsupported filter rule (hide)");
    case 'S': return fail("unsupported filter rule (show)");
    case 'P': return fail("unsupported filter rule (protect)");
    case 'R': return fail("unsupported filter rule (risk)");
    default: return fail("unknown filter rule");
  }

  bool negate = false;
  if (ch != '!') {
    for (char m; (m = at(++i)) && m != ' ' && m != '_';) {
      if (m != '!') {  // rsync also has / C e n p r s w x; none of them are implemented here
        return fail(std::string(std::strchr("/Cenprswx", m) ? "unsupported" : "invalid") + " modifier '" + m +
                    "' in filter rule");
      }
      negate = true;
    }
  }
  const std::string_view pat = rule.substr(std::min(i + 1, rule.size()));
  if (ch == '!') {
    if (!pat.empty()) return fail("'!' rule has trailing characters");
    rules_.clear();
    return true;
  }
  if (pat.empty()) return fail("unexpected end of filter rule");
  add_rule(pat, ch == '+', negate);
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

  // Lines end at '\n' or '\r'; empty lines and lines starting with ';' or '#' are skipped.
  // No whitespace is trimmed (rsync keeps it as part of the pattern).
  std::string line;
  bool ok = true;
  const auto flush = [&] {
    if (ok && !line.empty() && line[0] != ';' && line[0] != '#') ok = add_old_style(line, include, err);
    line.clear();
  };
  char buf[1 << 14];
  for (;;) {
    const size_t n = std::fread(buf, 1, sizeof buf, fp);
    for (size_t k = 0; k < n; ++k) {
      if (buf[k] == '\n' || buf[k] == '\r') flush();
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

bool FilterList::excluded(std::string_view path, bool is_dir) const {
  if (path.empty()) return false;
  const size_t n = path.size();
  const size_t slash = path.rfind('/');
  const std::string_view base = slash == path.npos ? path : path.substr(slash + 1);

  // "/path/" copy, built at most once per call and only for rules needing a virtual slash.
  char stack[4096];
  std::string heap;
  const char* framed = nullptr;

  for (const Rule& r : rules_) {
    bool m = false;
    if (is_dir || !r.dir_only) {
      const std::string_view pat = r.pat;
      switch (r.kind) {
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
    if (m != r.negate) return !r.include;
  }
  return false;
}

std::vector<std::string> FilterList::to_strings() const {
  std::vector<std::string> out;
  out.reserve(rules_.size());
  for (const Rule& r : rules_) {
    std::string s(1, r.include ? '+' : '-');
    if (r.negate) s += '!';
    s += ' ';
    s += r.text;
    out.push_back(std::move(s));
  }
  return out;
}
