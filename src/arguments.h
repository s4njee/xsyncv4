#pragma once
#include <string>
#include <vector>

bool long_option_takes_value(const std::string& name);
std::vector<std::string> effective_arguments(int argc, char** argv);
