# xs performance roadmap — learning from xsync v1

Written 2026-10-10 against source revision `0af4dbe` (benchmarked binary
`415900091024`). This roadmap covers backlog tier P3 (performance). It sets out
what xsync v1 (`s4njee/xsync`, the earlier Rust implementation) learned by
experiment and what xs's own first measurements show. From both it derives an
ordered plan of experiments and tuning work.

The backlog says *what* is open (F-01 … F-14). This document says *in what
order to attack it and why*. Every recommendation below names the evidence it
rests on. Where a statement is a hypothesis drawn from reading the code
rather than from a measurement, it says so.

Citation convention: `v1:path` is a file in `s4njee/xsync`. Unprefixed paths
are in this repository.

---

## 1. Where xs stands today

### 1.1 The first verified SSH matrix

The first paired neo ↔ freya run is
[`benchmarks/results/20261010T144748Z-715fa0-summary.md`](benchmarks/results/20261010T144748Z-715fa0-summary.md).
It ran over 1 GbE, warm caches, with three samples per tool, and every sample was
verified. The topline:

| Observation | Evidence |
|---|---|
| **Uncompressed transfers are at parity, not ahead.** mixed `-a` gives 1.01× / 1.04×. Large 2 GiB `-a` gives 1.00× both ways at ~114 MB/s, which is the NIC ceiling. | summary table |
| **The only clear wins come with `-z`**: mixed 1.12× / 1.28×, large pull 1.20×. Large push is only 1.03×. | summary table |
| **CPU is 1.6–8× rsync's.** Large fresh: 20.1 vs 12.5 s. Mixed push no-op: 0.554 vs 0.071 s. Mixed push checksum: 3.160 vs 0.402 s. | summary table |
| **Peak RSS is 7–20× rsync's.** 106–298 MiB vs 14–18 MiB. | summary table |
| **The full congress corpus (914,106 files) is a wall-time draw that costs ~4× the CPU.** Fresh push: xs 125.2 / 126.5 s, rsync 142.5 / 122.7 s. The freya receiver used **485–507 s CPU (396–414 s system)** against rsync's 83 s. Peak RSS was **990–1001 MiB** on the receiver and 543–550 MiB on the client, against 89 / 47 MiB for rsync. Voluntary context switches on the receiver: 6.2–6.3 M vs 0.46–0.49 M. | `…-congress-push.json` (2 of 3 runs; the case is still incomplete) |
| **`-c` on large files is slower.** The pull ran at 0.65× (3.986 vs 2.585 s), with CPU about equal (1.230 vs 1.105 s), so the gap is stalls, not compute. | summary table |
| **The tiny-file fixed cost is about equal:** 0.96× / 1.14×. | summary table |
| **The link cipher is chacha20-poly1305 in both directions.** | `…-ssh-cipher.json` |

### 1.2 The local APFS lead has regressed

The historical README table (pre-P0, M1 Max APFS, 76,838 files) showed a
no-op of **0.40 s vs rsync's 0.77 s** (1.9× faster).

The 2026-10-10 diagnostic on the same slice is
[`…-apfs-baseline-summary.md`](benchmarks/results/20261010T152712Z-apfs-baseline-summary.md).
It shows xs **1.8–3.2× slower** than rsync at every thread count: j4 is 2.861 vs
1.613 s, and j1 is 5.146 vs 1.626 s. Its CPU grows from 4.9 s (j1) to 18.1 s (j8).
That host was loaded and the volume was 98% full, but rsync slowed down
only ~2× against history on the same machine (0.77 → 1.61 s) while xs slowed
down 7–9× (0.40 → 2.86 s at j4, 3.47 s at j8). The regression is
relative, not environmental.

The stack profile (`…-j1-profile.txt`) puts 1,556 of 2,476 worker samples in
`openat`. Those calls come from repeated walks anchored at the destination root.
That is the price of the T-13 symlink-race hardening as currently implemented
(see §3.1).

### 1.3 What this means

