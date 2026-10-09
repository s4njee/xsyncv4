#pragma once
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

// Immutable include/exclude rules with separate sender and receiver decisions.
class FilterList {
 public:
  // --exclude=PAT (include=false) / --include=PAT (include=true). As in rsync, a leading
  // "+ " / "- " overrides the sense and a lone "!" clears the list.
  void add_pattern(std::string_view pat, bool include);
  // --filter=RULE: include/exclude, hide/show, protect/risk and clear, including
  // sender/receiver, absolute-path, perishable, negation and xattr modifiers.
  // Returns false for unsupported or invalid syntax, with a reason when supplied.
  bool add_filter(std::string_view rule, std::string* err);
  // --exclude-from=FILE / --include-from=FILE ("-" = stdin).
  bool add_from_file(const std::string& path, bool include, std::string* err);
  bool empty() const { return rules_.empty(); }
  // True if the entry is excluded: first matching rule wins, no match => included. Tests only
  // the given path, not its ancestors. Allocation-free; safe for concurrent calls.
  bool excluded(std::string_view relpath, bool is_dir, std::string_view absolute = {}) const;
  bool protected_from_deletion(std::string_view relpath, bool is_dir, bool delete_excluded = false,
                               bool deleting_directory = false, std::string_view absolute = {}) const;
  bool needs_extended() const;
  bool has_absolute() const;
  static std::string absolute_path(std::string_view path);
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
    char prefix = '-';
    std::string modifiers;
    uint8_t sides = 0;  // 0: default both (sender only with --delete-excluded).
    bool absolute = false, perishable = false, xattr = false;
    bool lead_slash = false;   // pattern starts with "**": text gets a virtual leading '/'
    bool trail_slash = false;  // pattern ends with "***": directories get a virtual trailing '/'
  };

  void add_rule(std::string_view pat, bool include, bool negate);
  bool add_old_style(std::string_view pat, bool include, std::string* err);
  bool match(std::string_view path, bool is_dir, bool receiver, bool delete_excluded,
             bool deleting_directory, std::string_view absolute) const;

  std::vector<Rule> rules_;
};
