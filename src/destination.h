#pragma once
#include <string>
#include <cstdint>
#include <memory>
#include <fcntl.h>
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
  DestPath(DestPath&& p) noexcept : fd(p.fd), name(std::move(p.name)), owned_(p.owned_) { p.fd = -1; }
  ~DestPath() { if (owned_ && fd >= 0) close(fd); }
  int release() {
    int f = owned_ || fd < 0 ? fd : fcntl(fd, F_DUPFD_CLOEXEC, 0);
    fd = -1;
    return f;
  }
 private:
  friend DestPath destination_path_impl(const std::string&, bool);
  DestPath(int f, std::string n, bool owned) : fd(f), name(std::move(n)), owned_(owned) {}
  bool owned_ = true;
};
bool anchor_destination(const std::string& path);
DestPath destination_path(const std::string& path);
int destination_open_dir(const char* path);
// How many parent directory descriptors may be retained at once (after raising a default open-file limit).
unsigned destination_parent_budget();
// Retained parent capability, independent of the worker that opened it. Only
// 256 of these descriptors may be retained, fewer with low descriptor limits;
// active scopes remain additional. Limits below 512 disable this cache.
class DestinationParent {
 public:
  ~DestinationParent();
  DestinationParent(const DestinationParent&) = delete;
  DestinationParent& operator=(const DestinationParent&) = delete;
 private:
  friend class DestinationDirectory;
  DestinationParent(int fd, std::string path) : fd_(fd), path_(std::move(path)) {}
  int fd_;
  std::string path_;
};
// A bounded, thread-local pin for one generator/copy batch. Descendants still
// walk with NOFOLLOW; paths outside the pin retain the transfer-root anchor.
class DestinationDirectory {
 public:
  explicit DestinationDirectory(const std::string& path,
                                const std::shared_ptr<const DestinationParent>& parent = {});
  ~DestinationDirectory();
  std::shared_ptr<const DestinationParent> share() const;
  DestinationDirectory(const DestinationDirectory&) = delete;
  DestinationDirectory& operator=(const DestinationDirectory&) = delete;
 private:
  friend DestPath destination_path(const std::string& path);
  friend DestPath destination_path_impl(const std::string& path, bool owned);
  DestinationDirectory* previous_ = nullptr;
  int fd_ = -1;
  std::string path_;
};
int destination_stat(const char* path, struct stat* st);
// Rewalk the logical name from the transfer root, bypassing worker parent pins.
int destination_named_stat(const char* path, struct stat* st);
// Publishes a staged regular file only if the final name is still absent.
// Never falls back to ordinary replacing rename.
int destination_publish_noreplace(int parent, const char* staged, const char* final);
int destination_rename_noreplace(int source_parent, const char* source, int destination_parent, const char* destination);
int destination_chmod(const char* path, mode_t mode);
int destination_chown(const char* path, uid_t uid, gid_t gid);
int destination_times(const char* path, const timespec times[2]);
int destination_crtime(const char* path, time_t seconds);
int fd_crtime(int fd, time_t seconds);
uint32_t blocking_fileflags(uint32_t flags);
int fd_fileflags(int fd, uint32_t flags, bool delay = false);
int destination_fileflags(const char* path, uint32_t flags, bool delay = false,
                          uint64_t expected_dev = 0, uint64_t expected_ino = 0);
int destination_mkdir(const char* path, mode_t mode);
int destination_unlink(const char* path);
int destination_rmdir(const char* path);
int destination_symlink(const char* target, const char* path);
ssize_t destination_readlink(const char* path, char* buf, size_t size);
int destination_mknod(const char* path, mode_t mode, dev_t dev);
int destination_mkfifo(const char* path, mode_t mode);
int destination_clone(const char* source, const char* path, unsigned flags);
bool unsafe_link(std::string_view target, std::string_view parent);