On the real targets the network or the disk is the ceiling, and xs reaches
it at much higher CPU and memory cost than rsync. On the Raspberry Pi
(4 cores, 4 GiB) that cost is the difference between "faster" and "slower" once
anything else is running. The P3 headline is therefore **efficiency first,
then throughput**. Ideas that buy throughput (more streams, more threads) will
not help while each operation costs several times what it should.

---

## 2. What xsync v1 learned

v1 ran a long, well-instrumented tuning programme (T0–T8, stories 0.x–8.x, and
the R-series). Its lessons fall into three groups: changes that won big,
ideas that were measured and lost, and mistakes in method.

### 2.1 Changes that won

| v1 change | Measured effect | Source | Status in xs |
|---|---|---|---|
| **Probe reflink support once per destination; do not spawn per-file clone attempts** | ext4 0.572 → 0.192 s (2.98×), turning a 1.93× loss into a 1.67× win over rsync | `v1:benches/results/tuning/T1/perf-profile-20260828/README.md` | **No Linux clone path at all.** xs uses a plain `read`/`pwrite` loop (`src/local.cpp:712-731`); no `FICLONE` or `copy_file_range` |
| The reflink probe must clone a real *source* file into the destination. A `st_dev` comparison is wrong: btrfs subvolumes reflink across device IDs | XFS congress-1m went from 1.61× slower to 1.07× faster | `v1:benches/results/mars-local-fs/README.md` | Applies when F-05 lands |
| **Native `clonefile(2)` for whole directories** | 109,615 files: 23.6 s → 3.8 s (6.3×) | `v1:…/T1/hash-and-100k-20260828/README.md` | Done (`clone_leaf`, ≤4096 entries) |
| Clone thresholds are per file and per subtree, not universal | Per-file clone wins above ~12 MiB. Directory clone wins only below ~4–7 MB of missing subtree | `v1:…/T1/DECISION.md`, `v1:…/T3/CROSSOVER.md` | Relevant to F-10 |
| **Batch small files and pipeline the protocol** | deep-small over SSH 8.731 → 0.343 s (25.5×) | `v1:benches/results/story-8.1/DECISION.md` | Done (1 MiB DATA blocks, DIR/NEED pipelining) |
| Sender read-ahead plus a receiver apply pool of `min(cores, 8)` | 2.05× and 1.2–1.6×; congress-100k to freya 26.3 → 8.46 s | `v1:legacy/BENCHMARKSv3.md` | Present, but the receiver uses up to **16** threads |
| **Adaptive compression from a sampled payload** (zstd-3, 64 KiB sample, keep only if it saves ≥5%) | 1.66× on congress-100k. Incompressible data added 0% to wire bytes | `v1:legacy/backlogv4.md` (4.28), `v1:benches/results/story-0.5` | **Missing.** xs compresses every block at level 3 and discards the result if it didn't shrink (`src/remote.cpp:698-713`) |
| Remove synchronous per-chunk acks on large files | Push went from 62.9 MB/s to line rate; pull came within 2% of rsync | `v1:legacy/backlogv4.md` (4.60–4.65) | Large files are at parity. **Delta still does a synchronous round trip per file** (`remote.cpp:1324-1332`) |
| Multiple streams *for large files only* | Stripe crossover: 4 MiB 0.98×, 16 MiB 1.41×, 64 MiB 1.94×, many-small **0.90×** | `v1:benches/results/story-4.3/stripe-crossover.md` | F-03 is unbuilt |
| Do not fsync per file in metadata stores | `--checksum` 4.09 → 0.21 s (19×) | `v1:legacy/BENCHMARKSv3.md` | Not applicable yet (xs has no persistent store) |

### 2.2 Ideas that lost: do not repeat without new evidence

