// Bounded JSON codec used only by the public subprocess interface.
#pragma once
#include <map>
#include <string>
#include <string_view>
#include <vector>

namespace app_json {
struct Value {
  enum Kind { Null, Bool, Number, String, Array, Object } kind = Null;
  std::string text;
  std::vector<Value> array;
  std::map<std::string, Value> object;
  const Value& at(std::string_view name) const;
  std::string string() const;
  bool boolean() const;
};
Value parse(std::string_view input);
std::string quote(std::string_view utf8);
std::string serialize(const Value& value);
std::string hex(std::string_view bytes);
std::string unhex(std::string_view hex);
std::string path(std::string_view bytes);
}
