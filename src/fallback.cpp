#include "fallback.h"
#include "arguments.h"
#include "progress.h"
#include <sys/stat.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <vector>

namespace {
std::vector<std::string> arguments;
bool enabled = true;
mode_t original_umask;
struct stat self_stat {};
bool have_self_stat = false;

std::string find_rsync() {
  const char* path = getenv("PATH");
  std::string dirs = path ? path : "/usr/bin:/bin";
  size_t start = 0;
  do {
    size_t end = dirs.find(':', start);
    std::string dir = dirs.substr(start, end == std::string::npos ? end : end - start);
    std::string candidate = (dir.empty() ? "." : dir) + "/rsync";
    struct stat st {};
    if (access(candidate.c_str(), X_OK) == 0 && stat(candidate.c_str(), &st) == 0 && S_ISREG(st.st_mode) &&
        !(have_self_stat && st.st_dev == self_stat.st_dev && st.st_ino == self_stat.st_ino)) return candidate;
    if (end == std::string::npos) break;
    start = end + 1;
  } while (true);
  return {};
}
}  // namespace

void init_fallback(int argc, char** argv) {
  original_umask = umask(0);
  umask(original_umask);
#ifdef __APPLE__
  uint32_t size = 0;
  _NSGetExecutablePath(nullptr, &size);
  std::vector<char> executable(size);
  if (_NSGetExecutablePath(executable.data(), &size) == 0) have_self_stat = stat(executable.data(), &self_stat) == 0;
#else
  have_self_stat = stat("/proc/self/exe", &self_stat) == 0;
#endif
  const char* setting = getenv("XSYNC_FALLBACK");
  enabled = !setting || strcmp(setting, "0") != 0;
  bool operands = false;
  bool server = false;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    if (operands || a.size() < 2 || a[0] != '-') { arguments.push_back(a); continue; }
    if (a == "--") { operands = true; arguments.push_back(a); continue; }
    if (a == "--server" || a == "--install" || a.rfind("--install=", 0) == 0) server = true;
    if (a == "--no-fallback") { enabled = false; continue; }
    if (a == "--fallback") { enabled = true; continue; }
    if (a == "--atomic" || a == "--no-atomic" || a == "--clone" || a == "--no-clone") continue;
    if (a == "--jobs" || a.rfind("--jobs=", 0) == 0) {
      if (a == "--jobs" && i + 1 < argc) ++i;
      continue;
    }
    if (a.rfind("--", 0) == 0) {
      arguments.push_back(a);
      if (a.find('=') == std::string::npos && long_option_takes_value(a.substr(2)) && i + 1 < argc) arguments.push_back(argv[++i]);
      continue;
    }
    // Strip -j from bundles, leaving the original rsync flags and option values.
    std::string short_flags = "-";
    for (size_t k = 1; k < a.size(); ++k) {
      char flag = a[k];
      if (flag != 'j') short_flags += flag;
      if (std::strchr("ej@fBTM", flag)) {
        if (flag != 'j') short_flags += a.substr(k + 1);
        if (short_flags.size() > 1) arguments.push_back(short_flags);
        short_flags = "-";
        if (k + 1 == a.size() && i + 1 < argc) {
          ++i;
          if (flag != 'j') arguments.push_back(argv[i]);
        }
        break;
      }
    }
    if (short_flags.size() > 1) arguments.push_back(short_flags);
  }
  if (server) enabled = false;  // The binary protocol server must never exec rsync.
}

bool fallback_enabled() { return enabled; }

[[noreturn]] void fallback_to_rsync(const std::string& reason, int strict_code) {
  progress_stop(false);
  if (!enabled) {
    fprintf(stderr, "xsync: %s (fallback disabled)\n", reason.c_str());
    std::exit(strict_code);
  }
  std::string binary = find_rsync();
  if (binary.empty()) {
    fprintf(stderr, "xsync: %s; no real rsync executable found in PATH\n", reason.c_str());
    std::exit(127);
  }
  // An explicit --rsync-path is a command, and is preserved exactly. If it names
  // xsync, users must choose an rsync-capable wrapper before enabling fallback.
  std::vector<char*> args{binary.data()};
  for (auto& arg : arguments) args.push_back(arg.data());
  args.push_back(nullptr);
  std::string notice = reason;
  for (char& ch : notice) if (ch == '\n' || ch == '\r') ch = ' ';
  fprintf(stderr, "xsync: falling back to rsync: %s\n", notice.c_str());
  fflush(nullptr);
  umask(original_umask);
  execv(binary.c_str(), args.data());
  fprintf(stderr, "xsync: cannot execute rsync: %s\n", strerror(errno));
  std::exit(127);
}
