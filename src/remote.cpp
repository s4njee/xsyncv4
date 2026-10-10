// Remote sync over a pipe pair (ssh or any -e command): xsync's own pipelined protocol.
//
// The sender walks the source tree and streams one DIR frame per directory. The receiver
// compares each against its destination and answers with a NEED frame naming the files whose
// data it wants. File data travels in DATA frames: blocks of many small files (or one chunk of
// a large one), optionally zstd-compressed, built and consumed by worker threads on both
// sides so that listing, reading, compression, decompression and writing all overlap.
#include <fcntl.h>
#include <grp.h>
#include <glob.h>
#include <pwd.h>
#include <poll.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include <cerrno>
#include <algorithm>
#include <array>
#include <cstdlib>
#include <climits>
#include <memory>
#include <system_error>
#include <map>
#include <unordered_map>
#include <unordered_set>

#include <zstd.h>

#define XXH_INLINE_ALL
#include <xxhash.h>

#include "engine.h"
#include "link_dest.h"
#include "progress.h"
#include "fallback.h"
#include "transport.h"
#include "output.h"
#include "delta.h"
#include "listing.h"
#include "rate_limit.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

namespace {

enum : u8 { F_HELLO = 1, F_DIR, F_NEED, F_DATA, F_LIST_END, F_DATA_END, F_DONE, F_MSG, F_IDMAP, F_DEST, F_OUTPUT, F_OUTPUT_CONFIG,
            F_DELTA_REQUEST, F_DELTA_SIGNATURE, F_DELTA_RETRY_ACK, F_LIST_ENTRY, F_IO_CONFIG, F_KEEPALIVE, F_FILTER_CONFIG, F_DELETE_CONFIG,
            F_PRUNE_CONFIG, F_RELATIVE_CONFIG, F_FILES_CONFIG, F_FILES_DATA, F_FILES_END, F_XATTR_CONFIG, F_XATTR_START, F_XATTR_CHUNK, F_XATTR_END, F_ACL_CONFIG, F_CHOWN_CONFIG, F_SPARSE_CONFIG, F_LINKDEST_CONFIG, F_PROGRESS, F_STAGE };
enum : u8 { DF_ATTRS = 1, DF_SINGLE = 2, DF_NODELETE = 4, DF_ZSTD = 8 };
enum : u8 { R_WHOLE = 1, R_CHUNK = 2, R_FAIL = 4, R_END = 8, R_LITERAL = 16, R_DELTA_END = 32, R_COPY = 64 };
constexpr size_t HDR = 5;                  // u32 payload length + u8 type
constexpr size_t BLOCK_TARGET = 1 << 20;   // raw bytes per DATA frame
constexpr size_t SMALL_MAX = 512 << 10;    // files up to this size are packed into shared blocks
constexpr size_t DATA_PREFIX = HDR + 1 + 8;
const char MAGIC[] = "XSYNC\x01";

bool resume_enabled() { return g_opt.partial && (g_opt.peer_features & PF_RESUME); }
bool structured_output() { return g_opt.peer_features & PF_OUTPUT; }
bool delta_enabled() { return g_opt.peer_features & PF_DELTA; }

// ---------------------------------------------------------------- encoding

void put_var(std::string& s, u64 v) {
  while (v >= 0x80) s.push_back((char)(v | 0x80)), v >>= 7;
  s.push_back((char)v);
}
void put_svar(std::string& s, i64 v) { put_var(s, ((u64)v << 1) ^ (u64)(v >> 63)); }
void put_str(std::string& s, std::string_view v) {
  put_var(s, v.size());
  s.append(v);
}

u64 send_xattr_value(const XattrValue& value);
XattrValue take_xattr_value(u64 id);
void receive_xattr_value(u8 type, std::string_view payload);
void check_xattr_values_drained();

void put_acls(std::string& buffer, const XattrSet& attrs) {
  auto records = export_acls(attrs.acl());
  buffer.push_back((char)records.complete);
  put_var(buffer, records.flags);
  for (const auto* list : {&records.access, &records.defaults}) {
    put_var(buffer, list->size());
    for (const auto& record : *list) {
      put_var(buffer, record.tag), put_var(buffer, record.permissions), put_var(buffer, record.flags), put_var(buffer, record.id);
      put_str(buffer, record.name);
    }
  }
}

void put_xattrs(std::string& s, const XattrSet& attrs) {
  s.push_back((char)attrs.complete);
  // An ACL read can mark combined metadata incomplete after successful xattr
  // reads. Do not send a partially populated list as an empty successful set.
  if (!attrs.complete) { put_var(s, 0); return; }
  put_var(s, attrs.values.size());
  for (const auto& [name, value] : attrs.values) {
    put_str(s, name);
    if (g_opt.peer_features & PF_XATTR_STREAM) {
      bool large = value.stored();
      s.push_back((char)large);
      if (large) { put_var(s, send_xattr_value(value)); continue; }
    }
    put_var(s, value.size());
    if (!value.append_to(s)) die(RERR_FILEIO, "read stored extended attributes: %s", errstr(errno).c_str());
  }
}

void put_file_attrs(std::string& s, const Entry& e, const XattrSet& xattrs) {
  put_var(s, e.mode), put_var(s, e.uid), put_var(s, e.gid);
  put_svar(s, e.mtime), put_var(s, e.mtime_ns);
  if (g_opt.peer_features & PF_ATIMES) put_svar(s, e.atime);
  if (g_opt.peer_features & PF_CRTIMES) put_svar(s, e.crtime);
  if (g_opt.peer_features & PF_FILEFLAGS) put_var(s, e.fileflags);
  if (g_opt.peer_features & PF_HLINK) {
    put_var(s, e.hdev), put_var(s, e.ino), put_var(s, e.nlink);
    put_svar(s, e.ctime), put_var(s, e.ctime_ns);
  }
  if (g_opt.peer_features & PF_XATTRS) put_xattrs(s, xattrs);
  if (g_opt.peer_features & PF_NATIVE_ACL) put_acls(s, xattrs);
}

struct RBuf {
  const u8* p;
  const u8* e;
  bool bad = false;
  RBuf(std::string_view v) : p((const u8*)v.data()), e((const u8*)v.data() + v.size()) {}
  u8 byte() {
    if (p >= e) return bad = true, 0;
    return *p++;
  }
  u64 var() {
    u64 v = 0;
    for (int sh = 0; sh < 64; sh += 7) {
      if (p >= e) return bad = true, 0;
      u8 b = *p++;
      if (sh == 63 && (b & 0xfe)) return bad = true, 0;
      v |= (u64)(b & 0x7f) << sh;
      if (!(b & 0x80)) return v;
    }
    return bad = true, 0;
  }
  i64 svar() {
    u64 v = var();
    return (i64)(v >> 1) ^ -(i64)(v & 1);
  }
  std::string_view raw(size_t n) {
    if ((size_t)(e - p) < n) return bad = true, std::string_view();
    std::string_view r((const char*)p, n);
    p += n;
    return r;
  }
  std::string_view str() { return raw((size_t)var()); }
  std::string_view rest() { return raw((size_t)(e - p)); }
  bool empty() const { return p >= e; }
};

XattrSet get_xattrs(RBuf& r) {
  XattrSet attrs;
  u8 complete = r.byte();
  u64 count = r.var();
  // Each pair needs at least its two length fields. Bound allocation before
  // constructing maps, and reject ambiguous names before any destination work.
  if (r.bad || complete > 1 || count > 65536 || count > (u64)(r.e - r.p) / 2 || (!complete && count))
    die(RERR_PROTOCOL, "protocol error: malformed xattr list");
  attrs.complete = complete;
  for (u64 i = 0; i < count; ++i) {
    auto name = r.str();
    if (r.bad || name.empty() || name.size() > 1024 || name.find('\0') != name.npos || attrs.values.count(name))
      die(RERR_PROTOCOL, "protocol error: invalid or duplicate xattr name/value");
    u8 kind = g_opt.peer_features & PF_XATTR_STREAM ? r.byte() : 0;
    if (r.bad || kind > 1) die(RERR_PROTOCOL, "protocol error: bad xattr value kind");
    if (kind) {
      u64 id = r.var();
      if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated xattr value reference");
      attrs.values.emplace(std::string(name), take_xattr_value(id));
    } else {
      auto value = r.str();
      if (r.bad || ((g_opt.peer_features & PF_XATTR_STREAM) && value.size() > XattrValue::INLINE_MAX))
        die(RERR_PROTOCOL, "protocol error: truncated or oversized inline xattr value");
      try { attrs.values.emplace(std::string(name), XattrValue(std::string(value))); }
      catch (const std::system_error& error) { die(RERR_FILEIO, "store received extended attributes: %s", error.what()); }
    }
  }
  return attrs;
}

void get_acls(RBuf& r, XattrSet& attrs, u8 type) {
  AclRecords records;
  u8 complete = r.byte();
  u64 flags = r.var();
  if (r.bad || complete > 1 || flags > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: malformed ACL header");
  records.complete = complete, records.flags = (u32)flags;
  for (auto* list : {&records.access, &records.defaults}) {
    u64 count = r.var();
    if (r.bad || count > ACL_MAX_RECORDS || count > (u64)(r.e - r.p) / 5)
      die(RERR_PROTOCOL, "protocol error: oversized or truncated ACL list");
    list->reserve((size_t)count);
    for (u64 index = 0; index < count; ++index) {
      u64 tag = r.var(), permissions = r.var(), entry_flags = r.var(), id = r.var();
      auto name = r.str();
      if (r.bad || tag > UINT32_MAX || permissions > UINT32_MAX || entry_flags > UINT32_MAX || id > UINT32_MAX || name.size() > 255)
        die(RERR_PROTOCOL, "protocol error: malformed ACL entry");
      list->push_back({(u32)tag, (u32)permissions, (u32)entry_flags, (u32)id, std::string(name)});
    }
  }
  if (!valid_acl_records(records, type)) die(RERR_PROTOCOL, "protocol error: invalid ACL entries");
  try {
    auto acl = import_acls(std::move(records));
    attrs.complete &= acl.complete;
    if (!acl.complete || acl.access.size() || acl.defaults.size()) attrs.acls = std::make_shared<AclSet>(std::move(acl));
  } catch (const std::system_error& error) { die(RERR_FILEIO, "construct received ACL: %s", error.what()); }
}

std::string new_frame(u8 type) {
  std::string f(HDR, '\0');
  f[4] = (char)type;
  return f;
}

// ---------------------------------------------------------------- connection

std::mutex peer_guard;
pid_t current_remote_peer = -1;
bool peer_cancelled = false;

struct Conn {
  int rfd = -1, wfd = -1;
  pid_t peer_pid = -1;
  RateLimiter limiter;
  std::atomic<u64> idle_ns{0}, last_activity{now_ns()}, last_send{now_ns()}, heartbeat_ns{10000000000ull};
  std::atomic<bool> keepalive{false};
  std::atomic<bool> timed_out{false};
  std::mutex timeout_mu;
  std::mutex mu;
  std::condition_variable cv, cv_space;
  std::deque<std::string> q;
  size_t qbytes = 0;
  bool closing = false;
  std::thread wt;
  std::thread::id wt_id;
  std::vector<char> rb = std::vector<char>(256 * 1024);
  size_t rpos = 0, rlen = 0;
  static constexpr size_t MAX_Q = 48 << 20;

  void configure(u64 rate, u32 seconds, bool heartbeat) {
    limiter.configure(rate);
    idle_ns = (u64)seconds * 1000000000ull;
    heartbeat_ns = seconds ? std::max<u64>(100000000ull, std::min<u64>(10000000000ull, idle_ns.load() / 3)) : 10000000000ull;
    keepalive = heartbeat;
  }
  void check_timeout(u64 write_progress = 0) {
    if (timed_out.load()) {
      std::lock_guard<std::mutex> lock(timeout_mu);
      return;  // The timeout owner exits while holding this mutex.
    }
    output_check();
    if (output_error()) return;  // Preserve the diagnostic failure as the exit reason.
    u64 deadline = idle_ns.load();
    u64 now = now_ns(), last = write_progress ? write_progress : last_activity.load();
    if (!deadline || now < last || now - last < deadline) return;
    // Read and write waits can expire together. Only one thread owns cleanup
    // and the final diagnostic; the others wait until that thread exits.
    std::lock_guard<std::mutex> timeout_lock(timeout_mu);
    timed_out = true;
    // A stalled writer cannot safely drain a fatal frame, especially mid-frame.
    // Both peers have the deadline; the client also recognizes shell exit 30.
    if (peer_pid > 0) kill(peer_pid, SIGTERM);
    g_msg_sink = nullptr;
    g_output_sink = nullptr;
    u64 seconds = deadline / 1000000000ull;
    die(RERR_TIMEOUT, "I/O timeout after %llu second%s", (unsigned long long)seconds, seconds == 1 ? "" : "s");
  }
  bool wait_fd(int fd, short events, u64 write_progress = 0) {
    for (;;) {
      if (g_stop.load()) return false;
      check_timeout(write_progress);
      pollfd p{fd, events, 0};
      int rc = poll(&p, 1, 100);
      if (rc > 0) return true;  // Let read/write report EOF, EPIPE, or other errors.
      if (rc < 0 && errno != EINTR) return false;
    }
  }
  int wait_peer() {
    int status = 0;
    for (;;) {
      {
        // Serialize reaping with cancellation so a reused PID is never killed.
        std::lock_guard<std::mutex> lock(peer_guard);
        pid_t result = waitpid(peer_pid, &status, WNOHANG);
        if (result == peer_pid || (result < 0 && errno != EINTR)) {
          if (current_remote_peer == peer_pid) current_remote_peer = -1;
          return status;
        }
      }
      output_check();
      if (g_stop.load()) { cancel_remote_peer(); exit_signal(); }
      check_timeout();
      usleep(25000);
    }
  }
  void start() {
    for (int fd : {rfd, wfd}) {
      int flags = fcntl(fd, F_GETFL);
      if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0)
        die(RERR_IPC, "cannot configure transport pipe: %s", errstr(errno).c_str());
    }
    wt = std::thread([this] { writer(); });
  }
  // Queue a frame built with new_frame(); `bounded` applies back-pressure to bulk producers.
  void send(std::string&& f, bool bounded = false, size_t queue_limit = MAX_Q) {
    if (f.size() < HDR || f.size() - HDR > (1u << 30)) die(RERR_PROTOCOL, "protocol error: oversized outgoing frame");
    u32 len = (u32)(f.size() - HDR);
    memcpy(f.data(), &len, 4);
    std::unique_lock<std::mutex> lk(mu);
    if (bounded) cv_space.wait(lk, [&] { return qbytes < queue_limit || closing; });
    if (closing) return;
    qbytes += f.size();
    q.push_back(std::move(f));
    cv.notify_one();
  }
  void finish() {
    {
      std::lock_guard<std::mutex> lk(mu);
      closing = true;
      cv.notify_all();
      cv_space.notify_all();
    }
    if (wt.joinable() && std::this_thread::get_id() != wt_id) wt.join();
  }
  void writer() {
    wt_id = std::this_thread::get_id();
    std::string small;
    std::deque<std::string> batch;
    auto out = [&](const char* p, size_t n, bool activity = true) {
      StageTimer timing(g_stats.network_ns);
      bool ok = true;
      u64 progress = now_ns();
      while (n) {
        size_t count = activity ? limiter.acquire(std::min<size_t>(n, 65536), [this, &progress] { check_timeout(progress); }) : n;
        if (!count) { ok = false; break; }
        // Reserve tokens once. EAGAIN and short writes use the remainder of the
        // same reservation, so pipe back-pressure does not charge bytes twice.
        while (count) {
          ssize_t wrote = write(wfd, p, count);
          if (wrote < 0 && errno == EINTR) continue;
          if (wrote < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            if (!wait_fd(wfd, POLLOUT, progress)) { ok = false; break; }
            continue;
          }
          if (wrote <= 0) { ok = false; break; }
          u64 now = now_ns();
          progress = now;
          last_send = now;
          if (activity) last_activity = now;
          p += wrote; n -= (size_t)wrote; count -= (size_t)wrote;
          g_stats.wire_sent.fetch_add((u64)wrote, std::memory_order_relaxed);
        }
        if (!ok) break;
      }
      if (!ok) {
        // The peer may have sent a fatal filesystem error before closing. Let
        // the reader consume it instead of racing it with an EPIPE exit here.
        std::lock_guard<std::mutex> lock(mu);
        closing = true;
        q.clear();
        qbytes = 0;
        cv_space.notify_all();
        return false;
      }
      return true;
    };
    for (;;) {
      {
        std::unique_lock<std::mutex> lk(mu);
        cv.wait_for(lk, std::chrono::milliseconds(100), [&] { return !q.empty() || closing; });
        if (q.empty()) {
          if (closing) break;
          lk.unlock();
          if (g_stop.load()) return;
          if (keepalive.load() && now_ns() - last_send.load() >= heartbeat_ns.load()) {
            std::string heartbeat = new_frame(F_KEEPALIVE);
            if (!out(heartbeat.data(), heartbeat.size(), false)) return;
          }
          continue;
        }
        batch.swap(q);
        qbytes = 0;
        cv_space.notify_all();
      }
      // Coalesce runs of small frames into one write.
      small.clear();
      for (std::string& f : batch) {
        if (f.size() < 32768) {
          small.append(f);
          if (small.size() >= (256 << 10)) {
            if (!out(small.data(), small.size())) return;
            small.clear();
          }
        } else {
          if (!small.empty()) {
            if (!out(small.data(), small.size())) return;
            small.clear();
          }
          if (!out(f.data(), f.size())) return;
        }
      }
      if (!small.empty() && !out(small.data(), small.size())) return;
      batch.clear();
    }
  }
  bool read_exact(char* dst, size_t n) {
    while (n) {
      if (g_stop.load()) return false;
      if (rpos < rlen) {
        size_t k = std::min(n, rlen - rpos);
        memcpy(dst, rb.data() + rpos, k);
        rpos += k, dst += k, n -= k;
        continue;
      }
      ssize_t k = n >= rb.size() ? read(rfd, dst, n) : read(rfd, rb.data(), rb.size());
      if (g_stop.load()) return false;
      if (k < 0 && errno == EINTR) continue;
      if (k < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        if (!wait_fd(rfd, POLLIN)) return false;
        continue;
      }
      if (k <= 0) return false;
      last_activity = now_ns();
      g_stats.wire_recv.fetch_add((u64)k, std::memory_order_relaxed);
      if (n >= rb.size()) dst += k, n -= (size_t)k;
      else rpos = 0, rlen = (size_t)k;
    }
    return true;
  }
  // Returns false on EOF at a frame boundary or on a broken stream.
  bool read_frame(u8& type, std::string& payload, bool hello = false) {
    for (;;) {
      char h[HDR]{};
      if (!read_exact(h, HDR)) {
        if (hello && std::any_of(h, h + HDR, [](char ch) { return ch != 0; }))
          die(RERR_PROTOCOL, "the remote shell is printing text on stdout (or --rsync-path is not xsync); remove shell startup output");
        return false;
      }
      u32 len;
      memcpy(&len, h, 4);
      type = (u8)h[4];
      if (hello && type != F_HELLO && type != F_MSG)
        die(RERR_PROTOCOL, "the remote shell is printing text on stdout (or --rsync-path is not xsync); remove shell startup output");
      if (len > (1u << 30)) die(RERR_PROTOCOL, "protocol error: oversized frame");
      if (type == F_PROGRESS && (len > (g_opt.peer_features & PF_STAGE_METRICS ? 30u : 20u) || !(g_opt.peer_features & PF_PROGRESS_ACK)))
        die(RERR_PROTOCOL, "protocol error: oversized or unnegotiated progress acknowledgment");
      if (type == F_STAGE && (len > 20 || !(g_opt.peer_features & PF_STAGE_METRICS)))
        die(RERR_PROTOCOL, "protocol error: oversized or unnegotiated stage metrics");
      if (type == F_IO_CONFIG && len > 20) die(RERR_PROTOCOL, "protocol error: malformed I/O configuration (oversized)");
      if (type == F_CHOWN_CONFIG && len > 1024 * 1024)
        die(RERR_PROTOCOL, "protocol error: oversized ownership configuration");
      if (type == F_CHOWN_CONFIG && !(g_opt.peer_features & PF_CHOWN))
        die(RERR_PROTOCOL, "protocol error: unnegotiated ownership configuration");
      if (type == F_SPARSE_CONFIG && (len > 1 || !(g_opt.peer_features & PF_SPARSE)))
        die(RERR_PROTOCOL, "protocol error: malformed or unnegotiated sparse configuration");
      if (type == F_LINKDEST_CONFIG && (len > 1024 * 1024 || !(g_opt.peer_features & PF_LINK_DEST)))
        die(RERR_PROTOCOL, "protocol error: oversized or unnegotiated link-dest configuration");
      if (type == F_FILTER_CONFIG && len > 1024 * 1024)
        die(RERR_PROTOCOL, "protocol error: oversized filter configuration");
      if (type == F_FILTER_CONFIG && !(g_opt.peer_features & PF_FILTERS))
        die(RERR_PROTOCOL, "protocol error: unnegotiated filter configuration");
      if (type == F_RELATIVE_CONFIG && (len != 1 || !(g_opt.peer_features & PF_RELATIVE)))
        die(RERR_PROTOCOL, "protocol error: malformed or unnegotiated relative configuration");
      if (type >= F_FILES_CONFIG && type <= F_FILES_END) {
        if (!(g_opt.peer_features & PF_FILES_FROM)) die(RERR_PROTOCOL, "protocol error: unnegotiated files-from frame");
        if ((type == F_FILES_CONFIG && len > 1024 * 1024 + 16) ||
            (type == F_FILES_DATA && (!len || len > 65536)) || (type == F_FILES_END && len > 10))
          die(RERR_PROTOCOL, "protocol error: oversized or malformed files-from frame");
      }
      if (type == F_XATTR_CONFIG && (len != 1 || !(g_opt.peer_features & PF_XATTRS)))
        die(RERR_PROTOCOL, "protocol error: malformed or unnegotiated xattr configuration");
      if (type == F_ACL_CONFIG && (len != 1 || !(g_opt.peer_features & PF_NATIVE_ACL)))
        die(RERR_PROTOCOL, "protocol error: malformed or unnegotiated ACL configuration");
      if (type >= F_XATTR_START && type <= F_XATTR_END) {
        if (!(g_opt.peer_features & PF_XATTR_STREAM)) die(RERR_PROTOCOL, "protocol error: unnegotiated xattr value stream");
        if ((type == F_XATTR_START && len > 20) || (type == F_XATTR_CHUNK && (len < 4 || len > 65536 + 32)) ||
            (type == F_XATTR_END && len > 18)) die(RERR_PROTOCOL, "protocol error: oversized xattr value frame");
      }
      if (type == F_KEEPALIVE) {
        if (!keepalive.load() || len) die(RERR_PROTOCOL, "protocol error: invalid or unnegotiated keep-alive");
        continue;
      }
      payload.resize(len);
      return read_exact(payload.data(), len);
    }
  }
};

Conn* g_conn = nullptr;

// Values precede their metadata references. The reader spools bounded chunks;
// worker threads consume completed values without waiting on other workers.
u64 send_xattr_value(const XattrValue& value) {
  static std::mutex start_mu;
  static u64 next_id = 0;
  u64 id;
  {
    std::lock_guard<std::mutex> lock(start_mu);
    id = ++next_id;
    if (!id) die(RERR_PROTOCOL, "xattr stream ID overflow");
    auto f = new_frame(F_XATTR_START);
    put_var(f, id), put_var(f, value.size());
    g_conn->send(std::move(f), true, 8 << 20);
  }
  XXH3_state_t hash;
  XXH3_64bits_reset(&hash);
  std::array<char, 65536> bytes;
  for (u64 pos = 0; pos < value.size();) {
    size_t n = (size_t)std::min<u64>(bytes.size(), value.size() - pos);
    if (!value.read(bytes.data(), n, pos)) die(RERR_FILEIO, "read stored extended attributes: %s", errstr(errno).c_str());
    XXH3_64bits_update(&hash, bytes.data(), n);
    auto f = new_frame(F_XATTR_CHUNK);
    put_var(f, id), put_var(f, pos), put_str(f, std::string_view(bytes.data(), n));
    g_conn->send(std::move(f), true, 8 << 20);
    pos += n;
  }
  auto f = new_frame(F_XATTR_END);
  put_var(f, id);
  u64 digest = XXH3_64bits_digest(&hash);
  f.append((const char*)&digest, sizeof digest);
  g_conn->send(std::move(f), true, 8 << 20);
  return id;
}
struct ReceivedXattr {
  XattrValue value;
  u64 received = 0;
  std::unique_ptr<XXH3_state_t, decltype(&XXH3_freeState)> hash{nullptr, XXH3_freeState};
};
std::mutex xattr_values_mu;
std::unordered_map<u64, ReceivedXattr> xattr_values;
u64 last_xattr_id = 0;
size_t active_xattr_values = 0;
void receive_xattr_value(u8 type, std::string_view payload) {
  RBuf r(payload);
  u64 id = r.var();
  std::lock_guard<std::mutex> lock(xattr_values_mu);
  if (type == F_XATTR_START) {
    u64 size = r.var();
    if (r.bad || !r.empty() || !id || id != last_xattr_id + 1 || !size || size > INT64_MAX || xattr_values.size() >= 1048576 || active_xattr_values >= MAX_WORKERS)
      die(RERR_PROTOCOL, "protocol error: invalid xattr value start");
    ReceivedXattr value;
    if (!XattrValue::allocate(size, value.value)) die(RERR_FILEIO, "store received extended attributes: %s", errstr(errno).c_str());
    value.hash.reset(XXH3_createState());
    if (!value.hash) die(RERR_FILEIO, "allocate xattr checksum state");
    XXH3_64bits_reset(value.hash.get());
    xattr_values.emplace(id, std::move(value));
    last_xattr_id = id;
    ++active_xattr_values;
    return;
  }
  auto it = xattr_values.find(id);
  if (r.bad || it == xattr_values.end() || !it->second.hash)
    die(RERR_PROTOCOL, "protocol error: unknown or completed xattr value stream");
  auto& value = it->second;
  if (type == F_XATTR_CHUNK) {
    u64 offset = r.var();
    auto bytes = r.str();
    if (r.bad || !r.empty() || bytes.empty() || bytes.size() > 65536 || offset != value.received || bytes.size() > value.value.size() - value.received)
      die(RERR_PROTOCOL, "protocol error: invalid xattr value chunk");
    if (!value.value.write(bytes.data(), bytes.size(), offset)) die(RERR_FILEIO, "write received extended attributes: %s", errstr(errno).c_str());
    XXH3_64bits_update(value.hash.get(), bytes.data(), bytes.size());
    value.received += bytes.size();
  } else {
    auto bytes = r.raw(sizeof(u64));
    if (r.bad || !r.empty() || value.received != value.value.size())
      die(RERR_PROTOCOL, "protocol error: incomplete xattr value stream");
    u64 expected;
    memcpy(&expected, bytes.data(), sizeof expected);
    if (expected != XXH3_64bits_digest(value.hash.get())) die(RERR_STREAMIO, "data corruption detected in xattr stream");
    value.hash.reset();
    --active_xattr_values;
  }
}
XattrValue take_xattr_value(u64 id) {
  std::lock_guard<std::mutex> lock(xattr_values_mu);
  auto it = xattr_values.find(id);
  if (it == xattr_values.end() || it->second.hash) die(RERR_PROTOCOL, "protocol error: unknown or incomplete xattr value reference");
  auto value = std::move(it->second.value);
  xattr_values.erase(it);
  return value;
}
void check_xattr_values_drained() {
  std::lock_guard<std::mutex> lock(xattr_values_mu);
  if (!xattr_values.empty()) die(RERR_PROTOCOL, "protocol error: unreferenced xattr value stream");
}

void send_msg(int kind, int code, std::string_view s) {
  std::string f = new_frame(F_MSG);
  f.push_back((char)kind);
  put_var(f, (u64)code);
  f.append(s);
  g_conn->send(std::move(f));
  if (kind == 2) g_conn->finish();  // fatal: make sure it reaches the client before we exit
}

[[noreturn]] void conn_lost() {
  // A timeout closes the peer before printing its diagnostic. Join that fatal
  // path instead of racing it with a second die() that could exit too early.
  if (g_conn) g_conn->check_timeout();
  // A broken connection cannot carry the fatal message back to the peer.
  g_msg_sink = nullptr;
  g_output_sink = nullptr;
  if (g_stop.load()) exit_signal();
  if (g_conn && g_conn->peer_pid > 0 && g_conn->idle_ns.load()) {
    int status = g_conn->wait_peer();
    if (WIFEXITED(status) && WEXITSTATUS(status) == RERR_TIMEOUT)
      die(RERR_TIMEOUT, "remote peer timed out in data send/receive");
  }
  die(RERR_STREAMIO, "connection unexpectedly closed");
}

// Completion status repeats the code already carried by individual F_MSGs.
// Keep a synthetic diagnostic only when the peer supplied no detail of that kind.
std::array<std::atomic<bool>, 256> peer_error_seen{};
void report_peer_error(int code, const char* message) {
  if (code > 0 && (code >= (int)peer_error_seen.size() || !peer_error_seen[code].load()))
    err_line(code, "%s", message);
}

void handle_msg(std::string_view payload) {
  RBuf r(payload);
  int kind = r.byte();
  int code = (int)r.var();
  std::string text(r.rest());
  if (kind == 0) output_legacy(text);
  else if (kind == 1) {
    if (code > 0 && code < (int)peer_error_seen.size()) peer_error_seen[code] = true;
    err_line(code, "%s", text.c_str());
  }
  else die(code ? code : RERR_STREAMIO, "%s", text.c_str());
}

void send_output(const OutputEvent& event) {
  std::string frame = new_frame(F_OUTPUT);
  put_str(frame, event.code), put_str(frame, event.path), put_str(frame, event.source), put_str(frame, event.target);
  frame.push_back((char)event.type);
  put_var(frame, (u64)event.size), put_var(frame, (u64)event.bytes), put_svar(frame, event.time);
  if (g_opt.peer_features & PF_HLINK) frame.push_back((char)event.hardlink_target);
  g_conn->send(std::move(frame), true);
}

void handle_output(std::string_view payload) {
  if (!structured_output() || g_opt.am_server) die(RERR_PROTOCOL, "file output without negotiated support");
  RBuf r(payload);
  OutputEvent event;
  event.code = r.str(), event.path = r.str(), event.source = r.str(), event.target = r.str();
  event.type = r.byte();
  event.size = (i64)r.var(), event.bytes = (i64)r.var(), event.time = r.svar();
  if (g_opt.peer_features & PF_HLINK) {
    u8 hardlink = r.byte();
    if (hardlink > 1) die(RERR_PROTOCOL, "protocol error: invalid hard-link output flag");
    event.hardlink_target = hardlink;
  }
  if (r.bad || !r.empty() || event.type > T_BLK || event.size < 0 || event.bytes < 0 ||
      (event.code.size() != ((g_opt.peer_features & PF_FILEFLAGS) ? 12 : 11) && event.code != "*deleting  ") ||
      std::any_of(event.code.begin(), event.code.end(), [](unsigned char c) { return c < 32 || c >= 127; }))
    die(RERR_PROTOCOL, "protocol error: malformed file output");
  output_event(std::move(event));
}

// Optionally compress `raw` into `f` (appending). Returns true if compressed.
bool pack(std::string& f, std::string_view raw, Worker& w) {
  StageTimer timing(g_stats.read_ns);
  if (!g_opt.compress || raw.size() < 128) return false;
  if (!w.zc) w.zc = ZSTD_createCCtx();
  size_t base = f.size(), bound = ZSTD_compressBound(raw.size());
  put_var(f, raw.size());
  size_t at = f.size();
  f.resize(at + bound);
  size_t n = ZSTD_compressCCtx((ZSTD_CCtx*)w.zc, f.data() + at, bound, raw.data(), raw.size(), (int)g_opt.compress_level);
  if (ZSTD_isError(n) || n >= raw.size()) {
    f.resize(base);
    return false;
  }
  f.resize(at + n);
  return true;
}

std::string_view unpack(std::string_view in, bool compressed, std::string& scratch, Worker& w, size_t limit = 1u << 30) {
  if (!compressed) {
    if (in.size() > limit) die(RERR_PROTOCOL, "protocol error: oversized frame body");
    return in;
  }
  if (!(g_opt.peer_features & PF_ZSTD)) die(RERR_PROTOCOL, "compressed data without negotiated zstd support");
  RBuf r(in);
  size_t raw = (size_t)r.var();
  std::string_view z = r.rest();
  if (r.bad || raw > limit) die(RERR_PROTOCOL, "protocol error: bad compressed frame");
  if (!w.zd) w.zd = ZSTD_createDCtx();
  scratch.resize(raw);
  size_t n = ZSTD_decompressDCtx((ZSTD_DCtx*)w.zd, scratch.data(), raw, z.data(), z.size());
  if (ZSTD_isError(n) || n != raw) die(RERR_STREAMIO, "decompression failed: corrupt data stream");
  return scratch;
}

// ---------------------------------------------------------------- options on the wire

u32 get_fileflags(RBuf& r) {
  u64 flags = r.var();
  if (r.bad || flags > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: bad file flags");
  return (u32)flags;
}
u32 get_identity(RBuf& r) {
  u64 id = r.var();
  if (r.bad || id > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: bad owner/group identity");
  return (u32)id;
}

std::string missing_feature(u64 features) {
  if (!g_opt.am_server && g_opt.progress && g_opt.progress_mode == Options::Json && !(features & PF_OUTPUT))
    return "peer does not support JSON file events";
  if (!g_opt.link_dest.empty() && !g_opt.list_only && !(features & PF_LINK_DEST)) return "peer does not support --link-dest";
  if (g_opt.sparse && !g_opt.list_only && !(features & PF_SPARSE)) return "peer does not support --sparse";
  if (g_opt.ownership.requested() && !g_opt.list_only && !(features & PF_CHOWN)) return "peer does not support --chown";
  if (g_opt.fileflags && !g_opt.list_only && !(features & PF_FILEFLAGS)) return "peer does not support --fileflags";
  if (g_opt.executability && !g_opt.perms && !g_opt.list_only && !(features & PF_EXECUTABILITY)) return "peer does not support --executability";
  if (g_opt.atimes && !g_opt.list_only && !(features & PF_ATIMES)) return "peer does not support --atimes";
  if (g_opt.crtimes && !g_opt.list_only && !(features & PF_CRTIMES)) return "peer does not support --crtimes";
  if (g_opt.open_noatime && !g_opt.list_only && !(features & PF_OPEN_NOATIME)) return "peer does not support --open-noatime";
  if (g_opt.acls && !g_opt.list_only && !(features & PF_NATIVE_ACL)) return "peer does not support the required ACL style";
  if (g_opt.acls && !g_opt.list_only && PF_NATIVE_ACL == PF_ACL_DARWIN && !(features & PF_ACL_UUID))
    return "peer does not support unresolved ACL UUID principals";
  if (g_opt.xattrs && !g_opt.list_only && !(features & PF_XATTRS)) return "peer does not support --xattrs";
  if ((features & PF_XATTRS) && !(features & PF_XATTR_STREAM)) return "peer does not support streamed --xattrs";
  if (g_opt.files_from_set && !(features & PF_FILES_FROM)) return "peer does not support --files-from";
  if (g_opt.relative && !(features & PF_RELATIVE)) return "peer does not support --relative";
  if (g_opt.prune_empty && !(features & PF_PRUNE_EMPTY)) return "peer does not support --prune-empty-dirs";
  if (!g_opt.list_only && g_opt.delete_after && !(features & PF_DELETE_AFTER))
    return "peer does not support --delete-after";
  if (!(features & PF_CORE)) return "peer does not support the required core transfer features";
  if ((g_opt.bwlimit || g_opt.timeout) && !(features & PF_IO_CONTROL))
    return "peer does not support bandwidth limits and idle timeouts";
  if (g_opt.filters.needs_extended() && !(features & PF_FILTERS))
    return "peer does not support extended filters";
  if (g_opt.filters.has_merges() && !(features & PF_MERGE_FILTERS))
    return "peer does not support per-directory filters";
  if ((g_opt.filters.has_cvs() || g_opt.filters.has_merges()) && !(features & PF_CVS_FILTERS))
    return "peer does not support global CVS filters";
  if (g_opt.list_only) return features & PF_LIST ? "" : "peer does not support source listing";
  if (g_opt.safe_links && !(features & PF_SAFE_LINKS)) return "peer does not support --safe-links";
  if (!g_opt.numeric_ids && (g_opt.owner || g_opt.group || g_opt.ownership.requested()) && !(features & PF_IDMAP))
    return "peer does not support user/group name mapping (use --numeric-ids)";
  return {};
}

void put_options(std::string& f) {
  const Options& o = g_opt;
#define X(n) f.push_back((char)(o.n || (std::string_view(#n) == "itemize" && (o.out_format_set || !o.log_file.empty()))));
  WIRE_V3_BOOL_OPTS(X)
#undef X
#define X(n) put_svar(f, o.n);
  WIRE_V3_INT_OPTS(X)
#undef X
  // Extended syntax must not reach legacy parsers before capability negotiation.
  auto rules = o.filters.needs_extended() ? std::vector<std::string>() : o.filters.to_strings();
  put_var(f, rules.size());
  for (auto& r : rules) put_str(f, r);
}

void get_options(RBuf& r) {
  Options& o = g_opt;
#define X(n) o.n = r.byte();
  WIRE_V3_BOOL_OPTS(X)
#undef X
#define X(n) o.n = r.svar();
  WIRE_V3_INT_OPTS(X)
#undef X
  size_t n = (size_t)r.var();
  std::string err;
  for (size_t i = 0; i < n && !r.bad; i++) {
    std::string rule(r.str());
    if (!o.filters.add_filter(rule, &err, false, false)) die(RERR_PROTOCOL, "protocol error: bad filter rule from client: %s", err.c_str());
  }
}

// ---------------------------------------------------------------- uid/gid names

struct IdMaps {
  std::mutex mu;
  std::unordered_set<u64> sent;            // sender: (kind<<32 | id) already described
  std::unordered_map<u32, u32> uid, gid;   // receiver: remote id -> local id

  // Sender: emit name records for ids not seen before.
  void describe(Conn& c, const DirList& l, const Entry& attrs) {
    const Options& o = g_opt;
    if (o.numeric_ids || (!o.owner && !o.group && !o.ownership.requested()) || !(o.peer_features & PF_IDMAP)) return;
    std::string f;
    std::lock_guard<std::mutex> lk(mu);
    auto one = [&](int kind, u32 id) {
      if (!sent.insert(((u64)kind << 32) | id).second) return;
      const char* name = nullptr;
      if (kind == 0) {
        if (passwd* pw = getpwuid(id)) name = pw->pw_name;
      } else if (group* gr = getgrgid(id)) name = gr->gr_name;
      if (!name) return;
      if (f.empty()) f = new_frame(F_IDMAP);
      f.push_back((char)kind);
      put_var(f, id);
      put_str(f, name);
    };
    auto both = [&](const Entry& e) {
      if (o.owner || o.ownership.user_set) one(0, e.uid);
      if (o.group || o.ownership.group_set) one(1, e.gid);
    };
    both(attrs);
    for (const Entry& e : l.e) both(e);
    if (!f.empty()) c.send(std::move(f));
  }
  void learn(std::string_view payload) {
    RBuf r(payload);
    std::lock_guard<std::mutex> lk(mu);
    while (!r.empty() && !r.bad) {
      int kind = r.byte();
      u32 id = (u32)r.var();
      std::string name(r.str());
      if (kind == 0) {
        if (passwd* pw = getpwnam(name.c_str())) uid[id] = pw->pw_uid;
      } else if (group* gr = getgrnam(name.c_str())) gid[id] = gr->gr_gid;
    }
  }
  void map(Entry& e) {
    if (uid.empty() && gid.empty()) return;
    if (auto it = uid.find(e.uid); it != uid.end()) e.uid = it->second;
    if (auto it = gid.find(e.gid); it != gid.end()) e.gid = it->second;
  }
};

// ---------------------------------------------------------------- sender

enum { K_WALK = 1, K_READ = 2, K_GEN = 3, K_DATA = 4, K_SIGNATURE = 5, K_PRUNE = 6 };

struct SDir {
  std::string src_path, rel, attr_source;
  std::vector<std::string> src_paths;
  std::vector<std::shared_ptr<const FilterList>> source_contexts;
  std::shared_ptr<const FilterList> source_filter;
  DirList list;
  XattrSet attrs_xattrs;
  std::vector<XattrSet> src_xattrs;
  bool attrs_xattrs_loaded = false;
  std::unordered_map<u32, ResumePrefix> prefixes;
  std::unordered_set<u32> delta_candidates;
  Entry attrs;
  u8 flags = 0;
  u32 id = 0;
  bool prelisted = false;
  std::shared_ptr<SelectedSource> selection;
  std::atomic<int> pending{2};  // walker and outstanding NEED; reads add references
};

struct Sender {
  Conn& c;
  SourceGuard guard;
  Pool pool;
  IdMaps ids;
  std::mutex smu;
  std::vector<SDir*> dirs;
  std::atomic<u32> next_id{0};
  std::mutex stage_mu;
  u64 stage_last = 0;

  void stage_snapshot(bool force = false) {
    if (client || !(g_opt.peer_features & PF_STAGE_METRICS)) return;
    std::lock_guard<std::mutex> lock(stage_mu);
    u64 now = now_ns();
    if (!force && now - stage_last < 100000000) return;
    std::string frame = new_frame(F_STAGE);
    put_var(frame, g_stats.read_ns), put_var(frame, g_stats.network_ns);
    c.send(std::move(frame));
    stage_last = now;
  }
  std::atomic<int> walks{0};
  u64 dirs_sent = 0, needs_recv = 0;  // guarded by the pool lock
  std::atomic<u64> dirs_sent_a{0};
  bool client;  // we are the client: keep progress counters
  std::mutex done_mu;
  std::condition_variable done_cv;
  bool got_done = false;
  struct DeltaReply {
    std::condition_variable cv;
    bool ready = false;
    std::shared_ptr<DeltaSignature> signature;
  };
  std::mutex reply_mu;
  std::unordered_map<u64, std::shared_ptr<DeltaReply>> signatures, retry_acks;

  Sender(Conn& conn, bool is_client) : c(conn), client(is_client) {}

  void put_fresh_attrs(std::string& body, const Entry& attrs, const XattrSet& xattrs) {
    // A source retry can reveal an owner/group absent from its original list.
    // Describe that identity before sending DATA that refers to it.
    DirList empty;
    ids.describe(c, empty, attrs);
    put_file_attrs(body, attrs, xattrs);
  }

  std::shared_ptr<DeltaReply> expect_reply(u64 key, bool retry) {
    auto reply = std::make_shared<DeltaReply>();
    std::lock_guard<std::mutex> lock(reply_mu);
    auto& replies = retry ? retry_acks : signatures;
    if (!replies.emplace(key, reply).second) die(RERR_PROTOCOL, "protocol error: duplicate delta request");
    return reply;
  }
  void wait_reply(const std::shared_ptr<DeltaReply>& reply) {
    std::unique_lock<std::mutex> lock(reply_mu);
    while (!reply->ready) {
      reply->cv.wait_for(lock, std::chrono::milliseconds(66));
      if (g_stop.load()) { lock.unlock(); exit_signal(); }
    }
  }
  void on_delta_reply(std::string_view payload, bool retry) {
    if (!delta_enabled()) die(RERR_PROTOCOL, "protocol error: unnegotiated delta reply");
    RBuf r(payload);
    u64 id = r.var(), idx = r.var();
    if (id > UINT32_MAX || idx > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: bad delta reply index");
    std::shared_ptr<DeltaSignature> sig;
    static thread_local Worker worker;
    static thread_local std::string scratch;
    if (!retry) {
      u8 compressed = r.byte();
      if (r.bad || compressed > 1) die(RERR_PROTOCOL, "protocol error: bad delta compression flag");
      r = RBuf(unpack(r.rest(), compressed, scratch, worker, (size_t)DELTA_MAX_BLOCKS * 12 + 64));
      u8 present = r.byte();
      if (present > 1) die(RERR_PROTOCOL, "protocol error: bad delta signature flag");
      if (present) {
        sig = std::make_shared<DeltaSignature>();
        sig->size = (i64)r.var();
        u64 block_size = r.var(), count = r.var();
        if (sig->size <= 0 || block_size < 1024 || block_size > DELTA_MAX_BLOCK ||
            !count || count > DELTA_MAX_BLOCKS || count != (u64)((sig->size - 1) / block_size + 1) ||
            count > (u64)(r.e - r.p) / 12)
          die(RERR_PROTOCOL, "protocol error: bad delta signature dimensions");
        sig->block_size = (u32)block_size;
        sig->blocks.resize((size_t)count);
        for (auto& block : sig->blocks) {
          auto weak = r.raw(4), strong = r.raw(8);
          if (!r.bad) memcpy(&block.weak, weak.data(), 4), memcpy(&block.strong, strong.data(), 8);
        }
      }
    }
    if (r.bad || !r.empty()) die(RERR_PROTOCOL, "protocol error: trailing or truncated delta reply");
    std::lock_guard<std::mutex> lock(reply_mu);
    auto& replies = retry ? retry_acks : signatures;
    auto it = replies.find((id << 32) | idx);
    if (it == replies.end() || it->second->ready) die(RERR_PROTOCOL, "protocol error: unsolicited delta reply");
    auto reply = it->second;
    reply->signature = std::move(sig), reply->ready = true;
    reply->cv.notify_all();
    replies.erase(it);
  }

  void push_walk(SDir* d, u32 parent_plus1, u32 pidx) {
    walks.fetch_add(1);
    Task t;
    t.kind = K_WALK;
    t.ptr = d;
    t.a = parent_plus1, t.b = pidx;
    pool.push(0, std::move(t));
  }

  bool walk(SDir* d, u32 parent_plus1, u32 pidx, Worker& w) {
    const Options& o = g_opt;
    if (!d->prelisted) {
      int e = list_dir(d->src_path.c_str(), d->list, o.copy_links ? LD_FOLLOW : o.links ? LD_LINKS : 0);
      if (e) {
        err_line(RERR_PARTIAL, "opendir \"%s\" failed: %s", d->src_path.c_str(), errstr(e).c_str());
        // Still send the directory's attributes, while protecting its contents.
        d->list.clear();
        d->flags |= DF_NODELETE;
      }
      if (d->list.incomplete) {
        d->flags |= DF_NODELETE;
        err_line(RERR_PARTIAL, "incomplete source listing: \"%s\"", d->src_path.c_str());
      }
      d->source_filter = directory_filters(d->source_filter, d->src_path, false);
      prune_source(d->list, d->rel, d->attrs.dev, w, nullptr, guard, d->src_path, d->source_filter.get());
    }
    DirList& l = d->list;
    if (metadata_enabled()) {
      const FilterList& base = d->source_filter ? *d->source_filter : o.filters;
      if ((d->flags & DF_ATTRS) && !d->attrs_xattrs_loaded) {
        d->attrs_xattrs = source_xattrs(d->attr_source.empty() ? d->src_path : d->attr_source, T_DIR, base);
        d->attrs_xattrs_loaded = true;
      }
      d->src_xattrs.resize(l.e.size());
      for (size_t i = 0; i < l.e.size(); ++i) {
        if (l.e[i].item_flags & IF_PRUNED) continue;
        const auto& context = d->source_contexts.empty() ? d->source_filter : d->source_contexts[i];
        d->src_xattrs[i] = source_xattrs(d->src_paths.empty() ? path_join(d->src_path, l.name_sv(l.e[i])) : d->src_paths[i],
                                        l.e[i].type, context ? *context : base);
      }
    }
    if (o.checksum) {
      l.sums.assign(l.e.size() * 2, 0);
      for (size_t i = 0; i < l.e.size(); i++) {
        if (l.e[i].type != T_REG) continue;
        w.p2 = d->src_paths.empty() ? path_join(d->src_path, l.name_sv(l.e[i])) : d->src_paths[i];
        if (!hash_file(w.p2.c_str(), &l.sums[2 * i]))
          err_line(RERR_PARTIAL, "source checksum read failed on \"%s\": %s", w.p2.c_str(), errstr(errno).c_str());
      }
    }
    u32 id = d->id = next_id.fetch_add(1);
    std::string body;
    put_str(body, d->rel);
    put_var(body, incoming_mode(d->attrs.mode, d->attrs.type));
    put_svar(body, d->attrs.mtime);
    put_var(body, d->attrs.mtime_ns);
    put_var(body, d->attrs.uid);
    put_var(body, d->attrs.gid);
    if (o.peer_features & PF_ATIMES) put_svar(body, d->attrs.atime);
    if (o.peer_features & PF_CRTIMES) put_svar(body, d->attrs.crtime);
    if (o.peer_features & PF_FILEFLAGS) put_var(body, d->attrs.fileflags);
    if (o.peer_features & PF_DIR_OUTPUT) {
      put_var(body, (u64)d->attrs.size);
      put_str(body, d->attr_source.empty() ? d->src_path : d->attr_source);
    }
    if (o.peer_features & PF_XATTRS) put_xattrs(body, d->attrs_xattrs);
    if (o.peer_features & PF_NATIVE_ACL) put_acls(body, d->attrs_xattrs);
    put_var(body, l.e.size());
    u64 nf = 0, nd = 0, nl = 0, ns = 0, nb = 0;
    for (size_t i = 0; i < l.e.size(); i++) {
      const Entry& e = l.e[i];
      put_str(body, l.name_sv(e));
      body.push_back((char)e.type);
      put_var(body, incoming_mode(e.mode, e.type));
      put_svar(body, e.mtime);
      put_var(body, e.mtime_ns);
      if (o.owner || (o.peer_features & PF_CHOWN)) put_var(body, e.uid);
      if (o.group || (o.peer_features & PF_CHOWN)) put_var(body, e.gid);
      if (o.peer_features & PF_ATIMES) put_svar(body, e.atime);
      if (o.peer_features & PF_CRTIMES) put_svar(body, e.crtime);
      if (o.peer_features & PF_FILEFLAGS) put_var(body, e.fileflags);
      switch (e.type) {
        case T_REG:
          put_var(body, (u64)e.size);
          if (o.checksum) body.append((const char*)&l.sums[2 * i], 16);
          nf++, nb += (u64)e.size;
          break;
        case T_DIR:
          put_var(body, e.rdev == 1);
          if (o.peer_features & (PF_RELATIVE | PF_FILES_FROM)) body.push_back((char)(bool)(e.item_flags & IF_SELECTED_CHILD));
          nd++;
          break;
        case T_LNK: put_str(body, l.link(e)), nl++; break;
        case T_CHR:
        case T_BLK: put_var(body, e.rdev); [[fallthrough]];
        default: if (e.type != T_NONE) ns++;
      }
      if (o.peer_features & PF_HLINK) {
        put_var(body, e.hdev), put_var(body, e.ino), put_var(body, e.nlink);
        put_svar(body, e.ctime), put_var(body, e.ctime_ns);
      }
      if (structured_output()) {
        if (e.type != T_REG) put_var(body, (u64)e.size);
        put_str(body, d->src_paths.empty() ? path_join(d->src_path, l.name_sv(e)) : d->src_paths[i]);
      }
      if (o.peer_features & (PF_CVS_FILTERS | PF_RELATIVE | PF_FILES_FROM))
        put_str(body, FilterList::absolute_path(d->src_paths.empty() ? path_join(d->src_path, l.name_sv(e)) : d->src_paths[i]));
      if (o.peer_features & PF_XATTRS) put_xattrs(body, d->src_xattrs[i]);
      if (o.peer_features & PF_NATIVE_ACL) put_acls(body, d->src_xattrs[i]);
    }
    if (client) {
      g_stats.files_seen.fetch_add(nf, std::memory_order_relaxed);
      g_stats.dirs_seen.fetch_add(nd, std::memory_order_relaxed);
      g_stats.links_seen.fetch_add(nl, std::memory_order_relaxed);
      g_stats.specials_seen.fetch_add(ns, std::memory_order_relaxed);
      g_stats.bytes_seen.fetch_add(nb, std::memory_order_relaxed);
    }
    std::string f = new_frame(F_DIR);
    put_var(f, id);
    put_var(f, parent_plus1);
    put_var(f, pidx);
    size_t flag_at = f.size();
    f.push_back((char)d->flags);
    if (pack(f, body, w)) f[flag_at] |= DF_ZSTD;
    else f.append(body);
    {
      std::lock_guard<std::mutex> lk(smu);
      if (dirs.size() <= id) dirs.resize(std::max<size_t>(id + 1, dirs.size() * 2));
      dirs[id] = d;
    }
    ids.describe(c, l, d->attrs);
    dirs_sent_a.fetch_add(1);
    c.send(std::move(f), true);
    if (!o.recursive && !d->selection) return true;
    for (size_t i = 0; i < l.e.size(); i++) {
      const Entry& e = l.e[i];
      if (e.type != T_DIR || e.rdev == 1) continue;
      SDir* ch = new SDir;
      std::string_view nm = l.name_sv(e);
      ch->src_path = d->src_paths.empty() ? path_join(d->src_path, nm) : d->src_paths[i];
      ch->source_filter = d->source_contexts.empty() ? d->source_filter : d->source_contexts[i];
      ch->rel = rel_join(d->rel, nm);
      ch->attrs = e;
      if (metadata_enabled()) { ch->attrs_xattrs = d->src_xattrs[i]; ch->attrs_xattrs_loaded = true; }
      ch->flags = DF_ATTRS;
      ch->selection = d->selection;
      if (ch->selection) {
        auto selected = ch->selection->take(ch->rel);
        ch->list = std::move(selected.list);
        ch->src_paths = std::move(selected.paths);
        ch->source_contexts = std::move(selected.contexts);
        ch->attr_source = std::move(selected.source);
        ch->prelisted = true;
        if (selected.no_delete) ch->flags |= DF_NODELETE;
      }
      // The same name coming from two source arguments is merged, so neither may delete.
      if (!d->src_paths.empty() && ((i > 0 && l.name_sv(l.e[i - 1]) == nm) || (i + 1 < l.e.size() && l.name_sv(l.e[i + 1]) == nm)))
        ch->flags |= DF_NODELETE;
      push_walk(ch, id + 1, (u32)i);
    }
    return true;
  }

  // NEED from the receiver: schedule reads for the files it asked for.
  void on_need(std::string_view payload) {
    RBuf r(payload);
    u32 id = (u32)r.var();
    u64 pruned = g_opt.peer_features & PF_PRUNE_EMPTY ? r.var() : 0;
    size_t n = (size_t)r.var();
    SDir* d;
    {
      std::lock_guard<std::mutex> lk(smu);
      d = id < dirs.size() ? dirs[id] : nullptr;
      if (d) dirs[id] = nullptr;
    }
    if (!d || r.bad || n > d->list.e.size()) die(RERR_PROTOCOL, "protocol error: bad NEED frame");
    if (pruned > (u64)std::count_if(d->list.e.begin(), d->list.e.end(), [](const Entry& e) { return e.type == T_DIR; }))
      die(RERR_PROTOCOL, "protocol error: bad pruned directory count");
    if (client && pruned) g_stats.dirs_seen.fetch_sub(pruned, std::memory_order_relaxed);
    if (n == 0) {
      if (d->pending.fetch_sub(1) == 1) delete d;
    } else {
      std::vector<u32> idx(n);
      u32 prev = 0;
      u64 bytes = 0;
      for (size_t i = 0; i < n; i++) {
        u64 difference = r.var();
        if (r.bad || difference > UINT32_MAX - prev || (i && !difference)) die(RERR_PROTOCOL, "protocol error: bad NEED index");
        prev += (u32)difference;
        if (prev >= d->list.e.size()) die(RERR_PROTOCOL, "protocol error: bad NEED index");
        idx[i] = prev;
        if (resume_enabled()) {
          ResumePrefix prefix;
          prefix.size = (i64)r.var();
          if (prefix.size) prefix.sum[0] = r.var(), prefix.sum[1] = r.var();
          if (r.bad || prefix.size < 0 || prefix.size > d->list.e[prev].size) die(RERR_PROTOCOL, "protocol error: bad resume prefix");
          if (prefix.size) d->prefixes.emplace(prev, prefix);
        }
        if (delta_enabled()) {
          u8 eligible = r.byte();
          if (eligible > 1 || (eligible && d->list.e[prev].type != T_REG))
            die(RERR_PROTOCOL, "protocol error: bad delta candidate");
          if (eligible) d->delta_candidates.insert(prev);
        }
        bytes += (u64)d->list.e[prev].size;
      }
      if (client) {
        g_stats.xfer_files_total.fetch_add(n, std::memory_order_relaxed);
        g_stats.xfer_bytes_total.fetch_add(bytes, std::memory_order_relaxed);
      }
      std::vector<Task> tasks;
      size_t start = 0;
      i64 acc = 0;
      for (size_t i = 0; i < n; i++) {
        acc += d->list.e[idx[i]].size;
        if (i + 1 - start >= 64 || acc >= (8 << 20) || i + 1 == n) {
          Task t;
          t.kind = K_READ;
          t.ptr = d;
          t.s.assign((const char*)&idx[start], (i + 1 - start) * sizeof(u32));
          tasks.push_back(std::move(t));
          start = i + 1, acc = 0;
        }
      }
      d->pending.fetch_add((int)tasks.size() - 1);  // replace NEED reference with reads
      for (Task& t : tasks) pool.push(1, std::move(t));
    }
    if (r.bad || !r.empty()) die(RERR_PROTOCOL, "protocol error: trailing or truncated NEED frame");
    pool.update([&] { needs_recv++; });
  }

  void begin_block(Worker& w) {
    w.block.assign(DATA_PREFIX, '\0');
    w.block_files = 0;
  }
  void flush_block(Worker& w) {
    if (w.block.size() <= DATA_PREFIX) return;
    std::string_view raw(w.block.data() + DATA_PREFIX, w.block.size() - DATA_PREFIX);
    u64 h = XXH3_64bits(raw.data(), raw.size());
    std::string f;
    if (g_opt.compress) {
      f = new_frame(F_DATA);
      f.push_back(1);
      f.append((const char*)&h, 8);
      if (!pack(f, raw, w)) f.clear();
    }
    if (f.empty()) {
      f = std::move(w.block);
      f[4] = (char)F_DATA;
      f[HDR] = 0;
      memcpy(f.data() + HDR + 1, &h, 8);
    }
    g_stats.compression_raw.fetch_add(raw.size());
    g_stats.compression_wire.fetch_add(f.size() - DATA_PREFIX);
    c.send(std::move(f), true);
    stage_snapshot();
    begin_block(w);
  }

  void read_one(SDir& d, u32 idx, Worker& w) {
    const Options& o = g_opt;
    const Entry& scanned = d.list.e[idx];
    if (w.block.size() < DATA_PREFIX) begin_block(w);
    auto head = [&](u8 kind) {
      put_var(w.block, d.id), put_var(w.block, idx);
      w.block.push_back((char)kind);
    };
    w.p2 = d.src_paths.empty() ? path_join(d.src_path, d.list.name_sv(scanned)) : d.src_paths[idx];
    i64 planned = scanned.size;
    bool requested_delta = false;
    std::shared_ptr<DeltaSignature> signature;
    for (u32 attempt = 0; attempt < 2; attempt++) {
      int in = open(w.p2.c_str(), O_RDONLY | O_CLOEXEC | read_time_flags() | (o.copy_links || !d.src_paths.empty() ? 0 : O_NOFOLLOW));
      struct stat before;
      if (in < 0 || fstat(in, &before) != 0 || !S_ISREG(before.st_mode)) {
        int error = in < 0 ? errno : EIO;
        if (in >= 0) close(in);
        err_line(error == ENOENT ? RERR_VANISHED : RERR_PARTIAL, "send_files failed to open \"%s\": %s", w.p2.c_str(), errstr(error).c_str());
        head(R_FAIL);
        if (client) {
          g_stats.xfer_files_total.fetch_sub(1);
          g_stats.xfer_bytes_total.fetch_sub((u64)planned);
          slot_end(w.id);
        }
        return;
      }
      Entry fresh = source_snapshot(scanned, before, false);
      XattrSet xattrs;
      if (metadata_enabled()) {
        const auto& context = d.source_contexts.empty() ? d.source_filter : d.source_contexts[idx];
        xattrs = source_fd_xattrs(in, w.p2, T_REG, context ? *context : o.filters);
        if (o.acls && !export_acls(xattrs.acl()).complete) xattrs.complete = false;
        if (!xattrs.complete) {
          close(in);
          head(R_FAIL);
          if (client) { g_stats.xfer_files_total.fetch_sub(1); g_stats.xfer_bytes_total.fetch_sub((u64)planned); slot_end(w.id); }
          return;
        }
      }
      if (client) {
        if (fresh.size >= planned) g_stats.xfer_bytes_total.fetch_add((u64)(fresh.size - planned));
        else g_stats.xfer_bytes_total.fetch_sub((u64)(planned - fresh.size));
        slot_begin(w.id, d.rel, d.list.name_sv(scanned), fresh.size);
      }
      planned = fresh.size;
      bool ok = true;
      auto read_some = [&](char* dst, size_t want) {
        StageTimer timing(g_stats.read_ns);
        size_t n = 0;
        while (n < want && !g_stop.load()) {
          ssize_t k = read(in, dst + n, want - n);
          if (k < 0 && errno == EINTR) continue;
          if (k < 0) {
            err_line(RERR_PARTIAL, "read errors mapping \"%s\": %s", w.p2.c_str(), errstr(errno).c_str());
            ok = false;
          }
          if (k <= 0) break;
          n += (size_t)k;
        }
        return n;
      };
      bool small = (u64)fresh.size <= SMALL_MAX;
      i64 prefix = 0;
      if (!small && attempt == 0 && resume_enabled()) {
        auto offered = d.prefixes.find(idx);
        if (offered != d.prefixes.end() && offered->second.size <= fresh.size) {
          u64 digest[2];
          if (hash_prefix_fd(in, offered->second.size, digest) && digest[0] == offered->second.sum[0] && digest[1] == offered->second.sum[1])
            prefix = offered->second.size;
        }
      }
      i64 off = prefix;
      if (prefix && lseek(in, prefix, SEEK_SET) < 0) ok = false, off = prefix = 0;
      if (client && prefix) slot_add(w.id, prefix);
      if (!prefix && fresh.size > DELTA_THRESHOLD && d.delta_candidates.count(idx) && !requested_delta) {
        requested_delta = true;
        flush_block(w);
        auto reply = expect_reply(((u64)d.id << 32) | idx, false);
        std::string request = new_frame(F_DELTA_REQUEST);
        put_var(request, d.id), put_var(request, idx);
        c.send(std::move(request));
        wait_reply(reply);
        signature = reply->signature;
      }
      bool delta = !prefix && fresh.size > DELTA_THRESHOLD && signature;
      DeltaResult delta_result;
      size_t checkpoint = w.block.size();
      if (delta) {
        flush_block(w);
        delta_result = delta_match_fd(in, fresh.size, *signature, [&](const DeltaOp& op) {
          head(op.count ? R_COPY : R_LITERAL);
          put_var(w.block, attempt), put_var(w.block, (u64)op.offset), put_var(w.block, (u64)fresh.size);
          if (op.count) put_var(w.block, op.first), put_var(w.block, op.count);
          else put_str(w.block, op.literal);
          if (client) slot_add(w.id, op.count ? signature->length(op.first, op.count) : (i64)op.literal.size());
          if (w.block.size() >= BLOCK_TARGET) flush_block(w);
          return !g_stop.load();
        });
        off = delta_result.processed;
        ok = delta_result.ok;
      } else if (small) {
        w.buf.resize((size_t)fresh.size);
        off = (i64)read_some(w.buf.data(), w.buf.size());
      } else {
        flush_block(w);
        w.buf.resize(BLOCK_TARGET);
        while (off < fresh.size && !g_stop.load()) {
          size_t want = (size_t)std::min<i64>((i64)BLOCK_TARGET, fresh.size - off);
          size_t n = read_some(w.buf.data(), want);
          // Pad only the abandoned attempt so its receiver can drain all records.
          if (n < want) memset(w.buf.data() + n, 0, want - n), ok = false;
          head(R_CHUNK);
          put_var(w.block, attempt);
          if (resume_enabled()) put_var(w.block, prefix);
          put_var(w.block, (u64)off), put_var(w.block, (u64)fresh.size);
          put_str(w.block, {w.buf.data(), want});
          off += (i64)want;
          if (client) slot_add(w.id, (i64)want);
          flush_block(w);
        }
      }
      bool stable = off == fresh.size && source_unchanged(in, w.p2, before) && (!metadata_enabled() || source_xattrs_unchanged(xattrs, w.p2));
      close(in);
      bool retry = !stable && attempt == 0 && !g_stop.load();
      if (!stable && !retry && !g_stop.load())
        err_line(RERR_PARTIAL, "file changed during transfer after retry: \"%s\"", w.p2.c_str());
      if (small) {
        w.block.resize(checkpoint);
        if (stable && ok) {
          head(R_WHOLE);
          put_fresh_attrs(w.block, fresh, xattrs);
          put_str(w.block, {w.buf.data(), (size_t)off});
        } else if (!retry) head(R_FAIL);
      } else {
        head(delta ? R_DELTA_END : R_END);
        put_var(w.block, attempt);
        if (!delta && resume_enabled()) put_var(w.block, prefix);
        put_var(w.block, (u64)off);
        w.block.push_back(retry ? 1 : stable && ok ? 0 : 2);
        put_fresh_attrs(w.block, fresh, xattrs);
        if (delta) w.block.append((const char*)delta_result.sum, 16);
        std::shared_ptr<DeltaReply> ack;
        if (delta && retry) ack = expect_reply(((u64)d.id << 32) | idx, true);
        flush_block(w);
        // Inplace retries must not overlap writes from the abandoned attempt.
        if (ack) wait_reply(ack);
      }
      if (retry) continue;
      if (client) {
        if (stable && ok) g_stats.xfer_bytes.fetch_add((u64)fresh.size), g_stats.xfer_files.fetch_add(1);
        else g_stats.xfer_files_total.fetch_sub(1), g_stats.xfer_bytes_total.fetch_sub((u64)planned);
        slot_end(w.id, stable && ok);
        if (delta && stable && ok) {
          g_stats.delta_files.fetch_add(1);
          g_stats.delta_literal_bytes.fetch_add((u64)delta_result.literal_bytes);
          g_stats.delta_matched_bytes.fetch_add((u64)(fresh.size - delta_result.literal_bytes));
        }
      }
      if (w.block.size() >= BLOCK_TARGET) flush_block(w);
      return;
    }
  }

  void run_task(Task& t, Worker& w) {
    SDir* d = (SDir*)t.ptr;
    if (t.kind == K_WALK) {
      if (walk(d, t.a, t.b, w) && d->pending.fetch_sub(1) == 1) delete d;
      if (walks.fetch_sub(1) == 1) c.send(new_frame(F_LIST_END));
      return;
    }
    size_t n = t.s.size() / sizeof(u32);
    for (size_t i = 0; i < n; i++) {
      u32 idx;
      memcpy(&idx, t.s.data() + i * sizeof(u32), sizeof idx);
      read_one(*d, idx, w);
    }
    if (d->pending.fetch_sub(1) == 1) delete d;
  }

  void reader() {
    u8 type;
    std::string payload;
    for (;;) {
      if (!c.read_frame(type, payload)) conn_lost();
      switch (type) {
        case F_NEED: on_need(payload); break;
        case F_DELTA_SIGNATURE: on_delta_reply(payload, false); break;
        case F_DELTA_RETRY_ACK: on_delta_reply(payload, true); break;
        case F_MSG: handle_msg(payload); break;
        case F_OUTPUT: handle_output(payload); break;
        case F_PROGRESS: {
          RBuf r(payload);
          u64 bytes = r.var(), files = r.var();
          u64 writing = g_opt.peer_features & PF_STAGE_METRICS ? r.var() : 0;
          if (r.bad || !r.empty()) die(RERR_PROTOCOL, "protocol error: malformed progress acknowledgment");
          if (client) {
            g_stats.acknowledged_bytes.store(bytes);
            g_stats.acknowledged_files.store(files);
            g_stats.peer_write_ns.store(writing);
          }
          break;
        }
        case F_DONE: {
          RBuf r(payload);
          int code = (int)r.var();
          if (client) {
            report_peer_error(code, "errors were reported by the receiver");
            g_stats.created_files = r.var(), g_stats.created_dirs = r.var(), g_stats.created_links = r.var();
            g_stats.created_specials = r.var(), g_stats.deleted = r.var();
            if (g_opt.peer_features & PF_STAGE_METRICS) g_stats.peer_write_ns = r.var();
            if ((g_opt.peer_features & PF_STAGE_METRICS) && (r.bad || !r.empty()))
              die(RERR_PROTOCOL, "protocol error: malformed receiver stage metrics");
            if (!(g_opt.peer_features & PF_PROGRESS_ACK) && code == 0) {
              g_stats.acknowledged_bytes = g_stats.xfer_bytes.load();
              g_stats.acknowledged_files = g_stats.xfer_files.load();
            }
            g_stats.receiver_done = true;
          }
          std::lock_guard<std::mutex> lk(done_mu);
          got_done = true;
          done_cv.notify_all();
          return;
        }
        default: die(RERR_PROTOCOL, "protocol error: unexpected frame %d from receiver", type);
      }
    }
  }

  int run(const std::vector<std::string>& srcs) {
    u8 type;
    std::string payload;
    do {
      if (!c.read_frame(type, payload)) conn_lost();
      if (type == F_MSG) handle_msg(payload);
    } while (type == F_MSG);
    if (type != F_DEST) die(RERR_PROTOCOL, "protocol error: missing destination identity");
    RBuf r(payload);
    std::string machine(r.str()), path(r.str());
    u64 dev = r.var(), ino = r.var();
    if (r.bad) die(RERR_PROTOCOL, "protocol error: bad destination identity");
    if (!machine.empty() && machine == machine_identity()) {
      guard.path = std::move(path);
      guard.dev = dev, guard.ino = ino;
    }
    guard.prepare(srcs);
    Worker w0;
    RootList rl;
    build_root(srcs, rl, w0, guard);
    w0.flush_log();
    SDir* root = new SDir;
    root->list = std::move(rl.list);
    root->src_paths = std::move(rl.src_paths);
    root->source_contexts = std::move(rl.source_contexts);
    root->attrs = rl.attrs;
    root->attr_source = std::move(rl.attr_source);
    root->flags = (rl.has_attrs ? DF_ATTRS : 0) | (rl.no_delete ? DF_NODELETE : 0) | (rl.single ? DF_SINGLE : 0);
    root->selection = std::move(rl.selection);
    root->prelisted = true;
    int n = default_jobs();
    pool.scan_workers = std::max(1, n / 2);
    pool.idle_check = [this] {
      if (walks.load() != 0 || needs_recv != dirs_sent_a.load()) return false;
      g_stats.scan_done.store(true);
      return true;
    };
    pool.on_idle = [this](Worker& w) {
      if (w.block.size() <= DATA_PREFIX) return false;
      flush_block(w);
      return true;
    };
    push_walk(root, 0, 0);
    std::thread rt([this] { reader(); });
    pool.start(n, [this](Task& t, Worker& w) { run_task(t, w); });
    wait_pool(pool);
    if (g_stop.load()) exit_signal();
    pool.join();
    std::string f = new_frame(F_DATA_END);
    put_var(f, (u64)g_exit_code.load());
    c.send(std::move(f));
    {
      std::unique_lock<std::mutex> lk(done_mu);
      while (!got_done) {
        done_cv.wait_for(lk, std::chrono::milliseconds(66));
        if (g_stop.load()) { lk.unlock(); exit_signal(); }
        if (client) {
          lk.unlock();
          progress_tick();
          lk.lock();
        }
      }
    }
    if (g_stop.load()) exit_signal();
    rt.join();
    stage_snapshot(true);
    c.finish();
    return g_exit_code.load();
  }
};

// ---------------------------------------------------------------- receiver

struct RDir {
  DirWork w;
  u32 id = 0, parent_plus1 = 0, pidx = 0;
  u8 flags = 0;
  bool gen_done = false;        // guarded by Receiver::dmu
  std::vector<Task> waiters;    // children that arrived before our generator ran
  std::unordered_map<u32, ResumePrefix> prefixes;
  // Mutable transfer state is guarded by Receiver::bmu.
  std::unordered_set<u32> delta_requested, completed;
  std::unordered_map<u32, std::shared_ptr<DeltaBasis>> bases;
};

struct BigFile {
  OutFile f;
  std::mutex mu;
  Entry attrs;
  XattrSet xattrs;
  i64 received = 0, expected = -1;
  i64 prefix = 0, total = -1;
  std::map<i64, i64> chunks;
  int status = -1;
  bool ok = true;
  bool opened = false;
  bool finished = false;
  bool prefix_ok = true;
  bool delta = false;
  std::shared_ptr<DeltaBasis> basis;
  i64 literal_bytes = 0;
  u64 sum[2] = {};
  int progress_slot = -1;
  i64 acknowledged = 0;
};

struct Receiver {
  Conn& c;
  Pool pool;
  IdMaps ids;
  std::string dest;
  std::mutex dmu;
  std::vector<RDir*> dirs;
  std::vector<Task> staged;
  std::mutex bmu;
  std::unordered_map<u64, std::shared_ptr<BigFile>> big;
  std::unordered_set<u64> closed_attempts;
  bool data_end = false;  // guarded by the pool lock
  std::atomic<bool> allow_disconnect{false};
  std::atomic<int> gens{0};
  std::atomic<bool> list_end{false};
  int sender_code = 0;
  bool client;

  std::mutex progress_mu;
  u64 progress_bytes = 0, progress_last_bytes = 0, progress_last_files = 0, progress_last_time = 0;

  // Serialize snapshots with updates so parallel writers cannot reorder ACKs.
  // Bound traffic to one per MiB or 100ms, plus the final snapshot.
  void acknowledge(i64 delta = 0, bool force = false) {
    if (client || !(g_opt.peer_features & PF_PROGRESS_ACK)) return;
    std::lock_guard<std::mutex> lock(progress_mu);
    if (delta < 0) {
      u64 removed = (u64)(-delta);
      if (removed > progress_bytes) die(RERR_PROTOCOL, "progress byte accounting underflow");
      progress_bytes -= removed;
    } else progress_bytes += (u64)delta;
    u64 bytes = g_opt.dry_run ? g_stats.xfer_bytes.load() : progress_bytes;
    u64 files = g_stats.xfer_files.load(), now = now_ns();
    bool changed = bytes != progress_last_bytes || files != progress_last_files;
    if (!force && (!changed || (now - progress_last_time < 100000000 &&
        bytes >= progress_last_bytes && bytes - progress_last_bytes < BLOCK_TARGET))) return;
    std::string frame = new_frame(F_PROGRESS);
    put_var(frame, bytes), put_var(frame, files);
    if (g_opt.peer_features & PF_STAGE_METRICS) put_var(frame, g_stats.write_ns);
    c.send(std::move(frame));
    progress_last_bytes = bytes, progress_last_files = files, progress_last_time = now;
  }

  Receiver(Conn& conn, bool is_client) : c(conn), client(is_client) {}

  RDir* dir(u32 id) {
    std::lock_guard<std::mutex> lk(dmu);
    return id < dirs.size() ? dirs[id] : nullptr;
  }

  void done_one(RDir& d) {
    if (d.w.pending.fetch_sub(1) == 1) finish_dir(d.w);
  }

  void complete_file(RDir& d, u32 idx) {
    {
      std::lock_guard<std::mutex> lock(bmu);
      if (!d.completed.insert(idx).second) die(RERR_PROTOCOL, "protocol error: duplicate file completion");
      d.bases.erase(idx);
    }
    done_one(d);
  }

  void on_delta_request(std::string_view payload) {
    if (!delta_enabled()) die(RERR_PROTOCOL, "protocol error: unnegotiated delta request");
    RBuf r(payload);
    u64 id = r.var(), idx = r.var();
    RDir* d;
    {
      std::lock_guard<std::mutex> lock(dmu);
      d = id < dirs.size() ? dirs[(size_t)id] : nullptr;
      if (!d || !d->gen_done) die(RERR_PROTOCOL, "protocol error: premature delta request");
    }
    if (r.bad || !r.empty() || idx >= d->w.src.e.size() || d->w.src.e[(size_t)idx].type != T_REG ||
        (!(d->w.src.e[(size_t)idx].flags & EF_INPLACE_SAFE) && d->w.src.e[(size_t)idx].link_basis == 255) ||
        !std::binary_search(d->w.need.begin(), d->w.need.end(), (u32)idx))
      die(RERR_PROTOCOL, "protocol error: unrequested delta basis");
    {
      std::lock_guard<std::mutex> lock(bmu);
      if (d->completed.count((u32)idx) || !d->delta_requested.insert((u32)idx).second)
        die(RERR_PROTOCOL, "protocol error: duplicate delta request");
    }
    Task task;
    task.kind = K_SIGNATURE, task.ptr = d, task.a = (u32)idx;
    pool.push(0, std::move(task));
  }

  void signature(RDir& d, u32 idx, Worker& worker) {
    bool active;
    {
      std::lock_guard<std::mutex> lock(bmu);
      u64 key = ((u64)d.id << 33) | ((u64)idx << 1);
      active = big.count(key) || big.count(key | 1);
    }
    // A retry of a legacy prefix attempt may still be draining; decline rather
    // than snapshotting an inplace destination while that attempt is writing it.
    auto basis = active ? std::shared_ptr<DeltaBasis>() :
      (d.w.src.e[idx].link_basis != 255 ? link_dest_delta_basis(d.w, idx) :
       destination_delta_basis(path_join(d.w.dst_path, d.w.dst_name(idx)), g_opt.inplace));
    std::string f = new_frame(F_DELTA_SIGNATURE);
    put_var(f, d.id), put_var(f, idx);
    size_t flag_at = f.size();
    f.push_back(0);
    std::string body(1, basis ? 1 : 0);
    if (basis) {
      const auto& sig = basis->signature;
      put_var(body, (u64)sig.size), put_var(body, sig.block_size), put_var(body, sig.blocks.size());
      for (const auto& block : sig.blocks) {
        body.append((const char*)&block.weak, 4), body.append((const char*)&block.strong, 8);
      }
      std::lock_guard<std::mutex> lock(bmu);
      if (d.completed.count(idx)) die(RERR_PROTOCOL, "protocol error: delta request after file completion");
      d.bases.emplace(idx, std::move(basis));
    }
    if (pack(f, body, worker)) f[flag_at] = 1;
    else f.append(body);
    c.send(std::move(f), true);
  }

  void parse_dir(RDir* d, std::string& payload, Worker& t) {
    const Options& o = g_opt;
    DirWork& w = d->w;
    RBuf h(payload);
    h.var(), h.var(), h.var(), h.byte();
    static thread_local std::string scratch;
    RBuf r(unpack(h.rest(), d->flags & DF_ZSTD, scratch, t));
    w.rel = std::string(r.str());
    w.attrs.type = T_DIR;
    w.attrs.mode = (u32)r.var();
    w.attrs.mtime = r.svar();
    w.attrs.mtime_ns = (u32)r.var();
    w.attrs.uid = get_identity(r);
    w.attrs.gid = get_identity(r);
    if (o.peer_features & PF_ATIMES) w.attrs.atime = r.svar();
    if (o.peer_features & PF_CRTIMES) w.attrs.crtime = r.svar();
    if (o.peer_features & PF_FILEFLAGS) w.attrs.fileflags = get_fileflags(r);
    if (o.peer_features & PF_DIR_OUTPUT) {
      w.attrs.size = (i64)r.var();
      w.attr_source = r.str();
      if (w.attrs.size < 0) die(RERR_PROTOCOL, "protocol error: negative directory size");
    }
    if (o.peer_features & PF_XATTRS) {
      w.attrs_xattrs = get_xattrs(r);
    }
    if (o.peer_features & PF_NATIVE_ACL) {
      get_acls(r, w.attrs_xattrs, T_DIR);
      incoming_acl_mode(w.attrs_xattrs.acls, w.attrs.mode, T_DIR);
    }
    if (metadata_enabled()) {
      w.xattrs_loaded = w.attrs_xattrs_loaded = true;
      if (!w.attrs_xattrs.complete) { g_source_io_error.store(true); err_line(RERR_PARTIAL, "incomplete source directory metadata"); }
    }
    size_t n = (size_t)r.var();
    if (r.bad || n > (1u << 28)) die(RERR_PROTOCOL, "protocol error: bad DIR frame");
    DirList& l = w.src;
    l.e.resize(n);
    if (metadata_enabled()) w.src_xattrs.resize(n);
    std::vector<std::string> filter_sources;
    if (o.peer_features & (PF_CVS_FILTERS | PF_RELATIVE | PF_FILES_FROM)) filter_sources.resize(n);
    if (structured_output()) w.output_sources.resize(n);
    if (o.checksum) l.sums.assign(n * 2, 0);
    for (size_t i = 0; i < n; i++) {
      Entry& e = l.e[i];
      std::string_view nm = r.str();
      // Never let a hostile or buggy sender escape the destination directory.
      if (nm.empty() || nm == "." || nm == ".." || nm.find('/') != std::string_view::npos || nm.find('\0') != std::string_view::npos)
        die(RERR_PROTOCOL, "protocol error: unsafe file name from sender");
      e.name_off = l.add_str(nm);
      e.name_len = (u16)nm.size();
      e.type = r.byte();
      e.mode = (u32)r.var() & 07777;
      e.mtime = r.svar();
      e.mtime_ns = (u32)r.var();
      if (o.owner || (o.peer_features & PF_CHOWN)) e.uid = get_identity(r);
      if (o.group || (o.peer_features & PF_CHOWN)) e.gid = get_identity(r);
      if (o.peer_features & PF_ATIMES) e.atime = r.svar();
      if (o.peer_features & PF_CRTIMES) e.crtime = r.svar();
      if (o.peer_features & PF_FILEFLAGS) e.fileflags = get_fileflags(r);
      switch (e.type) {
        case T_REG:
          e.size = (i64)r.var();
          if (o.checksum) memcpy(&l.sums[2 * i], r.raw(16).data(), r.bad ? 0 : 16);
          break;
        case T_LNK: {
          auto target = r.str();
          if (target.find('\0') != std::string_view::npos) die(RERR_PROTOCOL, "protocol error: NUL in symlink target");
          e.link_off = l.add_str(target);
          break;
        }
        case T_DIR:
          e.rdev = (u32)r.var();
          if (o.peer_features & (PF_RELATIVE | PF_FILES_FROM)) {
            u8 selected = r.byte();
            if (selected > 1) die(RERR_PROTOCOL, "protocol error: bad selected directory flag");
            if (selected) e.item_flags |= IF_SELECTED_CHILD;
          }
          break;
        case T_CHR:
        case T_BLK: e.rdev = (u32)r.var(); break;
        default: break;
      }
      if (o.peer_features & PF_HLINK) {
        e.hdev = r.var(), e.ino = r.var(), e.nlink = r.var();
        e.ctime = r.svar(), e.ctime_ns = (u32)r.var();
      }
      if (structured_output()) {
        if (e.type != T_REG) e.size = (i64)r.var();
        w.output_sources[i] = r.str();
        if (e.size < 0) die(RERR_PROTOCOL, "protocol error: negative file size");
      }
      if (o.peer_features & (PF_CVS_FILTERS | PF_RELATIVE | PF_FILES_FROM)) {
        filter_sources[i] = r.str();
        if (filter_sources[i].find('\0') != std::string::npos)
          die(RERR_PROTOCOL, "protocol error: NUL in filter source path");
      }
      if (o.peer_features & PF_XATTRS) {
        w.src_xattrs[i] = get_xattrs(r);
      }
      if (o.peer_features & PF_NATIVE_ACL) {
        get_acls(r, w.src_xattrs[i], e.type);
        incoming_acl_mode(w.src_xattrs[i].acls, e.mode, e.type);
      }
      if (metadata_enabled() && !w.src_xattrs[i].complete) { g_source_io_error.store(true); err_line(RERR_PARTIAL, "incomplete source metadata: %s", l.name(e)); }
    }
    if (r.bad || !r.empty()) die(RERR_PROTOCOL, "protocol error: truncated or trailing DIR frame");
    if (client && o.file_requests) {
      for (const auto& entry : l.e) {
        auto path = rel_join(w.rel, l.name_sv(entry));
        if (!o.file_requests->permits(path, entry.type == T_DIR))
          die(RERR_UNSUPPORTED, "rejecting unrequested file-list name: %s", path.c_str());
      }
    }
    // A per-directory merge delegates selection to the sender. Otherwise a
    // global CVS list must also agree with the pulling client's settings.
    if (client && (o.relative || o.files_from_set || o.filters.has_cvs()) && !o.filters.trusts_sender_filters()) {
      for (size_t i = 0; i < l.e.size(); ++i) {
        const Entry& e = l.e[i];
        auto name = l.name_sv(e);
        if (o.filters.excluded(rel_join(w.rel, name), e.type == T_DIR,
                               filter_sources[i]))
          die(RERR_UNSUPPORTED, "rejecting excluded file-list name: %s", rel_join(w.rel, name).c_str());
      }
    }
    if ((o.owner || o.group) && !o.numeric_ids) {
      std::lock_guard<std::mutex> lk(ids.mu);
      ids.map(w.attrs);
      for (Entry& e : l.e) ids.map(e);
    }
    incoming_ownership(w.attrs);
    for (Entry& e : l.e) incoming_ownership(e);
    if (!d->parent_plus1) {
      if (!w.rel.empty()) die(RERR_PROTOCOL, "protocol error: nonempty root path");
    } else {
      RDir* parent = dir(d->parent_plus1 - 1);
      if (!parent || d->pidx >= parent->w.src.e.size()) die(RERR_PROTOCOL, "protocol error: bad parent in DIR frame");
      const auto& entry = parent->w.src.e[d->pidx];
      if ((entry.type != T_DIR && entry.type != T_NONE) || w.rel != rel_join(parent->w.rel, parent->w.src.name_sv(entry)))
        die(RERR_PROTOCOL, "protocol error: inconsistent directory path");
    }
  }

  void generate_dir(RDir* d, Worker& t) {
    const Options& o = g_opt;
    DirWork& w = d->w;
    DirList& l = w.src;
    bool go = true;
    w.no_delete = d->flags & DF_NODELETE;
    if (d->parent_plus1 == 0) {
      if (!w.rel.empty()) die(RERR_PROTOCOL, "protocol error: nonempty root path");
      w.has_attrs = d->flags & DF_ATTRS;
      go = setup_dest(dest, w, d->flags & DF_SINGLE);
    } else {
      RDir* p = dir(d->parent_plus1 - 1);
      if (!p || d->pidx >= p->w.src.e.size()) die(RERR_PROTOCOL, "protocol error: bad parent in DIR frame");
      const Entry& pe = p->w.src.e[d->pidx];
      if ((pe.type != T_DIR && pe.type != T_NONE) || w.rel != rel_join(p->w.rel, p->w.src.name_sv(pe)))
        die(RERR_PROTOCOL, "protocol error: inconsistent directory path");
      go = pe.flags & EF_DESCEND;
      w.dst_path = path_join(p->w.dst_path, p->w.src.name_sv(pe));
      w.receiver_filter = p->w.receiver_filter;
      w.receiver_filter_node = p->w.receiver_filter_node;
      w.attrs.mode = pe.mode;  // final mode as decided by the parent's generator
      w.has_attrs = true;
      w.created = pe.flags & EF_CREATED;
      w.mode_ok = pe.flags & EF_MODE_OK;
      w.time_ok = pe.flags & EF_TIME_OK;
    }
    w.pending.store(1);
    std::string f = new_frame(F_NEED);
    put_var(f, d->id);
    if (o.peer_features & PF_PRUNE_EMPTY)
      put_var(f, std::count_if(l.e.begin(), l.e.end(), [](const Entry& e) { return e.item_flags & IF_PRUNED; }));
    if (go) {
      generate(w, t);
      if (o.dry_run) {
        for (u32 i : w.need) {
          g_stats.xfer_bytes.fetch_add((u64)l.e[i].size, std::memory_order_relaxed);
          note_transferred(w, i, 0, t);
        }
        w.need.clear();
      }
      w.pending.fetch_add((int)w.need.size());
    } else {
      w.has_attrs = false;
      for (Entry& e : l.e) e.flags &= (u8)~EF_DESCEND;
    }
    put_var(f, w.need.size());
    u32 prev = 0;
    for (u32 i : w.need) {
      put_var(f, i - prev), prev = i;
      if (resume_enabled()) {
        ResumePrefix prefix;
        if (l.e[i].size > (i64)SMALL_MAX)
          prefix = destination_resume_prefix(path_join(w.dst_path, w.dst_name(i)).c_str(), l.e[i].size);
        put_var(f, prefix.size);
        if (prefix.size) {
          put_var(f, prefix.sum[0]), put_var(f, prefix.sum[1]);
          d->prefixes.emplace(i, prefix);
        }
      }
      if (delta_enabled()) f.push_back(((l.e[i].flags & EF_INPLACE_SAFE) || l.e[i].link_basis != 255) ? 1 : 0);
    }
    std::vector<Task> wait;
    {
      std::lock_guard<std::mutex> lk(dmu);
      d->gen_done = true;
      wait.swap(d->waiters);
    }
    c.send(std::move(f));
    for (Task& x : wait) pool.push(0, std::move(x));
    done_one(*d);
    if (gens.fetch_sub(1) == 1 && list_end.load()) g_stats.scan_done.store(true);
  }

  void gen(RDir* d, std::string& payload, Worker& worker) {
    parse_dir(d, payload, worker);
    generate_dir(d, worker);
  }

  void prune_and_generate(Worker& worker) {
    std::vector<DirWork*> directories;
    directories.reserve(staged.size());
    for (auto& task : staged) {
      auto* directory = static_cast<RDir*>(task.ptr);
      parse_dir(directory, task.s, worker);
      std::string().swap(task.s);
      directories.push_back(&directory->w);
    }
    if (g_opt.prune_empty) prune_empty_directories(directories, dest.empty() ? "." : dest);
    for (auto& task : staged) {
      if (g_stop.load()) break;
      generate_dir(static_cast<RDir*>(task.ptr), worker);
    }
    staged.clear();
  }

  void get_file_attrs(RBuf& r, Entry& attrs, XattrSet& xattrs) {
    u32 source_mode = (u32)r.var() & 07777;
    u32 mode = incoming_mode(source_mode, T_REG);
    attrs.uid = get_identity(r), attrs.gid = get_identity(r);
    attrs.mtime = r.svar(), attrs.mtime_ns = (u32)r.var();
    if (g_opt.peer_features & PF_ATIMES) attrs.atime = r.svar();
    if (g_opt.peer_features & PF_CRTIMES) attrs.crtime = r.svar();
    if (g_opt.peer_features & PF_FILEFLAGS) attrs.fileflags = get_fileflags(r);
    if (g_opt.peer_features & PF_HLINK) {
      attrs.hdev = r.var(), attrs.ino = r.var(), attrs.nlink = r.var();
      attrs.ctime = r.svar(), attrs.ctime_ns = (u32)r.var();
    }
    if (g_opt.peer_features & PF_XATTRS) xattrs = get_xattrs(r);
    if (g_opt.peer_features & PF_NATIVE_ACL) {
      get_acls(r, xattrs, T_REG);
      incoming_acl_mode(xattrs.acls, source_mode, T_REG);
    }
    if (g_opt.perms) attrs.mode = mode;
    else if (g_opt.executability && ((attrs.flags & EF_INPLACE_SAFE) || attrs.link_basis != 255)) attrs.mode = execution_mode(mode, attrs.basis_mode);
    if ((g_opt.owner || g_opt.group) && !g_opt.numeric_ids) {
      std::lock_guard<std::mutex> lock(ids.mu);
      ids.map(attrs);
    }
    incoming_ownership(attrs);
  }

  void data(std::string& payload, Worker& t) {
    StageTimer timing(g_stats.write_ns);
    if (payload.size() < 9) die(RERR_PROTOCOL, "protocol error: short DATA frame");
    u64 want;
    memcpy(&want, payload.data() + 1, 8);
    static thread_local std::string scratch;
    std::string_view raw = unpack(std::string_view(payload).substr(9), payload[0] & 1, scratch, t);
    g_stats.compression_raw.fetch_add(raw.size());
    g_stats.compression_wire.fetch_add(payload.size() - 9);
    if (XXH3_64bits(raw.data(), raw.size()) != want) die(RERR_STREAMIO, "data corruption detected in transfer stream");
    RBuf r(raw);
    RDir* d = nullptr;
    while (!r.empty()) {
      u64 raw_id = r.var(), raw_idx = r.var();
      if (raw_id > UINT32_MAX || raw_idx > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: bad DATA index");
      u32 id = (u32)raw_id, idx = (u32)raw_idx;
      u8 kind = r.byte();
      if (!d || d->id != id) d = dir(id);
      if (r.bad || !d || idx >= d->w.src.e.size()) die(RERR_PROTOCOL, "protocol error: bad DATA record");
      DirWork& w = d->w;
      const Entry& s = w.src.e[idx];
      if (!d->gen_done || s.type != T_REG || !std::binary_search(w.need.begin(), w.need.end(), idx))
        die(RERR_PROTOCOL, "protocol error: unrequested file data");
      bool delta = kind == R_LITERAL || kind == R_COPY || kind == R_DELTA_END;
      std::shared_ptr<DeltaBasis> basis;
      {
        std::lock_guard<std::mutex> lock(bmu);
        if (d->completed.count(idx)) die(RERR_PROTOCOL, "protocol error: data after file completion");
        if (delta) {
          auto it = d->bases.find(idx);
          if (!delta_enabled() || it == d->bases.end()) die(RERR_PROTOCOL, "protocol error: unrequested delta data");
          basis = it->second;
        }
      }
      if (kind == R_FAIL) {
        g_stats.xfer_files_total.fetch_sub(1, std::memory_order_relaxed);
        g_stats.xfer_bytes_total.fetch_sub((u64)s.size, std::memory_order_relaxed);
        complete_file(*d, idx);
      } else if (kind == R_WHOLE) {
        Entry attrs = s;
        XattrSet xattrs;
        get_file_attrs(r, attrs, xattrs);
        std::string_view bytes = r.str();
        attrs.size = (i64)bytes.size();
        if (r.bad || !xattrs.complete) die(RERR_PROTOCOL, "protocol error: truncated DATA record or incomplete file xattrs");
        int progress_slot = slot_claim(w.rel, w.src.name_sv(s), (i64)bytes.size());
        OutFile file;
        bool ok = out_open(file, w, idx, t);
        if (ok) {
          file.size = (i64)bytes.size();
          ok = out_write(file, bytes.data(), bytes.size(), 0);
          if (!ok) file_io_error(errno, file.path.c_str(), "write");
          ok = out_finish(file, w, idx, t, ok, &attrs, &xattrs) && ok;
        }
        if (ok) {
          g_stats.xfer_bytes.fetch_add(bytes.size());
          if ((i64)bytes.size() >= s.size) g_stats.xfer_bytes_total.fetch_add(bytes.size() - (u64)s.size);
          else g_stats.xfer_bytes_total.fetch_sub((u64)s.size - bytes.size());
          note_transferred(w, idx, (i64)bytes.size(), t, (i64)bytes.size());
          acknowledge((i64)bytes.size());
        } else {
          g_stats.xfer_files_total.fetch_sub(1);
          g_stats.xfer_bytes_total.fetch_sub((u64)s.size);
        }
        slot_set(progress_slot, ok ? (i64)bytes.size() : 0);
        slot_end(progress_slot, ok);
        complete_file(*d, idx);
      } else if (kind == R_CHUNK || kind == R_END || delta) {
        u64 raw_attempt = r.var();
        if (raw_attempt > 1) die(RERR_PROTOCOL, "protocol error: invalid retry attempt");
        u32 attempt = (u32)raw_attempt;
        bool ending = kind == R_END || kind == R_DELTA_END;
        i64 prefix = !delta && resume_enabled() ? (i64)r.var() : 0;
        i64 off = 0, total;
        i64 length = 0;
        u32 first = 0, count = 0;
        u64 sum[2] = {};
        int status = -1;
        Entry attrs = s;
        XattrSet xattrs;
        std::string_view bytes;
        if (!ending) {
          off = (i64)r.var(), total = (i64)r.var();
          if (kind == R_COPY) {
            u64 raw_first = r.var(), raw_count = r.var();
            if (raw_first > UINT32_MAX || raw_count > UINT32_MAX) die(RERR_PROTOCOL, "protocol error: bad delta reference");
            first = (u32)raw_first, count = (u32)raw_count;
            length = basis->signature.length(first, count);
            if (length <= 0 || length > (8 << 20)) die(RERR_PROTOCOL, "protocol error: bad delta reference");
          } else {
            bytes = r.str(), length = (i64)bytes.size();
            if (delta && bytes.size() > (1 << 16)) die(RERR_PROTOCOL, "protocol error: oversized delta literal");
          }
          if (off < 0 || total < 0 || length <= 0 || length > total || off > total - length)
            die(RERR_PROTOCOL, "protocol error: bad chunk");
        } else {
          total = (i64)r.var();
          status = r.byte();
          get_file_attrs(r, attrs, xattrs);
          if (delta) {
            auto digest = r.raw(16);
            if (!r.bad) memcpy(sum, digest.data(), 16);
          }
          if (total < 0 || status > 2 || (status == 0 && !xattrs.complete)) die(RERR_PROTOCOL, "protocol error: bad file completion");
        }
        if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated file record");
        auto offered = d->prefixes.find(idx);
        if (prefix < 0 || prefix > total || (prefix && (attempt || offered == d->prefixes.end() || prefix != offered->second.size)) ||
            (!ending && off < prefix)) die(RERR_PROTOCOL, "protocol error: unverified resume prefix");
        u64 key = ((u64)id << 33) | ((u64)idx << 1) | attempt;
        std::shared_ptr<BigFile> b;
        {
          std::lock_guard<std::mutex> lk(bmu);
          if (closed_attempts.count(key)) die(RERR_PROTOCOL, "protocol error: data after file completion");
          auto& item = big[key];
          if (!item) item = std::make_shared<BigFile>();
          b = item;
        }
        std::unique_lock<std::mutex> file_lock(b->mu);
        if (b->finished) die(RERR_PROTOCOL, "protocol error: data after file completion");
        if (!b->opened) {
          b->opened = true;
          b->progress_slot = slot_claim(w.rel, w.src.name_sv(s), total);
          b->attrs = s;
          b->delta = delta, b->basis = basis;
          b->ok = out_open(b->f, w, idx, t, false, delta);
          b->prefix = prefix;
          b->total = !ending ? total : -1;
          b->received = prefix;
          if (b->ok && prefix && !out_restore_prefix(b->f, offered->second)) {
            file_io_error(errno, b->f.path.c_str(), "reuse partial prefix");
            b->prefix_ok = b->ok = false;
          }
          if (b->ok && prefix) acknowledge(prefix), b->acknowledged += prefix;
        }
        if (b->prefix != prefix || b->delta != delta) die(RERR_PROTOCOL, "protocol error: inconsistent transfer method");
        if (ending) {
          if (b->status != -1) die(RERR_PROTOCOL, "protocol error: duplicate file completion");
          if ((b->total >= 0 && (total > b->total || ((delta ? status == 0 : status != 2) && total != b->total))) ||
              (!b->chunks.empty() && b->chunks.rbegin()->second > total))
            die(RERR_PROTOCOL, "protocol error: inconsistent file size");
          b->status = status, b->expected = total, b->attrs = attrs;
          b->xattrs = std::move(xattrs);
          if (delta) memcpy(b->sum, sum, 16);
        } else {
          if (b->total < 0) b->total = total;
          if (b->total != total || (b->status >= 0 && (off + length > b->expected ||
              ((delta ? b->status == 0 : b->status != 2) && total != b->expected)))) die(RERR_PROTOCOL, "protocol error: inconsistent file size");
          auto next = b->chunks.lower_bound(off);
          i64 end = off + length;
          if ((next != b->chunks.end() && next->first < end) ||
              (next != b->chunks.begin() && std::prev(next)->second > off))
            die(RERR_PROTOCOL, "protocol error: overlapping file chunks");
          i64 start = off;
          if (next != b->chunks.begin() && std::prev(next)->second == start) {
            auto previous = std::prev(next);
            start = previous->first;
            next = b->chunks.erase(previous);
          }
          if (next != b->chunks.end() && next->first == end) {
            end = next->second;
            b->chunks.erase(next);
          }
          b->chunks.emplace(start, end);
          if (b->ok) {
            bool wrote = count ? delta_copy_blocks(b->f, *basis, first, count, off, t.buf) :
              out_write(b->f, bytes.data(), bytes.size(), off);
            if (wrote) acknowledge(length), b->acknowledged += length;
            else {
              file_io_error(errno, b->f.path.c_str(), count ? "reconstruct delta" : "write");
              g_source_io_error.store(true);
              b->ok = false;
            }
          }
          if (delta && !count) b->literal_bytes += length;
          b->received += length;
          if (b->ok) slot_set(b->progress_slot, b->received);
        }
        if (b->status >= 0 && b->received == b->expected) {
          b->finished = true;
          b->f.size = b->expected;
          b->attrs.size = b->expected;
          bool ok = false;
          if (b->f.fd >= 0) {
            if (b->delta && b->status == 0 && b->ok && !delta_verify_fd(b->f.fd, b->expected, b->sum)) {
              file_io_error(errno, b->f.path.c_str(), "verify reconstructed delta");
              g_source_io_error.store(true);
              b->ok = b->prefix_ok = false;
            }
            if (b->status == 0 && b->ok) ok = out_finish(b->f, w, idx, t, true, &b->attrs, &b->xattrs);
            else out_abort(b->f, b->prefix_ok && b->status == 2 && g_opt.partial);
          }
          {
            std::lock_guard<std::mutex> lk(bmu);
            big.erase(key);
            closed_attempts.insert(key);
          }
          if (b->status != 1) {
            if (ok) {
              g_stats.xfer_bytes.fetch_add((u64)b->expected);
              if (b->expected >= s.size) g_stats.xfer_bytes_total.fetch_add((u64)(b->expected - s.size));
              else g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - b->expected));
              note_transferred(w, idx, b->delta ? b->literal_bytes : b->expected - b->prefix, t, b->expected);
              if (b->delta) {
                g_stats.delta_files.fetch_add(1);
                g_stats.delta_literal_bytes.fetch_add((u64)b->literal_bytes);
                g_stats.delta_matched_bytes.fetch_add((u64)(b->expected - b->literal_bytes));
              }
            } else {
              g_stats.xfer_files_total.fetch_sub(1);
              g_stats.xfer_bytes_total.fetch_sub((u64)s.size);
            }
            complete_file(*d, idx);
          } else if (delta) {
            std::string ack = new_frame(F_DELTA_RETRY_ACK);
            put_var(ack, id), put_var(ack, idx);
            c.send(std::move(ack));
          }
          if (!ok && b->acknowledged) acknowledge(-b->acknowledged);
          else acknowledge();
          slot_end(b->progress_slot, ok);
        }
      } else {
        die(RERR_PROTOCOL, "protocol error: unknown DATA record");
      }
    }
  }

  void on_dir(std::string& payload) {
    if (list_end.load()) die(RERR_PROTOCOL, "protocol error: DIR after LIST_END");
    RBuf h(payload);
    RDir* d = new RDir;
    d->id = (u32)h.var();
    d->parent_plus1 = (u32)h.var();
    d->pidx = (u32)h.var();
    d->flags = h.byte();
    if (h.bad || d->id > (1u << 28) || ((d->parent_plus1 == 0) != (d->id == 0)))
      die(RERR_PROTOCOL, "protocol error: bad DIR header");
    Task t;
    t.kind = K_GEN;
    t.ptr = d;
    t.s = std::move(payload);
    gens.fetch_add(1);
    {
      std::lock_guard<std::mutex> lk(dmu);
      if (dirs.size() <= d->id) dirs.resize(std::max<size_t>(d->id + 1, dirs.size() * 2));
      if (dirs[d->id]) die(RERR_PROTOCOL, "protocol error: duplicate directory");
      dirs[d->id] = d;
      if (d->parent_plus1) {
        RDir* p = d->parent_plus1 - 1 < dirs.size() ? dirs[d->parent_plus1 - 1] : nullptr;
        if (!p) die(RERR_PROTOCOL, "protocol error: DIR frame before its parent");
        if (!g_opt.prune_empty && !g_opt.file_requests && !p->gen_done) {
          p->waiters.push_back(std::move(t));
          return;
        }
      }
      if (g_opt.prune_empty || g_opt.file_requests) { staged.push_back(std::move(t)); return; }
    }
    pool.push_bounded(0, std::move(t));
  }

  void reader() {
    u8 type;
    std::string payload;
    bool ended = false;
    for (;;) {
      if (!c.read_frame(type, payload)) {
        if (allow_disconnect.load()) return;
        conn_lost();
      }
      if (ended && type != F_STAGE) die(RERR_PROTOCOL, "protocol error: frame after DATA_END");
      switch (type) {
        case F_STAGE: {
          if (!client) die(RERR_PROTOCOL, "protocol error: sender-stage metrics in a push");
          RBuf r(payload);
          u64 reading = r.var(), network = r.var();
          if (r.bad || !r.empty()) die(RERR_PROTOCOL, "protocol error: malformed stage metrics");
          g_stats.peer_read_ns = reading, g_stats.peer_network_ns = network;
          break;
        }
        case F_XATTR_START:
        case F_XATTR_CHUNK:
        case F_XATTR_END: receive_xattr_value(type, payload); break;
        case F_DIR: on_dir(payload); break;
        case F_DELTA_REQUEST: on_delta_request(payload); break;
        case F_DATA: {
          Task t;
          t.kind = K_DATA;
          t.s = std::move(payload);
          pool.push_bounded(1, std::move(t));
          break;
        }
        case F_IDMAP:
          if (!(g_opt.peer_features & PF_IDMAP)) die(RERR_PROTOCOL, "ID map without negotiated name-mapping support");
          ids.learn(payload);
          break;
        case F_MSG: handle_msg(payload); break;
        case F_LIST_END:
          if (list_end.exchange(true)) die(RERR_PROTOCOL, "protocol error: duplicate LIST_END");
          if (g_opt.prune_empty || g_opt.file_requests) {
            if (staged.empty()) die(RERR_PROTOCOL, "protocol error: LIST_END without a root directory");
            Task task;
            task.kind = K_PRUNE;
            pool.push(0, std::move(task));
          }
          if (gens.load() == 0) g_stats.scan_done.store(true);
          break;
        case F_DATA_END: {
          if ((g_opt.prune_empty || g_opt.file_requests) && !list_end.load())
            die(RERR_PROTOCOL, "protocol error: DATA_END before LIST_END");
          RBuf r(payload);
          sender_code = (int)r.var();
          if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated DATA_END");
          ended = true;
          pool.update([&] { data_end = true; });
          // Keep observing EOF while queued writes and deletion are draining.
          break;
        }
        default: die(RERR_PROTOCOL, "protocol error: unexpected frame %d from sender", type);
      }
      payload.clear();
    }
  }

  int run(const std::string& dest_path) {
    dest = dest_path;
    SourceGuard guard(dest.empty() ? "." : dest);
    std::string identity = new_frame(F_DEST);
    put_str(identity, machine_identity());
    put_str(identity, guard.path);
    put_var(identity, guard.dev), put_var(identity, guard.ino);
    c.send(std::move(identity));
    int n = default_jobs();
    pool.max_bytes = 64 << 20;
    pool.idle_check = [this] { return data_end; };
    std::thread rt([this] { reader(); });
    pool.start(n, [this](Task& t, Worker& w) {
      if (t.kind == K_PRUNE) prune_and_generate(w);
      else if (t.kind == K_GEN) gen((RDir*)t.ptr, t.s, w);
      else if (t.kind == K_SIGNATURE) signature(*(RDir*)t.ptr, t.a, w);
      else data(t.s, w);
    });
    wait_pool(pool);
    if (g_stop.load()) exit_signal();
    pool.join();
    g_stats.scan_done.store(true);
    check_xattr_values_drained();
    // DATA_END cannot turn missing records or an undrained attempt into success.
    if (!big.empty()) die(RERR_PROTOCOL, "protocol error: incomplete file data");
    for (RDir* d : dirs)
      if (d && d->w.pending.load() != 0) die(RERR_PROTOCOL, "protocol error: missing requested file completion");
    if (sender_code) g_source_io_error.store(true);
    if (client) report_peer_error(sender_code, "errors were reported by the sender");
    finalize_tree();
    if (g_stop.load()) exit_signal();
    allow_disconnect.store(true);
    acknowledge(0, true);
    std::string f = new_frame(F_DONE);
    put_var(f, (u64)g_exit_code.load());
    put_var(f, g_stats.created_files), put_var(f, g_stats.created_dirs), put_var(f, g_stats.created_links);
    put_var(f, g_stats.created_specials), put_var(f, g_stats.deleted);
    if (g_opt.peer_features & PF_STAGE_METRICS) put_var(f, g_stats.write_ns);
    c.send(std::move(f));
    c.finish();
    rt.join();
    return g_exit_code.load();
  }
};

// ---------------------------------------------------------------- client / server glue

int receive_listing(Conn& c) {
  u64 count = 0;
  const bool verify = (g_opt.relative || g_opt.files_from_set || g_opt.filters.has_cvs()) && !g_opt.filters.trusts_sender_filters();
  std::vector<ListingEntry> pending;
  u8 type;
  std::string payload;
  for (;;) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type == F_MSG) { handle_msg(payload); continue; }
    if (type == F_LIST_END) {
      RBuf r(payload);
      u64 code = r.var(), expected = r.var();
      if (r.bad || !r.empty() || code > 255 || expected != count)
        die(RERR_PROTOCOL, "protocol error: malformed listing completion");
      for (const auto& entry : pending) {
        if (g_opt.file_requests && !g_opt.file_requests->permits(entry.path, entry.attrs.type == T_DIR))
          die(RERR_UNSUPPORTED, "rejecting unrequested file-list name: %s", entry.path.c_str());
        if (verify && entry.path != "." && g_opt.filters.excluded(entry.path, entry.attrs.type == T_DIR, entry.source))
          die(RERR_UNSUPPORTED, "rejecting excluded file-list name: %s", entry.path.c_str());
      }
      if (g_opt.prune_empty) prune_listing(pending);
      for (const auto& entry : pending) listing_output(entry);
      report_peer_error((int)code, "errors were reported while listing remote sources");
      c.finish();
      close(c.wfd);
      c.wfd = -1;
      char trailing;
      if (c.read_exact(&trailing, 1)) die(RERR_PROTOCOL, "protocol error: data after listing completion");
      return (int)code;
    }
    if (type != F_LIST_ENTRY) die(RERR_PROTOCOL, "protocol error: unexpected listing frame %u", type);
    RBuf r(payload);
    ListingEntry entry;
    entry.path = r.str();
    entry.attrs.type = r.byte();
    u64 mode = r.var();
    entry.attrs.mode = (u32)mode;
    entry.attrs.size = (i64)r.var();
    entry.attrs.mtime = r.svar();
    entry.target = r.str();
    if (g_opt.peer_features & (PF_CVS_FILTERS | PF_RELATIVE | PF_FILES_FROM)) entry.source = r.str();
    if (r.bad || !r.empty() || !listing_path_valid(entry.path) || mode > 07777 ||
        entry.attrs.type < T_REG || entry.attrs.type > T_BLK || entry.attrs.size < 0 ||
        entry.target.size() > (1 << 20) || entry.target.find('\0') != entry.target.npos ||
        entry.source.find('\0') != entry.source.npos ||
        (entry.attrs.type != T_LNK && !entry.target.empty()))
      die(RERR_PROTOCOL, "protocol error: malformed listing entry");
    entry.attrs.mode = incoming_mode(entry.attrs.mode, entry.attrs.type);
    if (verify || g_opt.prune_empty || g_opt.file_requests) pending.push_back(std::move(entry));
    else listing_output(entry);
    ++count;
  }
}

std::string expand_remote_home(const std::string& path) {
  if (path.empty() || path[0] != '~') return path;
  size_t slash = path.find('/');
  std::string user = path.substr(1, slash == std::string::npos ? slash : slash - 1);
  std::string home;
  if (user.empty()) {
    if (const char* value = getenv("HOME")) home = value;
    else if (passwd* pw = getpwuid(geteuid())) home = pw->pw_dir;
  } else if (passwd* pw = getpwnam(user.c_str())) home = pw->pw_dir;
  if (home.empty()) die(RERR_FILESELECT, "cannot expand remote home in \"%s\"", path.c_str());
  if (slash != std::string::npos) home.append(path.substr(slash));
  return home;
}

std::vector<std::string> expand_remote_sources(const std::vector<std::string>& paths) {
  std::vector<std::string> expanded;
  for (const auto& path : paths) {
    if (path.find_first_of("*?[\\") == std::string::npos) {
      expanded.push_back(path);
      continue;
    }
    glob_t matches{};
    int result = glob(path.c_str(), GLOB_ERR, nullptr, &matches);
    if (result == 0) {
      for (size_t i = 0; i < matches.gl_pathc; i++) expanded.emplace_back(matches.gl_pathv[i]);
    } else {
      err_line(RERR_PARTIAL, "remote source pattern \"%s\": %s", path.c_str(),
               result == GLOB_NOMATCH ? "No such file or directory (no matches)" : "glob failed");
    }
    globfree(&matches);
  }
  return expanded;
}

}  // namespace

