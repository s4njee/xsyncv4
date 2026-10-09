#include "transport.h"
#include "common.h"
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

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
