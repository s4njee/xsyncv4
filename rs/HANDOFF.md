# xs-rs MVP: the handoff

You are building **xs-rs**, a Rust implementation of xs, in one long session. xs is a parallel rsync
work-alike written in C++ (`src/`, about 24,000 lines). A benchmark lab measures it against rsync on real
links, and has done so for weeks; this document is what it learned, turned into a plan. Read it all
before you write code, and come back to it whenever you are unsure.

The bar: **xs-rs must interoperate with the C++ xs byte for byte, and be at least as fast as it.** The lab
will measure xs-rs against both C++ xs and rsync on the same links once your work passes its gate. Where
C++ xs is slow (listed below, with the reasons), being as fast as it is not enough: be faster.

## 1. What done means

A crate `rs/xs-rs` building a binary `xs-rs` for Linux (x86-64 and arm64), in the workspace with
`rs/xs-wire`. macOS is out of scope.

1. **Server, receiving.** `xs-rs --server` accepts a C++ client's push (role `R`): the C++ client runs
   `xs -a SRC/ host:DST/` with xs-rs as the remote program, and DST ends up identical to SRC.
2. **Server, sending.** `xs-rs --server` serves a C++ client's pull (role `S`).
3. **Client.** `xs-rs -a SRC/ host:DST/` pushes to a C++ `xs --server`, and `xs-rs -a host:SRC/ DST/` pulls
   from one. Remote shell from `-e`, then `$XSYNC_RSH`, then `ssh`; remote program from `--rsync-path`,
   else `xs` (as `run_client` finds it: `src/remote.cpp:2925-2963`). Version 4 only: when a server
   refuses it, print the server's message and exit with its code (no version 3, no rsync fallback).
4. **What a copy carries:** regular files (contents, mode, mtime with nanoseconds), directories (mode,
   mtime), symlinks (target, and their own mtime where Linux allows), empty files and directories, any
   valid UTF-8 or non-UTF-8 file name. Owner and group only when running as root (`-o`/`-g`).
   Unchanged files (same size and mtime in whole seconds, as C++ does: `src/fs.cpp:612`, `:1265-1271`)
   are not sent again: a no-op must be cheap.
5. **Features.** Advertise only the feature bits you implement; the C++ peer masks to what both have
   (`common.h:26-52`), so a correct subset interoperates. The MVP needs `PF_CORE`, and should implement
   `PF_ZSTD` (compressed listings and data with `-z`) and `PF_DIR_CHILDREN` if you can; leave delta,
   resume, xattrs, ACLs, hard links, filters and the app bridge for later steps.
6. **Proven by tests the gate runs** (section 7): `cargo test --manifest-path rs/Cargo.toml` with
   `XS_BIN` naming the parent's C++ build, plus `cargo clippy --all-targets -- -D warnings` and
   `cargo fmt --check`. At most 8,000 changed lines under rs/, not counting integration tests in a
   `tests/` directory of rs/.
7. **Measured** (section 8): your final report gives xs-rs's times against C++ xs on the same trees.

## 2. Ground rules

- **Wire-exact, design free.** Every byte on the wire must be what C++ xs writes and accepts; how you get
  there is yours. Different threading, buffering or syscalls are welcome where they are faster.
- **Only `rs/` changes.** `src/`, `tests/` and `benchmarks/` are the reference and the lab, not yours.
- **Crates:** `zstd` (zstd 1.5 frames, which C++ uses as independent one-shot frames), `xxhash-rust`
  with `xxh3` (XXH3-64 and XXH3-128, seed 0; 128-bit values go on the wire as low 64 bits then high, both
  little-endian), `rustix` or `libc` for `openat`/`statx`/`getdents64`/`futimens`/`renameat`,
  `crossbeam-channel`, `parking_lot`, `anyhow`. Plain threads are simpler than async here: the C++ engine
  is threads, and the lab found no win from io_uring, splice or sendfile.
- **Build small:** the controller you run on has 2 CPUs and 2 GB; cargo is held to 2 jobs. Keep
  dependency features minimal and do not build release profiles you do not need.

