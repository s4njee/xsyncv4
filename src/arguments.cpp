#include "arguments.h"
#include "common.h"
#include "transport.h"
#include <cstdlib>
#include <cstring>
#include <fstream>

bool long_option_takes_value(const std::string& name) {
  static const std::string names =
      " install rsh rsync-path jobs max-delete max-size min-size modify-window compress-level zl compress-choice zc "
      "exclude include exclude-from include-from filter info backup-dir suffix link-dest compare-dest copy-dest files-from "
      "chmod chown usermap groupmap bwlimit partial-dir port password-file log-file write-batch read-batch only-write-batch "
      "temp-dir iconv checksum-seed address sockopts stop-after stop-at max-alloc copy-as early-input remote-option "
      "timeout contimeout skip-compress block-size checksum-choice cc log-file-format debug out-format outbuf ";
  return names.find(" " + name + " ") != std::string::npos;
}

namespace {
const char* short_values = "ej@fBTM";

// Control invocations must work independently of personal transfer defaults.
bool bypass_defaults(int argc, char** argv) {
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--") break;
    if (arg.size() < 2 || arg[0] != '-') continue;
    if (arg == "--server" || arg == "--help" || arg == "--version") return true;
    if (arg.rfind("--", 0) == 0) {
      if (arg.find('=') == std::string::npos && long_option_takes_value(arg.substr(2))) ++i;
    } else {
      for (size_t k = 1; k < arg.size(); ++k) {
        if (arg[k] == 'V') return true;
        if (std::strchr(short_values, arg[k])) {
          if (k + 1 == arg.size()) ++i;
          break;
        }
      }
    }
  }
  return false;
}

void append_defaults(std::vector<std::string>& result, const std::vector<std::string>& options,
                     const std::string& source) {
  for (size_t i = 0; i < options.size(); ++i) {
    const std::string& arg = options[i];
    if (arg.size() < 2 || arg[0] != '-' || arg == "--")
      die(RERR_SYNTAX, "%s must contain options, not transfer paths or --", source.c_str());
    result.push_back(arg);
    bool needs_value = false;
    if (arg.rfind("--", 0) == 0) {
      size_t equals = arg.find('=');
      std::string name = arg.substr(2, equals == std::string::npos ? equals : equals - 2);
      if (name == "server" || name == "sender" || name == "daemon" || name == "install" || name == "help" || name == "version")
        die(RERR_SYNTAX, "--%s cannot be used in %s", name.c_str(), source.c_str());
      needs_value = equals == std::string::npos && long_option_takes_value(name);
    } else {
      for (size_t k = 1; k < arg.size(); ++k) {
        if (arg[k] == 'V') die(RERR_SYNTAX, "-V cannot be used in %s", source.c_str());
        if (std::strchr(short_values, arg[k])) {
          needs_value = k + 1 == arg.size();
          break;
        }
      }
    }
    if (needs_value) {
      if (++i == options.size()) die(RERR_SYNTAX, "%s in %s requires a value", arg.c_str(), source.c_str());
      result.push_back(options[i]);
    }
  }
}
}  // namespace

std::vector<std::string> effective_arguments(int argc, char** argv) {
  if (bypass_defaults(argc, argv)) return {argv, argv + argc};
  std::vector<std::string> result{argv[0]};
  std::string config;
  const char* explicit_config = getenv("XSYNC_CONFIG");
  if (explicit_config) config = explicit_config;
  else if (const char* xdg = getenv("XDG_CONFIG_HOME"); xdg && *xdg) config = std::string(xdg) + "/xsync/config";
  else if (const char* home = getenv("HOME")) config = std::string(home) + "/.config/xsync/config";
  if (!config.empty()) {
    std::ifstream file(config);
    if (!file) {
      if (explicit_config || errno != ENOENT) die(RERR_SYNTAX, "cannot read defaults file %s: %s", config.c_str(), strerror(errno));
    } else {
      std::vector<std::string> options;
      std::string line;
      while (std::getline(file, line)) {
        size_t first = line.find_first_not_of(" \t\r");
        if (first == std::string::npos || line[first] == '#') continue;
        auto words = split_shell_words(line, config);
        options.insert(options.end(), words.begin(), words.end());
      }
      if (file.bad()) die(RERR_SYNTAX, "cannot read defaults file %s", config.c_str());
      append_defaults(result, options, config);
    }
  }
  if (const char* options = getenv("XSYNC_OPTS")) append_defaults(result, split_shell_words(options, "XSYNC_OPTS"), "XSYNC_OPTS");
  const char* rsh = getenv("XSYNC_RSH");
  if (!rsh) rsh = getenv("RSYNC_RSH");
  if (rsh) result.insert(result.end(), {"--rsh", rsh});
  if (const char* fallback = getenv("XSYNC_FALLBACK")) result.push_back(strcmp(fallback, "0") == 0 ? "--no-fallback" : "--fallback");
  if (const char* progress = getenv("XSYNC_PROGRESS")) {
    if (strcmp(progress, "0") == 0) result.push_back("--no-progress");
    else if (strcmp(progress, "1") == 0) result.push_back("--progress");
    else if (strcmp(progress, "auto") != 0)
      die(RERR_SYNTAX, "XSYNC_PROGRESS must be 0, 1, or auto");
  }
  result.insert(result.end(), argv + 1, argv + argc);
  return result;
}
