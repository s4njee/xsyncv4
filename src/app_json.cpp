#include "app_json.h"
#include <stdexcept>

namespace app_json {
namespace {
[[noreturn]] void invalid() { throw std::runtime_error("invalid JSON or field type"); }
int digit(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}
void utf8(std::string& out, unsigned c) {
  if (c < 0x80) out += char(c);
  else if (c < 0x800) { out += char(0xc0 | (c >> 6)); out += char(0x80 | (c & 63)); }
  else if (c < 0x10000) { out += char(0xe0 | (c >> 12)); out += char(0x80 | ((c >> 6) & 63)); out += char(0x80 | (c & 63)); }
  else { out += char(0xf0 | (c >> 18)); out += char(0x80 | ((c >> 12) & 63)); out += char(0x80 | ((c >> 6) & 63)); out += char(0x80 | (c & 63)); }
}
// Return the length of a canonical UTF-8 sequence, or zero for invalid bytes.
size_t sequence(std::string_view s, size_t p) {
  unsigned a = (unsigned char)s[p];
  if (a < 128) return 1;
  size_t n = a >= 0xc2 && a <= 0xdf ? 2 : a >= 0xe0 && a <= 0xef ? 3 : a >= 0xf0 && a <= 0xf4 ? 4 : 0;
  if (!n || p + n > s.size()) return 0;
  for (size_t i = 1; i < n; ++i) if (((unsigned char)s[p+i] & 0xc0) != 0x80) return 0;
  unsigned b = (unsigned char)s[p+1];
  if ((a == 0xe0 && b < 0xa0) || (a == 0xed && b >= 0xa0) || (a == 0xf0 && b < 0x90) || (a == 0xf4 && b >= 0x90)) return 0;
  return n;
}
struct Parser {
  std::string_view s;
  size_t p = 0;
  void space() { while (p < s.size() && (s[p] == ' ' || s[p] == '\n' || s[p] == '\r' || s[p] == '\t')) ++p; }
  bool take(char c) { space(); if (p < s.size() && s[p] == c) { ++p; return true; } return false; }
  void need(char c) { if (!take(c)) invalid(); }
  unsigned code() {
    unsigned v = 0;
    for (int i = 0; i < 4; ++i) { if (p == s.size() || digit(s[p]) < 0) invalid(); v = v * 16 + digit(s[p++]); }
    return v;
  }
  std::string str() {
    need('"'); std::string out;
    while (p < s.size()) {
      unsigned c = (unsigned char)s[p++];
      if (c == '"') return out;
      if (c < 32) invalid();
      if (c == '\\') {
        if (p == s.size()) invalid();
        char e = s[p++];
        if (e == '"' || e == '\\' || e == '/') out += e;
        else if (e == 'b') out += '\b'; else if (e == 'f') out += '\f';
        else if (e == 'n') out += '\n'; else if (e == 'r') out += '\r'; else if (e == 't') out += '\t';
        else if (e == 'u') {
          unsigned u = code();
          if (u >= 0xd800 && u <= 0xdbff) {
            if (p + 2 > s.size() || s.substr(p, 2) != "\\u") invalid();
            p += 2; unsigned lo = code(); if (lo < 0xdc00 || lo > 0xdfff) invalid();
            u = 0x10000 + ((u - 0xd800) << 10) + lo - 0xdc00;
          } else if (u >= 0xdc00 && u <= 0xdfff) invalid();
          utf8(out, u);
        } else invalid();
      } else {
        size_t n = sequence(s, p-1); if (!n) invalid();
        out.append(s.substr(p-1, n)); p += n-1;
      }
    }
    invalid();
  }
  Value value(unsigned depth) {
    if (depth > 32) invalid();
    space(); if (p == s.size()) invalid(); Value v;
    if (s[p] == '"') { v.kind = Value::String; v.text = str(); }
    else if (take('{')) {
      v.kind = Value::Object;
      if (!take('}')) do {
        std::string k = str(); need(':');
        if (!v.object.emplace(std::move(k), value(depth+1)).second) invalid();
        if (take('}')) return v;
        need(',');
      } while (true);
    } else if (take('[')) {
      v.kind = Value::Array;
      if (!take(']')) do { v.array.push_back(value(depth+1)); if (take(']')) return v; need(','); } while (true);
    } else if (s.substr(p, 4) == "null") { p += 4; }
    else if (s.substr(p, 4) == "true") { p += 4; v.kind = Value::Bool; v.text = "true"; }
    else if (s.substr(p, 5) == "false") { p += 5; v.kind = Value::Bool; v.text = "false"; }
    else {
      size_t start = p; if (s[p] == '-') ++p;
      if (p == s.size()) invalid();
      if (s[p] == '0') ++p;
      else { if (s[p] < '1' || s[p] > '9') invalid(); while (p < s.size() && s[p] >= '0' && s[p] <= '9') ++p; }
      if (p < s.size() && s[p] == '.') { ++p; size_t begin = p; while (p < s.size() && s[p] >= '0' && s[p] <= '9') ++p; if (begin == p) invalid(); }
      if (p < s.size() && (s[p] == 'e' || s[p] == 'E')) { ++p; if (p < s.size() && (s[p] == '+' || s[p] == '-')) ++p; size_t begin = p; while (p < s.size() && s[p] >= '0' && s[p] <= '9') ++p; if (begin == p) invalid(); }
      v.kind = Value::Number; v.text = s.substr(start, p-start);
    }
    return v;
  }
};
}
const Value& Value::at(std::string_view key) const {
  if (kind != Object) invalid();
  auto i = object.find(std::string(key)); if (i == object.end()) throw std::runtime_error("missing field: " + std::string(key)); return i->second;
}
std::string Value::string() const { if (kind != String) invalid(); return text; }
bool Value::boolean() const { if (kind != Bool) invalid(); return text == "true"; }
Value parse(std::string_view input) {
  if (input.size() > 1024*1024) invalid();
  Parser p{input}; auto v = p.value(0); p.space(); if (p.p != input.size()) invalid(); return v;
}
std::string quote(std::string_view s) {
  std::string out = "\"";
  constexpr char h[] = "0123456789abcdef";
  for (size_t i = 0; i < s.size();) {
    unsigned c = (unsigned char)s[i];
    if (c == '"' || c == '\\') { out += '\\'; out += char(c); ++i; }
    else if (c < 32) { out += "\\u00"; out += h[c >> 4]; out += h[c & 15]; ++i; }
    else { size_t n = sequence(s, i); if (n) { out.append(s.substr(i, n)); i += n; } else { out += "\xef\xbf\xbd"; ++i; } }
  }
  return out + '"';
}
std::string serialize(const Value& v) {
  if (v.kind == Value::Null) return "null";
  if (v.kind == Value::String) return quote(v.text);
  if (v.kind == Value::Bool || v.kind == Value::Number) return v.text;
  std::string out = v.kind == Value::Array ? "[" : "{";
  bool first = true;
  if (v.kind == Value::Array) {
    for (const auto& item : v.array) { if (!first) out += ','; first = false; out += serialize(item); }
  } else {
    for (const auto& [key, item] : v.object) { if (!first) out += ','; first = false; out += quote(key) + ':' + serialize(item); }
  }
  return out + (v.kind == Value::Array ? ']' : '}');
}
std::string hex(std::string_view s) {
  constexpr char h[] = "0123456789abcdef"; std::string r; r.reserve(s.size()*2);
  for (unsigned char c : s) { r += h[c >> 4]; r += h[c & 15]; } return r;
}
std::string unhex(std::string_view s) {
  if (s.size() % 2 || s.size() > 8192) throw std::runtime_error("path hex exceeds 4096 bytes or has odd length");
  std::string r; r.reserve(s.size()/2);
  for (size_t i = 0; i < s.size(); i += 2) { int a = digit(s[i]), b = digit(s[i+1]); if (a < 0 || b < 0) throw std::runtime_error("invalid path hex"); r += char(a*16+b); }
  return r;
}
std::string path(std::string_view bytes) { return "{\"bytes_hex\":" + quote(hex(bytes)) + ",\"display\":" + quote(bytes) + "}"; }
}
