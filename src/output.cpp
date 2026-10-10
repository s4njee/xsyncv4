#include "output.h"
#include "fs.h"
#include "progress.h"

#include <algorithm>
#include <cerrno>
#include <ctime>
#include <fcntl.h>
#include <filesystem>
#include <mutex>
#include <unordered_set>
#include <unistd.h>
#include <poll.h>
#include <sys/stat.h>

void (*g_output_sink)(const OutputEvent&) = nullptr;
namespace {
std::mutex mutex;
struct Line { std::string path, text; };
std::vector<Line> lines;
int log_fd = -1;
bool ordered = false;
std::atomic<int> stdout_error{0};
std::unordered_set<std::string> created_directories;

// Keep script output one line per name, as rsync does for control bytes.
std::string escaped(std::string_view name) {
  std::string result;
  for (size_t i = 0; i < name.size();) {
    unsigned char c = name[i];
    size_t count = c < 0x80 ? 1 : c >= 0xc2 && c <= 0xdf ? 2 : c <= 0xef && c >= 0xe0 ? 3 : c <= 0xf4 && c >= 0xf0 ? 4 : 0;
    bool valid = count && i + count <= name.size();
    for (size_t k = 1; valid && k < count; ++k) valid = ((unsigned char)name[i + k] & 0xc0) == 0x80;
    if (valid && count >= 3) {
      unsigned char next = name[i + 1];
      valid = !(c == 0xe0 && next < 0xa0) && !(c == 0xed && next >= 0xa0) &&
              !(c == 0xf0 && next < 0x90) && !(c == 0xf4 && next >= 0x90);
    }
    if (c >= 128 && g_opt.raw_names) valid = true, count = 1;
    bool octal_backslash = c == '\\' && i + 4 < name.size() && name[i + 1] == '#' &&
                          name[i + 2] >= '0' && name[i + 2] <= '7' &&
                          name[i + 3] >= '0' && name[i + 3] <= '7' && name[i + 4] >= '0' && name[i + 4] <= '7';
    if (!valid || (c < 32 && c != '\t') || c == 127 || octal_backslash) {
      char buffer[6];
      snprintf(buffer, sizeof buffer, "\\#%03o", c);
      result.append(buffer);
      ++i;
    } else {
      result.append(name.substr(i, count));
      i += count;
    }
  }
  return result;
}

std::string render(const OutputEvent& event) {
  const Options& o = g_opt;
  std::string format = o.out_format_set ? o.out_format : o.itemize || !o.log_file.empty() ? "%i %n%L" : "%n%L";
  std::string path = event.path.empty() ? "." : event.path;
  std::string source = g_opt.receiving || event.source.empty() ? path : event.source;
  bool source_dot = source.ends_with("/.");
  // The client's receiving side uses the short name; senders use the source path.
  if (o.relative && !o.receiving) {
    bool cut = source.find("/./") != source.npos || source.starts_with("./");
    std::filesystem::path cleaned;
    for (const auto& component : std::filesystem::path(source))
      if (component != ".") cleaned /= component;
    source = cleaned.string();
    // Absolute -R names keep the slash in sender %n output, while %f still
    // omits it. Dot-dot in the cut-off physical prefix remains visible in %f.
    if (!cut && source.starts_with('/') && source.substr(1) == path) path.insert(path.begin(), '/');
  } else source = std::filesystem::path(source).lexically_normal().string();
  if (source.starts_with('/')) source.erase(0, 1);
  if (source.size() > 1 && source.back() == '/') source.pop_back();
  if (source_dot && source != ".") source += "/.";
  if (event.type == T_DIR) path.push_back('/');
  std::string result;
  for (size_t i = 0; i < format.size(); ++i) {
    if (format[i] != '%' || i + 1 == format.size()) { result.push_back(format[i]); continue; }
    ++i;
    bool left = format[i] == '-';
    if (left) ++i;
    size_t width = 0;
    while (i < format.size() && format[i] >= '0' && format[i] <= '9') width = std::min<size_t>(4096, width * 10 + format[i++] - '0');
    if (i == format.size()) break;
    std::string value, prefix;
    switch (format[i]) {
      case '%': value = "%"; break;
      case 'i': value = event.code; break;
      case 'n': value = escaped(path); break;
      case 'f': value = escaped(source); break;
      case 'L':
        if (!event.target.empty()) prefix = event.hardlink_target ? " => " : " -> ", value = escaped(event.target);
        else if (width) prefix = "    ";
        break;
      case 'l': value = std::to_string(event.size); break;
      case 'b': value = std::to_string(event.bytes); break;
      case 'o': value = event.code.starts_with("*deleting") ? "del." : o.receiving ? "recv" : "send"; break;
      case 't': {
        time_t when = (time_t)event.time;
        tm calendar{};
        if (!localtime_r(&when, &calendar)) { value = "?"; break; }
        char buffer[32];
        if (strftime(buffer, sizeof buffer, "%Y/%m/%d %H:%M:%S", &calendar)) value = buffer;
        else value = "?";
        break;
      }
    }
    if (value.size() < width) {
      if (left) value.append(width - value.size(), ' ');
      else value.insert(0, width - value.size(), ' ');
    }
    result += prefix + value;
  }
  if (!o.out_format_set && !o.itemize && o.log_file.empty() && event.code.starts_with("*deleting")) result.insert(0, "deleting ");
  return result;
}

int emit(std::string_view text) {
  ui_write(false, text);
  if (output_error()) return 0;
  if (log_fd >= 0 && !write_all(log_fd, text.data(), text.size())) {
    int error = errno;
    close(log_fd);
    log_fd = -1;
    return error;
  }
  return 0;
}
void log_error(int error) {
  if (error) err_line(RERR_FILEIO, "write log file \"%s\" failed: %s", g_opt.log_file.c_str(), errstr(error).c_str());
}
}

