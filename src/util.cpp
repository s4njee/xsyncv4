#include <algorithm>
#include <cstdarg>
#include <cstdlib>
#include <ctime>

#include "common.h"
#include "fs.h"
#include "progress.h"
#include "output.h"

Options g_opt;
u32 g_umask = 022;
Stats g_stats;
std::atomic<int> g_exit_code{0};
std::atomic<int> g_stop{0};
std::atomic<bool> g_source_io_error{false};
void (*g_msg_sink)(int kind, int code, std::string_view s) = nullptr;

void DirList::sort() {
  if (e.size() < 2) return;
  const char* base = names.data();
  std::sort(e.begin(), e.end(), [base](const Entry& a, const Entry& b) {
    return name_cmp({base + a.name_off, a.name_len}, {base + b.name_off, b.name_len}) < 0;
  });
}

u64 now_ns() {
  timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (u64)ts.tv_sec * 1000000000ull + (u64)ts.tv_nsec;
}

void out_line(std::string_view s) {
  if (g_msg_sink) return g_msg_sink(0, 0, s);
  std::string t(s);
  t.push_back('\n');
  output_text(t);
}

static void record_code(int code) {
  if (code <= 0) return;
  // A hard error outranks "partial transfer", which outranks "vanished files".
  int cur = g_exit_code.load();
  auto rank = [](int c) { return c == 0 ? 0 : c == RERR_VANISHED ? 1 : c == RERR_PARTIAL ? 2 : 3; };
  while (rank(code) > rank(cur) && !g_exit_code.compare_exchange_weak(cur, code)) {
  }
}

static std::string vformat(const char* fmt, va_list ap) {
  char buf[4096];
  int n = vsnprintf(buf, sizeof buf, fmt, ap);
  if (n < 0) n = 0;
  if (n >= (int)sizeof buf) n = sizeof buf - 1;
  return std::string(buf, (size_t)n);
}

void err_line(int code, const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  std::string s = vformat(fmt, ap);
  va_end(ap);
  record_code(code);
  if (g_msg_sink) return g_msg_sink(1, code, s);
  ui_write(true, "xsync: " + s + "\n");
}

void die(int code, const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  std::string s = vformat(fmt, ap);
  va_end(ap);
  cleanup_open_outputs();
  if (g_msg_sink) g_msg_sink(2, code, s);
  else {
    progress_stop(false);
    output_flush();
    fprintf(stderr, "xsync: %s\nxsync error: exiting (code %d)\n", s.c_str(), code);
  }
  fflush(nullptr);
  _Exit(code);
}

void exit_signal() {
  cleanup_open_outputs();
  progress_stop(false);
  output_flush();
  if (!g_opt.am_server) fprintf(stderr, "\nxsync error: received SIGINT, SIGTERM, or SIGHUP (code %d)\n", RERR_SIGNAL);
  _Exit(RERR_SIGNAL);
}

std::string fmt_size(double v) {
  static const char* u[] = {"B", "K", "M", "G", "T", "P"};
  int i = 0;
  while (v >= 1000.0 && i < 5) v /= 1024.0, i++;
  char b[32];
  if (i == 0) snprintf(b, sizeof b, "%.0fB", v);
  else snprintf(b, sizeof b, v >= 100 ? "%.0f%s" : v >= 10 ? "%.1f%s" : "%.2f%s", v, u[i]);
  return b;
}

std::string fmt_count(double v) {
  char b[32];
  if (v < 1000) snprintf(b, sizeof b, "%.0f", v);
  else if (v < 1e6) snprintf(b, sizeof b, v >= 1e5 ? "%.0fk" : "%.1fk", v / 1e3);
  else snprintf(b, sizeof b, "%.2fM", v / 1e6);
  return b;
}

std::string fmt_num(u64 v) {
  if (g_opt.human) {
    if (v < 1000) return std::to_string(v);
    static const char* u[] = {"", "K", "M", "G", "T", "P"};
    double d = (double)v, unit = g_opt.human > 1 ? 1024.0 : 1000.0;
    int i = 0;
    while (d >= unit && i < 5) d /= unit, i++;
    char b[32];
    snprintf(b, sizeof b, "%.2f%s", d, u[i]);
    return b;
  }
  std::string s = std::to_string(v), r;
  int n = (int)s.size();
  for (int i = 0; i < n; i++) {
    if (i && (n - i) % 3 == 0) r.push_back(',');
    r.push_back(s[i]);
  }
  return r;
}
