#include "app_actor.h"
#include "output.h"
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <dirent.h>
#include <algorithm>
#include <cerrno>
#include <cstring>
#include <cstdlib>

namespace app_actor {
namespace {
constexpr std::string_view PREFIX = "/tmp/xsync-app-actor-";
constexpr const char* NAME = "lease";
struct FD { int fd = -1; ~FD() { if (fd >= 0) close(fd); } };
[[noreturn]] void fail(const std::string& path,const char* operation,int error = 0) {
  throw app_partials::Error(path,operation,error,error ? strerror(error) : operation);
}
DestinationRevision observe(int fd,const std::string& path) {
  struct stat st;
  if (fstat(fd,&st)) fail(path,"recovery_actor_stat",errno);
  return DestinationRevision::from(st);
}
void directory_valid(int fd,const std::string& path,const DestinationRevision& expected) {
  struct stat st;
  auto held = observe(fd,path);
  if (!S_ISDIR(held.mode) || held.uid != geteuid() || (held.mode & 0777) != 0700 ||
      !expected.same_object(held) || lstat(path.c_str(),&st) || !held.same_object(DestinationRevision::from(st)))
    fail(path,"recovery_actor_changed");
}
void file_valid(int parent,int fd,const std::string& path,const DestinationRevision& expected) {
  struct stat st;
  auto held = observe(fd,path);
  if (!(held == expected) || !S_ISREG(held.mode) || held.uid != geteuid() ||
      held.links != 1 || (held.mode & 0777) != 0600 ||
      fstatat(parent,NAME,&st,AT_SYMLINK_NOFOLLOW) || !(held == DestinationRevision::from(st)))
    fail(path,"recovery_actor_changed");
}
std::string contents(const std::string& recovery,const std::string& attempt,const std::string& role) {
  if (!app_partials::valid_id(recovery) || !app_partials::valid_id(attempt) || (role != "sender" && role != "receiver"))
    fail({},"recovery_actor_invalid");
  return "xsync app actor 1\n" + recovery + '\n' + attempt + '\n' + role + '\n';
}
void report(const app_partials::Emit& emit,const app_partials::Error& error,const std::string& recovery) {
  bool busy = error.native == EWOULDBLOCK || error.native == EAGAIN;
  emit("\"type\":\"error\",\"category\":" + app_json::quote(busy || !error.native ? "conflict" : "filesystem") +
    ",\"operation\":" + app_json::quote(error.operation) + ",\"endpoint\":\"local\",\"path\":" + app_json::path(error.path) +
    ",\"recovery_id\":" + app_json::quote(recovery) + ",\"native_code\":" + (error.native ? app_json::quote(std::to_string(error.native)) : "null") +
    ",\"retryable\":" + (busy ? "true" : "false") + ",\"message\":" + app_json::quote(error.what()));
}
}
bool valid_path(std::string_view path) {
  return path.starts_with(PREFIX) && path.size() == PREFIX.size()+6 &&
    std::all_of(path.begin()+PREFIX.size(),path.end(),[](unsigned char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9'); });
}
Lease::Lease(const std::string& recovery,const std::string& attempt,const std::string& role) {
  auto data = contents(recovery,attempt,role);
  char pattern[] = "/tmp/xsync-app-actor-XXXXXX";
  if (!mkdtemp(pattern)) fail({},"recovery_actor_create",errno);
  path = pattern;
  try {
    directory_ = open(path.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (directory_ < 0) fail(path,"recovery_actor_open",errno);
    directory_valid(directory_,path,observe(directory_,path));
    file_ = openat(directory_,NAME,O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if (file_ < 0) fail(path,"recovery_actor_open",errno);
    if (flock(file_,LOCK_EX|LOCK_NB)) fail(path,"recovery_actor_lock",errno);
    size_t offset = 0;
    while (offset < data.size()) {
      ssize_t n = write(file_,data.data()+offset,data.size()-offset);
      if (n < 0 && errno == EINTR) continue;
      if (n <= 0) fail(path,"recovery_actor_write",n ? errno : EIO);
      offset += size_t(n);
    }
    revision = observe(file_,path); file_valid(directory_,file_,path,revision);
  } catch (...) {
    // Preserve uncertain paths rather than removing through an unverified name.
    if (file_ >= 0) close(file_);
    if (directory_ >= 0) close(directory_);
    file_ = directory_ = -1; throw;
  }
}
Lease::~Lease() { if (file_ >= 0) close(file_); if (directory_ >= 0) close(directory_); }
int quiescence(const std::string& path,const std::string& recovery,const std::string& attempt,
               const std::string& role,const DestinationRevision& expected,bool cleanup,const app_partials::Emit& emit) {
  try {
    if (!valid_path(path)) fail(path,"recovery_actor_invalid");
    auto data = contents(recovery,attempt,role);
    FD directory{open(path.c_str(),O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)};
    if (directory.fd < 0) fail(path,"recovery_actor_open",errno);
    auto identity = observe(directory.fd,path); directory_valid(directory.fd,path,identity);
    FD file{openat(directory.fd,NAME,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC)};
    if (file.fd < 0) fail(path,"recovery_actor_open",errno);
    file_valid(directory.fd,file.fd,path,expected);
    if (flock(file.fd,LOCK_EX|LOCK_NB)) fail(path,"recovery_actor_busy",errno);
    char bytes[256]; ssize_t n;
    do { n = pread(file.fd,bytes,sizeof bytes,0); } while (n < 0 && errno == EINTR);
    if (n < 0) fail(path,"recovery_actor_read",errno);
    if (n != ssize_t(data.size()) || std::string_view(bytes,size_t(std::max<ssize_t>(n,0))) != data)
      fail(path,"recovery_actor_changed");
    directory_valid(directory.fd,path,identity); file_valid(directory.fd,file.fd,path,expected);
    if (cleanup) {
      FD scan{fcntl(directory.fd,F_DUPFD_CLOEXEC,0)};
      DIR* entries = scan.fd < 0 ? nullptr : fdopendir(scan.fd);
      if (!entries) fail(path,"recovery_actor_scan",errno);
      scan.fd = -1; bool unexpected = false; errno = 0;
      while (auto entry = readdir(entries)) {
        std::string_view name = entry->d_name;
        if (name != "." && name != ".." && name != NAME) { unexpected = true; break; }
      }
      int error = errno; closedir(entries);
      if (error || unexpected) fail(path,"recovery_actor_cleanup_scope",error);
      directory_valid(directory.fd,path,identity); file_valid(directory.fd,file.fd,path,expected);
      if (unlinkat(directory.fd,NAME,0) || rmdir(path.c_str())) fail(path,"recovery_actor_cleanup",errno);
    }
    emit("\"type\":\"recovery_quiescent\",\"endpoint\":\"local\",\"recovery_id\":" + app_json::quote(recovery) +
      ",\"attempt_id\":" + app_json::quote(attempt) + ",\"role\":" + app_json::quote(role) + ",\"actor_path\":" + app_json::path(path) +
      ",\"actor_cleaned\":" + (cleanup ? "true" : "false"));
    return 0;
  } catch (const app_partials::Error& error) { report(emit,error,recovery); return RERR_FILESELECT; }
}
}
