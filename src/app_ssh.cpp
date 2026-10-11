#include "app_ssh.h"
#include "app_preview_manifest.h"
#include "app_conflict.h"
#include "app_actor.h"
#include "app_actions.h"
#include "common.h"
#include "engine.h"
#include "transport.h"
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>
#include <algorithm>
#include <cerrno>
#include <cstdlib>
#include <set>
#include <stdexcept>
#include <vector>
#include <thread>
#include <atomic>
#include <utility>

extern char** environ;
namespace app_ssh {
namespace {
using app_json::Value;
using app_json::quote;
constexpr size_t FRAME_LIMIT = 1024*1024, SECRET_LIMIT = 4096;
void nb(int fd) {
  int flags = fcntl(fd, F_GETFL);
  if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) throw std::runtime_error("cannot configure SSH pipe");
}
void cloexec(int fd) { if (fcntl(fd, F_SETFD, FD_CLOEXEC)) throw std::runtime_error("cannot protect SSH descriptor"); }
void pipe_pair(int (&fds)[2]) {
  if (pipe(fds)) throw std::runtime_error("cannot create SSH pipe");
  cloexec(fds[0]); cloexec(fds[1]);
}
unsigned integer(const Value& v, unsigned minimum, unsigned maximum) {
  auto s = v.string(); unsigned n = 0;
  if (s.empty() || s.size() > 5) throw std::runtime_error("invalid SSH integer field");
  for (char c : s) {
    if (c < '0' || c > '9' || n > maximum/10 || (n == maximum/10 && unsigned(c-'0') > maximum%10)) throw std::runtime_error("SSH integer field is out of range");
    n = n*10+c-'0';
  }
  if (n < minimum) throw std::runtime_error("SSH integer field is out of range");
  return n;
}
std::string option_path(const Value& v) {
  auto s = v.string();
  if (s.empty() || s.size() > 4096 || s[0] != '/') throw std::runtime_error("SSH profile file paths must be absolute");
  for (unsigned char c : s) if (c < 32 || c == 127) throw std::runtime_error("SSH profile file path contains a control byte");
  return s;
}
std::string config_quote(std::string_view s) {
  std::string out = "\"";
  for (char c : s) { if (c == '\\' || c == '"') out += '\\'; out += c; }
  return out + '"';
}
struct Reader {
  int fd = -1;
  std::string bytes;
  bool eof = false;
  Reader() = default;
  explicit Reader(int descriptor) : fd(descriptor) {}
  bool ready() {
    char buffer[8192]; ssize_t n = read(fd, buffer, sizeof buffer);
    if (n > 0) {
      bytes.append(buffer, (size_t)n);
      size_t start = 0, end;
      while ((end = bytes.find('\n', start)) != std::string::npos) { if (end-start > FRAME_LIMIT) throw std::runtime_error("SSH peer exceeded frame limit"); start = end+1; }
      if (bytes.size()-start > FRAME_LIMIT) throw std::runtime_error("SSH peer exceeded frame limit");
    } else if (!n) eof = true;
    else if (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) throw std::runtime_error("SSH pipe read failed");
    return n > 0;
  }
  bool pop(std::string& frame) {
    size_t end = bytes.find('\n'); if (end == std::string::npos) return false;
    frame = bytes.substr(0, end); bytes.erase(0, end+1); return true;
  }
};
bool write_frame(int fd, std::string_view bytes) {
  u64 deadline = now_ns() + 2000000000ULL;
  while (!bytes.empty() && !g_stop.load()) {
    ssize_t n = write(fd, bytes.data(), bytes.size());
    if (n > 0) { bytes.remove_prefix((size_t)n); continue; }
    if (n < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) return false;
    if (now_ns() > deadline) return false;
    pollfd p{fd, POLLOUT, 0}; poll(&p, 1, 50);
  }
  return bytes.empty();
}
bool same_user(int fd) {
#ifdef __APPLE__
  uid_t uid; gid_t gid;
  return getpeereid(fd, &uid, &gid) == 0 && uid == geteuid();
#else
  struct ucred credentials{}; socklen_t length = sizeof credentials;
  return getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &credentials, &length) == 0 && credentials.uid == geteuid();
#endif
}
std::string error_fields(std::string_view category, std::string_view message, const Connection& c, bool retryable) {
  // Raw ssh stderr never enters the event/log stream; it can contain sensitive
  // profile details. SSH's untyped exit is classified once inside this adapter.
  return "\"type\":\"error\",\"category\":" + quote(category) + ",\"operation\":\"ssh_connect\",\"endpoint\":{\"kind\":\"ssh\",\"host\":" + quote(c.host) + "},\"native_code\":null,\"retryable\":" + (retryable ? "true" : "false") + ",\"message\":" + quote(message);
}
const char* failure_category(std::string_view stderr_text, int code, bool prompted, bool negotiated) {
  if (stderr_text.find("HOST IDENTIFICATION HAS CHANGED") != stderr_text.npos || stderr_text.find("Host key verification failed") != stderr_text.npos) return "host_key";
  if (stderr_text.find("Permission denied") != stderr_text.npos || (!negotiated && prompted && code == 255)) return "authentication";
  if (code == 127) return "helper_missing";
  if (code == 255) return "network";
  return negotiated ? "interrupted" : "incompatible_schema";
}
std::string fields(Value v) {
  v.object.erase("schema"); v.object.erase("seq"); v.object.erase("id");
  auto json = app_json::serialize(v); return json.substr(1, json.size()-2);
}
u64 decimal(const Value& v) {
  auto s = v.string(); u64 n = 0;
  if (s.empty() || s.size() > 20) throw std::runtime_error("invalid SSH event integer");
  for (char c : s) { if (c < '0' || c > '9' || n > UINT64_MAX/10 || (n == UINT64_MAX/10 && (u64)(c-'0') > UINT64_MAX%10)) throw std::runtime_error("invalid SSH event integer"); n = n*10+c-'0'; }
  return n;
}
struct Process {
  pid_t pid = -1;
  int input = -1, output = -1, errors = -1;
  int status = 0;
  bool reaped = false;
  ~Process() {
    for (int fd : {input, output, errors}) if (fd >= 0) close(fd);
    if (pid <= 0 || reaped) return;
    kill(pid, SIGTERM);
    u64 deadline = now_ns() + 2000000000ULL;
    while (now_ns() < deadline) {
      pid_t r = waitpid(pid, &status, WNOHANG);
      if (r == pid || (r < 0 && errno == ECHILD)) return;
      poll(nullptr, 0, 20);
    }
    kill(pid, SIGKILL); while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
  }
  void reap() {
    if (reaped) return;
    pid_t r = waitpid(pid, &status, WNOHANG);
    if (r == pid) reaped = true;
    else if (r < 0 && errno != EINTR) throw std::runtime_error("SSH process wait failed");
  }
};
void spawn(Process& p, const Connection& c, const AuthContext& auth) {
  std::vector<std::string> args = {"/usr/bin/ssh", "-T", "-oBatchMode=no", "-oNumberOfPasswordPrompts=3", "-oControlMaster=no", "-oStrictHostKeyChecking=" + std::string(c.ask_host_key ? "ask" : "yes"), "-oConnectTimeout=" + std::to_string(c.connect_seconds)};
  if (!c.user.empty()) { args.push_back("-l"); args.push_back(c.user); }
  if (c.port) { args.push_back("-p"); args.push_back(std::to_string(c.port)); }
  if (!c.identity.empty()) { args.push_back("-i"); args.push_back(c.identity); }
  if (!c.known_hosts.empty()) args.push_back("-oUserKnownHostsFile=" + config_quote(c.known_hosts));
  if (!c.config.empty()) { args.push_back("-F"); args.push_back(c.config); }
  if (!c.jump.empty()) { args.push_back("-J"); args.push_back(c.jump); }
  args.push_back(c.host); args.push_back("exec " + shell_quote(c.helper) + " --app");
  std::vector<std::string> environment;
  const std::set<std::string> override = {"SSH_ASKPASS", "SSH_ASKPASS_REQUIRE", "XSYNC_APP_AUTH_SOCKET", "DISPLAY", "LC_ALL", "XSYNC_APP_ASKPASS"};
  for (char** env = environ; *env; ++env) { std::string s = *env; if (!override.count(s.substr(0, s.find('=')))) environment.push_back(std::move(s)); }
  environment.push_back("SSH_ASKPASS=" + auth.helper); environment.push_back("SSH_ASKPASS_REQUIRE=force");
  environment.push_back("XSYNC_APP_AUTH_SOCKET=" + auth.socket); environment.push_back("DISPLAY=xsync-app:0"); environment.push_back("LC_ALL=C");
  std::vector<char*> argv, envp;
  for (auto& arg : args) argv.push_back(arg.data());
  argv.push_back(nullptr);
  for (auto& env : environment) envp.push_back(env.data());
  envp.push_back(nullptr);
  int input[2], output[2], errors[2]; pipe_pair(input); pipe_pair(output); pipe_pair(errors);
  posix_spawn_file_actions_t actions; posix_spawn_file_actions_init(&actions);
  posix_spawn_file_actions_adddup2(&actions, input[0], 0); posix_spawn_file_actions_adddup2(&actions, output[1], 1); posix_spawn_file_actions_adddup2(&actions, errors[1], 2);
  for (int fd : {input[0], input[1], output[0], output[1], errors[0], errors[1]}) posix_spawn_file_actions_addclose(&actions, fd);
  posix_spawnattr_t attributes; posix_spawnattr_init(&attributes);
  sigset_t mask, defaults; sigemptyset(&mask); sigemptyset(&defaults); sigaddset(&defaults, SIGTERM); sigaddset(&defaults, SIGINT); sigaddset(&defaults, SIGHUP); sigaddset(&defaults, SIGPIPE);
  posix_spawnattr_setsigmask(&attributes, &mask); posix_spawnattr_setsigdefault(&attributes, &defaults);
  posix_spawnattr_setflags(&attributes, POSIX_SPAWN_SETSIGMASK | POSIX_SPAWN_SETSIGDEF);
  int code = posix_spawn(&p.pid, args[0].c_str(), &actions, &attributes, argv.data(), envp.data());
  posix_spawnattr_destroy(&attributes); posix_spawn_file_actions_destroy(&actions);
  close(input[0]); close(output[1]); close(errors[1]);
  if (code) { close(input[1]); close(output[0]); close(errors[0]); throw std::runtime_error("cannot launch OpenSSH"); }
  p.input = input[1]; p.output = output[0]; p.errors = errors[0]; nb(p.input); nb(p.output); nb(p.errors);
}
}