| Idea | Why it lost | Source |
|---|---|---|
| io_uring for the create/write path | The entire available win was 0.028 s of 0.653 s (4%) | `v1:…/T1/io-uring-spike-20260828/README.md` |
| Dedicated writer threads, deeper write queues, fsync cadence, `sync_file_range` | All flat (writer queue depths 2–32 within noise; `sync_file_range` gave 0.7%) | `v1:legacy/backlogv4.md` (4.67) |
| Hash caching / temp-path hash caching | Within noise | `v1:…/T1/DECISION.md` |
| Making hashing cheaper | Skipping hashing entirely changed wall time by 0 ms (APFS 2.515 vs 2.513 s) | `v1:…/T1/hash-and-100k-20260828/README.md` |
| Dispatch affinity / queue sharding | Only a 2.04% prize once the reflink fix landed | `v1:…/T7/DECISION.md` |
| Multiplexed logical streams over one ssh connection | 8.01 vs 7.54 s: slower | `v1:legacy/backlogv4.md` (4.28) |
| More ssh connections for many-small trees | 0.90× at 4 streams. Windows was 1.44–1.53× slower. `--streams 16` hits OpenSSH `MaxStartups` | `v1:…/story-4.3/stripe-crossover.md`, `v1:docs/OS.md` |
| zstd level 9; level 1 | Level 9 doubles time. Level 1 is only 5% faster than level 3 | `v1:legacy/backlogv4.md` (4.28) |
| Unconditional compression (`rsync -az` style) | 1.8–2.4× losses on incompressible data, and +191% on one corpus | `v1:legacy/BENCHMARKSv4.md` |
| A persistent destination index to skip scanning | 1.09 GB RSS and a 12.96 s build on congress-1m; failed both gates | `v1:…/T4.1/README.md` |
| Streaming without a pre-scan | First file 22.4 → 0.0 s, but 14% slower overall | `v1:backlog.md` |
| `fallocate` preallocation | No speed gain (kept only for reducing fragmentation) | `v1:legacy/exotic.md` |

Two v1 results conflict with xs and need re-measuring rather than inheriting:

- **`getattrlistbulk`.** v1's prototype ran at 0.73× its portable walker
  (`v1:benches/results/story-0.3`). xs's historical numbers credit it for the
  APFS lead. Neither result has been measured under xs's current anchored-walk
  design.
- **APFS thread count.** v1's T7 (warm, 10k files) peaked at 4–5 workers.
  BENCHMARKv2 (cold, 1M files, USB APFS) peaked at 8. xs's loaded run was best at
  j4. v1's own conclusion: *core count is a poor predictor*.

### 2.3 Lessons about method

v1's benchmarks said "environment impersonated code three times"
(`v1:legacy/BENCHMARKSv3.md`). Each item below cost v1 a result:

1. **Prove the binary.** The first T7 experiment was void because it measured a stale
   build. xs's CI already rejects a reference that is not the pinned clean
   revision. The neo/freya runner should enforce the same for staged binaries.
2. **Warm-up is real.** Settled runs were 1.9× faster than first runs. Discard or
   label the first pass; v1 used `first_pass` / `warm` / `cold_evicted`.
3. **Cache state swings results 2–7×.** Warm vs cold mount walks were 44.6 vs 101.6 s,
   and warm caches produced a fake 12-worker plateau. On ZFS, a reset command is
   not proof of a cold cache; ARC residency must be checked (this is already noted in
   `benchmarks/README.md`).
4. **Measure time to durable.** rsync exits with ~2.4 GB of dirty pages, while v1 had
   ~2.6 MB (`v1:legacy/backlogv4.md` 4.64). Wall time at exit flatters whichever
   tool leaves more in the page cache. On macOS, use `F_FULLFSYNC`, not `sync(2)`.
5. **Noise gate.** MAD/median above 15% marks a case as noisy and unusable for a gate.
   Use at least 5 samples; 3 only by exception.
6. **Check the environment for each run:** load average (v1 saw 265), disk fullness
   (APFS at 98%), QLC SLC-cache cliffs (1.6× drift), Pi thermal drift
   (18.1 → 27.1 s), and stale DHCP addresses (a fake "Pi defect").
7. **Profilers mislead.** `strace -c` blamed futex for 70.8% of the time, but removing the mutexes did
   nothing. Use stacks with frame pointers, and confirm any profile hypothesis
   by a timed A/B.
8. **Fewer syscalls ≠ proportionally faster.** Cutting syscalls by 44% bought
   13% of wall time because the materialization floor dominated. Know the floor before you
   optimise towards it.
9. **Use real trees, not synthetic smoke corpora, for performance work.** Real trees
   enumerate ~10× slower.
