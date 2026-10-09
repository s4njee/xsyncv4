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
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include <cerrno>
#include <algorithm>
#include <cstdlib>
#include <memory>
#include <unordered_map>
#include <unordered_set>

#include <zstd.h>

#define XXH_INLINE_ALL
#include <xxhash.h>

#include "engine.h"
#include "progress.h"
#include "fallback.h"
#include "transport.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

namespace {

enum : u8 { F_HELLO = 1, F_DIR, F_NEED, F_DATA, F_LIST_END, F_DATA_END, F_DONE, F_MSG, F_IDMAP, F_DEST };
enum : u8 { DF_ATTRS = 1, DF_SINGLE = 2, DF_NODELETE = 4, DF_ZSTD = 8 };
enum : u8 { R_WHOLE = 1, R_CHUNK = 2, R_FAIL = 4, R_END = 8 };
constexpr size_t HDR = 5;                  // u32 payload length + u8 type
constexpr size_t BLOCK_TARGET = 1 << 20;   // raw bytes per DATA frame
constexpr size_t SMALL_MAX = 512 << 10;    // files up to this size are packed into shared blocks
constexpr size_t DATA_PREFIX = HDR + 1 + 8;
const char MAGIC[] = "XSYNC\x01";

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

void put_file_attrs(std::string& s, const Entry& e) {
  put_var(s, e.mode), put_var(s, e.uid), put_var(s, e.gid);
  put_svar(s, e.mtime), put_var(s, e.mtime_ns);
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

std::string new_frame(u8 type) {
  std::string f(HDR, '\0');
  f[4] = (char)type;
  return f;
}

// ---------------------------------------------------------------- connection

struct Conn {
  int rfd = -1, wfd = -1;
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

  void start() {
    wt = std::thread([this] { writer(); });
  }
  // Queue a frame built with new_frame(); `bounded` applies back-pressure to bulk producers.
  void send(std::string&& f, bool bounded = false) {
    u32 len = (u32)(f.size() - HDR);
    memcpy(f.data(), &len, 4);
    std::unique_lock<std::mutex> lk(mu);
    if (bounded) cv_space.wait(lk, [&] { return qbytes < MAX_Q || closing; });
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
    auto out = [&](const char* p, size_t n) {
      if (!write_all(wfd, p, n)) {
        // The peer may have sent a fatal filesystem error before closing. Let
        // the reader consume it instead of racing it with an EPIPE exit here.
        std::lock_guard<std::mutex> lock(mu);
        closing = true;
        q.clear();
        qbytes = 0;
        cv_space.notify_all();
        return false;
      }
      g_stats.wire_sent.fetch_add(n, std::memory_order_relaxed);
      return true;
    };
    for (;;) {
      {
        std::unique_lock<std::mutex> lk(mu);
        cv.wait(lk, [&] { return !q.empty() || closing; });
        if (q.empty()) break;
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
      if (rpos < rlen) {
        size_t k = std::min(n, rlen - rpos);
        memcpy(dst, rb.data() + rpos, k);
        rpos += k, dst += k, n -= k;
        continue;
      }
      ssize_t k = n >= rb.size() ? read(rfd, dst, n) : read(rfd, rb.data(), rb.size());
      if (g_stop.load()) return false;
      if (k < 0 && errno == EINTR) continue;
      if (k <= 0) return false;
      g_stats.wire_recv.fetch_add((u64)k, std::memory_order_relaxed);
      if (n >= rb.size()) dst += k, n -= (size_t)k;
      else rpos = 0, rlen = (size_t)k;
    }
    return true;
  }
  // Returns false on EOF at a frame boundary or on a broken stream.
  bool read_frame(u8& type, std::string& payload, bool hello = false) {
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
    payload.resize(len);
    return read_exact(payload.data(), len);
  }
};

Conn* g_conn = nullptr;

void send_msg(int kind, int code, std::string_view s) {
  std::string f = new_frame(F_MSG);
  f.push_back((char)kind);
  put_var(f, (u64)code);
  f.append(s);
  g_conn->send(std::move(f));
  if (kind == 2) g_conn->finish();  // fatal: make sure it reaches the client before we exit
}

[[noreturn]] void conn_lost() {
  // A broken connection cannot carry the fatal message back to the peer.
  g_msg_sink = nullptr;
  if (g_stop.load()) exit_signal();
  die(RERR_STREAMIO, "connection unexpectedly closed");
}

void handle_msg(std::string_view payload) {
  RBuf r(payload);
  int kind = r.byte();
  int code = (int)r.var();
  std::string text(r.rest());
  if (kind == 0) ui_write(false, text + "\n");
  else if (kind == 1) err_line(code, "%s", text.c_str());
  else die(code ? code : RERR_STREAMIO, "%s", text.c_str());
}

// Optionally compress `raw` into `f` (appending). Returns true if compressed.
bool pack(std::string& f, std::string_view raw, Worker& w) {
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

std::string_view unpack(std::string_view in, bool compressed, std::string& scratch, Worker& w) {
  if (!compressed) return in;
  if (!(g_opt.peer_features & PF_ZSTD)) die(RERR_PROTOCOL, "compressed data without negotiated zstd support");
  RBuf r(in);
  size_t raw = (size_t)r.var();
  std::string_view z = r.rest();
  if (r.bad || raw > (1u << 30)) die(RERR_PROTOCOL, "protocol error: bad compressed frame");
  if (!w.zd) w.zd = ZSTD_createDCtx();
  scratch.resize(raw);
  size_t n = ZSTD_decompressDCtx((ZSTD_DCtx*)w.zd, scratch.data(), raw, z.data(), z.size());
  if (ZSTD_isError(n) || n != raw) die(RERR_STREAMIO, "decompression failed: corrupt data stream");
  return scratch;
}

// ---------------------------------------------------------------- options on the wire

std::string missing_feature(u64 features) {
  if (!(features & PF_CORE)) return "peer does not support the required core transfer features";
  if (g_opt.safe_links && !(features & PF_SAFE_LINKS)) return "peer does not support --safe-links";
  if (!g_opt.numeric_ids && (g_opt.owner || g_opt.group) && !(features & PF_IDMAP))
    return "peer does not support user/group name mapping (use --numeric-ids)";
  return {};
}

void put_options(std::string& f) {
  const Options& o = g_opt;
#define X(n) f.push_back((char)o.n);
  WIRE_V3_BOOL_OPTS(X)
#undef X
#define X(n) put_svar(f, o.n);
  WIRE_V3_INT_OPTS(X)
#undef X
  auto rules = o.filters.to_strings();
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
    if (!o.filters.add_filter(rule, &err)) die(RERR_PROTOCOL, "bad filter rule from client: %s", err.c_str());
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
    if (o.numeric_ids || (!o.owner && !o.group)) return;
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
      if (o.owner) one(0, e.uid);
      if (o.group) one(1, e.gid);
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

enum { K_WALK = 1, K_READ = 2, K_GEN = 3, K_DATA = 4 };

struct SDir {
  std::string src_path, rel;
  std::vector<std::string> src_paths;
  DirList list;
  Entry attrs;
  u8 flags = 0;
  u32 id = 0;
  bool prelisted = false;
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
  std::atomic<int> walks{0};
  u64 dirs_sent = 0, needs_recv = 0;  // guarded by the pool lock
  std::atomic<u64> dirs_sent_a{0};
  bool client;  // we are the client: keep progress counters
  std::mutex done_mu;
  std::condition_variable done_cv;
  bool got_done = false;

  Sender(Conn& conn, bool is_client) : c(conn), client(is_client) {}

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
      prune_source(d->list, d->rel, d->attrs.dev, w, nullptr, guard, d->src_path);
    }
    DirList& l = d->list;
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
    put_var(body, d->attrs.mode);
    put_svar(body, d->attrs.mtime);
    put_var(body, d->attrs.mtime_ns);
    put_var(body, d->attrs.uid);
    put_var(body, d->attrs.gid);
    put_var(body, l.e.size());
    u64 nf = 0, nd = 0, nl = 0, ns = 0, nb = 0;
    for (size_t i = 0; i < l.e.size(); i++) {
      const Entry& e = l.e[i];
      put_str(body, l.name_sv(e));
      body.push_back((char)e.type);
      put_var(body, e.mode);
      put_svar(body, e.mtime);
      put_var(body, e.mtime_ns);
      if (o.owner) put_var(body, e.uid);
      if (o.group) put_var(body, e.gid);
      switch (e.type) {
        case T_REG:
          put_var(body, (u64)e.size);
          if (o.checksum) body.append((const char*)&l.sums[2 * i], 16);
          nf++, nb += (u64)e.size;
          break;
        case T_DIR: put_var(body, e.rdev == 1), nd++; break;
        case T_LNK: put_str(body, l.link(e)), nl++; break;
        case T_CHR:
        case T_BLK: put_var(body, e.rdev); [[fallthrough]];
        default: ns++;
      }
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
    if (!o.recursive) return true;
    for (size_t i = 0; i < l.e.size(); i++) {
      const Entry& e = l.e[i];
      if (e.type != T_DIR || e.rdev == 1) continue;
      SDir* ch = new SDir;
      std::string_view nm = l.name_sv(e);
      ch->src_path = d->src_paths.empty() ? path_join(d->src_path, nm) : d->src_paths[i];
      ch->rel = rel_join(d->rel, nm);
      ch->attrs = e;
      ch->flags = DF_ATTRS;
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
    size_t n = (size_t)r.var();
    SDir* d;
    {
      std::lock_guard<std::mutex> lk(smu);
      d = id < dirs.size() ? dirs[id] : nullptr;
      if (d) dirs[id] = nullptr;
    }
    if (!d || r.bad) die(RERR_PROTOCOL, "protocol error: bad NEED frame");
    if (n == 0) {
      if (d->pending.fetch_sub(1) == 1) delete d;
    } else {
      std::vector<u32> idx(n);
      u32 prev = 0;
      u64 bytes = 0;
      for (size_t i = 0; i < n; i++) {
        prev += (u32)r.var();
        if (r.bad || prev >= d->list.e.size()) die(RERR_PROTOCOL, "protocol error: bad NEED index");
        idx[i] = prev;
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
    c.send(std::move(f), true);
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
    for (u32 attempt = 0; attempt < 2; attempt++) {
      int in = open(w.p2.c_str(), O_RDONLY | O_CLOEXEC | (o.copy_links || !d.src_paths.empty() ? 0 : O_NOFOLLOW));
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
      Entry fresh = source_snapshot(scanned, before);
      if (client) {
        if (fresh.size >= planned) g_stats.xfer_bytes_total.fetch_add((u64)(fresh.size - planned));
        else g_stats.xfer_bytes_total.fetch_sub((u64)(planned - fresh.size));
        slot_begin(w.id, d.rel, d.list.name_sv(scanned), fresh.size);
      }
      planned = fresh.size;
      bool ok = true;
      auto read_some = [&](char* dst, size_t want) {
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
      i64 off = 0;
      size_t checkpoint = w.block.size();
      if (small) {
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
          put_var(w.block, attempt), put_var(w.block, (u64)off), put_var(w.block, (u64)fresh.size);
          put_str(w.block, {w.buf.data(), want});
          off += (i64)want;
          if (client) slot_add(w.id, (i64)want);
          flush_block(w);
        }
      }
      bool stable = off == fresh.size && source_unchanged(in, w.p2, before);
      close(in);
      bool retry = !stable && attempt == 0 && !g_stop.load();
      if (!stable && !retry && !g_stop.load())
        err_line(RERR_PARTIAL, "file changed during transfer after retry: \"%s\"", w.p2.c_str());
      if (small) {
        w.block.resize(checkpoint);
        if (stable && ok) {
          head(R_WHOLE);
          put_file_attrs(w.block, fresh);
          put_str(w.block, {w.buf.data(), (size_t)off});
        } else if (!retry) head(R_FAIL);
      } else {
        head(R_END);
        put_var(w.block, attempt), put_var(w.block, (u64)off);
        w.block.push_back(retry ? 1 : stable && ok ? 0 : 2);
        put_file_attrs(w.block, fresh);
        flush_block(w);
      }
      if (retry) continue;
      if (client) {
        if (stable && ok) g_stats.xfer_bytes.fetch_add((u64)fresh.size), g_stats.xfer_files.fetch_add(1);
        else g_stats.xfer_files_total.fetch_sub(1), g_stats.xfer_bytes_total.fetch_sub((u64)planned);
        slot_end(w.id);
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
        case F_MSG: handle_msg(payload); break;
        case F_DONE: {
          RBuf r(payload);
          int code = (int)r.var();
          if (client) {
            if (code) err_line(code, "errors were reported by the receiver");
            g_stats.created_files = r.var(), g_stats.created_dirs = r.var(), g_stats.created_links = r.var();
            g_stats.created_specials = r.var(), g_stats.deleted = r.var();
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
    root->attrs = rl.attrs;
    root->flags = (rl.has_attrs ? DF_ATTRS : DF_NODELETE) | (rl.single ? DF_SINGLE : 0);
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
};

struct BigFile {
  OutFile f;
  std::mutex mu;
  Entry attrs;
  i64 received = 0, expected = -1;
  int status = -1;
  bool ok = true;
  bool opened = false;
  bool finished = false;
};

struct Receiver {
  Conn& c;
  Pool pool;
  IdMaps ids;
  std::string dest;
  std::mutex dmu;
  std::vector<RDir*> dirs;
  std::mutex bmu;
  std::unordered_map<u64, std::shared_ptr<BigFile>> big;
  bool data_end = false;  // guarded by the pool lock
  std::atomic<bool> allow_disconnect{false};
  std::atomic<int> gens{0};
  std::atomic<bool> list_end{false};
  int sender_code = 0;
  bool client;

  Receiver(Conn& conn, bool is_client) : c(conn), client(is_client) {}

  RDir* dir(u32 id) {
    std::lock_guard<std::mutex> lk(dmu);
    return id < dirs.size() ? dirs[id] : nullptr;
  }

  void done_one(RDir& d) {
    if (d.w.pending.fetch_sub(1) == 1) finish_dir(d.w);
  }

  void gen(RDir* d, std::string& payload, Worker& t) {
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
    w.attrs.uid = (u32)r.var();
    w.attrs.gid = (u32)r.var();
    size_t n = (size_t)r.var();
    if (r.bad || n > (1u << 28)) die(RERR_PROTOCOL, "protocol error: bad DIR frame");
    DirList& l = w.src;
    l.e.resize(n);
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
      if (o.owner) e.uid = (u32)r.var();
      if (o.group) e.gid = (u32)r.var();
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
        case T_DIR: e.rdev = (u32)r.var(); break;
        case T_CHR:
        case T_BLK: e.rdev = (u32)r.var(); break;
        default: break;
      }
    }
    if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated DIR frame");
    if ((o.owner || o.group) && !o.numeric_ids) {
      std::lock_guard<std::mutex> lk(ids.mu);
      ids.map(w.attrs);
      for (Entry& e : l.e) ids.map(e);
    }

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
      w.attrs.mode = pe.mode;  // final mode as decided by the parent's generator
      w.has_attrs = true;
      w.created = pe.flags & EF_CREATED;
      w.mode_ok = pe.flags & EF_MODE_OK;
      w.time_ok = pe.flags & EF_TIME_OK;
    }
    w.pending.store(1);
    std::string f = new_frame(F_NEED);
    put_var(f, d->id);
    if (go) {
      generate(w, t);
      if (o.dry_run) {
        for (u32 i : w.need) {
          g_stats.xfer_bytes.fetch_add((u64)l.e[i].size, std::memory_order_relaxed);
          note_transferred(w, i, l.e[i].size, t);
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
    for (u32 i : w.need) put_var(f, i - prev), prev = i;
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

  void get_file_attrs(RBuf& r, Entry& attrs) {
    u32 mode = (u32)r.var() & 07777;
    attrs.uid = (u32)r.var(), attrs.gid = (u32)r.var();
    attrs.mtime = r.svar(), attrs.mtime_ns = (u32)r.var();
    if (g_opt.perms) attrs.mode = mode;
    if ((g_opt.owner || g_opt.group) && !g_opt.numeric_ids) {
      std::lock_guard<std::mutex> lock(ids.mu);
      ids.map(attrs);
    }
  }

  void data(std::string& payload, Worker& t) {
    if (payload.size() < 9) die(RERR_PROTOCOL, "protocol error: short DATA frame");
    u64 want;
    memcpy(&want, payload.data() + 1, 8);
    static thread_local std::string scratch;
    std::string_view raw = unpack(std::string_view(payload).substr(9), payload[0] & 1, scratch, t);
    if (XXH3_64bits(raw.data(), raw.size()) != want) die(RERR_STREAMIO, "data corruption detected in transfer stream");
    RBuf r(raw);
    RDir* d = nullptr;
    while (!r.empty()) {
      u32 id = (u32)r.var(), idx = (u32)r.var();
      u8 kind = r.byte();
      if (!d || d->id != id) d = dir(id);
      if (r.bad || !d || idx >= d->w.src.e.size()) die(RERR_PROTOCOL, "protocol error: bad DATA record");
      DirWork& w = d->w;
      const Entry& s = w.src.e[idx];
      if (!d->gen_done || s.type != T_REG || !std::binary_search(w.need.begin(), w.need.end(), idx))
        die(RERR_PROTOCOL, "protocol error: unrequested file data");
      if (kind == R_FAIL) {
        g_stats.xfer_files_total.fetch_sub(1, std::memory_order_relaxed);
        g_stats.xfer_bytes_total.fetch_sub((u64)s.size, std::memory_order_relaxed);
        done_one(*d);
      } else if (kind == R_WHOLE) {
        Entry attrs = s;
        get_file_attrs(r, attrs);
        std::string_view bytes = r.str();
        if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated DATA record");
        slot_begin(t.id, w.rel, w.src.name_sv(s), (i64)bytes.size());
        OutFile file;
        bool ok = out_open(file, w, idx, t);
        if (ok) {
          file.size = (i64)bytes.size();
          ok = write_all(file.fd, bytes.data(), bytes.size());
          if (!ok) file_io_error(errno, file.path.c_str(), "write");
          ok = out_finish(file, w, idx, t, ok, &attrs) && ok;
        }
        if (ok) {
          g_stats.xfer_bytes.fetch_add(bytes.size());
          if ((i64)bytes.size() >= s.size) g_stats.xfer_bytes_total.fetch_add(bytes.size() - (u64)s.size);
          else g_stats.xfer_bytes_total.fetch_sub((u64)s.size - bytes.size());
          note_transferred(w, idx, (i64)bytes.size(), t);
        } else {
          g_stats.xfer_files_total.fetch_sub(1);
          g_stats.xfer_bytes_total.fetch_sub((u64)s.size);
        }
        slot_end(t.id);
        done_one(*d);
      } else if (kind == R_CHUNK || kind == R_END) {
        u32 attempt = (u32)r.var();
        if (attempt > 1) die(RERR_PROTOCOL, "protocol error: invalid retry attempt");
        i64 off = 0, total;
        int status = -1;
        Entry attrs = s;
        std::string_view bytes;
        if (kind == R_CHUNK) {
          off = (i64)r.var(), total = (i64)r.var();
          bytes = r.str();
          if (off < 0 || total < 0 || bytes.size() > (u64)total || off > total - (i64)bytes.size())
            die(RERR_PROTOCOL, "protocol error: bad chunk");
        } else {
          total = (i64)r.var();
          status = r.byte();
          get_file_attrs(r, attrs);
          if (total < 0 || status > 2) die(RERR_PROTOCOL, "protocol error: bad file completion");
        }
        if (r.bad) die(RERR_PROTOCOL, "protocol error: truncated file record");
        u64 key = ((u64)id << 33) | ((u64)idx << 1) | attempt;
        std::shared_ptr<BigFile> b;
        {
          std::lock_guard<std::mutex> lk(bmu);
          auto& item = big[key];
          if (!item) item = std::make_shared<BigFile>();
          b = item;
        }
        std::unique_lock<std::mutex> file_lock(b->mu);
        if (b->finished) die(RERR_PROTOCOL, "protocol error: data after file completion");
        if (!b->opened) {
          b->opened = true;
          b->attrs = s;
          b->ok = out_open(b->f, w, idx, t);
        }
        if (kind == R_END) {
          if (b->status != -1) die(RERR_PROTOCOL, "protocol error: duplicate file completion");
          b->status = status, b->expected = total, b->attrs = attrs;
        } else {
          slot_begin(t.id, w.rel, w.src.name_sv(s), total);
          slot_add(t.id, off + (i64)bytes.size());
          if (b->ok) {
            const char* p = bytes.data();
            size_t left = bytes.size();
            i64 at = off;
            while (left) {
              ssize_t k = pwrite(b->f.fd, p, left, at);
              if (k < 0 && errno == EINTR) continue;
              if (k <= 0) {
                file_io_error(errno, b->f.path.c_str(), "write");
                b->ok = false;
                break;
              }
              p += k, left -= (size_t)k, at += k;
            }
          }
          b->received += (i64)bytes.size();
        }
        if (b->status >= 0 && b->received == b->expected) {
          b->finished = true;
          b->f.size = b->expected;
          bool ok = false;
          if (b->f.fd >= 0) {
            if (b->status == 0 && b->ok) ok = out_finish(b->f, w, idx, t, true, &b->attrs);
            else out_abort(b->f, b->status == 2 && g_opt.partial);
          }
          {
            std::lock_guard<std::mutex> lk(bmu);
            big.erase(key);
          }
          if (b->status != 1) {
            if (ok) {
              g_stats.xfer_bytes.fetch_add((u64)b->expected);
              if (b->expected >= s.size) g_stats.xfer_bytes_total.fetch_add((u64)(b->expected - s.size));
              else g_stats.xfer_bytes_total.fetch_sub((u64)(s.size - b->expected));
              note_transferred(w, idx, b->expected, t);
            } else {
              g_stats.xfer_files_total.fetch_sub(1);
              g_stats.xfer_bytes_total.fetch_sub((u64)s.size);
            }
            done_one(*d);
          }
          slot_end(t.id);
        }
      } else {
        die(RERR_PROTOCOL, "protocol error: unknown DATA record");
      }
    }
  }

  void on_dir(std::string& payload) {
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
        if (!p->gen_done) {
          p->waiters.push_back(std::move(t));
          return;
        }
      }
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
      if (ended) die(RERR_PROTOCOL, "protocol error: frame after DATA_END");
      switch (type) {
        case F_DIR: on_dir(payload); break;
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
          list_end.store(true);
          if (gens.load() == 0) g_stats.scan_done.store(true);
          break;
        case F_DATA_END: {
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
      if (t.kind == K_GEN) gen((RDir*)t.ptr, t.s, w);
      else data(t.s, w);
    });
    wait_pool(pool);
    if (g_stop.load()) exit_signal();
    pool.join();
    g_stats.scan_done.store(true);
    if (sender_code) g_source_io_error.store(true);
    if (client && sender_code) err_line(sender_code, "errors were reported by the sender");
    finalize_tree();
    if (g_stop.load()) exit_signal();
    allow_disconnect.store(true);
    std::string f = new_frame(F_DONE);
    put_var(f, (u64)g_exit_code.load());
    put_var(f, g_stats.created_files), put_var(f, g_stats.created_dirs), put_var(f, g_stats.created_links);
    put_var(f, g_stats.created_specials), put_var(f, g_stats.deleted);
    c.send(std::move(f));
    c.finish();
    rt.join();
    return g_exit_code.load();
  }
};

// ---------------------------------------------------------------- client / server glue

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

struct Remote {
  std::string user, host, path;
};

Remote split_remote(const std::string& a) {
  Remote r;
  size_t colon = a.find(':');
  std::string hp = a.substr(0, colon);
  r.path = a.substr(colon + 1);
  size_t at = hp.rfind('@');
  if (at != std::string::npos) r.user = hp.substr(0, at), r.host = hp.substr(at + 1);
  else r.host = hp;
  return r;
}

bool is_remote_arg(const std::string& a) {
  size_t colon = a.find(':');
  if (colon == std::string::npos) return false;
  size_t slash = a.find('/');
  return slash == std::string::npos || colon < slash;
}

}  // namespace

int run_client(const std::vector<std::string>& srcs, const std::string& dest, u32 wire_version) {
  Options& o = g_opt;
  o.wire_version = wire_version;
  bool push = is_remote_arg(dest);
  Remote rem;
  std::vector<std::string> paths;  // paths on the remote side
  if (push) {
    rem = split_remote(dest);
    paths.push_back(rem.path);
  } else {
    for (const std::string& s : srcs) {
      if (!is_remote_arg(s)) die(RERR_SYNTAX, "all sources must be on the same remote host");
      Remote r = split_remote(s);
      if (paths.empty()) rem = r;
      else if (!r.host.empty() && (r.host != rem.host || r.user != rem.user)) die(RERR_SYNTAX, "all source args must come from the same machine.");
      paths.push_back(r.path);
    }
  }
  std::vector<std::string> cmd = split_shell_words(remote_shell_command());
  if (cmd.empty()) die(RERR_SYNTAX, "empty remote shell command");
  if (!rem.user.empty()) cmd.push_back("-l"), cmd.push_back(rem.user);
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
  g_conn = &c;
  o.pushing = push;
  // Hello: magic, version, the role the server plays, options, paths.
  std::string f = new_frame(F_HELLO);
  f.append(MAGIC, sizeof MAGIC - 1);
  put_var(f, wire_version);
  f.push_back(push ? 'R' : 'S');
  if (wire_version >= 4) put_var(f, PROTO_FEATURES);
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
    int status = 0;
    while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {
      if (g_stop.load()) exit_signal();
    }
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
      int st = 0;
      waitpid(pid, &st, 0);
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
    o.peer_features = features & PROTO_FEATURES;
    std::string missing = missing_feature(o.peer_features);
    if (!missing.empty()) fallback(missing, RERR_UNSUPPORTED);
    if (!(o.peer_features & PF_ZSTD)) o.compress = false;
    break;
  }
  if (o.verbose > 0) out_line(push ? "sending incremental file list" : "receiving incremental file list");
  progress_start(default_jobs());
  int rc;
  if (push) {
    Sender s(c, true);
    rc = s.run(srcs);
  } else {
    Receiver r(c, true);
    rc = r.run(dest);
  }
  close(c.wfd);
  int st = 0;
  waitpid(pid, &st, 0);
  close(c.rfd);
  g_conn = nullptr;
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
  if (r.bad || magic != std::string_view(MAGIC, sizeof MAGIC - 1)) die(RERR_PROTOCOL, "protocol error: bad hello from client");
  if (ver < PROTO_MIN_VERSION || ver > PROTO_VERSION)
    die(RERR_PROTOCOL, "protocol version mismatch: client %u, server %u (supports %u and %u)",
        ver, PROTO_VERSION, PROTO_VERSION, PROTO_MIN_VERSION);
  u64 advertised = ver >= 4 ? r.var() : LEGACY_V3_FEATURES;
  o = Options();
  o.am_server = true;
  o.wire_version = ver;
  o.peer_features = advertised & PROTO_FEATURES;
  get_options(r);
  if (r.bad || (role != 'R' && role != 'S')) die(RERR_PROTOCOL, "protocol error: malformed hello options or role");
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
  c.send(std::move(f));
  int rc;
  if (role == 'R') {
    Receiver rv(c, false);
    rc = rv.run(paths[0]);
  } else {
    Sender s(c, false);
    rc = s.run(expand_remote_sources(paths));
  }
  return rc;
}