## 3. The protocol, in the order a transfer runs

Everything is in `src/remote.cpp` (3,500 lines) and `src/common.h`. `rs/xs-wire` already has frames,
integers, HELLO and `F_MSG` (read `src/lib.rs` and its tests); if `rs/xs-wire/src/config.rs` exists, the
configuration frames are done too. Build on it.

| Step | Who sends | Frame | Layout and reference |
|---|---|---|---|
| 0 | both | any | 5-byte header: `u32` payload length, **little-endian**, then `u8` type; payload at most 1 GiB (`:332`, `:486-497`). Integers: unsigned LEB128 `var`, zigzag `svar`; strings: `var` length + bytes (`:68-76`, `:128-161`) |
| 1 | client | HELLO (1) | magic `XSYNC\x01`, `var` version (4), role byte `R`/`S`, `var` features, 32 option bytes then 7 `svar` options (`common.h:73-78`), `var` count + filter rules, `var` count + paths (`:2978-3018`) |
| 2 | server | HELLO (1) | magic, `var` version, `var` negotiated features (`:3336-3342`); a refused version gets a fatal `F_MSG` naming both (`:3234`) |
| 3 | client | config frames | each only when its feature was negotiated, in this order: IO_CONFIG, COMPRESS_CONFIG, XATTR_CONFIG, ACL_CONFIG, CHOWN_CONFIG, SPARSE_CONFIG, LINKDEST_CONFIG, RELATIVE_CONFIG, FILES_CONFIG (+ FILES_DATA/END), FILTER_CONFIG, DELETE_CONFIG, PRUNE_CONFIG, OUTPUT_CONFIG (`:3096-3160` / `:3343-3486`). With only CORE negotiated, none are sent |
| 4 | receiver | F_DEST (10) | `str` machine id (`host:dev:ino` of `/`), `str` path, `var` dev, `var` ino: an overlap guard (`:2697`) |
| 5 | sender | F_DIR (2) | one per directory, **parent before child**: `var` id, `var` parent+1, `var` index in parent, `u8` flags (`DF_*`), then the entries, zstd-packed when `DF_ZSTD` (`:1210-1295`; entry fields from `put_file_attrs`, `:114`; the receiver's parser, `:2018-2134`, refuses names containing `/`, `..` or NUL, `:2075`) |
| 6 | sender | F_IDMAP (9) | only with `PF_IDMAP` |
| 7 | receiver | F_NEED (3) | per directory: `var` id, `var` count, then delta-coded indices of the entries it wants (`:2200-2246`); optional fields only with RESUME/DELTA |
| 8 | sender | F_DATA (4) | `u8` flags (bit 0 = zstd), `u64` LE XXH3-64 of the raw records, then the records raw, or `var` raw length + one zstd frame (`:1399-1418`). Records: `var` dir id, `var` index, `u8` kind (`R_*`, `:55`): `WHOLE` (attrs + bytes; files up to 512 KiB), `CHUNK` (attempt, offset, total, bytes), `END` (attempt, total, `u8` status 0 ok / 1 retry / 2 fail, attrs), `FAIL`. The receiver's handling: `:2307-2562` |
| 9 | sender | F_LIST_END (5), F_DATA_END (6) | end of listings; `var` exit code |
| 10 | receiver | F_DONE (7) | code, files/dirs/links/specials created, deleted, [write ns] (`:2736-2743`), after checking it has everything (`:2720-2731`) |

Side frames you must at least accept: `F_MSG` (8: `u8` kind 0 out / 1 error / 2 fatal, `var` code, text to
the end), `F_KEEPALIVE` (18, empty). Exit codes are rsync's (`common.h:251`). EOF mid-transfer is 12.
How the server is launched: the client spawns `<rsh> host <program> --server` (`:2925-2963`); the server
reads stdin and writes stdout, with fd 1 duplicated and the original pointed at `/dev/null` so nothing
else can write protocol bytes (`:3218-3221`).

**Read the C++ for each frame before you write its Rust.** The table is a map, not the territory: field
order, optional fields and limits are in the code. `tests/wire_test.py` has a Python encoder for frames
and HELLO, and `tests/*_wire_test.py` show how hostile and older peers are refused.

## 4. How C++ xs is fast, and where it is not

The C++ engine, per side: one reader thread and one writer thread per connection, and N workers
(`src/pool.h`) taking tasks from two queues, listing/generating and transferring. The stream is fully
pipelined: no round trip per file, so scanning, reading, compressing, sending and writing all overlap.

What to keep (ranked by the lab's evidence):

1. **Pipelined DIR -> NEED -> DATA, no per-file round trips.** The sender walks and sends listings while
   the receiver diffs them and asks; data flows as soon as a NEED arrives.
2. **Small files packed into ~1 MiB DATA frames** (`SMALL_MAX` 512 KiB, `BLOCK_TARGET` 1 MiB, `:57-58`):
   about 160 files per frame at 6 KiB. Read each file straight into the frame buffer.
3. **A parallel walk, one task per directory**, with `getdents64` into a 64 KiB buffer and one
   `statx(AT_SYMLINK_NOFOLLOW)` per entry on the directory's fd (`src/linux_scan.cpp:35-98`); C++ does not
   trust `d_type`. Listings sorted by name; a listing window caps entries held (65,536, `:1781`).
4. **A cheap no-op:** the receiver lists the destination directory the same way and merge-joins it
   with the sorted source listing on size and mtime seconds; unchanged files cost no data at all.
5. **Bytes-bounded queues** (send queue 48 MiB, `Conn::MAX_Q` `:254`; receiver 16 MiB, `:2705`, charging
   compressed frames at their raw size): memory stays flat, and backpressure reaches ssh.
6. **Independent zstd per frame on worker threads**, with `-z` only: skip payloads under 128 bytes, sample
   blocks of 16 KiB or more (four 2 KiB samples at level 1, compress only if they shrink below 95%),
   skip when the output is not smaller, skip suffixes on a list (`compression.h:10-15`). Adaptive level:
   3 until 256 KiB written, then 1 when the writer moves at least 64 MiB/s, 6 below 8 MiB/s, else 3, and
   step down when the writer keeps up (`compression.cpp:70-145`). Level 1 is the right default on fast
   links (the lab: level 2-3 cost 20-30% at 10 GbE; negative levels were slower).
7. **Large files:** sequential 1 MiB reads, one CHUNK per frame; several large files go to several
   workers. C++ splits a lone file of 32 MiB or more into 4 MiB `pread` ranges only with an explicit
   `-jN` (`fs.cpp:1762-1773`). At 10 GbE C++ reaches 8.1-8.7 Gb/s on one ssh connection with AES-GCM:
   ssh's cipher is the ceiling there, not xs.
8. **Writer:** gathers frames under 32 KiB into writes of up to 256 KiB (`:405-445`). Use
   `write_vectored`; the lab found pipe and write sizes neutral, so do not spend time tuning them.
9. **No fsync.** C++ never syncs; the lab times "durable" with its own `syncfs` afterwards. Do the same.

Where C++ is slow, and how to beat it:

- **A global lock around file create and publish.** `out_open` and `out_finish` hold one
  `recursive_mutex` (`fs.cpp:1615,1883,2004`): on a 711,000-file tree it made `futex` 45% of xs's syscall
  time, 3.4 futex calls per file, and xs slower than rsync on a local copy (strace.md). **Have no global
  lock on the receiver's write path.** Per-file state belongs to the worker writing that file.
- **Walking destination paths from the root.** C++ kept at most 256 parent directory fds (32 on macOS),
  so most directories were opened by walking from the root: 4.2 million `openat` on a no-op pull, 187 s
  of kernel CPU against rsync's 24 s. A branch raising the budget to 8,192 took that no-op from 50 s to
  29 s. **Keep a directory-fd cache keyed by directory id, open each destination directory once, from
  its parent's fd, and raise `RLIMIT_NOFILE` to its hard limit at start.**
- **Too many receiving workers.** 4 receiving workers beat 16 (0.65 of the time on a no-op); on a 4-core
  sender, xs's workers fought ssh for CPU (`-j1` closed a 3-4% gap on large files). **Default to at
  most 4 receiving workers, and fewer sending workers than cores when cores are 4 or fewer.**
- **About 31 syscalls per file against rsync's 21.** C++'s receiver does `openat` (temp name,
  `O_CREAT|O_EXCL|O_NOFOLLOW`), `pwrite`, `fchmod` if needed, `futimens`, `close`, `renameat` and a `dup` of
  the directory fd per file (`fs.cpp:1882-2165`). Do the same work with fewer calls: no `dup`, no extra
  `fstat`, `O_NOATIME` on reads where permitted, `fchmod` only when the mode differs from what `openat`
  set. Count your syscalls with `strace -f -c` on a tree of small files and compare with C++.
- **The client polls for the peer's exit every 25 ms**; a 1 ms poll was 10-13% faster on tiny transfers.
  Wait on the child or the pipe instead of polling.
- **A no-op over a high-latency link is slow.** On this lab's own link (VPS A to AWS, 11 ms RTT), a
  no-op of real-projects takes C++ xs about 5.4 s against rsync's 3.4 s. Every directory costs a DIR and
  a NEED; with 26,652 directories, anything that waits for a reply per directory, or flushes one small
  frame per directory, pays the round trip or a syscall each time. **Never wait for a NEED before sending
  the next listing, batch small DIR and NEED frames into large writes, and keep the walk ahead.**
- **CPU and memory.** C++ uses 1.3-2.4x rsync's CPU and 4-10x its memory (110-200 MiB). Lower is welcome.

## 5. What the lab measured (time ratio = xs time / rsync time; below 1 is faster)

| Cell | C++ xs / rsync |
|---|---|
| Gigabit, small-flat (100,000 files) fresh, Pi 5 sending / receiving | 0.61 / 0.96 |
| Gigabit, small-flat no-op | 0.38-0.43 |
| Gigabit, real-congress (217,000 files, 1.2 GB) fresh | 0.47 / 0.84 |
| Gigabit, small-deep or small-real no-op into the Pi | 0.15 |
| Gigabit, 1 million files, no-op | 0.26-0.33 |
| Gigabit, mixed-bimodal fresh, Pi sending | **1.04 (C++ loses)** |
| 10 GbE, large files (8 GiB) | 0.31-0.46: xs 8-9 Gb/s, rsync 2.8 Gb/s |
| 10 GbE, real-congress fresh, Mac sending | 0.21-0.24 |
| 10 GbE, real-psample (711,000 files, 21 GB) fresh, Mac sending / receiving | 0.26 / 0.66 |
| 10 GbE, real-psample no-op into the Mac | **1.69 (C++ loses)** |
| Local copy, psample, Pi NVMe to USB SSD | **1.12 (C++ loses)** |
| VPS A to AWS, real-projects no-op | **about 1.6 (C++ loses: 5.4 s against 3.4 s)** |

Settings that mattered: `-z` level 1 on compressible data (0.77 of the time on mixed trees, 2x link rate
on text); AES-GCM over ChaCha20 at 10 GbE (1.4-1.7x); `--no-atomic` 0.70-0.75 on small files into a Pi.
Settings that did not: block size, small-file cutoff, queue sizes, read batches, pipe and write sizes.

### The targets for this lab

The lab's corpus is **real-projects**, a 1% sample of a developer's projects folder: 69,316 files,
26,652 directories, 2.13 GB, median file 2.7 KB, p90 20 KB, largest 1 GiB (`benchmarks/lab/samples/
real-projects.sample.json`). It is on the controller at the lab root's `corpora/real-projects`, which you
may read. The three scenarios that matter most:

1. **Projects-folder copies:** real-projects fresh, A to AWS over the internet. Match C++ xs (it copies
   in about 27 s, roughly 650 Mb/s), and beat rsync.
2. **Large files at line rate:** a 1 GiB file must move at the link's speed, limited by ssh, not by you.
3. **Small files on fast links:** per-file cost decides it. Beat C++ xs's 31 syscalls per file.

And the no-op of real-projects over the internet: beat C++ xs's 5.4 s, and aim for rsync's 3.4 s.

## 6. The order to build in: checkpoints

Work through these in order. Each ends with `cargo test` passing; write what you did, what you measured
and what is next in `NOTES.md` in your scratch directory before moving on. The connection to the model
drops now and then: when your session is resumed, read `NOTES.md`, `git status` and `git diff --stat`
first, and carry on from the last checkpoint. Do not start a checkpoint's code before the previous one's
tests pass.

1. **C1 Scaffolding.** Crate `rs/xs-rs` (binary) using `xs-wire`; a test helper that runs the parent's
   C++ `xs` (`XS_BIN`) with `-e tests/fakessh.sh` (the repository's stand-in for ssh: it drops the host
   and runs the command locally) and `--rsync-path` pointing at your built `xs-rs`; a helper that
   builds test trees (nested directories, empty files and directories, a 40 MiB file, symlinks, odd
   names) and one that compares two trees (names, types, sizes, modes, mtimes, symlink targets,
   contents).
2. **C2 The codec.** In xs-wire: the DIR body and file entries, F_NEED, F_DATA with every record kind and
   its XXH3-64, F_DEST, F_LIST_END, F_DATA_END, F_DONE. Unit tests with bytes taken from the C++ code.
3. **C3 Server, receiving.** `xs-rs --server` as receiver; the test: C++ `xs -a` pushes a tree to it,
   and the trees compare equal; then a second push is a no-op (nothing in DATA) and a third after
   changing one file sends only that file.
4. **C4 Server, sending.** The C++ client pulls from `xs-rs --server`; same three tests.
5. **C5 Client.** `xs-rs` pushes to and pulls from C++ `xs --server`; same tests, and the version
   refusal case.
6. **C6 Speed.** Parallel walk and receiver, the directory-fd cache, bounded queues, `-z` with the
   adaptive level; then measure (section 8) and close the gaps the measurements show.
7. **C7 Report.** Clippy and fmt clean, the gate's three commands passing, and the final report.

If time or budget runs short, a working C3 to C5 with honest measurements is worth more than a fast
C3 alone.

## 7. Testing

- Tests that need the C++ binary read `XS_BIN` and skip when it is unset, as
  `rs/xs-wire/tests/interop.rs` does. The parent's build is at `<scratch>/parent/build/xs`.
- Put integration tests in `rs/xs-rs/tests/`: they do not count toward the line limit, so test
  generously there.
- Run trees in a temporary directory under your scratch directory, never under the repository.
- Every interop test compares the destination tree with the source, not just exit codes.

## 8. Measuring

Before your final report, time xs-rs against the parent's C++ `xs` on the same tree, both through
`tests/fakessh.sh` on this machine (no network, so this measures the engine: CPU, syscalls and the
filesystem), at least three runs each, alternating:

- `real-projects` fresh into an empty directory, and again as a no-op;
- a tree of 50,000 files of 1-8 KiB in a few hundred directories;
- one 1 GiB file.

Report the medians and the ratio xs-rs / C++, and `strace -f -c` syscall totals per file for the small
trees. Delete what you copy. The lab then measures xs-rs on the real link.

## 9. Pitfalls the C++ hit

- The frame length is little-endian. Varints are strict: a tenth byte above 1, or more than ten bytes, is
  refused (`RBuf::var`, `:140-153`); mirror the refusals, a hostile peer test depends on them.
- A child's DIR must never be sent before its parent's; a receiver refuses one that arrives early.
- mtimes compare in whole seconds for the quick check, but are set with nanoseconds.
- Create files under a temporary name (`.name.XXXXXX`, `O_CREAT|O_EXCL|O_NOFOLLOW`) and `renameat` into
  place, as C++ does, so an interrupted copy leaves no half file under its real name.
- Never follow a symlink in the destination: open with `O_NOFOLLOW`, anchored to directory fds.
- Large files arrive as CHUNKs that may come out of order and before or after END; track which ranges
  you have and publish only when all are in (`:2474-2514`).
- One worker's slow file must not stall others: no blocking on one file while frames for others wait.
