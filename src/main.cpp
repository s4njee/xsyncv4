// xsync — rsync-compatible command line front end.
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <climits>
#include <cmath>
#include <csignal>
#include <cstdlib>

#include "engine.h"
#include "progress.h"
#include "fallback.h"
#include "install.h"
#include "transport.h"
#include "arguments.h"
#include "output.h"
#include "listing.h"

namespace {

[[noreturn]] void usage_error(const std::string& msg) {
  if (msg.starts_with("failed to open merge file ") || msg.starts_with("failed to read merge file "))
    die(RERR_FILEIO, "%s", msg.c_str());
  if (msg.find("not supported") != std::string::npos || msg.rfind("unsupported", 0) == 0 ||
      msg.rfind("--info supports", 0) == 0 || msg.find("supports only zstd or none") != std::string::npos)
    fallback_to_rsync(msg);
  fprintf(stderr, "xsync: %s\nxsync error: syntax or usage error (code 1)\n", msg.c_str());
  exit(RERR_SYNTAX);
}

void print_version() {
  printf("xsync  version %s  protocol version %u  git %s\n", XSYNC_VERSION, PROTO_VERSION, XSYNC_GIT_HASH);
  printf("A fast, parallel rsync work-alike. Native transfers use xsync on both ends;\n"
         "missing remote support falls back to rsync unless --no-fallback is set.\n");
}

void print_help() {
  print_version();
  fputs(R"(
Usage: xsync [OPTION]... SRC [SRC]... DEST
  or   xsync [OPTION]... SRC
  or   xsync [OPTION]... SRC [SRC]... [USER@]HOST:DEST
  or   xsync [OPTION]... [USER@]HOST:SRC [DEST]

Options (same meaning as rsync):
 -v, --verbose            increase verbosity
 -q, --quiet              suppress non-error messages
 -c, --checksum           skip based on checksum, not mod-time & size
 -a, --archive            archive mode; equals -rlptgoD
 -r, --recursive          recurse into directories
 -d, --dirs               transfer directories without recursing
     --list-only          list source entries; do not transfer or change DEST
 -H, --hard-links         preserve hard links within the transferred tree
 -l, --links              copy symlinks as symlinks
     --safe-links         skip symlinks that point outside the transfer tree
 -L, --copy-links         transform symlink into referent file/dir
 -p, --perms              preserve permissions
 -o, --owner              preserve owner (super-user only)
 -g, --group              preserve group
 -D                       same as --devices --specials
 -t, --times              preserve modification times
 -O, --omit-dir-times     omit directories from --times
 -J, --omit-link-times    omit symlinks from --times
 -n, --dry-run            perform a trial run with no changes made
 -W, --whole-file         send the whole file; disable resume and block matching
     --no-whole-file      enable verified-prefix resume again
 -x, --one-file-system    don't cross filesystem boundaries
 -e, --rsh=COMMAND        specify the remote shell to use
     --rsync-path=PROGRAM specify the xsync to run on the remote machine
     --no-fallback        fail instead of re-executing rsync for missing support
     --fallback           enable fallback (overrides XSYNC_FALLBACK=0)
     --existing           skip creating new files on receiver
     --ignore-existing    skip updating files that exist on receiver
     --delete             delete extraneous files from dest dirs
     --delete-excluded    also delete excluded files from dest dirs
     --ignore-errors      delete even when the sender encountered I/O errors
     --max-delete=NUM     delete at most NUM entries (exit 25 if exceeded)
     --force              force deletion of dirs even if not empty
     --max-size=SIZE      don't transfer any file larger than SIZE
     --min-size=SIZE      don't transfer any file smaller than SIZE
     --bwlimit=RATE       limit bytes sent/copied per second (bare RATE: KiB/s)
     --timeout=SECONDS    remote idle I/O timeout (0 disables; exits with code 30)
     --partial            keep partially transferred files
     --inplace            update destination files in-place
     --mkpath             create the destination's path component
     --numeric-ids        don't map uid/gid values by user/group name
 -u, --update             skip files that are newer on the receiver
 -I, --ignore-times       don't skip files that match size and time
     --size-only          skip files that match in size
 -@, --modify-window=NUM  set the accuracy for mod-time comparisons
 -z, --compress           compress file data during the transfer (zstd)
     --compress-level=NUM explicitly set compression level
 -f, --filter=RULE        add a file-filtering RULE
 -F                       merge .rsync-filter files (twice also excludes them)
 -C, --cvs-exclude        exclude CVS defaults and .cvsignore patterns
     --exclude=PATTERN    exclude files matching PATTERN
     --exclude-from=FILE  read exclude patterns from FILE
     --include=PATTERN    don't exclude files matching PATTERN
     --include-from=FILE  read include patterns from FILE
     --stats              give some file-transfer stats
 -h, --human-readable     output numbers in a human-readable format
     --progress           show live per-file and whole-transfer progress
 -P                       same as --partial --progress
 -i, --itemize-changes    output a change-summary for all updates
 -8, --8-bit-output       retain high bytes in names; escape unsafe control bytes
     --out-format=FORMAT  file lines: %i %n %L %l %o %f %b %t %% (optional width)
     --log-file=FILE      append the same stdout stream to FILE
     --version, --help

Documented compatibility no-ops:
 -s, --protect-args, --secluded-args
                          paths always travel as protocol data, not shell text
     --blocking-io, --no-blocking-io
                          transport polling handles either pipe mode internally
     --no-motd            no daemon transport or daemon greeting exists

xsync extensions:
     --install=HOST       explicitly install the matching release at ~/.local/bin
                          refuses newer versions unless --force is supplied
 -j, --jobs=N             number of worker threads (default: performance cores)
     --no-clone           always copy file data, even where a copy-on-write clone
                          (APFS, same volume, with -pt) would be possible
     --atomic             create new files via temp file + rename (default)
     --no-atomic          create new byte-copied files directly (fewer renames;
                          a crash can leave truncated files under final names)
)", stdout);
}

i64 parse_size(const std::string& s, const char* opt) {
  char* end = nullptr;
  double v = strtod(s.c_str(), &end);
  if (end == s.c_str() || v < 0) usage_error(std::string("--") + opt + " value is invalid: " + s);
  std::string suf(end);
  for (char& c : suf) c = (char)tolower(c);
  double mul = 1;
  if (suf.empty() || suf == "b") mul = 1;
  else if (suf == "k" || suf == "kib") mul = 1024.0;
  else if (suf == "m" || suf == "mib") mul = 1024.0 * 1024;
  else if (suf == "g" || suf == "gib") mul = 1024.0 * 1024 * 1024;
  else if (suf == "t" || suf == "tib") mul = 1024.0 * 1024 * 1024 * 1024;
  else if (suf == "kb") mul = 1e3;
  else if (suf == "mb") mul = 1e6;
  else if (suf == "gb") mul = 1e9;
  else if (suf == "tb") mul = 1e12;
  else usage_error(std::string("--") + opt + " value is invalid: " + s);
  return (i64)(v * mul);
}

struct Parsed {
  std::vector<std::string> args;
  std::string install;
  bool server = false;
};

u64 parse_rate(const std::string& value) {
  char* end;
  errno = 0;
  long double number = strtold(value.c_str(), &end);
  if (errno || end == value.c_str() || !std::isfinite(number) || number < 0)
    usage_error("--bwlimit requires a nonnegative rate: " + value);
  std::string suffix(end);
  for (char& c : suffix) c = (char)tolower((unsigned char)c);
  long double multiplier = 1024;
  if (suffix == "b") multiplier = 1;
  else if (!suffix.empty()) {
    size_t power = std::string("kmgtp").find(suffix[0]);
    if (power == std::string::npos || (suffix.size() != 1 && suffix.substr(1) != "b" && suffix.substr(1) != "ib"))
      usage_error("--bwlimit has an invalid suffix: " + value);
    multiplier = std::pow(suffix.size() == 2 ? 1000.L : 1024.L, (int)power + 1);
  }
  long double kib = std::floor((number * multiplier + 512) / 1024);
  if (kib > (long double)(INT64_MAX / 1024) || (number > 0 && kib < 1))
    usage_error("--bwlimit rate is out of range: " + value);
  return (u64)kib * 1024;
}

u32 parse_timeout(const std::string& value) {
  if (value.empty() || !std::all_of(value.begin(), value.end(), [](unsigned char c) { return std::isdigit(c); }))
    usage_error("--timeout requires nonnegative integer seconds");
  errno = 0;
  unsigned long long seconds = strtoull(value.c_str(), nullptr, 10);
  if (errno || seconds > INT_MAX) usage_error("--timeout seconds are out of range");
  return (u32)seconds;
}

void set_archive(Options& o) { o.recursive = o.links = o.perms = o.times = o.group = o.owner = o.devices = o.specials = true; }

Parsed parse(int argc, char** argv) {
  Options& o = g_opt;
  Parsed p;
  o.compress_level = 3;
  o.direct_new = false;
  o.clone = true;
  o.max_delete = -1;
  bool no_more = false;
  std::string err;
  int filter_files = 0;

  auto long_opt = [&](const std::string& name, const std::string* val, int& i) {
    auto need = [&]() -> std::string {
      if (val) return *val;
      if (i + 1 >= argc) usage_error("--" + name + ": option requires an argument");
      return argv[++i];
    };
    auto flag = [&](bool& b, const char* n) {
      if (name == n) return b = true, true;
      if (name == std::string("no-") + n) return b = false, true;
      return false;
    };
    if (name == "server") p.server = true;
    else if (name == "fallback" || name == "no-fallback") {}  // captured before parsing
    else if (name == "install") p.install = need();
    else if (name == "version") print_version(), exit(0);
    else if (name == "help") print_help(), exit(0);
    else if (name == "verbose") o.verbose++;
    else if (name == "no-verbose") o.verbose = 0;
    else if (name == "quiet") o.quiet = true;
    else if (name == "itemize-changes") o.itemize = true, ++o.itemize_level;
    else if (name == "no-itemize-changes") o.itemize = false, o.itemize_level = 0;
    else if (name == "archive") set_archive(o);
    else if (flag(o.list_only, "list-only")) {}
    else if (flag(o.recursive, "recursive") || flag(o.dirs, "dirs") || flag(o.links, "links") || flag(o.copy_links, "copy-links") ||
             flag(o.perms, "perms") || flag(o.times, "times") || flag(o.group, "group") || flag(o.owner, "owner") ||
             flag(o.devices, "devices") || flag(o.specials, "specials") || flag(o.compress, "compress") || flag(o.dry_run, "dry-run") ||
             flag(o.force, "force") || flag(o.update, "update") || flag(o.checksum, "checksum") || flag(o.size_only, "size-only") ||
             flag(o.ignore_times, "ignore-times") || flag(o.ignore_existing, "ignore-existing") || flag(o.existing, "existing") ||
             flag(o.one_fs, "one-file-system") || flag(o.inplace, "inplace") || flag(o.omit_dir_times, "omit-dir-times") ||
             flag(o.omit_link_times, "omit-link-times") || flag(o.numeric_ids, "numeric-ids") ||
             flag(o.partial, "partial") || flag(o.progress, "progress") || flag(o.stats, "stats") || flag(o.mkpath, "mkpath") ||
             flag(o.clone, "clone") || flag(o.ignore_errors, "ignore-errors") || flag(o.safe_links, "safe-links")) {
      if (name == "dirs" || name == "no-dirs") o.dirs_explicit = true;
    } else if (name == "ignore-non-existing") o.existing = true;
    else if (name == "no-D") o.devices = o.specials = false;
    else if (name == "cvs-exclude") o.cvs_exclude = true;
    else if (name == "atomic") o.direct_new = false;
    else if (name == "no-atomic") o.direct_new = true;
    else if (name == "delete-before") o.del = o.delete_before = true;
    else if (name == "delete" || name == "del" || name == "delete-during" || name == "delete-delay" ||
             name == "delete-after")
      o.del = true;
    else if (name == "delete-excluded") o.del = o.delete_excluded = true;
    else if (name == "human-readable") o.human++, o.human_ungrouped = false;
    else if (name == "no-human-readable" || name == "no-h") o.human = 0, o.human_ungrouped = true;
    else if (name == "rsh") o.rsh = need(), o.rsh_set = true;
    else if (name == "rsync-path") o.rsync_path = need();
    else if (name == "out-format") {
      o.out_format = need();
      o.out_format_set = true;
      if (!output_format_supported(o.out_format)) usage_error("unsupported --out-format escape (native: %i %n %L %l %o %f %b %t %%)");
    }
    else if (name == "log-file") {
      o.log_file = need();
      if (o.log_file.empty()) usage_error("--log-file requires a non-empty path");
    }
    else if (name == "jobs") o.jobs = atoi(need().c_str());
    else if (name == "max-delete") {
      std::string value = need();
      char* end;
      errno = 0;
      o.max_delete = strtoll(value.c_str(), &end, 10);
      if (errno || end == value.c_str() || *end || o.max_delete < 0) usage_error("--max-delete requires a nonnegative integer");
    }
    else if (name == "max-size") o.max_size = parse_size(need(), "max-size");
    else if (name == "min-size") o.min_size = parse_size(need(), "min-size");
    else if (name == "bwlimit") o.bwlimit = parse_rate(need());
    else if (name == "timeout") o.timeout = parse_timeout(need());
    else if (name == "modify-window") o.modify_window = atoi(need().c_str());
    else if (name == "compress-level" || name == "zl") o.compress_level = atoi(need().c_str());
    else if (name == "compress-choice" || name == "zc") {
      std::string choice = need();
      if (choice == "none") o.compress = false, o.compress_level = -1000;
      else if (choice != "zstd") usage_error("--" + name + " supports only zstd or none");
    } else if (name == "exclude") o.filters.add_pattern(need(), false);
    else if (name == "include") o.filters.add_pattern(need(), true);
    else if (name == "exclude-from" || name == "include-from") {
      if (!o.filters.add_from_file(need(), name == "include-from", &err)) usage_error(err);
    } else if (name == "filter") {
      if (!o.filters.add_filter(need(), &err)) usage_error(err);
    } else if (name == "info") {
      std::string v = need();
      size_t start = 0;
      do {
        size_t comma = v.find(',', start);
        std::string item = v.substr(start, comma == std::string::npos ? comma : comma - start);
        std::transform(item.begin(), item.end(), item.begin(), [](unsigned char c) { return (char)tolower(c); });
        if (item == "progress2") o.progress = true;
        else if (item == "progress0") o.progress = false;
        else if (item == "stats2") o.stats = true;
        else if (item == "stats0") o.stats = false;
        else usage_error("--info supports progress2, progress0, stats2, stats0 only");
        if (comma == std::string::npos) break;
        start = comma + 1;
      } while (true);
    } else if (flag(o.hard_links, "hard-links") || flag(o.whole_file, "whole-file") || flag(o.raw_names, "8-bit-output")) {}
    else if (name == "protect-args" || name == "secluded-args" ||
               name == "blocking-io" || name == "no-blocking-io" || name == "no-motd") {
      // These intrinsic behaviours are listed with their reasons in --help.
    } else {
      static const char* unsupported[] = {
          "acls", "xattrs", "backup", "backup-dir", "suffix", "link-dest", "compare-dest", "copy-dest", "files-from",
          "from0", "relative", "chmod", "chown", "usermap", "groupmap", "append", "append-verify", "partial-dir",
          "delay-updates", "fuzzy", "remove-source-files", "keep-dirlinks", "copy-dirlinks", "copy-unsafe-links",
          "munge-links", "executability", "atimes", "crtimes", "prune-empty-dirs", "daemon", "port", "password-file",
          "write-batch", "read-batch", "only-write-batch", "super", "fake-super", "temp-dir",
          "iconv", "checksum-seed", "address", "sockopts", "stop-after", "stop-at", "max-alloc", "write-devices", "copy-devices",
          "delete-missing-args", "ignore-missing-args", "trust-sender", "copy-as", "early-input", "remote-option",
          "contimeout", "sparse", "no-sparse", "fsync", "preallocate", "skip-compress",
          "block-size", "checksum-choice", "cc", "log-file-format", "debug", "outbuf",
          "inc-recursive", "no-inc-recursive", "i-r", "no-i-r", "no-protect-args", "old-args",
          "ipv4", "ipv6", "msgs2stderr", "no-msgs2stderr", "new-compress", "old-compress", "no-implied-dirs",
          "implied-dirs", "open-noatime"};
      for (const char* u : unsupported)
        if (name == u) usage_error("--" + name + " is not supported by xsync");
      usage_error("--" + name + ": unknown option");
    }
  };

  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (no_more || a.size() < 2 || a[0] != '-') {
      p.args.push_back(a);
      continue;
    }
    if (a == "--") {
      no_more = true;
      continue;
    }
    if (a[1] == '-') {
      size_t eq = a.find('=');
      if (eq == std::string::npos) long_opt(a.substr(2), nullptr, i);
      else {
        std::string v = a.substr(eq + 1);
        long_opt(a.substr(2, eq - 2), &v, i);
      }
      continue;
    }
    for (size_t k = 1; k < a.size(); k++) {
      char c = a[k];
      auto need = [&]() -> std::string {
        std::string v = a.substr(k + 1);
        k = a.size();
        if (!v.empty()) return v[0] == '=' ? v.substr(1) : v;
        if (i + 1 >= argc) usage_error(std::string("-") + c + ": option requires an argument");
        return argv[++i];
      };
      switch (c) {
        case 'v': o.verbose++; break;
        case 'q': o.quiet = true; break;
        case 'a': set_archive(o); break;
        case 'r': o.recursive = true; break;
        case 'd': o.dirs = o.dirs_explicit = true; break;
        case 'l': o.links = true; break;
        case 'L': o.copy_links = true; break;
        case 'p': o.perms = true; break;
        case 't': o.times = true; break;
        case 'g': o.group = true; break;
        case 'o': o.owner = true; break;
        case 'D': o.devices = o.specials = true; break;
        case 'z': o.compress = true; break;
        case 'n': o.dry_run = true; break;
        case 'u': o.update = true; break;
        case 'c': o.checksum = true; break;
        case 'I': o.ignore_times = true; break;
        case 'x': o.one_fs = true; break;
        case 'O': o.omit_dir_times = true; break;
        case 'J': o.omit_link_times = true; break;
        case 'i': o.itemize = true; ++o.itemize_level; break;
        case 'h': o.human++; o.human_ungrouped = false; break;
        case 'P': o.partial = o.progress = true; break;
        case 'W': o.whole_file = true; break;
        case 's': break;  // documented compatibility no-op
        case '8': o.raw_names = true; break;
        case 'S': usage_error("--sparse is not supported by xsync");
        case '4': usage_error("--ipv4 is not supported by xsync");
        case '6': usage_error("--ipv6 is not supported by xsync");
        case 'e': o.rsh = need(); o.rsh_set = true; break;
        case 'j': o.jobs = atoi(need().c_str()); break;
        case '@': o.modify_window = atoi(need().c_str()); break;
        case 'f':
          if (!o.filters.add_filter(need(), &err)) usage_error(err);
          break;
        case 'V': print_version(); exit(0);
        case 'B': usage_error("--block-size is not supported by xsync");
        case 'T': usage_error("--temp-dir is not supported by xsync");
        case 'M': usage_error("--remote-option is not supported by xsync");
        case 'H': o.hard_links = true; break;
        case 'A': usage_error("--acls is not supported by xsync");
        case 'X': usage_error("--xattrs is not supported by xsync");
        case 'R': usage_error("--relative is not supported by xsync");
        case 'b': usage_error("--backup is not supported by xsync");
        case 'C': o.cvs_exclude = true; break;
        case 'F':
          if (++filter_files == 1) {
            if (!o.filters.add_filter(": /.rsync-filter", &err)) usage_error(err);
          } else if (filter_files == 2) o.filters.add_pattern(".rsync-filter", false);
          break;
        case 'm': usage_error("--prune-empty-dirs is not supported by xsync");
        case 'y': usage_error("--fuzzy is not supported by xsync");
        default: usage_error(std::string("-") + c + ": unknown option");
      }
    }
  }
  if (o.copy_links) o.links = false;
  if (!p.server && p.install.empty() && p.args.size() == 1) o.list_only = true;
  if (o.list_only && !o.dirs_explicit && !o.recursive) o.dirs = true;
  if (o.compress_level == -1000) o.compress_level = 3;
  if (o.del && !o.recursive && !o.dirs) usage_error("--delete does not work without --recursive (-r) or --dirs (-d).");
  if (o.quiet) o.verbose = 0;
  if (o.bwlimit) o.clone = false;  // A clone must not bypass a requested copy rate.
  if (o.cvs_exclude && !o.filters.add_cvs_option(&err)) usage_error(err);
  return p;
}

