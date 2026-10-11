#pragma once
#include "app_json.h"
#include "revision.h"
#include <functional>
#include <optional>

namespace app_actions {
struct Item {
  std::string name, destination;
  DestinationRevision expected, destination_expected;
};
struct Request {
  std::string operation, root;
  DestinationRevision parent;
  std::vector<Item> items;
  bool recursive = false, replace = false;
  std::optional<mode_t> mode;
  std::optional<timespec> mtime;
};
bool operation(std::string_view op);
DestinationRevision parse_revision(const app_json::Value& value);
Request parse(const app_json::Value& request, const std::string& root);
int run(const Request& request, int root_fd, const std::function<bool()>& root_valid,
        const std::function<void(std::string)>& emit);
}
