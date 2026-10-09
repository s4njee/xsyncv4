// Tests for FilterList.
//
// kCases was generated from the real rsync 3.4.4: for every rule set,
//   LC_ALL=C rsync -rn8 --out-format=%n <rules> src/ dst/
// was run over a tree holding exactly kTree, and the entries it listed were recorded. Re-verify
// against rsync when editing a row rather than trusting FilterList's own answer.
#include <unistd.h>

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <string_view>
#include <unordered_set>
#include <vector>

#include "filter.h"

namespace {

int g_checks = 0, g_failures = 0;

#define CHECK(cond, ...)                                           \
  do {                                                             \
    ++g_checks;                                                    \
    if (!(cond)) {                                                 \
      ++g_failures;                                                \
      std::printf("FAIL %s:%d: %s: ", __FILE__, __LINE__, #cond);  \
      std::printf(__VA_ARGS__);                                    \
      std::printf("\n");                                           \
    }                                                              \
  } while (0)

// Entries of the test tree, parents before children; a trailing '/' marks a directory.
const char* const kTree[] = {
    "a.c", "a.h", "a.o", "b.c", "ab", "foo", ".hid", "Makefile", "README", "UP.C", "sp ace", "st*r", "star",
    "q\?m", "qxm", "br[a]ck", "brack", "b\\s", "bs", "x.c~", "1file", "a-b", "!bang", "+ plus", "#hash",
    ";semi", "\303\251", " a.c", "a.c ", "c", "x", "a]", "[x", "-x", "^x", "bar/", "bar/a", "bar/b.o",
    "bar/foo/", "bar/foo/a.c", "bar/foo/bar", "bar/baz/", "bar/baz/foo", "bar/baz/x.c", "dir1/", "dir1/a",
    "dir1/c", "dir1/ab/", "dir1/ab/c", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
    "dir1/ab/foo/bar/b", "dir1/foo/", "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2", "deep/", "deep/a/",
    "deep/a/b/", "deep/a/b/c/", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/", "deep/a/bar/x", ".git/",
    ".git/config", ".git/objects/", ".git/objects/ab/", ".git/objects/ab/cd", "empty/", "foo.d/",
    "foo.d/foo",
};

// kExcl: `paths` are the entries rsync dropped whose parent it kept (anything below a dropped
//        directory is never visited, so has no expectation); everything else must be included.
// kKeep: `paths` are all the entries rsync kept; every other reachable entry must be excluded.
// kError: rsync rejects the rule set.
enum Mode { kExcl, kKeep, kError };

// Rule specs: "e:PAT" = --exclude=PAT, "i:PAT" = --include=PAT, "f:RULE" = --filter=RULE,
// "E:TEXT" / "I:TEXT" = --exclude-from / --include-from a file whose contents are TEXT.
struct Case {
  std::vector<const char*> rules;
  Mode mode;
  std::vector<const char*> paths;
};

const Case kCases[] = {
    {{"e:foo"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:*.o"}, kExcl, {"a.o", "bar/b.o"}},
    {{"e:*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:a.\?"}, kExcl, {"a.c", "a.h", "a.o", "bar/foo/a.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:a*"}, kExcl, {"a.c", "a.h", "a.o", "ab", "a-b", "a.c ", "a]", "bar/a", "bar/foo/a.c", "dir1/a",
     "dir1/ab/", "deep/a/", ".git/objects/ab/"}},
    {{"e:*a*"}, kExcl, {"a.c", "a.h", "a.o", "ab", "Makefile", "sp ace", "star", "br[a]ck", "brack", "a-b",
     "!bang", "#hash", " a.c", "a.c ", "a]", "bar/", "dir1/a", "dir1/ab/", "dir1/foo/bar", "deep/a/",
     ".git/objects/ab/"}},
    {{"e:\?\?"}, kExcl, {"ab", "bs", "\303\251", "a]", "[x", "-x", "^x", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:\?"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:*"}, kKeep, {}},
    {{"e:.*"}, kExcl, {".hid", ".git/"}},
    {{"e:*~"}, kExcl, {"x.c~"}},
    {{"e:ab"}, kExcl, {"ab", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:Makefile"}, kExcl, {"Makefile"}},
    {{"e:makefile"}, kExcl, {}},
    {{"e:fo"}, kExcl, {}},
    {{"e:oo"}, kExcl, {}},
    {{"e:f*o"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:*.c*"}, kExcl, {"a.c", "b.c", "x.c~", " a.c", "a.c ", "bar/foo/a.c", "bar/baz/x.c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"e:a.c"}, kExcl, {"a.c", "bar/foo/a.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:*c"}, kExcl, {"a.c", "b.c", " a.c", "c", "bar/foo/a.c", "bar/baz/x.c", "dir1/c", "dir1/ab/c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c", "deep/a/b/c/"}},
    {{"e:b*"}, kExcl, {"b.c", "br[a]ck", "brack", "b\\s", "bs", "bar/", "dir1/ab/foo/bar/", "dir1/foo/bar",
     "dir1/foo/b.c", "deep/a/b/", "deep/a/bar/"}},
    {{"e:\?*.\?"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "UP.C", " a.c", "bar/b.o", "bar/foo/a.c",
     "bar/baz/x.c", "dir1/ab/foo/bar/a.c", "dir1/foo/b.c", "foo.d/"}},
    {{"e:*.*.*"}, kExcl, {}},
    {{"e:.git"}, kExcl, {".git/"}},
    {{"e:foo/"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"e:bar/"}, kExcl, {"bar/", "dir1/ab/foo/bar/", "deep/a/bar/"}},
    {{"e:*/"}, kExcl, {"bar/", "dir1/", "deep/", ".git/", "empty/", "foo.d/"}},
    {{"e:ab/"}, kExcl, {"dir1/ab/", ".git/objects/ab/"}},
    {{"e:a*/"}, kExcl, {"dir1/ab/", "deep/a/", ".git/objects/ab/"}},
    {{"e:a/"}, kExcl, {"deep/a/"}},
    {{"e:c/"}, kExcl, {"deep/a/b/c/"}},
    {{"e:foo*/"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/", "foo.d/"}},
    {{"e:foo//"}, kExcl, {}},
    {{"e:.*/"}, kExcl, {".git/"}},
    {{"e:/foo"}, kExcl, {"foo"}},
    {{"e:/foo/"}, kExcl, {}},
    {{"e:/bar/foo"}, kExcl, {"bar/foo/"}},
    {{"e:/a.c"}, kExcl, {"a.c"}},
    {{"e:/*.c"}, kExcl, {"a.c", "b.c", " a.c"}},
    {{"e:/bar/*.o"}, kExcl, {"bar/b.o"}},
    {{"e:/dir1/*/foo"}, kExcl, {"dir1/ab/foo/"}},
    {{"e:/"}, kExcl, {}},
    {{"e://"}, kExcl, {}},
    {{"e:/bar/foo/"}, kExcl, {"bar/foo/"}},
    {{"e:/bar/foo/bar"}, kExcl, {"bar/foo/bar"}},
    {{"e:/a"}, kExcl, {}},
    {{"e:/dir1/a"}, kExcl, {"dir1/a"}},
    {{"e:/*"}, kKeep, {}},
    {{"e:/*/a"}, kExcl, {"bar/a", "dir1/a", "deep/a/"}},
    {{"e:/*/*"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/", "bar/baz/", "dir1/a", "dir1/c", "dir1/ab/",
     "dir1/foo/", "dir1/st*r2", "deep/a/", ".git/config", ".git/objects/", "foo.d/foo"}},
    {{"e:/b*/"}, kExcl, {"bar/"}},
    {{"e:/dir1/foo/bar/"}, kExcl, {}},
    {{"e:/deep/a/b"}, kExcl, {"deep/a/b/"}},
    {{"e:/\?"}, kExcl, {"c", "x"}},
    {{"e:/bar"}, kExcl, {"bar/"}},
    {{"e:foo/bar"}, kExcl, {"bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar"}},
    {{"e:bar/foo"}, kExcl, {"bar/foo/"}},
    {{"e:foo/bar/"}, kExcl, {"dir1/ab/foo/bar/"}},
    {{"e:ab/foo/bar"}, kExcl, {"dir1/ab/foo/bar/"}},
    {{"e:foo/*.c"}, kExcl, {"bar/foo/a.c", "dir1/foo/b.c"}},
    {{"e:*/foo"}, kExcl, {"bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:*/*/foo"}, kExcl, {"bar/baz/foo", "dir1/ab/foo/", "deep/a/b/foo"}},
    {{"e:bar/*/foo"}, kExcl, {"bar/baz/foo"}},
    {{"e:a/b"}, kExcl, {"deep/a/b/"}},
    {{"e:b/c/d.txt"}, kExcl, {"deep/a/b/c/d.txt"}},
    {{"e:foo/b*"}, kExcl, {"bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"e:r/foo"}, kExcl, {}},
    {{"e:*/*/*/*"}, kExcl, {"dir1/ab/foo/bar/", "deep/a/b/c/", "deep/a/b/foo", "deep/a/bar/x",
     ".git/objects/ab/cd"}},
    {{"e:*/a"}, kExcl, {"bar/a", "dir1/a", "deep/a/"}},
    {{"e:\?/b"}, kExcl, {"deep/a/b/"}},
    {{"e:dir1/a"}, kExcl, {"dir1/a"}},
    {{"e:1/a"}, kExcl, {}},
    {{"e:a/b/c/d.txt"}, kExcl, {"deep/a/b/c/d.txt"}},
    {{"e:deep/a/b/c/d.txt"}, kExcl, {"deep/a/b/c/d.txt"}},
    {{"e:x/deep/a/b/c/d.txt"}, kExcl, {}},
    {{"e:*/deep/a"}, kExcl, {}},
    {{"e:*/bar"}, kExcl, {"bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar", "deep/a/bar/"}},
    {{"e:foo/"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"e:ab/c"}, kExcl, {"dir1/ab/c"}},
    {{"e:b/foo"}, kExcl, {"deep/a/b/foo"}},
    {{"e:a/bar/"}, kExcl, {"deep/a/bar/"}},
    {{"e:objects/*/cd"}, kExcl, {".git/objects/ab/cd"}},
    {{"e:*/\?"}, kExcl, {"bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:**/foo"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:**foo"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:foo/**"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"e:bar/**/foo"}, kExcl, {"bar/baz/foo"}},
    {{"e:bar/**.c"}, kExcl, {"bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:**.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:/**/foo"}, kExcl, {"bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:/bar/**"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/", "bar/baz/"}},
    {{"e:dir1/**/a.c"}, kExcl, {"dir1/ab/foo/bar/a.c"}},
    {{"e:**/"}, kExcl, {"bar/", "dir1/", "deep/", ".git/", "empty/", "foo.d/"}},
    {{"e:**"}, kKeep, {}},
    {{"e:a**c"}, kExcl, {"a.c", "bar/foo/a.c", "dir1/ab/c", "dir1/ab/foo/bar/a.c", "deep/a/b/c/"}},
    {{"e:deep/**/foo"}, kExcl, {"deep/a/b/foo"}},
    {{"e:**/a/**"}, kExcl, {"deep/a/b/", "deep/a/bar/"}},
    {{"e:b**"}, kExcl, {"b.c", "br[a]ck", "brack", "b\\s", "bs", "bar/", "dir1/ab/foo/bar/", "dir1/foo/bar",
     "dir1/foo/b.c", "deep/a/b/", "deep/a/bar/"}},
    {{"e:**/bar/"}, kExcl, {"bar/", "dir1/ab/foo/bar/", "deep/a/bar/"}},
    {{"e:**/a"}, kExcl, {"bar/a", "dir1/a", "deep/a/"}},
    {{"e:/**"}, kKeep, {}},
    {{"e:/**/"}, kExcl, {"bar/", "dir1/", "deep/", ".git/", "empty/", "foo.d/"}},
    {{"e:/**.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:a/**/x"}, kExcl, {"deep/a/bar/x"}},
    {{"e:/dir1/**/b*"}, kExcl, {"dir1/ab/foo/bar/", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"e:**/*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:**/**/foo"}, kExcl, {"bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/foo"}},
    {{"e:ab/**"}, kExcl, {"dir1/ab/c", "dir1/ab/foo/", ".git/objects/ab/cd"}},
    {{"e:**r"}, kExcl, {"st*r", "star", "bar/", "dir1/ab/foo/bar/", "dir1/foo/bar", "deep/a/bar/"}},
    {{"e:**/b"}, kExcl, {"dir1/ab/foo/bar/b", "deep/a/b/"}},
    {{"e:b**/foo"}, kExcl, {"bar/foo/", "bar/baz/foo", "deep/a/b/foo"}},
    {{"e:r**/a.c"}, kExcl, {}},
    {{"e:**/foo/**/a.c"}, kExcl, {"dir1/ab/foo/bar/a.c"}},
    {{"e:foo**bar"}, kExcl, {"bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar"}},
    {{"e:*/**/c"}, kExcl, {"dir1/ab/c", "deep/a/b/c/"}},
    {{"e:**/\?"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:d**"}, kExcl, {"dir1/", "deep/"}},
    {{"e:/d**/c"}, kExcl, {"dir1/c", "dir1/ab/c", "deep/a/b/c/"}},
    {{"e:\\**"}, kExcl, {}},
    {{"e:**\\*r"}, kExcl, {"st*r"}},
    {{"e:foo/***"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"e:/bar/***"}, kExcl, {"bar/"}},
    {{"e:bar/foo/***"}, kExcl, {"bar/foo/"}},
    {{"i:foo/***", "e:*"}, kKeep, {}},
    {{"i:/dir1/***", "e:*"}, kKeep, {"dir1/", "dir1/a", "dir1/c", "dir1/ab/", "dir1/ab/c", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b", "dir1/foo/", "dir1/foo/bar",
     "dir1/foo/b.c", "dir1/st*r2"}},
    {{"i:dir1/ab/***", "e:*"}, kKeep, {}},
    {{"e:***"}, kKeep, {}},
    {{"e:foo***"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/"}},
    {{"e:/dir1/ab/***/"}, kExcl, {"dir1/ab/"}},
    {{"e:**/foo/***"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"i:/bar/", "i:/bar/foo/***", "e:*"}, kKeep, {"bar/", "bar/foo/", "bar/foo/a.c", "bar/foo/bar"}},
    {{"e:ab/***"}, kExcl, {"dir1/ab/", ".git/objects/ab/"}},
    {{"e:a/***"}, kExcl, {"deep/a/"}},
    {{"e:/***"}, kKeep, {}},
    {{"e:*/***"}, kExcl, {"bar/", "dir1/", "deep/", ".git/", "empty/", "foo.d/"}},
    {{"e:foo/***/"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"i:deep/", "i:deep/a/", "i:deep/a/b/***", "e:*"}, kKeep, {"deep/", "deep/a/", "deep/a/b/",
     "deep/a/b/c/", "deep/a/b/c/d.txt", "deep/a/b/foo"}},
    {{"e:ba*/***"}, kExcl, {"bar/", "dir1/ab/foo/bar/", "deep/a/bar/"}},
    {{"i:/bar/***", "i:/.git/***", "e:/*"}, kKeep, {"bar/", "bar/a", "bar/b.o", "bar/foo/", "bar/foo/a.c",
     "bar/foo/bar", "bar/baz/", "bar/baz/foo", "bar/baz/x.c", ".git/", ".git/config", ".git/objects/",
     ".git/objects/ab/", ".git/objects/ab/cd"}},
    {{"e:fo***"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo",
     "foo.d/"}},
    {{"e:****"}, kKeep, {}},
    {{"e:foo/****"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"e:/foo/***"}, kExcl, {}},
    {{"e:b/***"}, kExcl, {"deep/a/b/"}},
    {{"e:*/foo/***"}, kExcl, {"bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"e:objects/***"}, kExcl, {".git/objects/"}},
    {{"e:foo.d/***"}, kExcl, {"foo.d/"}},
    {{"e:[ab].c"}, kExcl, {"a.c", "b.c", "bar/foo/a.c", "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"e:[!a].c"}, kExcl, {"b.c", "bar/baz/x.c", "dir1/foo/b.c"}},
    {{"e:[^a].c"}, kExcl, {"b.c", "bar/baz/x.c", "dir1/foo/b.c"}},
    {{"e:[a-c].\?"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "bar/b.o", "bar/foo/a.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:*.[ch]"}, kExcl, {"a.c", "a.h", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:[[:upper:]]*"}, kExcl, {"Makefile", "README", "UP.C"}},
    {{"e:[[:digit:]]*"}, kExcl, {"1file"}},
    {{"e:*[[:punct:]]*"}, kExcl, {"a.c", "a.h", "a.o", "b.c", ".hid", "UP.C", "st*r", "q\?m", "br[a]ck",
     "b\\s", "x.c~", "a-b", "!bang", "+ plus", "#hash", ";semi", " a.c", "a.c ", "a]", "[x", "-x", "^x",
     "bar/b.o", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c", "dir1/foo/b.c", "dir1/st*r2",
     "deep/a/b/c/d.txt", ".git/", "foo.d/"}},
    {{"e:[[:alpha:]][[:alpha:]]"}, kExcl, {"ab", "bs", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:[]x]"}, kExcl, {"x", "deep/a/bar/x"}},
    {{"e:[]x]*"}, kExcl, {"x.c~", "x", "bar/baz/x.c", "deep/a/bar/x"}},
    {{"e:br[[]a]ck"}, kExcl, {"br[a]ck"}},
    {{"e:[a-]*"}, kExcl, {"a.c", "a.h", "a.o", "ab", "a-b", "a.c ", "a]", "-x", "bar/a", "bar/foo/a.c",
     "dir1/a", "dir1/ab/", "deep/a/", ".git/objects/ab/"}},
    {{"e:[[:bogus:]]*"}, kExcl, {}},
    {{"e:[ab"}, kExcl, {}},
    {{"e:*[![:alnum:].]*"}, kExcl, {"sp ace", "st*r", "q\?m", "br[a]ck", "b\\s", "x.c~", "a-b", "!bang",
     "+ plus", "#hash", ";semi", "\303\251", " a.c", "a.c ", "a]", "[x", "-x", "^x", "dir1/st*r2"}},
    {{"e:[\\a].c"}, kExcl, {"a.c", "bar/foo/a.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:*[[:space:]]*"}, kExcl, {"sp ace", "+ plus", " a.c", "a.c "}},
    {{"e:[[:space:]]*"}, kExcl, {" a.c"}},
    {{"e:[[:xdigit:]][[:xdigit:]]"}, kExcl, {"ab", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:[[:lower:]].[[:lower:]]"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "bar/b.o", "bar/foo/a.c",
     "bar/baz/x.c", "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"e:[!/]"}, kExcl, {}},
    {{"e:a[./]c"}, kExcl, {}},
    {{"e:bar[/]a"}, kExcl, {}},
    {{"e:[b-a].c"}, kExcl, {"b.c", "dir1/foo/b.c"}},
    {{"e:[a\\-c].c"}, kExcl, {"a.c", "bar/foo/a.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:[[:alnum:]]"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/"}},
    {{"e:[[:graph:]]"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/"}},
    {{"e:[[:print:]]a.c"}, kExcl, {" a.c"}},
    {{"e:[[:blank:]]*"}, kExcl, {" a.c"}},
    {{"e:[[:cntrl:]]*"}, kExcl, {}},
    {{"e:[[:alpha:]"}, kExcl, {}},
    {{"e:[[:alpha]]*"}, kExcl, {"a]"}},
    {{"e:[[:]*"}, kExcl, {"[x"}},
    {{"e:[[]*"}, kExcl, {"[x"}},
    {{"e:[[:alpha:]-z]*"}, kKeep, {".hid", "1file", "!bang", "+ plus", "#hash", ";semi", "\303\251", " a.c",
     "[x", "^x", ".git/"}},
    {{"e:[!]a]*"}, kKeep, {"a.c", "a.h", "a.o", "ab", "a-b", "a.c ", "a]"}},
    {{"e:[^]]"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:[a-c-x]"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/"}},
    {{"e:[A-Z][A-Z]*"}, kExcl, {"README", "UP.C"}},
    {{"e:[+!#;]*"}, kExcl, {"!bang", "+ plus", "#hash", ";semi"}},
    {{"e:*[*\?]*"}, kExcl, {"st*r", "q\?m", "dir1/st*r2"}},
    {{"e:[[:ALPHA:]]*"}, kExcl, {}},
    {{"e:[.]*"}, kExcl, {".hid", ".git/"}},
    {{"e:a[!.]b"}, kExcl, {"a-b"}},
    {{"e:[\\]]"}, kExcl, {}},
    {{"e:x[\\"}, kExcl, {}},
    {{"e:[x\\"}, kExcl, {}},
    {{"e:/bar/[a-b]*"}, kExcl, {"bar/a", "bar/b.o", "bar/baz/"}},
    {{"e:[a-c]/b"}, kExcl, {"deep/a/b/"}},
    {{"e:*/[[:alpha:]]"}, kExcl, {"bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:[\303]\?"}, kExcl, {"\303\251"}},
    {{"e:[!\303]\?"}, kExcl, {"ab", "bs", "a]", "[x", "-x", "^x", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:st\\*r"}, kExcl, {"st*r"}},
    {{"e:st*r"}, kExcl, {"st*r", "star"}},
    {{"e:q\\\?m"}, kExcl, {"q\?m"}},
    {{"e:q\?m"}, kExcl, {"q\?m", "qxm"}},
    {{"e:br\\[a]ck"}, kExcl, {"br[a]ck"}},
    {{"e:br[a]ck"}, kExcl, {"brack"}},
    {{"e:b\\s"}, kExcl, {"b\\s"}},
    {{"e:b\\\\s"}, kExcl, {}},
    {{"e:b\\\\s*"}, kExcl, {"b\\s"}},
    {{"e:b\\s*"}, kExcl, {"bs"}},
    {{"e:\\a.c"}, kExcl, {}},
    {{"e:\\a.\?"}, kExcl, {"a.c", "a.h", "a.o", "bar/foo/a.c", "dir1/ab/foo/bar/a.c"}},
    {{"e:foo\\"}, kExcl, {}},
    {{"e:fo*\\"}, kExcl, {}},
    {{"e:st\\*r*"}, kExcl, {"st*r", "dir1/st*r2"}},
    {{"e:\\s\\t\\a\\r*"}, kExcl, {"star"}},
    {{"e:b\\\\*"}, kExcl, {"b\\s"}},
    {{"e:*\\\\*"}, kExcl, {"b\\s"}},
    {{"e:dir1/st\\*r2"}, kExcl, {"dir1/st*r2"}},
    {{"e:dir1/st\\*r\?"}, kExcl, {"dir1/st*r2"}},
    {{"e:*\\*r"}, kExcl, {"st*r"}},
    {{"e:\\\?"}, kExcl, {}},
    {{"e:b[\\\\]s"}, kExcl, {"b\\s"}},
    {{"e:\?\\\\\?"}, kExcl, {"b\\s"}},
    {{"e:\\/foo*"}, kExcl, {}},
    {{"e:bar\\/a*"}, kExcl, {"bar/a", "dir1/ab/foo/bar/a.c"}},
    {{"e:\\*"}, kExcl, {}},
    {{"e:/b\\ar/*"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/", "bar/baz/"}},
    {{"i:*/", "i:*.c", "e:*"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/", ".git/",
     ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*.c", "e:*"}, kKeep, {"a.c", "b.c", " a.c"}},
    {{"e:*", "i:*.c"}, kKeep, {}},
    {{"i:/bar/", "i:/bar/foo/", "i:/bar/foo/a.c", "e:*"}, kKeep, {"bar/", "bar/foo/", "bar/foo/a.c"}},
    {{"e:*.o", "i:*"}, kExcl, {"a.o", "bar/b.o"}},
    {{"i:a.c", "e:a.*"}, kExcl, {"a.h", "a.o", "a.c "}},
    {{"i:/dir1/", "i:/dir1/ab/", "i:/dir1/ab/**", "e:*"}, kKeep, {"dir1/", "dir1/ab/", "dir1/ab/c",
     "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b"}},
    {{"i:foo/", "e:foo"}, kExcl, {"foo", "bar/baz/foo", "deep/a/b/foo", "foo.d/foo"}},
    {{"e:foo", "i:foo/"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/",
     "deep/a/b/foo", "foo.d/foo"}},
    {{"i:/bar/foo/a.c", "e:*"}, kKeep, {}},
    {{"i:*/", "e:*"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "i:foo", "e:*"}, kKeep, {"foo", "bar/", "bar/foo/", "bar/baz/", "bar/baz/foo", "dir1/",
     "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/",
     "deep/a/b/c/", "deep/a/b/foo", "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/",
     "foo.d/", "foo.d/foo"}},
    {{"e:/bar/foo/", "i:bar/**"}, kExcl, {"bar/foo/"}},
    {{"i:*.c", "i:*.h", "e:/*"}, kKeep, {"a.c", "a.h", "b.c", " a.c"}},
    {{"i:bar/a", "e:a"}, kExcl, {"dir1/a", "deep/a/"}},
    {{"i:/a.c", "e:*.c"}, kExcl, {"b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:*.c", "i:/a.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"i:dir1/", "i:ab/", "i:foo/", "i:bar/", "i:a.c", "e:*"}, kKeep, {"a.c", "bar/", "bar/foo/",
     "bar/foo/a.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/"}},
    {{"i:**/", "i:**/foo", "e:**"}, kKeep, {"foo", "bar/", "bar/foo/", "bar/baz/", "bar/baz/foo", "dir1/",
     "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/",
     "deep/a/b/c/", "deep/a/b/foo", "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/",
     "foo.d/", "foo.d/foo"}},
    {{"e:.git/", "i:*/", "i:*.[ch]", "e:*"}, kKeep, {"a.c", "a.h", "b.c", " a.c", "bar/", "bar/foo/",
     "bar/foo/a.c", "bar/baz/", "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/",
     "dir1/ab/foo/bar/a.c", "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", "empty/", "foo.d/"}},
    {{"i:deep/***", "e:/*"}, kKeep, {"deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/b/c/d.txt",
     "deep/a/b/foo", "deep/a/bar/", "deep/a/bar/x"}},
    {{"i:/deep", "e:/*"}, kKeep, {"deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/b/c/d.txt",
     "deep/a/b/foo", "deep/a/bar/", "deep/a/bar/x"}},
    {{"e:+ a.c", "e:*"}, kKeep, {"a.c"}},
    {{"i:- *.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:*.c", "e:!", "e:*.o"}, kExcl, {"a.o", "bar/b.o"}},
    {{"e:!foo"}, kExcl, {}},
    {{"e:!bang"}, kExcl, {"!bang"}},
    {{"e:+ plus"}, kExcl, {}},
    {{"e:- + plus"}, kExcl, {"+ plus"}},
    {{"i:+ plus", "e:*"}, kKeep, {}},
    {{"e:+ + plus", "e:*"}, kKeep, {"+ plus"}},
    {{"e:*.c", "i:!"}, kExcl, {}},
    {{"e:+a.c"}, kExcl, {}},
    {{"e:-a.c"}, kExcl, {}},
    {{"e:!*"}, kExcl, {"!bang"}},
    {{"e:- !"}, kExcl, {}},
    {{"e:+ !", "e:*"}, kKeep, {}},
    {{"e:-  a.c"}, kExcl, {" a.c"}},
    {{"e:*", "e:!", "e:!"}, kExcl, {}},
    {{"f:- *.o"}, kExcl, {"a.o", "bar/b.o"}},
    {{"f:+ a.c", "f:- *"}, kKeep, {"a.c"}},
    {{"f:-_*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"f:exclude *.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"f:+_a.c", "f:-_a.*"}, kExcl, {"a.h", "a.o", "a.c "}},
    {{"f:include */", "f:include *.c", "f:exclude *"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/",
     "bar/foo/a.c", "bar/baz/", "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/",
     "dir1/ab/foo/bar/a.c", "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:-! */"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:+! *.c", "f:- *"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"f:-,! *.c"}, kKeep, {"a.c", "b.c", " a.c"}},
    {{"f:exclude,! */"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:- *.c", "f:!", "f:- *.o"}, kExcl, {"a.o", "bar/b.o"}},
    {{"f:- *.c", "f:clear", "f:- *.h"}, kExcl, {"a.h"}},
    {{"f:-  a.c"}, kExcl, {" a.c"}},
    {{"f:- sp ace"}, kExcl, {"sp ace"}},
    {{"f:-! foo/"}, kKeep, {}},
    {{"f:include,! */", "f:- /*"}, kExcl, {"bar/", "dir1/", "deep/", ".git/", "empty/", "foo.d/"}},
    {{"f:exclude_foo"}, kExcl, {"foo", "bar/foo/", "bar/baz/foo", "dir1/ab/foo/", "dir1/foo/",
     "deep/a/b/foo", "foo.d/foo"}},
    {{"f:include_*.c", "f:exclude_*"}, kKeep, {"a.c", "b.c", " a.c"}},
    {{"f:-!_/bar/***"}, kKeep, {"bar/", "bar/a", "bar/b.o", "bar/foo/", "bar/foo/a.c", "bar/foo/bar",
     "bar/baz/", "bar/baz/foo", "bar/baz/x.c"}},
    {{"f:- + plus"}, kExcl, {"+ plus"}},
    {{"f:- !bang"}, kExcl, {"!bang"}},
    {{"f:+ !bang", "f:- *"}, kKeep, {"!bang"}},
    {{"f:-! /dir1/***"}, kKeep, {"dir1/", "dir1/a", "dir1/c", "dir1/ab/", "dir1/ab/c", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b", "dir1/foo/", "dir1/foo/bar",
     "dir1/foo/b.c", "dir1/st*r2"}},
    {{"f:-! **"}, kExcl, {}},
    {{"f:-!! */"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:-,!_*/"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:- - b.c"}, kExcl, {}},
    {{"f:- a.c ", "f:-_ a.c"}, kExcl, {" a.c", "a.c "}},
    {{"e:*.o", "f:+ */", "i:*.c", "f:- *"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c",
     "bar/baz/", "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/",
     "dir1/ab/foo/bar/a.c", "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:+! foo", "e:/*"}, kExcl, {"foo"}},
    {{"f:- /bar/", "f:clear"}, kExcl, {}},
    {{"E:*.o\n# comment\n; other\n\n+ a.c\n- *.c\nfoo/\n"}, kExcl, {"a.o", "b.c", " a.c", "bar/b.o",
     "bar/foo/", "bar/baz/x.c", "dir1/ab/foo/", "dir1/foo/"}},
    {{"I:*.c\n*/\n", "e:*"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/", ".git/",
     ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"E:*.c\r\n*.o\r\n"}, kExcl, {"a.c", "a.o", "b.c", " a.c", "bar/b.o", "bar/foo/a.c", "bar/baz/x.c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"E: a.c\n"}, kExcl, {" a.c"}},
    {{"E:*.c\n!\n*.o\n"}, kExcl, {"a.o", "bar/b.o"}},
    {{"E:a.c \n"}, kExcl, {"a.c "}},
    {{"E:#hash\n;semi\n"}, kExcl, {}},
    {{"E:[#]hash\n\?semi\n"}, kExcl, {"#hash", ";semi"}},
    {{"I:- *.o\n+ *.h\n", "e:a.*"}, kExcl, {"a.c", "a.o", "a.c ", "bar/b.o", "bar/foo/a.c",
     "dir1/ab/foo/bar/a.c"}},
    {{"E:*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"E:"}, kExcl, {}},
    {{"E:\n\n\n"}, kExcl, {}},
    {{"E: # not a comment\n #hash\n*.h"}, kExcl, {"a.h"}},
    {{"E:- #hash\n- ;semi\n"}, kExcl, {"#hash", ";semi"}},
    {{"I:!\n", "e:*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:*.c", "I:!\n*.o\n", "e:*"}, kKeep, {"a.o"}},
    {{"E:*.c\r*.o\r"}, kExcl, {"a.c", "a.o", "b.c", " a.c", "bar/b.o", "bar/foo/a.c", "bar/baz/x.c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"E:  \n"}, kExcl, {}},
    {{"E:\t*.c\n*.o\t\n"}, kExcl, {}},
    {{"I:*/\n+ *.c\n- *\n"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/", ".git/",
     ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"E:/bar/foo/\nfoo/***\n**/a.c\n"}, kExcl, {"a.c", "bar/foo/", "dir1/ab/foo/", "dir1/foo/"}},
    {{"E:+ */\n+ **.c\n*\n"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/", ".git/",
     ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"I:/dir1/\n/dir1/ab/***\n", "E:*\n"}, kKeep, {"dir1/", "dir1/ab/", "dir1/ab/c", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b"}},
    {{"E:!foo\n!bang\n"}, kExcl, {"!bang"}},
    {{"E:+ + plus\n- *\n"}, kKeep, {"+ plus"}},
    {{"E:-\n+\n-a.c\n"}, kExcl, {}},
    {{"E:exclude *.c\ninclude *.o\n"}, kExcl, {}},
    {{"E:sp ace\nst\\*r\n"}, kExcl, {"sp ace", "st*r"}},
    {{"e:sp ace"}, kExcl, {"sp ace"}},
    {{"e:sp*"}, kExcl, {"sp ace"}},
    {{"e:* *"}, kExcl, {"sp ace", "+ plus", " a.c", "a.c "}},
    {{"e:#hash"}, kExcl, {"#hash"}},
    {{"e:;semi"}, kExcl, {";semi"}},
    {{"e:\303\251"}, kExcl, {"\303\251"}},
    {{"e:[[:alpha:]]"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/"}},
    {{"e:a-b"}, kExcl, {"a-b"}},
    {{"e:a[-]b"}, kExcl, {"a-b"}},
    {{"e:1file"}, kExcl, {"1file"}},
    {{"e:[0-9]*"}, kExcl, {"1file"}},
    {{"e: *"}, kExcl, {" a.c"}},
    {{"e:* "}, kExcl, {"a.c "}},
    {{"e:a.c "}, kExcl, {"a.c "}},
    {{"e: a.c"}, kExcl, {" a.c"}},
    {{"e:\?\?\?"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "foo", "q\?m", "qxm", "b\\s", "a-b", "bar/",
     "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo", "deep/a/bar/", "foo.d/foo"}},
    {{"e:[\303\251]"}, kExcl, {}},
    {{"e:\?[!a]"}, kExcl, {"ab", "bs", "\303\251", "a]", "[x", "-x", "^x", "dir1/ab/", ".git/objects/ab/"}},
    {{"e:[a-z]\?[a-z]"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "foo", "q\?m", "qxm", "b\\s", "a-b", "bar/",
     "dir1/ab/foo/", "dir1/foo/", "deep/a/b/foo", "deep/a/bar/", "foo.d/foo"}},
    {{"e:+*"}, kExcl, {"+ plus"}},
    {{"e:-*"}, kExcl, {"-x"}},
    {{"f:-foo"}, kError, {}},
    {{"f:x foo"}, kError, {}},
    {{"f:clear x"}, kError, {}},
    {{"f:- "}, kError, {}},
    {{"f:!x"}, kError, {}},
    {{"f:exclude"}, kError, {}},
    {{"f:+!"}, kError, {}},
    {{"f:excludes foo"}, kError, {}},
    {{"f:-\tfoo"}, kError, {}},
    {{"f:exclude\tfoo"}, kError, {}},
    {{"f:"}, kExcl, {}},
    {{"e:"}, kExcl, {}},
    {{"E:*.c\n- \n"}, kError, {}},
    {{"f:+"}, kError, {}},
    {{"f:-"}, kError, {}},
    {{"f: - foo"}, kError, {}},
    {{"f:-,"}, kError, {}},
    {{"f:-,foo"}, kError, {}},
    {{"f:!,"}, kExcl, {}},
    {{"f:clear,"}, kExcl, {}},
    {{"f:clear_"}, kError, {}},
    {{"f:! "}, kError, {}},
    {{"i:*/", "e:foo/***"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:/bar/***"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo",
     "bar/baz/x.c"}},
    {{"i:*/", "e:bar/foo/***"}, kExcl, {"bar/foo/a.c", "bar/foo/bar"}},
    {{"i:*/", "e:**/foo/**"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:foo/**"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:/bar/**"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo",
     "bar/baz/x.c"}},
    {{"i:*/", "e:dir1/**"}, kExcl, {"dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2"}},
    {{"i:*/", "e:a**c"}, kExcl, {"a.c", "bar/foo/a.c", "dir1/ab/c", "dir1/ab/foo/bar/a.c"}},
    {{"i:*/", "e:**/a/**"}, kExcl, {"deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x"}},
    {{"i:*/", "e:ab/**"}, kExcl, {"dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     ".git/objects/ab/cd"}},
    {{"i:*/", "e:**"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "e:***"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "e:/**"}, kKeep, {"bar/", "bar/foo/", "bar/baz/", "dir1/", "dir1/ab/", "dir1/ab/foo/",
     "dir1/ab/foo/bar/", "dir1/foo/", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/",
     ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "e:b**"}, kExcl, {"b.c", "br[a]ck", "brack", "b\\s", "bs", "bar/a", "bar/b.o", "bar/foo/a.c",
     "bar/foo/bar", "bar/baz/foo", "bar/baz/x.c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x"}},
    {{"i:*/", "e:d**"}, kExcl, {"dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x"}},
    {{"i:*/", "e:**/b*"}, kExcl, {"b.c", "br[a]ck", "brack", "b\\s", "bs", "bar/b.o", "bar/foo/bar",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:deep/**/foo"}, kExcl, {"deep/a/b/foo"}},
    {{"i:*/", "e:bar/**/foo"}, kExcl, {"bar/baz/foo"}},
    {{"i:*/", "e:**/foo/**/a.c"}, kExcl, {"dir1/ab/foo/bar/a.c"}},
    {{"i:*/", "e:foo/*"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:*/foo/*"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:/dir1/*/*"}, kExcl, {"dir1/ab/c", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:foo/bar/*"}, kExcl, {"dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b"}},
    {{"i:*/", "e:*/*/*/*"}, kExcl, {"dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b", "deep/a/b/c/d.txt",
     "deep/a/b/foo", "deep/a/bar/x", ".git/objects/ab/cd"}},
    {{"i:*/", "e:/*/*"}, kExcl, {"bar/a", "bar/b.o", "dir1/a", "dir1/c", "dir1/st*r2", ".git/config",
     "foo.d/foo"}},
    {{"i:*/", "e:a/b/*"}, kExcl, {"deep/a/b/foo"}},
    {{"i:*/", "e:ab/foo/bar/*"}, kExcl, {"dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b"}},
    {{"i:*/", "e:**r/a.c"}, kExcl, {"dir1/ab/foo/bar/a.c"}},
    {{"i:*/", "e:foo**"}, kExcl, {"foo", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c", "deep/a/b/foo", "foo.d/foo"}},
    {{"i:*/", "e:fo***"}, kExcl, {"foo", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c", "deep/a/b/foo", "foo.d/foo"}},
    {{"i:*/", "e:**/foo/***"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/a.c",
     "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:*/***"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo",
     "bar/baz/x.c", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x",
     ".git/config", ".git/objects/ab/cd", "foo.d/foo"}},
    {{"i:*/", "e:a/***"}, kExcl, {"deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x"}},
    {{"i:*/", "e:/dir1/ab/***"}, kExcl, {"dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b"}},
    {{"i:*/", "e:objects/***"}, kExcl, {".git/objects/ab/cd"}},
    {{"i:*/", "e:**.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"i:*/", "e:/**.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"i:*/", "e:bar/**.c"}, kExcl, {"bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c"}},
    {{"i:*/", "e:/dir1/**/b*"}, kExcl, {"dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "e:**/\?"}, kExcl, {"c", "x", "bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/bar/x"}},
    {{"i:*/", "e:*/[[:alpha:]]"}, kExcl, {"bar/a", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/b",
     "deep/a/bar/x"}},
    {{"i:*/", "e:foo/[!b]*"}, kExcl, {"bar/foo/a.c"}},
    {{"i:*/", "e:**/bar/\?"}, kExcl, {"bar/a", "dir1/ab/foo/bar/b", "deep/a/bar/x"}},
    {{"i:*/", "e:/d*/**/[a-c]"}, kExcl, {"dir1/ab/c", "dir1/ab/foo/bar/b"}},
    {{"i:*/", "e:[bd]*/**"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo",
     "bar/baz/x.c", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x"}},
    {{"i:*/", "e:**[!c]"}, kKeep, {"a.c", "b.c", " a.c", "c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/c", "dir1/ab/", "dir1/ab/c", "dir1/ab/foo/", "dir1/ab/foo/bar/",
     "dir1/ab/foo/bar/a.c", "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "e:foo/b\\ar"}, kExcl, {}},
    {{"i:*/", "e:foo/b\\a\?"}, kExcl, {"bar/foo/bar", "dir1/foo/bar"}},
    {{"i:*/", "e:**/b\\ar"}, kExcl, {"bar/foo/bar", "dir1/foo/bar"}},
    {{"i:*/", "e:*r/*o/*r"}, kExcl, {"bar/foo/bar"}},
    {{"i:*/", "e:\?*/\?*/\?*"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "bar/baz/foo", "bar/baz/x.c",
     "dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b", "dir1/foo/bar", "dir1/foo/b.c",
     "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x", ".git/objects/ab/cd"}},
    {{"i:foo/", "e:foo/***"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/ab/foo/bar/", "dir1/foo/bar",
     "dir1/foo/b.c"}},
    {{"i:/bar/", "e:/bar/***", "e:*.c"}, kExcl, {"a.c", "b.c", " a.c", "bar/a", "bar/b.o", "bar/foo/",
     "bar/baz/", "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"f:+ */", "f:-! **/foo/**"}, kKeep, {"bar/", "bar/foo/", "bar/foo/a.c", "bar/foo/bar", "bar/baz/",
     "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/", "dir1/foo/bar", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:+ */", "f:-! *.c"}, kKeep, {"a.c", "b.c", " a.c", "bar/", "bar/foo/", "bar/foo/a.c", "bar/baz/",
     "bar/baz/x.c", "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c",
     "dir1/foo/", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/", "deep/a/bar/", ".git/",
     ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"f:+ */", "f:+! foo/*", "f:- *"}, kExcl, {"bar/foo/a.c", "bar/foo/bar", "dir1/foo/bar", "dir1/foo/b.c"}},
    {{"i:*/", "i:foo/**", "e:*"}, kKeep, {"bar/", "bar/foo/", "bar/foo/a.c", "bar/foo/bar", "bar/baz/",
     "dir1/", "dir1/ab/", "dir1/ab/foo/", "dir1/ab/foo/bar/", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/", "dir1/foo/bar", "dir1/foo/b.c", "deep/", "deep/a/", "deep/a/b/", "deep/a/b/c/",
     "deep/a/bar/", ".git/", ".git/objects/", ".git/objects/ab/", "empty/", "foo.d/"}},
    {{"i:*/", "e:/dir1/ab/foo/bar/a.c", "e:deep/a/b/c/d.txt"}, kExcl, {"dir1/ab/foo/bar/a.c",
     "deep/a/b/c/d.txt"}},
    {{"i:*/", "e:ab/foo/bar/a.c"}, kExcl, {"dir1/ab/foo/bar/a.c"}},
    {{"i:*/", "e:oo/bar"}, kExcl, {}},
    {{"i:*/", "e:/foo/bar"}, kExcl, {}},
    {{"i:*/", "e:/dir1/foo/bar"}, kExcl, {"dir1/foo/bar"}},
    {{"i:*/", "e:b/c/d.txt/"}, kExcl, {}},
    {{"e:[a-b-x]*"}, kExcl, {"a.c", "a.h", "a.o", "b.c", "ab", "br[a]ck", "brack", "b\\s", "bs", "x.c~",
     "a-b", "a.c ", "x", "a]", "-x", "bar/", "dir1/a", "dir1/ab/", "dir1/foo/bar", "dir1/foo/b.c",
     "deep/a/", ".git/objects/ab/"}},
    {{"e:[a-b-x]"}, kExcl, {"x", "bar/a", "dir1/a", "dir1/ab/foo/bar/b", "deep/a/"}},
    {{"e:/bar\?a"}, kExcl, {}},
    {{"e:**bar\?a"}, kExcl, {}},
    {{"e:/dir1/ab\?c"}, kExcl, {}},
    {{"e:/bar*a"}, kExcl, {}},
    {{"e:/bar[!x]a"}, kExcl, {}},
    {{"i:*/", "e:/dir1/ab\?foo\?bar\?b"}, kExcl, {}},
    {{"i:*/", "e:/dir1/ab*b"}, kExcl, {}},
    {{"i:*/", "e:/dir1/**b"}, kExcl, {"dir1/ab/foo/bar/b"}},
    {{"i:*/", "e:ab\?c"}, kExcl, {}},
    {{"i:*/", "e:r/*/a.c"}, kExcl, {}},
    {{"i:*/", "e:**/*/*/*/*/*"}, kExcl, {"dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b", "deep/a/b/c/d.txt"}},
    {{"E:b\\s\nb\\\\s*\n"}, kExcl, {"b\\s"}},
    {{"E:*.c\r\r\n\r*.h"}, kExcl, {"a.c", "a.h", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c",
     "dir1/ab/foo/bar/a.c", "dir1/foo/b.c"}},
    {{"e:[[:alpha]]"}, kExcl, {"a]"}},
    {{"e:[[:alpha]]*"}, kExcl, {"a]"}},
    {{"e:[[]x"}, kExcl, {"[x"}},
    {{"e:[^^]x"}, kExcl, {"[x", "-x"}},
    {{"e:[!-]x"}, kExcl, {"[x", "^x"}},
    {{"e:[a-]]"}, kExcl, {"a]"}},
    {{"e:[]-a]x"}, kExcl, {"^x"}},
    {{"e:[[:punct:]]x"}, kExcl, {"[x", "-x", "^x"}},
    {{"e:[[:x]"}, kExcl, {"x", "deep/a/bar/x"}},
    {{"e:[[:]x"}, kExcl, {"[x"}},
    {{"e:[[:]]x"}, kExcl, {}},
    {{"e:[[:alpha:]]]"}, kExcl, {"a]"}},
    {{"e:-x"}, kExcl, {"-x"}},
    {{"e:\\-x"}, kExcl, {}},
    {{"e:[\\[-\\]]x"}, kExcl, {"[x"}},
    {{"e:*\?c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:a*\?"}, kExcl, {"a.c", "a.h", "a.o", "ab", "a-b", "a.c ", "a]", "bar/foo/a.c", "dir1/ab/",
     ".git/objects/ab/"}},
    {{"e:**\?c"}, kExcl, {"a.c", "b.c", " a.c", "bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c",
     "dir1/foo/b.c"}},
    {{"e:/*\?r"}, kExcl, {"st*r", "star", "bar/"}},
    {{"e:*[a-c]c"}, kExcl, {}},
    {{"e:**[!.]c"}, kExcl, {}},
    {{"e:*\\\?m"}, kExcl, {"q\?m"}},
    {{"e:**\\*r"}, kExcl, {"st*r"}},
    {{"i:*/", "e:/**\?/*\?"}, kExcl, {"bar/a", "bar/b.o", "bar/foo/a.c", "bar/foo/bar", "bar/baz/foo",
     "bar/baz/x.c", "dir1/a", "dir1/c", "dir1/ab/c", "dir1/ab/foo/bar/a.c", "dir1/ab/foo/bar/b",
     "dir1/foo/bar", "dir1/foo/b.c", "dir1/st*r2", "deep/a/b/c/d.txt", "deep/a/b/foo", "deep/a/bar/x",
     ".git/config", ".git/objects/ab/cd", "foo.d/foo"}},
    {{"i:*/", "e:b*/*\?r"}, kExcl, {}},
    {{"i:*/", "e:**/*a*/**\?c"}, kExcl, {"bar/foo/a.c", "bar/baz/x.c", "dir1/ab/foo/bar/a.c"}},
};

// Rules that still need merge support, and invalid side/modifier combinations.
const char* const kUnsupported[] = {
    ": .f", ". f", "merge f", "dir-merge .f", "-C",
    "Hs foo", "Hr foo", "Ss foo", "Sr foo", "Ps foo", "Pr foo", "Rs foo", "Rr foo",
    "HC foo", "-e foo", "-n foo", "-w foo",
};

std::string write_temp(std::string_view content) {
  const char* dir = std::getenv("TMPDIR");
  std::string path = std::string(dir && *dir ? dir : "/tmp") + "/xsync_filter_test.XXXXXX";
  const int fd = mkstemp(path.data());
  std::FILE* f = fd < 0 ? nullptr : fdopen(fd, "wb");
  if (!f || std::fwrite(content.data(), 1, content.size(), f) != content.size() || std::fclose(f) != 0) {
    std::perror("cannot write temp file");
    std::exit(2);
  }
  return path;
}

bool apply(FilterList& fl, std::string_view spec, std::string* err) {
  const std::string_view val = spec.substr(2);
  switch (spec[0]) {
    case 'e': fl.add_pattern(val, false); return true;
    case 'i': fl.add_pattern(val, true); return true;
    case 'f': return fl.add_filter(val, err);
    default: {
      const std::string path = write_temp(val);
      const bool ok = fl.add_from_file(path, spec[0] == 'I', err);
      std::remove(path.c_str());
      return ok;
    }
  }
}

std::string printable(std::string_view s) {
  std::string out;
  for (const char c : s) {
    if (c == '\n') out += "\\n";
    else if (c == '\r') out += "\\r";
    else if (c == '\t') out += "\\t";
    else out += c;
  }
  return out;
}

std::string_view rel_of(std::string_view entry) {
  return entry.back() == '/' ? entry.substr(0, entry.size() - 1) : entry;
}

void test_table() {
  for (const Case& c : kCases) {
    std::string name;
    for (const char* r : c.rules) name += (name.empty() ? "" : " | ") + printable(r);

    FilterList fl;
    std::string err;
    bool ok = true;
    for (const char* r : c.rules) ok = ok && apply(fl, r, &err);
    if (c.mode == kError) {
      CHECK(!ok && !err.empty(), "[%s] should have been rejected", name.c_str());
      continue;
    }
    CHECK(ok, "[%s] rejected: %s", name.c_str(), err.c_str());
    if (!ok) continue;

    // Walk top-down like rsync, pruning at the directories rsync dropped.
    const std::unordered_set<std::string_view> listed(c.paths.begin(), c.paths.end());
    std::vector<std::string_view> pruned;
    size_t seen = 0;
    for (const std::string_view entry : kTree) {
      const auto under = [&](std::string_view dir) { return entry.starts_with(dir); };
      if (std::any_of(pruned.begin(), pruned.end(), under)) continue;
      const bool is_dir = entry.back() == '/';
      const bool in_list = listed.contains(entry);
      const bool want = (c.mode == kExcl) == in_list;
      seen += in_list;
      CHECK(fl.excluded(rel_of(entry), is_dir) == want, "[%s] '%s' should be %s", name.c_str(),
            entry.data(), want ? "excluded" : "included");
      if (want && is_dir) pruned.push_back(entry);
    }
    CHECK(seen == listed.size(), "[%s] table row names unknown or unreachable entries", name.c_str());

    // to_strings() -> add_filter() must reproduce the list exactly, for every path and either type.
    FilterList rt;
    bool same = true;
    for (const std::string& s : fl.to_strings()) same = same && rt.add_filter(s, &err);
    same = same && rt.to_strings() == fl.to_strings() && rt.empty() == fl.empty();
    for (const std::string_view entry : kTree) {
      const std::string_view rel = rel_of(entry);
      for (const bool d : {false, true}) same = same && fl.excluded(rel, d) == rt.excluded(rel, d);
    }
    CHECK(same, "[%s] to_strings() round trip differs", name.c_str());
  }
}

void test_api() {
  FilterList fl;
  std::string err;
  CHECK(fl.empty(), "new list");
  CHECK(fl.to_strings().empty(), "new list");
  CHECK(!fl.excluded("a.o", false), "empty list excludes nothing");

  fl.add_pattern("*.o", false);
  CHECK(!fl.empty(), "after add_pattern");
  CHECK(fl.excluded("a.o", false) && fl.excluded("d/a.o", true) && !fl.excluded("a.c", false), "*.o");
  CHECK(!fl.excluded("", false) && !fl.excluded("", true), "empty path never matches");

  fl.add_pattern("/foo/", true);
  CHECK(fl.add_filter("-! */", &err), "%s", err.c_str());
  CHECK(fl.add_filter("exclude_bar", &err), "%s", err.c_str());
  CHECK(fl.add_filter("include,! x y ", &err), "%s", err.c_str());
  fl.add_pattern("+ keep", false);
  fl.add_pattern("- drop", true);
  fl.add_pattern("", false);  // ignored, as by rsync
  CHECK(fl.add_filter("", &err), "empty -f rule is ignored");
  const std::vector<std::string> want = {"- *.o", "+ /foo/", "-! */", "- bar", "+! x y ", "+ keep", "- drop"};
  CHECK(fl.to_strings() == want, "to_strings() text");

  // Clearing: "!" via any entry point empties the list.
  fl.add_pattern("!", true);
  CHECK(fl.empty() && fl.to_strings().empty(), "'!' pattern clears");
  fl.add_pattern("x", false);
  CHECK(fl.add_filter("clear", &err) && fl.empty(), "'clear' rule clears");
  fl.add_pattern("x", false);
  CHECK(fl.add_filter("!", &err) && fl.empty(), "'!' rule clears");

  // Rejected rules leave the list untouched and name the rule in the message.
  for (const char* rule : kUnsupported) {
    err.clear();
    CHECK(!fl.add_filter(rule, &err), "'%s' should be unsupported", rule);
    CHECK(err.find(rule) != err.npos, "error for '%s' should name the rule, got '%s'", rule, err.c_str());
    CHECK(fl.empty(), "'%s' must not add a rule", rule);
  }
  CHECK(!fl.add_filter("x foo", nullptr), "null err is tolerated");

  // Files.
  err.clear();
  CHECK(!fl.add_from_file("/nonexistent/xsync/filter", false, &err), "missing file");
  CHECK(err.find("/nonexistent/xsync/filter") != err.npos, "I/O error names the file: %s", err.c_str());
  CHECK(!fl.add_from_file("/nonexistent/xsync/filter", true, nullptr), "missing file, null err");
  CHECK(fl.add_from_file("", false, &err) && fl.empty(), "empty file name is ignored, as by rsync");

  const std::string path = write_temp("*.c\n+ a.o\n*\n");
  CHECK(std::freopen(path.c_str(), "rb", stdin) != nullptr, "freopen stdin");
  CHECK(fl.add_from_file("-", false, &err), "stdin: %s", err.c_str());
  std::remove(path.c_str());
  const std::vector<std::string> from_stdin = {"- *.c", "+ a.o", "- *"};
  CHECK(fl.to_strings() == from_stdin, "\"-\" reads rules from stdin");
  CHECK(fl.excluded("a.c", false) && !fl.excluded("a.o", false) && fl.excluded("d", true), "stdin rules");
}

// Paths longer than any internal buffer (rsync itself cannot produce these).
void test_long_paths() {
  FilterList fl;
  fl.add_pattern("**/foo", false);
  fl.add_pattern("bar/***", false);
  fl.add_pattern("x*/**baz", false);
  for (size_t len = 4088; len <= 4104; ++len) {
    const std::string stem(len - 4, 'x');
    CHECK(fl.excluded(stem + "/foo", false), "len %zu foo", len);
    CHECK(fl.excluded(stem + "/bar", true), "len %zu bar dir", len);
    CHECK(!fl.excluded(stem + "/bar", false), "len %zu bar file", len);
    CHECK(fl.excluded(stem + "/baz", false), "len %zu baz", len);
    CHECK(!fl.excluded(stem + "/fox", true), "len %zu fox", len);
  }
  const std::string deep = std::string(100000, 'y') + "/q/foo";
  CHECK(fl.excluded(deep, false) && !fl.excluded(deep + "d", true), "100k path");
}

void test_sides() {
  std::string error;
  for (const auto& prefix : {"H", "S", "P", "R", "-s", "+s", "-r", "+r", "-sr", "+sr"}) {
    FilterList filters, roundtrip;
    CHECK(filters.add_filter(std::string(prefix) + " *.o", &error), "%s", error.c_str());
    for (const auto& rule : filters.to_strings()) CHECK(roundtrip.add_filter(rule, &error), "%s", error.c_str());
    const bool include = prefix[0] == '+' || prefix[0] == 'S' || prefix[0] == 'R';
    const bool sender = prefix[0] == 'H' || prefix[0] == 'S' || std::string_view(prefix).find('s') != std::string_view::npos;
    const bool receiver = prefix[0] == 'P' || prefix[0] == 'R' || std::string_view(prefix).find('r') != std::string_view::npos;
    CHECK(filters.excluded("d/a.o", false) == (sender && !include), "sender %s", prefix);
    for (const bool deleted : {false, true}) {
      CHECK(filters.protected_from_deletion("d/a.o", false, deleted) == (receiver && !include), "receiver %s", prefix);
      CHECK(roundtrip.protected_from_deletion("d/a.o", false, deleted) == (receiver && !include), "roundtrip %s", prefix);
    }
  }
  FilterList defaults;
  defaults.add_pattern("*.o", false);
  CHECK(defaults.protected_from_deletion("a.o", false), "default receiver protection");
  CHECK(!defaults.protected_from_deletion("a.o", false, true), "delete-excluded removes default protection");
  FilterList perish;
  CHECK(perish.add_filter("-p *.o", &error), "%s", error.c_str());
  CHECK(perish.protected_from_deletion("dir/a.o", false), "perishable at existing directory");
  CHECK(!perish.protected_from_deletion("dir/a.o", false, false, true), "perishable inside deleted directory");
  FilterList absolute;
  CHECK(absolute.add_filter("-/ /tmp/src/a.o", &error), "%s", error.c_str());
  CHECK(absolute.excluded("a.o", false, "/tmp/src/a.o"), "absolute match");
  CHECK(!absolute.excluded("a.o", false, "/tmp/dst/a.o"), "absolute mismatch");
  FilterList xattr;
  CHECK(xattr.add_filter("-x *", &error), "%s", error.c_str());
  CHECK(!xattr.excluded("file", false) && !xattr.protected_from_deletion("file", false), "xattr rules ignore filenames");
}

}  // namespace

int main() {
  test_table();
  test_api();
  test_long_paths();
  test_sides();
  std::printf("%d checks, %d failures\n", g_checks, g_failures);
  return g_failures ? 1 : 0;
}