void cancel_remote_peer() {
  std::lock_guard<std::mutex> lock(peer_guard);
  // A second SIGTERM makes xsync bypass cleanup. Cancellation may be noticed
  // by both transport threads, so signal this child exactly once.
  if (current_remote_peer > 0 && !peer_cancelled) {
    peer_cancelled = true;
    kill(current_remote_peer, SIGTERM);
  }
}

namespace {
void send_file_frames(Conn& connection, const std::string& path, bool allow_stdin, bool from0,
                      std::vector<std::string>* names, bool forwarded) {
  FileListParser parser(from0, names, forwarded);
  u64 bytes = 0;
  read_file_chunks(path, allow_stdin, [&](std::string_view chunk) {
    parser.feed(chunk);
    bytes += chunk.size();
    std::string frame = new_frame(F_FILES_DATA);
    frame.append(chunk);
    connection.send(std::move(frame));
  }, forwarded);
  parser.feed({}, true);
  std::string end = new_frame(F_FILES_END);
  put_var(end, bytes);
  connection.send(std::move(end));
}
void receive_file_frames(Conn& connection, bool from0, std::vector<std::string>* names, bool forwarded) {
  FileListParser parser(from0, names, forwarded);
  u64 bytes = 0;
  u8 type;
  std::string payload;
  for (;;) {
    if (!connection.read_frame(type, payload)) conn_lost();
    if (type == F_MSG) { handle_msg(payload); continue; }
    if (type == F_FILES_END) {
      RBuf end(payload);
      u64 expected = end.var();
      if (end.bad || !end.empty() || expected != bytes)
        die(RERR_PROTOCOL, "protocol error: incomplete files-from stream");
      parser.feed({}, true);
      return;
    }
    if (type != F_FILES_DATA) die(RERR_PROTOCOL, "protocol error: unexpected files-from frame");
    bytes += payload.size();
    parser.feed(payload);
  }
}
}

