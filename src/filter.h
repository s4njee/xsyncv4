#pragma once
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

// rsync-compatible include/exclude rules (simple "+" / "-" / "!" rules only).
class FilterList {
 public:
  // --exclude=PAT (include=false) / --include=PAT (include=true). As in rsync, a leading
  // "+ " / "- " overrides the sense and a lone "!" clears the list.
  void add_pattern(std::string_view pat, bool include);
  // -f / --filter=RULE: "- PAT", "+ PAT", "exclude PAT", "include PAT", "!" / "clear", with
  // '_' accepted for the separating space and the '!' (negate) modifier. Returns false and
  // sets *err for anything else (merge, dir-merge, hide/show/protect/risk, other modifiers).
  bool add_filter(std::string_view rule, std::string* err);
  // --exclude-from=FILE / --include-from=FILE ("-" = stdin).
  bool add_from_file(const std::string& path, bool include, std::string* err);
  bool empty() const { return rules_.empty(); }
  // True if the entry is excluded: first matching rule wins, no match => included. Tests only
  // the given path, not its ancestors. Allocation-free; safe for concurrent calls.
  bool excluded(std::string_view relpath, bool is_dir) const;
  // One add_filter()-compatible string per rule, in order.
  std::vector<std::string> to_strings() const;

 private:
  enum class Kind : uint8_t {
    NameLit,      // final component == pat
    NameSuffix,   // "*lit": final component ends with pat
    NamePrefix,   // "lit*": final component starts with pat
    NameWild,     // wildmatch against the final component
    PathLit,      // anchored literal: whole path == pat
    PathLitTail,  // unanchored literal with a '/': trailing components == pat
    PathWild,     // wildmatch against the path
  };
  struct Rule {
    std::string text;  // pattern as given, for to_strings()
    std::string pat;   // match form: leading/trailing '/' (and the '*' of Suffix/Prefix) removed
    int where = 0;     // PathWild: >0 last N components, <0 retry after each '/', 0 at the start
    uint32_t head = 0, tail = 0;  // wild kinds: lengths of pat's literal prefix / suffix prefilters
    Kind kind = Kind::NameLit;
    bool include = false, negate = false, dir_only = false;
    bool lead_slash = false;   // pattern starts with "**": text gets a virtual leading '/'
    bool trail_slash = false;  // pattern ends with "***": directories get a virtual trailing '/'
  };

  void add_rule(std::string_view pat, bool include, bool negate);
  bool add_old_style(std::string_view pat, bool include, std::string* err);

  std::vector<Rule> rules_;
};
