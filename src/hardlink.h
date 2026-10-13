#pragma once
#include "fs.h"
#include "output.h"

// Hold linked entries until all independently validated copies have finished.
// Only receiver-owned paths derived from validated entries are used for linking.
bool hardlink_participant(const DirWork& w, u32 index);
void hardlink_prepare(DirWork& w, u32 index, const Entry* before, bool alternate = false);
void hardlink_complete(DirWork& w, u32 index, const Entry& source, const struct stat* published = nullptr, bool restore_flags = false);
// Regular files only. The first name of a source inode that will have data at
// the destination holds it. Returns true when another name already does and
// this one may follow it: the caller then skips the transfer, and finalization
// links the name to the holder.
bool hardlink_follow(DirWork& w, u32 index, bool may_follow);
bool hardlink_defer(DirWork& w, u32 index, OutputEvent event);
std::vector<std::string> hardlink_finalize();
