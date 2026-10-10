#pragma once
#include "fs.h"
#include "destination.h"
#include "delta.h"
#include <optional>

void init_link_dest(const std::string& destination);
DestPath link_dest_path(const DirWork& work, u32 index);
bool link_dest_regular(DirWork& work, u32 index, Worker& worker, const Entry* before);
bool link_dest_nonregular(DirWork& work, u32 index, Worker& worker, std::optional<Entry>& before);
std::optional<Entry> link_dest_directory(const std::string& relative, Entry& source, const XattrSet& attrs, const FilterList& filters);
std::shared_ptr<DeltaBasis> link_dest_delta_basis(const DirWork& work, u32 index);
