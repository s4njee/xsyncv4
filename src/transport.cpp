#include "transport.h"
#include "common.h"
#include <strings.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

RemoteSpec parse_remote_spec(const std::string& argument) {
  RemoteSpec spec;
  if (strncasecmp(argument.c_str(), "rsync://", 8) == 0) {
    spec.remote = spec.daemon = true;
    return spec;
  }
  size_t host_begin = 0, host_end = std::string::npos;
  for (size_t i = 0; i < argument.size(); ++i) {
    char ch = argument[i];
    if (ch == '/') return {};
    if (ch == ':') {
      spec.remote = true;
      spec.host = argument.substr(host_begin, (host_end == std::string::npos ? i : host_end) - host_begin);
      // User selection applies after brackets are removed, including odd hosts.
      size_t at = spec.host.rfind('@');
      if (at != std::string::npos) {
        spec.user = (spec.has_user ? spec.user + "@" : "") + spec.host.substr(0, at);
        spec.has_user = true;
        spec.host.erase(0, at + 1);
      }
      spec.daemon = i + 1 < argument.size() && argument[i + 1] == ':';
      spec.path = argument.substr(i + 1 + spec.daemon);
      if (spec.path.empty() && !spec.daemon) spec.path = ".";
      return spec;
    }
    if (ch == '@') {
      spec.has_user = true;
      spec.user = argument.substr(0, i);
      host_begin = i + 1;
    } else if (ch == '[') {
      if (i != host_begin) return {};
      size_t close = argument.find(']', i + 1);
      size_t slash = argument.find('/', i + 1);
      if (close == std::string::npos || close == i + 1 || slash < close) return {};
      if (close + 1 < argument.size() && argument[close + 1] != ':' && argument[close + 1] != '/') return {};
      host_begin = i + 1;
      host_end = close;
      i = close;
    }
  }
  return {};
}

std::vector<std::string> split_shell_words(const std::string& command) {
  std::vector<std::string> words;
  std::string word;
  char quote = 0;
  bool present = false;
  for (size_t i = 0; i < command.size(); ++i) {
    char ch = command[i];
    if (ch == '\\' && quote != '\'') {
      if (++i == command.size()) die(RERR_SYNTAX, "remote shell command ends with an escape");
      char next = command[i];
      if (quote == '"' && next != '"' && next != '\\' && next != '$' && next != '`' && next != '\n') word += '\\';
      if (next != '\n') word += next;
      present = true;
    } else if (quote) {
      if (ch == quote) quote = 0;
      else word += ch;
    } else if (ch == '\'' || ch == '"') quote = ch, present = true;
    else if (ch == ' ' || ch == '\t' || ch == '\n') {
      if (present) words.push_back(word), word.clear(), present = false;
    } else word += ch, present = true;
  }
  if (quote) die(RERR_SYNTAX, "unterminated quote in remote shell command");
  if (present) words.push_back(word);
  return words;
}

std::string remote_shell_command() {
  if (!g_opt.rsh.empty()) return g_opt.rsh;
  if (const char* env = getenv("RSYNC_RSH")) return env;
  return "ssh";
}

std::string shell_quote(const std::string& value) {
  std::string quoted = "'";
  for (char ch : value) {
    if (ch == '\'') quoted += "'\\''";
    else quoted += ch;
  }
  return quoted + "'";
}

std::string executable_path() {
#ifdef __APPLE__
  uint32_t size = 0;
  _NSGetExecutablePath(nullptr, &size);
  std::vector<char> path(size);
  if (_NSGetExecutablePath(path.data(), &size) == 0) return path.data();
#else
  std::vector<char> path(65536);
  ssize_t size = readlink("/proc/self/exe", path.data(), path.size());
  if (size > 0 && (size_t)size < path.size()) return std::string(path.data(), size);
#endif
  return {};
}
