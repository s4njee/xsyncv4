# xsync backlog — from benchmark winner to daily driver

Initial audit written 2026-10-08 against xsync 0.1.0 (protocol 1).
All fifteen P0 stories completed against protocol 3; per-story evidence is below.
P1 R-02 through R-09 and E-01 through E-13 are complete (21 of 22 stories). Current protocol 4 supports protocol 3. The remaining P1 story is R-01.
Problem statements retain the original audit findings.

## What "daily driver" means here

The bar is: `alias rsync=xsync` and never notice, except that it is faster and the progress
is better. That is judged against how rsync is actually used on this machine, not against
the whole rsync manual. From shell history and project scripts:

| shape | share | what it needs from xsync |
|---|---|---|
| `rsync -axhP DIR DEST` | 17 of 28 history entries | `-x` correct, `-P` meaning real resume, progress on a real terminal |
| `rsync -az[P] SRC DEST`, some with `--exclude` | 8 of 28 | remote path solid, filters (done) |
| `rsync -e "ssh -i KEY" …` (alone or with the above) | 4 of 28 | real ssh, quoting in `-e`, key/passphrase prompts |
| scripts: `-az --delete --out-format='%i %n'`, `-rlptz`, `--info=progress2` | several repos | `--out-format` honoured, stable script-readable output |
| targets | Linux hosts on the LAN, a Raspberry Pi | xsync present on the far end, or a fallback when it is not |

At the initial audit xsync was strong on the middle of that table (local and pipe transfers of many small
files, 157/159 differential tests) and weak at the edges: it had never run over real ssh,
needs itself installed on every remote, and has a handful of behaviours that would cost
trust the first time they bite.

## How to read this

Status of each claim:

- **partial** — verified progress recorded below; acceptance checks remain
- **done** — implemented and verified; evidence is in the completion log below
- **confirmed** — reproduced on 2026-10-08 with the current binary
- **code** — known from how it is implemented; not separately tested
- **unverified** — suspected or simply never exercised; the first task is a test

Size: **S** an hour or two, **M** a day, **L** several days, **XL** a week or more.

Priority tiers are ordered. Within a tier, items are roughly in the order I would do them.

---

## P0 — Trust: things that are wrong or dangerous today

Nothing below is exotic. Each is a way a normal invocation produces a wrong tree, loses
work, or lies about what it did.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| T-01 | **Runaway recursion when DEST already exists inside SRC.** `xsync -a r/ r/backup/` on a second run nests `backup/backup/backup/…` until `ENAMETOOLONG` (about 145 levels before it stopped). rsync nests once per run because its file list is built before it writes. | **done** | The destination root (by device+inode, and by path prefix) is never descended into as a source; a difftest case covers first and second run, local and remote. | S |
| T-02 | **`host:~/path` is not expanded.** Paths travel in the handshake rather than through the remote shell, so `~` arrives literally: `mkdir "~/tilde-dst" failed`. | **done** | Leading `~` and `~user` expand on the server for both source and destination paths; test via fakessh with a fake `HOME`. | S |
| T-03 | **Remote wildcards do not expand.** `host:dir/*.txt` fails with `link_stat … No such file`. Same root cause as T-02. | **done** | Server-side glob of source args, with rsync's "no match is an error" behaviour. | S |
| T-04 | **Options accepted and silently ignored.** `--out-format` (used in a project script), `--timeout`, `--contimeout`, `-S/--sparse`, `--fsync`, `--preallocate`, `--ignore-errors`, `--skip-compress`, `--block-size`, `--checksum-choice`, `--log-file-format`, `--debug`. The README promises unsupported options are rejected. | **done** | Every option is one of: implemented, rejected with an error, or listed in `--help` as a documented no-op with the reason. No fourth category. | M |
| T-05 | **Attribute failures are silent.** Return values of `chmod`, `chown`, `utimensat`, `futimens`, `fchmod` are discarded, so a destination that cannot take the mode or time reports success. rsync prints `failed to set times/permissions` and exits 23. | **done** | Each failure prints one rsync-style error and sets exit 23; difftest case on a destination where `chmod` fails. | S |
| T-06 | **No detection of files changing while they are read.** The copy reads `st_size` bytes as of the scan. A file rewritten mid-read lands as a mix with no warning; rsync verifies a whole-file checksum and retries. | **done** | Size and mtime are re-checked after the read; a mismatch re-sends once, then warns and exits 23/24. Test with a writer racing the copy. | M |
| T-07 | **`--delete` keeps going after source I/O errors.** rsync skips all deletions if the sender hit any I/O error (`IO error encountered — skipping file deletion`). xsync only protects the one directory whose listing was incomplete; an unreadable sibling does not stop deletes elsewhere. | **done** | Any sender-side read/list error disables deletion for the rest of the run unless `--ignore-errors`; `--max-delete=N` implemented. | M |
| T-08 | **Interrupted remote transfers leave temp files.** On connection loss the receiver exits immediately; in-flight `.name.XXXXXX` files stay and nothing sweeps them later. | **done** | Receiver unlinks (or, with `--partial`, keeps under the final name) every open temp on disconnect and on signal; test kills the sender mid-file and asserts a clean tree. | M |
| T-09 | **Disk-full behaviour is untested** — and this machine's data volume is 99.6 % full. Expected risks: one error per file instead of stopping, temp files left behind, misleading exit code. | **done** | Test on a small disk image: `ENOSPC` stops the run promptly with one clear message, exit 11, no temp files, no truncated files under final names. | M |
| T-10 | **`-x` has only been tested on a tree with no mount point**, yet it is in the most common invocation. | **done** | Test with a mounted disk image inside the source: the mount-point directory is created empty, nothing below it is copied, local and remote. | S |
| T-11 | **New files are written under their final name.** A crash or `kill -9` leaves a truncated new file (repaired next run because its mtime differs). Defensible for speed, but it is a real difference from rsync and deserves a decision rather than a default nobody chose. See "Decisions". | **done** | Decision recorded; if kept, the cost of `--atomic` is measured on ext4 and APFS and stated in the README. | S |
| T-12 | **Case and Unicode-normalisation collisions.** A Linux source with `A` and `a`, or NFC/NFD variants of one name, written to APFS: last writer wins silently and the result depends on thread timing. | **done** | Detect collisions in the generator (case-folded, normalised compare when the destination is insensitive), warn once per pair, exit 23. | M |
| T-13 | **Symlink trust on the receiver.** All operations are path-based, so a destination directory swapped for a symlink mid-run is followed. Symlink targets from the sender are taken as-is; `--safe-links`, `--copy-unsafe-links`, `--munge-links` are not implemented. | **done** | Receiver opens destination directories with `O_NOFOLLOW` and works `openat`-relative, or re-verifies type before writing; `--safe-links` implemented. | L |
| T-14 | **Ctrl-C during a remote transfer.** Local interrupt is tested (exit 20, resumes cleanly). The remote case — does the far side stop, are both terminals and both trees clean — is not. | **done** | Test in the two-container ssh rig (Q-06): SIGINT on the client ends the server within a second and leaves no temp files. | S |
| T-15 | **Root-only paths never ran.** `-o`, device nodes, uid/gid name mapping, `--numeric-ids`, running under `sudo`. | **done** | difftest group that runs in a container as root, including a uid that exists on one side only. | M |

## P1 — Reach: being able to use it against the machines you sync with

