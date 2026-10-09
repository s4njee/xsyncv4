# xsync

A fast, parallel rsync work-alike in C++20. Same command line as rsync, a modern live
progress display, and an engine built for trees of many small files.

```sh
xsync -a  src/ dst/                      # local
xsync -az src/ user@host:/backup/src/    # push over ssh
xsync -az --delete host:/data/ data/     # pull, mirroring deletions
xsync -a --progress src/ dst/            # live per-file + whole-transfer progress
```

## Build

Needs a C++20 compiler, CMake, zstd, xxhash and ICU (`brew install zstd xxhash icu4c` /
`apt install libzstd-dev libxxhash-dev libicu-dev`). ICU supplies Unicode filename comparison.

```sh
cmake -S . -B build -G Ninja && cmake --build build
```

The binary is `build/xsync`. It builds on macOS and Linux (checked with clang 21 and
gcc 12). Native remote transfers use matching xsync versions on both machines
(`--rsync-path=/path/to/xsync` if it is not on the remote `PATH`). If the remote
helper is missing or has a different protocol version, xsync re-executes a real
rsync from PATH with one stderr notice. Unsupported rsync options and daemon
URLs also use this fallback before any transfer. It never installs a helper.
Use `--no-fallback` or `XSYNC_FALLBACK=0` for strict native-only operation;
`--fallback` overrides that environment setting. Transfer failures and malformed
protocol data do not fall back. Original rsync arguments are retained, including
an explicit `--rsync-path`: that command must support rsync if fallback is needed.
Worker, clone and atomic extensions are stripped before invoking rsync.

## Benchmark

`bench/bench.py`, 3 runs per tool, best time shown. Corpus: the 109th Congress slice of the
congress data (76,838 files in 19,073 directories, 494 MiB of content, average file 6.4 KiB),
copied on an M1 Max to the same APFS volume. rsync is 3.4.4 from Homebrew.

These baseline numbers predate the P0 trust fixes and the atomic-write default.
Rerun the benchmark when comparing the current binary's performance.

| scenario                        | rsync   | xsync      | speed-up |
|---------------------------------|--------:|-----------:|---------:|
| local `-a`, fresh copy          | 15.02 s | **2.02 s** | 7.4×     |
| local `-az`, fresh copy         | 15.05 s | **1.97 s** | 7.6×     |
| local `-a`, fresh, `--no-clone` | 15.02 s | **6.65 s** | 2.3×     |
| local `-a`, nothing to do       |  0.77 s | **0.40 s** | 1.9×     |
| pipe `-a`, fresh copy           | 19.92 s | **8.47 s** | 2.4×     |
| pipe `-az`, fresh copy          | 18.00 s | **7.77 s** | 2.3×     |
| pipe `-az`, nothing to do       |  0.99 s | **0.52 s** | 1.9×     |

"pipe" runs the real remote code path of both tools — a sender and a receiver process
talking over a pipe (`-e tests/fakessh.sh`) — without ssh or a network in between. Every
result was verified against the source with `rsync -anci --delete`.

Reproduce (the corpus slice is expected at `.bench/corpus`; any tree works via `--corpus`):

```sh
python3 bench/bench.py --runs 3
```

Things worth knowing when reading these numbers:

- On this machine the cost is almost entirely file creation inside APFS, which does not
  scale with threads: creating a file and writing its first block costs ~100 µs however
  many threads ask. That is why the byte-copying paths top out around 2.3× while clones,
  which need one metadata transaction per directory instead of several per file, reach 7×.
- The local numbers with clones are only available on the same APFS volume with `-a`
  (or at least `-pt`). Across volumes, or with `--no-clone`, expect the 2.3× row.
- `-z` is accepted but does nothing for a local copy: there is no wire to compress for.
  rsync does compress and decompress locally, which costs it nothing here because
  creation dominates.