void on_signal(int) {
  if (g_stop.fetch_add(1) >= 1) {
    static const char show[] = "\x1b[?25h\n";
    if (g_progress_on) (void)!write(2, show, sizeof show - 1);
    _exit(RERR_SIGNAL);
  }
}

const char* rerr_name(int c) {
  switch (c) {
    case RERR_SYNTAX: return "syntax or usage error";
    case RERR_PROTOCOL: return "protocol incompatibility";
    case RERR_FILESELECT: return "errors selecting input/output files, dirs";
    case RERR_UNSUPPORTED: return "requested action not supported";
    case RERR_STARTCLIENT: return "error starting client-server protocol";
    case RERR_FILEIO: return "error in file IO";
    case RERR_STREAMIO: return "error in rsync protocol data stream";
    case RERR_IPC: return "error in IPC code";
    case RERR_SIGNAL: return "received SIGINT, SIGTERM, or SIGHUP";
    case RERR_PARTIAL: return "some files/attrs were not transferred (see previous errors)";
    case RERR_VANISHED: return "some files vanished before they could be transferred";
    case RERR_DEL_LIMIT: return "the --max-delete limit stopped deletions";
    case RERR_TIMEOUT: return "timeout in data send/receive";
    case RERR_CMD_NOTFOUND: return "remote command not found";
    default: return "unexplained error";
  }
}

}  // namespace

