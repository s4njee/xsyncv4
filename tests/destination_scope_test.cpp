#include "destination.h"
#include <algorithm>
#include <barrier>
#include <cerrno>
#include <exception>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sys/resource.h>
#include <thread>
#include <vector>

namespace fs = std::filesystem;
void require(bool ok, const char* message) {
  if (!ok) throw std::runtime_error(message);
}
void write_file(const fs::path& path) {
  auto parent = destination_path(path.string());
  require(parent.fd >= 0, "anchored parent lookup failed");
  int fd = openat(parent.fd, parent.name.c_str(), O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
  require(fd >= 0, "relative creation failed");
  bool ok = write(fd, "safe", 4) == 4;
  close(fd);
  require(ok, "file write failed");
}
size_t descriptors() {
  rlimit limit{};
  require(getrlimit(RLIMIT_NOFILE, &limit) == 0, "descriptor limit lookup failed");
  size_t count = 0;
  for (int fd = 0; fd < (int)std::min<rlim_t>(4096, limit.rlim_cur); ++fd)
    if (fcntl(fd, F_GETFD) >= 0) ++count;
  return count;
}
int main(int argc, char** argv) {
  try {
    require(argc == 3, "provide owned temporary root and case");
    fs::path root = fs::canonical(argv[1]);
    fs::path dest = root / "destination", a = dest / "a", b = dest / "b";
    fs::path outside = root / "outside";
    fs::create_directories(a / "nested");
    fs::create_directories(b);
    fs::create_directories(outside);
    std::string test(argv[2]);
    require(anchor_destination(test == "root-anchor" ? "/" : dest.string()), "destination anchoring failed");
    if (test == "nested") {
      DestinationDirectory first(a.string());
      write_file(a / "one");
      {
        DestinationDirectory second(b.string());
        write_file(b / "two");
      }
      write_file(a / "three");
      write_file(a / "nested" / "four");
      require(fs::exists(a / "one") && fs::exists(b / "two") && fs::exists(a / "three") &&
              fs::exists(a / "nested" / "four"), "nested pins did not restore their parents");
    } else if (test == "escape") {
      fs::create_directory_symlink(outside, a / "escape");
      DestinationDirectory first(a.string());
      require(destination_mkdir((a / "escape" / "bad").c_str(), 0700) < 0,
              "a descendant symlink escaped the pin");
      {
        DestinationDirectory rejected((a / "escape").string());
        write_file(a / "after-failed-pin");
      }
      auto rejected = destination_path((a / ".." / ".." / ".." / "outside").string());
      require(rejected.fd < 0 && errno == EPERM, "a pin bypassed the transfer root");
      require(fs::is_empty(outside), "outside directory changed");
    } else if (test == "swap") {
      {
        DestinationDirectory first(a.string());
        fs::rename(a, dest / "old-a");
        fs::create_directory_symlink(outside, a);
        write_file(a / "pinned");
      }
      require(fs::exists(dest / "old-a" / "pinned") && fs::is_empty(outside),
              "a pinned write followed the replacement symlink");
      auto rejected = destination_path((a / "after-scope").string());
      require(rejected.fd < 0, "the expired pin was retained");
    } else if (test == "threads") {
      std::barrier ready(3);
      std::exception_ptr errors[2];
      auto worker = [&](const fs::path& path, int slot) {
        try {
          DestinationDirectory pin(path.string());
          ready.arrive_and_wait();
          ready.arrive_and_wait();
          write_file(path / "thread-file");
        } catch (...) { errors[slot] = std::current_exception(); }
      };
      std::thread first(worker, a, 0), second(worker, b, 1);
      ready.arrive_and_wait();
      fs::rename(a, dest / "old-a");
      fs::rename(b, dest / "old-b");
      fs::create_directory_symlink(outside, a);
      fs::create_directory_symlink(outside, b);
      ready.arrive_and_wait();
      first.join(); second.join();
      for (auto& error : errors) if (error) std::rethrow_exception(error);
      require(fs::exists(dest / "old-a" / "thread-file") && fs::exists(dest / "old-b" / "thread-file") &&
              fs::is_empty(outside), "directory pins leaked between threads");
    } else if (test == "normalization") {
      DestinationDirectory pin(a.string() + "/./nested/../");
      write_file(a.string() + "//nested/../normalized");
      write_file(a / ".name");
      write_file(a / "...");
      auto same = destination_path(a.string() + "/nested/.././");
      require(same.fd >= 0 && same.name == ".", "normalized pin root lookup failed");
      struct stat st{}, expected{};
      require(fstat(same.fd, &st) == 0 && stat(a.c_str(), &expected) == 0 &&
              st.st_dev == expected.st_dev && st.st_ino == expected.st_ino,
              "normalized root resolved to a different directory");
      auto rejected = destination_path(dest.string() + "-sibling/file");
      require(rejected.fd < 0 && errno == EPERM, "prefix sibling crossed the root boundary");
      auto original = fs::current_path();
      fs::current_path(dest);
      write_file("./a/relative-one");
      fs::current_path(b);
      write_file("../a/relative-two");
      fs::current_path(original);
      require(fs::exists(a / "normalized") && fs::exists(a / "relative-one") &&
              fs::exists(a / "relative-two"), "normalization or changed cwd lost a file");
    } else if (test == "root-anchor") {
      auto same = destination_path("/");
      require(same.fd >= 0 && same.name == ".", "filesystem root lookup failed");
      DestinationDirectory pin(a.string());
      write_file(a / "root-anchored");
      write_file(b / "outside-pin");
      require(fs::exists(a / "root-anchored") && fs::exists(b / "outside-pin"),
              "filesystem root suffix calculation failed");
    } else if (test == "inherited") {
      std::shared_ptr<const DestinationParent> parent;
      {
        DestinationDirectory pin(a.string());
        parent = pin.share();
        require((bool)parent, "parent sharing failed");
      }
      fs::rename(a, dest / "old-a");
      fs::create_directory_symlink(outside, a);
      {
        DestinationDirectory child((a / "nested").string(), parent);
        write_file(a / "nested" / "inherited");
      }
      fs::create_directory_symlink(outside, dest / "old-a" / "escape");
      {
        DestinationDirectory child((a / "escape").string(), parent);
        require(destination_mkdir((a / "escape" / "bad").c_str(), 0700) < 0,
                "inherited descendant followed a symlink");
      }
      require(fs::exists(dest / "old-a" / "nested" / "inherited") && fs::is_empty(outside),
              "inherited parent followed its replacement");
    } else if (test == "inherited-boundaries") {
      DestinationDirectory pin(a.string());
      auto parent = pin.share();
      {
        DestinationDirectory sibling(b.string(), parent);
        write_file(b / "sibling");
      }
      {
        DestinationDirectory normalized(a.string() + "/nested/../nested", parent);
        write_file(a / "nested" / "normalized");
      }
      {
        DestinationDirectory rejected(outside.string(), parent);
        require(destination_mkdir((outside / "bad").c_str(), 0700) < 0 && errno == EPERM,
                "inherited parent crossed the transfer root");
      }
      require(fs::exists(b / "sibling") && fs::exists(a / "nested" / "normalized") && fs::is_empty(outside),
              "inherited prefix fallback or normalization failed");
    } else if (test == "inherited-thread") {
      std::shared_ptr<const DestinationParent> parent;
      {
        DestinationDirectory pin(a.string());
        parent = pin.share();
      }
      fs::rename(a, dest / "old-a");
      fs::create_directory_symlink(outside, a);
      std::exception_ptr error;
      std::thread worker([&] {
        try {
          DestinationDirectory pin((a / "nested").string(), parent);
          write_file(a / "nested" / "thread-inherited");
        } catch (...) { error = std::current_exception(); }
      });
      worker.join();
      if (error) std::rethrow_exception(error);
      require(fs::exists(dest / "old-a" / "nested" / "thread-inherited") && fs::is_empty(outside),
              "parent capability did not cross worker lifetime safely");
    } else if (test == "parent-low-limit") {
      rlimit original{};
      require(getrlimit(RLIMIT_NOFILE, &original) == 0, "descriptor limit lookup failed");
      rlimit low = original;
      low.rlim_cur = 64;
      require(setrlimit(RLIMIT_NOFILE, &low) == 0, "cannot lower descriptor limit");
      size_t before = descriptors();
      {
        DestinationDirectory pin(a.string());
        require(!pin.share(), "parent cache consumes a low descriptor budget");
        write_file(a / "low-limit");
        DestinationDirectory child((a / "nested").string());
        write_file(a / "nested" / "low-limit-child");
      }
      require(descriptors() == before, "low-limit fallback leaked descriptors");
      require(setrlimit(RLIMIT_NOFILE, &original) == 0, "cannot restore descriptor limit");
    } else if (test == "parent-budget") {
      DestinationDirectory pin(a.string());
      size_t before = descriptors();
      std::vector<std::shared_ptr<const DestinationParent>> parents;
      for (int i = 0; i < 300; ++i) {
        auto parent = pin.share();
        if (parent) parents.push_back(std::move(parent));
      }
      require(parents.size() == 256 && descriptors() == before + 256,
              "retained parent descriptors are not bounded");
      {
        DestinationDirectory fallback(b.string());
        require(!fallback.share(), "full descriptor budget admitted another parent");
        write_file(b / "fallback");
      }
      parents.clear();
      require(descriptors() == before, "retained parent descriptors leaked");
      require((bool)pin.share(), "released parent capacity was not reusable");
    } else if (test == "descriptors") {
      auto before = descriptors();
      for (int i = 0; i < 200; ++i) {
        DestinationDirectory first(a.string());
        DestinationDirectory second(b.string());
        auto parent = destination_path((b / "probe").string());
        require(parent.fd >= 0, "descriptor probe failed");
      }
      require(descriptors() == before, "directory pins leaked descriptors");
    } else throw std::runtime_error("unknown case");
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
