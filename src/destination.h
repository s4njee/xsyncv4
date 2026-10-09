#pragma once
#include <string>
#include <sys/stat.h>
#include <unistd.h>

// The explicitly selected destination may contain symlinks. Resolve it once,
// then open every receiver-owned descendant without following any symlink.
struct DestPath {
  int fd = -1;
  std::string name;
  DestPath() = default;
  DestPath(int f, std::string n) : fd(f), name(std::move(n)) {}
  DestPath(const DestPath&) = delete;
  DestPath(DestPath&& p) noexcept : fd(p.fd), name(std::move(p.name)) { p.fd = -1; }
  ~DestPath() { if (fd >= 0) close(fd); }
  int release() { int f = fd; fd = -1; return f; }
};
bool anchor_destination(const std::string& path);
DestPath destination_path(const std::string& path);
int destination_open_dir(const char* path);
int destination_stat(const char* path, struct stat* st);
int destination_chmod(const char* path, mode_t mode);
int destination_chown(const char* path, uid_t uid, gid_t gid);
int destination_times(const char* path, const timespec times[2]);
int destination_crtime(const char* path, time_t seconds);
int fd_crtime(int fd, time_t seconds);
int destination_mkdir(const char* path, mode_t mode);
int destination_unlink(const char* path);
int destination_rmdir(const char* path);
int destination_symlink(const char* target, const char* path);
ssize_t destination_readlink(const char* path, char* buf, size_t size);
int destination_mknod(const char* path, mode_t mode, dev_t dev);
int destination_mkfifo(const char* path, mode_t mode);
int destination_clone(const char* source, const char* path, unsigned flags);
bool unsafe_link(std::string_view target, std::string_view parent);
