#pragma once
#include "fs.h"
#include "output.h"

// Hold linked entries until all independently validated copies have finished.
// Only receiver-owned paths derived from validated entries are used for linking.
bool hardlink_participant(const DirWork& w, u32 index);
void hardlink_prepare(DirWork& w, u32 index, const Entry* before);
void hardlink_complete(DirWork& w, u32 index, const Entry& source, const struct stat* published = nullptr, bool restore_flags = false);
bool hardlink_defer(DirWork& w, u32 index, OutputEvent event);
std::vector<std::string> hardlink_finalize();