struct RemoteLease::Impl {
  Process ssh;
  Connection connection;
  Reader output;
  u64 sequence = 0, call = 0;
  bool failed = false;
};
RemoteLease::RemoteLease() = default;
RemoteLease::~RemoteLease() = default;
bool RemoteLease::active() const { return bool(impl); }
int RemoteLease::run(Value request, const Emit& emit) {
  if (!impl || impl->failed) return RERR_STREAMIO;
  auto& state = *impl;
  auto id = "lease-call-" + std::to_string(++state.call);
  request.object["id"] = {Value::String, id, {}, {}};
  auto fail = [&] {
    state.failed = true;
    emit(error_fields("interrupted", "Remote move lease ended before an authoritative outcome", state.connection, false));
    return RERR_STREAMIO;
  };
  try {
    if (!write_frame(state.ssh.input, app_json::serialize(request) + '\n')) return fail();
    u64 activity = now_ns();
    for (;;) {
      if (g_stop.load()) { state.failed = true; return RERR_SIGNAL; }
      std::string frame;
      while (state.output.pop(frame)) {
        auto event = app_json::parse(frame);
        if (event.at("schema").string() != "1" || decimal(event.at("seq")) != ++state.sequence || event.at("id").string() != id)
          return fail();
        auto type = event.at("type").string();
        if (type == "result") {
          auto code = decimal(event.at("code")); auto status = event.at("status").string();
          if (code > 255 || (status != "success" && status != "partial_failure" && status != "failure" && status != "cancellation") || (status == "success") != (code == 0)) return fail();
          return int(code);
        }
        static const std::set<std::string> types = {"started", "entries", "entry", "phase", "progress", "error", "diagnostic", "action_result", "summary", "invalidate"};
        if (!types.count(type)) return fail();
        if (type == "started") continue;
        if (event.object.count("endpoint")) {
          auto& endpoint = event.object["endpoint"];
          if (endpoint.kind == Value::String) endpoint = {Value::String, "ssh", {}, {}};
          else if (endpoint.kind == Value::Object) endpoint.object["kind"] = {Value::String, "ssh", {}, {}};
        }
        emit(fields(std::move(event)));
      }
      state.ssh.reap();
      if (state.output.eof || state.ssh.reaped || (state.connection.idle_seconds && now_ns()-activity > u64(state.connection.idle_seconds)*1000000000ULL)) return fail();
      pollfd p[2] = {{state.output.fd, POLLIN, 0}, {state.ssh.errors, POLLIN, 0}};
      if (poll(p, 2, 50) > 0) {
        if (p[0].revents & (POLLIN | POLLHUP | POLLERR)) { if (state.output.ready()) activity = now_ns(); }
        if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) { char discard[4096]; (void)read(state.ssh.errors, discard, sizeof discard); }
      }
    }
  } catch (...) { return fail(); }
}
int RemoteLease::finish(const Emit& emit) {
  if (!impl) return 0;
  auto release = app_json::parse("{\"op\":\"_move_release\"}");
  int code = run(std::move(release), emit);
  if (!code) {
    close(impl->ssh.input); impl->ssh.input = -1;
    u64 deadline = now_ns() + 2000000000ULL;
    while (!impl->ssh.reaped && !g_stop.load() && now_ns() < deadline) {
      impl->ssh.reap();
      pollfd p[2] = {{impl->ssh.output, POLLIN, 0}, {impl->ssh.errors, POLLIN, 0}};
      if (poll(p, 2, 20) > 0) {
        if (p[0].revents & (POLLIN | POLLHUP | POLLERR)) impl->output.ready();
        if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) { char discard[4096]; (void)read(impl->ssh.errors, discard, sizeof discard); }
      }
    }
    if (!impl->ssh.reaped || !WIFEXITED(impl->ssh.status) || WEXITSTATUS(impl->ssh.status) || !impl->output.bytes.empty()) {
      emit(error_fields("interrupted", "Remote move helper did not finish cleanly", impl->connection, false)); code = RERR_STREAMIO;
    }
  }
  impl.reset(); return code;
}

