#include <algorithm>
#include <array>
#include <cstdarg>
#include <cstdlib>
#include <ctime>
#include <mutex>

#include "common.h"
#include "fs.h"
#include "progress.h"
#include "output.h"
#include "engine.h"

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

namespace {
constexpr size_t ERROR_SAMPLES = 10, OTHER_ERROR = 256;
struct ErrorSample { int code = 0; std::string text; };
std::mutex error_mu;
std::array<u64, OTHER_ERROR + 1> error_counts{};
std::array<ErrorSample, ERROR_SAMPLES> error_samples;
size_t error_sample_count = 0;

size_t error_group(int code) { return code < (int)OTHER_ERROR ? (size_t)code : OTHER_ERROR; }

void remember_error(int code, std::string_view text) {
  if (code <= 0 || g_opt.am_server) return;
  std::lock_guard<std::mutex> lock(error_mu);
  ++error_counts[error_group(code)];
  if (error_sample_count < ERROR_SAMPLES)
    error_samples[error_sample_count++] = {code, std::string(text.substr(0, 4095))};
}

const char* error_kind(size_t code) {
  switch (code) {
    case RERR_SYNTAX: return "syntax or usage";
    case RERR_PROTOCOL: return "protocol incompatibility";
    case RERR_FILESELECT: return "file selection";
    case RERR_UNSUPPORTED: return "unsupported action";
    case RERR_STARTCLIENT: return "protocol startup";
    case RERR_FILEIO: return "file IO";
    case RERR_STREAMIO: return "stream IO";
    case RERR_MESSAGEIO: return "diagnostic IO";
    case RERR_IPC: return "IPC";
    case RERR_SIGNAL: return "interruption";
    case RERR_PARTIAL: return "partial transfer";
    case RERR_VANISHED: return "vanished source files";
    case RERR_DEL_LIMIT: return "deletion limit";
    case RERR_TIMEOUT: return "idle timeout";
    case RERR_CMD_FAILED: return "remote command failed";
    case RERR_CMD_NOTFOUND: return "remote command not found";
    case 255: return "remote shell failure";
    default: return "other error";
  }
}
}  // namespace

void print_error_summary() {
  if (g_opt.am_server) return;
  // Snapshot before formatting/output so workers never wait on terminal IO.
  std::array<u64, OTHER_ERROR + 1> counts;
  std::array<ErrorSample, ERROR_SAMPLES> samples;
  size_t shown;
  {
    std::lock_guard<std::mutex> lock(error_mu);
    counts = error_counts;
    samples = error_samples;
    shown = error_sample_count;
  }
  u64 total = 0;
  for (u64 n : counts) total += n;
  if (!total) return;
  std::string summary = "xsync: error summary: " + std::to_string(total) +
    (total == 1 ? " error" : " errors") + " (showing first " + std::to_string(shown) + ")\n";
  for (size_t group = 1; group < counts.size(); ++group) {
    if (!counts[group]) continue;
    summary += "  ";
    summary += error_kind(group);
    if (group != OTHER_ERROR) summary += " (code " + std::to_string(group) + ")";
    summary += ": " + std::to_string(counts[group]) + (counts[group] == 1 ? " error\n" : " errors\n");
    for (size_t i = 0; i < shown; ++i) {
      if (error_group(samples[i].code) != group) continue;
      summary += "    ";
      if (group == OTHER_ERROR) summary += "(code " + std::to_string(samples[i].code) + ") ";
      summary += output_escape(samples[i].text) + "\n";
    }
  }
  if (total > shown) summary += "  " + std::to_string(total - shown) + " more errors not shown\n";
  ui_write(true, summary);
}

void err_line(int code, const char* fmt, ...) {
  va_list ap;
  va_start(ap, fmt);
  std::string s = vformat(fmt, ap);
  va_end(ap);
  record_code(code);
  remember_error(code, s);
  if (g_msg_sink) return g_msg_sink(1, code, s);
  ui_write(true, "xsync: " + s + "\n");
}

void die(int code, const char* fmt, ...) {
  // A worker may report a fatal protocol error while the reader observes EOF.
  // Keep the first fatal code instead of letting that disconnect replace it.
  static std::atomic<int> fatal_code{0};
  int previous = 0;
  if (!fatal_code.compare_exchange_strong(previous, code)) _Exit(previous);
  va_list ap;
  va_start(ap, fmt);
  std::string s = vformat(fmt, ap);
  va_end(ap);
  cleanup_open_outputs();
  if (g_msg_sink) g_msg_sink(2, code, s);
  else {
    progress_stop(false);
    output_flush();
    remember_error(code, s);
    fprintf(stderr, "xsync: %s\n", s.c_str());
    print_error_summary();
    fprintf(stderr, "xsync error: exiting (code %d)\n", code);
  }
  fflush(nullptr);
  _Exit(code);
}

void exit_signal() {
  // Reader, writer and main can observe the same output failure together.
  // One thread owns cleanup; the others wait until it exits the process.
  static std::mutex exit_mu;
  std::lock_guard<std::mutex> lock(exit_mu);
  if (output_error()) cancel_remote_peer();
  cleanup_open_outputs();
  progress_stop(false);
  if (!output_error()) output_flush();
  if (int error = output_error()) {
    cancel_remote_peer();
    remember_error(RERR_MESSAGEIO, "write stdout failed: " + errstr(error));
    print_error_summary();
    fprintf(stderr, "xsync error: errors with program diagnostics (code %d)\n", RERR_MESSAGEIO);
    fflush(stderr);
    _Exit(RERR_MESSAGEIO);
  }
  print_error_summary();
  if (!g_opt.am_server) fprintf(stderr, "\nxsync error: received SIGINT, SIGTERM, or SIGHUP (code %d)\n", RERR_SIGNAL);
  _Exit(RERR_SIGNAL);
}

double human_base() { return g_opt.human > 1 ? 1024.0 : 1000.0; }

std::string fmt_size(double v) {
  static const char* u[] = {"B", "K", "M", "G", "T", "P"};
  double unit = human_base();
  int i = 0;
  while (v >= unit && i < 5) v /= unit, i++;
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
    static const char* u[] = {"", "K", "M", "G", "T", "P"};
    double d = (double)v, unit = human_base();
    if (d < unit) return std::to_string(v);
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
