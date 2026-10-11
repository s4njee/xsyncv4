#pragma once
#include "app_preview.h"

namespace app_preview {
app_json::Value revision_value(const DestinationRevision&);
// Expectations travel on the authenticated, negotiated private channel before
// native data handoff. One bounded chunk is outstanding at a time.
class ManifestSender {
  const Inventory& inventory;
  bool receiver;
  std::map<std::string,DestinationRevision>::const_iterator position;
  u64 sequence = 0;
 public:
  ManifestSender(const Inventory&,bool);
  app_json::Value header() const;
  std::string next(u64 requested_sequence);
  bool complete() const;
};
class ManifestReceiver {
  Inventory inventory;
  bool receiver;
  u64 entries, received = 0, sequence = 0, bytes = 0;
 public:
  ManifestReceiver(bool,const app_json::Value&,std::string root);
  u64 next_sequence() const { return sequence+1; }
  void append(const app_json::Value&,size_t frame_bytes);
  bool complete() const { return received==entries; }
  Inventory release();
};
}