void print_summary(u64 t0) {
  const Options& o = g_opt;
  Stats& s = g_stats;
  double el = std::max(1e-6, (double)(now_ns() - t0) / 1e9);
  u64 sent = s.wire_sent.load(), recv = s.wire_recv.load();
  if (sent == 0 && recv == 0) sent = o.dry_run ? 0 : s.xfer_bytes.load();  // local copy: nothing on a wire
  u64 total = s.bytes_seen.load();
  std::string out;
  if (o.stats) {
    u64 nreg = s.files_seen, ndir = s.dirs_seen, nlnk = s.links_seen, nspec = s.specials_seen;
    u64 created = s.created_files + s.created_dirs + s.created_links + s.created_specials;
    out += "\nNumber of files: " + fmt_num(nreg + ndir + nlnk + nspec) + " (reg: " + fmt_num(nreg) + ", dir: " + fmt_num(ndir) +
           (nlnk ? ", link: " + fmt_num(nlnk) : "") + (nspec ? ", special: " + fmt_num(nspec) : "") + ")\n";
    out += "Number of created files: " + fmt_num(created) + " (reg: " + fmt_num(s.created_files) + ", dir: " + fmt_num(s.created_dirs) +
           (s.created_links ? ", link: " + fmt_num(s.created_links) : "") + ")\n";
    out += "Number of deleted files: " + fmt_num(s.deleted) + "\n";
    out += "Number of regular files transferred: " + fmt_num(s.xfer_files) + "\n";
    out += "Total file size: " + fmt_num(total) + " bytes\n";
    out += "Total transferred file size: " + fmt_num(s.xfer_bytes) + " bytes\n";
    out += "Delta literal data: " + fmt_num(s.delta_literal_bytes) + " bytes\n";
    out += "Delta matched data: " + fmt_num(s.delta_matched_bytes) + " bytes\n";
    out += "Total bytes sent: " + fmt_num(sent) + "\n";
    out += "Total bytes received: " + fmt_num(recv) + "\n";
  }
  if (o.verbose > 0 || o.stats) {
    char rate[64], speedup[64];
    snprintf(rate, sizeof rate, "%.2f", (double)(sent + recv) / el);
    std::string r = rate;
    if (!o.human) {  // add thousands separators to the integer part
      size_t dot = r.find('.');
      r = fmt_num(strtoull(r.substr(0, dot).c_str(), nullptr, 10)) + r.substr(dot);
    }
    snprintf(speedup, sizeof speedup, "%.2f", sent + recv ? (double)total / (double)(sent + recv) : 0.0);
    out += "\nsent " + fmt_num(sent) + " bytes  received " + fmt_num(recv) + " bytes  " + r + " bytes/sec\n";
    out += "total size is " + fmt_num(total) + "  speedup is " + speedup + (o.dry_run ? " (DRY RUN)" : "") + "\n";
  }
  if (!out.empty()) output_text(out);
}

