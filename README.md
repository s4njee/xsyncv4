# xs (xsyncv4)

A fast, parallel rsync work-alike in C++20. Same command line as rsync, a modern live
progress display, and an engine built for trees of many small files.

```sh
xs -a  src/ dst/                      # local
xs -az src/ user@host:/backup/src/    # push over ssh
xs -az --delete host:/data/ data/     # pull, mirroring deletions
xs -a --progress src/ dst/            # live per-file + whole-transfer progress
xs src/                              # list immediate local entries
xs -r host:/data/                     # list remote entries recursively
```

## Build

Needs Python 3, a C++20 compiler, CMake, zstd, xxhash and ICU (`brew install zstd xxhash icu4c` /
`apt install libzstd-dev libxxhash-dev libicu-dev`). ICU supplies Unicode filename comparison.

```sh
cmake -S . -B build -G Ninja && cmake --build build
```

The executable is named `xs` in every build and installation. The existing
`XSYNC_*` environment variables and `xsync/config` defaults remain supported.
The development binary is `build/xs`. It builds on macOS and Linux (checked with clang 21 and
gcc 12). Native remote transfers use a common supported xs protocol on both machines
(`--rsync-path=/path/to/xs` if it is not on the remote `PATH`). If the remote
helper is missing or has no supported protocol in common, xs re-executes a real
rsync from PATH with one stderr notice. Unsupported rsync options and daemon
URLs also use this fallback before any transfer. It never installs a helper.
Use `--no-fallback` or `XSYNC_FALLBACK=0` for strict native-only operation;
`--fallback` overrides that environment setting. Transfer failures and malformed
protocol data do not fall back. Original rsync arguments are retained, including
an explicit `--rsync-path`: that command must support rsync if fallback is needed.
Worker, clone and atomic extensions are stripped before invoking rsync.

## Product page and docs