- A destination filesystem that scales with threads (ext4, XFS) should favour xsync's
  parallel receiver more than APFS does; that has not been measured here.

## How it gets its speed

- **Parallel scan.** Directories are listed with `getattrlistbulk` (names and attributes in
  one call per directory, no per-file `stat`) by a pool of threads; source and destination
  listings are merge-joined to decide what to do.
- **Parallel transfer.** Files are copied by a thread pool in batches per directory. The
  scan runs ahead of the copy, so totals are known almost immediately.
- **Copy-on-write clones.** On APFS, a local copy with `-a` clones files instead of copying
  bytes, and a new directory that holds only files and symlinks is cloned in a single call.
  Clones are independent files sharing storage until one is modified. Disable with
  `--no-clone`.
- **A pipelined wire protocol.** Over ssh the sender streams directory listings, the
  receiver answers with the files it needs, and data flows in ~1 MB blocks that pack many
  small files together. Blocks are zstd-compressed (`-z`) and decompressed on multiple
  threads, checksummed with XXH3, and written by a thread pool. Listing, reading,
  compressing and writing all overlap.

## Progress display

`--progress`, `-P` or `--info=progress2` shows up to four rows of files currently in flight
and a bar for the whole transfer:

```
  data/109/bills/hr/hr1248/fdsys_billstatus.xml           14.9K ━━━━━━━━━━━━ 100%
  data/109/votes/2005/h671/data.json                       212K ━━━━━━╸━━━━━  54%
  data/109/bills/s/s3415/fdsys_billstatus.xml             4.74K ━━━━━━━━━━━━   0%
  data/109/bills/hr/hr1246/data.xml                       13.1K ━━━━━━━━━━━━ 100%
 ━━━━━━━━━━━━━━━━━━╸━━━━━━━━━━━  61%  46,870/76,838 files  · 301M/494M  · 84.7M/s  · 12.9k files/s  · ETA 0:02
```

It is drawn on stderr and only when that is a terminal; otherwise one summary line per
second is printed. `-v` and `-i` lines scroll above the live region. `NO_COLOR` is honoured.

## Compatibility with rsync

Supported with rsync's meaning: `-a -r -d -l -L -p -t -g -o -D -O -J -n -u -c -I -x -z -v -q
-i -h -P -e -f`, `--delete` (and `--del`, `--delete-before/-during/-after/-delay`),
`--delete-excluded`, `--force`, `--exclude`, `--include`, `--exclude-from`,
`--include-from`, `--filter` (`+`/`-` rules and `!`), `--existing`, `--ignore-existing`,
`--ignore-errors`, `--max-delete`,
`--size-only`, `--modify-window`, `--max-size`, `--min-size`, `--inplace`, `--partial`,
`--mkpath`, `--numeric-ids`, `--rsync-path`, `--compress-level`, `--stats`, `--progress`,
`--no-OPTION` forms, trailing-slash semantics, multiple sources, `host:path` and
`user@host:path` on either side, and rsync's exit codes.

Differences to be aware of:

- **Not wire-compatible.** xsync speaks its own protocol, so it needs xsync on both ends
  and delegates rsync daemon transfers (`host::module`, `rsync://`) to rsync.
