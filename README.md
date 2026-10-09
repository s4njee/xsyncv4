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

Needs Python 3, a C++20 compiler, CMake, zstd, xxhash and ICU (`brew install zstd xxhash icu4c` /
`apt install libzstd-dev libxxhash-dev libicu-dev`). ICU supplies Unicode filename comparison.

```sh
cmake -S . -B build -G Ninja && cmake --build build
```

The binary is `build/xsync`. It builds on macOS and Linux (checked with clang 21 and
gcc 12). Native remote transfers use a common supported xsync protocol on both machines
(`--rsync-path=/path/to/xsync` if it is not on the remote `PATH`). If the remote
helper is missing or has no supported protocol in common, xsync re-executes a real
rsync from PATH with one stderr notice. Unsupported rsync options and daemon
URLs also use this fallback before any transfer. It never installs a helper.
Use `--no-fallback` or `XSYNC_FALLBACK=0` for strict native-only operation;
`--fallback` overrides that environment setting. Transfer failures and malformed
protocol data do not fall back. Original rsync arguments are retained, including
an explicit `--rsync-path`: that command must support rsync if fallback is needed.
Worker, clone and atomic extensions are stripped before invoking rsync.

## Personal defaults

For scalar options and on/off flags, precedence is **command-line flags, then
environment, then config**. Within one layer, the last value wins. Repeatable
options such as filters accumulate from config, then environment, then flags;
`--filter='!'` clears earlier
filter rules. There is no automatic change to progress defaults.

The optional config file is `$XDG_CONFIG_HOME/xsync/config`, or
`~/.config/xsync/config` when `XDG_CONFIG_HOME` is unset. `XSYNC_CONFIG` selects
another file; an empty value disables the config file. A missing default file
is ignored; an explicitly selected missing file is an error. For example:

```text
# ~/.config/xsync/config
--progress
--jobs=4
--exclude 'scratch files'
```

`XSYNC_OPTS` contains additional shell-quoted options, for example
`export XSYNC_OPTS='--jobs=8 --no-progress'`. Config lines use the same quoting;
blank lines and whole-line `#` comments are allowed. Quoting only splits words:
commands, variables and `~` are never expanded. Defaults contain options and
their values, with transfer paths supplied on the command line. Control actions
such as `--install`, `--server`, `--help` and `--version` are not defaults.

`-e`/`--rsh` overrides `XSYNC_RSH`, which overrides `RSYNC_RSH`, then a remote
shell in `XSYNC_OPTS`, then one in config, then `ssh`. `XSYNC_FALLBACK` overrides
a fallback switch in `XSYNC_OPTS` or config; an explicit command-line
`--fallback`/`--no-fallback` wins. Empty remote-shell values fail clearly.
Fallback passes the effective defaults and original transfer arguments to rsync
after stripping xsync's extensions. `--help`, `--version` and protocol-server
invocations bypass personal defaults; servers use the client's wire options.

## Install locally

Install the built executable, generated man page and zsh completion into a prefix:

```sh
cmake --install build --prefix "$HOME/.local"
```

Add that prefix's `bin` to `PATH`. For zsh, put
`fpath=("$HOME/.local/share/zsh/site-functions" $fpath)` before `compinit` in
`.zshrc`. The completer uses zsh's rsync completion and adds xsync's extensions.
The manual is generated from the built executable's `--help`.

For a local Homebrew tap, generate the source archive and formula from this checkout:

```sh
python3 tools/package.py
brew tap-new xsync/local
cp dist/homebrew/Formula/xsync.rb "$(brew --repository xsync/local)/Formula/"
brew install --build-from-source xsync/local/xsync
brew test xsync/local/xsync
```

If the local tap already exists, skip `tap-new`; use `brew reinstall` to replace an
installed copy. The generated formula points to this checkout's source archive
and builds its hash-checked vendored dependencies. No public tap is published.
Release helpers already present in `dist/` are included under
`share/xsync/releases/` for explicit remote installation.

## Release binaries and explicit remote install

Build on macOS with CMake 3.24+, Ninja, a C/C++ compiler, GNU make and Docker
(with Linux amd64/arm64 emulation available):

```sh
cmake --preset release-static
cmake --build --preset release-static
```

The preset creates `dist/xsync-linux-amd64`, `dist/xsync-linux-arm64` and
`dist/xsync-darwin-universal`, plus a SHA-256 manifest. Linux uses musl and is
fully static; macOS contains both architectures and links only Apple system
libraries. zstd, xxHash and ICU source archives are vendored and hash checked,
including ICU's Unicode name comparison support. Linux outputs run without
installed runtime dependencies. A Linux build host can produce the two Linux
outputs; producing the macOS universal output requires macOS. `--version`
includes the source Git revision (`-dirty` for modified application sources). Exported source trees can pass
`-DXSYNC_GIT_HASH=REVISION` to CMake.

```sh
build/xsync --install sanjee@neo.local
build/xsync --install user@host --force  # explicitly replace a newer version
```

`--install HOST` probes the host's OS and architecture, chooses the matching
release, and atomically installs it at `~/.local/bin/xsync`. It refuses newer or
unrecognized existing versions unless `--force` is given. An interrupted or
invalid upload leaves the previous executable intact. Release files are searched
beside the local executable, in its sibling `dist/`, or in
`../share/xsync/releases/`; `XSYNC_RELEASE_DIR` explicitly selects another directory.
Only the install command uploads an executable; transfers never install one.

Normal transfers search the remote PATH for `xsync`, then `~/.local/bin/xsync`,
then the executable named by `XSYNC_REMOTE_PATH` (local environment first,
otherwise the remote environment). That path can contain spaces or begin `~/`.
An explicit `--rsync-path` supplies the remote command and bypasses this lookup.

Remote paths accept bracketed IPv6 (`user@[::1]:path`); the brackets are removed
before invoking SSH. An empty remote path (`host:`) means its current directory.
Multiple pull sources can use `host:first :second` to reuse the host. Colons in
the path, including `host:dir/a::b` and local `./a::b`, remain filename characters.
Daemon detection applies to the host separator (`host::module`) or an rsync URL.
The parser's host/user choices are checked against
[rsync's implementation](https://github.com/RsyncProject/rsync/blob/v3.4.1/options.c#L2893).

## Protocol compatibility

The current protocol is **4**. Each release supports its current protocol N and
N-1, so this release also supports **3**. A client retries a protocol-3 peer
before transfer begins; an older protocol-3 client can use the new server. The
protocol-3 option layout stays frozen. Versions outside that window delegate to
rsync unless fallback is disabled.

Protocol 4 advertises feature bits in both Hello messages and uses their
intersection. Unknown feature bits are ignored. The core transfer format is
required; compression, identity mapping and safe-link filtering have distinct
bits. If compression is unavailable, both sides send plain data. Requested
safe-link or user/group mapping semantics are never silently dropped: missing
support fails before transfer (or invokes rsync when fallback is enabled).
Receivers reject compressed or identity-map frames that were not negotiated.
Protocol-3 peers use their known baseline feature set and receive the historical
Hello response without new fields.

Future optional frames/options must be gated by an agreed feature bit; they must
not change the protocol-3 layout or add unnegotiated fields to the baseline Hello.
When the compatibility window advances, keep a frozen N-1 peer fixture and prove
both old-client/new-server and new-client/old-server transfers with fallback off.

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
python3 tests/protocol_test.py                            # frozen N-1 and feature subsets
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
