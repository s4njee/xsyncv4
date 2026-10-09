#pragma once
#include <string>

// Capture before parsing: an unsupported option can occur before --no-fallback.
void init_fallback(int argc, char** argv);
bool fallback_enabled();
[[noreturn]] void fallback_to_rsync(const std::string& reason, int strict_code = 1);