Connection parse_connection(const Value& endpoint) {
  Connection c; const auto& v = endpoint.at("connection"); c.host = v.at("host").string();
  auto valid_atom = [](const std::string& s, const std::string& allowed) { if (s.empty() || s.size() > 1024 || s[0] == '-') return false; for (char ch : s) if (allowed.find(ch) == allowed.npos) return false; return true; };
  const std::string basic = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-";
  if (!valid_atom(c.host, basic + ":%[]")) throw std::runtime_error("invalid SSH host or alias");
  if (v.object.count("user")) { c.user = v.at("user").string(); if (!valid_atom(c.user, basic + "@")) throw std::runtime_error("invalid SSH user"); }
  if (v.object.count("port")) c.port = integer(v.at("port"), 1, 65535);
  if (v.object.count("identity_file")) c.identity = option_path(v.at("identity_file"));
  if (v.object.count("known_hosts_file")) c.known_hosts = option_path(v.at("known_hosts_file"));
  if (v.object.count("config_file")) c.config = option_path(v.at("config_file"));
  if (v.object.count("jump_host")) { c.jump = v.at("jump_host").string(); if (!valid_atom(c.jump, basic + "@:%[],")) throw std::runtime_error("invalid SSH jump host"); }
  if (v.object.count("helper_path")) {
    c.helper = v.at("helper_path").string();
    if (c.helper != "xs") c.helper = option_path(v.at("helper_path"));
  }
  if (v.object.count("host_key_policy")) {
    auto policy = v.at("host_key_policy").string();
    if (policy != "ask" && policy != "strict") throw std::runtime_error("host_key_policy must be ask or strict");
    c.ask_host_key = policy == "ask";
  }
  if (v.object.count("connect_timeout_seconds")) c.connect_seconds = integer(v.at("connect_timeout_seconds"), 1, 300);
  if (v.object.count("authentication_timeout_seconds")) c.auth_seconds = integer(v.at("authentication_timeout_seconds"), 1, 600);
  if (v.object.count("prompt_timeout_seconds")) c.prompt_seconds = integer(v.at("prompt_timeout_seconds"), 1, 3600);
  if (v.object.count("idle_timeout_seconds")) c.idle_seconds = integer(v.at("idle_timeout_seconds"), 0, 3600);
  return c;
}
void cleanup_directory(const std::string& directory) {
  if (directory.empty()) return;
  unlink((directory + "/socket").c_str()); unlink((directory + "/askpass").c_str()); rmdir(directory.c_str());
}
AuthContext::~AuthContext() { cleanup(); }
void AuthContext::close_listener() { if (listener >= 0) close(listener); listener = -1; }
void AuthContext::cleanup() { close_listener(); cleanup_directory(directory); directory.clear(); }
void AuthContext::start() {
  char dir[] = "/tmp/xsync-auth-XXXXXX";
  if (!mkdtemp(dir)) throw std::runtime_error("cannot create private authentication directory");
  directory = dir; socket = directory + "/socket"; helper = directory + "/askpass";
  listener = ::socket(AF_UNIX, SOCK_STREAM, 0);
  if (listener < 0) throw std::runtime_error("cannot create authentication socket");
  cloexec(listener); nb(listener);
  sockaddr_un address{}; address.sun_family = AF_UNIX;
  if (socket.size() >= sizeof address.sun_path) throw std::runtime_error("authentication socket path too long");
  memcpy(address.sun_path, socket.c_str(), socket.size()+1);
  if (bind(listener, (sockaddr*)&address, sizeof address) || chmod(socket.c_str(), 0600) || listen(listener, 4)) throw std::runtime_error("cannot bind private authentication socket");
  auto exe = executable_path(); if (exe.empty()) throw std::runtime_error("cannot locate askpass executable");
  std::string script = "#!/bin/sh\nexec " + shell_quote(exe) + " --app-askpass \"$@\"\n";
  int fd = open(helper.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0700);
  if (fd < 0) throw std::runtime_error("cannot create private askpass helper");
  ssize_t written = write(fd, script.data(), script.size()); close(fd);
  if (written != (ssize_t)script.size()) throw std::runtime_error("cannot write private askpass helper");
}

