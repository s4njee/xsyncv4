#pragma once
#include "common.h"
#include <memory>

struct XattrBlob;
struct XattrInline;

// Values share an 8 MiB inline budget; overflow and large values use extents
// in one unlinked temporary file. Metadata copies share the underlying bytes.
class XattrValue {
 public:
  static constexpr size_t INLINE_MAX = 65536;
  XattrValue() = default;
  explicit XattrValue(std::string bytes);
  static bool from_fd(int fd, u64 size, XattrValue& out);
  static bool allocate(u64 size, XattrValue& out);
  bool write(const char* bytes, size_t size, u64 offset);
  u64 size() const;
  bool read(char* bytes, size_t size, u64 offset) const;
  bool append_to(std::string& output) const;
  bool operator==(const XattrValue& other) const;
  bool stored() const { return (bool)blob_; }
  const std::string& inline_bytes() const;
 private:
  std::shared_ptr<XattrInline> bytes_;
  std::shared_ptr<XattrBlob> blob_;
};
