#pragma once
#include "app_json.h"
#include "fs.h"
#include <functional>
#include <thread>

namespace app_conflict {
void configure(bool enabled, unsigned timeout, std::function<void(std::string)> emit);
void response(std::string_view payload);
bool plan(DirWork& work, u32 index, Entry& destination, bool& exists,
          std::string_view reason = {});
bool recheck(const ItemPtr& item, const DestinationRevision& observed);
// A local job uses the same supervisor control pipe as the SSH adapter.
class ControlReader {
  std::atomic<bool> done{false};
  std::thread thread;
 public:
  explicit ControlReader(int fd);
  ~ControlReader();
};
}
