#include "progress.h"

#include <sys/ioctl.h>
#include <unistd.h>
#include <signal.h>
#include <langinfo.h>
#include <locale.h>
#include <wchar.h>
#include <strings.h>

#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <mutex>
#include "output.h"

Slot g_slots[MAX_WORKERS];
std::atomic<bool> g_progress_on{false};

namespace {
std::mutex ui_mu;
std::mutex claim_mu;
std::atomic<u64> small_completed{0};
u64 last_small = 0;
double rate_small = 0;
bool tty = false, color = false, live = false;
bool unicode = false, winch_installed = false;
volatile sig_atomic_t window_changed = 0;
struct sigaction previous_winch {};
std::vector<int> drawn_widths;
int drawn_cols = 80;
int drawn = 0;  // lines currently occupied by the live region
u64 t_start = 0, t_last = 0, t_plain = 0;
u64 t_draw = 0;
u64 last_bytes = 0, last_files = 0;
double rate_b = 0, rate_f = 0;
unsigned spin = 0;

constexpr int MAX_ROWS = 4;
constexpr u64 ROW_DELAY = 200000000;
struct FileRate { u64 started = 0, time = 0; i64 bytes = 0; double rate = 0; };
FileRate file_rates[MAX_WORKERS];

struct Snap {
  bool active = false;
  i64 size = 0, done = 0;
  u64 started = 0;
  bool cloning = false;
  std::string name;
};

struct RenderLocale {
  locale_t value = newlocale(LC_CTYPE_MASK, "", nullptr);
  ~RenderLocale() { if (value) freelocale(value); }
};
RenderLocale& render_locale() { static RenderLocale locale; return locale; }
struct LocaleScope {
  locale_t previous = render_locale().value ? uselocale(render_locale().value) : nullptr;
  ~LocaleScope() { if (previous) uselocale(previous); }
};
void on_winch(int) { window_changed = 1; }
int term_cols() {
  winsize ws{};
  return ioctl(2, TIOCGWINSZ, &ws) == 0 && ws.ws_col ? ws.ws_col : 80;
}
int term_rows() {
  winsize ws{};
  return ioctl(2, TIOCGWINSZ, &ws) == 0 && ws.ws_row ? ws.ws_row : 24;
}

void raw(std::string_view s) {
  while (!s.empty()) {
    ssize_t n = write(2, s.data(), s.size());
    if (n < 0 && errno == EINTR) continue;
    if (n <= 0) break;
    s.remove_prefix((size_t)n);
  }
}

void erase(std::string& out) {
  if (!drawn) return;
  int cols = term_cols(), rows = drawn;
  if (window_changed && cols != drawn_cols) {
    rows = 0;
    for (int width : drawn_widths) rows += std::max(1, (width + cols - 1) / cols);
  }
  rows = std::min(rows, std::max(1, term_rows() - 1));
  out += '\r';
  if (rows > 1) out += "\x1b[" + std::to_string(rows - 1) + "A";
  out += "\x1b[J";
  drawn = 0;
  drawn_widths.clear();
}

const char* C(const char* code) { return color ? code : ""; }

size_t char_size(std::string_view s) {
  if (s.empty()) return 0;
  unsigned char c = s[0];
  size_t n = c < 0x80 ? 1 : c >= 0xc2 && c <= 0xdf ? 2 : c >= 0xe0 && c <= 0xef ? 3 : c >= 0xf0 && c <= 0xf4 ? 4 : 1;
  if (n > s.size()) return 1;
  for (size_t i = 1; i < n; ++i) if (((unsigned char)s[i] & 0xc0) != 0x80) return 1;
  if (n >= 3) {
    unsigned char next = s[1];
    if ((c == 0xe0 && next < 0xa0) || (c == 0xed && next >= 0xa0) ||
        (c == 0xf0 && next < 0x90) || (c == 0xf4 && next >= 0x90)) return 1;
  }
  return n;
}
int char_width(std::string_view s) {
  wchar_t character;
  mbstate_t state{};
  size_t n = mbrtowc(&character, s.data(), s.size(), &state);
  if (n == (size_t)-1 || n == (size_t)-2) return (unsigned char)s[0] < 0x80 ? 1 : 2;
  return std::max(0, wcwidth(character));
}
int width(std::string_view s) {
  int w = 0;
  while (!s.empty()) {
    size_t n = char_size(s);
    w += char_width(s.substr(0, n));
    s.remove_prefix(n);
  }
  return w;
}

std::string clip(std::string_view s, int columns) {
  std::string result;
  for (int used = 0; !s.empty();) {
    size_t n = char_size(s);
    int w = char_width(s.substr(0, n));
    if (used + w > columns) break;
    result.append(s.substr(0, n));
    s.remove_prefix(n);
    used += w;
  }
  return result;
}
std::string display_name(std::string_view name) {
  std::string result;
  std::string escaped_name = output_escape(name);
  for (std::string_view text = escaped_name; !text.empty();) {
    unsigned char c = text[0];
    size_t n = char_size(text);
    if (c == '\t' || (c >= 128 && (!unicode || n == 1))) {
      char escaped[6];
      snprintf(escaped, sizeof escaped, "\\#%03o", c);
      result += escaped;
      n = 1;
    } else result.append(text.substr(0, n));
    text.remove_prefix(n);
  }
  return result;
}
const char* separator() { return unicode ? " · " : " | "; }

// Keep the tail of a path that fits in `w` columns.
std::string fit_left(std::string_view s, int w) {
  if (w <= 0) return {};
  if (width(s) <= w) return std::string(s) + std::string((size_t)(w - width(s)), ' ');
  const char* ellipsis = unicode ? "…" : "~";
  size_t i = s.size();
  int used = 1;
  while (i > 0) {
    size_t j = i - 1;
    while (j > 0 && ((unsigned char)s[j] & 0xC0) == 0x80) j--;
    int cw = char_width(s.substr(j, i - j));
    if (used + cw > w) break;
    used += cw;
    i = j;
  }
  return ellipsis + std::string(s.substr(i)) + std::string((size_t)(w - used), ' ');
}

std::string bar(double frac, int w) {
  frac = std::clamp(frac, 0.0, 1.0);
  int full = (int)(frac * w);
  std::string b;
  for (int i = 0; i < full; i++) b += unicode ? "━" : "#";
  if (full < w) {
    b += unicode ? (frac * w - full >= 0.5 ? "╸" : "─") : ">";
    for (int i = full + 1; i < w; i++) b += unicode ? "─" : "-";
  }
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
  std::unique_lock<std::mutex> lock(s.mutex, std::try_to_lock);
  if (lock.owns_lock()) {
    sn.active = s.active.load(std::memory_order_relaxed);
    sn.size = s.size;
    sn.started = s.started;
    sn.cloning = s.cloning;
    sn.done = s.done.load(std::memory_order_relaxed);
    sn.name.assign(s.name, std::min<size_t>(s.len, sizeof s.name));
    return sn;
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
  if (g_opt.pushing) {
    t.bytes = g_stats.acknowledged_bytes.load(std::memory_order_relaxed);
    t.files = g_stats.acknowledged_files.load(std::memory_order_relaxed);
  }
  t.seen = g_stats.files_seen.load(std::memory_order_relaxed);
  t.scanning = !g_stats.scan_done.load(std::memory_order_relaxed);
  t.files_total = std::max(t.files_total, t.files);
  t.bytes_total = std::max(t.bytes_total, t.bytes);
  t.frac = t.bytes_total ? (double)t.bytes / (double)t.bytes_total
                         : t.files_total ? (double)t.files / (double)t.files_total : (t.scanning ? 0.0 : 1.0);
  if (g_opt.pushing && t.files < t.files_total) t.frac = std::min(t.frac, .99);
  return t;
}

void draw_locked() {
  LocaleScope locale;
  u64 now = now_ns();
  Totals t = totals();
  double dt = (double)(now - t_last) / 1e9;
  if (dt >= 0.05) {
    double ib = (double)(t.bytes >= last_bytes ? t.bytes - last_bytes : 0) / dt;
    double inf = (double)(t.files >= last_files ? t.files - last_files : 0) / dt;
    double a = t_last == t_start ? 1.0 : std::min(1.0, dt / 1.0);
    rate_b += (ib - rate_b) * a;
    rate_f += (inf - rate_f) * a;
    u64 small = small_completed.load(std::memory_order_relaxed);
    rate_small += ((double)(small - last_small) / dt - rate_small) * a;
    last_small = small;
    last_bytes = t.bytes, last_files = t.files, t_last = now;
  }
  static const char* frames[] = {"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"};
  static const char* ascii_frames[] = {"|", "/", "-", "\\"};
  int columns = tty ? std::max(0, term_cols() - 1) : 99;
  std::string total;
  if (t.scanning && t.files == 0 && t.bytes == 0) {
    total = std::string(" ") + (unicode ? frames[spin++ % 10] : ascii_frames[spin++ % 4]) +
            " scanning  " + fmt_num(t.seen) + " files";
    if (t.files_total) total += separator() + fmt_num(t.files_total) + " to transfer (" + fmt_size((double)t.bytes_total) + ")";
    total = clip(total, columns);
  } else {
    int pct = (int)(std::clamp(t.frac, 0.0, 1.0) * 100);
    std::vector<std::string> fields;
    fields.push_back(fmt_num(t.files) + "/" + fmt_num(t.files_total) + " files");
    if (g_stats.clone_dirs_total.load()) fields.push_back(fmt_num(g_stats.cloned_dirs) + "/" + fmt_num(g_stats.clone_dirs_total) + " directories cloned");
    fields.push_back(fmt_size((double)t.bytes) + "/" + fmt_size((double)t.bytes_total));
    if (g_opt.pushing) fields.push_back("sent " + fmt_size((double)g_stats.wire_sent.load()) + " wire");
    fields.push_back(fmt_size(rate_b) + "/s");
    fields.push_back(fmt_count(rate_f) + " files/s");
    if (t.scanning) fields.push_back(unicode ? "scanning…" : "scanning...");
    else if (rate_b > 1 && t.bytes_total > t.bytes) fields.push_back("ETA " + fmt_eta((double)(t.bytes_total - t.bytes) / rate_b));
    int bw = tty && columns >= 32 ? std::clamp(columns - 70, 8, 30) : 0;
    total = (bw ? " " + bar(t.frac, bw) + " " : "") + std::to_string(pct) + "%";
    for (const auto& field : fields) {
      std::string between = &field == &fields[0] ? "  " : separator();
      if (width(total) + width(between) + width(field) > columns) break;
      total += between + field;
    }
    total = clip(total, columns);
  }

  if (!tty) {
    if (now - t_plain < 1000000000ull) return;
    t_plain = now;
    raw(total + "\n");
    return;
  }

  std::string out = "\x1b[?2026h";
  erase(out);
  int rows = std::min(MAX_ROWS, std::max(0, term_rows() - 2));
  Snap snaps[MAX_WORKERS];
  std::vector<int> visible;
  bool small_active = false;
  for (int w = 0; w < MAX_WORKERS; w++) {
    snaps[w] = sample(w);
    const Snap& s = snaps[w];
    if (!s.active) continue;
    if (!s.cloning && (now <= s.started || now - s.started < ROW_DELAY)) { small_active = true; continue; }
    visible.push_back(w);
    FileRate& f = file_rates[w];
    if (f.started != s.started) f = {s.started, now, s.done, now > s.started ? (double)s.done / ((double)(now - s.started) / 1e9) : 0};
    else if (now > f.time) {
      double elapsed = (double)(now - f.time) / 1e9;
      double rate = (double)std::max<i64>(0, s.done - f.bytes) / elapsed;
      f.rate += (rate - f.rate) * std::min(1.0, elapsed);
      f.time = now, f.bytes = s.done;
    }
  }
  std::stable_sort(visible.begin(), visible.end(), [&](int a, int b) { return snaps[a].started < snaps[b].started; });
  u64 small = small_completed.load(std::memory_order_relaxed);
  bool show_small = rows && (small_active || small);
  if (show_small) --rows;
  for (int w : visible) {
    if (rows-- <= 0) break;
    const Snap& s = snaps[w];
    std::string line;
    if (s.cloning) line = "  cloning " + display_name(s.name);
    else {
      double fr = s.size > 0 ? (double)s.done / (double)s.size : 1.0;
      std::string pct = std::to_string((int)(std::clamp(fr, 0.0, 1.0) * 100)) + "%";
      std::string tail = " " + pct;
      if (columns >= 55) {
        double rate = file_rates[w].rate;
        tail += " " + fmt_size(rate) + "/s";
        if (rate > 1 && s.size > s.done) tail += " ETA " + fmt_eta((double)(s.size - s.done) / rate);
      }
      if (columns >= 95) {
        std::string size = fmt_size((double)s.size);
        size.insert(0, size.size() < 7 ? 7 - size.size() : 0, ' ');
        tail = " " + size + " " + bar(fr, 12) + tail;
      }
      int namew = std::max(0, columns - 2 - width(tail));
      line = "  " + fit_left(display_name(s.name), namew) + tail;
    }
    line = clip(line, columns);
    out += line + '\n';
    drawn_widths.push_back(width(line));
    ++drawn;
  }
  if (show_small) {
    std::string line = clip("  small files  " + fmt_num(small) + separator() + fmt_count(rate_small) + " files/s", columns);
    out += line + '\n';
    drawn_widths.push_back(width(line));
    ++drawn;
  }
  out += std::string(C("\x1b[1m")) + total + C("\x1b[0m");
  drawn_widths.push_back(width(total));
  ++drawn;
  drawn_cols = term_cols();
  window_changed = 0;
  out += "\x1b[?2026l";
  raw(out);
}

}  // namespace

void slot_begin(int wid, std::string_view dir, std::string_view name, i64 size, bool cloning) {
  if (!g_progress_on || wid < 0) return;
  Slot& s = g_slots[wid];
  std::lock_guard<std::mutex> lock(s.mutex);
  size_t n = 0, cap = sizeof s.name;
  if (!dir.empty()) {
    if (dir.size() + 1 + name.size() > cap) dir.remove_prefix(std::min(dir.size(), dir.size() + 1 + name.size() - cap));
    memcpy(s.name, dir.data(), dir.size());
    n = dir.size();
    if (n < cap) s.name[n++] = '/';
  }
  size_t m = std::min(name.size(), cap - n);
  memcpy(s.name + n, name.data(), m);
  s.len = (u16)(n + m);
  s.size = size;
  s.started = now_ns();
  s.cloning = cloning;
  s.done.store(0, std::memory_order_relaxed);
  s.active.store(true, std::memory_order_relaxed);
}

int slot_claim(std::string_view dir, std::string_view name, i64 size) {
  if (!g_progress_on) return -1;
  std::lock_guard<std::mutex> lock(claim_mu);
  for (int w = 0; w < MAX_WORKERS; w++) {
    if (g_slots[w].active.load(std::memory_order_relaxed)) continue;
    slot_begin(w, dir, name, size);
    return w;
  }
  return -1;
}

void slot_end(int wid, bool completed) {
  if (!g_progress_on || wid < 0) return;
  Slot& s = g_slots[wid];
  std::lock_guard<std::mutex> lock(s.mutex);
  if (completed && s.active.load(std::memory_order_relaxed) && now_ns() - s.started < ROW_DELAY)
    small_completed.fetch_add(1, std::memory_order_relaxed);
  s.active.store(false, std::memory_order_relaxed);
}

void ui_write(bool is_err, std::string_view text) {
  std::lock_guard<std::mutex> lk(ui_mu);
  if (live && drawn) {
    std::string out;
    erase(out);
    raw(out);
  }
  FILE* f = is_err ? stderr : stdout;
  if (!is_err && output_error()) return;
  if (fwrite(text.data(), 1, text.size(), f) != text.size() && !is_err) output_failure(errno);
  if ((live || !is_err) && fflush(f) != 0 && !is_err) output_failure(errno);
}

void progress_start(int n) {
  std::lock_guard<std::mutex> lk(ui_mu);
  t_start = t_last = now_ns();
  if (!g_opt.progress || g_opt.am_server) return;
  g_progress_on = true;
  tty = isatty(2);
  const char* term = getenv("TERM");
  tty = tty && term && *term && strcmp(term, "dumb") != 0;
  auto locale = render_locale().value;
  const char* codeset = locale ? nl_langinfo_l(CODESET, locale) : "";
  unicode = strcasecmp(codeset, "UTF-8") == 0 || strcasecmp(codeset, "UTF8") == 0;
  if (term && strcmp(term, "dumb") == 0) unicode = false;
  color = tty && !getenv("NO_COLOR");
  if (tty) {
    live = true;
    struct sigaction action {};
    action.sa_handler = on_winch;
    sigemptyset(&action.sa_mask);
    winch_installed = sigaction(SIGWINCH, &action, &previous_winch) == 0;
    raw("\x1b[?25l");
  }
}

void progress_tick() {
  output_check();
  if (!g_progress_on) return;
  std::lock_guard<std::mutex> lk(ui_mu);
  if (!g_progress_on) return;
  u64 now = now_ns();
  if (now - t_draw < 60000000) return;
  t_draw = now;
  draw_locked();
}

void progress_stop(bool ok) {
  std::lock_guard<std::mutex> lk(ui_mu);
  if (!g_progress_on) return;
  g_progress_on = false;
  LocaleScope locale;
  std::string out;
  if (live) {
    erase(out);
    out += "\x1b[?25h";
    live = false;
  }
  if (winch_installed) {
    sigaction(SIGWINCH, &previous_winch, nullptr);
    winch_installed = false;
  }
  if (ok) {
    Totals t = totals();
    double el = std::max(1e-9, (double)(now_ns() - t_start) / 1e9);
    char secs[32];
    snprintf(secs, sizeof secs, "%.2fs", el);
    std::string complete = unicode ? " ✓ " : " OK ";
    if (t.files == 0) {
      const char* result = g_exit_code.load() ? (g_opt.pushing ? "no files acknowledged" : "no files completed") : "up to date";
      complete += std::string(result) + separator() + fmt_num(t.seen) + " files checked in " + secs;
    } else {
      complete += fmt_num(t.files) + (t.files == 1 ? " file" : " files") + separator() + fmt_size((double)t.bytes) + " in " + secs + separator() +
             fmt_size((double)t.bytes / el) + "/s" + separator() +
             fmt_count((double)t.files / el) + " files/s";
    }
    if (g_opt.dry_run) complete += "  (dry run)";
    if (g_stats.cloned_dirs.load()) complete += separator() + fmt_num(g_stats.cloned_dirs) + " directories cloned";
    out += (tty ? clip(complete, std::max(0, term_cols() - 1)) : complete) + '\n';
  }
  raw(out);
}
