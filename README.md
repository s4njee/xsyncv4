# xsync

A fast, parallel rsync work-alike in C++20. Same command line as rsync, a modern live
progress display, and an engine built for trees of many small files.

```sh
xsync -a  src/ dst/                      # local
xsync -az src/ user@host:/backup/src/    # push over ssh
xsync -az --delete host:/data/ data/     # pull, mirroring deletions
xsync -a --progress src/ dst/            # live per-file + whole-transfer progress
xsync src/                              # list immediate local entries
xsync -r host:/data/                     # list remote entries recursively
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

Supported with rsync's meaning: `-a -r -d -H -R -0 -l -L -p -t -g -o -D -O -J -n -u -c -I -x -z -v -q
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

- **Not wire-compatible.** xsync speaks its own protocol, so it needs xsync on both ends
  and delegates rsync daemon transfers (`host::module`, `rsync://`) to rsync.
- **Large local and remote transfers reuse verified blocks** from an existing
  destination. `-W` requests whole-file transfers; APFS cloning remains preferred
  for eligible local copies.
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
  `--numeric-ids` retains numeric identities. As with rsync, a remote push's
  receiver re-enables `--perms` for `-A`, including after `--no-perms`.
- **Delegated to rsync** (strict mode rejects them): incompatible remote `-A`,
  `-b`, `--link-dest`/`--compare-dest`/`--copy-dest`,
  `--chmod`, `--append`, `--partial-dir`, and `--remove-source-files`.
- **Unsupported options fall back before transfer; strict mode fails.** This includes
  `--contimeout`, `-S`/`--sparse`, `--fsync`, `--preallocate`,
  `--skip-compress`, `--block-size`, `--checksum-choice`,
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

For example, `find . -type f -print0 | xsync -a0 --files-from=- ./ host:backup/`
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
`--rsync-path='xsync --from0'`.

`-R`/`--relative` preserves source path components, creating real implied
directories with their source attributes. A `/./` component cuts off the
prefix: `xsync -aR /data/./project/file dest/` creates `dest/project/file`.
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

xsync-only options: `-j N`/`--jobs=N` (worker threads; default is the number of
performance cores), `--no-clone`, `--atomic` (default), `--no-atomic`.

## Tests

`tests/difftest.py` runs 231 scenarios on macOS through both rsync and xsync and compares the
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
python3 tests/xattrs_test.py                              # local/push/pull xattrs, filters, clones and resource forks
python3 tests/xattrs_wire_test.py                         # xattr negotiation and hostile metadata
python3 tests/xattrs_race_test.py                         # fresh file/link attributes after source-read retries
python3 tests/xattrs_memory_test.py                       # fork RSS scaling, inline quota, descriptor and storage failures
python3 tests/xattrs_privileged_test.py                   # Linux root trusted/capability parity (isolated SYS_ADMIN rig)
python3 tests/acls_test.py                               # local/push/pull ACLs, inherited modes, itemization and clones
python3 tests/acls_wire_test.py                          # ACL negotiation, principal mapping and hostile records
python3 tests/protocol_test.py                            # frozen N-1 and feature subsets
python3 tests/output_test.py                              # formats, ordering, log parity
python3 tests/error_test.py                               # error counts, samples, exit codes and log parity
python3 tests/io_limit_test.py                            # pacing, deadlines, keep-alives and negotiation
./tests/ssh-rig.sh io_limit_test.py                        # real SSH pacing and interruption
python3 tests/list_test.py                                # listing parity and no destination writes
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