int askpass(int argc, char** argv) {
  // Only the private wrapper uses this internal entry point. Secrets are sent
  // to OpenSSH via stdout, never argv, environment or the app event stream.
  if (argc != 3) return 1;
  const char* socket = getenv("XSYNC_APP_AUTH_SOCKET");
  if (!socket || strlen(socket) >= sizeof(sockaddr_un{}.sun_path)) return 1;
  int fd = ::socket(AF_UNIX, SOCK_STREAM, 0); if (fd < 0) return 1;
  sockaddr_un address{}; address.sun_family = AF_UNIX; strcpy(address.sun_path, socket);
  if (connect(fd, (sockaddr*)&address, sizeof address) || !same_user(fd)) { close(fd); return 1; }
  signal(SIGPIPE, SIG_IGN);
  try {
    nb(fd);
    const char* hint = getenv("SSH_ASKPASS_PROMPT");
    std::string prompt = argv[2]; if (prompt.size() > SECRET_LIMIT) { close(fd); return 1; }
    if (!write_frame(fd, "{\"prompt\":" + quote(prompt) + ",\"hint\":" + quote(hint ? hint : "") + "}\n")) { close(fd); return 1; }
    Reader response{fd}; std::string frame;
    while (!response.pop(frame) && !response.eof) { pollfd p{fd, POLLIN, 0}; if (poll(&p, 1, 100) > 0) response.ready(); }
    close(fd); fd = -1;
    if (frame.empty()) return 1;
    auto answer = app_json::parse(frame);
    if (answer.at("cancelled").boolean()) return 1;
    auto secret = answer.at("answer").string();
    if (secret.size() > SECRET_LIMIT || secret.find_first_of("\r\n\0", 0, 3) != secret.npos) return 1;
    return write_frame(STDOUT_FILENO, secret + '\n') ? 0 : 1;
  } catch (...) { if (fd >= 0) close(fd); return 1; }
}

