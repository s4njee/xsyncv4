#pragma once
#include "app_partials.h"

// A helper parent and its forked worker share this locked open-file description.
// A fresh authenticated process can prove both released it without trusting PIDs
// or the disappearance of a path. The lock inode is never replaced while held.
namespace app_actor {
class Lease {
 public:
  Lease(const std::string& recovery, const std::string& attempt, const std::string& role);
  ~Lease();
  Lease(const Lease&) = delete;
  Lease& operator=(const Lease&) = delete;
  std::string path;
  DestinationRevision revision;
 private:
  int directory_ = -1, file_ = -1;
};
bool valid_path(std::string_view path);
int quiescence(const std::string& path, const std::string& recovery,
               const std::string& attempt, const std::string& role,
               const DestinationRevision& expected, bool cleanup,
               const app_partials::Emit& emit);
}