- **No delta transfer.** Changed files are always sent whole (rsync's `-W`). For many small
  files that is the fast path anyway; for large files that change slightly over a slow
  link, rsync will send less.
- **New byte-copied files are atomic by default.** Files are written to temporary
  names and renamed after verification. `--no-atomic` saves a rename for new files,
  but a crash can leave a truncated file under its final name. `--inplace` explicitly
  requests direct writes. APFS clones already create a content snapshot.
- **Receiver paths are anchored to directories.** Descendant symlinks are never
  followed by writes, metadata operations or cleanup. `--safe-links` skips links
  outside the transfer tree and protects their existing destination entries from
  deletion. The explicit destination path is resolved once at setup.
- **Clones carry extended attributes and ACLs** along, which `rsync -a` (without `-X -A`)
  does not. Use `--no-clone` if that matters.
- **Output order.** With `-v`/`-i`, names appear in the order threads finish them.
- **Delegated to rsync** (strict mode rejects them): `-H`, `-A`, `-X`, `-R`,
  `-b`, `-m`, `-C`, `-F`, `--files-from`, `--link-dest`/`--compare-dest`/`--copy-dest`,
  `--bwlimit`, `--chmod`, `--append`, `--partial-dir`, `--remove-source-files`, per-directory
  merge files and `P`/`R`/`H`/`S` filter rules, listing mode (a single `SRC` argument).
- **Unsupported options fall back before transfer; strict mode fails.** This includes `--out-format`,
  `--timeout`, `--contimeout`, `-S`/`--sparse`, `--fsync`, `--preallocate`,
  `--skip-compress`, `--block-size`, `--checksum-choice`,
  `--log-file-format`, and `--debug`. `--compress-choice` accepts `zstd` or `none`.
  `--info` accepts `progress2`, `progress0`, `stats2`, and `stats0` (comma separated).
- **Compatibility no-ops are listed in `--help` with reasons.** `-W`/`--whole-file`
  and `--no-whole-file` cannot change this engine's whole-file transfers (no delta
  engine exists); `-s`/`--protect-args`/`--secluded-args` is intrinsic
  to protocol-carried paths. `--blocking-io`/`--no-blocking-io` cannot change the
  blocking pipe transport. `-8`/`--8-bit-output` matches the always-raw name output.
  `--no-motd` has no effect because there is no daemon transport.

xsync-only options: `-j N`/`--jobs=N` (worker threads; default is the number of
performance cores), `--no-clone`, `--atomic` (default), `--no-atomic`.

## Tests

`tests/difftest.py` runs 214 scenarios on macOS through both rsync and xsync and compares the
resulting trees (names, types, contents, modes, nanosecond mtimes, symlink targets) and exit
codes — local and remote, fresh copies and updates, deletions, filters, odd file names,
permissions, type changes.

```sh
XSYNC_FALLBACK=0 python3 tests/difftest.py                  # native clone paths
XSYNC_FALLBACK=0 python3 tests/difftest.py --xsync tests/xsync-noclone.sh # byte-copy
cmake --build build --target filter_test && build/filter_test
python3 tests/p0_test.py                                  # trust and injected I/O races
python3 tests/wire_test.py                                # hostile receiver protocol peers
python3 tests/mount_test.py                               # macOS: disposable APFS image
./tests/ssh-rig.sh                                        # Docker: real SSH + SIGINT
./tests/ssh-rig.sh ssh_reach_test.py fallback_test.py        # prompts + fallback
python3 tests/fallback_test.py                            # local fallback checks
XSYNC_LAN_HOST=user@host python3 tests/lan_test.py -v       # missing-helper LAN
./tests/ssh-rig.sh root_test.py                           # Docker: 96 root/ID/device cases
```

In strict native mode, 212 of 214 pass in both configurations; the two that do not use `-m` and `P` filter rules,
which are not implemented. The root group also compares UID/GID values and
character/block device numbers across two machines with different account databases,
including IDs present on only one machine and real sudo elevation on both ends.

## Layout

| file | |
|---|---|
| `src/main.cpp` | option parsing, summary output |
| `src/fs.cpp` | directory listing, the generator (compare and decide), file writing |
| `src/destination.cpp` | anchored receiver paths and symlink safety |
| `src/names.cpp` | destination case and Unicode name equivalence |
| `src/local.cpp` | local engine: scan, clone, copy |
| `src/remote.cpp` | wire protocol, sender, receiver, ssh client/server glue |
| `src/pool.h` | two-queue worker pool |
| `src/progress.cpp` | live progress display |
| `src/filter.cpp` | rsync include/exclude rules |
