# xsync backlog — from benchmark winner to daily driver

Initial audit written 2026-10-08 against xsync 0.1.0 (protocol 1).
All fifteen P0 stories completed against protocol 3; per-story evidence is below.
P1 R-02 through R-09 and E-01 through E-07 are complete (15 of 22 stories). Current protocol 4 supports protocol 3; E-08 is in progress.
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
| E-08 | **Filter completeness.** Global rule sides, single/per-directory merge files, `-F`, merge modifiers, global CVS rules/`-C`, and `--delete-after` reloading newly transferred receiver merge files are implemented. Remaining: `-m`. The prune-empty case is the remaining difftest failure. | **in progress** | 231/231 difftest (expanded from 159); a differential fuzzer against rsync for the new rule kinds, checked into `tests/`. | L |
| E-09 | **`--files-from`, `-R`, `--from0`.** Common in backup scripts and with `find … -print0`. | code | Implemented for local and remote, including the "implied directories" semantics of `-R`. | L |
| E-10 | **Metadata beyond `-a`.** `-H` hard links, `-X` xattrs, `-A` ACLs, `-N` creation times, `-U` atimes, BSD file flags, `-E`, `--chmod`, `--chown`. Also an inconsistency to resolve: the clone path already carries xattrs and ACLs while the byte-copy and remote paths drop them. | code | `-H` and `-X` first (most used on macOS). Without `-X`, both paths behave the same — either strip on clone or document that clones are a superset. | XL |
| E-11 | **Backup-style options.** `--backup`/`--backup-dir`, `--link-dest`, `--compare-dest`, `--remove-source-files`, `--append`, real `-S` sparse handling, `--preallocate`. | code | Prioritise `--link-dest` (snapshot backups) and `-S`; the rest fall back to rsync via R-02 until needed. | L |
| E-12 | **macOS specifics.** Dataless iCloud files (reading triggers a download; cloning may not), immutable (`uchg`) destination files, sockets (rsync creates them, xsync skips silently), paths beyond `PATH_MAX` (tested to 40 levels only). | unverified | One test each; behaviour documented where it differs. | M |
| E-13 | **Broken stdout.** `xsync -av … \| head` — rsync dies on EPIPE; xsync's behaviour is unknown. | unverified | Exits promptly with the right code and does not keep copying silently. | S |

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