10. **Wire it into CI.** v1's gate was never wired into CI, and CI was never green
    (`v1:backlog.md`). xs already has F-02 in CI; keep it green, and extend it
    instead of building a parallel harness.

---

## 3. Diagnosis: where xs's extra cost likely goes

These hypotheses come from reading the code. Each one is tied to an experiment in
§5 that confirms or refutes it before any change is merged.

### 3.1 Destination operations repeat a full anchored walk

`destination_path()` (`src/destination.cpp:74-89`) runs on every
destination stat, open, mkdir, chmod, chown, times, hash and delta basis. Each call
normalises the path, `dup`s the root fd, and `openat`s **every component** from the
root, closing each one in turn. A file at depth *d* costs *d* `openat`/`close` pairs per
operation, and several operations per file.

`reject_name_collisions` (`src/names.cpp`) re-walks once per directory, and
does so twice for lazily created directories. On macOS its result is never
cached.

This explains:

- the APFS profile (`openat` in 63% of samples);
- the freya receiver's ~400 s of system time and 6 M context switches on a tree 417k
  directories deep and wide, with 16 threads walking shared ancestors;
- the CPU cost of the no-op and checksum cases.

The fix keeps T-13's guarantee. Hold an `O_NOFOLLOW` dirfd per directory
being worked on, and do child operations relative to it, which is the `openat`-relative
design T-13 itself names. Cache `NameRules` per device.

### 3.2 Global output serialization

`out_open`, `out_finish`, `out_abort` and `clone_copy` all take one
`std::recursive_mutex output_mu`. `out_write` takes a shared lock on
`output_io_mu` for every write (`src/fs.cpp:1305-1634`). File creation and
publishing are therefore serial across all workers, which would also explain why more
threads add CPU without adding throughput.

### 3.3 Memory retention

- The receiver keeps every `RDir`, with its full listing, `need` vector and hash containers,
  until the end-of-run check (`src/remote.cpp:2324`). The same applies to
  `final_directories`. This is O(tree) memory, consistent with ~1 GiB at 914k files.
- `pack()` resizes each frame to `ZSTD_compressBound` and then shrinks it, so
  capacity stays at ~1 MiB per queued frame. The send queue counts `size()`, not
  capacity (`remote.cpp:316`, `:698-713`). With compressible data, a
  "48 MiB" queue can pin several hundred MiB. This matches the `-z` push peaks of
  292 MiB (large) and 298 MiB (mixed).
- The local q1 cap is 200,000 *tasks* of up to 64 files each
  (`src/local.cpp:847`), which is effectively unbounded.

### 3.4 Serial `-c` hashing

- The sender hashes every regular file in a directory, one after another, before the
  DIR frame leaves (`remote.cpp:1031-1039`).
- The receiver hashes same-size files serially inside `generate()`.
- Neither side overlaps its hashing with the other's.

This explains the large-file `-c` pull at 0.65× with equal CPU.

### 3.5 Defaults that differ from rsync's choice

- **Local delta is on by default.** Any existing destination file over 1 MiB is
  reconstructed through block matching and then re-read for verification
  (`src/local.cpp:650-683`). rsync uses `-W` for local copies, because the disk is cheaper
  than the matcher.
- **Threads clamp at 16** (`src/local.cpp:30-40`), so freya's receiver runs 16 workers.
  v1 found its receiver apply pool flat beyond 8 (1 → 11.45 s, 8 → 8.75 s, 16 → 8.80 s,
  `v1:legacy/backlogv4.md` 4.27) and shipped `min(cores, 8)`. Under the
  contention described in §3.1–3.2, extra workers add system time without throughput.
- **Compression has a fixed level and is not adaptive** (see §2.1).

---

## 4. Ground rules for every experiment

These carry forward v1's methodology. Most are already in `benchmarks/README.md`.

- **One question per experiment.** Write the hypothesis, the metric and the
  decision rule before running it.
- **Paired and rotated.** Run xs and rsync in alternating order in the same session.
  Gate on the ratio to rsync, never on absolute wall time across sessions.
