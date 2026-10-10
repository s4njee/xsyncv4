#include "install.h"
#include "transport.h"
#include "common.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <signal.h>
#include <unistd.h>
#include <array>
#include <cerrno>
#include <filesystem>
#include <sstream>

namespace {
int remote_command(const std::string& host, const std::string& command, int input, std::string& output) {
  auto args = split_shell_words(remote_shell_command());
  if (args.empty()) die(RERR_SYNTAX, "empty remote shell command");
  args.push_back(host);
  args.push_back(command);
  int pipefd[2];
  if (pipe(pipefd) != 0) die(RERR_IPC, "installer pipe: %s", strerror(errno));
  pid_t child = fork();
  if (child < 0) die(RERR_IPC, "installer fork: %s", strerror(errno));
  if (child == 0) {
    if (input < 0) input = open("/dev/null", O_RDONLY);
    if (input < 0 || dup2(input, STDIN_FILENO) < 0 || dup2(pipefd[1], STDOUT_FILENO) < 0) _exit(RERR_IPC);
    close(pipefd[0]); close(pipefd[1]);
    if (input > 2) close(input);
    umask(g_umask);
    std::vector<char*> argv;
    for (auto& a : args) argv.push_back(a.data());
    argv.push_back(nullptr);
    execvp(argv[0], argv.data());
    fprintf(stderr, "xs: installer cannot execute %s: %s\n", argv[0], strerror(errno));
    _exit(127);
  }
  close(pipefd[1]);
  char buffer[4096];
  bool oversized = false;
  for (;;) {
    ssize_t n = read(pipefd[0], buffer, sizeof buffer);
    if (n < 0 && errno == EINTR) {
      if (g_stop.load()) { kill(child, SIGTERM); break; }
      continue;
    }
    if (n <= 0) break;
    if (output.size() + n > 65536) oversized = true;
    else output.append(buffer, n);
  }
  close(pipefd[0]);
  int status = 0;
  while (waitpid(child, &status, 0) < 0 && errno == EINTR) {
    if (g_stop.load()) kill(child, SIGTERM);
  }
  if (g_stop.load()) return RERR_SIGNAL;
  if (oversized) die(RERR_PROTOCOL, "remote installer output exceeds limit (check shell startup output)");
  return WIFEXITED(status) ? WEXITSTATUS(status) : RERR_SIGNAL;
}

bool version(const std::string& text, std::array<int, 3>& v) {
  return sscanf(text.c_str(), "xs version %d.%d.%d", &v[0], &v[1], &v[2]) == 3 &&
         v[0] >= 0 && v[1] >= 0 && v[2] >= 0;
}

std::filesystem::path release_binary(const std::string& name) {
  std::vector<std::filesystem::path> dirs;
  if (const char* env = getenv("XSYNC_RELEASE_DIR")) dirs.emplace_back(env);
  else {
    auto exe = std::filesystem::path(executable_path()).parent_path();
    dirs = {exe, exe / "../dist", exe / "../share/xs/releases"};
  }
  for (auto& dir : dirs) {
    std::error_code error;
    auto path = dir / name;
    if (std::filesystem::is_regular_file(path, error) && access(path.c_str(), R_OK) == 0) return path;
  }
  die(RERR_FILESELECT, "release artifact %s not found; build the release-static preset or set XSYNC_RELEASE_DIR", name.c_str());
}
}  // namespace

int install_remote(const std::string& host, bool force) {
  if (host.empty() || host[0] == '-' || host.find_first_of("\r\n\0", 0, 3) != std::string::npos)
    die(RERR_SYNTAX, "invalid install host");
  std::string output;
  int code = remote_command(host,
      "set -e; uname -s; uname -m; target=\"$HOME/.local/bin/xs\"; "
      "if [ -e \"$target\" ] && [ ! -f \"$target\" ]; then echo 'xs: install target is not a regular file' >&2; exit 4; fi; "
      "if [ -x \"$target\" ]; then \"$target\" --version 2>/dev/null | head -n 1; else printf '\\n'; fi", -1, output);
  if (code) return code;
  std::istringstream lines(output);
  std::string system, arch, installed, extra;
  if (!std::getline(lines, system) || !std::getline(lines, arch) || !std::getline(lines, installed) || std::getline(lines, extra))
    die(RERR_PROTOCOL, "invalid remote platform response (check shell startup output)");
  std::string name;
  if (system == "Linux" && (arch == "x86_64" || arch == "amd64")) name = "xs-linux-amd64";
  else if (system == "Linux" && (arch == "aarch64" || arch == "arm64")) name = "xs-linux-arm64";
  else if (system == "Darwin" && (arch == "arm64" || arch == "x86_64")) name = "xs-darwin-universal";
  else die(RERR_UNSUPPORTED, "no release binary for remote platform %s/%s", system.c_str(), arch.c_str());
  std::array<int, 3> current{}, ours{};
  version(std::string("xs version ") + XSYNC_VERSION, ours);
  if (!force && !installed.empty() && (!version(installed, current) || current > ours))
    die(RERR_UNSUPPORTED, "refusing to overwrite remote version '%s'; use --force", installed.c_str());
  auto binary = release_binary(name);
  int fd = open(binary.c_str(), O_RDONLY | O_CLOEXEC);
  if (fd < 0) die(RERR_FILEIO, "open release %s: %s", binary.c_str(), strerror(errno));
  // The receiving shell performs the version check again before publishing.
  // mktemp and rename keep an interrupted upload from changing the old binary.
  std::string script =
      "set -eu; umask 077; mkdir -p \"$HOME/.local/bin\"; target=\"$HOME/.local/bin/xs\"; "
      "tmp=$(mktemp \"$HOME/.local/bin/.xs-install.XXXXXXXX\"); "
      "trap 'rm -f \"$tmp\"' EXIT; trap 'exit 20' HUP INT TERM; "
      "cat >\"$tmp\"; chmod 755 \"$tmp\"; "
      "new=$(\"$tmp\" --version | head -n 1); "
      "case \"$new\" in 'xs  version " XSYNC_VERSION "  '*) ;; *) echo 'xs: release version mismatch' >&2; exit 4;; esac; ";
  if (!force) script +=
      "current=''; if [ -x \"$target\" ]; then current=$(\"$target\" --version 2>/dev/null | head -n 1); fi; "
      "if [ \"$current\" != " + shell_quote(installed) +
      " ]; then echo 'xs: remote version changed during install; retry or use --force' >&2; exit 4; fi; ";
  script += "if [ -e \"$target\" ] && [ ! -f \"$target\" ]; then echo 'xs: install target is not a regular file' >&2; exit 4; fi; "
            "mv -f \"$tmp\" \"$target\"; printf '%s\\n' \"$new\"";
  output.clear();
  code = remote_command(host, script, fd, output);
  close(fd);
  if (!code) printf("Installed %s on %s at ~/.local/bin/xs\n%s", name.c_str(), host.c_str(), output.c_str());
  return code;
}
