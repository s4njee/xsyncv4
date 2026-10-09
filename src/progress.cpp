#include "progress.h"

#include <sys/ioctl.h>
#include <unistd.h>

#include <algorithm>
#include <cstdlib>
#include <mutex>

Slot g_slots[MAX_WORKERS];
bool g_progress_on = false;

namespace {
std::mutex ui_mu;
bool tty = false, color = false, live = false;
int drawn = 0;  // lines currently occupied by the live region
int nworkers = 0;
u64 t_start = 0, t_last = 0, t_plain = 0;
u64 last_bytes = 0, last_files = 0;
double rate_b = 0, rate_f = 0;
unsigned spin = 0;

constexpr int MAX_ROWS = 4;
int row_w[MAX_ROWS];

struct Snap {
  bool active = false;
  i64 size = 0, done = 0;
  std::string name;
};

void raw(std::string_view s) {
  while (!s.empty()) {
    ssize_t n = write(2, s.data(), s.size());
    if (n <= 0) break;
    s.remove_prefix((size_t)n);
  }
}

void erase(std::string& out) {
  if (!drawn) return;
  out += '\r';
  if (drawn > 1) out += "\x1b[" + std::to_string(drawn - 1) + "A";
  out += "\x1b[J";
  drawn = 0;
}

int term_cols() {
  winsize ws{};
  if (ioctl(2, TIOCGWINSZ, &ws) == 0 && ws.ws_col > 20) return ws.ws_col;
  return 80;
}

const char* C(const char* code) { return color ? code : ""; }

// Display width of UTF-8 text, counting every non-ASCII code point as two columns (safe
// over-estimate so rows never wrap).
int width(std::string_view s) {
  int w = 0;
  for (unsigned char c : s)
    if (c < 0x80) w++;
    else if (c >= 0xC0) w += 2;
  return w;
}

// Keep the tail of a path that fits in `w` columns.
std::string fit_left(std::string_view s, int w) {
  if (width(s) <= w) return std::string(s) + std::string((size_t)(w - width(s)), ' ');
  size_t i = s.size();
  int used = 1;
  while (i > 0) {
    size_t j = i - 1;
    while (j > 0 && ((unsigned char)s[j] & 0xC0) == 0x80) j--;
    int cw = (unsigned char)s[j] < 0x80 ? 1 : 2;
    if (used + cw > w) break;
    used += cw;
    i = j;
  }
  return "…" + std::string(s.substr(i)) + std::string((size_t)(w - used), ' ');
}

std::string bar(double frac, int w) {
  frac = std::clamp(frac, 0.0, 1.0);
  int full = (int)(frac * w);
  std::string b = C("\x1b[36m");
  for (int i = 0; i < full; i++) b += "━";
  if (full < w) {
    b += (frac * w - full >= 0.5) ? "╸" : std::string(C("\x1b[2;37m")) + "━";
    b += C("\x1b[0;2;37m");
    for (int i = full + 1; i < w; i++) b += "━";
  }
  b += C("\x1b[0m");
  return b;
}

std::string fmt_eta(double sec) {
  char b[32];
  u64 s = (u64)(sec + 0.5);
  if (s >= 3600) snprintf(b, sizeof b, "%llu:%02llu:%02llu", (unsigned long long)(s / 3600), (unsigned long long)(s / 60 % 60), (unsigned long long)(s % 60));
  else snprintf(b, sizeof b, "%llu:%02llu", (unsigned long long)(s / 60), (unsigned long long)(s % 60));
  return b;
}

Snap sample(int w) {
  Snap sn;
  Slot& s = g_slots[w];
  for (int tries = 0; tries < 4; tries++) {
    u32 a = s.seq.load(std::memory_order_acquire);
    if (a & 1) continue;
    sn.active = s.active.load(std::memory_order_relaxed);
    sn.size = s.size;
    sn.done = s.done.load(std::memory_order_relaxed);
    sn.name.assign(s.name, std::min<size_t>(s.len, sizeof s.name));
    if (s.seq.load(std::memory_order_acquire) == a) return sn;
  }
  sn.active = false;
  return sn;
}

struct Totals {
  u64 files, files_total, bytes, bytes_total, seen;
  bool scanning;
  double frac;
};
Totals totals() {
  Totals t;
  t.files = g_stats.xfer_files.load(std::memory_order_relaxed);
  t.files_total = g_stats.xfer_files_total.load(std::memory_order_relaxed);
  t.bytes = g_stats.xfer_bytes.load(std::memory_order_relaxed);
  t.bytes_total = g_stats.xfer_bytes_total.load(std::memory_order_relaxed);
  t.seen = g_stats.files_seen.load(std::memory_order_relaxed);
  t.scanning = !g_stats.scan_done.load(std::memory_order_relaxed);
  t.files_total = std::max(t.files_total, t.files);
  t.bytes_total = std::max(t.bytes_total, t.bytes);
  t.frac = t.bytes_total ? (double)t.bytes / (double)t.bytes_total
                         : t.files_total ? (double)t.files / (double)t.files_total : (t.scanning ? 0.0 : 1.0);
  return t;
}

void draw_locked() {
  u64 now = now_ns();
  Totals t = totals();
  double dt = (double)(now - t_last) / 1e9;
  if (dt >= 0.05) {
    double ib = (double)(t.bytes - last_bytes) / dt, inf = (double)(t.files - last_files) / dt;
    double a = t_last == t_start ? 1.0 : std::min(1.0, dt / 1.0);  // ~1s smoothing window
    rate_b += (ib - rate_b) * a;
    rate_f += (inf - rate_f) * a;
    last_bytes = t.bytes, last_files = t.files, t_last = now;
  }
  static const char* frames[] = {"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"};

  std::string total;
  if (t.scanning && t.files == 0 && t.bytes == 0) {
    total = std::string(" ") + C("\x1b[36m") + frames[spin++ % 10] + C("\x1b[0m") + " scanning  " + fmt_num(t.seen) + " files";
    if (t.files_total) total += "  ·  " + fmt_num(t.files_total) + " to transfer (" + fmt_size((double)t.bytes_total) + ")";
  } else {
    char pct[16];
    snprintf(pct, sizeof pct, "%3d%%", (int)(t.frac * 100));
    std::vector<std::string> f;
    f.push_back(fmt_num(t.files) + "/" + fmt_num(t.files_total) + " files");
    f.push_back(fmt_size((double)t.bytes) + "/" + fmt_size((double)t.bytes_total));
    f.push_back(fmt_size(rate_b) + "/s");
    f.push_back(fmt_count(rate_f) + " files/s");
    if (t.scanning) f.push_back("scanning…");
    else if (rate_b > 1 && t.bytes_total > t.bytes) f.push_back("ETA " + fmt_eta((double)(t.bytes_total - t.bytes) / rate_b));
    int cols = tty ? term_cols() : 100, bw = std::clamp(cols - 70, 10, 30);
    total = " " + (tty ? bar(t.frac, bw) + " " : std::string()) + C("\x1b[1m") + pct + C("\x1b[0m");
    int used = 1 + (tty ? bw + 1 : 0) + 4;
    for (auto& s : f) {
      if (used + 2 + width(s) >= cols) break;
      total += std::string("  ") + C("\x1b[2m") + (&s == &f[0] ? "" : "· ") + C("\x1b[0m") + s;
      used += 2 + width(s) + (&s == &f[0] ? 0 : 2);
    }
  }

  if (!tty) {
    if (now - t_plain < 1000000000ull) return;
    t_plain = now;
    raw(total + "\n");
    return;
  }

  int cols = term_cols();
  std::string out = "\x1b[?2026h";
  erase(out);
  // Per-file rows. Rows stick to a worker, but a worker busy with a large file takes over a
  // row that is only showing small ones.
  int rows = std::min(nworkers, MAX_ROWS);
  Snap snaps[MAX_WORKERS];
  for (int w = 0; w < nworkers; w++) snaps[w] = sample(w);
  auto big = [&](int w) { return snaps[w].active && snaps[w].size >= (1 << 20); };
  for (int w = 0; w < nworkers; w++) {
    if (!big(w) || std::find(row_w, row_w + rows, w) != row_w + rows) continue;
    for (int r = 0; r < rows; r++)
      if (!big(row_w[r])) {
        row_w[r] = w;
        break;
      }
  }
  int namew = std::max(10, cols - 34);
  for (int r = 0; r < rows; r++) {
    const Snap& s = snaps[row_w[r]];
    if (!s.active) {
      out += std::string(C("\x1b[2m")) + "  ·" + C("\x1b[0m") + "\n";
    } else {
      double fr = s.size > 0 ? (double)s.done / (double)s.size : 1.0;
      char tail[64];
      snprintf(tail, sizeof tail, " %7s ", fmt_size((double)s.size).c_str());
      char pct[16];
      snprintf(pct, sizeof pct, " %3d%%", (int)(std::clamp(fr, 0.0, 1.0) * 100));
      out += "  " + fit_left(s.name, namew) + C("\x1b[2m") + tail + C("\x1b[0m") + bar(fr, 12) + pct + "\n";
    }
    drawn++;
  }
  out += total;
  drawn++;
  out += "\x1b[?2026l";
  raw(out);
}
}  // namespace