- **Verify every sample independently** (`rsync -anci --delete`).
  A tool that exits 0 with a wrong tree fails the run.
- **Report wall, CPU (split by client and peer), peak RSS and context switches.**
  A win on wall time that costs 4× CPU is not a win on the Pi.
- **Label the environment:** source revision, binary hash, filesystem,
  free space, load, cache state (`first_pass`/`warm`/`cold_evicted`),
  ARC/page-cache snapshot (`benchmarks/snapshot.py`) and link cipher.
- **At least 5 samples.** Report MAD/median and treat anything above 15% as
  inconclusive.
- **Record time to durable** (`syncfs`/`F_FULLFSYNC` after exit) next to time to exit for
  write-heavy cases.
- **Make decisions with an A/B on the target, not with a profile.**
- **Make knobs runtime-tunable for experiments.** Today every constant
  (`BLOCK_TARGET`, `MAX_Q`, thread clamp, zstd level, `DELTA_THRESHOLD`…) is a
  compile-time value (`src/remote.cpp:56-57, 248`, `src/delta.h:7`), which makes
  sweeps expensive. Add an undocumented `XSYNC_TUNE=key=value,…` read once at
  start-up, recorded in `--version -vv` and in the result JSON, and remove it
  before a release if it is not needed.

---

## 5. Roadmap

The phases are ordered: each one makes the next one's measurements meaningful.
IDs in brackets are backlog items.

### Phase 0: finish the baseline and make it cheap to iterate

**Goal:** a trustworthy before-picture and a harness that can sweep knobs.

| # | Work | Done when |
|---|---|---|
| 0.1 | Finish the frozen F-01 matrix: congress fresh/no-op/checksum and update-1pct, 3 runs per tool in both directions. **[F-01]** | Summary table includes congress and update-1pct medians |
| 0.2 | Add `XSYNC_TUNE` runtime overrides for the constants in §3 and the thread clamp, and record the active values in the result JSON. | A sweep can run without rebuilding; the JSON shows the effective values |
| 0.3 | Teach `pair.py` the existing `run.py` features: `--threads`, `delete`, `--cache cold`. Wire `snapshot.py` before and after each case. | A `-j` sweep and a `--delete` case run from one command |
| 0.4 | Add time-to-durable (`syncfs` on Linux, `F_FULLFSYNC` on macOS) as a second timing for write-heavy cases. | Both times are reported side by side |
| 0.5 | Redo the APFS diagnostic on a quiet machine with ≥20% free space. **[F-07]** | j1/2/4/8 table with load < 2 and the volume < 80% full |
| 0.6 | Cold-cache protocol for freya (ARC) and neo (`drop_caches`), with residency checked by `snapshot.py`. **[F-01]** | At least one cold congress push and pull, labelled `cold_evicted` with ARC evidence |

### Phase 1: efficiency recovery (CPU and RSS)

**Goal:** get back to rsync-class CPU and memory without giving up any T-series
safety guarantee. All the work in this phase is confirmed by A/Bs on congress push (freya receiver)
and the APFS no-op.

| # | Experiment / change | Hypothesis tested | Success criterion |
|---|---|---|---|
| 1.1 | **Per-directory dirfd.** Each `DirWork` holds an `O_NOFOLLOW` fd for its destination directory, and child operations are `*at()`-relative to it. `destination_path()` is used only to open a directory, never per file. | §3.1: anchored walks dominate system time | APFS no-op j4 ≤ rsync's time. Congress-push receiver system time cut ≥50%. All T-13/race tests still pass |
| 1.2 | Cache `NameRules` per `st_dev` on macOS too, and call `reject_name_collisions` once per directory | Part of §3.1 | `openat` drops out of the top of the APFS profile |
| 1.3 | Narrow `output_mu` to the state that actually needs it (the temp-name registry), and remove `output_io_mu` from the per-write path | §3.2: the global lock serializes creation | `-j` sweep shows wall time improving to at least 8 threads on ext4/ZFS, where today it is flat or worse |
| 1.4 | Free `RDir`/`SDir` once a directory and all its files are complete; bound local q1 by bytes and files, not tasks **[F-09]** | §3.3: RSS is O(tree) | Congress receiver RSS < 200 MiB. 5 M-file synthetic tree under a stated bound |
| 1.5 | In `pack()`, compress into a per-worker scratch buffer and copy out exactly the bytes needed (or count capacity in `qbytes`) | §3.3: frame capacity is retained | Mixed/large push `-z` peak RSS < 100 MiB with wall time unchanged |
| 1.6 | Linux scan: `getdents64` with `d_type`, `statx` with the minimal mask, and skip `fstatat` when `d_type` and the listing make it unnecessary **[F-06]** | Scan cost on ext4/ZFS | Congress no-op CPU ≤ 1.5× rsync |
| 1.7 | Gate RSS and CPU in CI next to wall time (e.g. a candidate may not exceed 1.15× the reference for either) **[F-02]** | Prevent backsliding | The gate fails on an injected leak or busy loop |

