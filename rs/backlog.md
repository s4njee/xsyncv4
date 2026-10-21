# xs-rs speed backlog

What stands between xs-rs and xs-c++, in the order to work on it: one pull request into `rust-ds` each, with the
race numbers before and after in its description. From a review on 2026-10-21 of `rs/` against `src/`.

Where things stood: a local race through `tests/fakessh.sh` (no network) had xs-rs slightly ahead on small-deep
(fresh 0.93, no-op 0.89, update 0.98 of xs-c++'s time). Over a real internet link (11 ms RTT) it lost: projects
tree fresh 1.46, no-op 1.66; congress update 1.19. The difference is structure: both ends of xs-rs do nearly
everything on one thread, which costs little on a zero-latency pipe and a lot when every NEED waits a round trip.

## 1. macOS: per-OS constants, and the macOS build
- [x] `ffi.rs` hard-coded Linux's `AT_FDCWD` (-100), `AT_SYMLINK_NOFOLLOW` (0x100) and `UTIME_OMIT`; macOS's are
  -2, 0x20 and -2. Symlink mtimes were never set, and `UTIME_OMIT` wrote a bogus atime.
- [x] The xs-wire configuration test offered POSIX ACLs to a macOS xs, which wants Darwin ACLs.

## 2. A round trip in the race
- [x] `rs/race.py --rtt MS`: run the remote side behind a relay that delays each direction by half the RTT, so a
  local race shows what a real link does to a pipeline that waits.

## 3. Sender: walk, read and answer NEEDs at once
- [x] `run_sender` (`transfer.rs`) walks and lists the whole tree before it serves one NEED, then reads every file
  on that same thread. xs-c++ runs `-j` workers (half of them scanning), a reader thread for NEEDs, tasks of 64
  files or 8 MiB, each worker filling its own 1 MiB DATA block (`remote.cpp:1374-1421`, `:1774-1794`).
- [x] A delta signature wait (`wait_signature`) stalls only its own worker, not the sender.

## 4. Receiver: a reader thread and a worker pool
- [x] `run_receiver` (`transfer/receiver.rs`) parses DIRs, lists the destination, diffs, builds NEEDs and writes
  every small file on one thread; a DIR behind a 1 MiB DATA frame waits for ~160 file writes. xs-c++'s reader
  only queues: DIRs to queue 0 (LIFO, preferred by half the workers), DATA to queue 1, 16 MiB bound
  (`remote.cpp:2603-2706`).

## 5. Directory fds and fewer syscalls per file
- [x] A directory-fd cache keyed by directory id, each opened from its parent's fd; `openat`, `futimens`,
  `renameat`, `mkdirat`. Raise `RLIMIT_NOFILE` to its hard limit.
- [x] Per file: no `set_len` on a new file, `fchmod` only when the created mode differs, `fchown` only when the
  group differs, ids and groups looked up once (`fs.cpp:1882-2165`, `:136-151`).
- [x] Per new directory: one `mkdir(mode|0700)`, no `lstat` when the parent listing says the name is absent.
- [ ] The final pass skips directories already right, and works on directory fds (`fs.cpp:1553-1589`).

## 6. Bulk listings
- [x] Linux: a `statx` relative to the directory's fd per entry (`DirEntry::metadata`), as `linux_scan.cpp`
  does, instead of a full-path `lstat`, for the destination listing and the source walk.
- [x] Skip listing a directory just created.
- [ ] macOS: `getattrlistbulk` into a 128 KiB buffer (`fs.cpp:327-442`), which needs a compact entry type in
  place of `fs::Metadata` in the receiver's listing; the sender's walk on worker threads (`scan_workers`).

## 7. The output path
- [x] The server writes through `io::stdout()`, whose `LineWriter` splits writes at newline bytes: write fd 1
  directly (and read fd 0 directly).
- [x] A byte-bounded writer queue (48 MiB, `Conn::MAX_Q`) that gathers small frames into writes of up to 256 KiB
  with `write_vectored`, instead of an unbounded channel flushed whenever it is momentarily empty.
- [x] Fewer copies: frames passed by value, written without a header-plus-payload copy (unlimited, one piece);
  the receiver writes small files and chunks from the DATA frame as it arrived; no 1 MiB allocation per NEED.
- [ ] DATA built in a reused buffer with its header reserved and files read straight into it (`remote.cpp:1395`).
- [x] `Watchdog::drop` joins a thread that sleeps 50 ms at a time, on both ends: wake it instead.