void output_failure(int error) {
  int none = 0;
  if (stdout_error.compare_exchange_strong(none, error ? error : EIO)) {
    int running = 0;
    g_stop.compare_exchange_strong(running, 1);
  }
}
int output_error() { return stdout_error.load(); }
void output_check() {
  bool events = output_enabled() && (!g_opt.out_format_set || !g_opt.out_format.empty());
  if (g_opt.am_server || g_opt.quiet || output_error() ||
      !(events || g_opt.verbose > 0 || g_opt.stats || g_opt.list_only)) return;
  // Sorted file events can wait until the transfer finishes. Observe the pipe
  // independently so a vanished consumer still cancels active work promptly.
  static const bool monitor = [] {
    struct stat st;
    return fstat(STDOUT_FILENO, &st) != 0 || S_ISFIFO(st.st_mode) || S_ISSOCK(st.st_mode);
  }();
  if (!monitor) return;
  pollfd descriptor{STDOUT_FILENO, POLLOUT, 0};
  int result = poll(&descriptor, 1, 0);
  if (result > 0 && (descriptor.revents & (POLLERR | POLLHUP | POLLNVAL)))
    output_failure(descriptor.revents & POLLNVAL ? EBADF : EPIPE);
}

bool output_enabled() {
  return g_opt.itemize || g_opt.verbose > 0 || g_opt.out_format_set || !g_opt.log_file.empty();
}
std::string output_escape(std::string_view name) { return escaped(name); }

bool output_format_supported(std::string_view format) {
  for (size_t i = 0; i < format.size(); ++i) if (format[i] == '%') {
    if (++i == format.size()) continue;
    if (format[i] == '-') ++i;
    while (i < format.size() && format[i] >= '0' && format[i] <= '9') ++i;
    if (i == format.size() || std::string_view("inLlofbt%").find(format[i]) == std::string_view::npos) return false;
  }
  return true;
}

bool output_format_has(std::string_view format, char escape) {
  for (size_t i = 0; i < format.size(); ++i) if (format[i] == '%') {
    if (++i == format.size()) break;
    if (format[i] == '-') ++i;
    while (i < format.size() && format[i] >= '0' && format[i] <= '9') ++i;
    if (i < format.size() && format[i] == escape) return true;
  }
  return false;
}

void output_configure() {
  g_opt.output_attrs = g_opt.itemize || output_format_has(g_opt.out_format, 'i') || !g_opt.log_file.empty();
  g_opt.output_unchanged = g_opt.itemize_level > 1;
}

void output_start() {
  ordered = !isatty(STDOUT_FILENO);
  if (!g_opt.log_file.empty()) {
    log_fd = open(g_opt.log_file.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    if (log_fd < 0) die(RERR_FILEIO, "open log file \"%s\" failed: %s", g_opt.log_file.c_str(), errstr(errno).c_str());
  }
}

void output_event(OutputEvent event) {
  if (!output_enabled() || g_opt.quiet) return;
  if (!event.time) event.time = time(nullptr);
  if (event.type == T_DIR && (event.code == "cd+++++++++" || event.code == "cd++++++++++")) {
    std::lock_guard<std::mutex> lock(mutex);
    if (!created_directories.insert(event.path).second) return;
  }
  if (g_output_sink) { g_output_sink(event); return; }
  if (g_opt.am_server) return;  // Older peers receive the existing Worker log instead.
  if (g_opt.out_format_set && g_opt.out_format.empty()) return;
  std::string text = render(event) + '\n';
  int error = 0;
  {
    std::lock_guard<std::mutex> lock(mutex);
    if (ordered) lines.push_back({std::move(event.path), std::move(text)});
    else error = emit(text);
  }
  log_error(error);
}

void output_text(std::string_view text) {
  if (g_opt.quiet) return;
  int error;
  {
    std::lock_guard<std::mutex> lock(mutex);
    error = emit(text);
  }
  log_error(error);
}

void output_legacy(std::string_view text) {
  if (g_opt.quiet) return;
  if (text.starts_with("created directory ") || text.find("incremental file list") != std::string_view::npos) {
    output_text(std::string(text) + '\n');
    return;
  }
  int error = 0;
  {
    std::lock_guard<std::mutex> lock(mutex);
    while (!text.empty()) {
      size_t end = text.find('\n');
      auto line = text.substr(0, end);
      std::string path(line);
      if (g_opt.itemize && path.size() > 12) path.erase(0, 12);
      else if (path.starts_with("deleting ")) path.erase(0, 9);
      if (ordered) lines.push_back({std::move(path), std::string(line) + '\n'});
      else if (!error) error = emit(std::string(line) + '\n');
      if (end == std::string_view::npos) break;
      text.remove_prefix(end + 1);
    }
  }
  log_error(error);
}

void output_flush() {
  int error = 0;
  {
    std::lock_guard<std::mutex> lock(mutex);
    std::sort(lines.begin(), lines.end(), [](const Line& a, const Line& b) {
      int order = name_cmp(a.path, b.path);
      return order ? order < 0 : a.text < b.text;
    });
    for (const auto& line : lines) {
      if (output_error()) break;
      if (!error) error = emit(line.text);
    }
    lines.clear();
  }
  log_error(error);
}
