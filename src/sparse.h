#pragma once
#include <cstddef>
#include <cstdint>
#include <atomic>

bool sparse_write(int fd, const char* bytes, size_t size, int64_t offset, bool reused);
bool sparse_compact(int fd, const std::atomic<int>* stop = nullptr);
