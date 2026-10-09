#pragma once
#include <string>
#include <vector>

std::vector<std::string> split_shell_words(const std::string& command);
std::string remote_shell_command();
std::string shell_quote(const std::string& value);
std::string executable_path();