int run_client(const std::vector<std::string>& srcs, const std::string& dest, u32 wire_version) {
  Options& o = g_opt;
  o.wire_version = wire_version;
  bool push = parse_remote_spec(dest).remote;
  RemoteSpec rem;
  std::vector<std::string> paths;  // paths on the remote side
  if (push) {
    rem = parse_remote_spec(dest);
    paths.push_back(rem.path);
  } else {
    for (const std::string& s : srcs) {
      RemoteSpec r = parse_remote_spec(s);
      if (!r.remote) die(RERR_SYNTAX, "all sources must be on the same remote host");
      if (paths.empty()) rem = r;
      else if (!r.host.empty() && (r.host != rem.host || r.user != rem.user)) die(RERR_SYNTAX, "all source args must come from the same machine.");
      paths.push_back(r.path);
    }
  }
  RemoteSpec list;
  if (o.files_from_set) {
    list = parse_remote_spec(o.files_from);
    if (list.daemon) die(RERR_SYNTAX, "files-from list must use the transfer's remote shell host");
    if (list.remote && ((!list.host.empty() && list.host != rem.host) || (list.has_user && list.user != rem.user)))
      die(RERR_SYNTAX, "files-from hostname must match the transfer host");
    if (list.remote && o.files_from.ends_with(':')) list.path.clear();
  }
  std::vector<std::string> cmd = split_shell_words(remote_shell_command());
  if (cmd.empty()) die(RERR_SYNTAX, "empty remote shell command");
  if (rem.has_user) cmd.push_back("-l"), cmd.push_back(rem.user);
  cmd.push_back(rem.host);
  if (!o.rsync_path.empty()) cmd.push_back(o.rsync_path);
  else {
    const char* override_path = getenv("XSYNC_REMOTE_PATH");
    std::string lookup =
        "if command -v xsync >/dev/null 2>&1; then exec xsync \"$@\"; "
        "elif [ -x \"$HOME/.local/bin/xsync\" ]; then exec \"$HOME/.local/bin/xsync\" \"$@\"; fi; ";
    if (override_path && *override_path) lookup += "extra=" + shell_quote(override_path) + "; ";
    else lookup += "extra=${XSYNC_REMOTE_PATH:-}; ";
    lookup += "case \"$extra\" in '~/'*) extra=\"$HOME/${extra#??}\";; esac; "
              "if [ -n \"$extra\" ] && [ -x \"$extra\" ]; then exec \"$extra\" \"$@\"; fi; exit 127";
    cmd.push_back("sh -c " + shell_quote(lookup) + " xsync");
  }
  cmd.push_back("--server");

  int to_child[2], from_child[2];
  if (pipe(to_child) != 0 || pipe(from_child) != 0) die(RERR_IPC, "pipe failed: %s", errstr(errno).c_str());
  pid_t pid = fork();
  if (pid < 0) die(RERR_IPC, "fork failed: %s", errstr(errno).c_str());
  if (pid == 0) {
    umask((mode_t)g_umask);
    dup2(to_child[0], 0);
    dup2(from_child[1], 1);
    close(to_child[0]), close(to_child[1]), close(from_child[0]), close(from_child[1]);
    std::vector<char*> argv;
    for (auto& s : cmd) argv.push_back(s.data());
    argv.push_back(nullptr);
    execvp(argv[0], argv.data());
    fprintf(stderr, "xsync: failed to exec %s: %s\n", argv[0], strerror(errno));
    _exit(RERR_CMD_NOTFOUND);
  }
  close(to_child[0]), close(from_child[1]);
  fcntl(to_child[1], F_SETFD, FD_CLOEXEC);
  fcntl(from_child[0], F_SETFD, FD_CLOEXEC);

  Conn c;
  c.rfd = from_child[0], c.wfd = to_child[1];
  c.peer_pid = pid;
  {
    std::lock_guard<std::mutex> lock(peer_guard);
    current_remote_peer = pid;
    peer_cancelled = false;
  }
  c.configure(0, o.timeout, false);  // Also covers authentication and hello waits.
  g_conn = &c;
  o.pushing = push;
  o.receiving = !push;
  // Hello: magic, version, the role the server plays, options, paths.
  std::string f = new_frame(F_HELLO);
  f.append(MAGIC, sizeof MAGIC - 1);
  put_var(f, wire_version);
  f.push_back(push ? 'R' : 'S');
  u64 advertised = PROTO_FEATURES & (o.whole_file ? ~(PF_RESUME | PF_DELTA) : ~u64(0));
  if (!push || !o.progress) advertised &= ~PF_PROGRESS_ACK;
  if (o.verbose < 2) advertised &= ~PF_STAGE_METRICS;
  if (o.list_only) advertised &= PF_CORE | PF_ZSTD | PF_LIST | PF_IO_CONTROL | PF_FILTERS | PF_MERGE_FILTERS | PF_CVS_FILTERS | PF_PRUNE_EMPTY | PF_RELATIVE | PF_FILES_FROM;
  else advertised &= ~PF_LIST;
  if (!o.filters.needs_extended()) advertised &= ~PF_FILTERS;
  if (!o.filters.has_merges()) advertised &= ~PF_MERGE_FILTERS;
  if (!o.filters.has_cvs() && !o.filters.has_merges()) advertised &= ~PF_CVS_FILTERS;
  if (!o.delete_after) advertised &= ~PF_DELETE_AFTER;
  if (!o.prune_empty) advertised &= ~PF_PRUNE_EMPTY;
  if (!o.relative) advertised &= ~PF_RELATIVE;
  if (!o.files_from_set) advertised &= ~PF_FILES_FROM;
  if (!o.hard_links) advertised &= ~PF_HLINK;
  if (!o.xattrs) advertised &= ~(PF_XATTRS | PF_XATTR_STREAM);
  if (!o.acls) advertised &= ~(PF_ACLS | PF_ACL_UUID);
  if (!o.executability || o.perms) advertised &= ~PF_EXECUTABILITY;
  if (!o.atimes) advertised &= ~PF_ATIMES;
  if (!o.crtimes) advertised &= ~PF_CRTIMES;
  if (!o.fileflags) advertised &= ~PF_FILEFLAGS;
  if (!o.ownership.requested()) advertised &= ~PF_CHOWN;
  if (!o.sparse) advertised &= ~PF_SPARSE;
  if (o.link_dest.empty()) advertised &= ~PF_LINK_DEST;
  if (!o.open_noatime) advertised &= ~PF_OPEN_NOATIME;
  if (!output_enabled()) advertised &= ~(PF_OUTPUT | PF_DIR_OUTPUT);
  if (wire_version >= 4) put_var(f, advertised);
  put_options(f);
  put_var(f, paths.size());
  for (auto& p : paths) put_str(f, p);
  c.start();
  c.send(std::move(f));
  u8 type;
  std::string payload;
  // Only handshake failures can fall back. No destination has been opened yet.
  auto disconnect = [&]() {
    c.finish();
    close(c.wfd);
    close(c.rfd);
    c.wait_peer();
    g_conn = nullptr;
  };
  auto fallback = [&](const std::string& reason, int strict_code) {
    disconnect();
    fallback_to_rsync(reason, strict_code);
  };
  auto mismatch = [&](u64 peer_version, const std::string& reason) -> int {
    // Retry once using the frozen N-1 layout, before either end opens a destination.
    if (wire_version == PROTO_VERSION && peer_version == PROTO_MIN_VERSION) {
      disconnect();
      return run_client(srcs, dest, PROTO_MIN_VERSION);
    }
    fallback(reason, RERR_PROTOCOL);
    return RERR_PROTOCOL;
  };
  for (;;) {
    if (!c.read_frame(type, payload, true)) {
      if (g_stop.load()) exit_signal();
      int st = c.wait_peer();
      int code = WIFEXITED(st) ? WEXITSTATUS(st) : 255;
      if (code == 127) fallback("remote xsync is not installed on " + rem.host, RERR_CMD_NOTFOUND);
      die(code == 255 ? 255 : RERR_STREAMIO, "connection unexpectedly closed (remote shell exited with code %d)", code);
    }
    if (type == F_MSG) {
      RBuf message(payload);
      int kind = message.byte();
      int code = (int)message.var();
      std::string text(message.rest());
      if (!message.bad && kind == 2 && code == RERR_PROTOCOL && text.rfind("protocol version mismatch:", 0) == 0) {
        size_t server = text.find("server ");
        u64 peer = server == std::string::npos ? 0 : strtoull(text.c_str() + server + 7, nullptr, 10);
        return mismatch(peer, text);
      }
      if (!message.bad && kind == 2 && code == RERR_UNSUPPORTED && text.rfind("peer does not support", 0) == 0)
        fallback(text, RERR_UNSUPPORTED);
      handle_msg(payload);
      continue;
    }
    if (type != F_HELLO || payload.size() < sizeof MAGIC - 1 || memcmp(payload.data(), MAGIC, sizeof MAGIC - 1) != 0)
      die(RERR_PROTOCOL, "protocol error: the remote side did not answer as xsync (is --rsync-path pointing at xsync?)");
    RBuf answer(payload);
    answer.raw(sizeof MAGIC - 1);
    u64 version = answer.var();
    if (answer.bad) die(RERR_PROTOCOL, "protocol error: malformed server hello");
    if (version != wire_version) return mismatch(version, "protocol version mismatch: client " + std::to_string(wire_version) +
                                                 ", server " + std::to_string(version));
    u64 features = version >= 4 ? answer.var() : LEGACY_V3_FEATURES;
    if (answer.bad || !answer.empty()) die(RERR_PROTOCOL, "protocol error: malformed server hello");
    o.peer_features = features & advertised;
    std::string missing = missing_feature(o.peer_features);
    if (!missing.empty()) fallback(missing, RERR_UNSUPPORTED);
    if (!o.list_only && (o.out_format_set || !o.log_file.empty()) && !structured_output())
      fallback("peer does not support structured file output", RERR_UNSUPPORTED);
    if (!o.list_only && (o.out_format_set || o.output_unchanged) && !(o.peer_features & PF_DIR_OUTPUT))
      fallback("peer does not support directory output metadata", RERR_UNSUPPORTED);
    if (!(o.peer_features & PF_ZSTD)) o.compress = false;
    if (!o.list_only && o.hard_links && !(o.peer_features & PF_HLINK))
      fallback("peer does not support hard-link preservation", RERR_UNSUPPORTED);
    break;
  }
  if (o.peer_features & PF_IO_CONTROL) {
    std::string config = new_frame(F_IO_CONFIG);
    put_var(config, o.bwlimit), put_var(config, o.timeout);
    c.configure(o.bwlimit, o.timeout, true);
    c.send(std::move(config));
  }
  if (o.peer_features & PF_XATTRS) c.send(new_frame(F_XATTR_CONFIG) + (char)o.xattrs);
  if (o.peer_features & PF_NATIVE_ACL) c.send(new_frame(F_ACL_CONFIG) + '\1');
  if (o.peer_features & PF_CHOWN) {
    std::string config = new_frame(F_CHOWN_CONFIG);
    put_str(config, push ? o.ownership.user : "");
    put_str(config, push ? o.ownership.group : "");
    c.send(std::move(config));
  }
  if (o.peer_features & PF_SPARSE) c.send(new_frame(F_SPARSE_CONFIG) + '\1');
  if (o.peer_features & PF_LINK_DEST) {
    std::string config = new_frame(F_LINKDEST_CONFIG);
    put_var(config, push ? o.link_dest.size() : 0);
    if (push) for (const auto& path : o.link_dest) put_str(config, path);
    c.send(std::move(config));
  }
  if (o.peer_features & PF_RELATIVE) c.send(new_frame(F_RELATIVE_CONFIG) + '\1');
  if (o.peer_features & PF_FILES_FROM) {
    std::string config = new_frame(F_FILES_CONFIG);
    config.push_back(list.remote ? '\2' : '\1');
    config.push_back((char)o.from0);
    put_str(config, list.remote ? list.path : "");
    c.send(std::move(config));
    if (!c.read_frame(type, payload)) conn_lost();
    if (type == F_MSG) handle_msg(payload);
    if (type != F_FILES_CONFIG || payload.size() != 1 || (u8)payload[0] > 1 ||
        (!list.remote && (payload[0] != (char)o.from0)) || (list.remote && o.from0 && !payload[0]))
      die(RERR_PROTOCOL, "protocol error: malformed files-from acknowledgement");
    o.file_names.clear();
    if (list.remote) receive_file_frames(c, payload[0] != 0, push ? &o.file_names : nullptr, push);
    else send_file_frames(c, o.files_from, true, o.from0, &o.file_names, !push);
    if (!push && !list.remote) o.file_requests = std::make_shared<const FileListRequests>(o);
    o.files_from_loaded = true;
  }
  if (o.peer_features & PF_FILTERS) {
    std::string config = new_frame(F_FILTER_CONFIG);
    if (o.peer_features & PF_CVS_FILTERS) config.push_back((char)o.cvs_exclude);
    auto rules = o.filters.to_strings(push, o.delete_excluded, !push && o.cvs_exclude, !push, push && !o.del);
    if (rules.size() > 10000) die(RERR_UNSUPPORTED, "too many filter rules for a remote transfer");
    put_var(config, rules.size());
    for (const auto& rule : rules) put_str(config, rule);
    if (config.size() > 1024 * 1024) die(RERR_UNSUPPORTED, "filter configuration exceeds 1 MiB");
    c.send(std::move(config));
  }
  if (o.peer_features & PF_DELETE_AFTER) c.send(new_frame(F_DELETE_CONFIG) + '\1');
  if (o.peer_features & PF_PRUNE_EMPTY) c.send(new_frame(F_PRUNE_CONFIG) + '\1');
  if (o.peer_features & PF_DIR_OUTPUT) {
    std::string config = new_frame(F_OUTPUT_CONFIG);
    config.push_back((char)o.output_attrs);
    config.push_back((char)o.output_unchanged);
    config.push_back((char)o.mkpath);
    config.push_back((char)o.delete_before);
    c.send(std::move(config));
  }
  if (!push && !o.list_only) init_ownership();
  output_start();
  if (!o.list_only && o.verbose > 0)
    out_line(o.prune_empty ? (push ? "sending file list" : "receiving file list") :
                            (push ? "sending incremental file list" : "receiving incremental file list"));
  if (!o.list_only) progress_start(default_jobs());
  int rc;
  if (!push) o.filters.prepare_pull();
  if (o.list_only) rc = receive_listing(c);
  else if (push) {
    Sender s(c, true);
    rc = s.run(srcs);
  } else {
    Receiver r(c, true);
    rc = r.run(dest);
  }
  if (c.wfd >= 0) close(c.wfd);
  int st = c.wait_peer();
  close(c.rfd);
  g_conn = nullptr;
  if (o.list_only && !rc && (!WIFEXITED(st) || WEXITSTATUS(st))) {
    rc = WIFEXITED(st) ? WEXITSTATUS(st) : RERR_STREAMIO;
    err_line(rc, "remote shell exited after listing with code %d", rc);
  }
  return rc;
}

