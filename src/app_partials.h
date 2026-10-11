#pragma once
#include "app_json.h"
#include "revision.h"
#include <functional>
#include <memory>
#include <stdexcept>

struct OutFile;
struct ResumePrefix;
struct TransferItem;
namespace app_partials {
using Emit = std::function<void(std::string)>;
struct Error : std::runtime_error {
  std::string path, operation;
  int native;
  Error(std::string path, std::string operation, int native, std::string message);
};
std::string new_id();
bool valid_id(std::string_view id);
// Binding omits credentials and resource knobs. It names the selected endpoint
// paths and copy semantics, while per-file records bind actual destinations.
class Session {
 public:
  struct Impl;
  std::unique_ptr<Impl> impl;
  Session(const std::string& root, const std::string& id,
          const app_json::Value& binding, bool resume, const Emit& emit,
          const app_json::Value& actor = {});
  ~Session();
  void finish(int code);
};
bool active();
struct Choice { std::string decision, destination, recovery_id; };
int restore_choice(const std::shared_ptr<TransferItem>& item, Choice& choice);
bool remember_choice(const std::shared_ptr<TransferItem>& item, const std::string& decision,
                     const std::string& scope, const std::string& kind, const std::string& directory);
bool conflict_policy(const std::shared_ptr<TransferItem>& item, const std::string& kind,
                     const std::string& directory, std::string& action);
bool prepare_entry(const std::shared_ptr<TransferItem>& item);
bool own_entry(const std::shared_ptr<TransferItem>& item);
bool validate_entry(const std::shared_ptr<TransferItem>& item);
bool removed_entry(const std::shared_ptr<TransferItem>& item);
void finish_entry(const std::shared_ptr<TransferItem>& item);
bool open_stage(OutFile& file);
ResumePrefix prefix(const char* path, i64 limit);
int open_prefix(const std::string& path, bool published, const DestinationRevision& expected);
void retained(int stage, const std::string& name, const DestinationRevision& identity);
void discarded(int stage, const std::string& name, const DestinationRevision& identity);
bool preparing_publication(const OutFile& file);
void published(const OutFile& file);
void stopped();
bool hidden(int parent, std::string_view name);
int inspect(const std::string& root, const std::string& id, const Emit& emit);
int verify(const std::string& root, const std::string& id,
           const app_json::Value& binding, const DestinationRevision& expected_job,
           const std::string& expected_inventory,
           const Emit& emit);
int checkpoint(const std::string& root, const std::string& id,
               const app_json::Value& binding, const Emit& emit, const std::string& closed_attempt = {});
int cleanup(const std::string& root, const std::string& id,
            const DestinationRevision& expected_job, const Emit& emit);
}
