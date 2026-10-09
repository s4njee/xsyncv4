#pragma once
#include <string>
#include <vector>

struct RemoteSpec {
  bool remote = false, daemon = false, has_user = false;
  std::string user, host, path;
};
RemoteSpec parse_remote_spec(const std::string& argument);
std::vector<std::string> split_shell_words(const std::string& command);
std::string remote_shell_command();
std::string shell_quote(const std::string& value);
std::string executable_path();
