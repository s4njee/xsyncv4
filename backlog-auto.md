# Backlog: automated xs-c++ work on congress transfer time

The work list of the automated loop on branch `auto-cpp`. Every item aims at one number: the time xs-c++ takes to copy
**real-congress** from the Mac to mars over the direct link (216,518 files in 52,593 directories, 1.16 GB: about
5 KB a file and four files a directory, so per-file and per-directory costs rule, not bandwidth).

How the loop uses this file:

- An engineer (Claude Code, run headless) takes the first item marked **todo**, implements it on top of the newest
  commit of `auto-cpp`, and commits it there once xs builds and its tests pass. It edits `src/` and `tests/` only.
- Each committed item is raced against its parent commit on real-congress, Mac→mars, fresh and no-op, 8 blocks each.
  The results go to `auto-cpp/results/<item>/` and its row below is updated with the verdict and the commit.
- An item that makes congress slower stays in the chain (later items build on it) and is entered in
  [regression.md](regression.md) as needing a revert.
- While one item is being raced, the engineer implements the next.

The items came from the analysis of xs-c++'s profiles and of the lab's runs on 21 October 2026. Their evidence names
the lab's experiments (N3, H0, H1b, P2b, H21, MA7). Items that cannot help this link are kept at the end, not
scheduled.

| # | Item | Expected on congress | Size | State | Commit | Verdict (fresh / no-op) |
|---|---|---|---|---|---|---|
| A1 | Remove the receiver's global output lock | fresh: large | ~130 lines | todo (written, uncommitted) | | |
| A2 | Parallel final directory pass | fresh: large | ~80 lines | todo (written, uncommitted) | | |
| A3 | Batch NEED frames across directories | fresh, no-op: small | ~100 lines | todo | | |
| A4 | Stream fresh subtrees without per-directory NEEDs | fresh: large | ~300 lines | todo | | |
| A5 | Stage a fresh subtree and rename it into place once | fresh: medium | ~200 lines | todo | | |
| A6 | Persistent per-directory index for no-op syncs, part 1: the index | no-op: large (with A7) | ~400 lines | todo | | |
| A7 | Persistent index, part 2: compare root hashes and walk only what differs | no-op: large | ~400 lines | todo | | |

States: **todo**, **building**, **testing**, **kept** (faster or no worse), **regression** (slower: see
regression.md), **failed** (did not build or pass its tests in three tries; skipped, and the next item goes on).

## A1 · Remove the receiver's global output lock

- **Where:** `src/fs.cpp`: `out_open`, `out_abort`, `out_finish`, `clone_copy`, `cleanup_open_outputs()`; `src/fs.h`.
- **Change:** they all hold one `std::recursive_mutex` (`output_mu`) across `openat(O_CREAT)`, metadata, `futimens`,
  `close` and `renameat`. Replace it with a shared lifecycle lock that `cleanup_open_outputs()` takes exclusively. Give
  the `open_outputs` registry its own small mutex, keyed by a unique id rather than the fd number, since a closed fd
  can be reused by another worker before its entry is erased. App sessions keep exclusive locking.
- **Why:** N3 small-flat, Mac to mars: the transfer phase stayed flat from recv1 to recv16 (2.96 to 3.23 s) while the
  receiver's write_ns grew with the worker count (2.9, 5.9, 12.1, 47 s): about 18 µs per file serialized (30 µs with
  the rename), a cap of 35k to 56k files a second. Congress is 216k files.
- **Risk:** interrupt cleanup of temporary files and partials must stay correct. No wire change.
- **Note:** written in worktree `~/projects/xsyncv4-receiver-locks` (branch `engine/receiver-locks`), with A2,
  not yet committed; its regression tests are running there. Take that change as this item once it is committed,
  rather than writing it again. A draft experiment is `benchmarks/experiments/LK1-receiver-locks.toml` there.

## A2 · Parallel final directory pass

- **Where:** `src/fs.cpp`, `finalize_tree()`.
- **Change:** it runs serially on the main thread and opens each directory by walking from the root
  (`destination_open_dir`, about 8 `openat` and `close` per directory). Process one depth at a time, deepest first,
  with each depth's directories in parallel. Sort siblings together so they share one open parent descriptor (one
  `openat` each). Use an `unordered_set` for `dirty` instead of a linear `std::find`.
- **Why:** 1.31 to 1.45 s in every small-deep run (N3, H0, H1b, P2b), 25 to 29% of the best wall time. Congress has
  52,593 directories.
- **Risk:** parents must still get their modes after their children: a barrier per depth keeps that. App sessions and
  the root directory stay serial.
- **Note:** written with A1 in `~/projects/xsyncv4-receiver-locks`; take it from there once committed.

