// Source metadata listing. This path never creates a destination or reads file data.
#pragma once
#include <functional>
#include "common.h"

struct ListingEntry { Entry attrs; std::string path, target, source; };
using ListingSink = std::function<void(const ListingEntry&)>;
int run_listing(const std::vector<std::string>& sources, const ListingSink& emit);
void prune_listing(std::vector<ListingEntry>& entries);
void listing_output(const ListingEntry& entry);
bool listing_path_valid(std::string_view path);
