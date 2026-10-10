#pragma once
#include "common.h"

#ifdef __linux__
// Reads from the supplied open directory. The caller retains its descriptor.
int list_dir_linux(int fd, DirList& out);
#endif