int run(const Connection& c, const std::string& operation, const std::string& request,
        const AuthContext& auth, int control_fd, const Emit& emit, const Copy* copy) {
  Process ssh; spawn(ssh, c, auth);
  Reader output{ssh.output}, controls{control_fd}, challenge;
  std::unique_ptr<app_preview::ManifestSender> manifest;
  if (copy && copy->preview_inventory) manifest=std::make_unique<app_preview::ManifestSender>(*copy->preview_inventory,copy->push);
  nb(control_fd);
  std::string stderr_text, outgoing = "{\"id\":\"remote-hello\",\"op\":\"hello\",\"schema\":\"1\"}\n";
  bool error_eof = false, negotiated = false, terminal = false, prompted = false;
  int result_code = RERR_STREAMIO, prompt_client = -1;
  u64 last_seq = 0, auth_deadline = now_ns() + (u64)c.auth_seconds*1000000000ULL;
  u64 last_activity = now_ns();
  u64 prompt_deadline = 0; unsigned prompts = 0; std::string prompt_id;
  std::atomic<int> transfer_code{-1};
  std::atomic<bool> conflict_bridge_ready{false};
  std::thread transfer;
  struct Join { std::thread& thread; ~Join() { if (thread.joinable()) { g_stop.store(1); thread.join(); } } } join{transfer};
  bool streaming = false, awaiting_lease = false;
  auto stop_prompt = [&] { if (prompt_client >= 0) close(prompt_client); prompt_client = -1; challenge = Reader{}; prompt_id.clear(); };
  emit("\"type\":\"phase\",\"phase\":\"connecting\"");
  try {
    // The transfer can finish between a body check and this condition. Keep
    // running until the body has joined it and recorded its terminal outcome.
    while (!ssh.reaped || !output.eof || !error_eof || (streaming && !terminal)) {
      if (g_stop.load()) { stop_prompt(); return RERR_SIGNAL; }
      if (!negotiated && prompt_client < 0 && now_ns() > auth_deadline) { emit(error_fields("authentication_timeout", "SSH authentication exceeded its deadline", c, true)); stop_prompt(); return RERR_TIMEOUT; }
      if (negotiated && !streaming && c.idle_seconds && now_ns()-last_activity > (u64)c.idle_seconds*1000000000ULL) { emit(error_fields("network_timeout", "SSH operation exceeded its idle deadline", c, true)); stop_prompt(); return RERR_TIMEOUT; }
      if (prompt_client >= 0 && now_ns() > prompt_deadline) { emit(error_fields("authentication_timeout", "Authentication prompt exceeded its deadline", c, false)); stop_prompt(); return RERR_TIMEOUT; }
      std::string frame;
      while (controls.pop(frame)) {
        auto response = app_json::parse(frame);
        if (response.at("op").string() == "conflict_response") {
          if (streaming && copy && copy->push && conflict_bridge_ready.load()) send_app_control(frame);
          else app_conflict::response(frame);
          continue;
        }
        if (prompt_id.empty() || response.at("prompt_id").string() != prompt_id) {
          emit("\"type\":\"auth_response_rejected\",\"reason\":\"stale_prompt\""); continue;
        }
        if (response.object.count("cancelled") && response.at("cancelled").boolean()) { emit(error_fields("authentication_cancelled", "Authentication prompt was cancelled", c, false)); stop_prompt(); return RERR_SIGNAL; }
        auto answer = response.at("answer").string();
        if (answer.size() > SECRET_LIMIT || answer.find_first_of("\r\n\0", 0, 3) != answer.npos) throw std::runtime_error("invalid authentication answer");
        if (!write_frame(prompt_client, "{\"cancelled\":false,\"answer\":" + quote(answer) + "}\n")) throw std::runtime_error("authentication helper disconnected");
        emit("\"type\":\"auth_response_ack\",\"prompt_id\":" + quote(prompt_id));
        stop_prompt(); auth_deadline = now_ns() + (u64)c.auth_seconds*1000000000ULL;
        emit("\"type\":\"phase\",\"phase\":\"connecting\"");
      }
      if (controls.eof) { stop_prompt(); return RERR_SIGNAL; }
      if (prompt_client >= 0 && challenge.pop(frame)) {
        auto prompt = app_json::parse(frame); auto text = prompt.at("prompt").string(); auto hint = prompt.at("hint").string();
        if (text.size() > SECRET_LIMIT || !prompt_id.empty()) throw std::runtime_error("invalid authentication prompt");
        prompt_id = "auth-" + std::to_string(++prompts); prompted = true;
        // OpenSSH 9.x does not mark host-key questions with its askpass hint.
        // This adapter runs SSH in the C locale and translates its local trust
        // prompt once; GUI clients never inspect prompt strings for control flow.
        bool host_key = (text.starts_with("The authenticity of host '") && text.find("Are you sure you want to continue connecting") != text.npos) || text.starts_with("Please type 'yes', 'no' or the fingerprint:");
        const char* credential_kind = text.starts_with("Enter passphrase for key") ? "key_passphrase" : text.find("password:") != text.npos ? "password" : "interactive";
        emit("\"type\":\"auth_prompt\",\"prompt_id\":" + quote(prompt_id) + ",\"kind\":" + quote(host_key ? "host_key" : hint == "confirm" ? "confirmation" : "credential") + ",\"credential_kind\":" + (host_key ? "null" : quote(credential_kind)) + ",\"echo\":" + (host_key || hint == "confirm" ? "true" : "false") + ",\"message\":" + quote(text) + ",\"timeout_seconds\":" + quote(std::to_string(c.prompt_seconds)));
        emit("\"type\":\"phase\",\"phase\":\"waiting_authentication\"");
      }
      if (prompt_client >= 0 && challenge.eof) {
        emit(error_fields("authentication", "Authentication helper disconnected", c, false));
        stop_prompt(); return RERR_STARTCLIENT;
      }
      while (output.pop(frame)) {
        auto event = app_json::parse(frame);
        if (event.at("schema").string() != "1" || decimal(event.at("seq")) != ++last_seq) throw std::runtime_error("incompatible SSH event schema or ordering");
        auto type = event.at("type").string(), id = event.at("id").string();
        if (!negotiated) {
          if (type != "capabilities" || id != "remote-hello") throw std::runtime_error("SSH helper did not negotiate the app contract");
          bool supports = operation == "probe";
          const auto& operations = event.at("operations");
          if (operations.kind != Value::Array) throw std::runtime_error("invalid SSH capabilities");
          for (const auto& op : operations.array) if (op.string() == operation) supports = true;
          bool bridge = event.object.count("transfer_bridge") && event.at("transfer_bridge").kind == Value::String && event.at("transfer_bridge").string() == "3" &&
            event.object.count("typed_transfer_errors") && event.at("typed_transfer_errors").kind == Value::Bool && event.at("typed_transfer_errors").text == "true";
          bool mappings = bridge && event.object.count("selection_mappings") &&
            event.at("selection_mappings").kind == Value::Bool && event.at("selection_mappings").boolean();
          bool interactive = bridge && event.object.count("conflict_bridge") && event.at("conflict_bridge").kind == Value::String &&
            event.at("conflict_bridge").string() == "1" && event.object.count("interactive_conflicts") && event.at("interactive_conflicts").kind == Value::Bool && event.at("interactive_conflicts").boolean() && (PROTO_FEATURES & PF_APP_CONTROLS);
          bool actions = event.object.count("filesystem_actions") && event.at("filesystem_actions").kind == Value::String && event.at("filesystem_actions").string() == "1";
          bool fingerprint = false;
          for (const auto& op : operations.array) if (op.string() == "fingerprint") fingerprint = true;
          bool moves = bridge && actions && fingerprint && event.object.count("safe_move") &&
            event.at("safe_move").kind == Value::String && event.at("safe_move").string() == "1" && event.object.count("move_lease") &&
            event.at("move_lease").kind == Value::String && event.at("move_lease").string() == "1" && (PROTO_FEATURES & PF_APP_LEASE);
          bool action = operation == "mkdir" || operation == "rename" || operation == "delete" || operation == "metadata";
          auto exact_one = [&](const char* field) {
            return event.object.count(field) && event.at(field).kind == Value::String && event.at(field).string() == "1";
          };
          bool recovery = exact_one("private_partials");
          bool recovery_entries = recovery && exact_one("recovery_entries");
          bool recovery_conflicts = recovery_entries && interactive && exact_one("recovery_conflicts");
          for (const auto& name : {"resume","recovery_state","cleanup_partials"}) {
            bool present = false;
            for (const auto& op : operations.array) if (op.string() == name) present = true;
            recovery = recovery && present;
          }
          recovery_entries = recovery && recovery_entries;
          recovery_conflicts = recovery && recovery_conflicts;
          bool recovery_bridge = recovery_entries && bridge && exact_one("recovery_bridge") &&
            (PROTO_FEATURES & (PF_RESUME | PF_APP_PARTIALS)) == (PF_RESUME | PF_APP_PARTIALS);
          bool pause_bridge = recovery_bridge && exact_one("pause_bridge");
          for (const auto& name : {"recovery_quiescence","_pause_checkpoint"}) {
            bool present = false;
            for (const auto& op : operations.array) if (op.string() == name) present = true;
            pause_bridge = pause_bridge && present;
          }
          if ((operation == "recovery_quiescence" || operation == "_pause_checkpoint") && !pause_bridge) supports = false;
          if ((operation == "recovery_state" || operation == "cleanup_partials") && !recovery) supports = false;
          bool recovery_verification = recovery_bridge && exact_one("recovery_verification");
          for (const auto& name : {"verify_recovery","_verify_recovery"}) {
            bool present = false;
            for (const auto& op : operations.array) if (op.string() == name) present = true;
            recovery_verification = recovery_verification && present;
          }
          if (operation == "verify_recovery" || operation == "_verify_recovery") supports = recovery_verification;
          if (action && !actions) supports = false;
          if (operation == "preflight" && !exact_one("destination_preflight")) supports = false;
          if (copy && (!bridge || (copy->selection_mappings && !mappings) || (copy->interactive_conflicts && !interactive) || (copy->lease && !moves) || (copy->recoverable && !recovery_bridge))) supports = false;
          if (copy && copy->recoverable && copy->interactive_conflicts && !recovery_conflicts) supports = false;
          if (manifest && (!exact_one("preview_bridge") || !exact_one("preview_source_checks"))) supports=false;
          if (!supports) { emit(error_fields("unsupported_feature", "Remote helper does not support this operation", c, false)); return RERR_UNSUPPORTED; }
          // A helper can copy on its own local filesystem. That does not imply
          // this SSH adapter implements transfer requests or remote-to-remote
          // copies. Report the intersection the public endpoint can execute.
          Value available{Value::Array, {}, {}, {}};
          for (const auto& op : operations.array) {
            auto name = op.string();
            if (name == "probe" || name == "list" || name == "stat" || name == "lstat" || name == "fingerprint" || name == "resolve" || (name == "preflight" && exact_one("destination_preflight")) || (name == "copy" && bridge) || (name == "move" && moves) || (name == "resume" && recovery_bridge) || (recovery_verification && name == "verify_recovery") || (pause_bridge && (name == "pause" || name == "recovery_quiescence")) || (recovery && (name == "recovery_state" || name == "cleanup_partials")) || (actions && (name == "mkdir" || name == "rename" || name == "delete" || name == "metadata"))) available.array.push_back(op);
          }
          event.object["peer_operations"] = operations;
          event.object["operations"] = available;
          event.object["ssh_operations"] = available;
          event.object["endpoint_kinds"] = {Value::Array, {}, {{Value::String, "ssh", {}, {}}}, {}};
          event.object["copy_endpoint_kinds"] = bridge ? Value{Value::Array, {}, {{Value::String, "local", {}, {}}, {Value::String, "ssh", {}, {}}}, {}} : Value{Value::Array, {}, {}, {}};
          event.object["conflict_policies"] = bridge ? Value{Value::Array, {}, {{Value::String, "replace", {}, {}}, {Value::String, "skip", {}, {}}}, {}} : Value{Value::Array, {}, {}, {}};
          if (interactive) event.object["conflict_policies"].array.push_back({Value::String, "ask", {}, {}});
          event.object["interactive_conflicts"] = {Value::Bool, interactive ? "true" : "false", {}, {}};
          event.object["selection_mappings"] = {Value::Bool, mappings ? "true" : "false", {}, {}};
          event.object["typed_transfer_errors"] = {Value::Bool, bridge ? "true" : "false", {}, {}};
          event.object["destination_revision_checks"] = {Value::Bool, bridge ? "true" : "false", {}, {}};
          event.object["filesystem_actions"] = actions ? Value{Value::String, "1", {}, {}} : Value{};
          for (const auto& feature : {"delete", "permanent_delete"})
            event.object[feature] = {Value::Bool, actions ? "true" : "false", {}, {}};
          event.object["move_lease"] = moves ? Value{Value::String, "1", {}, {}} : Value{};
          event.object["safe_move"] = moves ? Value{Value::String, "1", {}, {}} : Value{};
          event.object["move"] = {Value::Bool, moves ? "true" : "false", {}, {}};
          event.object["private_partials"] = recovery ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["recovery_entries"] = recovery_entries ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["recovery_conflicts"] = recovery_conflicts ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["recovery_verification"] = recovery_verification ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["destination_preflight"] = exact_one("destination_preflight") ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["recovery_bridge"] = recovery_bridge ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["pause_bridge"] = pause_bridge ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["safe_pause"] = pause_bridge ? Value{Value::String,"1",{}, {}} : Value{};
          event.object["recovery_endpoint_kinds"] = recovery_bridge ? Value{Value::Array,{},{{Value::String,"local",{}, {}},{Value::String,"ssh",{}, {}}},{}} : Value{Value::Array,{},{},{}};
          for (const auto& feature : {"trash", "undo_delete", "fallback"})
            event.object[feature] = {Value::Bool, "false", {}, {}};
          auto version = event.at("version").string(); event.object["peer_version"] = {Value::String, version, {}, {}};
          event.object["backend"] = {Value::String, "native-ssh", {}, {}};
          event.object["endpoint"] = {Value::Object, {}, {}, {{"kind", {Value::String, "ssh", {}, {}}}, {"host", {Value::String, c.host, {}, {}}}}};
          emit(fields(std::move(event))); negotiated = true;
          last_activity = now_ns();
          auto negotiated_request = request;
          if (copy && copy->recoverable && !pause_bridge) {
            auto header = app_json::parse(request); header.object.erase("attempt_id");
            negotiated_request = app_json::serialize(header);
          }
          // Once operation bytes enter the outgoing buffer we cannot prove the
          // remote job did not start, including a partial/failed pipe write.
          if (copy && copy->on_submitted) copy->on_submitted();
          outgoing += operation == "probe" ? "{\"id\":\"remote-operation\",\"op\":\"shutdown\"}\n" : negotiated_request + '\n';
          continue;
        }
        if (id != "remote-operation" || terminal) throw std::runtime_error("SSH helper sent an unexpected request ID or late event");
        if (type=="preview_binding_ready") {
          if (!manifest || !outgoing.empty() || streaming) throw std::runtime_error("unexpected preview binding acknowledgement");
          outgoing=manifest->next(decimal(event.at("next_sequence")))+'\n';
          last_activity=now_ns(); continue;
        }
        if (type == "transfer_ready" && copy && !streaming) {
          if (manifest && !manifest->complete()) throw std::runtime_error("native transfer began before complete preview binding");
          if (event.at("native_wire").string() != "4" || !output.bytes.empty() || !outgoing.empty()) throw std::runtime_error("invalid native transfer handoff");
          int read_fd = ssh.output, write_fd = ssh.input;
          if (copy->lease) {
            read_fd = fcntl(ssh.output, F_DUPFD_CLOEXEC, 0);
            write_fd = fcntl(ssh.input, F_DUPFD_CLOEXEC, 0);
            if (read_fd < 0 || write_fd < 0) { if (read_fd >= 0) close(read_fd); if (write_fd >= 0) close(write_fd); throw std::runtime_error("cannot retain move channel"); }
          } else ssh.output = ssh.input = -1;
          output.eof = true; output.fd = -1;
          streaming = true;
          emit("\"type\":\"phase\",\"phase\":\"scanning\"");
          if (copy->on_started) copy->on_started();
          transfer = std::thread([&, read_fd, write_fd] {
            AppStream stream{copy->push, read_fd, write_fd, [&](std::string json) {
              auto remote = app_json::parse(json);
              auto type = remote.at("type").string();
              static const std::set<std::string> types = {"error", "item_discovered", "item_stage", "item_progress", "item_retry", "item_result", "item_mapping", "conflict", "conflict_resolved", "conflict_replayed", "conflict_response_rejected", "recovery_preparing", "recovery_created", "recovery_resuming", "partial_retained", "partial_published"};
              if (!types.count(type)) throw std::runtime_error("unsupported native app event");
              if (type == "conflict") conflict_bridge_ready.store(true);
              if (type == "conflict_resolved" && remote.at("decision").string() == "cancel") g_stop.store(1);
              if (type.starts_with("item_")) {
                remote.object["source_endpoint"] = {Value::String, copy->push ? "local" : "ssh", {}, {}};
                remote.object["destination_endpoint"] = {Value::String, copy->push ? "ssh" : "local", {}, {}};
              }
              if (remote.object.count("endpoint")) remote.object["endpoint"] = {Value::String, "ssh", {}, {}};
              emit(fields(std::move(remote)));
            }, copy->lease != nullptr, copy->recoverable, copy->receiver_preflight};
            transfer_code.store(run_client(copy->sources, copy->destination, PROTO_VERSION, &stream));
          });
          break;
        }
        if (type == "move_lease_ready" && copy && copy->lease && awaiting_lease) {
          auto code = decimal(event.at("code"));
          if (code > 255 || !output.bytes.empty()) throw std::runtime_error("invalid move lease handoff");
          auto lease = std::make_unique<RemoteLease::Impl>();
          lease->ssh.pid = std::exchange(ssh.pid, -1);
          lease->ssh.input = std::exchange(ssh.input, -1);
          lease->ssh.output = std::exchange(ssh.output, -1);
          lease->ssh.errors = std::exchange(ssh.errors, -1);
          lease->connection = c; lease->sequence = last_seq; lease->output = Reader{lease->ssh.output};
          copy->lease->impl = std::move(lease);
          stop_prompt();
          return result_code ? result_code : int(code);
        }
        if (type == "result") {
          auto status = event.at("status").string(); u64 code = decimal(event.at("code"));
          if (code > 255 || (status != "success" && status != "partial_failure" && status != "failure" && status != "cancellation") || (status == "success") != (code == 0)) throw std::runtime_error("SSH helper sent an invalid result");
          result_code = (int)code; terminal = true;
          // Keeping stdin open until this record prevents an EOF cancellation.
          close(ssh.input); ssh.input = -1;
        } else {
          static const std::set<std::string> types = {"started", "entries", "entry", "resolved", "destination_preflight", "phase", "progress", "item_update", "summary", "error", "diagnostic", "action_result", "invalidate", "recovery_state", "recovery_entry", "recovery_cleaned", "recovery_actor", "recovery_quiescent", "pause_checkpoint", "recovery_verified", "recovery_verified_entry"};
          if (!types.count(type)) throw std::runtime_error("SSH helper sent an unsupported event");
          if (type == "started") continue;  // The local supervisor owns the public lifecycle.
          if (type == "recovery_actor") {
            if (!copy || !copy->recoverable || streaming || event.at("attempt_id").string() != copy->attempt_id ||
                event.at("role").string() != (copy->push ? "receiver" : "sender") ||
                event.at("recovery_id").string() != app_json::parse(request).at("recovery_id").string() ||
                !app_actor::valid_path(app_json::unhex(event.at("actor_path").at("bytes_hex").string())) ||
                !S_ISREG(app_actions::parse_revision(event.at("actor_revision")).mode)) throw std::runtime_error("invalid recovery actor evidence");
            if (copy->actor_ready) {
              auto actor = event; actor.object["endpoint"] = {Value::String,"ssh",{}, {}};
              actor.object.erase("schema"); actor.object.erase("seq"); actor.object.erase("id");
              copy->actor_ready(std::move(actor));
            }
          }
          if (type == "recovery_state" && event.object.count("actors") && event.at("actors").kind == Value::Array)
            for (auto& actor : event.object["actors"].array) if (actor.object.count("endpoint") && actor.at("endpoint").kind == Value::String && actor.at("endpoint").string() == "local")
              actor.object["endpoint"] = {Value::String,"ssh",{}, {}};
          // The helper describes its own filesystem as local. Public attribution
          // belongs to the selected SSH endpoint; path bytes are left untouched.
          if (event.object.count("endpoint")) {
            auto& endpoint = event.object["endpoint"];
            if (endpoint.kind == Value::String) endpoint = {Value::String, "ssh", {}, {}};
            else if (endpoint.kind == Value::Object) endpoint.object["kind"] = {Value::String, "ssh", {}, {}};
          }
          emit(fields(std::move(event)));
        }
      }
      ssh.reap();
      if (streaming && transfer_code.load() >= 0) {
        if (transfer.joinable()) transfer.join();
        result_code = transfer_code.load();
        if (copy->lease) {
          if (!awaiting_lease) { awaiting_lease = true; output = Reader{ssh.output}; last_activity = now_ns(); }
          if (c.idle_seconds && now_ns()-last_activity > u64(c.idle_seconds)*1000000000ULL) throw std::runtime_error("move lease handshake timed out");
        } else terminal = true;
      }
      if (ssh.reaped && output.eof && error_eof && (!streaming || transfer_code.load() >= 0)) break;
      pollfd p[5] = {{output.eof ? -1 : output.fd, POLLIN, 0}, {error_eof ? -1 : ssh.errors, POLLIN, 0}, {controls.eof ? -1 : control_fd, POLLIN, 0}, {prompt_client < 0 ? auth.listener : -1, POLLIN, 0}, {prompt_client, POLLIN, 0}};
      if (poll(p, 5, 50) > 0) {
        if ((p[0].revents & (POLLIN | POLLHUP | POLLERR)) && output.ready()) last_activity = now_ns();
        if (p[1].revents & (POLLIN | POLLHUP | POLLERR)) {
          char buffer[4096]; ssize_t n = read(ssh.errors, buffer, sizeof buffer);
          if (n > 0) {
            stderr_text.append(buffer, (size_t)n);
            if (stderr_text.size() > 16384) stderr_text.erase(0, stderr_text.size()-16384);
          }
          else if (!n) error_eof = true;
          else if (n < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) throw std::runtime_error("SSH diagnostic pipe failed");
        }
        if (p[2].revents & (POLLIN | POLLHUP | POLLERR)) controls.ready();
        if (p[3].revents & POLLIN) {
          int fd = accept(auth.listener, nullptr, nullptr);
          if (fd >= 0) {
            if (!same_user(fd) || prompts >= 16) { close(fd); throw std::runtime_error("invalid authentication broker client"); }
            cloexec(fd); nb(fd); prompt_client = fd; challenge = Reader{fd};
            prompt_deadline = now_ns() + (u64)c.prompt_seconds*1000000000ULL;
          }
        }
        if (p[4].revents & (POLLIN | POLLHUP | POLLERR)) challenge.ready();
      }
      if (!outgoing.empty() && ssh.input >= 0) {
        ssize_t n = write(ssh.input, outgoing.data(), outgoing.size());
        if (n > 0) outgoing.erase(0, (size_t)n);
        else if (n < 0 && errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK) {
          // A refused/failed SSH connection can close stdin before we collect
          // its exit and stderr. Drain those first to preserve the typed cause.
          close(ssh.input); ssh.input = -1; outgoing.clear();
        }
      }
    }
    stop_prompt();
    int code = WIFEXITED(ssh.status) ? WEXITSTATUS(ssh.status) : RERR_SIGNAL;
    if (!output.bytes.empty()) throw std::runtime_error("SSH helper sent a truncated event");
    if (!terminal) { emit(error_fields(failure_category(stderr_text, code, prompted, negotiated), "SSH connection ended before an authoritative result", c, code == 255 && !prompted)); return code ? code : RERR_STREAMIO; }
    // With a native bridge, a local receiver/sender failure can legitimately
    // finish with a successful remote helper. Retain that partial/failure code.
    bool local_failure = streaming && code == 0 && result_code != 0;
    if (!WIFEXITED(ssh.status) || (code != result_code && !local_failure)) { emit(error_fields("interrupted", "SSH helper exit disagrees with its result", c, false)); return RERR_STREAMIO; }
    return result_code;
  } catch (const std::exception&) {
    stop_prompt();
    // Do not include exception data or raw remote text in an authentication log.
    if (streaming) die(RERR_PROTOCOL, "SSH transfer adapter failed");
    emit(error_fields("protocol", "SSH transport or remote machine contract failed", c, false));
    return RERR_PROTOCOL;
  }
}
}