**Exit criterion for Phase 1:** across the F-01 matrix, xs CPU ≤ 1.5× rsync's
and peak RSS ≤ 4× rsync's, with wall time no worse than today's. Then
advance `ci-policy.json` to the new reference.

### Phase 2: restore and widen the local lead

| # | Experiment / change | v1 prior | Success criterion |
|---|---|---|---|
| 2.1 | **Linux reflink and copy offload.** Probe `FICLONE` once per (source fs, destination) by cloning a real source file, then use `FICLONE` per file. Otherwise use `copy_file_range` before falling back to `read`/`pwrite`. **[F-05]** | 2.98× on ext4 (probe only); 1.61× slower → 1.07× faster on XFS once the probe was correct | XFS/btrfs local fresh copy ≥ 2× rsync; ext4 not slower |
| 2.2 | **Whole-file by default for local copies** (as rsync's `-W`), with delta kept for remote and for `--no-whole-file`. A/B on an edited-large-file local update first. | rsync's own choice; v1 had no local delta | Local update of a 2 GiB edited file no slower than rsync. No regression in E-04 remote tests |
| 2.3 | **Thread count per filesystem.** Sweep -j {1,2,4,8,16,32} for fresh, no-op and update on APFS, ext4 (neo), ZFS (freya) and XFS. Choose a default from `fstatfs` type and cores. **[F-07]** | Optimum ranged 4–32 by filesystem; "core count is a poor predictor" | A documented table; the default within 5% of the per-fs optimum on each measured fs |
| 2.4 | APFS byte-copy floor with 1.1/1.3 in place: is ~100 µs/file the filesystem or contention? **[F-07]** | APFS 4,636 files/s at the optimum (`v1:legacy/BENCHMARKv2.md`) | Either reach v1's rate, or document the fs floor with a C microbenchmark |
| 2.5 | Bounded subtree clones (missing subtree under N entries / M bytes in one call) **[F-10]** | Directory clone wins only below ~4–7 MB of subtree | Crossover measured on xs; threshold set from it |
| 2.6 | Clone then fix mode for `-rt`/`-rlt` **[F-11]** | — | Faster than create+write on APFS for `-rt` |
| 2.7 | Parallel deletion by subtree **[F-12]** | — | Deleting a 96k-entry stale subtree ≥ 3× faster than `rm -rf` |

### Phase 3: remote throughput

Only after Phase 1, so that throughput gains are not paid for in CPU.

| # | Experiment / change | v1 prior | Success criterion |
|---|---|---|---|
| 3.1 | **Adaptive compression.** Decide per file (or per run) from a 64 KiB sample: keep zstd only if it saves ≥ 5%. Honour `--skip-compress` instead of rejecting it. Measure the link-speed crossover on neo↔freya and on a shaped (`tc`) link. **[F-04]** | 1.66× on congress-100k; 0% overhead on incompressible data; level 1/9 not worth it | `-z` on an incompressible corpus within 3% of `-a`; compressible corpus no worse than today |
| 3.2 | **Pipelined `-c`.** Hash files on the q1 pool (not in the walker), and send DIR as soon as names are listed with sums following. Receiver hashes candidates in parallel. **[F-14]** | Hashing is off the critical path when it overlaps (skipping it saved 0 ms) | Large `-c` pull ≥ 1.0×; mixed `-c` CPU ≤ 1.5× rsync's |
| 3.3 | **Asynchronous delta requests.** Do not block a sender worker in `wait_reply` per file; let several basis signatures be in flight at once. | Removing synchronous per-chunk acks took push from 62.9 MB/s to line rate | A tree of 100 edited 8 MiB files, updated remotely, at least matches rsync |
| 3.4 | **Cipher check.** Measure chacha20 vs `aes128-gcm@openssh.com` on neo (Cortex-A76 has ARMv8 crypto) and freya with `stream_probe.py`. If AES wins on both ends, document `-e "ssh -c aes128-gcm@openssh.com"` and consider preferring it when the user has not set `-c`. **[F-03]** | freya loopback: chacha 845 MB/s vs AES 2,374 MB/s; within 4% at 1 GbE | Decision recorded with the Pi's numbers |
| 3.5 | **Multiple streams for large files only.** Only if 3.4 shows that one ssh stream is the ceiling on a >1 GbE link. Stripe files ≥16 MiB across N connections; never stripe small-file trees. **[F-03]** | 16 MiB 1.41×, 64 MiB 1.94×, small trees 0.90× | A large file on 10 GbE ≥ 1.4× a single stream; no small-tree regression |
| 3.6 | Receiver apply-pool size: compare `min(cores, 8)` with today's 16 on freya after 1.1/1.3 land | v1 settled on `min(cores,8)` | Default set from the sweep |
| 3.7 | Tiny transfers: break down start-up (thread pool, handshake RTT) against rsync's **[F-13]** | No-op floor ≈ ssh KEX (~195 ms) + two scans | Single small file within 10 ms of rsync in both directions |

### Phase 4: scale and real-world shapes

| # | Work | Done when |
|---|---|---|
| 4.1 | 5 M-file synthetic tree plus 1 M-file real tree, with memory bound and wall time vs rsync **[F-09]** | Stated bound met; receiver memory flat in tree size |
| 4.2 | Pathological shapes: one directory of 500k entries; depth 64+; long names | No superlinear CPU; tested on APFS, ext4, ZFS |
| 4.3 | `-H`, `-X`, `-A` cost on congress (metadata-heavy paths were never benchmarked) | Each within 1.2× of the plain `-a` cost ratio vs rsync |
| 4.4 | Shaped links (`tc netem`: 20 ms / 100 Mb/s and 80 ms / 20 Mb/s) for no-op, update-1pct and delta | Table recorded; regressions on high-RTT links identified |
| 4.5 | Pi durability and thermal: run the same congress push with a 60 s soak, cooled and uncooled | Drift < 5% or documented |

### Phase 5: lock in

- Advance `ci-policy.json` after each phase's verified improvement.
- Add CI scenarios for each confirmed fix: a `-z` incompressible fixture (RSS),
  a deep-tree no-op (walk cost), `--delete` of a large subtree, and `-c` on
  large files.
- Keep the README's benchmark table generated from `report.py` output, and keep the
  historical table clearly labelled.

---

## 6. Explicitly deferred

These are parked on the strength of v1's evidence. Reopen only with a new
measurement that contradicts it:

- io_uring create/write paths.
- Dedicated receiver writer threads, fsync/`sync_file_range` tuning.
- Hash-cache or temp-name micro-optimisations.
- ssh multiplexing / `ControlMaster`, and logical streams multiplexed over one connection.
- A persistent destination index (revisit only with a memory budget well under v1's 1.09 GB at 1 M files).
- Unconditional compression level changes (level 1 or 9).

---

## 7. Decisions needed

1. **Local delta default** (2.2): keep rsync-style whole-file for local copies?
   The recommendation is yes, pending the A/B.
2. **Thread default** (2.3): a per-filesystem table, or a single conservative
   default (e.g. `min(cores, 8)`) plus documentation?
3. **Cipher preference** (3.4): should xs ever choose a cipher on the user's behalf,
   or only document the choice?
4. **Performance budget**: adopt the Phase 1 exit criteria (CPU ≤ 1.5×,
   RSS ≤ 4× rsync's) as standing CI gates?
