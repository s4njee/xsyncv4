#pragma once
#include <cstdint>
#include <memory>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

// Immutable include/exclude rules with separate sender and receiver decisions.
class FilterList {
 public:
  // --exclude=PAT (include=false) / --include=PAT (include=true). As in rsync, a leading
  // "+ " / "- " overrides the sense and a lone "!" clears the list.
  void add_pattern(std::string_view pat, bool include);
  // --filter=RULE: include/exclude, hide/show, protect/risk and clear, including
  // sender/receiver, absolute-path, perishable, negation and xattr modifiers,
  // single-instance merge files and per-directory merge templates.
  // Returns false for unsupported or invalid syntax, with a reason when supplied.
  bool add_filter(std::string_view rule, std::string* err, bool read_merge_files = true);
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
  bool has_merges() const;
  // Return a new immutable context: local rules precede inherited rules within
  // their merge slot. The parent remains safe to share across worker threads.
  FilterList in_directory(std::string_view path, bool receiver, std::string* err) const;
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
    Merge,
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
    std::string scope;  // Physical directory for rules originating in a dir-merge file.
    std::string merge_name;
    bool merge_ready = false;
    uint64_t merge_id = 0;
    std::shared_ptr<const FilterList> merged;
    bool lead_slash = false;   // pattern starts with "**": text gets a virtual leading '/'
    bool trail_slash = false;  // pattern ends with "***": directories get a virtual trailing '/'
  };

  void add_rule(std::string_view pat, bool include, bool negate);
  bool add_old_style(std::string_view pat, bool include, std::string* err);
  int match(std::string_view path, bool is_dir, bool receiver, bool delete_excluded,
             bool deleting_directory, std::string_view absolute) const;
  bool load_merge(const std::string& path, const Rule& defaults, std::string_view scope,
                  std::string* err, bool optional);
  using MergeRegistry = std::vector<std::pair<std::string, uint64_t>>;
  void registered_merges(MergeRegistry& registry, bool inheriting) const;
  FilterList directory_impl(std::string_view path, bool receiver, std::string* err, unsigned depth,
                            MergeRegistry& registry) const;

  std::vector<Rule> rules_;
  bool cleared_ = false;
  unsigned merge_depth_ = 0;
  std::string parse_scope_;
};