## A3 · Batch NEED frames across directories

- **Where:** `src/remote.cpp`, `generate_dir` and the sender's `on_need`.
- **Change:** coalesce the NEEDs for many small directories into one frame, behind a new `PF_` feature bit; a peer
  without it gets one frame per directory as now.
- **Why:** congress averages four files a directory, so it sends tens of thousands of small NEED frames: CPU and thread
  wakeups on both ends (the receiver showed about 200k voluntary context switches on small-deep).
- **Risk:** a wire change, so it must keep working against an older xs (the interop tests cover this).

## A4 · Stream fresh subtrees without per-directory NEEDs

- **Where:** `src/remote.cpp`: `generate_dir` / NEED, and the sender's `on_need`.
- **Change:** when the receiver reports that a directory does not exist, nothing in it needs comparing. Have it say so
  once for the whole subtree, and the sender stream that subtree's listing and data together without waiting for a
  NEED per directory. Behind a new `PF_` feature bit.
- **Why:** a fresh congress copy is 52,593 new directories: this removes a round trip, CPU and wakeups for each.
- **Risk:** a wire change; `--delete` and filters must behave as before inside a fresh subtree.
- **Depends:** after A3 (it subsumes part of it).

## A5 · Stage a fresh subtree and rename it into place once

- **Where:** the receiver's output path (`src/fs.cpp`) for subtrees A4 marks fresh.
- **Change:** write a fresh subtree into a staging directory beside its destination, as final names, and rename the
  subtree into place once at the end, instead of a temporary file and a rename per file.
- **Why:** removes about 216k renames from a fresh congress copy, and makes the first copy of a subtree atomic.
- **Risk:** interacts with `--delete`, filters and interrupted copies (a staged subtree must be cleaned up or resumed).
- **Depends:** A4.

## A6 · Persistent index for no-op syncs, part 1: the index

- **Where:** new `src/index.cpp` / `src/index.h`, used by the sender's and the receiver's listing.
- **Change:** keep a per-directory hash tree on each side, keyed by inode, mtime, ctime and size (like git's index):
  written after a sync, read before the next, invalidated when any key changes. Nothing uses it for decisions yet;
  tests check it matches a fresh scan.
- **Why:** most real re-syncs change nothing, and congress's no-op push has been 0.74× rsync, with 408.8 s of CPU
  against rsync's 18.8 s (H21).
- **Risk:** the index files' durability and invalidation; it must never be trusted when it might be stale.

## A7 · Persistent index, part 2: walk only what differs

- **Where:** `src/remote.cpp` (listing and generate), behind a new `PF_` feature bit.
- **Change:** exchange root hashes first, and descend only into subtrees whose hashes differ; a matching root ends a
  no-op sync at once.
- **Why:** turns congress's no-op from a full walk of 216k files into a comparison of hashes.
- **Risk:** a wire change and a new source of wrong answers if the index is stale: fall back to a full walk whenever
  either side's index is missing or doubtful.
- **Depends:** A6.

## Not scheduled for this link

Kept from the same analysis; each needs another link or a person.

- **Cheaper destination path walks on Linux** (`openat2(RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS)` in
  `src/destination.cpp`, ~60 lines): mars, congress's receiver, runs macOS. For a Linux receiver (MA7's no-op pull
  spent most of 187 s of kernel CPU in `openat`). Complements branch `engine/dest-anchors`.
- **Writeback control** (`sync_file_range` early, one `syncfs` at the end, ~40 lines): Linux receivers only (P2b,
  about 1.15×).
- **TCP transport, then large writes** (`--transport=tcp`, branch `transport`, commits `dd867d7a` and `6fb1e19b`, not
  yet raced; then ~1 MiB blocking writes in `Conn::writer`): helps large files at 10 GbE and weak senders, not
  congress's small files on this link. Unencrypted, for trusted links only.
- **Several receiver processes over multiple TCP streams**: large; depends on A1, A2 and the TCP transport, and is
  worth doing only if A1 and A2 leave a per-process ceiling (4 tar processes reached 37k files/s against xs's 19k).
- **Compression for slow links** (a trained zstd dictionary, or long-range mode): fewer bytes matter only where bytes
  are the limit, such as lab2's internet link.
- **Out of scope for an automated engineer:** zfs or btrfs send/receive when both ends match, SquashFS or EROFS
  images, lazy materialization through FUSE or FSKit, similarity-based deltas.
- **Tried before with no gain:** splice, MSG_ZEROCOPY, sendfile, io_uring (about 4%, before the lock and walk costs
  were removed), fallocate, compressing metadata frames, dedicated writer threads.
