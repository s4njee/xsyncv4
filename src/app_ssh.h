// Headless SSH transport for the public app contract. Remote paths remain data.
#pragma once
#include "app_json.h"
#include "app_preview.h"
#include <functional>
#include <string>
#include <memory>

namespace app_ssh {
struct Connection {
  std::string host, user, identity, known_hosts, config, jump, helper = "xs";
  unsigned port = 0, connect_seconds = 30, auth_seconds = 60, prompt_seconds = 120, idle_seconds = 30;
  bool ask_host_key = false;
  bool operator==(const Connection&) const = default;
};
Connection parse_connection(const app_json::Value& endpoint);
// Owned by the supervisor, so forced job exits still remove the private broker.
struct AuthContext {
  std::string directory, helper, socket;
  int listener = -1;
  AuthContext() = default;
  AuthContext(const AuthContext&) = delete;
  AuthContext& operator=(const AuthContext&) = delete;
  ~AuthContext();
  void start();
  void close_listener();
  void cleanup();
};
void cleanup_directory(const std::string& directory);
using Emit = std::function<void(std::string)>;
// A move keeps the authenticated helper and its inode locks alive after native
// transfer completion. Cleanup RPCs use that same helper, never a second writer.
class RemoteLease {
 public:
  struct Impl;
  std::unique_ptr<Impl> impl;
  RemoteLease();
  ~RemoteLease();
  bool active() const;
  int run(app_json::Value request, const Emit& emit);
  int finish(const Emit& emit);
};
struct Copy {
  bool push;
  bool selection_mappings;
  bool interactive_conflicts;
  std::vector<std::string> sources;
  std::string destination;
  std::function<void()> on_started;
  RemoteLease* lease = nullptr;
  bool recoverable = false;
  std::function<int()> receiver_preflight = {};
  std::string attempt_id;
  std::function<void(app_json::Value)> actor_ready = {};
  // Called before queuing any operation bytes, even if the subsequent write fails.
  std::function<void()> on_submitted = {};
  std::shared_ptr<const app_preview::Inventory> preview_inventory;
};
int run(const Connection& connection, const std::string& operation,
        const std::string& request, const AuthContext& auth, int control_fd,
        const Emit& emit, const Copy* copy = nullptr);
int askpass(int argc, char** argv);
}