void ui_write(bool is_err, std::string_view text) {
  std::lock_guard<std::mutex> lk(ui_mu);
  if (live && drawn) {
    std::string out;
    erase(out);
    raw(out);
  }
  FILE* f = is_err ? stderr : stdout;
  fwrite(text.data(), 1, text.size(), f);
  if (live) fflush(f);
}

void progress_start(int n) {
  std::lock_guard<std::mutex> lk(ui_mu);
  nworkers = std::min(n, MAX_WORKERS);
  t_start = t_last = now_ns();
  if (!g_opt.progress || g_opt.am_server) return;
  g_progress_on = true;
  tty = isatty(2);
  const char* term = getenv("TERM");
  color = tty && !getenv("NO_COLOR") && term && strcmp(term, "dumb") != 0;
  for (int r = 0; r < MAX_ROWS; r++) row_w[r] = r;
  if (tty) {
    live = true;
    raw("\x1b[?25l");
  }
}

void progress_tick() {
  if (!g_progress_on) return;
  std::lock_guard<std::mutex> lk(ui_mu);
  draw_locked();
}

void progress_stop(bool ok) {
  std::lock_guard<std::mutex> lk(ui_mu);
  if (!g_progress_on) return;
  g_progress_on = false;
  std::string out;
  if (live) {
    erase(out);
    out += "\x1b[?25h";
    live = false;
  }
  if (ok) {
    Totals t = totals();
    double el = std::max(1e-9, (double)(now_ns() - t_start) / 1e9);
    char secs[32];
    snprintf(secs, sizeof secs, "%.2fs", el);
    out += std::string(" ") + C("\x1b[32m") + "✓" + C("\x1b[0m") + " ";
    if (t.files == 0) {
      out += "up to date  " + std::string(C("\x1b[2m")) + "· " + C("\x1b[0m") + fmt_num(t.seen) + " files checked in " + secs;
    } else {
      out += fmt_num(t.files) + (t.files == 1 ? " file  " : " files  ") + C("\x1b[2m") + "· " + C("\x1b[0m") + fmt_size((double)t.bytes) + " in " + secs + "  " +
             C("\x1b[2m") + "· " + C("\x1b[0m") + fmt_size((double)t.bytes / el) + "/s  " + C("\x1b[2m") + "· " + C("\x1b[0m") +
             fmt_count((double)t.files / el) + " files/s";
    }
    if (g_opt.dry_run) out += "  (dry run)";
    out += "\n";
  }
  raw(out);
}