The product page and VitePress manual live in [sites/xsync](sites/xsync/README.md).
The [hosted manual](https://xsync-transfer.s4njee.chatgpt.site/docs/) includes command
examples, option reference, actual captured output, and development status.

```sh
cd sites/xsync
npm ci
npm run build
npm run preview
```

Open `http://127.0.0.1:4173/docs/` for the manual or `/` for the product page.
The site retains its command-help snapshot and recordings so it builds without
compiling the C++ application. See the site README for refreshing those inputs.

## Personal defaults

GUI integrations can launch `xs --app` for the experimental schema-1 subprocess
interface: local and SSH pane browsing, headless SSH authentication, explicit
local and SSH selected copies with literal destination-name mappings, live
progress and item outcomes, revision-bound conflict decisions, scoped policies,
keep-both names, acknowledged cancellation, revision-checked filesystem actions,
safe moves with verified copy/remove outcomes, and opt-in private local/SSH
partials with explicit verified-prefix resume, guarded cleanup and confirmed
safe pause checkpoints. Directory/symlink receipts, source type changes, saved
conflict decisions and keep-both mappings are guarded across recovery attempts. It bypasses
personal CLI defaults and never falls back to rsync. See the
[machine contract](docs/app-protocol.md) and [reference client](tools/app_client.py).
The [reference queue journal](tools/app_queue.py) persists copy selections,
profile references, recovery IDs and authoritative outcomes; unfinished attempts
use helper quiescence and read-only inventory/destination verification before
an explicit restart resume. Missing results remain unconfirmed and cancel intent
survives lost acknowledgements. Explicit failed-file/symlink retries preserve
nested destination mappings and save their admission across restart; replacements
ask for a fresh conflict decision. Opt-in bounded reconnects require engine proof
that no copy request was submitted and survive queue restart with their remaining
budget. An additional opt-in policy reconciles disconnected private SSH copies
before resuming: helpers must be quiet and inventory/destination guards must pass.
Capable engines accept a queue-reserved private ID saved before copy submission,
so losing every initial receipt still leaves an inspection target.
Missing results remain unconfirmed; cancellation prevents automatic recovery.
Regular-file publication intents allow guarded reconciliation after rename when
the final receipt is lost. Directory retry and remaining creation/publication
gaps remain in progress. Read-only local/SSH destination preflight reports
filesystem capacity, detectable name/metadata constraints and an optional exact
advisory budget for regular files and atomic staging. Unknown physical storage
and quota requirements remain explicit; preflight does not authorize a copy.
Copy/resume refresh hints identify mapped destination items and conservatively
invalidate the destination tree when completion receipts are lost. The reference
pane view rejects late navigation events after invalidation and routes SSH hints
using the job's saved profile.
Read-only local/SSH transfer previews report selected-copy or mirror proposals,
reasons, conflicts and stat-verified source budgets. Complete selected-copy
previews can guard copy admission against changed inventories. Mirror deletion
execution and SSH revision handoff remain open. Local guarded copies also check
saved source/destination revisions through planning and publication, including
conflict replies and directory metadata restoration;
preview itself never writes or authorizes deletion.
Engine/reference-client P0 and P1 acceptance is tracked in [the GUI backlog](backlog-gui.md).

For scalar options and on/off flags, precedence is **command-line flags, then
environment, then config**. Within one layer, the last value wins. Repeatable
options such as filters accumulate from config, then environment, then flags;
`--filter='!'` clears earlier
filter rules. Progress defaults to enabled when stderr is a terminal and
disabled when stderr is redirected or piped.

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
`XSYNC_PROGRESS=0` disables progress and `XSYNC_PROGRESS=1` enables it,
overriding config and `XSYNC_OPTS`; explicit `--progress`/`--no-progress` wins.
`XSYNC_PROGRESS=auto` leaves config/options and the terminal default in effect.
`--quiet` suppresses progress along with other non-error messages.
Fallback passes the effective defaults and original transfer arguments to rsync
after stripping extensions for xs. `--help`, `--version` and protocol-server
invocations bypass personal defaults; servers use the client's wire options.

## Install locally

Install the built executable, generated man page and zsh completion into a prefix:

```sh
cmake --install build --prefix "$HOME/.local"
```

Add that prefix's `bin` to `PATH`. For zsh, put
`fpath=("$HOME/.local/share/zsh/site-functions" $fpath)` before `compinit` in
`.zshrc`. The completer uses zsh's rsync completion and adds extensions for xs.
The manual is generated from the built executable's `--help`.

For a local Homebrew tap, generate the source archive and formula from this checkout:

```sh
python3 tools/package.py
brew tap-new xs/local
cp dist/homebrew/Formula/xs.rb "$(brew --repository xs/local)/Formula/"
brew install --build-from-source xs/local/xs
brew test xs/local/xs
```

If the local tap already exists, skip `tap-new`; use `brew reinstall` to replace an
installed copy. The generated formula points to this checkout's source archive
and builds its hash-checked vendored dependencies. No public tap is published.
Release helpers already present in `dist/` are included under
`share/xs/releases/` for explicit remote installation.

## Release binaries and explicit remote install

Build on macOS with CMake 3.24+, Ninja, a C/C++ compiler, GNU make and Docker
(with Linux amd64/arm64 emulation available):

```sh
cmake --preset release-static
cmake --build --preset release-static
```

The preset creates `dist/xs-linux-amd64`, `dist/xs-linux-arm64` and
`dist/xs-darwin-universal`, plus a SHA-256 manifest. Linux uses musl and is
fully static; macOS contains both architectures and links only Apple system
libraries. zstd, xxHash and ICU source archives are vendored and hash checked,
including ICU's Unicode name comparison support. Linux outputs run without
installed runtime dependencies. A Linux build host can produce the two Linux
outputs; producing the macOS universal output requires macOS. `--version`
includes the source Git revision (`-dirty` for modified application sources). Exported source trees can pass
`-DXSYNC_GIT_HASH=REVISION` to CMake.

```sh
build/xs --install sanjee@neo.local
build/xs --install user@host --force  # explicitly replace a newer version
```

`--install HOST` probes the host's OS and architecture, chooses the matching
release, and atomically installs it at `~/.local/bin/xs`. It refuses newer or
unrecognized existing versions unless `--force` is given. An interrupted or
invalid upload leaves the previous executable intact. Release files are searched
beside the local executable, in its sibling `dist/`, or in
`../share/xs/releases/`; `XSYNC_RELEASE_DIR` explicitly selects another directory.
Only the install command uploads an executable; transfers never install one.

Normal transfers search the remote PATH for `xs`, then `~/.local/bin/xs`,
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

## Listing sources

A single source argument lists metadata instead of copying. A directory argument
without a trailing slash lists that entry; a trailing slash lists `.` and its
immediate contents. Use `-r` (or `-a`) to include descendants. Listings show type,
permissions, byte size, local modification time and escaped names; `-l` adds
symlink targets. `-h`/`-hh` select readable sizes and `--no-h` removes digit
separators. Filters, `-L`, `--no-dirs` and quiet mode apply.

`--list-only SRC [SRC]... DEST` also lists, leaving DEST untouched. It supports
multiple sources, merges duplicate directory arguments, ignores transfer-only
flags, and reads no regular-file contents. Listing statistics report zero
transfers/creations/deletions; an explicit log file records the same stdout.
Remote listing requests `PF_LIST` (512) with the sender role and receives only
validated metadata and a counted completion. No transfer receiver is created.
Peers without native listing use rsync fallback, or fail with code 4 in strict
mode. The frozen protocol-3 options and ordinary transfer layout are unchanged.

## Protocol compatibility

The current protocol is **4**. Each release supports its current protocol N and
N-1, so this release also supports **3**. A client retries a protocol-3 peer
before transfer begins; an older protocol-3 client can use the new server. The
protocol-3 option layout stays frozen. Versions outside that window delegate to
rsync unless fallback is disabled.

Protocol 4 advertises feature bits in both Hello messages and uses their
intersection. Unknown feature bits are ignored. The core transfer format is
required; compression, identity mapping, safe-link filtering and verified-prefix
resume and structured file output have distinct bits. If compression is unavailable, both sides send plain data. Requested
safe-link or user/group mapping semantics are never silently dropped: missing
support fails before transfer (or invokes rsync when fallback is enabled).
Receivers reject compressed or identity-map frames that were not negotiated.
Protocol-3 peers use their known baseline feature set and receive the historical
Hello response without new fields.

`--bwlimit=RATE` caps each remote writer's serialized bytes after compression.
Bare numbers are KiB/s; fractional numbers and `K`/`M`/`G`/`T`/`P`, `KiB`/`MiB`
or decimal `KB`/`MB` suffixes are supported, rounded to the nearest KiB/s.
Zero disables the limit; nonzero rates below 512 bytes/s are rejected. The
token bucket accumulates at most 0.1 seconds or 16 KiB. Local copies share one
bucket across workers and limit bytes written; a limit disables APFS cloning.

`--timeout=SECONDS` bounds remote idle I/O, including initial shell/hello waits,
partial frames, blocked writes and a shell that stays alive after protocol EOF.
It uses integer seconds; zero disables the deadline. Timeouts clean up atomic
outputs using the usual `--partial` policy and exit 30. A local copy has no
remote connection deadline. Negotiated empty keep-alive frames preserve live
connections during scans, checksums and disk work. They are sent at most every
10 seconds, shortened to one third of a nonzero timeout (minimum 0.1 seconds).
Sending one's own keep-alive never extends an idle peer deadline, and incoming
heartbeats cannot extend a blocked writer's deadline.

`PF_IO_CONTROL` (1024) gates a separate bandwidth/timeout configuration and
keep-alives; the frozen v3 options remain unchanged. A requested nonzero limit
or timeout against a peer without this feature falls back to rsync, or fails
before transfer with code 4 in strict mode. Ordinary transfers still negotiate
their common features with older peers.

With `--partial`/`-P`, current peers hash an existing destination prefix with
XXH3-128 on both sides and send only the remaining bytes when the hashes match.
The receiver rechecks the prefix while copying it into the atomic output file;
a concurrently changed prefix fails instead of publishing mixed data. A prefix
that does not match the source is discarded as a resume candidate and the file
is sent in full. Local byte copies use the same verification. Interrupted
outputs retain only their fully written contiguous prefix, with holes from
unfinished out-of-order chunks removed. Existing `--inplace` files retain their
length on interruption; an already verified partial prefix can be reused.
Files up to 512 KiB use the whole-file path. Peers without the resume feature,
including protocol 3, keep the historical full-file format and transfer the
whole file; no new fields are added to their wire messages.
`-W`/`--whole-file` disables resume; `--no-whole-file` enables it again.

`--out-format` supports `%i` (itemization), `%n` (transfer-relative name, with a
trailing slash for directories), `%L` (symlink target), `%l` (source length),
`%o` (`send`, `recv`, `del.`), `%f` (long source name on a sender, short name on
a remote pull), `%b` (file-content bytes transferred), `%t` (local date/time)
and `%%`. Optional field widths such as `%-40n` and `%12l` pad with spaces.
`%b` counts content before compression, excluding framing; a resumed transfer
counts only the remaining tail, and clones, metadata updates and dry runs count
zero. This differs from rsync's protocol-specific byte accounting.

When stdout is a pipe or file, file events are buffered until the transfer ends
and sorted by transfer-relative path. A terminal receives events as they finish.
Progress stays on stderr. `--log-file=FILE` appends exactly the same stdout
stream, including summaries, without timestamps or prefixes added to the log.
An empty output format suppresses file lines; `-q` suppresses the stream.
When an output consumer closes its pipe (for example, `xs -av SRC DEST | head`),
xs stops active copying, cancels the remote peer and exits 13 with a stderr
diagnostic. Cleanup follows the usual interruption policy: temporary outputs
are removed, or `--partial` retains the completed prefix for a later resume.
Silent transfers do not require a stdout reader. Other stdout write failures,
including a full output device, also return 13.
Transfer errors end with a stderr error count and the first ten diagnostics, grouped
by exit-code kind, before the existing exit-code line. Quiet mode retains errors.
Remote completion codes do not duplicate errors already reported by the peer;
zero-code notices are excluded. Summary examples escape control bytes. These
diagnostics do not enter stdout or the transfer log.
Control bytes other than tabs are escaped as `\\#ooo`; valid UTF-8 is retained. Invalid
high bytes are escaped unless `-8`/`--8-bit-output` is set.

Structured events and display-only source paths use a negotiated feature bit.
An explicit format or log request against a peer lacking that feature delegates
to rsync before any destination writes, or fails with code 4 in strict mode.
Ordinary `-v`/`-i` output still works with older peers using their plain messages.

Directory display lengths/source paths and output configuration have a separate
`PF_DIR_OUTPUT` bit. After Hello agrees that feature, a four-byte configuration
frame selects attribute reporting, repeated itemization, `--mkpath` and the
`--delete-before` itemization convention. Unsupported or malformed configuration
fails before the receiver creates its destination. Current formatted-output and
`-ii` requests require that feature; the protocol-3 layout remains frozen.
`-ii` includes unchanged entries, while `-i` reports updates. Nanosecond-only
mtime restoration under checksum mode does not invent a seconds-based item flag.

`-H` negotiates `PF_HLINK` only when requested. It adds source device/inode/link
count/change-time fields to directory entries and fresh file metadata, and a
hard-link-target flag to structured output. Old peers receive none of these
fields; missing support falls back or fails with code 4 before destination writes.
The frozen Hello options and four-byte output configuration remain unchanged.

With `-H`, selected regular files, symlinks and special files retain their source
hard-link groups, including groups spanning directories. Each selected member
is independently validated/copied before the receiver joins successful members
with verified temporary links. This first implementation can copy/send duplicate
contents; `%b` still reports the actual bytes copied for each member. Link
creation pins the selected object and both receiver-owned parent directories,
checks inode and type, and publishes atomically. Directory times are restored
once linking and deletion finish. Links outside the selected source list are
not recreated. `hf`, `hL` and `hS` records and `%L` distinguish hard-link targets
(` => `) from symlink targets (` -> `), including repeated itemization.

Future optional frames/options must be gated by an agreed feature bit; they must
not change the protocol-3 layout or add unnegotiated fields to the baseline Hello.
When the compatibility window advances, keep a frozen N-1 peer fixture and prove
both old-client/new-server and new-client/old-server transfers with fallback off.

Local byte copies and remote transfers above 1 MiB can match blocks from an existing regular
destination (at least 1 KiB). A rolling weak checksum finds candidates; XXH3
checksums verify matched blocks and the completed file. The matcher keeps one
block plus 1 MiB of source data, emits bounded literal batches and consecutive
block runs, and recognizes inserted, deleted and moved data. `-W` disables it;
verified-prefix resume takes priority when `--partial` finds a matching prefix.
APFS clones continue to take priority over byte copying.

The basis is opened through the destination anchor without following child
symlinks. With `--inplace`, an anonymous basis snapshot preserves moved blocks
while the original destination inode is updated. Source changes retry once;
unverifiable basis blocks fail with code 23. A final checksum mismatch prevents
publication and retention of the atomic output. `--stats` reports successful
delta literal/matched data; `%b` reports literal source bytes for delta copies.
Remote matching uses negotiated feature `PF_DELTA` (256): NEED carries basis
eligibility, and the sender requests block signatures only after a resume prefix
fails verification or is unavailable. Signatures and literal data can use zstd;
block references are bounded and each attempt ends with a whole-file checksum.
An abandoned delta attempt must finish draining before an inplace retry starts.
Peers without this feature continue with their supported whole-file/prefix path.
Tests compare total bytes in both directions, including signatures and framing,
against rsync on edited 64 MiB and 2 GiB files, with a maximum ratio of 1.20.

## Benchmark

Current SSH measurements use neo (Raspberry Pi 5, ext4) and freya (Ryzen 7950X,
ZFS), each with a 1 Gb/s NIC. Source revision `415900091024`, three samples per
tool, alternating order; every sample passed a checksum rsync dry run. These
runs retain existing OS caches. Cold-cache, reverse full-corpus and 1% update
results are pending.

| Dataset / direction | Flags | rsync median | xs median | Speedup |
|---|---|---:|---:|---:|
| 10,002 files, 578 MB, neo → freya | `-a` | 5.422 s | 5.388 s | 1.01× |
| 10,002 files, 578 MB, freya → neo | `-a` | 5.455 s | 5.249 s | 1.04× |
| 10,002 files, 578 MB, neo → freya | `-az` | 3.538 s | 3.149 s | 1.12× |
| 10,002 files, 578 MB, freya → neo | `-az` | 3.548 s | 2.777 s | 1.28× |
| Two files, 2 GiB, neo → freya | `-a` | 18.716 s | 18.795 s | 1.00× |
| Two files, 2 GiB, freya → neo | `-a` | 18.605 s | 18.625 s | 1.00× |
| Two files, 2 GiB, freya → neo | `-az` | 11.607 s | 9.652 s | 1.20× |
| One file, 19 bytes, neo → freya | `-a` | 0.186 s | 0.163 s | 1.14× |
| One file, 19 bytes, freya → neo | `-a` | 0.159 s | 0.166 s | 0.96× |
| Full Congress, 10.53 GB, neo → freya | `-a`, fresh | 122.717 s | 125.154 s | 0.98× |
| Full Congress, 10.53 GB, neo → freya | `-az`, fresh | 153.572 s | 117.980 s | 1.30× |
| Full Congress, 10.53 GB, neo → freya | `-a`, no-op | 19.536 s | 26.372 s | 0.74× |
| Full Congress, 10.53 GB, neo → freya | `-ac`, no-op | 121.693 s | 53.476 s | 2.28× |

The available data-only Congress snapshot contains 914,106 files, 417,408
directories and 10,528,134,423 logical bytes (10.53 GB), rather than the
historical 14 GB estimate. A separate update fixture changes 9,141 files.
See [benchmark instructions](benchmarks/README.md) and the
[complete result table and JSON evidence](benchmarks/results/20261010T144748Z-715fa0-summary.md).
`bench/bench.py --target host:absolute-root` runs the SSH harness.

APFS `-rt` and `-rlt` use file and eligible directory clones, then
correct omitted permissions and selected ownership. On a busy M1 Max, five
samples per tool showed a 1 GiB read-only file dropping from about 0.30 s to
0.008–0.009 s, and a 1,000-file tree from about 0.29 s to 0.04 s. Every sample
matched rsync data and metadata. These results come from a 98%-full volume;
see [the measured comparison and caveats](benchmarks/results/20261010-f11-clone-modes-summary.md).

Missing compatible APFS subtrees can now clone in one transaction, limited to
4,096 descendant entries and 32 levels. Oversized or incompatible trees fall
back to ordinary walking, which can clone eligible smaller children. In the
six-sample leaf-only comparison, bounded cloning uses less CPU in all cases;
`-rlt` wall medians improve by 3–12%, while `-a` remains 6–15% slower.
See [the full comparison and host limits](benchmarks/results/20261010-f10-parallel-summary.md).


### Historical local baseline

`bench/bench.py`, 3 runs per tool, best time shown. Corpus: the 109th Congress slice of the
congress data (76,838 files in 19,073 directories, 494 MiB of content, average file 6.4 KiB),
copied on an M1 Max to the same APFS volume. rsync is 3.4.4 from Homebrew.

These baseline numbers predate the P0 trust fixes and the atomic-write default.
Rerun the benchmark when comparing the current binary's performance.

| scenario                        | rsync   | xs      | speed-up |
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
  (or at least `-pt`). Current per-file clones also support `-rt` and `-rlt`,
  correcting omitted permissions before publication. Across volumes, or with
  `--no-clone`, these historical measurements used the byte-copy path.
- `-z` is accepted but does nothing for a local copy: there is no wire to compress for.
  rsync does compress and decompress locally, which costs it nothing here because
  creation dominates.
- A destination filesystem that scales with threads (ext4, XFS) should favour xs's
  parallel receiver more than APFS does; that has not been measured here.

## How it gets its speed

- **Parallel scan.** Directories are listed with `getattrlistbulk` (names and attributes in
  one call per directory, no per-file `stat`) by a pool of threads; source and destination
  listings are merge-joined to decide what to do.
- **Parallel transfer.** Files are copied by a thread pool in batches per directory. The
  scan runs ahead of the copy, while queued transfers take priority once the
  backlog grows. Local copies switch priority at 512 batches of up to 64 files.
- **Copy-on-write clones.** On APFS, a local copy with `-a`, `-rt` or `-rlt` clones files
  instead of copying bytes, then applies the requested mode and ownership. An
  eligible new subtree is cloned in a single call after its inventory is checked
  against the 4,096-entry and 32-level limits.
  Clones are independent files sharing storage until one is modified. Disable with
  `--no-clone`.
- **A pipelined wire protocol.** Over ssh the sender streams directory listings, the
  receiver answers with the files it needs, and data flows in ~1 MB blocks that pack many
  small files together. Blocks are zstd-compressed (`-z`) and decompressed on multiple
  threads, checksummed with XXH3, and written by a thread pool. Listing, reading,
  compressing and writing all overlap.
  Peers that negotiate the optional directory-child count release a receiver
  directory record after its requested files and children finish. Active worker
  tasks retain their own references. Older peers keep the original wire layout
  and release completed records after the end of the file list. Final directory
  metadata and deletion plans remain retained until tree finalization.

## Progress display

Progress is enabled by default when stderr is a terminal. `--no-progress` or
`XSYNC_PROGRESS=0` disables it. `--progress`, `-P` or `--info=progress2` enables
it explicitly, including when stderr is redirected. The display shows up to four detail rows and a bar
for the whole transfer. Files receive a row after 200 ms in flight; faster files
share one `small files` row with a completion rate. Longer transfers show their
own speed and ETA. Remote pulls retain the same file record across chunks and
worker changes:

```
  data/archive.dat                       240M ━━━━━━╸───── 54% 18.2M/s ETA 0:06
  small files  46,869 · 12.9k files/s
 ━━━━━━━━━━━━━━━━━━╸━━━━━━━━━━━  61%  46,870/76,838 files  · 301M/494M  · 84.7M/s  · 12.9k files/s  · ETA 0:02
```

Whole-directory APFS clones show `cloning path/` immediately, even for quick
operations. The total line counts completed directories, and the completion
line reports how many directories were cloned. Planned file/byte counters
advance with each directory and are reversed if a clone falls back to copying.
Display updates are limited to roughly 16 frames per second.

On a push, the total bar follows receiver acknowledgments after successful
writes. It stays below 100% until the files are completed on the receiver;
`sent … wire` reports the separately measured bytes sent, including compressed
data and protocol overhead. Resume prefixes and reconstructed delta blocks
count as logical file progress. Retried/aborted writes are removed from the
acknowledged count. Older helpers that lack this optional protocol-4 capability
keep the bar at zero until they report successful completion, while still
showing sent wire bytes.

With `-z`, the total and completion lines show wire rate and the DATA payload
compression ratio (raw record bytes divided by transmitted record bytes,
including compression framing). Incompressible blocks report about `1.0x`.
`-vv` adds a limiting-stage estimate: `reading`, `network`, or `writing`,
both live when space permits and in the final verbose summary. It compares
cumulative service time measured on the two sides; parallel stages can overlap,
so this is an estimate. Read time includes source reads and compression, network
time includes transport waits and requested pacing, and write time includes
receiver DATA processing. Current helpers exchange these optional metrics;
older helpers continue transferring without a stage estimate.

Checksum hashing shows `verifying N checks`; successful source and destination
hashes each count as a check. Deletion shows `deleting N`, with the count of
removed entries. A push waiting for final writes or cleanup shows
`waiting for receiver`, retaining acknowledged progress and sent wire bytes.
Waiting for a pull helper to exit shows `waiting for sender`. Current helpers
send optional, bounded phase snapshots; older helpers remain compatible with
the client's local phases and wait label. JSON records include `phase`,
`verified` and `deleted` counters.

Native dry-run transfers (`-n`) always end on stdout with
`would transfer N files (X), delete M`, even without `-v`. This counts regular
files needing data and their logical size; deletion counts include directories
and their entries. `--quiet` suppresses the plan summary. Push totals come from
the receiver's virtual plan, including replacements of existing files. A helper
without dry-run total acknowledgments delegates before transfer or fails in
strict mode; `-n --quiet` can still use such a helper without a summary. Rsync
fallback uses rsync's own dry-run output.

Size units use one base throughout progress, wire rates, dry-run plans and
summaries: decimal (1000) by default and with `-h`, binary (1024) with `-hh`.
Progress and plans use compact `K`/`M`/`G` amounts; ordinary summary counters
retain full integers unless `-h` is requested. For example, 1,048,576 bytes
appears as `1.05M` with decimal units or `1.00M` with `-hh`. Values below the
chosen base remain unscaled. JSON always retains raw integer counts and bytes.

Progress uses stderr. The live display is used on terminals; explicit
`--progress` prints one plain line per second on pipes. `--info=progress2`
uses rsync's byte/percent/rate/time and `(xfr#N, to-chk=R/T)` line shape on
pipes, with `ir-chk` while scanning; the final line is always printed.
`--progress=json` emits newline-delimited JSON on stderr, on both terminals
and pipes, without cursor escapes. `progress` records contain elapsed
milliseconds, completed/planned files and bytes, files seen, wire bytes,
scanning and dry-run flags. `file` records identify each transferred regular
file (including clones and hard-link aliases), its itemization code, size and
literal bytes; they are emitted after the destination operation succeeds,
or represent planned operations in dry runs. `complete` records include final
counters, success and an exit code (null if cleanup precedes the fatal code).
All JSON counters are raw integers. `path` retains valid UTF-8; control bytes
are JSON-escaped and invalid bytes are represented as Unicode byte values.
`path_bytes_hex` preserves the original path bytes exactly. JSON remote
transfers require a helper with structured file events; rsync fallback cannot
provide JSON and fails clearly. Ordinary stdout remains available for `-v`,
`-i`, formats and stats. The last progress-mode option wins; `--no-progress`
or `--quiet` suppresses events.
`-v` and `-i` lines scroll above the live region. `NO_COLOR` is honoured.
The renderer respects the actual terminal width, including very narrow windows,
and redraws after `SIGWINCH`. Bars use the terminal's foreground color so they
remain readable on light backgrounds. `TERM=dumb` receives plain ASCII lines
without cursor escapes. Non-UTF-8 locales use ASCII bars and escaped filenames;
UTF-8 names are clipped by display columns, with control bytes escaped even under
`-8`. The terminal verification checklist is in [tests/progress-terminal.md](tests/progress-terminal.md).

On a live terminal, Ctrl-Z clears the display and restores the cursor before
suspending all threads at the next progress refresh. `fg` redraws using the
current window size. A shared signal-safe cursor hook covers normal returns,
worker failures, cancellation and repeated interrupts; JSON and plain pipe
output never acquire a hidden cursor.

## Compatibility with rsync

Supported with rsync's meaning: `-a -r -d -H -X -A -E -U -R -0 -l -L -p -t -g -o -D -O -J -n -u -c -I -x -z -v -q
-i -h -P -e -f`, `--delete` (and `--del`, `--delete-before/-during/-after/-delay`),
`--delete-excluded`, `--force`, `--exclude`, `--include`, `--exclude-from`,
`--include-from`, `--files-from`, `--relative`, `--from0`, `--filter` (`+`/`-`, `H`/`S`, `P`/`R`, `!`, and modifiers
`! / s r p x`), `--existing`, `--ignore-existing`,
`--ignore-errors`, `--max-delete`,
`--size-only`, `--modify-window`, `--max-size`, `--min-size`, `--inplace`, `--partial`,
`--mkpath`, `--numeric-ids`, `--rsync-path`, `--compress-level`, `--stats`, `--progress`,
`--no-OPTION` forms, trailing-slash semantics, multiple sources, `host:path` and
`user@host:path` on either side, and rsync's exit codes.

Differences to be aware of:

- **Not wire-compatible.** xs speaks its own protocol, so it needs xs on both ends
  and delegates rsync daemon transfers (`host::module`, `rsync://`) to rsync.
- **Large local and remote transfers reuse verified blocks** from an existing
  destination. `-W` requests whole-file transfers; APFS cloning remains preferred
  for eligible local copies.
- **Large Linux local copies use kernel acceleration.** Files of at least 1 MiB
  on btrfs/XFS try a reflink with `FICLONE`, then same-device
  `copy_file_range`, before falling
  back to byte copying. Short copies, interrupted calls and unsupported operations
  retain the correct offset. `--no-clone`, sparse copies and bandwidth limits
  use the byte path. Source consistency checks and output metadata finalization
  still apply. With explicit `-jN` (`N > 1`), files with at least 32 MiB remaining
  also spread disjoint ranges across the configured worker pool when the directory requests one large file
  (local byte copies use at most two range workers);
  multiple large files retain file-level parallelism to avoid inode contention.
  Automatic worker selection keeps file-level parallelism: cached single-file
  byte copies can slow down with ranges, while compression overlap can benefit.
  Native transfers parallelize reads and
  receiver writes while retaining source retries and partial-prefix verification.
  Sparse and delta receiver writes stay serialized. macOS disables data caching on source and output descriptors for
  copies of at least 1 GiB with `F_NOCACHE`.
- **Compression is opt-in with `-z`.** Large blocks are sampled before compression;
  incompressible blocks travel raw. The automatic zstd level starts at 1 and
  follows the link only while the link is the bottleneck, that is, while
  frames queue behind the transport: after a second of such writing below
  64 MiB/s it rises to 3, and below 8 MiB/s to 6. It falls back a step as soon
  as the link proves fast or the queue empties, because a sender that cannot
  keep the link busy is limited by compression and a costlier level only slows
  it; a rise that had to be undone is not retried for ten seconds. `-vv`
  reports the level that compressed the most data, with the split when there
  was more than one. `--compress-level=NUM` fixes the level. `--skip-compress=gz/jpg/mp[34]` replaces the default compressed-media
  suffix list; an empty list disables suffix skipping. Matching is case-insensitive,
  and skipped files stay raw even beside compressible files in a shared batch.
  This implements the suffix syntax in the
  [rsync manual](https://download.samba.org/pub/rsync/rsync.1#skip-compress),
  whose current codecs ignore per-file skip requests. Custom suffix policies
  for pulls require a capable native peer; older peers use rsync fallback.
- **New byte-copied files are atomic by default.** Files are written to temporary
  names and renamed after verification. `--no-atomic` saves a rename for new files,
  but a crash can leave a truncated file under its final name. `--inplace` explicitly
  requests direct writes. APFS clones already create a content snapshot.
- **Receiver paths are anchored to directories.** Descendant symlinks are never
  followed by writes, metadata operations or cleanup. `--safe-links` skips links
  outside the transfer tree and protects their existing destination entries from
  deletion. The explicit destination path is resolved once at setup.
- **Clones carry extended attributes, ACLs, access and creation times** along,
  which `rsync -a` (without `-X -A -U -N`)
  does not. Use `--no-clone` if that matters.
- **Output order.** File lines are sorted by path when stdout is not a terminal.
- **Extended attributes.** `-X`/`--xattrs` copies xattrs on files, directories
  and supported symlinks. `-XX` also copies rsync internal attributes. Attribute-only
  updates and per-file APFS clones apply the same attribute selection as byte copies.
  Whole-directory clones are disabled with `-X` so every entry is handled individually.
  Local and remote transfers support xattrs. Helpers without the xattr and streaming capabilities
  delegate before destination writes, or refuse in strict mode. Cached attribute
  values share an 8 MiB memory budget and spill into an unlinked temporary file.
  Large macOS resource forks use descriptor I/O and remote 64 KiB chunks; other
  attribute APIs may still require one contiguous value during a read or write.
  Temporary storage must have space for the cached values. Linux privileged
  namespaces also transfer on supported symlinks and special inodes. Ownership
  updates restore selected Linux file capabilities.
- **Access control lists.** `-A`/`--acls` transfers preserve macOS extended
  ACLs and Linux access/default ACLs, including ACL-only updates and per-file
  clones. `-A` implies `--perms`; `--no-perms` retains rsync's permission behavior.
  ACLs are handled independently of `-X` attribute filters. Physical symlink
  ACLs are skipped; `-L` preserves the referent's ACL. Native remote transfers
  require matching ACL styles; older helpers and transfers between macOS and
  Linux delegate before destination writes, or refuse in strict mode. ACL
  principals map by user/group name even without `--owner`/`--group`;
  `--numeric-ids` retains numeric identities. Darwin transfers also preserve
  unresolved UUID principals, synchronization rights and global inheritance
  flags that rsync may reject or omit. UUID principals retain their UUIDs,
  including with `--numeric-ids`; remote Darwin ACLs require the UUID capability.
  Rsync itself rejects the tested nontrivial Darwin/POSIX ACLs in both cross-platform
  directions, so fallback does not guarantee cross-platform ACL conversion.
  As with rsync, a remote push's
  receiver re-enables `--perms` for `-A`, including after `--no-perms`.
- **Executability.** `-E`/`--executability` preserves whether existing regular
  files are executable when `--perms` is off. A non-executable source clears
  execute bits; an executable source adds execute rights for destination read
  classes only when the destination has no execute bits. Other destination
  permissions are retained, including when a byte copy does not need a readable
  basis (rsync may treat an unreadable replacement as new). New files use the
  usual source mode and umask. `--perms` takes precedence, and `-a` does not
  imply `-E`. Physical symlinks, directories and special inodes are unaffected;
  `-L` applies it to regular referents. Older helpers delegate or refuse before
  writes when `-E` requires its negotiated capability. This follows modern
  rsync's executability meaning; Apple's system rsync uses `-E` for extended
  attributes, for which xs uses `-X`. Fallback retains the original arguments,
  so system rsync's interpretation also applies after delegation; use
  `--executability` for unambiguous fallback.
- **Permission overrides.** `--chmod=CHMOD` changes incoming permissions using
  numeric modes or comma-separated symbolic rules. `D`/`F` restrict rules to
  directories or non-directory files; repeated options append rules. Conditional
  `X` uses the original incoming execution state (and applies to directories).
  Omitted user/group/other classes obey the invoking process's umask. Physical
  symlinks are unchanged. Existing entries still obey `--perms` and regular-file
  `--executability`; without either, their existing modes are retained. Whole
  directory clones are disabled so overrides can be applied per entry. Native
  restrictive directory modes are finalized after children; rsync can instead
  lose pathname access and report a partial transfer when a root loses search
  permission. Remote overrides use existing mode fields and work with protocol 3
  and feature-subset peers; no new wire capability is required.
- **Ownership overrides.** `--chown=USER:GROUP` sets incoming ownership using
  names resolved on the destination host or numeric IDs. Either field may be
  omitted; empty fields preserve the ordinary mapping. Separate repeated
  options may set the user and group once each. Overrides imply the corresponding
  `--owner`/`--group` options and still require the normal filesystem privileges.
  Unknown names warn and leave the ordinary mapping in effect. `--numeric-ids`
  does not disable explicit overrides. With `-A`, overrides also map named ACL
  principals; Linux retains ordered entries when several principals map to the
  same ID. A mapped Darwin deny-delete ACL can prevent publication and report
  exit 23, preserving the previous destination's data.
  Native remote transfers negotiate ownership overrides before writes; older
  helpers delegate or refuse. Explicit helper overrides also require that
  capability, and overlapping client/helper fields fail before writes.
  On a push, the receiver applies requested overrides even after a later
  `--no-owner`/`--no-group`: native transfers retain the source identities needed
  for this. Rsync can instead omit those identities and attempt owner/group 0,
  which may fail without privilege. Local and pull transfers honor those later
  disabling options. Whole-directory clones are disabled for ownership overrides;
  per-file clones apply the requested ownership.
- **Additional times.** `-U`/`--atimes` preserves file and special-inode access
  times; directories and physical symlinks retain rsync's omission. `-UU` also
  enables `--open-noatime`, which requests `O_NOATIME` on systems that provide it
  and may require file ownership or privilege. macOS ignores that read flag.
  `-N`/`--crtimes` preserves creation times on macOS, including directories and
  symlinks. Linux creation-time preservation is unsupported. Both time values
  use whole seconds, as rsync does. `-O`/`-J` omit directory/symlink time writes;
  rsync's creation-time itemization can still report an omitted difference.
  Native remote transfers negotiate these options before writes and older
  helpers delegate or refuse. Whole-directory cloning is disabled when `-U`
  or `-N` needs per-entry handling; file clones correct the requested times.
- **BSD file flags.** `--fileflags` preserves macOS `st_flags` on files,
  directories and special inodes. Physical symlinks are skipped; `-L` preserves
  their referents' flags. Archive mode does not imply it, and `--no-fileflags`
  disables it. Requested flags add a twelfth `%i` character (`f` when changed).
  Flags that block writes or links are applied after publication and hard-link
  creation; existing immutable destinations are not automatically made writable
  for data replacement. Failed or silently ignored flag updates report exit 23.
  File clones retain their flag superset without this option. Whole-directory
  cloning is disabled when flags are requested. Linux refuses native flag
  preservation; older helpers delegate or refuse before writes. Fallback needs
  a flags-capable rsync; standard upstream builds do not include `--fileflags`.
- **Sparse files.** `-S`/`--sparse` creates holes for zero-filled regions on
  local, push and pull transfers, including delta, partial/resumed and in-place
  writes. `--no-sparse`/`--no-S` cancels it. Sparse transfers disable cloning
  and preserve requested metadata and hard links. A bounded allocation pass
  joins zeroes split across delta blocks; it reads allocated extents where the
  file system exposes them. Files without hole-punch support, and write-only
  in-place files that cannot be read for refinement, retain correct bytes but
  may allocate more space. Remote helpers negotiate the option before writes;
  older helpers delegate or refuse in strict mode.
- **Backup snapshots.** `--link-dest=DIR` searches up to 20 previous snapshots
  on the receiver. Relative paths start at the destination directory, including
  an explicitly symlinked destination root. Unchanged files with matching
  requested metadata become hard links; differing metadata and cross-device
  links produce independent copies. Changed files can use a read-only snapshot
  as their delta basis, including with `--inplace`, `-H`, `-X`, `-A` and `-S`.
  Snapshot roots may be explicit symlinks; descendants are traversed without
  following symlinks. Basis reads can advance access times on systems without
  `O_NOATIME`. Unlike rsync's `-U` reuse, differing requested access times require
  an independent copy. An already shared destination retains ordinary update
  semantics: changing its metadata or writing in place can change other links.
  Missing or empty snapshot paths warn and are skipped; newly created
  directories are itemized as new when no basis exists. Native remote helpers
  negotiate snapshot support before writes; older helpers delegate or refuse.
- **macOS edge cases.** Dataless files bypass cloning and use ordinary reads,
  which may ask the file provider to download their content. Immutable existing
  files keep their protection; unsuccessful data replacements report exit 23.
  Unix sockets copy as inactive filesystem nodes, including hard-link aliases
  and long filenames. Socket creation errors are reported. Socket ACLs and
  changes to socket creation times or BSD flags currently report exit 23;
  use rsync for those metadata requests. Source paths beyond `PATH_MAX` report
  a partial transfer with a path-length error. The macOS rsync 3.4.4 reference
  also rejects the tested deep paths.
- **Delegated to rsync** (strict mode rejects them): incompatible remote `-A`,
  `-b`, `--compare-dest`/`--copy-dest`,
  `--append`, `--partial-dir`, and `--remove-source-files`.
- **Unsupported options fall back before transfer; strict mode fails.** This includes
  `--contimeout`, `--fsync`, `--preallocate`,
  `--block-size`, `--checksum-choice`,
  `--log-file-format`, and `--debug`. `--compress-choice` accepts `zstd` or `none`.
  `--info` accepts `progress2`, `progress0`, `stats2`, and `stats0` (comma separated).
- **Compatibility no-ops are listed in `--help` with reasons.**
  `-s`/`--protect-args`/`--secluded-args` is intrinsic
  to protocol-carried paths. `--blocking-io`/`--no-blocking-io` cannot change the
  internally polled pipe transport.
  `--no-motd` has no effect because there is no daemon transport.

Filters use first-match ordering independently for the source file list and
destination deletion. Hide/show (`H`/`S`) apply to the source; protect/risk
(`P`/`R`) apply to deletion. Unqualified include/exclude rules normally apply to
both, but become sender-only with `--delete-excluded`; explicit receiver rules
continue to protect entries. Perishable (`p`) rules are ignored inside a
directory being deleted. The `/` modifier matches the entry's absolute path.

`--files-from=FILE` selects names relative to one source directory. Use `-` for
stdin, `:FILE` to read the list on the transfer's remote machine, or `HOST:FILE`
with the same host as the transfer. Lists imply `--relative` and `--dirs`;
`--no-relative` flattens selected paths. With a file list, `-a` preserves
attributes but does not enable recursion: add `-r` to copy directory trees.
An entry `dir/` also selects its immediate contents without recursion, while
`dir` selects the directory itself. These defaults do not depend on option order.

For example, `find . -type f -print0 | xs -a0 --files-from=- ./ host:backup/`
copies selected files with their implied parents. Leading slashes in the list
refer to the source root; `..` components cannot escape that root. Lists travel
in bounded frames after capability checks. A pulling client validates locally
requested names before creating the destination.

`-0`/`--from0` uses NUL delimiters for file lists, include/exclude files and filter merge
files, preserving newlines and carriage returns inside patterns. It affects
command-line files opened after the option; directory merge files use the
final setting; file lists also use the final setting. `--no-from0` restores line mode.
For transfers without `--files-from`, ordinary SSH
helpers retain line mode unless explicitly configured, for example with
`--rsync-path='xs --from0'`.

`-R`/`--relative` preserves source path components, creating real implied
directories with their source attributes. A `/./` component cuts off the
prefix: `xs -aR /data/./project/file dest/` creates `dest/project/file`.
Selecting an individual file leaves unlisted siblings in its implied parents
alone, including with `--delete`. `-R` does not enable recursion; use `-r` or
`-a` to walk explicitly selected directory trees. `--no-relative` restores
ordinary source basename handling. `--no-implied-dirs` still delegates to rsync.
The `x` modifier applies to xattr names and does not filter filenames.
`-X` transfers honor xattr filters; an `x` modifier on a merge container does not
add `x` to the rules inside it. Extended filters negotiate `PF_FILTERS` before
their rule text is sent. Older helpers refuse or delegate these requests before
transferring, while ordinary include/exclude filters retain their original wire
format.

Single-instance merge rules (`. FILE`) read their file on the client and send
the expanded rules. Per-directory rules (`: FILE`, `dir-merge FILE`) load each
side's own files as traversal enters a directory. Local rules precede inherited
rules within that merge slot; `!` clears that slot's inherited list. Merge
modifiers support `e` (exclude the merge file), `n` (no inheritance), `w` (split
words), `+`/`-` (unprefixed patterns), and `C` (CVS-style word lists without
inheritance), together with side, absolute-path, perishable and xattr defaults.
`-F` merges `.rsync-filter` files, including ancestor files; a second `-F` also
excludes those files. Per-directory rules additionally negotiate
`PF_MERGE_FILTERS` so helpers with only global-filter support refuse or delegate
the request before transfer.

`-C`/`--cvs-exclude` appends CVS filtering after explicit rules: per-directory
`.cvsignore` files, built-in CVS exclusions, `$HOME/.cvsignore`, and `CVSIGNORE`.
Use `--filter=':C'` and `--filter='-C'` to choose their positions explicitly.
Built-in exclusions are perishable; home and environment patterns retain
deletion protection unless made perishable explicitly. A push sends the
client's global CVS patterns to the receiver; a pull uses each side's own
settings. Explicit global CVS filters can reject a pull when those settings
disagree about a file selected by the sender; remote listings enforce the same
checks. Global CVS and per-directory
merge syntax additionally negotiate `PF_CVS_FILTERS` before transfer.

`--delete-after` scans the destination after transfers finish and loads receiver
merge files from the updated tree. Newly transferred protection and risk rules
therefore apply to that deletion pass, and files created during transfer are
included in the scan. Source I/O errors suppress deletion unless
`--ignore-errors` is set. The option negotiates `PF_DELETE_AFTER`; helpers
missing it refuse or delegate before destination creation. Conflicting
`--delete-WHEN` options are rejected.

`-m`/`--prune-empty-dirs` removes empty directory chains from the filtered source
list before generating transfers or listings. Global receiver protection keeps
matching empty directories and their ancestors. Transfer restrictions such as
`--min-size`, `--existing`, and `--safe-links` do not make a directory empty in
that list. The option requires a complete source walk and negotiates
`PF_PRUNE_EMPTY` before transfer; helpers missing it refuse or delegate the
request. `--no-prune-empty-dirs` disables it.

xs-only options: `-j N`/`--jobs=N` (worker threads), `--no-clone`, `--atomic`
(default), `--no-atomic`. Automatic workers use up to 16 CPU cores (performance
cores on macOS); local and receiver pools on APFS use at most four. Explicit
`-j` values override the filesystem budget. Automatic worker selection does
not enable the intra-file ranges reserved for explicit parallel requests.

## Tests

`tests/difftest.py` runs 231 scenarios on macOS through both rsync and xs and compares the
resulting trees (names, types, contents, modes, nanosecond mtimes, symlink targets) and exit
codes — local and remote, fresh copies and updates, deletions, filters, odd file names,
permissions, type changes.

```sh
XSYNC_FALLBACK=0 python3 tests/difftest.py                  # native clone paths
XSYNC_FALLBACK=0 python3 tests/difftest.py --xsync tests/xs-noclone.sh # byte-copy
cmake --build build --target filter_test && build/filter_test
cmake --build build --target xattr_value_test && build/xattr_value_test
cmake --build build --target sparse_test && build/sparse_test
XSYNC_TEST_RSYNC=/path/to/rsync-3.4.4 python3 tests/sparse_test.py  # allocation, delta, metadata, interruption and source races
XSYNC_TEST_RSYNC=/path/to/rsync-3.4.4 python3 tests/link_dest_test.py  # snapshot selection, metadata, delta and publication races
python3 tests/mac_specific_test.py  # sockets, immutable files, dataless policy and deep paths
# Optional real cloud hydration: XSYNC_ICLOUD_FILE=/path/to/an/opted-in/dataless/file python3 tests/mac_specific_test.py
python3 tests/p0_test.py                                  # trust and injected I/O races
python3 tests/wire_test.py                                # hostile receiver protocol peers
python3 tests/directory_lifetime_test.py                  # late/missing children, retired IDs and parent lifetime
python3 tests/mount_test.py                               # macOS: disposable APFS image
./tests/ssh-rig.sh                                        # Docker: real SSH + SIGINT
./tests/ssh-rig.sh ssh_reach_test.py fallback_test.py        # prompts + fallback
python3 tests/fallback_test.py                            # local fallback checks
python3 tests/xattrs_test.py                              # local/push/pull xattrs, filters, clones and resource forks
python3 tests/xattrs_wire_test.py                         # xattr negotiation and hostile metadata
python3 tests/xattrs_race_test.py                         # fresh file/link attributes after source-read retries
python3 tests/xattrs_memory_test.py                       # fork RSS scaling, inline quota, descriptor and storage failures
python3 tests/xattrs_privileged_test.py                   # Linux root trusted/capability parity (isolated SYS_ADMIN rig)
python3 tests/acls_test.py                               # local/push/pull ACLs, inherited modes, itemization and clones
python3 tests/acls_wire_test.py                          # ACL negotiation, principal mapping and hostile records
python3 tests/executability_test.py                       # executable-bit mode/itemize differentials
python3 tests/executability_wire_test.py                  # fresh source modes and capability guard
python3 tests/executability_race_test.py                  # execution bits refresh during source retries
python3 tests/protocol_test.py                            # frozen N-1 and feature subsets
python3 tests/output_test.py                              # formats, ordering, log parity
python3 tests/error_test.py                               # error counts, samples, exit codes and log parity
python3 tests/broken_stdout_test.py                       # closed pipes, cancellation, cleanup and resume
python3 tests/io_limit_test.py                            # pacing, deadlines, keep-alives and negotiation
./tests/ssh-rig.sh io_limit_test.py                        # real SSH pacing and interruption
python3 tests/list_test.py                                # listing parity and no destination writes
python3 tests/app_test.py                                 # GUI contract, byte paths, cancellation and job isolation
python3 tests/app_mapping_test.py                         # literal selection mappings and mapped retries
python3 tests/app_retry_test.py                           # nested retries preserve destination parents
python3 tests/app_conflict_test.py                        # decisions, scopes, keep-both and revision races
python3 tests/app_actions_test.py                         # revision-checked mkdir, rename, permanent delete and metadata
python3 tests/app_preflight_test.py                       # read-only destination capabilities and exact advisory budgets
python3 tests/app_preview_test.py                         # read-only plans, verified budgets and stale-copy admission guards
python3 tests/app_refresh_test.py                         # mapped destination refresh and stale pane generations
python3 tests/app_move_test.py                            # native rename and verified copy/remove outcomes
python3 tests/app_partials_test.py                        # private local interruption, resume and guarded cleanup
./tests/ssh-rig.sh app_ssh_test.py                         # GUI SSH browsing and authentication without a TTY
python3 tests/rig/app_host.py                             # native host engine against an isolated SSH helper
python3 tests/list_wire_test.py                           # hostile listing metadata and fallback
python3 tests/filter_diff_test.py                         # global rule-side differential fuzzer
python3 tests/filter_merge_test.py                        # merge scopes, inheritance and modifiers
python3 tests/filter_cvs_test.py                          # CVS imports and client/server settings
python3 tests/filter_after_test.py                        # updated receiver rules and fresh deletion scans
python3 tests/filter_prune_test.py                        # prune-empty transfers and listings
python3 tests/filter_wire_test.py                         # negotiated filter/deletion/prune configuration
python3 tests/prune_wire_test.py                          # incomplete or unsafe staged prune lists
./tests/ssh-rig.sh list_test.py                            # real SSH listing parity
python3 tests/delta_test.py                               # local/push/pull matching and races
python3 tests/delta_wire_test.py                          # signatures, references, integrity
XSYNC_DELTA_LARGE=1 python3 tests/delta_remote_test.py     # 64 MiB + 2 GiB wire cost vs rsync
./tests/ssh-rig.sh delta_remote_test.py                   # real SSH delta wire cost
XSYNC_LAN_HOST=user@host python3 tests/lan_test.py -v       # missing-helper LAN
./tests/ssh-rig.sh root_test.py                           # Docker: 96 root/ID/device cases
```

The strict native corpus passes 231/231 with sorted itemization on forced
byte-copy transfers. The root group also compares UID/GID values and
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