int run_server() {
  Options& o = g_opt;
  static Conn c;
  c.rfd = 0, c.wfd = dup(1);
  // Anything that strays onto stdout would corrupt the protocol stream.
  int devnull = open("/dev/null", O_WRONLY);
  if (devnull >= 0) dup2(devnull, 1), close(devnull);
  g_conn = &c;
  u8 type;
  std::string payload;
  if (!c.read_frame(type, payload) || type != F_HELLO) return RERR_PROTOCOL;
  RBuf r(payload);
  std::string_view magic = r.raw(sizeof MAGIC - 1);
  u32 ver = (u32)r.var();
  char role = (char)r.byte();
  c.start();
  g_msg_sink = send_msg;
  const bool server_acls = o.acls;
  if (r.bad || magic != std::string_view(MAGIC, sizeof MAGIC - 1)) die(RERR_PROTOCOL, "protocol error: bad hello from client");
  if (ver < PROTO_MIN_VERSION || ver > PROTO_VERSION)
    die(RERR_PROTOCOL, "protocol version mismatch: client %u, server %u (supports %u and %u)",
        ver, PROTO_VERSION, PROTO_VERSION, PROTO_MIN_VERSION);
  u64 advertised = ver >= 4 ? r.var() : LEGACY_V3_FEATURES;
  // Like rsync, an explicitly configured helper may set its own input
  // delimiter. Ordinary SSH invocations do not forward the client's -0.
  const bool server_from0 = o.from0;
  const auto server_chmod = std::move(o.chmod_rules);
  auto server_ownership = std::move(o.ownership);
  const bool server_fileflags = o.fileflags;
  const bool server_sparse = o.sparse;
  auto server_link_dest = std::move(o.link_dest);
  const bool server_executability = o.executability && !o.perms;
  const bool server_atimes = o.atimes, server_crtimes = o.crtimes, server_noatime = o.open_noatime;
  o = Options();
  o.chmod_rules = server_chmod;
  o.ownership = std::move(server_ownership);
  o.sparse = server_sparse;
  o.link_dest = std::move(server_link_dest);
  o.from0 = server_from0;
  o.filters.set_from0(server_from0);
  o.am_server = true;
  o.wire_version = ver;
  o.peer_features = advertised & PROTO_FEATURES;
  if ((advertised & PF_LINK_DEST) && !(PROTO_FEATURES & PF_LINK_DEST)) die(RERR_UNSUPPORTED, "peer does not support --link-dest");
  if (!o.link_dest.empty() && !(o.peer_features & PF_LINK_DEST) && !(o.peer_features & PF_LIST))
    die(RERR_UNSUPPORTED, "explicit helper --link-dest requires negotiated snapshot bases");
  if ((advertised & PF_SPARSE) && !(PROTO_FEATURES & PF_SPARSE)) die(RERR_UNSUPPORTED, "peer does not support --sparse");
  if (server_sparse && !(o.peer_features & PF_SPARSE) && !(o.peer_features & PF_LIST))
    die(RERR_UNSUPPORTED, "explicit helper --sparse requires negotiated sparse writes");
  if ((advertised & PF_CHOWN) && !(PROTO_FEATURES & PF_CHOWN)) die(RERR_UNSUPPORTED, "peer does not support --chown");
  if (o.ownership.requested() && !(o.peer_features & PF_CHOWN) && !(o.peer_features & PF_LIST))
    die(RERR_UNSUPPORTED, "explicit helper --chown requires negotiated ownership overrides");
  if ((advertised & PF_FILEFLAGS) && !(PROTO_FEATURES & PF_FILEFLAGS))
    die(RERR_UNSUPPORTED, "peer does not support --fileflags");
  if (server_fileflags && !(o.peer_features & PF_FILEFLAGS)) die(RERR_UNSUPPORTED, "peer does not support --fileflags");
  if ((advertised & PF_CRTIMES) && !(PROTO_FEATURES & PF_CRTIMES))
    die(RERR_UNSUPPORTED, "peer does not support --crtimes");
  if (server_executability && !(o.peer_features & PF_EXECUTABILITY)) die(RERR_UNSUPPORTED, "peer does not support --executability");
  if (server_atimes && !(o.peer_features & PF_ATIMES)) die(RERR_UNSUPPORTED, "peer does not support --atimes");
  if (server_crtimes && !(o.peer_features & PF_CRTIMES)) die(RERR_UNSUPPORTED, "peer does not support --crtimes");
  if (server_noatime && !(o.peer_features & PF_OPEN_NOATIME)) die(RERR_UNSUPPORTED, "peer does not support --open-noatime");
  if ((advertised & PF_ACL_UUID) && !(advertised & PF_ACL_DARWIN))
    die(RERR_PROTOCOL, "protocol error: ACL UUID principals require Darwin ACL metadata");
  if ((advertised & PF_ACLS) == PF_ACLS) die(RERR_PROTOCOL, "protocol error: ambiguous ACL style");
  if ((server_acls || (advertised & PF_ACLS)) && !(o.peer_features & PF_NATIVE_ACL))
    die(RERR_UNSUPPORTED, "peer does not support the required ACL style");
  if ((o.peer_features & PF_XATTR_STREAM) && !(o.peer_features & PF_XATTRS))
    die(RERR_PROTOCOL, "protocol error: xattr streaming requires xattr metadata");
  o.list_only = o.peer_features & PF_LIST;
  o.hard_links = o.peer_features & PF_HLINK;
  o.acls = o.peer_features & PF_NATIVE_ACL;
  o.executability = o.peer_features & PF_EXECUTABILITY;
  o.atimes = (o.peer_features & PF_ATIMES) ? 1 : 0;
  o.crtimes = o.peer_features & PF_CRTIMES;
  o.fileflags = o.peer_features & PF_FILEFLAGS;
  o.open_noatime = o.peer_features & PF_OPEN_NOATIME;
  get_options(r);
  // rsync's remote receiver parses -A after the client's options and thereby
  // re-enables -p, including when the pushing client used --no-perms.
  if (o.acls && role == 'R') o.perms = true;
  if (o.filters.needs_extended())
    die(RERR_PROTOCOL, "protocol error: extended filters require a negotiated configuration");
  o.output_attrs = o.itemize;
  if (r.bad || (role != 'R' && role != 'S')) die(RERR_PROTOCOL, "protocol error: malformed hello options or role");
  if (o.list_only && role != 'S') die(RERR_PROTOCOL, "protocol error: listing requires sender role");
  if (o.acls && o.list_only) die(RERR_PROTOCOL, "protocol error: ACL metadata is not valid for listing");
  std::string missing = missing_feature(o.peer_features);
  if (!missing.empty()) die(RERR_UNSUPPORTED, "%s", missing.c_str());
  if (ver == 3 && o.compress && !(o.peer_features & PF_ZSTD))
    die(RERR_UNSUPPORTED, "peer does not support legacy protocol compression");
  if (!(o.peer_features & PF_ZSTD)) o.compress = false;
  init_ids();
  std::vector<std::string> paths;
  size_t n = (size_t)r.var();
  for (size_t i = 0; i < n && !r.bad; i++) paths.push_back(expand_remote_home(std::string(r.str())));
  if (r.bad || paths.empty() || !r.empty()) die(RERR_PROTOCOL, "protocol error: truncated or trailing hello");
  o.pushing = role == 'R';
  std::string f = new_frame(F_HELLO);
  f.append(MAGIC, sizeof MAGIC - 1);
  put_var(f, ver);
  if (ver >= 4) put_var(f, o.peer_features);
  if (structured_output()) g_output_sink = send_output;
  c.send(std::move(f));
  if (o.peer_features & PF_IO_CONTROL) {
    if (!c.read_frame(type, payload)) conn_lost();
    RBuf config(payload);
    u64 rate = config.var(), seconds = config.var();
    if (type != F_IO_CONFIG || config.bad || !config.empty() || rate > INT64_MAX || rate % 1024 || seconds > INT_MAX)
      die(RERR_PROTOCOL, "protocol error: malformed I/O configuration");
    o.bwlimit = rate;
    o.timeout = (u32)seconds;
    c.configure(rate, (u32)seconds, true);
  }
  if (o.peer_features & PF_XATTRS) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_XATTR_CONFIG || payload.size() != 1 || (payload[0] != 1 && payload[0] != 2) || o.list_only)
      die(RERR_PROTOCOL, "protocol error: malformed xattr configuration");
    o.xattrs = (u8)payload[0];
  }
  if (o.peer_features & PF_NATIVE_ACL) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_ACL_CONFIG || payload != std::string(1, '\1'))
      die(RERR_PROTOCOL, "protocol error: malformed ACL configuration");
  }
  if (o.peer_features & PF_CHOWN) {
    if (!c.read_frame(type, payload)) conn_lost();
    RBuf config(payload);
    std::string user(config.str()), group(config.str());
    if (type != F_CHOWN_CONFIG || config.bad || !config.empty() || payload.size() > 1024 * 1024 ||
        user.find_first_of(":,\0", 0, 3) != user.npos || group.find_first_of(",\0", 0, 2) != group.npos ||
        o.list_only || (role == 'R' ? user.empty() && group.empty() : !user.empty() || !group.empty()))
      die(RERR_PROTOCOL, "protocol error: malformed ownership configuration");
    if ((!user.empty() && o.ownership.user_set) || (!group.empty() && o.ownership.group_set))
      die(RERR_SYNTAX, "You can only specify a user/group-affecting --chown once");
    if (!user.empty()) o.ownership.user = std::move(user), o.ownership.user_set = true;
    if (!group.empty()) o.ownership.group = std::move(group), o.ownership.group_set = true;
  }
  if (o.peer_features & PF_SPARSE) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_SPARSE_CONFIG || payload != std::string(1, '\1') || o.list_only)
      die(RERR_PROTOCOL, "protocol error: malformed sparse configuration");
    o.sparse = role == 'R';
  }
  if (o.peer_features & PF_LINK_DEST) {
    if (!c.read_frame(type, payload)) conn_lost();
    RBuf config(payload);
    u64 count = config.var();
    if (type != F_LINKDEST_CONFIG || count > 20 || o.list_only || (role == 'R' ? count == 0 : count != 0))
      die(RERR_PROTOCOL, "protocol error: malformed link-dest configuration");
    for (u64 index = 0; index < count; ++index) {
      std::string path(config.str());
      if (path.find('\0') != std::string::npos) config.bad = true;
      o.link_dest.push_back(std::move(path));
    }
    if (config.bad || !config.empty() || o.link_dest.size() > 20)
      die(RERR_PROTOCOL, "protocol error: malformed link-dest directories");
  }
  if (o.peer_features & PF_RELATIVE) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_RELATIVE_CONFIG || payload != std::string(1, '\1'))
      die(RERR_PROTOCOL, "protocol error: malformed relative configuration");
    o.relative = true;
  }
  if (o.peer_features & PF_FILES_FROM) {
    if (!c.read_frame(type, payload)) conn_lost();
    RBuf config(payload);
    u8 mode = config.byte(), from0 = config.byte();
    std::string path(config.str());
    if (type != F_FILES_CONFIG || config.bad || !config.empty() || (mode != 1 && mode != 2) ||
        from0 > 1 || path.find('\0') != path.npos || (mode == 1 && !path.empty()) || (mode == 2 && path == "-"))
      die(RERR_PROTOCOL, "protocol error: malformed files-from configuration");
    if (paths.size() != 1) die(RERR_PROTOCOL, "protocol error: files-from requires one source root");
    o.files_from_set = true;
    if (role == 'S') o.dirs = true;
    // rsync transports a client list to a remote sender in NUL mode. The
    // native stream retains raw bytes; filter-file mode and record mode are
    // therefore kept separate here. Receiver helpers retain their own setting.
    if (mode == 1 && role == 'S') o.from0 = true;
    if (mode == 2) o.from0 |= from0 != 0;
    o.filters.set_from0(o.from0);
    bool record_from0 = mode == 2 ? o.from0 : from0 != 0;
    c.send(new_frame(F_FILES_CONFIG) + (char)record_from0);
    if (mode == 1) receive_file_frames(c, record_from0, role == 'S' ? &o.file_names : nullptr, role == 'S');
    else send_file_frames(c, path.empty() ? (role == 'S' ? "." : "") : expand_remote_home(path), false, record_from0,
                          role == 'S' ? &o.file_names : nullptr, role == 'R');
    o.files_from_loaded = true;
  }
  if (o.peer_features & PF_FILTERS) {
    if (!c.read_frame(type, payload)) conn_lost();
    RBuf config(payload);
    if (o.peer_features & PF_CVS_FILTERS) {
      u8 cvs = config.byte();
      if (cvs > 1) die(RERR_PROTOCOL, "protocol error: malformed CVS configuration");
      o.cvs_exclude = cvs;
    }
    u64 count = config.var();
    if (type != F_FILTER_CONFIG || config.bad || count > 10000 || !o.filters.empty())
      die(RERR_PROTOCOL, "protocol error: malformed filter configuration");
    std::string error;
    for (u64 i = 0; i < count && !config.bad; ++i) {
      auto rule = config.str();
      if (!config.bad && !o.filters.add_filter(rule, &error, false, o.peer_features & PF_CVS_FILTERS))
        die(RERR_PROTOCOL, "protocol error: bad configured filter: %s", error.c_str());
    }
    if (config.bad || !config.empty()) die(RERR_PROTOCOL, "protocol error: malformed filter configuration");
    if ((o.filters.has_merges() || o.cvs_exclude) && !(o.peer_features & PF_MERGE_FILTERS))
      die(RERR_PROTOCOL, "protocol error: unnegotiated per-directory filters");
    if (o.filters.has_merges() && !(o.peer_features & PF_CVS_FILTERS))
      die(RERR_PROTOCOL, "protocol error: unnegotiated CVS merge-file syntax");
    if (o.cvs_exclude && role == 'S' && !o.filters.add_cvs_option(&error))
      die(RERR_PROTOCOL, "protocol error: bad CVS configuration: %s", error.c_str());
  }
  if (o.peer_features & PF_DELETE_AFTER) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_DELETE_CONFIG || payload != std::string(1, '\1') || !o.del)
      die(RERR_PROTOCOL, "protocol error: malformed delete-after configuration");
    o.delete_after = true;
  }
  if (o.peer_features & PF_PRUNE_EMPTY) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_PRUNE_CONFIG || payload != std::string(1, '\1'))
      die(RERR_PROTOCOL, "protocol error: malformed prune-empty configuration");
    o.prune_empty = true;
  }
  if (o.peer_features & PF_DIR_OUTPUT) {
    if (!c.read_frame(type, payload)) conn_lost();
    if (type != F_OUTPUT_CONFIG || payload.size() != 4 ||
        std::any_of(payload.begin(), payload.end(), [](unsigned char value) { return value > 1; }))
      die(RERR_PROTOCOL, "protocol error: malformed output configuration");
    o.output_attrs = payload[0];
    o.output_unchanged = payload[1];
    o.mkpath = payload[2];
    o.delete_before = payload[3];
  }
  if (role == 'R' && !o.list_only) {
    if (o.ownership.user_set) o.owner = true;
    if (o.ownership.group_set) o.group = true;
    init_ownership();
  }
  int rc;
  if (o.list_only) {
    u64 count = 0;
    rc = run_listing(expand_remote_sources(paths), [&](const ListingEntry& entry) {
      std::string f = new_frame(F_LIST_ENTRY);
      put_str(f, entry.path);
      f.push_back((char)entry.attrs.type);
      put_var(f, entry.attrs.mode), put_var(f, (u64)entry.attrs.size);
      put_svar(f, entry.attrs.mtime), put_str(f, entry.target);
      if (o.peer_features & (PF_CVS_FILTERS | PF_RELATIVE | PF_FILES_FROM)) put_str(f, entry.source);
      c.send(std::move(f), true);
      ++count;
    });
    std::string f = new_frame(F_LIST_END);
    put_var(f, (u64)rc), put_var(f, count);
    c.send(std::move(f));
    c.finish();
  } else if (role == 'R') {
    Receiver rv(c, false);
    rc = rv.run(paths[0]);
  } else {
    Sender s(c, false);
    rc = s.run(expand_remote_sources(paths));
  }
  return rc;
}