int main(int argc, char** argv) {
  signal(SIGPIPE, SIG_IGN);
  auto arguments = effective_arguments(argc, argv);
  std::vector<char*> effective;
  for (auto& argument : arguments) effective.push_back(argument.data());
  init_fallback((int)effective.size(), effective.data());
  Parsed p = parse((int)effective.size(), effective.data());
  output_configure();
  g_umask = umask(0);
  init_ids();
  struct sigaction sa {};
  sa.sa_handler = on_signal;
  sigaction(SIGINT, &sa, nullptr);
  sigaction(SIGTERM, &sa, nullptr);
  sigaction(SIGHUP, &sa, nullptr);
  if (p.server) {
    g_opt.am_server = true;
    return run_server();
  }
  if (!p.install.empty()) {
    if (!p.args.empty()) usage_error("--install cannot be combined with transfer paths");
    return install_remote(p.install, g_opt.force);
  }

  if (p.args.empty()) {
    print_help();
    fprintf(stderr, "xsync error: syntax or usage error (code 1)\n");
    return RERR_SYNTAX;
  }
  std::string dest = p.args.size() == 1 ? "" : p.args.back();
  std::vector<std::string> srcs(p.args.begin(), p.args.end() - (p.args.size() > 1 ? 1 : 0));
  RemoteSpec destination = parse_remote_spec(dest);
  bool remote_dest = !g_opt.list_only && destination.remote, remote_src = false;
  for (auto& s : srcs) {
    RemoteSpec source = parse_remote_spec(s);
    if (source.daemon) usage_error("rsync daemon transfers are not supported by xsync");
    remote_src |= source.remote;
  }
  if (destination.daemon && !g_opt.list_only) usage_error("rsync daemon transfers are not supported by xsync");
  if (remote_src && remote_dest) usage_error("The source and destination cannot both be remote.");

  u64 t0 = now_ns();
  if (!remote_src && !remote_dest) output_start();
  int rc = remote_src || remote_dest ? run_client(srcs, g_opt.list_only ? "" : dest) :
    g_opt.list_only ? run_listing(srcs, listing_output) : run_local(srcs, dest);
  if (g_stop.load()) rc = RERR_SIGNAL;
  if (!rc) rc = g_exit_code.load();
  progress_stop(rc == 0 || rc == RERR_PARTIAL || rc == RERR_VANISHED);
  output_flush();
  if (rc != RERR_SIGNAL) print_summary(t0);
  if (!rc) rc = g_exit_code.load();
  fflush(stdout);
  print_error_summary();
  if (rc == RERR_VANISHED) fprintf(stderr, "xsync warning: %s (code %d)\n", rerr_name(rc), rc);
  else if (rc) fprintf(stderr, "xsync error: %s (code %d)\n", rerr_name(rc), rc);
  if (rc == RERR_SIGNAL) _exit(rc);  // workers may still be parked in syscalls
  return rc;
}