At the initial audit, every `host:` argument failed unless matching xsync was on
the remote PATH. R-02 through R-06 now provide fallback, releases, explicit
installation, lookup and protocol compatibility. R-07 through R-09 add local
packaging, IPv6 host parsing and personal defaults. R-01's second physical-host
coverage clarification remains open.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| R-01 | **Real ssh, end to end.** Everything "remote" so far ran through `tests/fakessh.sh` on one machine. Unknowns: `-e "ssh -i KEY"` quoting, passphrase / host-key / password prompts appearing while the progress region is live, `ControlMaster`, remote shells that print a banner on stdout (rsync detects this as protocol garbage and says so), ssh's own stderr. | partial | Checklist run by hand against a Linux LAN host and the Pi, then automated in Q-06; a banner on stdout produces a clear "the remote shell is printing text" error. | M |
| R-02 | **Fallback to rsync.** If the remote has no xsync (ssh exit 127), the versions do not match, or the command line uses an option xsync rejects (`-H`, `-A`, `-X`, `-R`, daemon URLs…), re-exec the real rsync with the original arguments and say so in one line. This is what makes the alias safe. | done | `xsync -a src host-without-xsync:dst` completes via rsync with a one-line notice; `--no-fallback` and `XSYNC_FALLBACK=0` turn it off; the notice goes to stderr only. | M |
| R-03 | **Static release binaries.** Linux amd64 and arm64 (musl, zstd and xxhash vendored), macOS universal. The current build links whatever Homebrew/apt provides. | done | `cmake --preset release-static` produces one file per target that runs on a bare Debian and on Raspberry Pi OS; `xsync --version` shows the git hash. | M |
| R-04 | **Explicit remote install.** `xsync --install HOST` copies the matching binary to `~/.local/bin/xsync` on the host after detecting its OS/arch. Never implicit — the v3 decision that a transfer must not upload a helper still stands. | done | One command gets a fresh Linux host ready; it refuses to overwrite a newer version without `--force`. | M |
| R-05 | **Find xsync on the remote without `--rsync-path`.** Non-interactive ssh sessions often lack `~/.local/bin` on `PATH`. | done | Server lookup tries `xsync`, then `~/.local/bin/xsync`, then `XSYNC_REMOTE_PATH`; documented. | S |
| R-06 | **Protocol negotiation instead of version equality.** Any protocol change currently breaks every installed remote at once. | done | Hello carries feature bits; a newer client talks to an older server using the common subset; policy written down (client supports N and N-1). | M |
| R-07 | **Install on this machine.** `cmake --install`, a Homebrew formula or tap, zsh completion (rsync's completer mostly applies), a man page generated from `--help`. | **done** | `brew install` or `make install` puts `xsync`, its completion and man page in place. | M |
| R-08 | **IPv6 literals and odd host specs.** `[::1]:path` is mis-parsed; `user@host:` with an empty path and `host:` alone are untested. | **done** | Host parsing matches rsync's for bracketed IPv6, empty paths and `-l`-style users; unit tests. | S |
| R-09 | **Defaults without flags.** Environment (`XSYNC_RSH` alongside the honoured `RSYNC_RSH`) and an optional config file or `XSYNC_OPTS` for personal defaults such as "progress on when stderr is a terminal". | **done** | Documented precedence: flags, then env, then config. | S |

## P1 — Everyday behaviour: the flags in your muscle memory

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| E-01 | **`-P` does not resume.** `--partial` is accepted, but a partial file is never reused: there is no delta or append logic, so an interrupted 10 GB file starts from zero. On a remote disconnect the partial is not even kept (T-08). | **done** | An interrupted large file resumes from the verified prefix (hash the existing bytes on both sides, send the rest); tested by killing a transfer at 50 %. | L |
| E-02 | **`--out-format` and stable script output.** One project script parses `--out-format='%i %n'`. With `-v`/`-i`, line order follows thread completion, so diffs between runs are noisy. | **done** | `%i %n %L %l %o %f %b %t` supported; when stdout is not a terminal, lines are emitted in path order; `--log-file` writes the same stream. | M |
| E-03 | **Itemize parity.** Missing against rsync: the `./` root line, `.d..t......` for existing directories whose time changed, `cd` lines in clone mode come from a different code path than byte-copy mode, `hf` for hard links. | **done** | `-i` output of both paths matches rsync's on the difftest corpus after sorting; difftest starts comparing stdout for `-i` runs. | M |
| E-04 | **Delta transfer for large changed files.** Changed files are always sent whole. Irrelevant for the congress corpus, decisive for a 2 GB database dump with small edits over Wi-Fi. | **done** | Files above a threshold (1 MiB) use block matching (rsync rolling checksum, or content-defined chunks with XXH3) when the destination has a previous version; `-W` disables; bytes-on-wire within 20 % of rsync on an edited-large-file test. | XL |
| E-05 | **List mode.** `xsync host:dir/` or a single SRC should list, as rsync does; today it is a usage error. | **done** | `ls -l`-style listing for local and remote sources. | S |
| E-06 | **End-of-run error summary.** With thousands of files an error scrolls away. | **done** | After the run: count of errors and the first ten, grouped by kind; exit-code line as now. | S |
| E-07 | **`--bwlimit`, `--timeout`, keep-alive.** `--bwlimit` is rejected; `--timeout` is ignored (T-04). A stalled ssh connection hangs forever. | **done** | Token-bucket limit on the writer thread; idle timeout with keep-alive frames; exit 30 on timeout like rsync. | M |
| E-08 | **Filter completeness.** Global rule sides, single/per-directory merge files, `-F`, merge modifiers, global CVS rules/`-C`, `-m`, and `--delete-after` reloading newly transferred receiver merge files are implemented and verified. | **done** | 231/231 difftest (expanded from 159); a differential fuzzer against rsync for the new rule kinds, checked into `tests/`. | L |
| E-09 | **`--files-from`, `-R`, `--from0`.** Common in backup scripts and with `find … -print0`. | **done** | Implemented for local and remote, including the "implied directories" semantics of `-R`. | L |
| E-10 | **Metadata beyond `-a`.** `-H` hard links, `-X` xattrs, `-A` ACLs, `-N` creation times, `-U` atimes, BSD file flags, `-E`, `--chmod`, `--chown`. Also an inconsistency to resolve: the clone path already carries xattrs and ACLs while the byte-copy and remote paths drop them. | **done** | `-H` and `-X` first (most used on macOS). Without `-X`, both paths behave the same — either strip on clone or document that clones are a superset. | XL |
| E-11 | **Backup-style options.** `--backup`/`--backup-dir`, `--link-dest`, `--compare-dest`, `--remove-source-files`, `--append`, real `-S` sparse handling, `--preallocate`. | **done** | Native `-S` and `--link-dest` are implemented and verified on universal/static releases. Other backup options fall back to rsync via R-02 until needed. | L |
| E-12 | **macOS specifics.** Dataless iCloud files (reading triggers a download; cloning may not), immutable (`uchg`) destination files, sockets (rsync creates them, xsync skips silently), paths beyond `PATH_MAX` (tested to 40 levels only). | **done** | Regression fixtures cover all four cases on the universal/static releases; dataless policy, immutable writes, sockets and path-length failures are documented. Real iCloud hydration remains an explicitly opted-in fixture. | M |
| E-13 | **Broken stdout.** `xsync -av … \| head` — rsync dies on EPIPE; xsync's behaviour is unknown. | done | Exits promptly with the right code and does not keep copying silently. | S |

## P2 — Progress and feel: the reason to switch

The display has only been checked by capturing frames from a pseudo-terminal.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| U-01 | **Real-terminal pass.** Terminal.app, iTerm, tmux, over ssh, narrow widths, resize mid-run, light themes, `TERM=dumb`, non-UTF-8 locales (needs an ASCII bar fallback). | unverified | Checklist with screenshots; SIGWINCH handled; ASCII fallback when `LC_CTYPE` is not UTF-8. | M |
| U-02 | **Rows are noise for small files.** At 12,000 files/s each row shows a random file at 0 % or 100 %. | confirmed | Rows are reserved for files that have been in flight for more than ~200 ms; small files collapse into one "small files" row with a rate. Large files show their own speed and ETA. | M |
| U-03 | **Clone mode shows nothing per file.** Whole directories complete in one call, so the rows stay empty and the bar moves in jumps. | code | Rows show the directory being cloned; the bar advances per directory. | S |
| U-04 | **Push progress counts bytes read, not bytes landed.** The bar can sit at 100 % while the receiver is still writing. | code | Receiver acknowledges completed bytes; the client bar reflects acknowledged work, with "sent" shown separately. | M |
| U-05 | **Remote detail.** Wire bytes, compression ratio, and which side is the bottleneck (reading, network, writing) are known internally and not shown. | new | Total line shows wire rate and ratio with `-z`; `-vv` names the limiting stage. | M |
| U-06 | **Progress by default on a terminal?** rsync is silent without `-P`. A daily driver might show the bar whenever stderr is a tty and stay silent in scripts. See "Decisions". | new | Decision recorded; `--no-progress` and env override exist either way. | S |
| U-07 | **Machine-readable progress.** Off a terminal, `--progress` prints a line a second. Scripts and wrappers want rsync's `--info=progress2` single line or JSON events. | code | `--info=progress2` output is line-compatible with rsync off a tty; `--progress=json` emits one object per tick and per file. | M |
| U-08 | **Phases that look like hangs.** Deleting a large tree, waiting for the remote to finish, hashing with `-c`: the display says "scanning" or sits at 100 %. | code | Each phase has its own label and counter (`deleting 12,410`, `verifying`, `waiting for receiver`). | S |
| U-09 | **Dry-run summary.** `-n` prints names only with `-v`. | new | `-n` always ends with "would transfer N files (X), delete M". | S |
| U-10 | **`-h` consistency.** The summary follows rsync's `-h` (1000-based, 1024 with `-hh`); the progress display is always 1024-based. | code | One rule, applied everywhere, documented. | S |
| U-11 | **Suspend/resume and cursor hygiene.** Ctrl-Z / `fg`, and every exit path (including `die()` from a worker thread) restoring the cursor. | unverified | SIGTSTP/SIGCONT redraw; cursor restored in a single exit hook. | S |

## P3 — Performance: holding the lead where you actually sync

The benchmark so far is one corpus slice, one machine, one filesystem, no network.

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| F-01 | **Benchmark the real targets.** Over ssh to a Linux LAN host (ext4/XFS) and to the Pi; the full 14 GB corpus (needs disk space freed first); an update run with ~1 % of files changed; a mixed tree with large files; cold cache. | new | `bench/bench.py --target host:path` and a results table per target in the README; this decides the order of everything below. | M |
| F-02 | **Regression gate.** Nothing stops a change from losing the lead. | new | CI job fails if any scenario drops below a recorded ratio to rsync on the same runner. | M |
| F-03 | **ssh is one stream on one core.** On a fast LAN the cipher becomes the ceiling long before the disks do. | unverified | Measured first. Then, if it is the limit: `--streams N` (several ssh connections sharing one transfer) and no compression by default on links faster than the compressor. | L |
| F-04 | **Adaptive compression.** `-z` compresses every block at level 3 regardless of content or link. | code | Incompressible blocks are detected from a sample and sent raw; `--skip-compress` suffixes honoured; level chosen from measured link speed unless set. | M |
| F-05 | **Large files.** One thread reads and one stream carries each large file; local copies on Linux use a plain read/write loop. | code | Parallel ranges within a file on both ends; `copy_file_range`/`FICLONE` on Linux (reflinks on btrfs/XFS mirror the APFS clone path); `F_NOCACHE` above a size so a 50 GB copy does not evict the page cache. | L |
| F-06 | **Linux scan path.** macOS uses `getattrlistbulk`; Linux uses `readdir` plus one `fstatat` per entry. | code | `getdents64` + `statx`, optionally batched with io_uring; measured against rsync on a no-op re-sync of the corpus on ext4. | M |
| F-07 | **APFS byte-copy ceiling.** Creation is ~100 µs per file and does not scale with threads here; system time triples from 2 to 8 threads for no gain. Unknown: how much is path-lookup contention versus the filesystem itself, and how much is the nearly full volume. | confirmed | Re-measure on a volume with free space; try `openat`-relative creation; pick the thread count per filesystem instead of always using all performance cores. | M |
| F-08 | **No-op re-sync burns CPU.** 0.40 s wall but 2.7 s of system time at 8 threads. | confirmed | Wall time unchanged or better with under 1 s of CPU; or an opt-in manifest that skips listing the destination entirely. | M |
| F-09 | **Memory on very large trees.** The receiver keeps every directory record until exit; the local engine holds up to 200,000 pending files. Never run beyond 77k files. | code | A 5-million-file synthetic tree syncs within a stated memory bound; receiver frees a directory once it and its children are finished. | M |
| F-10 | **Whole-subtree clones.** Only leaf directories are cloned in one call. A missing subtree could be one call, at the price of a long volume-wide lock. | new | Bounded version (subtrees under N entries, known from the scan) measured against the leaf-only path. | M |
| F-11 | **Clones when `-a` is incomplete.** `-rt` or `-rlt` fall back to byte copies because the clone would bring the wrong mode. | code | Clone, then correct mode/owner; still cheaper than create+write. | S |
| F-12 | **Deletion is single-threaded.** Removing the 96,000-entry benchmark tree takes about 10 s with `rm`; `--delete` of a large stale subtree will feel the same. | code | Parallel removal by subtree. | S |
| F-13 | **Tiny transfers.** For one file over ssh the fixed costs dominate: thread pool start, handshake round trip. | unverified | A single small file over ssh is within 10 ms of rsync. | S |
| F-14 | **`-c` at scale.** Sender hashes in the walkers, receiver hashes inline in the generator; unmeasured. | unverified | Benchmarked against `rsync -c`; hashing gets its own pool if it starves the scan. | S |

## P4 — Engineering base

| ID | Item | Status | Done when | Size |
|---|---|---|---|---|
| Q-01 | **Version control.** The directory is not a git repository. | confirmed | `git init`, first commit, `.gitignore` already present. | S |
| Q-02 | **CI.** Nothing runs automatically. | new | GitHub Actions on macOS and Linux: build, `filter_test`, difftest (clone and no-clone), warnings as errors. | M |
| Q-03 | **difftest on Linux.** The harness was written and validated on macOS only; the Linux check so far is a hand-written smoke script in a container. | confirmed | Full harness passes against Debian's rsync, with macOS-only expectations (symlink modes, clones) gated. | M |
| Q-04 | **Sanitizers.** Never built with ASan, UBSan or TSan. The progress slots use a seqlock that TSan will flag and needs annotating. | new | Clean runs of the full difftest under each; TSan suppressions limited to the documented seqlock. | M |
| Q-05 | **Fuzz the wire decoders.** `DIR`, `NEED`, `DATA`, hello and options parsing take bytes from the other side. Name validation exists; nothing else is adversarially tested. | new | libFuzzer targets for each frame type and for `get_options`; a day of fuzzing with no crashes; corpus checked in. | M |
| Q-06 | **Two-machine test rig.** A pair of containers with a real sshd, for R-01, T-08, T-14 and network fault injection (`tc` delay, loss, mid-transfer disconnect). | new | `tests/ssh-rig.sh` runs the remote difftest group over real ssh and three fault cases. | M |
| Q-07 | **Kill and converge.** `kill -9` either side at random points, re-run, compare to rsync's result. | new | 200 random kill points, local and remote, always converge with no stray files. | M |
| Q-08 | **Randomised differential testing.** The 159 cases are hand-written. | new | Generator of random trees × random supported option sets, compared against rsync; failures minimised and added as named cases. | L |
| Q-09 | **Large and sparse files.** Largest file tested is 12 MB. | unverified | Cases past 4 GiB offsets, a sparse file, and a file that grows or shrinks during transfer. | S |
| Q-10 | **Option parser versus popt.** Bundled short options with arguments, `--opt=value` versus `--opt value`, `--no-*` for every negatable option, `--` handling. | code | Table-driven test comparing accept/reject against rsync for a few hundred argument vectors. | M |
| Q-11 | **Progress rendering tests.** No automated check of the display. | new | Golden-frame tests through a pty at three widths; a test that every exit path restores the cursor. | S |
| Q-12 | **Internal cleanups.** Fixed clone temp name `.name.xsclone` (two concurrent runs collide); `die()` from worker threads exits without cleanup; a source directory that cannot be listed is created on the destination but never gets its attributes; global mutable option state; `remove_tree` recursion depth unbounded. | code | Each fixed with a test where one is possible. | M |
| Q-13 | **Docs.** Protocol description, a changelog, a "differences from rsync" page kept in step with the tests. | new | `docs/protocol.md` matches the code; README differences section is generated from the difftest skip list. | S |

---

## Decisions needed from you

These change defaults, so they should be chosen rather than inherited from a benchmark run.

1. **Clones by default** (current: on). Fastest by far and uses no extra disk, but copies
   carry xattrs/ACLs and share storage with the source. Alternative: opt-in `--clone`.
2. **New files written in place — resolved by T-11.** Atomic writes are now the
   default for P0 trust hardening. `--no-atomic` restores direct new-file writes;
   `--inplace` remains an explicit opt-in to direct writing.
3. **Progress on by default when stderr is a terminal** (current: off, as in rsync).
4. **Fallback to rsync — resolved by R-02.** Automatic with a one-line stderr notice,
   as specified in its acceptance criteria. `--no-fallback` or `XSYNC_FALLBACK=0`
   selects strict failure; `--fallback` overrides the environment.
5. **Remote install** (R-04): keep it an explicit command, as decided in v3, or allow
   `--bootstrap` during a transfer.
6. **Scope line.** Delta transfer (E-04) and the long tail of options (E-09 to E-11) are
   weeks of work. With fallback in place they can wait until a real invocation needs them.

## Suggested order

1. **Trust** — T-01 to T-05 and Q-01. All small; T-01 is a real hazard.
2. **Reach** — R-01, R-02, R-03, R-05, with the ssh rig Q-06. After this the alias is safe
   for every shape in the table at the top.
3. **Your top invocation** — T-10 (`-x`), E-01 (`-P` resume), T-08, U-01, U-02.
4. **Scripts** — E-02, E-03, T-07, E-06.
5. **Measure, then tune** — F-01 before any other F item; it decides which of them matter.
6. **Parity as needed** — E-08 onward, driven by what falls back to rsync in practice
   (log every fallback and its reason; that log is the real backlog).


## P0 completion log

### T-01 — complete (2026-10-08)

- Source scans exclude the destination root and descendants by canonical path,
  and aliases by device/inode. This covers a destination that does not exist yet.
- Remote receivers send destination identity before scanning; senders apply the
  guard when both ends identify the same machine/filesystem root. Protocol is now 2;
  both endpoints must be rebuilt.
- Six differential cases cover new/existing nested destinations, two consecutive
  runs each, local/push/pull. rsync receives an explicit destination exclusion
  because xsync intentionally avoids rsync's once-per-run nesting. All six pass.
- Additional `-aL` symlink-alias checks pass for local/push/pull, two runs each.

### T-02 — complete (2026-10-08)

- Server expands leading `~` from HOME (account database fallback) and `~user`
  from the account database before resolving either source or destination.
- Unknown users fail clearly with exit 3; they cannot create a literal `~user` tree.
- `python3 tests/p0_test.py` passes fake-HOME-with-spaces push/pull, named-user
  push/pull, unknown-user, and destination-alias tests (2 test methods).
- T-01 full differential verification: 163/165 pass; only the original unsupported
  prune-empty/protect-filter cases fail.

### T-03 — complete (2026-10-08)

- Server globs source arguments after home expansion, with sorted matches, shell
  dot-file rules, brackets, question marks, escaped metacharacters and trailing slashes.
- No matches produce a clear error and exit 23. Destination paths remain literal.
- Four new differential cases pass (multiple patterns, no match, directory contents,
  bracket patterns); the existing wildcard-filter case and fake-HOME regressions pass.

### T-04 — complete (2026-10-08)

- Previously ignored semantic options now fail before any transfer, including all
  options listed in T-04 and the previously ignored short forms `-S`, `-B`, `-T`, `-M`.
- Audited the rest of the parser: rejected ignored recursion, address-family,
  compression and argument-mode switches. Retained only intrinsic/no-effect
  compatibility flags, explicitly documented with reasons in help and README.
- Compression choice is restricted to zstd/none; info accepts progress2/progress0
  and stats2/stats0, including comma-separated and case-insensitive forms.
- Trust regression covers 39 rejected options with an unchanged destination,
  documented no-ops and valid compression/info choices. All 3 test methods pass.
- The first full pass exposed three uses of `--no-whole-file`; retained it as a\n+  documented no-op because this engine has no delta mode. Final verification below.

### T-05 — complete (2026-10-08)

- Checked permission, ownership and timestamp calls in the generator, directory
  finalizer, clone path and file writer. Each failed operation reports its path
  and errno and records exit 23. In-place truncation failures are also reported.
- Real APFS immutable-file differential cases force chmod to fail: local, push
  and pull all match rsync's exit 23 and resulting tree. Fixture cleanup clears flags.
- Full differential suite after T-04/T-05: 170/172 pass; only the original unsupported
  prune-empty/protect-filter cases fail. All 3 trust test methods pass.

### T-06 — complete (2026-10-08)

- Byte readers snapshot the opened file and recheck size, nanosecond mtime/ctime,
  device/inode and the named path after reading. An unstable read retries once;
  a second change reports exit 23. Missing source opens report exit 24.
- Remote large files remain staged until a completion record confirms stability;
  abandoned attempts are drained and removed, including out-of-order chunk work.
  Successful retries apply the fresh source timestamps and size. Small files are
  validated before emitting their record. APFS clones already snapshot file content.
- Fixed sender-directory lifetime so a fast NEED response cannot free a directory
  while its walker is scheduling children.
- 24 deterministic writer races cover growth, shrinkage, same-size rewrites and
  replacement by a new inode, local/push/pull. One change succeeds with fresh bytes
  and mtime; two changes exit 23, preserve the old destination, and leave no temp.
- All 4 trust methods pass. Clone and byte-copy differential suites each pass
  170/172 (the same two known filter failures); filter_test: 32,842 checks pass.

### T-07 — complete (2026-10-08)

- Extraneous-entry deletion is deferred until all source scans and reads finish.
  Any source selection/list/read/checksum error skips deletions across the whole
  tree, with one clear notice; `--ignore-errors` explicitly overrides it.
- Directory metadata is restored after deletions, deepest directories first.
- `--max-delete=N` counts files and directories recursively, handles zero,
  and reports exit 25 when a limit prevents further deletions. Deletion ordering
  matches rsync's reverse sorted-list order within the tested directories.
- Fixed generic listing descriptor leaks and detection of readdir/stat/readlink
  failures, so incomplete source listings cannot masquerade as complete trees.
- Unreadable-directory and injected-read-error sibling tests pass for local/push/pull,
  with and without `--ignore-errors`. All 24 missing-source/max-delete differential
  cases pass, including recursive limits.
- Clone and byte-copy full suites before adding the 12 nested-limit cases each
  pass 182/184; only the original two filter failures remain.

### T-08 — complete (2026-10-08)

- Open outputs are registered independently of worker lifetimes. Fatal exits and
  caught signals close and unlink all in-flight temporaries; `--partial` renames
  them under their final names. New direct outputs are removed without `--partial`.
- Output finalization/cleanup is serialized so disconnect cleanup cannot race a
  worker into publishing an incomplete file. Server mode now installs signal handlers.
- Eight deterministic in-flight tests pass: push/pull, killed sender or client SIGINT,
  with/without `--partial`. They assert expected exits, no hidden temporaries,
  absent uncommitted files or incomplete retained partials as appropriate.
- Full differential suite: 194/196 pass, only the same two unsupported filter cases fail.

### T-09 — complete (2026-10-08)

- ENOSPC/EDQUOT now stop filesystem writes promptly with one diagnostic and exit 11.
  The fatal path cleans all registered outputs, preserving existing final files.
- Connection writers let readers consume a peer's fatal filesystem error before
  treating EPIPE as a generic stream failure, so remote disk-full exits remain 11.
- `tests/mount_test.py` fills a disposable 64 MiB APFS image, leaving about 2 MiB
  free, then copies 16 MiB files. All six real-ENOSPC cases pass: new/existing final
  files, local/push/pull; one clear message, exit 11, no temps/truncated finals.
- The same mount test exposed a real T-10 bug: bulk source attributes report the
  underlying mount point's device, so -x crossed it. T-10 is being fixed next.

### T-10 — complete (2026-10-08)

- Fixed a reproduced APFS mount-boundary bug: getattrlistbulk can return the
  underlying mount-point device. Under -x, source directory entries are resolved
  with stat/lstat and refreshed before comparing against the parent device.
- The wire carries the boundary marker so the receiver creates the mount-point
  directory and restores its attributes without expecting a child listing.
- Disposable mounted APFS image tests pass locally, for push and for pull: the
  directory is empty and has matching mode/mtime. A control run without -x copies
  the mounted content. Disk images are detached and deleted after testing.

### T-11 — complete (2026-10-08)

- Decision for P0 hardening: atomic new-file writes are the default. The optional
  preference question received no answer; the agent chose the safer default under
  the trust goal. `--no-atomic` retains the previous fast path, and `--inplace`
  explicitly writes directly. Clones create their own content snapshot.
- Help and README document the choice and flag the earlier performance table as
  a baseline from before trust hardening.
- In-flight tests verify default temporary visibility versus `--no-atomic` and
  `--inplace`, then SIGINT cleanup. Both focused atomic/remote-cleanup test methods pass.
- Full default-path differential suite remains 194/196, with only the known filter
  limitations.
- Linux build/real-SSH test-image scaffolding is prepared for T-14/T-15.

### T-01 follow-up — parent destinations (2026-10-08)

- Narrowed subtree exclusion to cases where DEST lies inside a selected source.
  Copying a child source into its parent destination is valid and remains supported.
- Three new differential cases cover this shape locally, on push and on pull.
  They pass alongside the six nested-destination cases and symlink-alias regression.

### P0 checkpoint after T-11 (2026-10-08)

- Both full differential configurations pass 197/199 after the parent-destination
  regressions were added; only the original -m/protect-filter limitations fail.
- T-01 through T-11 are complete. Next: T-12 destination-name collisions, then
  T-13 receiver path/symlink safety, T-14 real-SSH interruption, T-15 root ownership/devices.
- The active goal remains open until those four stories are verified.

### T-12 — complete (2026-10-08)

- Generator compares names according to destination case and normalization rules
  before requesting any bytes. ICU supplies full Unicode folding and canonical
  decomposition (including multi-character folds such as Straße/STRASSE).
- Each colliding pair reports one diagnostic and exit 23. Both colliding entries
  are suppressed; unrelated entries transfer, and deletion in that directory is
  disabled. Duplicate directory arguments retain their merge semantics.
- Eighteen file/directory collision cases pass locally, on push and on pull.
  Case-sensitive APFS keeps A/a distinct while still rejecting NFC/NFD aliases.
  Linux ext4 checks pass without falsely folding its distinct names.
- Full macOS differential suite remains 197/199, with the same two filter limitations.
- Build now requires ICU; prerequisites and the Linux test image were updated.

### T-13 — complete (2026-10-08)

- The receiver pins the explicit destination once, then opens descendants with
  `O_NOFOLLOW` and performs file creation, metadata changes, directory creation,
  symlinks, special files, checksums, cloning and deletion through directory
  descriptors. Open outputs retain their parent descriptors through rename,
  abort and disconnect cleanup. Clone temporaries now use unique names.
- `--safe-links` rejects absolute targets and relative targets escaping the
  transfer tree. Unsafe source links protect existing destination entries from
  `--delete`, matching rsync. `--copy-unsafe-links`/`--munge-links` still fail
  explicitly as unsupported. Protocol is now version 3; install matching peers.
- Twenty-eight deterministic syscall-boundary races pass on macOS and Linux:
  local/push/pull, atomic/direct/in-place/clone writes, final-name swaps,
  metadata, deletion, interruption and partial retention. Every outside tree
  remains byte-for-byte intact, including permissions and nanosecond mtimes.
- Ten hostile-peer tests pass on both systems: escaping/NUL names, NUL link
  targets, forged directory paths, duplicate roots and unrequested file data
  are rejected with protocol error 2.
- Fifteen new rsync differential cases pass: safe links, safe-link deletion,
  `-L`, source-directory depth and replacing a preexisting destination symlink
  with `--inplace`. Full corpus plus these additions: 212/214 in clone and
  byte-copy configurations; only the two preexisting unsupported filter cases
  remain. 32,842 filter checks, the full P0 fault suite and real mount/ENOSPC
  tests pass.

### P0 progress checkpoint

- T-01 through T-13 are complete. Next: T-14 real-SSH interruption, then T-15
  root ownership, ID mapping, sudo and devices.

### T-14 — complete (2026-10-08)

- `tests/ssh-rig.sh` builds a disposable Debian client/server pair, runs a real
  sshd on a private internal Docker network, and removes its containers,
  network and temporary keys even on failure. Key and transfer paths contain
  spaces to exercise actual `-e` argument quoting.
- Fixed interrupt handling while the sender waits for `DONE`. The receiver now
  continues watching EOF after `DATA_END` while writes/deletions drain, so a
  disconnected client stops the remote process and cleans its open outputs.
- Eight SIGINT cases pass: push/pull, source reading/receiver draining, with and
  without `--partial`. Draining cases verify that the sender has already sent
  `DATA_END`. Client exit is 20; the slowest observed server shutdown is 0.598s,
  under the one-second acceptance limit. No temporary names survive; atomic
  updates retain old complete files and partial updates retain incomplete data.
- A real client PTY retains its terminal settings and restores its hidden cursor.
  Both source trees remain complete. Real-SSH compressed transfers and unchanged
  reruns pass in both directions, including spaces in paths and key filenames.
- Existing injected disconnect cleanup and hostile-wire tests still pass.

### P0 progress checkpoint

- T-01 through T-14 are complete. Remaining: T-15 root ownership, ID mapping,
  sudo and device-node differential tests.

### T-15 — complete (2026-10-08)

- `tests/root_test.py` compares rsync and xsync in 96 root-only cases: local,
  real-SSH push/pull; fresh, changed, in-place and metadata-only files; archive,
  numeric IDs, owner-only and group-only preservation; direct root and real
  `runner -> sudo` elevation on client and server.
- Client/server databases give `shared` different UID/GID values (1111/3333).
  Each side has an account absent from the other (22222/33333), plus unknown
  numeric ID 45454. Assertions verify name mapping, numeric preservation and
  fallback, rather than only comparing two possibly incomplete fixtures.
- Snapshots compare owner/group, permission and set-id bits, nanosecond mtimes,
  contents, symlink targets, FIFOs, sockets, and character/block device numbers.
- Fixed destination-root owner/group preservation, restoring UID/GID 0 for
  in-place writes, and restoring set-id permissions after metadata-only chown.
- All 96 differential cases pass. The shared rig also passes all eight SIGINT
  cases (latest maximum server shutdown 0.619s), compressed transfers and reruns.
- Final macOS suites: 212/214 in both clone and byte-copy modes. Linux root suite:
  208/210; the same two unsupported filter cases remain. macOS-only attribute
  fixtures and the non-root unreadable-file fixture are correctly excluded on
  Linux root. Full injected trust and hostile-wire suites pass on both platforms.

### P0 completion checkpoint

- T-01 through T-15 are complete, with each story updated when verified.
- The next priority tier remains open. The real-SSH rig supplies part of Q-06;
  network delay/loss faults and R-01's LAN/Pi/prompt checklist are still future work.
- Protocol 3 requires matching xsync builds on both ends. ICU is a build dependency.
- Two existing differential failures are explicitly unsupported P1 filter features
  (`-m` and protect filters), not unfinished P0 acceptance checks.

## P1 completion log

### R-01 — partial: SSH prompts and shell checks (2026-10-09)

- `tests/ssh_reach_test.py` runs against a real sshd in the isolated two-machine
  rig: host-key confirmation, an encrypted key with a spaced filename, password
  authentication, cancellation during a prompt, ControlMaster reuse, stdout
  banners (including a short banner), and ordinary SSH stderr. All five methods
  pass. Terminal attributes are preserved; progress starts after authentication
  and restores the cursor. Authentication cancellation returns 20.
- A shell banner now produces the explicit “the remote shell is printing text
  on stdout” diagnostic. Protocol corruption does not trigger fallback.
- `sanjee@neo.local` is an accessible Raspberry Pi 5 running Debian 13.5/aarch64;
  rsync 3.4.1 is installed, xsync is absent. R-02's fallback push/pull is verified
  there with disposable directories, spaces, a 2 MiB file, symlink, timestamp and
  SHA-256 comparisons. No helper was uploaded.
- **Remaining:** run the native xsync LAN/Pi checklist after R-03/R-04 provide a
  compatible release and explicit install. Container SSH coverage supplements
  that checklist; it does not complete the physical-host requirement.

### R-02 — complete (2026-10-09)

- Unsupported rsync options/filter features and daemon URLs exec a real rsync
  from PATH before any xsync transfer. Original rsync arguments, quoting,
  explicit `--rsync-path`, exit status and the caller's umask are preserved.
  xsync-only worker/clone/atomic/fallback switches are removed. Executables
  resolving to xsync itself are skipped to prevent an alias recursion loop.
- A remote exit 127 or an explicit handshake version mismatch closes and reaps
  the first connection before exec. Authentication failures, malformed frames,
  shell banners, filesystem failures and disconnects after handshake remain
  failures; an already-started transfer is never replayed. Protocol servers
  cannot fall back. Exactly one fallback notice goes to stderr.
- `--no-fallback` and `XSYNC_FALLBACK=0` disable fallback even when the flag is
  after an unsupported option. `--fallback` enables it over the environment.
- Six regression methods pass on macOS and Linux: real rsync hard-link/umask
  preservation, exact argument capture and exit status, strict controls, daemon
  and filter dispatch, no rsync/recursive alias, and push/pull handshake cases.
  Existing strict unsupported-option and hostile receiver checks also pass.
- `XSYNC_LAN_HOST=sanjee@neo.local python3 tests/lan_test.py -v` passes with a
  missing remote xsync: strict exit 127 leaves the disposable remote directory
  empty, then automatic push/pull via rsync preserves contents, symlink and
  nanosecond mtime. Both disposable directories are removed afterward.

### R-03 — complete (2026-10-09)

- `release-static` builds a macOS arm64/x86_64 universal binary and Linux
  amd64/arm64 binaries using musl in Alpine. Original zstd 1.5.7, xxHash 0.8.3
  and ICU 77.1 archives, SHA-256 checks and licenses are vendored.
- Both Linux artifacts run in scratch containers with no runtime libraries.
  The universal binary runs under arm64 and x86_64/Rosetta and links only
  libc++/libSystem; its destination file/directory collision checks pass.
- Git tracking was initialized locally; `--version` includes the source commit.
  The final artifacts record commit `29050650e074`; both Linux architectures
  pass local and compressed push/pull transfers in bare Debian bookworm-slim,
  including spaces, Unicode names and a symlink. SHA-256 manifests are emitted.
- The arm64 file runs on the actual Pi 5, Raspberry Pi OS reference image
  2026-06-18 (Debian 13.5), kernel `6.18.34+rpt-rpi-2712`, with no runtime
  dependencies installed. Its SHA-256 exactly matches the release manifest.
  Native compressed LAN transfers also pass (details below).

### R-04 — complete (2026-10-09)

- `--install HOST` detects Linux amd64/arm64 or macOS, chooses the release,
  streams it over SSH into a private temp file, verifies its version and uses
  rename to publish `~/.local/bin/xsync`. It never runs during a transfer.
- Newer/unrecognized versions are refused unless `--force`; the version is
  checked again before publishing to catch concurrent changes. Invalid upload
  preserves the old executable and removes its temp file. Non-file targets,
  unexpected shell output, unsupported platforms and missing artifacts fail.
- Five local installer regression methods pass on macOS and Linux. A real
  SSH test in the disposable server also passes fresh install, exact executable
  SHA-256, refusal of version 99.0.0, forced replacement and temp cleanup.
- `build-release/xsync --install sanjee@neo.local` explicitly installed the
  matching arm64 release at `/home/sanjee/.local/bin/xsync`. The remote file
  SHA-256 is `b2a44fd2aff99b716f7306c15eb65ae8952afaf2cdeaadb480649fdd3f652ffb`,
  matching that release's `dist/manifest.json` (commit `29050650e074`).
  `--version` reports commit `29050650e074`.
  Native push/pull, reruns, update/delete, metadata and shell checks pass there.

### R-05 — complete (2026-10-09)

- Default SSH server lookup tries PATH `xsync`, `~/.local/bin/xsync`, then
  `XSYNC_REMOTE_PATH` (local value, otherwise remote value). Quoted paths with
  spaces/apostrophes and `~/` are supported. Explicit `--rsync-path` bypasses
  all lookup. Nothing is uploaded; no candidate exits 127 before transfer.
- A real SSH regression isolates PATH and HOME in disposable directories and
  verifies all lookup choices, the explicit override, the missing-helper strict
  failure and copied file SHA-256. All six cases pass. Fallback regressions and
  the original SSH prompt/banner suite also pass after shell quoting was shared
  with the installer and extended to validate quotes/escapes.

### R-01 follow-up — physical Pi/LAN checklist (2026-10-09)

- After R-04's explicit installation, `XSYNC_TEST_BINARY=build-release/xsync
  XSYNC_LAN_HOST=sanjee@neo.local XSYNC_LAN_NATIVE=1 python3 tests/lan_test.py -v`
  passes with fallback disabled. It covers compressed push/pull, unchanged
  reruns, updated files and deletions, 100 small files and a 2 MiB file, spaced
  and Unicode paths, symlink targets, modes and nanosecond file/directory times.
  Local and remote tree SHA-256 snapshots match. Disposable directories are
  removed afterward.
- ControlMaster is confirmed running and reused before being closed. A stdout
  banner fails clearly with code 2; stderr text is preserved and the transfer
  succeeds. The Linux SSH rig separately covers the interactive auth prompts,
  cancellation and cursor/terminal restoration.
- The first ControlPath exceeded SSH's Unix socket pathname limit in macOS's
  default temp directory; SSH's 255 propagated without fallback. The fixture
  now uses a shorter `/tmp` path, and the entire native checklist passes.
- **Remaining clarification:** Neo is both the physical Pi and a Linux LAN
  host. Awaiting whether that plus the isolated Linux SSH rig is the intended
  coverage or a second physical Linux target should also be included.

### P1 native regression checkpoint (2026-10-09)

- `XSYNC_FALLBACK=0 python3 tests/difftest.py`: 212/214 pass after R-02 through
  R-05. The only two failures remain native `-m` and `P` filters (E-08); fallback
  is disabled here so it cannot mask missing native features.

### R-06 — complete (2026-10-09)

- Protocol 4 Hello advertises core, zstd, identity-map and safe-link features;
  peers use their intersection. Unknown bits are ignored, core is required, and
  unnegotiated compressed/identity-map frames are rejected. A common subset
  can transfer without compression. Requested safe-link or name-mapping
  semantics fail before transfer if unavailable (or use R-02's fallback).
- The documented window is N and N-1: **4 and 3**. The client closes/reaps an
  initial incompatible connection and retries version 3 once, before progress
  or transfer. The server accepts a version-3 Hello and sends the historical
  response. Its boolean/integer option layout is frozen separately from
  future options. Versions outside this window use fallback or strict failure.
- `tests/fixtures/protocol3.tar.gz` freezes actual pre-negotiation sources from
  commit `29050650e074`, with a verified SHA-256. Compatibility tests compile
  that historical peer separately, then test both client/server version orders,
  push/pull, compression, safe links, unchanged reruns and file SHA-256. A
  separately compiled core-only peer proves compression can be omitted and
  safety/identity requirements cannot be silently lost. Three methods pass
  natively and over real SSH.
- The protocol-4 development client also passes the complete physical Neo LAN
  checklist against its installed **protocol-3** static binary, with fallback
  disabled. No remote upgrade was needed or performed.
- Current/current real SSH and all eight SIGINT phases pass (maximum server
  shutdown 0.612 s). All 96 root/ID/device differential cases pass. Hostile
  receiver and fallback regressions pass with the updated Hello format.
- After the final R-06 source commit `e40d07f5fe39`, all three static releases
  were refreshed. Both musl architectures pass scratch execution and bare Debian
  local/compressed push/pull tests; the universal binary runs under x86_64 too.
  Neo intentionally retains the tested protocol-3 release for compatibility.
- The final strict native differential run remains 212/214: only E-08's native
  `-m` and protect-filter cases are unsupported. No new failures were introduced.


### R-07 — complete (2026-10-09)

- CMake installs the executable, a manual generated from its `--help`, and zsh
  completion. The completer reuses zsh's rsync support and adds xsync's worker,
  explicit-install, clone, atomic and fallback switches. Existing release helpers
  are installed under `share/xsync/releases/` for explicit remote installation.
- `tools/package.py` creates a reproducible source archive and a local Homebrew
  formula with the archive's SHA-256. The formula builds static, hash-checked
  vendored dependencies. The local `xsync/local` tap is installed on this machine;
  nothing was published. README contains both CMake and Homebrew instructions.
- Functional packaging tests pass on macOS (including the universal static build)
  and Linux: disposable prefixes with spaces, actual copied bytes/nanosecond
  timestamps, clean man-page rendering, and interactive zsh TAB completion of
  both xsync extensions and baseline rsync options.
- `brew reinstall --build-from-source xsync/local/xsync` and `brew test
  xsync/local/xsync` pass. `/opt/homebrew/bin/xsync` is linked, the installed
  manual passes `mandoc -Tlint`, and adding the documented completion directory
  to zsh's `fpath` registers `_xsync`. `otool -L` shows only libc++/libSystem.
- The first static install exposed vendored zstd's install rules, producing a
  Homebrew header conflict. The dependency subdirectory now builds without
  installing its headers/libraries. The regression checks package ownership;
  the existing Homebrew zstd installation was preserved without overwriting it.


### R-08 — complete (2026-10-09)

- Main dispatch and SSH client use one shared host parser. Bracketed IPv6
  addresses (including scoped/mapped addresses) are passed to SSH without the
  brackets. Empty paths become `.`; an empty-host subsequent pull source inherits
  the first host. Explicit users, including an empty user, become SSH `-l` args.
- Daemon recognition uses the outside host separator or a case-insensitive
  rsync URL. Double colons inside a path no longer misclassify a normal file as
  a daemon transfer. Invalid bracket forms remain local, matching rsync.
- `tests/host_spec_test.py` compares actual remote-shell argv with real rsync
  for 17 host/user forms in both directions, including an existing `-l` shell
  option. Ten local/invalid-bracket filename cases also match real rsync.
- Native compressed push/pull proves empty remote paths, relative double-colon
  filenames and multiple sources with an inherited host. All five methods pass
  in the Linux rig, including an isolated real sshd on IPv6 `::1`; the four
  applicable methods pass on macOS. All six fallback regressions pass in the rig.
- The strict native differential result remains 212/214. The only failures are
  E-08's pending `-m` and protect-filter support; host parsing adds no failures.


### R-09 — complete (2026-10-09)

- Personal defaults load from `$XDG_CONFIG_HOME/xsync/config` or
  `~/.config/xsync/config`, then shell-quoted `XSYNC_OPTS`, then command-line
  flags. `XSYNC_CONFIG` selects a file; an empty value disables config. Missing
  implicit files are ignored, while explicitly selected missing files fail.
- Scalar options and on/off flags follow flags > environment > config.
  Repeatable filters accumulate in normal rsync order; `--filter=!` clears them.
  Dedicated `XSYNC_RSH` overrides `RSYNC_RSH` and default-option shell settings;
  `-e`/`--rsh` wins. Dedicated fallback environment controls likewise override
  defaults, with explicit flags highest. Empty remote shells fail clearly.
- Quoted values retain spaces and literal characters without shell evaluation.
  Config supports blank lines and whole-line comments. Defaults reject transfer
  operands and control actions. `--help`, `--version`, and protocol servers bypass
  personal defaults; native servers use the client's wire options.
- Fallback retains the effective default options and original CLI arguments,
  stripping worker/clone/atomic extensions as before. README and the generated
  manual document precedence and all supported environment/config settings.
- All seven functional default tests pass on macOS and Linux: actual copies and
  dry-runs, file/environment/flag precedence, quoted exclusions and clearing,
  exact shell argv, config selection, malformed/default control handling,
  server isolation and fallback argv/exit status. Packaging and host-spec tests
  pass; all six original fallback methods pass. Real SSH transfer/SIGINT,
  lookup, and local/SSH installer suites pass (max shutdown 0.639 s).
- The strict native differential run remains 212/214, with only E-08's pending
  `-m` and protect-filter support failing.


### R-07 through R-09 — release/package checkpoint (2026-10-09)

- All three static artifacts were refreshed from source commit `f2041d1c7d06`.
  Linux amd64 and arm64 pass execution in scratch and local/compressed transfers
  in bare Debian. The macOS universal binary also runs under x86_64/Rosetta.
  `dist/manifest.json` records each artifact's revision, size and SHA-256.
- Static-prefix packaging checks pass with the current executable/manual, and
  the source archive/local Homebrew formula were regenerated with those helpers.
  Homebrew reinstall and its package test pass; `/opt/homebrew/bin/xsync` reports
  `f2041d1c7d06`. All seven defaults tests also pass against that installed binary.
  The installed manual passes lint; all installed release helpers match their
  manifest hashes. Homebrew's existing zstd headers were left intact.
- The complete Neo native LAN checklist passes with the new universal client
  against the intentionally retained protocol-3 Pi helper. The frozen-peer
  protocol suite passes all three methods, including compression-free subsets
  and required-feature rejection. No remote helper upgrade occurred.
- Next open implementation story: **E-01, verified-prefix resume**. R-01 remains
  partial only for its outstanding physical Linux-host coverage clarification.


### E-01 — complete (2026-10-09)

- `-P`/`--partial` reuses a destination prefix for files above 512 KiB after
  comparing XXH3-128 hashes on both sides. Current peers negotiate `PF_RESUME`;
  NEED offers the prefix length/hash and data records carry the accepted length.
  A mismatch sends the file in full. Local byte copies use the same verification.
- The receiver rehashes its original prefix while copying into the atomic output;
  a changed destination fails with 23 and is preserved. A verified `--inplace`
  prefix is hashed without rewriting it. `-W`/`--whole-file` disables resume;
  `--no-whole-file` enables it again. The client negotiates that choice without
  adding unagreed options to Hello or changing the frozen protocol-3 layout.
- Older peers lacking the feature keep the full-file format. Mixed protocol-3/4
  push/pull tests now also request `--partial` and all three protocol methods
  pass natively and in the real SSH rig, including the compression-free subset.
- Writes track completed intervals for partial outputs. Cleanup stops admitting
  writes, waits for active writes and retains only the contiguous prefix, trimming
  out-of-order holes before rename. Existing inplace files retain their length.
  Receiver chunks reject overlaps, inconsistent lengths and unoffered prefixes.
- `tests/resume_test.py` passes all seven methods on Linux (six applicable methods
  on macOS). It stops 64 MiB transfers at the 32 MiB write boundary: local and
  remote SIGINT, sender SIGKILL/disconnect in both directions, then restart. The
  retained 33 MiB prefix matches the source, and each restart sends only the
  remaining 31 MiB plus less than 256 KiB of overhead. SHA-256, mode and ns mtime
  match after completion. Valid/corrupt/empty/full/oversized candidates, inplace
  reuse, local source-read offsets and whole-file controls are also covered.
- Real SSH push and pull repeat the halfway sender-kill check in the isolated
  Linux rig: each keeps 33 MiB and transfers about 32,507,000 bytes on restart,
  preserving the full hash and metadata. The final real SSH regression suite
  passes all eight SIGINT phases; maximum server shutdown was 0.777 s.
- All four `tests/resume_wire_test.py` methods pass on macOS and Linux: gaps are
  trimmed, out-of-order completion works, changed prefixes remain unpublished,
  and unoffered prefixes/overlapping chunks fail. All 12 P0 trust methods and the
  original hostile-wire test pass. Six fallback regressions pass. Strict native
  differentials remain 212/214, with only E-08's pending filter features failing.
- A sparse 4 GiB prefix plus a 1 MiB tail passes on macOS and Linux, checking
  64-bit offsets, preserved prefix samples and transfer of only the tail. The
  full seven-method Linux resume suite passes against the final source build.
- Static release artifacts at source commit `e77fcadcceb7` pass standalone
  execution and compressed resume transfers in scratch and bare Debian. The
  universal macOS binary passes ARM-client/x86_64-peer push and pull: a 2 MiB
  prefix in a 4 MiB file sends 2,097,435 and 2,097,355 bytes respectively.


### E-02 — complete (2026-10-09)

- Native local, push and pull support `%i %n %L %l %o %f %b %t`, literal `%%`
  and optional field widths. Explicit formats imply file reporting; empty formats
  suppress file lines. Source lengths include directories and symlinks, and a
  retried file reports its final size without mutating shared scanned entries.
- File events remain structured until the client formats them. Non-terminal
  stdout buffers and sorts events by transfer-relative path; terminal output
  reports completions live. Ordinary `-v`/`-i` use the same ordering. Progress
  stays on stderr. `--log-file` appends exactly the stdout stream, including
  summaries; opening a missing/unwritable log fails before copying.
- Control characters and invalid UTF-8 bytes are escaped as `\#ooo`, with valid
  Unicode retained. `-8` retains high bytes while still escaping control bytes.
  Linux covers invalid-byte names; APFS rejects that fixture before xsync runs.
- `PF_OUTPUT` gates structured output records and extended DIR display fields.
  Source paths from a remote peer are display-only. Frozen protocol-3 layouts
  stay unchanged. Explicit format/log requests require negotiated support and
  fail with 4 (or fall back to rsync) before destination writes; ordinary output
  still works with older peers. Malformed/unnegotiated output records fail with
  2, and an overflowing timestamp renders safely without exposing memory.
- `%b` counts file-content bytes before compression, excluding framing: resume
  reports only its tail; clones, metadata changes and dry runs report zero.
  This deliberate native accounting difference from rsync is documented in
  README. Field meanings were checked against the
  [official rsync format definitions](https://download.samba.org/pub/rsync/rsyncd.conf.5).
- All nine output methods pass on macOS and Linux, including real SSH, repeated
  ordering, all eight fields, mirrored/append logs, metadata/deletions, escaped
  names, dry runs, compressed resume and hostile event records. All four
  mixed-version/feature methods pass on macOS and over real SSH, including new
  strict format/log rejection against the frozen protocol-3 and core-only peers.
- All twelve P0 trust methods pass (the repaired help/options and source-mutation
  checks were rerun after the full suite). Six fallback methods, the original
  hostile receiver test, all seven Linux resume methods and four resume wire
  methods pass. Strict differentials remain 212/214; the two pending E-08 filter
  features are unchanged. Installed executable/manual and live completion pass.
- E-03 remains open for root/directory itemization and full sorted stdout parity.
- Release checkpoint: all three artifacts identify source `22b1cfae0b94`.
  Linux amd64/arm64 pass scratch execution and bare-Debian compressed resume
  with formatted lengths/byte counts and logs matching stdout. All nine output
  methods pass against the macOS universal artifact; ARM-client/x86_64-peer
  push and pull also pass formatted resume and mirrored-log checks. Existing
  Homebrew and Pi helper installations were not changed by this story.


### E-03 — completed: itemization and differential gate (2026-10-09)

- Native local/push/pull now report the `./` root, directory time/permission/
  ownership changes, transfer permission markers and symlink target changes.
  Same-type symlink replacement reports `cLc` plus its metadata flags; type
  replacement reports new-item markers and suppresses the replaced node's
  extra deletion line while retaining child-deletion records.
- A nanosecond-only checksum metadata correction still restores exact times,
  but does not invent an item flag when rsync would show none. Merging identical
  directory names from multiple sources emits one creation event. Tabs remain
  literal, as in rsync; unsafe controls and invalid UTF-8 retain the documented
  escaping. `-ii` reports unchanged entries without altering the frozen options.
- `PF_DIR_OUTPUT` gates directory display lengths/source paths and a validated
  four-boolean post-Hello output configuration. Old peers receive no new fields
  or configuration frames. Current formatted output and repeated itemization
  require the feature. Display paths remain separate from filesystem paths.
- `tests/difftest.py` compares sorted per-file stdout for `-i` runs and adds
  `--itemize` to request that comparison throughout the corpus. It avoids adding
  a second `-i` to already-itemized commands. Both native APFS-clone and byte-copy
  configurations pass **212/214** with this stronger gate, retaining only E-08's
  two known filter failures. This covers root, directory, attribute, type-change,
  symlink, delete-before, mkpath, dry-run and remote cases against rsync.
- All twelve P0 trust methods pass; the original hostile receiver check passes.
  All nine existing output methods and four mixed-version/feature methods pass
  on macOS and Linux, including real SSH. New repeated-itemization and malformed
  output-configuration checks pass on macOS and Linux; all ten output methods
  and both hostile-wire methods pass on the real SSH rig.
- Native `-H` now preserves groups of regular files, symlinks and special files
  across directories for local, push and pull transfers. `PF_HLINK` gates source
  inode identity/fresh metadata and the structured hard-link-target flag; older
  peers receive no extensions, and strict requests fail with code 4 before
  writes. The v3 option layout and four-byte output configuration remain frozen.
- Added seventeen hard-link differential cases: new/existing groups, local/
  push/pull, dry runs, inplace, no-perms, ignore-existing, update, existing-only,
  checksum, filters and repeated itemization. **229/231** now pass with sorted
  itemization for both clone and byte-copy configurations; only the same two
  E-08 filter cases fail. All eighteen hard-link cases (including no-H) pass.
- Four dedicated native hard-link methods pass on macOS and Linux with real
  SSH, covering compressed large files, fresh groups, unchanged reruns, quiet,
  dry runs and inplace. All thirteen P0 methods pass on macOS; Linux passes
  eleven with its two existing platform/privilege skips. The new concurrent
  anchor-replacement check covers local/push/pull, rejects symlink inode reuse,
  leaves the outside sentinel untouched and removes temporary links.
- All ten output methods, both hostile-wire methods and four mixed-version/
  feature methods pass on macOS and Linux, including real SSH. Unsupported
  hard-link requests are checked against both frozen v3 and core-only peers.
- The first `-H` implementation independently validates/copies selected members
  and then joins successful members with verified atomic links. Duplicate data
  may be copied/sent; README documents this and `%b` retains actual copied bytes.
  E-10 remains open for xattrs and wider metadata; its hard-link prerequisite is
  implemented. Release artifacts at source `e0adac5d165a` were rebuilt and
  verified in scratch and bare Debian for Linux amd64/arm64. Release smoke
  covers compressed resume/logs plus local/push/pull hard-linked regular files,
  symlinks and FIFOs. The four hard-link methods also pass on the universal
  macOS release in ARM and Rosetta modes; ARM-client/x86_64-peer compressed
  push/pull checks preserve both regular/symlink groups and formatted logs.
  Homebrew and the installed Pi helper were not changed.

### E-03 release manifest (2026-10-09)

- `xsync-darwin-universal`: `cfc1b63efc6cd3c53c4b1a084cf770f875da259ac8ba941b536ae0b0206f14c9`, 2,724,280 bytes, source
  `e0adac5d165a`.
- `xsync-linux-amd64`: `846364be84a6fda2a391d71e90cebb58590dbfed8443378a455a2d66dd747858`, 4,695,736 bytes, source
  `e0adac5d165a`.
- `xsync-linux-arm64`: `737cc8dcbcbfb82396d658cbd9f56c54d77501b4f9cbfe98384ec3a1e52533fc`, 4,679,728 bytes, source
  `e0adac5d165a`.

### E-04 — in progress: streaming matcher and local reconstruction (2026-10-09)

- Added a bounded streaming rolling-checksum/XXH3 matcher, adaptive block
  signatures, literal batches and consecutive block references. Matching covers
  insertions, deletions, moved blocks and the final short block without loading
  the whole source into memory. Strong checksums revalidate each copied block;
  XXH3-128 verifies the completed output before publication.
- Local byte copies above 1 MiB now reuse an existing regular destination.
  `-W` disables matching; a verified `--partial` prefix retains priority, and
  APFS cloning remains preferred. `%b` reports literal source bytes; new stats
  explicitly name delta literal/matched data. In an 8 MiB insertion fixture,
  5,806 literal bytes reconstruct the entire source correctly.
- Destination bases use anchored, no-follow opens. `--inplace` snapshots the
  basis into an anonymous file and preserves the destination inode, including
  its existing hard links. A changed source retries once; a changed basis is
  rejected with code 23; final checksum failure prevents retaining unverified
  atomic output. Existing output cleanup tracks verified writes.
- Seven dedicated methods pass on macOS and Linux (local paths in the isolated
  Linux container). They cover edited blocks, insertion/deletion/reordering,
  append/truncate, threshold and whole-file toggles, inplace inode preservation,
  25 deterministic random-edit cases, source retry, basis corruption and a
  concurrent basis-path replacement with an outside symlink sentinel.
- All thirteen P0 methods, ten output methods, four hard-link methods and six
  applicable resume methods pass on macOS (the real-SSH resume method requires
  its rig). The forced-byte-copy sorted-itemization corpus stays **229/231**;
  only E-08's existing filter failures remain. The resume read-observation test
  now recognizes actual streaming preads separately from prefix-hash preads.
- **Not complete:** SSH/general remote deltas, negotiated signatures/references,
  hostile new-wire checks and the measured <=120%-of-rsync wire-cost gate remain.
  Next: request signatures lazily after sender prefix verification, so valid
  partial resumes retain their existing fast path and do not require large
  inplace snapshots. Gate new requests/responses, NEED eligibility and data
  records behind a new feature bit; preserve the frozen options/configuration.
  Published release artifacts remain E-03 source `e0adac5d165a` while E-04 is
  incomplete; installed Homebrew/Pi binaries were not changed.

### E-04 — remote implementation verified; release checks pending (2026-10-09)

- Added negotiated `PF_DELTA` (256), leaving the frozen protocol-3 options and
  four-byte output configuration unchanged. NEED advertises eligible regular
  bases; sender workers request signatures lazily after prefix verification.
  Signatures optionally use zstd, references cover at most 8 MiB, literals at
  most 64 KiB, and each successful attempt supplies a whole-file XXH3-128 sum.
  Older peers keep the whole-file/verified-prefix path; `-W` clears both optional
  reuse features. A delta retry waits for receiver acknowledgment after the
  abandoned attempt drains, including inplace writes.
- Receiver blocks are revalidated from anchored pinned bases; reconstruction
  checksums gate publication. Unverified final output is never retained even
  with `--partial`. Tombstones reject replayed attempts/completions, and DATA_END
  rejects missing requested completions or undrained file records before tree
  finalization/deletion.
- **Measured bidirectional total wire cost**, including signatures and framing:
  edited **2 GiB** push **468,375 bytes** vs rsync **644,399**; pull **468,298** vs
  **644,407** (**0.727x**, below the required **1.20x** limit). The 64 MiB fixture
  passes normal, compressed and inplace push/pull on macOS and real Linux SSH:
  normal/inplace about **0.862x**, compressed about **0.644x**. Whole-file mode
  sends the complete source and reports zero matched delta bytes.
- All **24** local/fake-push/fake-pull delta methods pass on macOS, including 25
  random-edit cases per transport and shrink/grow plus inplace retries. Seven
  new hostile-wire methods pass: malformed/unsolicited signatures, invalid
  compression dimensions, reference bounds, overlap/method mixing, out-of-order
  completion, replay, missing completion, final checksum failure, basis changes
  and a replaced basis path with an outside symlink sentinel.
- Existing P0 (13), formatted output (10), hard links (4), mixed-version protocol
  (4), baseline hostile wire (2) and applicable resume methods pass on macOS and
  the real-SSH rig (existing platform/privilege skips remain). The four resume
  wire methods also pass. Corrupt partial prefixes now reject prefix reuse but
  independently verify and reuse their unchanged delta blocks.
- Strict native forced-byte-copy sorted itemization remains **229/231**; the only
  failures are E-08's known unsupported `-m`/protect-filter stories. E-04 remains
  in progress until static Linux and universal macOS release checks finish.

### E-04 — completed: release and acceptance gate (2026-10-09)

- Completed the local and negotiated remote block-matching story. Its 2 GiB
  edited-file fixture uses **0.727x rsync's total wire bytes**, including reverse
  signatures and framing, for both push and pull. Compressed and inplace 64 MiB
  fixtures also pass the **<=1.20x** limit over real Linux SSH. `-W` disables reuse.
- All 24 matching/race methods and seven hostile-wire methods pass on macOS and
  Linux; the four existing resume-wire methods remain green. Source shrink/grow
  retries, including inplace reconstruction, preserve current contents/metadata.
  The Linux SSH regression suite retains its existing platform/privilege skips;
  all applicable P0, output, hard-link and protocol-3/4 checks pass.
- Source **`11cf957c0d36`** builds verified macOS universal and static musl Linux
  amd64/arm64 artifacts. Linux artifacts pass scratch startup and bare-Debian
  local, push, pull, compression, resume, logging, hard-link and new delta smoke
  checks; the inplace delta pull also preserves its destination inode.
- The universal macOS ARM build passes all 24 delta methods, seven hostile-wire
  methods and applicable wire-budget methods. Rosetta passes the hostile-wire
  and wire-budget methods. ARM-client/x86_64-peer compressed inplace push/pull
  passes final-content checks, inode preservation and full stdout/log parity:
  **23,934 / 23,806 total wire bytes** for an edited 8 MiB insertion fixture.
- Strict native forced-byte-copy itemization remains **229/231**, with only the
  two known E-08 filter failures. Installed Homebrew/Pi helpers were unchanged.

Verified artifact manifest (source `11cf957c0d36`):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `xsync-darwin-universal` | 2,849,752 | `99a6b34c006e44049112fa24da075dadaa60eb780875e7e722eb9fda04fc2d48` |
| `xsync-linux-amd64` | 4,751,184 | `794451e4a8f274f5dd9e8384cc983c958b6a3ff792204b79e7f96f5594a09018` |
| `xsync-linux-arm64` | 4,688,312 | `c67a688c7453429035f076e011c02d7c28108889452ddf3e751ea48ce3b44b43` |

### E-05 — in progress: local and negotiated remote source listings (2026-10-09)

- Single-source invocations now list metadata instead of requiring a destination.
  Directory/trailing-slash and recursive behavior matches rsync; explicit
  `--list-only SRC [SRC]... DEST` leaves DEST untouched and merges directory
  arguments. Listings include all filesystem types, permission/special bits,
  readable/ungrouped sizes, client-local timestamps and escaped names. Link
  targets require `-l`; filters, `-L`, `--no-dirs` and quiet mode apply.
- Listing uses metadata reads, not file-data reads or the transfer generator.
  Stats report no transfers/creations/deletions; logs match stdout. Native remote
  listing requests `PF_LIST` (512) with the existing sender role, streams validated
  metadata and counts its completion. Ordinary transfers do not advertise that
  request bit. Frozen protocol-3 options remain unchanged. Unsupported peers
  fall back with the original argv, or exit 4 in strict mode before any writes.
- Seven differential/no-write methods pass locally, through fake SSH and over real
  Linux SSH. Coverage includes 100+ option/source combinations, files/directories,
  symlinks (including dangling and followed directory links), FIFO/socket entries,
  control/Unicode names, filters, human sizes, explicit/implicit listing, duplicate
  sources, quiet mode, ignored destination sentinels, logs and missing-source 23.
- Four hostile/negotiation methods pass: fifteen malformed metadata/completion
  cases, invalid receiver role, missing-feature strict refusal, exact original
  arguments at fallback and shell failure after a valid completion. Full transfer regressions and release checks are pending;
  E-05 remains in progress until those finish.

### E-05 — regression checkpoint; release verification pending (2026-10-09)

- All seven listing methods and four hostile/negotiation methods pass on macOS
  and in the Linux rig. Source forms include trailing slash, `/.`, `/..`, files,
  symlinks and specials; recursive and explicit multi-source listing match the
  rsync reference. Homebrew rsync 3.4.4 rejects remote `/..` with an unrequested
  file-list-name error; its equivalent `/../` spelling supplies the reference
  output for that case (direct local `/..` parity is separately verified).
- Positive-control I/O injection proves both local and fake-remote `-c` listing
  read no regular-file contents, while an actual forced-byte copy fails with the
  same injected read error. Source/destination filesystem snapshots remain
  unchanged by the differential listing suite. Completion must be followed by
  EOF, and a nonzero shell exit after an otherwise valid list remains an error.
- macOS P0 (13), formatted output (10), fallback (6), protocol compatibility (4),
  delta matching/races (24) and delta wire integrity (7) remain green. Real Linux
  SSH P0/output/protocol checks, listing wire checks and delta wire-budget methods
  also pass, retaining only their pre-existing platform/privilege/large-fixture
  skips. Strict native forced-byte-copy sorted itemization remains **229/231**:
  only E-08's two known filter failures remain.
- Updated help, generated manual (lint passes) and README with listing semantics
  and test commands. Static/universal artifacts will include local/remote listing
  parity, no destination creation and zero-transfer-statistics release smoke.
  E-05 remains in progress until those release checks finish.

### E-05 — completed: native listing and verified releases (2026-10-09)

- Single local/remote SRC and explicit `--list-only` now produce rsync-style
  metadata listings. Trailing slash, dot/parent forms, recursion, filters,
  symlinks/specials, escaped names and size formatting are covered. Explicit
  destinations remain unchanged; positive-control injection verifies no regular
  file contents are read, including with `-c`. No transfer receiver is created.
- Seven listing methods and four hostile/negotiation methods pass on macOS and
  Linux. The universal ARM build passes those same methods. Rosetta passes the
  six applicable listing methods and all four hostile-wire methods (the native
  ARM fault-injection library is used for the no-content-read positive control).
  ARM-client/x86_64-peer recursive listing also matches local stdout and logs,
  including symlink/FIFO metadata and ignored output-format overrides.
- New `PF_LIST` (512) gates listing metadata/completion with the existing sender
  role. Invalid paths/types/modes/sizes, malformed completions, transfer records
  and trailing bytes are rejected. Unsupported peers refuse in strict mode or
  fall back with unchanged original argv. A shell failure after a valid list is
  preserved. Frozen v3 options and ordinary transfer payloads remain unchanged.
- Source **`75865d22f284`** builds verified macOS universal and static musl Linux
  amd64/arm64 artifacts. Scratch startup and bare-Debian release smoke pass the
  existing local/push/pull, resume, compression, output/logging, hard-link and
  delta checks, plus new local/remote listing parity, no destination creation
  and zero transferred files. Generated manual lint passes.
- Transfer regression suites remain green; strict native forced-byte-copy sorted
  itemization remains **229/231**, with the two existing E-08 filter failures.
  The earlier release smoke failure was an over-escaped dot test pattern and was
  corrected before verification. Installed Homebrew/Pi helpers were unchanged.

Verified artifact manifest (source `75865d22f284`):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `xsync-darwin-universal` | 2,921,416 | `e1e94744af64df5828228f946de7b29f8a8730aa4d46bb395d246cf308e49777` |
| `xsync-linux-amd64` | 4,803,064 | `f5d7ec600fbcd1391bc17a48c1c613f9d780d9540deb3cd9a833192384d7ac86` |
| `xsync-linux-arm64` | 4,779,264 | `23218d9103dd9d31e5e65692c22f82d2ad6cb37ca7329b70ef3ef91fa8dbe613` |

### E-06 — in progress: bounded end-of-run error summaries (2026-10-09)

- Client/local diagnostics retain counts by exit-code kind and the first ten
  examples across kinds. Storage is bounded; summary examples escape controls.
  The stderr summary follows stopped progress and flushed output, before the
  unchanged exit-code line. Quiet mode retains it; stdout/logs remain unchanged.
- Fatal errors include preceding diagnostics; interruption preserves earlier
  failures. Zero-code notices and peer completion codes repeating detailed
  diagnostics are excluded. A peer status without details retains a synthetic
  diagnostic. Server processes never add summaries to their protocol stream.
- Eleven summary methods pass on macOS, including local/push/pull exact counts,
  remote receiver errors, quiet/log parity, fatal/interrupted exits, mixed kinds,
  escaped samples, 64 concurrent read failures and 6,000 errors with ten samples.
  Real Linux SSH passes the first ten methods; the final large-count method and
  verified static/universal artifacts are pending. Listing wire (4), frozen
  protocol compatibility (4), Linux P0/output, macOS output/fallback and real
  APFS disk-full/cross-mount checks pass. Collision/disk-full assertions now
  distinguish the immediate diagnostic from its intentional summary repeat.
- Strict native forced-byte-copy sorted itemization remains **229/231**, retaining
  only E-08's two known filter failures. Release smoke now checks local/remote
  error counts, stderr-only output and the original final exit-code line.
  E-06 remains in progress until final release verification finishes.

### E-06 — completed: bounded error summaries and verified releases (2026-10-09)

- Local/client errors now end with a count and the first ten examples across
  exit-code kinds, grouped by kind on stderr before the original exit-code line.
  Storage remains bounded with thousands of failures. Control characters in
  samples are escaped, quiet mode retains errors, and stdout/log streams retain
  their existing contents. Zero-code notices and redundant peer completion
  statuses do not inflate counts; status-only peer failures remain visible.
- Eleven focused methods pass on macOS ARM, Rosetta and real Linux SSH, covering
  local/push/pull failures, receiver failures, 64 simultaneous read errors,
  6,000 errors with exactly ten retained examples, quiet/log parity, mixed kinds,
  fatal errors, vanished-file warnings and interruption after earlier errors.
  ARM-client/Rosetta-peer push and pull also preserve exact counts and log output.
- macOS P0 (13), output (10), fallback (6) and real APFS mount/disk-full (2)
  methods pass. Linux P0/output, frozen protocol compatibility (4), and hostile
  listing wire checks (4) pass with the two pre-existing Linux P0 platform/root
  skips. Existing collision/disk-full tests check immediate errors separately
  from the intentional repeat in the summary. Strict native forced-byte-copy
  sorted itemization remains **229/231**, with E-08's two known filter failures.
- Source **`d68b5af629c3`** builds verified macOS universal and static musl Linux
  amd64/arm64 artifacts. Scratch startup and bare-Debian release smoke pass,
  including local/remote stderr-only error counts and the unchanged exit line,
  plus prior transfer/resume/compression/output/hard-link/delta/listing checks.
  Generated manual lint passes. Installed Homebrew/Pi helpers were unchanged.

Verified artifact manifest (source `d68b5af629c3`):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `xsync-darwin-universal` | 2,954,824 | `2f55d168ab03fc3ea7854549e07e1b4ba8c31a275629ff950fa3211871aa345d` |
| `xsync-linux-amd64` | 4,808,104 | `c93c071363ca1d9b868cfab1864d2b981413c12bcf1db836fecc533d7ab73e89` |
| `xsync-linux-arm64` | 4,780,352 | `6fb670112e59a626e974e84f168a367f928f2d43a44201a1c91e0fce62345e43` |

### E-07 — in progress: pacing, deadlines and keep-alives (2026-10-09)

- Added a token bucket to each remote writer, accounting for serialized bytes
  after compression, and one shared bucket for all local byte-copy workers.
  Accumulation is capped at 0.1 seconds or 16 KiB; short writes/back-pressure do
  not charge bytes twice. A local limit disables clones. Bare rates are KiB/s;
  fractional and binary/decimal suffixes round to the nearest KiB/s, with zero
  unlimited and invalid/nonfinite/overflow/tiny rates rejected.
- Nonblocking pipes with polling bound remote idle waits from shell/hello through
  partial frames and post-EOF shell exit. Empty keep-alives preserve long native
  work without extending a silent peer's deadline. An independent write-stall
  deadline cannot be extended by received heartbeats. Timeout exits use code 30,
  terminate the shell, and retain existing atomic/partial cleanup semantics.
- `PF_IO_CONTROL` (1024) negotiates a separate two-value configuration and empty
  keep-alives without changing frozen v3 options. Invalid or unnegotiated frames
  are rejected; configuration lengths are bounded before allocation. A nonzero
  limit/timeout against unsupported peers delegates or refuses before transfer.
- Fifteen I/O methods pass on macOS and real Linux SSH, including aggregate
  local/push/pull pacing, clone bypass prevention, compressed wire accounting,
  unit parsing, all stalled read stages, a blocked writer receiving heartbeats,
  bidirectional keep-alives, delayed native source reads, interruption, remote
  code 30, malformed configuration and atomic/partial timeout cleanup. The added
  oversized-configuration case passes on macOS; final Linux/release checks remain.
- P0/output/fallback/error-summary checks pass; Linux delta wire-budget checks
  retain their pre-existing optional 2 GiB skip. Strict native forced-byte-copy
  sorted itemization remains **229/231**, with E-08's two known filter failures.
  Expanded frozen/subset peer tests initially had a stale expected diagnostic
  string for the new options; that assertion is corrected and verification is
  running. Static/universal release verification is still pending.

### E-07 — completed: rate limits, idle deadlines and verified releases (2026-10-09)

- `--bwlimit` now uses token buckets in remote writers and one shared bucket for
  local copies. Rates account for compressed wire bytes remotely and written
  bytes locally; a local limit disables clones. Units, fractional/rounded rates,
  zero/unlimited, invalid values and bounded accumulated credit are documented.
- `--timeout` now bounds remote shell/hello, idle and partial-frame reads, blocked
  writes and post-EOF shell waits. It exits 30 and uses existing atomic/partial
  cleanup. Negotiated keep-alives preserve live native work; outgoing heartbeats
  cannot hide a silent peer, and received heartbeats cannot hide a blocked writer.
  Simultaneous read/write expiration has one cleanup and final diagnostic owner.
- `PF_IO_CONTROL` (1024) adds separate configuration/empty keep-alive frames,
  keeping frozen v3 options unchanged. Oversized, malformed and unnegotiated
  controls are rejected. Unsupported peers refuse nonzero limits/timeouts with
  code 4 or fall back with original argv, before destination changes.
- Sixteen I/O methods pass on universal ARM, Rosetta and real Linux SSH, covering
  aggregate pacing, clone bypass prevention, compression, native delayed reads,
  stalled reads/writes/EOF, bidirectional heartbeats, interruption, remote exit
  30, concurrent deadline expiration and atomic/partial prefix cleanup. ARM-client
  to Rosetta-peer push/pull also preserve pacing, data and stdout/log equality.
  Expanded frozen/subset protocol checks (4) pass on macOS, Linux and universal
  ARM, including refusal of new options against old peers. A stale expected
  diagnostic in the expanded tests was corrected before final verification.
- macOS P0 (13), output (10), fallback (6) and error summaries (11) remain green;
  Linux P0/output and delta wire budgets pass with their existing optional skips.
  Strict native forced-byte-copy sorted itemization remains **229/231**, retaining
  E-08's two known filter failures. Help/manual/README reflect the implemented
  flags and polled transport; generated manual lint passes.
- Source **`864bd37edf14`** builds verified macOS universal and static musl Linux
  amd64/arm64 artifacts. Scratch startup and bare-Debian release smoke pass
  local/push/pull pacing with `--timeout=1`, stalled-shell exit 30, and prior
  resume/compression/output/hard-link/delta/listing/error-summary checks.
  Installed Homebrew/Pi helpers were unchanged.

Verified artifact manifest (source `864bd37edf14`):

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `xsync-darwin-universal` | 2,957,800 | `1d05ec29d5b6b2141353109d495790c2394ff7d5f68dd7089b9ccb95c265902b` |
| `xsync-linux-amd64` | 4,842,480 | `4b68887b2af6f53abbf91f80bcb7f09124b6d9ab89b001eb767d67baf70f4a84` |
| `xsync-linux-arm64` | 4,785,944 | `458d6373ad5a14673a042e01dce378d31a46b8b82fcf92ec8fbb16c7a3b452fd` |

### E-08 — in progress: global rule sides and differential coverage (2026-10-09)

- Added native hide/show and protect/risk rules, long spellings, and global
  modifiers `/ p r s x` alongside existing negation. Sender traversal and
  receiver deletion now evaluate their own ordered rules. `--delete-excluded`
  drops default receiver protection while retaining explicit receiver rules.
  Perishable rules can protect a directory itself, but are ignored during
  removal of children inside an unprotected directory. Absolute patterns use
  the named entry's absolute path; xattr rules do not filter filenames.
- `PF_FILTERS` (2048) negotiates a bounded, separate rule configuration (frame
  19). Extended text is omitted from the frozen v3 hello and sent only after
  negotiation. Unsupported peers refuse with code 4 or delegate original argv
  before transfer. Malformed, oversized, unnegotiated and hello-embedded extended
  rules are rejected before destination creation. Invalid side modifiers on
  `H`/`S`/`P`/`R` fail with rsync's syntax status.
- Checked in `tests/filter_diff_test.py`: reproducible seeds, mixed rule order,
  sender/receiver sides, deletion, `--delete-excluded`, perishable rules,
  absolute paths, source integrity, data/types/modes/times and sorted itemization.
  Its 234 local/push/pull comparisons pass on macOS ARM, Rosetta and real Linux
  SSH. An additional 512 local random seeds plus 30 directed cases pass. Twelve
  invalid side/modifier cases match rsync on ARM, Rosetta and Linux. The fuzzer
  currently covers the implemented global subset; merge/prune cases remain to
  be added with those implementations.
- All 32,913 filter unit checks pass on ARM and Rosetta. Four hostile filter-wire
  methods pass on macOS, Rosetta and Linux; expanded frozen/subset protocol
  checks (4) pass on macOS and Linux. A Python 3.11 f-string incompatibility in
  the new wire test was corrected before final Linux verification. macOS P0
  (13), output (10) and listing (7) methods remain green.
- Strict native forced-byte-copy sorted itemization is now **230/231**; the
  protect-filter failure is fixed and `include_exclude_prune_empty` remains.
  **E-08 is not complete:** single/per-directory merge files, inheritance and
  merge modifiers `C e n w`, `-F`, CVS rules/`-C` and `-m` still need implementation
  and differential coverage. QA builds include both macOS architectures; release
  artifacts remain the completed E-07 set above, and installed helpers were unchanged.

### E-08 — in progress: merge files and directory contexts (2026-10-09)

- Added single-instance (`.`/`merge`) and per-directory (`:`/`dir-merge`)
  filters, nested merge files, ancestor scans, scoped anchors, independent
  sender/receiver files, and `-F`/`-FF`. Child rules precede inherited rules
  within their merge slot; `!` clears that slot without clearing global rules.
  Directory contexts are immutable and carried through local transfers,
  remote traversal, listings and recursive destination removal. Duplicate
  merge filenames, including self-references, retain their first active slot.
- Merge defaults support `C e n w + - / p r s x`. Single-instance files are
  expanded on the client; configured `.` rules are rejected on the wire before
  file access. Per-directory files negotiate `PF_MERGE_FILTERS` (4096) in
  addition to `PF_FILTERS`; helpers with only global-filter support refuse
  before destination creation. Frozen protocol-3 peers still accept expanded
  single-instance files containing basic include/exclude rules.
- Fixed transfer-root and path semantics found by differential tests: a named
  source does not read ordinary merge files from its parent, and relative
  merge filenames are resolved during traversal. Ancestor checks remove `.`
  components while retaining `..`, matching both reference versions tested.
  Strengthened the global fuzzer's fixtures so source/destination file sizes
  differ and comparisons verify which bytes transfer rather than quick-check
  skips.
- Checked in `tests/filter_merge_test.py`: 294 local/push/pull comparisons
  (34 directed cases, `-F` repetitions, named roots and 24 random seeds per
  direction), plus 24 listing comparisons with multiple roots and different
  working directories. All seven methods pass on macOS ARM, Rosetta and real
  Linux SSH. An additional 128 local random seeds plus 74 directed comparisons
  pass on ARM. Unit checks total **32,924**, all green on ARM, Rosetta and Linux.
  Native tests separately cover documented CVS word-list clearing because
  the released rsync 3.2.7/3.4.4 references reject `!` in these lists; word-mode
  differential cases use their accepted underscore prefix separator.
- macOS P0 (13) and listing (7) checks pass. Hostile filter-wire checks (4)
  pass on ARM, Rosetta and Linux. Expanded mixed-version protocol checks (6)
  pass on macOS and real Linux SSH. The strengthened global differential
  suite's 234 comparisons pass on ARM, Rosetta and real Linux SSH.
- Forced byte-copy sorted itemization remains **230/231**, with only
  `include_exclude_prune_empty` failing. **E-08 remains in progress:** global
  CVS rules/`-C`, prune-empty directories/`-m`, and `--delete-after` reloading
  newly transferred receiver merge files still need implementation and
  differential coverage. Release artifacts remain the completed E-07 set;
  QA builds cover both macOS architectures and installed helpers were unchanged.

### E-08 — in progress: global CVS filters (2026-10-09)

- Added `-C`/`--cvs-exclude` and positioned global `-C`/`+C` filter rules.
  CVS defaults, `$HOME/.cvsignore` and `CVSIGNORE` share the first imported
  global list; per-directory `.cvsignore` files retain their own merge slots.
  Built-in patterns are perishable, while home/environment patterns inherit
  explicit perishable defaults. Directory-only VCS patterns leave ordinary
  files such as a file named `.git` visible. Repeated command-line `-C` flags
  append the CVS rules once, after explicit rules.
- Matched separate client/server settings: pushes expand the client's global
  CVS patterns; pulls import the sender's own settings. Command-line `-C`
  preserves the receiver's unsent global cache under `--delete-excluded`.
  Receiver-only global markers do not initialize the sender's CVS cache.
  Explicit global filters reject excluded incoming names with exit 4; a
  per-directory rule delegates filter selection to the sender, including when
  that rule is subsequently cleared. Remote listings apply the same checks.
- Added `PF_CVS_FILTERS` (8192): the negotiated filter configuration carries
  the CLI CVS flag, and transfer/listing entries carry each source's absolute
  path for global filter checks, including relative and multiple source roots.
  Configured CVS rules require negotiation before reading home files; frozen
  hello fields cannot import CVS rules. Per-directory merge syntax also needs
  this feature because its files can contain global CVS markers. Helpers
  missing the feature refuse before destination creation.
- Checked in `tests/filter_cvs_test.py`: **282** transfer comparisons (35
  directed cases with both deletion policies and 24 randomized cases in each
  direction), distinct client/server settings, an unchanged-destination
  rejection check, and direct native coverage of documented CVS list clearing.
  `tests/filter_cvs_listing_test.py` adds **16** local/remote listing comparisons.
  Cases include single/per-directory merges with side, perishable and xattr
  defaults; CVS imports deliberately do not inherit an xattr default.
- All **298** CVS transfer/listing comparisons pass on ARM, Rosetta and real
  Linux SSH. Unit checks total **32,940**, green on all three; filter-wire
  checks (6), listing-wire
  checks (5), and mixed-version protocol checks (7) cover negotiation and
  malformed inputs. Existing P0 (13), listing (7), and merge checks (7) pass.
  Forced byte-copy sorted itemization remains **230/231**, with only
  `include_exclude_prune_empty` failing.
- **E-08 remains in progress:** `-m` and `--delete-after` reloading newly
  transferred receiver merge files still need implementation and differential
  coverage. Release artifacts remain the completed E-07 set; installed helpers
  were unchanged.

### E-08 — in progress: refreshed delete-after filters (2026-10-09)

- `--delete-after` now scans the updated destination tree after all transfers,
  rather than reusing the extras found by the generator. Receiver merge files
  are loaded during that pass, so newly transferred protection/risk rules and
  newly created extra files affect deletion. Immutable parent contexts survive
  removal of their own merge files. Named source roots retain their established
  filter scope, and dry runs consult the unchanged receiver tree.
- Preserved sender-error deletion suppression, `--ignore-errors`, deletion
  limits and final directory attributes. The non-incremental deletion pass
  handles subdirectories before sibling files, matching rsync's surviving
  entries when `--max-delete` is reached. Conflicting `--delete-WHEN` modes
  fail with a syntax error before touching the destination.
- Added `PF_DELETE_AFTER` (16384) and a strict, separately negotiated deletion
  configuration frame. Older helpers refuse before destination creation;
  fallback retains the original arguments. Malformed or unnegotiated
  configurations cannot create a destination.
- Checked in `tests/filter_after_test.py`: **237** local/push/pull comparisons
  covering changed receiver rules, inheritance, nested merges, CVS imports,
  excluded merge files, named roots, type replacements, sender read errors,
  dry runs, deletion limits, 24 random seeds per direction and transfers
  without filter configuration. A timed paired check creates an extra file
  after copying starts and verifies that the final scan deletes it. Eight
  conflicting-mode executions verify an unchanged destination.
- All six methods pass on macOS ARM, Rosetta and real Linux SSH (the final
  no-filter method was run separately). Filter-wire checks (7) pass on all
  three; mixed-version checks (8) pass on ARM and Linux. Unit checks remain
  **32,940**, green on all three. Existing merge checks (7) and P0 checks (13)
  pass on ARM. Forced byte-copy sorted itemization remains **230/231**, with
  only `include_exclude_prune_empty` failing.
- **E-08 remains in progress:** `-m` still needs implementation and differential
  coverage. Release artifacts remain the completed E-07 set; installed helpers
  were unchanged.

### E-08 — complete: prune-empty directories and full filter acceptance (2026-10-09)

- `-m`/`--prune-empty-dirs` now prunes empty directory chains from the complete
  filtered source list before local or remote generation and before listing
  output. Global receiver protection keeps matching empty directories and
  their ancestors; transfer restrictions do not make the source list empty.
  Receiver per-directory files still govern deletion separately. Local source
  directories are scanned once, with their immutable filter contexts retained.
- Remote generation waits for `LIST_END`, preserves source indices and parent
  references, and acknowledges pruned directories without requesting their
  files or changing their attributes. `PF_PRUNE_EMPTY` (32768) negotiates the
  configuration and pruned-directory counts used by push statistics. Older
  helpers refuse or delegate before destination creation. Empty named roots
  create no destination; trailing-slash roots retain their directory attributes.
- Checked in `tests/filter_prune_test.py`: **348** transfer comparisons and
  **32** listing comparisons, plus native pruned-statistics checks. These cover
  global protection and rule sides, empty ancestor chains, absolute paths,
  merge files, CVS imports, `-F`/`-FF`, named and empty roots, multiple listing
  roots, non-recursive directory transfers, transfer restrictions, deletion
  limits, read errors, dry runs and 24 random seeds per direction. All six
  methods pass on ARM, Rosetta and real Linux SSH; the two final methods were
  run separately on Rosetta and Linux.
- `tests/prune_wire_test.py` rejects unfinished lists, a missing root and unsafe
  staged names/child paths before destination creation. It passes on ARM,
  Rosetta and Linux. Filter-wire checks (8) pass on all three; mixed-version
  checks (9) pass on ARM and Linux, including a helper with all earlier feature
  bits but no pruning support. Unit checks remain **32,940**, green on all three.
- The refreshed delete-after suite (6) passes on real Linux SSH after pruning
  was added. Existing macOS P0 (13), listing (7), receiver-wire (2), CVS (6)
  and merge (7) methods remain green. The packaged macOS binary passes the
  prune suite (6) and staged-stream check, and forced byte-copy sorted
  itemization is now **231/231**. The formerly failing prune-empty case also
  passes through the packaged clone path.
- Rebuilt and verified the release set from source `5bd96f61ddfa`. Linux
  amd64/arm64 scratch and Debian checks include pruning, refreshed receiver
  rules, CVS filtering, push/pull statistics and remote listing, in addition
  to the existing transfer, metadata, delta and I/O controls. macOS remains
  universal and links only system dylibs; final Rosetta checks pass. Artifacts:
  - `xsync-darwin-universal`: 3,235,672 bytes,
    SHA-256 `67c3d966bc44efccb74e58870edd47f9e4f334a8984ebe64a0bd9548d256b4af`.
  - `xsync-linux-amd64`: 4,978,728 bytes,
    SHA-256 `bbad84586788af883469f7511721b907ac3d1d4c833d639d8cb5257c7029bf3f`.
  - `xsync-linux-arm64`: 4,930,800 bytes,
    SHA-256 `48f21ece76e56f811f040077d0a3033cc86ccb1bbb343c939f2570e5c1a56ceb`.
- **E-08 is complete; P1 is now 16/22.** Installed helpers were unchanged.
  E-09 is next; R-01 still awaits a distinct Linux LAN target beyond the Pi.

### E-09 progress — NUL-delimited filter input (2026-10-09)

- Implemented `-0`/`--from0` and `--no-from0` for include/exclude files,
  single-instance and per-directory merge files, nested merges, word-split
  templates and CVS inputs. CR/LF and spaces remain pattern bytes in NUL
  record mode. Word templates still split whitespace. Empty/comment records,
  missing final delimiters and line-mode input containing NUL match rsync.
- CLI filter files use the setting at the point they are opened; directory
  contexts inherit the final setting. Ordinary SSH helper contexts remain in
  line mode as in rsync; an explicit `--rsync-path='xsync --from0'` works.
  No protocol version or frozen HELLO layout changed for this component.
- Added `tests/filter_from0_test.py`: **147** transfer comparisons across
  local/push/pull, **5** stdin comparisons and **2** listing comparisons,
  including source integrity, metadata, deletion, rule sides, nested merges,
  CVS, pruning and delete-after. ARM and Rosetta checks pass. Linux SSH
  transfer/stdio checks and its separate listing check pass. Existing merge
  regression checks (7) pass on ARM and Linux, and filter-wire checks (8)
  pass on Linux. Unit checks remain **32,940**, green on all three.
- **E-09 remains partial and P1 remains 16/22.** `--files-from` and `-R`,
  including local/remote file-list input and implied directory behavior,
  still require implementation and acceptance checks. Packaged releases and
  installed helpers remain at the completed E-08 baseline.

### E-09 progress — relative paths and implied directories (2026-10-09)

- Implemented `-R`/`--relative` and `--no-relative` using a selected source
  tree shared by local transfers, remote senders and listing. Absolute source
  paths preserve their components below the destination; `/./` cuts off a
  physical prefix. Implied parents are real directories with source metadata,
  including when a source component is a symlink. A requested descendant takes
  directory priority over an explicitly selected symlink at the same name,
  regardless of argument order.
- Implied/partial parents protect unlisted destination siblings during deletion;
  explicitly scanned directory contents own their deletion pass. Non-recursive
  selections walk only their selected nodes. Selected trees are built before
  writes, preserve source/filter contexts, and use per-file cloning rather than
  whole-directory cloning. Pruning, hard links, transfer restrictions, dry runs,
  checksums and refreshed deletion rules share the existing receiver paths.
- Added separately negotiated `PF_RELATIVE` and configuration frame 22.
  Selected directory flags and absolute source paths are capability-gated;
  protocol 3's frozen HELLO remains unchanged. Missing helpers refuse or fall
  back with original arguments before destination creation. Pulls validate
  globally excluded implied names, matching rsync's rejection behavior.
- Added `tests/relative_test.py`: **171** transfer comparisons (including clone,
  source alias/overlap and absolute-path output checks), **48** listing
  comparisons, plus native invalid-path checks in all three directions.
  The baseline suite passes on ARM, Rosetta and real Linux SSH; later overlap,
  absolute-output and local regression checks pass separately on all three.
  Final filter-wire checks (10) pass on all three, including malformed selected
  metadata and original-argument fallback. ARM receiver-wire checks (2) pass.
- Fixed sender `%n`/`%f` rendering for absolute relative paths and physical
  prefixes containing `..`. Complete DIR frames reject trailing data. A fatal
  protocol error retains its exit code if the reader concurrently sees EOF;
  the new Linux hostile-frame check exposed and now verifies that race.
- Existing forced byte-copy itemization remains **231/231** on ARM. The full
  NUL-input suite remains green after relative support was added. **E-09 and
  the overall P1 goal remain in progress (16/22 stories complete):** the
  remaining E-09 work is `--files-from`, including client/remote files, stdin,
  NUL input, option defaults and selected directory semantics. Release
  artifacts and installed helpers remain at the E-08 baseline.

### E-09 progress — file-list selection and transport (2026-10-09)

- Implemented `--files-from` for one source root: client files, stdin, and lists
  on the transfer's remote host (`:FILE` or matching `HOST:FILE`). Defaults imply
  relative paths and directories independently of option order; archive mode
  requires explicit `-r` for recursion. Selection handles path sanitizing,
  `/./` cuts, nonrecursive directory contents, implied parents, deletion,
  filters, pruning, hard links, dry runs and listings.
- Added `PF_FILES_FROM` and bounded configuration/data/completion frames 23–25;
  the frozen protocol 3 HELLO is unchanged. Capability and acknowledgement
  checks precede file/stdin reads. Missing capabilities retain original fallback
  arguments; stdin consumed by an earlier filter can be replayed to rsync.
- Pulls validate locally requested names and stage directory metadata before
  writes, rejecting unrequested names with code 4. Lists retain rsync's distinct
  sender-owned and forwarded parsing behavior, including comments, embedded
  NUL bytes, helper delimiter settings and merge files in implied directories.
- Added `tests/files_from_test.py`, covering 470 transfer comparisons, 100 listing
  comparisons, input/syntax failures and source integrity. ARM and Rosetta
  baseline file-list suites pass; targeted oversized-record and syntax checks
  pass on ARM. Relative and NUL-filter regression suites also pass, along with
  231/231 forced byte-copy/itemized corpus cases and 32,940 filter unit checks.
  Protocol checks cover malformed configurations, streams, selected metadata,
  acknowledgements, original-argument/stdin fallback and unrequested names.
- Real Linux SSH verification and the rebuilt three-platform release set are
  still pending. Two fixture issues were corrected before rerunning Linux:
  preserving hard links during fixture upload, and normalizing JSON's list
  representation when comparing hard-link tuples. **E-09 remains partial and
  P1 remains 16/22 until final cross-platform verification completes.** Installed
  helpers remain unchanged.

### E-09 — complete: selected sources and NUL input (2026-10-09)

- **E-09 is complete; P1 is now 17/22.** Native `--files-from`, relative source
  paths and NUL-delimited inputs work locally and over SSH. README documents
  file-list defaults, remote lists, stdin, directory selection and helper
  delimiter behavior. `--no-implied-dirs` remains delegated to rsync.
- File-list verification covers **470 transfer comparisons**, **100 listings**,
  input/syntax failures and source integrity. ARM and Rosetta baseline suites
  and later record/syntax checks pass. The final complete Linux SSH file-list
  suite passes all 10 methods. All 16 protocol checks pass on ARM, Rosetta and
  Linux, including rejected streams/metadata, capability and acknowledgement
  checks before reads, stdin replay on fallback and requested-name validation
  before writes. The Linux wire helper also runs under Python 3.11.
- Relative and NUL-filter regression suites remain green on ARM, with focused
  relative and stdin checks passing again on Linux. Filter unit tests report
  **32,940 checks, zero failures** on ARM, Rosetta and Linux. Both development
  and packaged ARM byte-copy/itemization corpora pass **231/231**.
- Release artifacts were rebuilt from source commit **c4a380a025cf**. Linux
  amd64/arm64 scratch and Debian smoke checks pass, including selected file
  lists, stdin, remote-owned lists, implied-directory deletion, hard links,
  relative cuts and NUL-filter/listing input. Packaged ARM and Rosetta file-list
  checks also pass. macOS contains both architectures and only system dylibs;
  manifest sizes and SHA-256 values were verified:

  | Artifact | Bytes | SHA-256 |
  |---|---:|---|
  | Darwin universal | 3,380,104 | `ee1e3f6dee8b934934bce830474be9bd06a8797105838728caa66a6bbc65089c` |
  | Linux amd64 | 5,053,680 | `e38ad5deb562e1eafcb25599b50c99ef42c188cf675b6306d6e0108659a7e241` |
  | Linux arm64 | 4,946,976 | `18d62cb84c417a1f1ded7184f35b111c5da13abe448dadbadd6d9f97afabcef3` |

- Installed helpers remain unchanged; disposable SSH rigs were removed.
  **E-10 is next**, starting with native extended attributes (`-H` is already
  implemented). R-01 still awaits a distinct Linux LAN target beyond the Pi.


## E-10 progress — 2026-10-09: local extended attributes

- E-10 remains **code**, with P1 still **17/22**. Its `-H` prerequisite is already
  complete. Native local `-X`/`--xattrs`, repeated `-XX` and `--no-xattrs`/`--no-X`
  now handle file and directory xattrs, binary/empty values, supported macOS
  symlinks, stale-attribute removal and attribute-only itemization (`x`).
- Byte-copy and per-file APFS-clone transfers share the metadata updater. Filtered
  attributes carried by a clone are removed as required; whole-directory cloning
  is disabled with `-X` so each entry receives its selected attributes. Without
  `-X`, the documented clone superset remains unchanged.
- Destination updates use anchored file descriptors, including read-only-file
  metadata updates that temporarily add owner write permission and restore it.
  Metadata opens are nonblocking and symlink attributes do not follow referents.
  Copied file attributes are refreshed from the opened source, and source-read failures cannot erase
  destination attributes. `-L` retains rsync's physical-link xattr behavior.
- The local differential suite covers **84 cross-platform cases**, eight macOS
  resource-fork cases and idempotence, checking data, modes, timestamps, hard
  links, binary xattrs, source integrity and successful itemization against rsync.
  The seven cross-platform methods pass on Apple Silicon,
  Rosetta, Linux root and Linux UID/GID 60000. macOS resource-fork checks also
  verify mtime restoration after attribute-only updates. Two unprivileged read-only
  `--inplace` cases verify matching partial-transfer status and final trees;
  rsync reports a planned failed write, while xsync reports completed transfers.
- Existing CVS/merge local regression suites pass. Filter unit tests remain
  **32,940 checks, zero failures** on ARM, Rosetta and Linux. Fallback fixtures
  now use unsupported ACLs to test delegation; xattrs get their own missing-peer
  capability checks, with strict refusal before destination creation and actual
  rsync fallback preserving binary attribute values.
- **Remaining before E-10 completion:** negotiated native remote xattrs and
  cross-platform namespace handling, source-race/resource-fork stress, packaging,
  and the wider metadata scope (`-A`, creation/access times, file flags, `-E`,
  `--chmod`, `--chown`). Current remote `-X` delegates or strictly refuses before
  writes. No installed helper or release artifact has been replaced for this
  partial milestone. R-01 still awaits a distinct Linux LAN host beyond the Pi.


## E-10 progress — 2026-10-09: negotiated remote extended attributes

- E-10 remains **code** and P1 remains **17/22**. Native push/pull `-X` and
  `-XX` now use `PF_XATTRS` (262144), configuration frame 26 and feature-gated
  directory/file attribute records. Protocol 4 remains compatible with the frozen
  protocol-3 Hello and transfers; helpers lacking the feature still refuse or
  delegate before destination writes.
- Source directory/entry attributes follow the selected filter context. Opened
  files send fresh xattrs with each data attempt; whole-file, chunked, delta and
  resumed transfers apply that attempt's attributes at publication. Large-file
  completion records keep metadata with their attempt under its lock, including
  when completion arrives before chunks. Invalid configurations, duplicate/NUL
  names, oversized counts, incomplete values and trailing data are rejected.
  Incomplete source records preserve destination data/attributes and suppress
  deletion with partial-transfer status.
- Push filter forwarding now follows rsync: without deletion, global xattr rules
  select sender values and are omitted at the remote receiver; deletion forwards
  the relevant rules. Destination merge files still load locally. A cross-platform
  check also caught skipped symlinks/specials being treated as absent under
  `--delete`; their source names now guard deletion without copying metadata.
- Source read retries also guard the physical symlink's inode/ctime under `-L`,
  in addition to the opened referent. The sender refreshes file or link attributes
  after a detected change. macOS resource-fork checks now include 16 MiB values
  through local clone/copy and native push/pull paths.
- Verification: **95 local and 172 push/pull differential cases** plus
  idempotence and macOS resource-fork cases pass on Apple Silicon, Rosetta and
  unprivileged Linux (Darwin-only fork cases skip on Linux). Linux root real-SSH
  regressions also pass, followed by xattr trust, source-retry, filter-wire and
  fallback suites. **24 macOS/Linux namespace cases** compare ordinary/internal
  values, filters, symlinks and unsupported-attribute partial status with rsync.
  **18 source-mutation cases** pass on ARM/Rosetta; Linux verifies regular-file
  mutations and skips unavailable symlink xattrs. Four wire-test methods cover
  42 valid/error scenarios; malformed records cannot publish file data or erase
  destination values. Filter units remain **32,940 checks, zero failures** on
  ARM/Rosetta/Linux; nine frozen-peer/capability protocol tests pass. The
  **231-case** byte-copy corpus also passes with fallback disabled and itemization.
- Cross-platform copying now reports partial status when selected incoming
  attributes cannot be written on the destination file type, matching rsync's
  Linux symlink behavior instead of silently discarding values.
- **Remaining before E-10 completion:** wider namespace/collision and privileged
  attribute handling, resource-fork memory scaling across large directories,
  packaging, and the metadata scope beyond `-H`/`-X` (`-A`, creation/access times,
  BSD file flags, `-E`, `--chmod`, `--chown`). No installed helper or release
  artifact has been replaced for this checkpoint. R-01 still awaits a distinct
  Linux LAN host beyond the Pi.


## E-10 progress — 2026-10-09: namespace aliases and memory baseline

- E-10 remains **code**, with P1 at **17/22**. On macOS, a literal attribute
  and an rsync namespace alias can encode the same name. Source reads now retain
  the last enumerated value, matching rsync (`foo` versus `rsync.user.foo`, and
  `user.foo` versus `rsync.user.user.foo`). The empty `rsync.` disguise is skipped
  on macOS; Linux's ordinary `user.rsync.` attribute remains valid.
- Eighteen local/clone/push/pull cases compare aliases, empty namespace prefixes,
  foreign namespaces and internal attributes under `-X`, `-XX` and xattr filters.
  These pass on Apple Silicon, Rosetta and Linux UID/GID 60000, including source
  integrity and itemization checks. The wire format and frozen peer layout are
  unchanged.
- The resource-fork memory check confirms the pending scaling issue: copying
  four distinct 4 MiB forks peaks at **32,342,016 bytes RSS**; 32 forks peak at
  **150,880,256 bytes RSS**. Values are still retained in directory metadata and
  copied into wire frames. This is evidence of incomplete memory scaling, not a
  passing performance claim.
- Verified on the current macOS filesystem that
  `openat(existing_file_fd, "..namedfork/rsrc", O_NOFOLLOW)` opens the resource
  fork through the anchored inode. This supports a streaming implementation
  without reopening the file by a mutable pathname. Disk-backed values and
  bounded remote value frames are the next xattr work; privileged namespaces,
  the wider metadata options and packaging also remain pending.


## E-10 progress — 2026-10-09: bounded xattr storage and remote streams

- E-10 remains **code**, and P1 remains **17/22**. Cached xattr values now share
  their bytes across metadata copies. A process-wide **8 MiB** inline budget
  spills overflow and values larger than **64 KiB** into shared extents in one
  unlinked, mode-0600 temporary file. Freed extents are reused; descriptor use
  does not grow with the number of attributes.
- Large macOS resource forks are read and written through anchored fork file
  descriptors in **64 KiB** chunks. Remote peers negotiate `PF_XATTR_STREAM`
  (**524288**) and use bounded START/CHUNK/END frames with XXH3 checksums before
  metadata references. The xattr producer queue uses an **8 MiB** limit. Frozen
  protocol-3 options and the protocol version remain unchanged; older X-only
  helpers delegate or refuse before destination writes.
- Receiver checks reject bad lengths, overflowing varints, unordered IDs,
  excessive active streams, gaps/overlaps, oversized chunks, duplicate endings,
  incomplete/duplicate references, checksum corruption and unreferenced values.
  Unreferenced streams fail before deletion finalization. Temporary-storage
  failures protect existing files, attributes and deletion candidates; received
  storage failures occur before destination work. Active streams are capped at
  the sender's 64-worker limit; pending value records are capped at 1,048,576.
- On Apple Silicon, **4/32/128 distinct 4 MiB forks** now peak locally at
  **11,304,960 / 11,436,032 / 11,649,024 bytes RSS**, versus the prior
  **32,342,016 / 150,880,256** baseline for 4/32 files. The 128-file directory
  contains **512 MiB** of attribute data; push/pull peaks are approximately
  **59.2 MB**, and 512 files with 32 KiB small attributes peak below **70 MB**.
  Data, exact fork/attribute values, mtimes and source integrity are checked.
  Rosetta passes the same scaling and storage-failure checks. These are fixture
  measurements; directory entry/name metadata still scales with entry count,
  and non-fork platform APIs can require one contiguous attribute value.
- Verification: **19** xattr differential methods pass on ARM and Rosetta;
  **10** hostile-stream/configuration methods pass on ARM, Rosetta and Linux;
  source-retry checks and fallback checks pass on all three. Linux additionally
  copies **5,000 files with 2 KiB attributes** locally and in both remote
  directions under a **64-descriptor** limit, forcing small-value spill.
  Real SSH namespace, attribute-only/idempotence and read-only cases pass.
  The **nine** frozen-peer/capability protocol methods pass. Private temporary
  storage is empty after each scaling transfer.
- Evidence: `/tmp/xsync-e10-stream-memory-final.log`,
  `/tmp/xsync-e10-stream-memory-rosetta.log`,
  `/tmp/xsync-e10-stream-wire-final.log`,
  `/tmp/xsync-e10-stream-linux-final.log`,
  `/tmp/xsync-e10-stream-linux-tests.log`,
  `/tmp/xsync-e10-stream-xattrs-{first,rosetta}.log`,
  `/tmp/xsync-e10-stream-races{,-rosetta}.log`,
  `/tmp/xsync-e10-stream-fallback-{mac,rosetta}.log`,
  `/tmp/xsync-e10-stream-protocol-mac.log`, and
  `/tmp/xsync-e10-stream-real-ssh{,-final}.log` (the first SSH run's namespace
  method passed; its later request for a disabled method was a harness selection
  error, corrected in the final run).
- **Remaining before E-10 completion:** privileged namespace/type behavior,
  the wider metadata options (`-A`, creation/access times, BSD flags, `-E`,
  `--chmod`, `--chown`) and packaging. Installed helpers and release artifacts
  remain unchanged. R-01 still needs a distinct Linux LAN target beyond the Pi.


## E-10 progress — 2026-10-09: privileged Linux attributes and capabilities

- E-10 remains **code**, with P1 at **17/22**. Linux `trusted.*` attributes are
  supported on symlinks, FIFOs, sockets and character/block devices, including
  fresh destination inodes. Source reads now retain selected attributes on those
  types. Receiver operations use `O_PATH | O_NOFOLLOW` and the `/proc/self/fd`
  descriptor link; they address the held inode without opening a device/FIFO or
  following the physical symlink to its referent. Darwin's supported types are
  unchanged.
- Fixed a verified capability-loss case: an otherwise unchanged file had equal
  `security.capability` bytes but different owner/group IDs. Ownership changes
  cleared the destination capability; xsync returned success without restoring
  it, while rsync retained it and itemized an xattr change. Comparisons now account
  for planned ownership changes when the capability is selected, then restore it
  after chown. Excluded capabilities retain rsync's behavior.
- **87 differential cases** pass in an isolated Linux container with
  `SYS_ADMIN`: local/push/pull, trusted attributes on ordinary and special
  inodes, binary values, stale-value removal, `-X`/`-XX`, dry runs, filters,
  `-L`, direct/inplace writes, owner-only/group-only/both ID changes, and mixed
  root/UID-GID-60000 sender/receiver roles. File data, metadata, all visible
  attributes, source integrity and itemization match rsync. Selected attributes
  that an unprivileged receiver cannot remove report the same partial status
  and resulting metadata as rsync.
- The Linux source-retry harness now optionally exercises trusted attributes
  on followed physical symlinks (`XSYNC_TEST_PRIVILEGED_XATTRS=1`). All **18**
  file/link metadata mutations pass across local/push/pull, whole/delta and
  inplace paths, confirming the physical-link ctime guard refreshes metadata.
  The ordinary **19-method** xattr suite passes on ARM, Rosetta and Linux
  (four Darwin-only skips on Linux); Linux hostile-wire and ordinary retry
  checks also pass.
- Evidence: `/tmp/xsync-e10-privileged-final.log`,
  `/tmp/xsync-e10-privileged-linux-races.log`,
  `/tmp/xsync-e10-privileged-linux-regression.log`,
  `/tmp/xsync-e10-privileged-mac-xattrs.log`, and
  `/tmp/xsync-e10-privileged-rosetta-xattrs.log`. The earlier mixed-role fixture
  incorrectly inherited root's defaults path and required success from rsync
  for every selection; the final fixture supplies empty defaults and compares
  rsync's actual 0/23 status.
- **Remaining before E-10 completion:** native ACLs (`-A`), creation/access times,
  BSD flags, `-E`, `--chmod`, `--chown`, and packaging. Installed helpers and
  release artifacts have not been replaced.

## E-10 progress — 2026-10-09: native local ACLs

- E-10 remains **code**, and P1 remains **17/22**. Local `-A`/`--acls` now
  preserves macOS extended ACLs and Linux access/default ACLs. It implies
  `--perms`, while an explicit `--no-perms` retains destination permissions and
  respects inherited restrictions on newly created files. ACL-only changes
  itemize as `a`; mode-only changes do not falsely itemize an ACL change.
- Source ACLs use held descriptors during file transfers and share the bounded
  metadata value cache. Destination ACL reads/writes address held inodes through
  the existing destination directory anchors. FIFO and other supported special
  inodes are handled without opening them for data I/O. Physical symlink ACLs
  are skipped, matching the reference; `-L` carries the referent's ACL.
- Per-file APFS clones apply explicit ACL selection; whole-directory shortcuts
  are disabled with `-A`. ACL handling is independent of xattr filters, including
  `-AX --filter='-x *'`. On Linux this prevents xattr cleanup from removing ACLs
  managed by `-A`. Directory working permissions remain writable while children
  are created and final ACL-linked permission bits are restored afterward.
- **16 differential cases** pass on native ARM and Rosetta macOS; **13** pass
  as both root and UID/GID 60000 on Linux (the three APFS clone cases are skipped).
  Checks include ACL-only updates, stale ACL removal, ordinary xattr selection,
  dry runs, checksum, atomic/direct/inplace/partial paths, inherited ACLs,
  permissions disabled, read-only directories, and exact itemization. A second
  sync produces no changes. Source data and ACLs remain unchanged.
- All **eight** local source-read ACL mutations pass on ARM, Rosetta and
  unprivileged Linux: file/followed-link, whole/delta, and atomic/inplace. The
  retry refreshes the ACL from the held source descriptor. The ordinary macOS
  **19-method** xattr suite remains green after the shared metadata integration.
- Native remote ACL serialization and ID mapping are still pending. Push/pull
  `-A`/`-AX` refuse in strict mode or delegate before any destination write.
  Explicit `--server -A`/`--server --acls` also refuse rather than silently
  dropping the option. The **nine-method** fallback suite passes on ARM,
  Rosetta and unprivileged Linux; its generic unsupported-option fixtures now
  use `-b` because local `-A` is supported. All **nine** frozen protocol-3 and
  feature-subset checks pass; the frozen option layout remains unchanged.
- Evidence: `/tmp/xsync-e10-acls-edges-mac.log`,
  `/tmp/xsync-e10-acls-edges-rosetta.log`,
  `/tmp/xsync-e10-acls-linux-final.log`,
  `/tmp/xsync-e10-acls-linux-root-final.log`,
  `/tmp/xsync-e10-acls-races-mac.log`,
  `/tmp/xsync-e10-acls-races-rosetta.log`,
  `/tmp/xsync-e10-acls-fallback-final.log`,
  `/tmp/xsync-e10-acls-fallback-rosetta-final.log`,
  `/tmp/xsync-e10-acls-xattrs-mac.log`, and
  `/tmp/xsync-e10-acls-protocol.log`. Early retry fixtures accidentally
  reused a regular source path as a symlink and compared Linux ACL xattrs as
  ordinary physical-link attributes; the final fixtures compare referent ACLs
  separately and retain the ordinary xattr checks.
- **Remaining before E-10 completion:** native remote ACLs and principal ID
  mapping, broader ACL flag/identity cases, creation/access times, BSD flags,
  `-E`, `--chmod`, `--chown`, and packaging. Installed helpers and release
  artifacts have not been replaced.

## E-10 progress — 2026-10-09: negotiated remote ACLs and principal names

- E-10 remains **code**, and P1 remains **17/22**. Native push/pull `-A` now
  transfers Linux POSIX access/default ACLs between Linux peers and macOS
  extended ACLs between Darwin peers. Separate capabilities (`1048576` POSIX,
  `2097152` Darwin) select the style; frame **30** confirms ACL configuration.
  Root-directory, file-list and fresh file-data metadata carry ACLs. Protocol
  **4** still supports **3**, and the frozen v3 option layout is unchanged.
- The wire uses bounded semantic records: tags, permissions, flags, numeric
  principals and optional names. Receivers reject invalid counts, overflows,
  missing POSIX base/mask entries, unordered/duplicate POSIX entries, invalid
  flags/tags/permissions, malformed names, inappropriate defaults, and ACLs on
  physical symlinks before metadata or file publication. Darwin ACL objects are
  constructed with ACL APIs from validated fields; opaque remote blobs never
  reach `acl_copy_int`. Cached native values retain the shared metadata budget;
  name caches are bounded at 4096 entries each.
- Named user/group ACL principals map independently of `--owner` and `--group`.
  Unresolved names retain numeric IDs; `--numeric-ids` bypasses name mapping.
  A real-SSH rig with distinct user/group databases passes **30** root
  differentials: local/push/pull, fresh/existing destinations, ordinary and
  numeric mapping, owner/group preservation disabled, and `--no-perms`. These
  include regular files, directories/default ACLs, FIFOs, sockets and devices.
  Data, all ACL bytes, metadata, source integrity and itemization match rsync.
- A verified compatibility wrinkle is retained: rsync's remote receiver parses
  `-A` and re-enables permissions even when the pushing client used
  `--no-perms`. Native push now matches that behavior, while local/pull retain
  destination modes and inherited restrictions. Mode-only cases explicitly
  exercise different existing destination permissions.
- The ACL differential suite passes **53** cases on ARM and Rosetta macOS and
  **50** on unprivileged Linux (three APFS clone cases are skipped). This adds
  **30** push/pull cases and **six** local/push/pull hard-link compositions to
  the local foundation, including compression and `-AX` filters. The hard-link
  checks exposed duplicate `a`/`x` itemization on aliases; those writes are now
  reported on the anchor, matching rsync. The separate hard-link regression
  suite remains green.
- All **16** remote source-read ACL mutations pass on ARM, Rosetta and Linux:
  file/followed-link, whole/delta, atomic/inplace. Fresh ACL records replace the
  scanned metadata on the successful retry. A **five-method** hostile-wire
  suite also verifies name mapping without owner/group, numeric override,
  incomplete-source protection and rejected configurations/styles.
- Fixed combined metadata failure framing: if an ACL read fails after selected
  xattrs were cached, the sender emits an incomplete empty xattr list instead
  of an invalid partially populated list. **Three** Darwin local/push/pull
  failure cases fill the inline xattr budget, deny spill storage for the ACL,
  return **23**, and retain existing data, ACLs, xattrs and deletion candidates.
  The fixture explicitly selects its budget attributes to avoid incidental
  provenance attributes consuming the quota first.
- All **ten** mixed-version/feature-subset protocol checks pass, including new
  frozen-v3 ACL refusals. The **nine-method** fallback and **ten-method** xattr
  hostile-wire suites remain green. Missing or incompatible ACL capabilities
  refuse or delegate before writes; no helper is installed automatically.
- Evidence: `/tmp/xsync-e10-acls-all-final-mac.log`,
  `/tmp/xsync-e10-acls-all-final-rosetta.log`,
  `/tmp/xsync-e10-acls-all-final-linux.log`,
  `/tmp/xsync-e10-acls-name-ssh-final.log`,
  `/tmp/xsync-e10-acls-remote-races-mac.log`,
  `/tmp/xsync-e10-acls-remote-races-rosetta.log`,
  `/tmp/xsync-e10-acls-remote-linux-final.log`,
  `/tmp/xsync-e10-acls-wire-mac-final.log`,
  `/tmp/xsync-e10-acls-wire-rosetta.log`,
  `/tmp/xsync-e10-acls-remote-protocol.log`,
  `/tmp/xsync-e10-acls-hardlink-regression.log`, and
  `/tmp/xsync-e10-acls-root-linux-regression.log`. The first real-SSH fixture
  compared rsync's extra creation banner with itemized rows; the corrected
  fixture compares all metadata and the itemized rows separately.
- **Remaining before E-10 completion:** cross-style ACL conversion and broader
  flag/identity cases, creation/access times, BSD flags, `-E`, `--chmod`,
  `--chown`, and packaging. Installed helpers and release artifacts have not
  been replaced.

## E-10 progress — 2026-10-09: complete Darwin ACL fields and cross-style boundary

- E-10 remains **code**, and P1 remains **17/22**. Native Darwin remote ACLs
  now preserve unresolved UUID allow/deny principals, including UUID bytes
  containing NUL. Tags **5/6** carry exactly 16 bytes with the undefined numeric
  ID; ordinary user/group records continue to map by name. `--numeric-ids`
  leaves UUIDs intact. Capability **4194304** explicitly negotiates this support;
  older Darwin ACL helpers delegate or refuse before writes. Invalid UUID
  lengths/IDs and UUID capability without Darwin ACL capability are rejected.
  Linux does not advertise UUID support. Protocol 4/v3 framing remains unchanged.
- **84** native Darwin cases pass on both ARM and Rosetta: twelve ACL variants
  across local/push/pull, data and metadata-only updates, plus APFS clones. Every
  case checks source integrity, root and file ACLs, data and empty repeat-sync
  output. Variants cover synchronization/all permission bits, both global
  inheritance flags, every entry inheritance flag and unresolved UUID allow/deny
  principals. These native fields are preserved even where rsync's Darwin shim
  drops synchronization/global flags or rejects an unresolved UUID with **23**;
  matching rsync's omission would lose source permissions.
- Strengthened the ordinary ACL differential suite to explicitly compare the
  transfer root's ACL as well as descendants and source integrity. All **seven**
  methods pass on ARM and Rosetta, retaining the existing 53-case differential
  coverage and storage-failure checks. The first expanded fixture incorrectly
  expected child snapshots to contain the root; it was corrected before final
  verification.
- The **six-method** hostile-wire suite passes on ARM and Rosetta, including
  four successful binary UUID allow/deny cases with ordinary/numeric mapping.
  Linux passes all applicable ordinary/wire ACL methods; the opt-in cross-style
  rig and Darwin-only cases skip there. All **ten** mixed-version protocol
  checks pass. The **ten-method** fallback suite passes on ARM and Rosetta,
  including push/pull against a Darwin ACL peer without UUID support.
- Resolved the previously listed cross-style conversion question with an actual
  Darwin/Linux SSH baseline: Homebrew rsync **3.4.4** and Debian rsync **3.2.7**
  reject the tested nontrivial macOS extended/POSIX access/default ACLs with
  **12** in both directions. Native strict mode retains its pre-write **4**
  refusal rather than inventing an access-policy conversion. The durable opt-in
  `tests/acls_cross_test.py` passes **12** push/pull cases: rsync, native strict
  and native fallback, each with fresh/existing destinations. It checks both
  source trees and destination integrity, owns a disposable SSH container bound
  only to localhost, and removes it afterward. Empty/trivial cross-style ACLs
  are not claimed to fail. Cross-style native conversion is outside rsync's
  demonstrated compatibility behavior; the guarded boundary is retained.
- Evidence: `/tmp/xsync-e10-acls-darwin-complete.log`,
  `/tmp/xsync-e10-acls-darwin-complete-rosetta.log`,
  `/tmp/xsync-e10-acls-root-check-final-mac.log`,
  `/tmp/xsync-e10-acls-root-check-final-rosetta.log`,
  `/tmp/xsync-e10-acls-uuid-wire-final-mac.log`,
  `/tmp/xsync-e10-acls-uuid-wire-final-rosetta.log`,
  `/tmp/xsync-e10-acls-uuid-final-linux.log`,
  `/tmp/xsync-e10-acls-uuid-protocol.log`,
  `/tmp/xsync-e10-acls-uuid-fallback-final-mac.log`,
  `/tmp/xsync-e10-acls-uuid-fallback-final-rosetta.log`,
  `/tmp/xsync-e10-acls-cross-final.log`, and the exploratory reference
  `/tmp/xsync-e10-acls-flags-baseline.log`.
- **Remaining before E-10 completion:** creation/access times, BSD flags, `-E`,
  `--chmod`, `--chown`, final metadata composition checks and packaging. Installed
  helpers and release artifacts have not been replaced. `sanjee@neo.local`
  currently fails DNS resolution, so R-01's outstanding physical-host checks
  remain pending.

## E-10 progress — 2026-10-09: native access and creation times

- E-10 remains **code**, and P1 remains **17/22**. Local and native push/pull
  `-U`/`--atimes` now preserve regular/special-inode access times. Repeated `-U`
  enables `--open-noatime`; supported systems request `O_NOATIME` on source,
  checksum, resume and destination-basis reads. macOS has no such read flag and
  ignores it as rsync does. On Linux it can require ownership or privilege.
  Directory and physical-link access times retain rsync's omission.
- `-N`/`--crtimes` now preserves Darwin creation times on regular files,
  directories, physical symlinks and supported special inodes. Creation-time
  writes pin the destination object with event-only descriptors, including
  `O_SYMLINK` for links and nonblocking opens for FIFOs. Atomic file outputs use
  their already-open descriptor. Linux's missing arbitrary birth-time setter
  is rejected before transfer. Directory finalization restores requested times
  after children/deletions; rsync's volume-root creation-time guard is retained.
- Three capabilities negotiate access times (**8388608**), creation times
  (**16777216**, Darwin only) and no-atime reads (**33554432**) outside the
  frozen v3 options. Root, entry and fresh DATA records carry signed time
  fields only when negotiated. Explicit helper time flags also require peer
  support. Protocol **4** still supports **3**; older peers delegate or refuse
  before destination writes.
- Comparisons and changed-value writes use whole seconds, matching rsync.
  Unchanged existing access/create times retain their fractional seconds.
  Checksum reads cannot replace the sender's listed access time. `-O` and `-J`
  omit directory/link time writes, including creation times; rsync still
  itemizes differing omitted creation times. Slot **8** uses `u`, `n` or `b`.
  Hard-link aliases suppress the anchor's creation-time itemization while
  retaining rsync's access-time reporting.
- Per-file APFS clones correct explicitly requested times. Whole-directory
  clone shortcuts are disabled with `-U`/`-N`. Without those options, clones
  retain source access/create times as additional metadata; this is documented
  alongside the existing xattr/ACL superset. Without preservation, access times
  can differ due to incidental reads, and new timestamps are checked against
  the actual transfer clock window rather than compared as fixed metadata.
- The **14-method** time/wire suite passes on ARM and Rosetta (two Linux-only
  methods skip). It includes **113** Darwin differentials: local/push/pull,
  data/metadata-only updates, dry runs, inplace, checksum, omissions, negated
  options, followed links, APFS clones, hard links, ACL/xattr compositions,
  unchanged fractional timestamps, and 3 MiB whole/delta/inplace/resume paths.
  Repeat-sync checks and five wire methods
  verify truncated/overflowing records before publication, fresh time fields,
  unsupported platforms and unnegotiated helper flags. Linux covers **57**
  differentials plus repeat-sync and explicit unsupported-creation checks.
  All **41** Linux time/wire, trust, output and hard-link methods pass, with
  four platform/root skips.
- A disposable real-SSH Darwin/Linux rig passes **four** additional access-time
  differentials (`-U`/`-UU`, push/pull), checking exact destination times, data
  and itemization. Its first output comparison included rsync's destination
  creation banner; the corrected test compares itemized rows separately.
- All **13** macOS trust methods pass, including new local/push/pull access and
  creation-time symlink swaps. Outside data/modes/modification/create times
  remain intact. The broader **53-method** macOS regression run passed every
  method except its obsolete unsupported-`--open-noatime` assertion; that
  assertion was updated for the implemented option and the full trust suite
  rerun successfully. Output, hard-link, ACL and xattr methods passed. All
  **ten** protocol compatibility methods pass with additional time requests
  against feature subsets and the frozen v3 helper.
- Evidence: `/tmp/xsync-e10-times-mac-final.log`,
  `/tmp/xsync-e10-times-rosetta-final.log`,
  `/tmp/xsync-e10-times-linux-final.log`,
  `/tmp/xsync-e10-times-cross-final.log`,
  `/tmp/xsync-e10-times-trust-final-mac.log`,
  `/tmp/xsync-e10-times-regression-mac.log`,
  `/tmp/xsync-e10-times-option-check.log` and
  `/tmp/xsync-e10-times-protocol.log`. Initial probes exposed a blocked FIFO
  open, conflicting symlink open flags, checksum-induced atime drift, and
  unnecessary fractional-time writes; these were corrected and retested.
  The Linux trust fixture initially lacked a passwd entry for UID 60000; final
  verification runs as a real disposable rig user. Semantics were checked
  against [rsync's official manual](https://download.samba.org/pub/rsync/rsync.1)
  and its 3.4.4 source.
- **Remaining before E-10 completion:** BSD flags, `-E`, `--chmod`, `--chown`,
  final metadata composition checks and packaging. Installed helpers and
  release artifacts have not been replaced.


## E-10 progress — 2026-10-09: native executability

- E-10 remains **code**, and P1 remains **17/22**. Native local/push/pull
  `-E`/`--executability` now preserves regular-file execution state with
  `--perms` disabled. Non-executable sources clear execute bits; executable
  sources add execution rights to destination read classes only when no
  execution rights already exist. Existing read/write/special bits are retained;
  new files use the usual source mode and umask. `--perms` takes precedence,
  and archive mode does not imply `-E`. Physical links/directories/special
  inodes are unchanged; `-L` handles regular referents. Mode-only changes use
  rsync's `p` itemization, and dry runs do not write.
- **Negotiation and fresh metadata:** `PF_EXECUTABILITY=67108864` is outside
  the frozen protocol-3 option layout and is requested only when needed. Older
  helpers delegate or refuse with code 4 before destination writes. When `-p`
  makes `-E` redundant, older/subset peers can still transfer normally. An
  explicit helper `-E` cannot silently disappear if the client did not negotiate
  it. Local source retries and remote fresh DATA modes compute execution rights
  from the original destination mode, preserving its original execution classes
  even after a prior plan cleared them. No new file-list/DATA fields are needed.
- **Verification:** `tests/executability_test.py` has **36** rsync differential
  transfers over local/push/pull paths, with a matrix of **9** source modes and
  **12** destination modes. Coverage includes existing/new files, data and
  metadata-only changes, set-ID bits, empty-directory/symlink replacements,
  `--perms` precedence, `-L`, checksum, in-place, dry-run, hard-link anchors and
  aliases, and `-AX` composition. Another **6** native cases retain unreadable
  destination modes on byte replacement. `tests/executability_race_test.py`
  verifies **24** source-mode mutations across local/push/pull, whole/delta and
  atomic/in-place retries. Wire tests verify **4** listed/fresh mode combinations
  and unnegotiated explicit helper refusal. The protocol suite has **11** passing
  methods against frozen protocol 3 and feature subsets, including redundant
  `-pE` success. Fallback checks verify strict refusal and original-argument
  delegation. The receiver trust fixture now swaps a destination leaf for an
  outside symlink during an `-E` permission update in all three directions.
- **Real SSH:** `tests/executability_cross_test.py` owns and removes its
  disposable Linux container and SSH keys. **6** Darwin/Linux rsync differentials
  cover both directions with plain `-E`, `-pE` and dry-run, checking exact file
  modes, contents and itemized output. Opt in with `XSYNC_ACL_CROSS_RIG=1`.
- **Documented compatibility boundaries:** a native byte replacement that needs
  no readable basis retains the original destination permissions; rsync's
  receiver can instead treat an unreadable basis as a new file. Native `-E`
  follows modern rsync's executability meaning. Apple's system rsync uses `-E`
  for extended attributes; fallback retains the original arguments, so use
  `--executability` for unambiguous delegation. README/help now describe the
  option and the boundary. Semantics were checked against rsync 3.4.4's
  `dest_mode()` implementation and its official manual.
- **Logs:** ARM macOS **17** test methods, Intel macOS **6** executability methods,
  Linux **45** methods (four platform skips), and the **11** protocol methods
  pass. Separate macOS time/hard-link/output regressions pass **28** methods
  (two Linux-only skips). Logs are `/tmp/xsync-e10-executability-mac-final.log`,
  `/tmp/xsync-e10-executability-rosetta-final.log`,
  `/tmp/xsync-e10-executability-linux-final.log`,
  `/tmp/xsync-e10-executability-protocol.log`,
  `/tmp/xsync-e10-executability-regression-mac.log`, and
  `/tmp/xsync-e10-executability-cross.log`. Early fixtures incorrectly expected
  rsync to accept `--no-E`, used an unresolved macOS fault-hook path, and
  requested owner/group mapping from a minimal peer; those were corrected.
  A misspelled trust-test class in two runners was corrected and rerun; the
  trust method also passed separately on both platforms.
- **Remaining before E-10 completion:** BSD flags, `--chmod`, `--chown`, final
  metadata composition checks and packaging. Installed helpers and release
  artifacts have not been replaced. Installed rsync variants do not expose
  `--fileflags`; upstream's separate `fileflags.diff` does not apply cleanly to
  rsync 3.4.4, so the next milestone needs a compatible flags reference rather
  than treating an unknown option as a successful comparison.


## E-10 progress — 2026-10-09: negotiated BSD file flags

- E-10 remains **code**, with P1 at **17/22**. Native local/push/pull
  `--fileflags` preserves Darwin `st_flags` on regular files, directories and
  special inodes. Physical symlinks are skipped; `-L` preserves referents.
  Archive mode does not imply flags, and `--no-fileflags` disables them. Flags
  add a twelfth `%i` character only when requested (`f` for changed flags).
  Directory flags are finalized after children/deletions; immutable/append
  flags on new files wait until checked data closure and publication, and on
  hard-link anchors until aliases exist. Existing immutable receivers are not
  implicitly made writable for data replacement. Failed or silently ignored
  flag writes report exit 23, including compression/synthetic bits that Darwin
  accepts without applying. All flag setters use pinned, non-following FDs.
- **Protocol:** `PF_FILEFLAGS=134217728` leaves the frozen protocol-3 layout
  intact. Root/entry and fresh DATA flags are separately negotiated bounded
  32-bit fields; malformed/truncated/overflow values fail before publication.
  Fresh source flags survive retries. Older helpers strictly refuse with code 4
  or delegate once before writes. Linux CLI requests fail with code 1 and a
  raw advertised flags capability fails with code 4 before writes; no BSD/Linux
  flag translation is invented. Structured output validates the negotiated
  itemization width. Installed helpers and release artifacts remain unchanged.
- **Clone handling:** APFS clones carry source flags even without the option.
  New cloned immutable/append flags are temporarily cleared before metadata
  writes/rename, then restored using the pinned inode; hard-link clones restore
  them after alias publication. Failed source validation can clean up its clone.
  Whole-directory cloning is disabled when per-entry flag handling is requested.
  README/help document the clone superset and native/fallback boundaries.
- **Reference:** standard rsync 3.4.4 and the system rsync lack `--fileflags`.
  `tests/build_fileflags_reference.py` reproducibly builds rsync **3.3.0** with
  upstream `fileflags.diff` at patch commit
  `10ab5e57446d10ef641ceb045ef3094e7d2bd439`, checking pinned archive/patch
  SHA-256 hashes and applying every hunk without fuzz in a disposable directory.
  It never installs a binary; use its printed path as `XSYNC_FILEFLAGS_RSYNC`.
  The recipe was executed successfully; log:
  `/tmp/xsync-e10-fileflags-reference-recipe.log`.
- **Reference defect retained as evidence:** that upstream patch writes flags
  before atime but reads flags after atime in `flist.c`. With `-U --fileflags`,
  a source atime of 1200000000 and `UF_HIDDEN` can become destination atime 128
  and an invalid flags request `0x868c0047`, causing exit 23. A minimal pinned
  reference regression reproduces it. **11** native combined U/N/ACL/xattr/H
  transfers instead check exact flags, timestamps, data and identities against
  independently captured expectations. No reference code was patched to make
  the comparisons pass. Creation-time combinations without U still compare
  native data/metadata and itemized output directly against that reference.
- **Verification:** **56** rsync differential transfers cover local/push/pull,
  bytes/clones, metadata-only updates, new files, FIFOs, physical/followed links,
  hard links, N/AX/E composition, checksum, in-place, deletion, dry-run,
  unchanged output, option cancellation and existing immutable failures.
  Another **4** native immutable hard-link transfers and one no-option clone
  check verify publication/restoration ordering. **24** source-flag mutation
  cases exercise whole/delta and atomic/in-place retries in all directions.
  Wire cases cover nine malformed root/entry/DATA fields, four listed/fresh
  flag combinations, three failed/ignored flag values and explicit helper
  negotiation. Older-helper tests verify refusal and flags-capable fallback.
  Receiver symlink swaps now check outside flags as well as data/modes/times.
- Composition found and fixed duplicate time itemization through shared inodes:
  requested destination flags/access/creation times are refreshed after an
  earlier metadata-only alias update, even without H. **6** modern rsync
  shared-inode time differentials pass on each macOS architecture; the **3**
  supported Linux cases also pass. The fixture resets directory mtimes after
  creating links and compares fixed alias metadata, excluding unrequested
  current-clock creation times on unrelated new files.
- **Logs:** ARM macOS **58** methods (three skips), Intel macOS **17** flags
  methods (one skip), Linux **44** methods (18 platform skips), plus one shared
  time method on each platform pass. Logs are
  `/tmp/xsync-e10-fileflags-mac-verified.log`,
  `/tmp/xsync-e10-fileflags-rosetta-verified.log`,
  `/tmp/xsync-e10-fileflags-linux-verified.log`, and
  `/tmp/xsync-e10-fileflags-shared-times{,-rosetta,-linux}.log`.
  The feature/frozen protocol suite passed **11** methods; a separate pre-final
  metadata regression passed **57** (two skips). Earlier incorrect flag-update
  and clone assumptions, and the U/reference composition failure, were resolved
  and rerun rather than counted as passing. The supplied `sanjee@neo.local`
  target still fails DNS resolution; R-01 physical-host coverage remains open.
- **Remaining before E-10 completion:** `--chmod`, `--chown`, final metadata
  composition checks and packaging. No complete-story count has been advanced.

## E-10 progress — 2026-10-09: native incoming permission overrides

- E-10 remains **code**, with P1 at **17/22**. Native local/push/pull transfers
  and listings now implement `--chmod`. Numeric modes, comma-separated symbolic
  rules, `D`/`F` selectors, repeated options, set-ID/sticky bits, conditional `X`
  and omitted-class umask semantics match rsync. Existing entries retain normal
  `--perms`/`--executability` precedence; physical symlinks remain unchanged.
- **Data paths:** overrides apply once to incoming modes, including fresh modes
  after a source retry and explicitly configured helper rules. Per-file APFS
  clones validate and apply fresh permissions; whole-directory clones are
  disabled when overrides require per-entry processing. Roots, nested entries,
  relative cut points, file lists and renamed single-file destinations are
  covered. No new wire fields or capability are required: frozen protocol-3 and
  feature-subset peers continue to use their existing mode fields.
- **Composition fixes:** shared destination inodes refresh basic metadata after
  an earlier alias update. Their xattr comparisons are captured per source before
  writes in the directory plan, including differing source values. Existing
  `-H` aliases report a metadata-only anchor's shared xattr update. POSIX access
  ACL writes consume basic permission itemization while separate special-bit
  and default-ACL changes retain the appropriate `p`. Temporary directory access
  no longer substitutes temporary group/other permissions into ACL setup.
  Pull-side overrides reconstruct implicit owning-group ACL access from the
  received mode, matching rsync's direction-dependent behavior.
- **Verification:** `tests/chmod_test.py` covers **110** Darwin and **120** Linux
  rsync differential transfers, with eight source and five destination modes,
  existing/new data, metadata-only updates, FIFO/symlink handling, clone,
  checksum, in-place, dry-run, hard links, ACL/xattr combinations, listing and
  source integrity. Another **six** native cases finalize restrictive directory
  modes after children, and **16** invalid grammars fail before writes.
  `tests/chmod_race_test.py` checks **36** source-mode mutations across all three
  directions, whole/delta and atomic/in-place writes. Linux ACL cases exercise
  both data and metadata updates with `-p`, without `-p` and with `-E`.
- **Real SSH and compatibility:** `tests/chmod_cross_test.py` owns and removes
  disposable Linux containers and keys; **eight** Darwin/Linux differentials
  check modes, bytes and output in both directions. The **12** protocol methods
  pass, including **four** chmod cases against frozen/subset peers. The supplied
  `sanjee@neo.local` target still fails DNS resolution; R-01's physical-host
  checks remain open.
- **Passing logs:** ARM and Intel chmod suites each pass **13** methods with
  two POSIX-only skips, with the **36** mutation cases passing separately on
  both architectures. Darwin metadata regressions pass **63** methods (one
  Linux-only skip); Linux chmod/race/ACL/xattr/hard-link/executability/output
  regressions pass **57** methods (six platform skips). Logs:
  `/tmp/xsync-e10-chmod-mac-complete.log`,
  `/tmp/xsync-e10-chmod-intel-complete.log`,
  `/tmp/xsync-e10-chmod-mac-verified.log`,
  `/tmp/xsync-e10-chmod-intel-verified.log`,
  `/tmp/xsync-e10-chmod-metadata-final.log`,
  `/tmp/xsync-e10-chmod-linux-final3.log`,
  `/tmp/xsync-e10-chmod-protocol-final.log`, and
  `/tmp/xsync-e10-chmod-cross-final.log`. Initial restrictive-root/relative-path
  fixtures, ACL interactions and a missing ACL-negotiation guard were corrected
  and rerun; failing runs are not counted as passing evidence.
- **Documented boundary:** native pinned directories can complete transfers
  whose final root loses search permission; rsync can instead report a partial
  transfer after losing pathname access. README/help describe native overrides
  and this behavior. Installed helpers and release artifacts are unchanged.
- **Remaining before E-10 completion:** `--chown`, final metadata composition
  checks and packaging. No complete-story count has been advanced.

## E-10 progress — 2026-10-09: native incoming ownership overrides

- E-10 remains **code**, with P1 at **17/22**. `--chown=USER:GROUP` now works
  in local/push/pull transfers. Names resolve on the receiver; numeric IDs,
  omitted/empty fields, disjoint repeated fields, `--numeric-ids` and normal
  privilege checks are supported. Unknown receiver names warn without changing
  the successful transfer status; overlapping fields and numeric overflow fail
  before writes. Source data, basic metadata, ACLs and xattrs remain unchanged.
- **Data paths and compatibility:** roots, entries, metadata-only updates,
  whole/delta retries and per-file APFS clones apply incoming overrides.
  Whole-directory clones are disabled. Capability `PF_CHOWN` guards the bounded
  receiver configuration and complete entry identities; protocol-3 and older
  feature-subset helpers refuse or delegate before writes. Empty overrides
  remain compatible. Explicit helper options require negotiation and overlapping
  client/helper fields fail before writes. Pulling helpers retain source IDs.
- **Fresh identities:** sender retries describe newly encountered UID/GID names
  before their DATA records. Four real-SSH Mac-to-Linux group mutations use
  deliberately different numeric group IDs to verify receiver name mapping
  after whole/delta and atomic/in-place retries. Another **36** Linux root
  ownership mutations verify overrides and fresh omitted fields in all three
  directions. Oversized/truncated configurations and root/entry/DATA identity
  overflow fail before file publication.
- **ACL composition:** explicit overrides map named principals even with
  `--numeric-ids`. Linux accepts ordered duplicate named identities when distinct
  principals map to the same ID; stable sorting preserves their relative order,
  and a subsequent ordinary `-aA` transfer can read them again. This corrects
  the earlier blanket duplicate rejection: duplicate base entries and descending
  named identities still fail validation. Three Darwin deny-delete differentials
  verify exit 23 and preservation of existing data when a mapped ACL prevents
  publication.
- **Verification:** the main matrix covers **64** Darwin, **68** non-root Linux
  and **77** root Linux rsync differential transfers. It includes ownership-only,
  data, dry-run, in-place, H/AX/chmod composition, option order and clones.
  Six unknown-name cases, six invalid arguments, three explicit native helper
  cases and malformed-peer checks supplement it. Real SSH adds **10** normal
  ownership differentials and a contradictory-option boundary check.
  Intel ownership/wire/ACL tests pass **20** methods (one platform skip), Linux
  root mutation/ownership/wire/ACL tests pass **21** (two skips), Linux non-root
  metadata regressions pass **80** (ten skips), and protocol/fallback tests pass
  **24**. Logs: `/tmp/xsync-e10-chown-intel-verified.log`,
  `/tmp/xsync-e10-chown-linux-root-verified.log`,
  `/tmp/xsync-e10-chown-linux-user-verified.log`,
  `/tmp/xsync-e10-chown-compat-verified.log`, and
  `/tmp/xsync-e10-chown-cross-final.log`.
  ARM ownership/wire/ACL/xattr/H/chmod/time/executability/output regressions
  also pass **88** methods (four skips), recorded in
  `/tmp/xsync-e10-chown-metadata-verified.log`. Initial wire fixtures omitted
  name-map negotiation; they were corrected and rerun before counting results.
- **Documented boundaries:** with a pushing client's later `--no-owner` or
  `--no-group`, rsync can omit identities then attempt owner/group 0 on its
  receiver, failing for non-root group changes. Native negotiated transfers
  retain identities and apply the requested receiver override. Local/pull
  transfers honor later disabling options. README describes this distinction.
  Installed helpers and release artifacts have not yet been updated.
- **Remaining:** final metadata composition and packaging. Combined dry-run
  checks exposed missing permission/ownership/time/ACL markers on existing
  hard-link aliases; this must be repaired before E-10 can be marked complete.

## E-10 progress — 2026-10-09: combined metadata and output checks

- Existing hard-link aliases now retain their planned permission, ownership,
  time, ACL and xattr markers during dry-run. Actual linked-inode updates still
  report the completed anchor's shared metadata writes. The combined preview
  originally differed from rsync in all three directions and now matches.
- Regular-file output captures original destination identities in the transient
  output object. Whole/delta retries compare final incoming ownership against
  those identities, adding or clearing owner/group markers correctly. This adds
  no per-entry file-list memory. **72** root Linux mutation cases cover local,
  push and pull, atomic/in-place writes, user/group/both overrides, initially
  matching source IDs and initially matching final IDs.
- `tests/metadata_composition_test.py` checks **10** Darwin and **nine** Linux
  rsync differentials combining H/AX/U, chmod/chown and, on Darwin, N/flags.
  Modes, identities, bytes, ACLs, xattrs, times, hard-link identities and the
  ordinary itemized fields match modern rsync. Flags are checked independently
  against source stat because of the upstream U/flags defect recorded above.
  Dry-run leaves destination metadata/data unchanged. The Darwin clone case
  clears set-ID bits with its incoming rule and verifies zero transferred bytes
  for the changed file, so it exercises an actual clone. Blocking source flags
  are applied after all shared-inode times have been set in the fixture.
- Passing logs: `/tmp/xsync-e10-composition-mac3.log` (**28** methods, three
  skips), `/tmp/xsync-e10-composition-mac-verified.log` (**24**, one skip),
  `/tmp/xsync-e10-composition-intel-verified.log` (**24**, one skip),
  `/tmp/xsync-e10-composition-linux-final.log` (**16**), and
  `/tmp/xsync-e10-composition-mac-clone.log`. Initial fixture atime observations
  and immutable aliases were corrected; the production preview and fresh-ID
  output failures were reproduced, repaired and rerun.
- **Remaining before E-10 completion:** release builds, packaged metadata
  checks and installation/manual verification. P1 remains **17/22**.

## E-10 progress — 2026-10-09: static worker-stack regression

- Packaged musl binaries exposed a crash in xattr equality: two automatic
  64 KiB comparison buffers exhausted a worker's small stack, even for inline
  attributes. The reproducible ARM debugger backtrace reaches
  `XattrValue::operator==` from `xattrs_differ`/`generate`; development builds
  and basic release smoke transfers had passed. E-10 was kept open.
- Equality now compares inline values directly and allocates stored-value
  buffers on the heap only when needed. Stored-value streaming/import buffers
  also use the heap. The 8 MiB inline quota, 64 KiB chunks and shared unlinked
  spool remain unchanged.
- `tests/xattr_value_test.cpp` exercises inline/stored/mixed comparisons,
  differing stored bytes, allocation, import and streaming on a **64 KiB**
  pthread stack. The old musl implementation exits **-11**, while the fix
  passes. Linux release builds compile and run this regression before exporting
  binaries; Docker/source packages include its source. The macOS universal
  target also passes. README lists the regression command.
- The patched musl ARM build passes **11** composition/ownership/quota methods
  (one Darwin-only skip), including **5,000** xattr files in each direction and
  a 64-descriptor limit. Darwin composition/resource-fork regressions pass
  **four** methods (one Linux-only skip), with per-process RSS below **70 MiB**
  for the tested 512 MiB resource-fork directory and inline overflow. Logs:
  `/tmp/xsync-e10-static-debug2.log`,
  `/tmp/xsync-e10-stack-musl-baseline2.log`,
  `/tmp/xsync-e10-stack-arm-verified.log`, and
  `/tmp/xsync-e10-stack-mac-verified.log`.
- **Remaining:** rebuild the clean release set and repeat packaged checks.
  The failing pre-fix release runs are not counted as passing evidence.

## E-10 completion — 2026-10-09: metadata and release verification

- **Done; P1 is 18/22.** H/X/A/E/U/N, BSD flags, chmod and chown now have
  native implementations with documented platform/clone boundaries. Requested
  remote metadata negotiates before destination writes; unsupported styles,
  platforms and older helpers refuse or delegate. Protocol-3 compatibility is
  retained. The preceding progress entries contain individual metadata,
  mutation, malformed-peer and real-SSH evidence.
- Final composition covers data, metadata-only, whole/delta retries, in-place,
  atomic writes, actual APFS clones, hard links and dry-run output. The linked
  alias preview, fresh ownership itemization and static worker-stack defects
  found during composition/packaging are repaired and verified.
- Clean releases built from **38bc6f9fcfd9**: macOS arm64/x86_64 universal,
  Linux musl amd64 and Linux musl arm64. Both Linux build stages run the
  small-stack metadata regression. Standalone scratch startup and Debian smoke
  transfers pass; the macOS executable has no third-party dynamic dependencies.
  `dist/manifest.json` records each release's revision, size and SHA-256.
- Both Linux release binaries pass **16** packaged composition/ownership/wire/
  quota methods (one Darwin-only skip each), including 5,000-file xattr spill
  transfers in all directions. The final universal binary passes combined
  metadata checks on both ARM and Intel. Installation into a disposable prefix
  passes the **two** executable/manual/live-completion methods; its executable
  and all three bundled releases match the verified bytes and manifest.
- Logs: `/tmp/xsync-e10-clean-releases.log`,
  `/tmp/xsync-e10-clean-package-linux-amd64.log`,
  `/tmp/xsync-e10-clean-package-linux-arm64.log`,
  `/tmp/xsync-e10-clean-package-native-metadata.log`,
  `/tmp/xsync-e10-clean-package-intel-metadata.log`, and
  `/tmp/xsync-e10-clean-package-install.log`. The source archive and local
  Homebrew formula are regenerated, including the small-stack regression.
  Physical-host checks remain under R-01; `sanjee@neo.local` still fails DNS
  resolution. No helper was installed on that target during these transfers.

## E-11 progress — 2026-10-09: native sparse transfers

- **Sparse milestone complete; E-11 remains in progress and P1 is 18/22.**
  `-S`/`--sparse` now handles local, push and pull transfers; `--no-sparse`
  and `--no-S` cancel it. File/directory cloning is disabled when sparse
  allocation is requested. `--link-dest` is next; the other backup options
  retain their existing rsync fallback.
- New outputs skip zeroes; reused inodes clear previous data with aligned
  hole punching and ordinary writes for partial edge blocks. Unsupported
  punching falls back to writing zeroes. EOF, metadata, hard links, verified
  partial prefixes and delta checksums remain correct. A 64 KiB allocation
  pass joins zeroes split across delta blocks and handles APFS allocation
  during file growth. It reads allocated extents when supported, otherwise
  the whole output. Write-only in-place files still accept whole-file copies;
  they can retain extra allocation when refinement cannot read their data.
- Sparse capability **536870912** and bounded one-byte configuration frame
  **32** leave the protocol-3 options layout unchanged. Unsupported helpers
  refuse with exit 4 before writes or delegate once. Malformed, oversized,
  unnegotiated and listing configurations fail before publication. Explicit
  helper options also require negotiation; cancelled sparse flags work with
  frozen and capability-subset peers.
- Differential coverage against **rsync 3.4.4**: **120** ordinary sparse
  cases, plus **six** write-only cases, across local/push/pull. These verify
  bytes, EOF, allocation, mode/IDs/times and itemization for zero/mixed/trailing
  regions, empty/small files, whole/delta/in-place writes, checksum, compression,
  dry runs, cancellation and H/AX/chmod composition. Native `--no-perms`
  retains a write-only destination's mode; reference rsync changes it to the
  source mode. The fixture checks this explicit boundary independently.
- **Five** signal/disconnect cases retain a verified halfway prefix and resume
  with correct allocation and metadata. **Twelve** source-growth/shrink cases
  verify fresh EOF and data across atomic/in-place local/push/pull copies.
  Real SSH passes **24** native allocation/data/metadata transfers. The C++
  regression verifies unaligned zeroing without erasing neighbors, EOF,
  invalid offsets, offsets beyond **4 GiB**, and allocation after file growth.
  Linux release builds run it before exporting binaries; source packages
  include its source.
- macOS sparse checks pass **nine** methods (one real-SSH skip), with the clone
  policy regression passing separately. Linux root sparse/config/fallback
  checks pass **39** methods (three platform/permission/SSH skips); nonroot
  sparse checks pass **nine** methods (one SSH skip), plus the separate Linux
  clone regression. Protocol compatibility passes **14** methods. Delta and
  metadata/ownership regressions pass **30** methods. New guard checks pass
  separately; the real SSH method passes in the isolated two-container rig.
- Logs: `/tmp/xsync-e11-sparse-mac-verified.log`,
  `/tmp/xsync-e11-sparse-linux-verified.log`,
  `/tmp/xsync-e11-sparse-linux-nonroot-verified.log`,
  `/tmp/xsync-e11-sparse-clone-verified.log`,
  `/tmp/xsync-e11-sparse-linux-clone-verified.log`,
  `/tmp/xsync-e11-sparse-protocol.log`,
  `/tmp/xsync-e11-sparse-regressions.log`,
  `/tmp/xsync-e11-sparse-guards-verified.log`, and
  `/tmp/xsync-e11-sparse-ssh.log`. Debian's rsync 3.2.7 produced incorrect bytes
  in eight remote sparse/in-place cases; rebuilding the primary 3.4.4 source
  with ACL support resolves those reference failures. Failed diagnostic runs
  are not counted as passing evidence.


## E-11 progress — 2026-10-09: native snapshot reuse

- `--link-dest` now supports local/push/pull, up to 20 ordered receiver-side
  roots, relative paths, explicit root symlinks, single-file destination names,
  files-from/relative selections and dry runs. Regular files, symlinks, FIFOs
  and source hard-link groups can share unchanged prior inodes. Data matches
  with differing requested metadata produce independent local copies; changed
  large files use read-only prior snapshots for deltas, including `--inplace`.
- Matching covers requested permissions/executability, ownership, timestamps,
  xattrs, ACLs and BSD flags. Sparse and H/AX/chmod composition is covered.
  Basis roots and descendant parents are pinned, descendants reject symlink
  traversal, and atomic publication validates inode identity, times and metadata.
  Cross-device link failures copy independently. Swapped leaves, leaf symlinks,
  pinned-parent replacements and metadata changes cannot publish unchecked links.
  Prior data/mode/IDs/mtime/xattrs/ACLs remain unchanged for fresh snapshots;
  basis reads may naturally advance atimes without O_NOATIME. Already shared
  destinations retain ordinary rsync update semantics.
- Capability **1073741824** and configuration frame **33** preserve the frozen
  protocol-3 layout. Receiver roots are bounded to 20 and wire payloads to 1 MiB;
  source-role configs contain zero roots. Oversized, malformed, NUL-containing,
  wrong-role, unnegotiated and listing configs fail before writes. Empty paths
  warn and skip. Frozen/subset peers refuse requested snapshots before writes;
  list-only requests need no snapshot capability. Unsupported-peer fallback
  delegates once with the original arguments.
- Snapshot differential/fault checks against rsync 3.4.4 pass **13 methods**
  (one real-SSH skip) on macOS and Linux, including Linux nonroot. Existing-destination guard checks pass separately on macOS; the expanded
  Linux suite passes **14 methods** (one SSH skip).
  Coverage includes repeated itemization, checksum/ignore-times/size-only,
  multiple and maximum roots, metadata inheritance, root aliases,
  symlink/FIFO and hard-link fixtures.
  Device-node fixtures remain outside this snapshot corpus.
- Explicit differences: native -U requires matching requested atimes before
  sharing, while reference rsync can share and update the prior inode's atime.
  If every snapshot path is unavailable, native newly created directories use
  ordinary new-directory itemization rather than rsync's dummy-basis comparison.
- Broader sparse/delta/metadata/hard-link/wire/fallback regressions pass
  **72 methods** (one real-SSH skip); protocol compatibility passes **15 methods**.
  Real SSH passes snapshot reuse followed by a changed 8 MiB delta in each
  direction, with wire totals below 1 MiB and prior snapshots unchanged, plus
  **24** sparse transfer checks. No physical helper was installed.
- Logs: `/tmp/xsync-e11-linkdest-mac-verified.log`,
  `/tmp/xsync-e11-linkdest-linux-verified.log`,
  `/tmp/xsync-e11-linkdest-linux-nonroot.log`,
  `/tmp/xsync-e11-linkdest-regressions.log`,
  `/tmp/xsync-e11-linkdest-protocol.log`, and `/tmp/xsync-e11-backup-ssh.log`.
  E-11 remains in progress until universal/static releases are rebuilt and tested;
  P1 remains **18/22**. R-01 still needs reachable physical-host targets.


## E-11 complete — 2026-10-09: packaged sparse and snapshot transfers

- **Done; P1 is 19/22.** Native -S and --link-dest cover the backup workflows;
  backup/backup-dir, compare/copy-dest, append, remove-source-files and preallocate
  continue using the established rsync fallback. Strict mode rejects those
  delegated options before transfer. E-12 is next; R-01 remains open.
- Clean universal macOS and musl Linux amd64/arm64 artifacts identify source
  commit **c5d66ab422d0**. Linux binaries pass the scratch-image and release smoke
  checks, including sparse and xattr worker-stack units during their builds.
  The macOS executable contains both architectures and no third-party dynamic
  dependencies. All three artifacts are recorded in dist/manifest.json.
- Packaged snapshot/sparse/metadata checks pass **22 methods** (one SSH skip)
  on both macOS ARM and Intel. Intel fault tests re-inject the universal test
  library after arch launches, so cross-device and replacement faults actually
  run. Packaged Linux checks pass **39 methods** (one permission skip) for each
  static architecture, covering snapshot differentials, sparse allocation,
  metadata composition and wire guards. Static Linux cannot use LD_PRELOAD;
  replacement and EXDEV injection are verified with the corresponding dynamic
  Linux build rather than counted as static-artifact failures or successes.
- The final dynamic Linux snapshot suite passes **14 methods** (one SSH skip).
  Existing/ignore-existing/update guards preserve their normal precedence over
  prior snapshots; the independent macOS guard method also passes.
  The macOS universal sparse C++ unit passes, and installation into a disposable
  prefix passes **two methods** for executable/manual/completion behavior.
- Logs: `/tmp/xsync-e11-clean-releases.log`,
  `/tmp/xsync-e11-release-mac-arm.log`,
  `/tmp/xsync-e11-release-mac-intel2.log`,
  `/tmp/xsync-e11-release-linux-amd64-verified.log`,
  `/tmp/xsync-e11-release-linux-arm64-verified.log`,
  `/tmp/xsync-e11-release-sparse-unit.log`,
  `/tmp/xsync-e11-release-install.log`,
  `/tmp/xsync-e11-linkdest-linux-final.log`, and
  `/tmp/xsync-e11-linkdest-dest-guards2.log`.
  Failed diagnostic runs are excluded from this evidence. Releases and the
  source archive are local artifacts; no remote helper was installed or PR pushed.


## E-12 progress — 2026-10-09: macOS edge-case regressions

- Socket creation now uses a short temporary Unix bind name in the pinned
  receiver parent and atomically renames it to the requested leaf. A small
  child changes cwd, leaving the threaded receiver's cwd untouched. Failure
  paths report exit 23 and remove temporary nodes. Long socket filenames,
  ordinary a/H/X metadata, hard-link aliases and link-dest reuse are verified.
  Darwin cannot open socket vnodes, so hard-link/snapshot publication validates
  their pinned-parent identity and the temporary inode rather than requiring
  O_EVTONLY. Unchanged socket BSD flags need no write; unsupported socket ACL,
  changed creation-time and changed-flag requests report errors explicitly.
- Dataless SF_DATALESS flags are requested even without --fileflags. Known
  dataless directories/files bypass whole-directory/per-file cloning; per-file
  clones recheck the source and reject a dataless result before publication.
  Ordinary reads then perform the data transfer. Synthetic flags verify actual
  read calls and the absence of clone calls, with resident controls confirming
  the clone path still runs. Real cloud hydration is a separate opted-in fixture
  using XSYNC_ICLOUD_FILE; it is skipped here because no file was supplied.
- Immutable existing destinations retain inode/data/mode/flags/mtime when
  atomic or in-place replacement fails, matching rsync's exit 23. Deep source
  paths beyond the filesystem's PATH_MAX also return 23 and a path-length
  error; the macOS rsync 3.4.4 reference rejects the same deep paths.
- The macOS-specific suite passes **10 methods** (one real-cloud skip), covering
  local/push/pull, failed binds, pinned-parent replacement, socket aliases,
  long names, snapshot reuse, metadata limits, immutable writes, dataless policy
  and deep paths. Broader hard-link/snapshot/metadata/namespace regressions pass
  **21 methods** (one SSH skip); Linux regressions pass **20 methods** (one SSH
  skip). Logs: `/tmp/xsync-e12-mac-final4.log`,
  `/tmp/xsync-e12-regressions.log`, and `/tmp/xsync-e12-linux-regressions.log`.
  E-12 remains in progress for release validation; P1 remains **19/22**.


## E-12 complete — 2026-10-09: release validation

- **Done; P1 is 20/22.** All four requested macOS edge cases have regression
  fixtures and documented behavior. E-13 is next; R-01 still needs the physical
  host clarification/reachability checks. The real iCloud download fixture is
  available but skipped without an explicitly selected cloud file; synthetic
  file/directory flags verify clone exclusion and ordinary reads independently.
- Clean releases identify source **92186d817578**. The universal executable
  passes macOS-specific, hard-link, snapshot and metadata checks on ARM and
  Intel: **29 methods** each, with the real-cloud and real-SSH fixtures skipped.
  Directory-only dataless flags prevent directory cloning while allowing checked
  resident per-file clones. Actual interposition runs on both architectures.
- Static Linux amd64/arm64 checks pass **36 methods** each: hard links, snapshot
  differentials, metadata composition and wire guards. Build-time sparse and
  small-stack xattr units and the scratch/transfer release smoke tests pass.
  dist/manifest.json records all three artifacts; the source package is refreshed
  after this journal update. No physical helper or installed local binary was
  changed.
- Logs: `/tmp/xsync-e12-clean-releases.log`,
  `/tmp/xsync-e12-release-mac-arm.log`, `/tmp/xsync-e12-release-mac-intel.log`,
  `/tmp/xsync-e12-release-linux-amd64.log`, and
  `/tmp/xsync-e12-release-linux-arm64.log`.

## E-13 progress — 2026-10-09: diagnostic output cancellation

- Confirmed the original failure: a closed stdout pipe could return success and
  let copying continue. Stdout writes and flushes now record the first failure,
  request cancellation, and report diagnostic I/O exit **13**. Help/version and
  final summaries use the same exit behavior. Silent/quiet transfers and an
  empty output format do not require a stdout reader.
- Pipe closure is checked during local worker waits and transport waits/pacing,
  including when non-terminal file events remain sorted in memory. Cancellation
  signals a tracked remote child once, serializes process cleanup, and avoids
  killing a reused PID. A repeated test exposed duplicate SIGTERM delivery that
  could bypass helper cleanup; cancellation is now idempotent.
- Closed-before-start, first-line closure, closure during paced transfers,
  listing, dry-run and help/version fixtures cover local/push/pull. Temporary
  outputs are removed; --partial retains a completed prefix and resumes on a
  later run. Linux also exercises /dev/full diagnostic failures. Rsync's
  --outbuf=N makes fwrite observe EPIPE directly for the exit-13 comparison;
  some libc/iconv builds otherwise ignore a failed fflush and return success.
- Initial macOS closure and output/error/pacing suites pass **8 methods** (one
  Linux-device skip) and **37 methods** respectively. Protocol/fallback/trust
  regressions pass **30 methods**. Linux output/error/pacing/closure regressions
  pass **45 methods**. E-13 remains partial pending the repeated cleanup checks,
  final real-SSH run and release validation; P1 remains **20/22**.
- Final development verification: the macOS cancellation/cleanup pair passes
  **five repeated runs**, including local/push/pull and partial resume. The real
  two-container SSH run passes **8** closure methods, **2** transfer/interrupt
  methods and **10** output methods. Remote SIGINT shutdown peaks at **0.339s**.
  Final Linux regressions pass **45 methods**; the macOS output/error/pacing
  regressions pass **37 methods**. Logs:
  `/tmp/xsync-e13-mac-final4.log`,
  `/tmp/xsync-e13-mac-cancellation-repeat.log`,
  `/tmp/xsync-e13-real-ssh-final2.log`,
  `/tmp/xsync-e13-linux-regressions-final.log`,
  `/tmp/xsync-e13-mac-regressions-final.log`, and
  `/tmp/xsync-e13-protocol-regressions.log`.
- Release validation found a separate fatal-path race in the simultaneous
  timeout fixture: amd64 returned 30 but could exit before the diagnostic was
  printed. Closing the peer let connection-loss reporting race the timeout
  owner. Connection loss now checks/join-waits the active timeout path before
  reporting another fatal error. Source/release validation is being repeated;
  E-13 is still partial.

### R-01 reachability follow-up — 2026-10-09

- The earlier physical Neo checklist remains valid evidence; its log is
  `/tmp/xsync-r01-pi-native.log`. Neo is a Raspberry Pi running Linux on the LAN.
  The pending clarification is whether Neo plus the isolated Linux SSH rig is
  the intended coverage, or a second physical Linux host is also required.
- Fresh SSH attempts to the supplied `sanjee@neo.local` still fail name
  resolution. A bounded mDNS lookup produced no address, and the SSH config and
  Neo's trusted host-key aliases contain no usable IP override. The same
  reachability issue has persisted through the E-09, E-10, E-11 and E-12
  checkpoints. A reachable IP/target is needed for additional physical checks;
  the existing request for that information remains pending. No helper was
  installed or changed on a physical host during E-13.

## E-13 complete — 2026-10-09: release validation

- **Done; P1 is 21/22.** Closed diagnostic pipes cancel local and remote copies
  promptly and return **13**, with a stderr diagnostic. File cleanup, partial
  resume, silent/quiet transfers, listing and help/version output are covered.
  The adjacent simultaneous-timeout race also preserves its single diagnostic
  and exit 30. R-01 is the only remaining P1 story, awaiting the physical-host
  clarification/reachability information recorded above.
- Clean release artifacts identify source **3b686e385923**. macOS ARM and Intel
  each pass **43 methods** (one Linux /dev/full skip); static Linux arm64 passes
  **43**, and static Linux amd64 passes **47**, including four additional runs
  of the four-case simultaneous-timeout fixture. Each artifact is checked
  against dist/manifest.json's source revision and SHA-256.
- Static artifacts cannot use Linux LD_PRELOAD, and the Intel launcher does not
  preserve ordinary DYLD injection. Two existing interposition methods are
  excluded from the artifact suite and independently pass in development:
  Linux's complete output/error/pacing/closure suite passes **45 methods**, and
  macOS's closure/pacing suite plus five repeated timeout methods passes **29**
  (one Linux-device skip). Earlier macOS output/error/pacing and protocol/
  fallback/trust checks pass **37** and **30** respectively.
- Final real SSH verification passes **8** closure methods, **1** simultaneous
  timeout method and **2** transfer/interrupt methods; maximum measured remote
  SIGINT shutdown is **0.336s**. The output suite also passed **10 methods** in
  the preceding real-SSH run. Build-time Linux xattr/sparse units and scratch/
  transfer smoke checks pass. macOS xattr/sparse units pass on ARM and Intel.
- Logs: `/tmp/xsync-e13-clean-releases-final.log`,
  `/tmp/xsync-e13-release-mac-arm-final.log`,
  `/tmp/xsync-e13-release-mac-intel-final.log`,
  `/tmp/xsync-e13-release-linux-amd64-final.log`,
  `/tmp/xsync-e13-release-linux-arm64-final.log`,
  `/tmp/xsync-e13-timeout-cancellation-final.log`,
  `/tmp/xsync-e13-linux-regressions-final2.log`, and
  `/tmp/xsync-e13-real-ssh-final3.log`. The source package is refreshed after
  this completion entry. No installed local executable or physical helper was
  changed.
