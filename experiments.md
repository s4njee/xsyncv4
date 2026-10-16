# Small- and mixed-file tuning experiments

Plan for a measurement framework that supports statistical inference about
`xs` performance on small-file and mixed-size trees, and for the experiment
campaign it will run. Nothing here has been built or measured yet.

Sources, abbreviated below:

- **v4** — this repository: `benchmarks/`, `backlog.md`, `README.md`, `src/`.
  Line numbers are from the working tree on 2026-10-11.
- **old** — `~/projects/xcalibur/xsync` (the Rust v1–v3 tool): `docs/`,
  `legacy/`, `benches/`. Its Raspberry Pi was called `orion`; it has no host
  named `neo`, no Wi-Fi sync benchmark and no SD-card measurement.
- **holochart** — `~/projects/holochart`, the charting library the paper's
  figures will be drawn with (section 9). This is the original three.js
  library, not the WebGPU port in `holochartv2`.

## 1. What the two projects already tell us

### 1.1 Hypotheses to reproduce on v4

Each row is a claim with prior evidence that v4 should either reproduce or
refute with a confidence interval. "Exp" points at section 6.

| ID | Claim to test | Prior evidence | Exp |
|---|---|---|---|
| H1 | Small-file time does not scale with files × RTT: v4 has no per-file round trip, so added RTT costs a constant, not a per-file term. | old: batching took 1,000 entries from 8.73 s to 0.34 s; congress-100k 211.5 s unbatched vs 17.3 s (`docs/STREAMS.md:32-41`). v4 packs files ≤ 512 KiB into 1 MiB blocks with no per-file ack. | E1, E7 |
| H2 | Per-directory exchanges dominate when directories ≈ files. | old: congress-1k (1,079 dirs, 1,076 files) 18.3 → 2.4 s as per-dir loops were pipelined (`docs/STREAMS.md:49-57`). v4 sends one `F_DIR` and one `F_NEED` per directory, even when empty. | E1, E4d |
| H3 | Flow-control windows have a knee, and it moves with RTT. | old: 256 → 2048 frames gave 1.26×, flat beyond; fitted at one suspect RTT and never re-swept (`docs/what-makes-file-sync-slow-v2.md:355-368`). v4 windows: 48 MiB send queue, 16 MiB receive, 65,536-entry listing window, all compile-time. | E4b |
| H4 | The sender is not the bottleneck on small files once reads overlap sends. | old: read-ahead loader gave 2.05× (`…slow-v2.md:279-298`). v4 has reader pool + writer thread; unverified which stage limits. | E2, E4e |
| H5 | Receiver apply concurrency saturates at about 2 workers. | old: Pi worker sweep 1/2/8/16 = 11.45/9.23/8.75/8.80 s. v4: `out_open`/`out_finish` in `src/fs.cpp` each hold the global `output_mu` for their whole body; README says a create costs "~100 µs however many threads ask"; ext4/XFS scaling "has not been measured here". | E3a, E5a |
| H6 | Per-file cost lands on the receiver, per-byte cost on the sender. | old: on small files swapping the sender changed time 1.07–1.20×, swapping the receiver 3.33×; on mixed, the Pi sent at 48.9 MB/s vs 92.8 (`…slow-v2.md:190-218`, n=2). | E1 |
| H7 | The Pi is close to a desktop as a small-file receiver. | old: 11,890 vs 12,961 files/s (`…slow-v2.md:173-185`); contradicted elsewhere by a 1.8 s storage-path penalty. | E1, E2c |
| H8 | With the Pi sending small files, xs is no faster than `rsync -a`. | old: 10.67 s vs 9.41 s, hashing blamed but never isolated. v4: congress fresh 0.98× push, 0.93× pull, n=3, "unexplained". | E1, E4h |
| H9 | Wall-clock comparisons with rsync mislead unless timed to durability. | old: rsync exits with ~2.4 GB dirty vs ~2.6 MB; a 1.73× wall win became parity when durable. v4 never fsyncs and has no durable timing. | E1 |
| H10 | Small-file throughput is receiver-bound with the link mostly idle. | old: plateau at 16–17k files/s with the link 33% used; 2–4 streams then gave up to 1.85×. v4 chose a single stream on LAN evidence only. | E2a |
| H11 | Fixed startup/teardown cost is measurable and reducible. | old: ControlMaster cut a no-op from 0.379 to 0.230 s (n=20). v4: tiny transfer ≈ 170 ms vs rsync 168–189 ms; `sh -c` peer lookup and a 25 ms `wait_peer` poll are on the path. | E3e, E4g |
| H12 | Cipher choice is worth ≤ 4% at 1 GbE even with a Pi. | old: four ciphers within 4% freya→orion; but another doc claims a 23% "SSH tax" (USB-dongle confound). | E3f |
| H13 | Compression helps compressible small files even at gigabit. | old: zstd-3 1.66× on congress-100k, level 9 halves throughput. v4: congress push 125.2 s plain vs 118.0 s `-z`, n=3. | E3b |
| H14 | Compression must be skipped, cheaply, on incompressible data. | old: `rsync -az` 1.8–2.9× slower on mixed data or with a Pi. v4 samples blocks ≥ 16 KiB and has a suffix skip list, but under `-z` each skip-suffix file gets its own DATA frame (`src/remote.cpp:1329-1340`). | E3b |
| H15 | The compression/link-speed crossover sits between LAN and Wi-Fi rates. | old: never mapped. v4 adaptive level switches at 64 and 8 MiB/s — values chosen without a slow-link measurement. | E3b, E4f |
| H16 | Temp-file + rename costs single-digit percent. | old: 7%, kept for atomicity. v4: `--no-atomic` exists; backlog T-11 asked for the cost on ext4 and APFS and no measurement is recorded. | E3c |
| H17 | Serial per-directory finalisation is visible on deep trees. | old: a serial pre-pass cost 16%. v4: `finalize_tree` in `src/fs.cpp` applies directory mode/mtime on one thread; `-O` skips most of it. | E3d, E5b |
| H18 | Worker optimum tracks storage, and a warm cache can invert it. | old: Pi cold, 4 cores: 16 workers beat 4 (218 s vs 260 s); a warm "plateau" vanished cold. v4: every recorded run is warm. | E3a |
| H19 | The receiver filesystem sets the create ceiling. | old: Pi tmpfs 6,277 files/s, mars ext4 7,778, mars tmpfs 70,605. v4: ext4 (neo), ZFS (freya), APFS (Mac) never compared with a tmpfs control. | E2c |
| H20 | Syscalls per file are near rsync's; the residue is scheduling. | old: 30.3 vs 30.1 syscalls/file but 100k–335k futex calls vs 64. | E2b |
| H21 | No-op re-sync is where xs should win most, in both directions. | old: 3.2×. v4: congress no-op 2.89× pulling but **0.74×** pushing, with 408.8 s CPU vs 18.8 s. | E1, E4d |
| H22 | `SMALL_MAX`/`BLOCK_TARGET` are near-optimal for mixed trees. | v4 only: 512 KiB and 1 MiB are untested constants; files just above 512 KiB flush the shared block and go one chunk per frame. | E4a |
| H23 | Per-file output (`-v`, `-i`, `--progress=json`) has a measurable cost on small files. | v4 only: one `F_OUTPUT` frame per file; this is the mode the app uses. | E3g |

### 1.2 Things the old project tried that did not help

Not worth re-testing unless an attribution run points back at them: `splice`,
`MSG_ZEROCOPY`, `sendfile`, io_uring (ceiling ~4% of wall), `fallocate`,
`sync_file_range`, flush cadence, dedicated writer threads, solid tar+zstd
containers (2× better ratio, 1.5× slower), compressing metadata frames (saves
bytes, not time), and a 10 GbE direct link.

### 1.3 Contradictions the old data never resolved

- Multi-stream on small files: "net loss on every corpus" vs 1.85× on a split
  corpus. The default rule changed three times and was never validated.
- "Hashing is free" vs hashing blamed for the Pi-sender deficit.
- "The Pi has no AES acceleration" vs "Cortex-A76 AES-GCM ties ChaCha20".
- Scan overlap: predicted a 10–19% gain, measured a 14% loss on a debug build.
- Corpus names drifted: congress-100k is 557 MB in one document and 850 MB in
  another. Every corpus here is pinned by digest (section 4.5).

### 1.4 Measurement failures that become harness gates

Each of these produced a published-then-retracted result in the old project
or a caveat in v4. Section 4.3 turns every one into a check.

| Failure | Gate |
|---|---|
| Both A/B arms ran the same stale binary | Binary hash recorded on both ends per sample; refuse dirty or debug builds |
| Failures recorded as timings (`>/dev/null`, no exit check) | Nonzero exit or failed verification is never a timing |
| Silent fallback to rsync | Always `--no-fallback`; blank `XSYNC_CONFIG` and `XSYNC_OPTS` |
| Run landed on Wi-Fi, a stale IP or a hidden mesh hop | Path proof before every block |
| Cold first run 1.9× slower; cold/warm swing of 7.6× | Cache state is a declared factor, never an accident |
| Pi bracket drifted 1.5× (thermal) | Temperature and throttle flags per sample; blocked design |
| Mac load average 15–265 during runs | Load gate; host state recorded per sample |
| `sync` flushed the previous cell's deletes into the timer | `syncfs` on the destination filesystem only, and a settle step |
| n = 2–3 with best-of; outliers of 30–148% in v4's n=3 runs | Sample size from a measured noise floor (section 5.5) |

## 2. Testbed

| Host | Hardware | Role |
|---|---|---|
| `neo.local` | Raspberry Pi 5 Model B, 4 cores, 4 GiB; Debian 13, kernel 6.18; ext4 on NVMe; `eth0` at 1 Gb/s | One end of every pair |
| `freya.local` | Ryzen 9 7950X, 32 threads, 62 GiB; CachyOS, kernel 7.1; benchmark root on ext4 on a QLC NVMe drive at `/mnt/nvme`, reformatted 2026-10-12; ZFS home; `enp10s0` at 1 Gb/s; runs other services | Phase A peer |
| `mars.local` | Ryzen 9 7900X, 24 threads, 30 GiB; CachyOS, kernel 7.2; ext4 on NVMe with 700 GB free; `enp9s0` wired at 1 Gb/s into the mesh, about 2.3 ms from neo and freya and 1 ms from the Mac; steady drive (1.6-fold in the write test). Inventoried 2026-10-12. No helper yet, and SSH host keys between mars and neo or freya are not yet accepted | Phase B peer |
| this Mac | M1 Max, 10 cores, 64 GiB, APFS (98–99% full in past runs), USB gigabit adapter | Phase C peer; controller for A and B |

| Phase | Pair | Link | Purpose |
|---|---|---|---|
| A | neo ↔ freya | wired LAN, 1 Gb/s | Build and calibrate the framework; main tuning |
| B | neo ↔ mars | mesh Wi-Fi | Re-test link-sensitive factors; check the LAN tuning holds |
| C | neo ↔ Mac | wired LAN | macOS/APFS endpoint; final confirmation |

Known constraints:

- neo and freya were inventoried on 2026-10-11 (`benchmarks/results/lab/
  preflight/`): both ends of the LAN link are wired at 1 Gb/s with a 0.36 ms
  round trip. mars was off the network and its row is still from the old
  docs.
- rsync differs by host: 3.4.1 on neo and 3.5.0 on freya. Every record names
  both versions; E1 should say whether the baseline is each host's own
  rsync or one pinned build.
- The old topology notes put freya behind the mesh hop and mars on the
  switch, the reverse of the layout above. The path proof must confirm the
  current wiring rather than trust either description.
- Every v4 run recorded so far has neo as the SSH client, because freya
  could not authenticate to neo, so direction is confounded with client
  role in that data. neo and freya now authenticate both ways; mars gets
  the same before phase B. E1b measures whether client role matters.
- freya's benchmark root is `/mnt/nvme/xsbench`, on an ext4 filesystem on a
  1.9 TB QLC NVMe drive mounted at `/mnt/nvme` from `fstab`. The helper
  mounts it if it is not mounted, and preflight checks the mount and its
  type. The drive's write speed collapses when it is nearly full and
  untrimmed (see the progress notes), so it is kept mostly empty. The ZFS home
  stays in use as a second receiver filesystem for H19, warm-cache only,
  because `drop_caches` does not prove a cold ZFS ARC.
- Root operations go through one fixed helper per Linux host (section 4.8).
- Phase C starts only after A and B finish, because the Mac's wired link is
  not available earlier and the Mac is the controller until then.

## 3. Principles

1. **Paired, blocked, randomized.** Arms are compared inside short blocks so
   that thermal, load and link drift cancel. Order inside a block is random
   from a recorded seed.
2. **Ratios, not seconds.** The estimand is a time ratio between two arms in
   the same cell. Absolute times are recorded but never gated or pooled.
3. **Declared before measured.** Each experiment is a committed spec naming
   its hypothesis, arms, cells, primary metric, effect threshold and block
   budget. The analysis reads only what the spec declares.
4. **One binary per comparison where possible.** Arms differ by flags or
   environment on the same executable. Arms that need different builds
   record both hashes.
5. **Every sample is verified and self-describing.** A record carries enough
   to be re-analysed without the harness that produced it.
6. **Screening finds candidates; confirmation estimates them.** The effect
   size of a winner picked from many arms is biased upward, so it is
   re-measured on fresh blocks against the control alone.
7. **Reuse what exists.** `benchmarks/measure.py`, the ownership markers and
   lock in `run.py`, `snapshot.py`, `stream_probe.py`,
   `tests/compression_proxy.py` and `tools/release.py` stay in use.

## 4. Framework design

### 4.1 Vocabulary

- **Sample**: one timed transfer.
- **Arm**: a tool configuration (binary, flags, environment on each end).
- **Cell**: corpus × scenario × direction × client role × link × cache
  state.
- **Block**: every arm of an experiment run once in one cell, in random
  order, back to back.
- **Experiment**: a spec — arms, cells, one control arm, a block budget.

### 4.2 Components

New code lives in `benchmarks/lab/`; specs in `benchmarks/experiments/`;
results in `benchmarks/results/lab/<experiment>/<run-id>/`.

| File | Runs on | Job |
|---|---|---|
| `hosts.toml` | controller | Host inventory, owned roots, declared interface and peer route per link |
| `experiments/E*.toml` | controller | Pre-registered specs |
| `corpus.py` | each endpoint | Seeded generator; writes a manifest and digest |
| `stage.py` | controller | Builds a commit's static release from `git archive`, stages `xs-<rev12>` and the lab scripts, verifies SHA-256 remotely |
| `preflight.py` | controller + agent | Inventory, path proof, link probe, tool versions |
| `plan.py` | controller | Spec + seed → block plan (JSON) |
| `agent.py` | driver endpoint | Executes a plan with no controller in the timed path; appends JSONL after every sample |
| `probe.py` | both endpoints | Host-state snapshot before and after each sample |
| `analyze.py` | controller | Estimates, intervals, tests, verdicts |
| `report.py` | controller | Markdown report per experiment |
| `export.py` | controller | Tidy tables for figures (section 9) |
| `selftest.py` | controller | Statistics tested on synthetic data with known effects |

The agent and probes use only the Python standard library, as the existing
harness does, so they run unchanged on neo. The analysis is also standard
library only; the estimators in section 5 need nothing more.

The controller ships a plan to one endpoint, the driver (neo), and collects
results afterwards. The agent runs there detached, so a sleeping laptop or a
Wi-Fi drop on the controller cannot perturb or abort a block. The driver
reaches the other endpoint over SSH and starts each timed transfer on
whichever host the cell names as the SSH client, under `measure.py` on that
host, so the agent itself is outside the timed path too.

### 4.3 Sample lifecycle

Before a run:

1. Refuse any `xs` that is not the recorded build of the commit under test.
   Builds are made from `git archive` of a commit, never from the working
   tree, so a binary cannot hold uncommitted changes; each host's copy must
   match the recorded SHA-256 and report that revision. Record the revision
   and binary hash on both ends, and the rsync and OpenSSH versions.
2. Check each corpus against its pinned manifest digest and file count.
3. Path proof: resolve the peer name fresh, record `ip route get <peer>`
   (interface, source address), link speed and MTU, and the peer's
   `$SSH_CONNECTION`. Fail if the interface is not the one `hosts.toml`
   declares for the link.

The run also sets the `performance` governor through the helper, checks
that freya's root is ext4 at `/mnt/nvme`, and refuses to start if the helper
reports a leftover `netem` qdisc. At exit, including on failure, it clears
`netem` and restores the governor.

Before each block:

4. Link probe: 20 pings for RTT and jitter, plus a short `stream_probe.py`
   run for raw SSH throughput. Stored as block covariates.
5. One untimed warm-up transfer at the start of a session only.

For each sample, in the block's random order:

6. Prepare the destination for the scenario (empty, identical, or 1% stale),
   untimed.
7. Apply the cache state: pre-read the source for `warm`, or run the
   helper's `drop-caches` on both ends for `cold`.
8. Settle: `syncfs` the destination filesystem, then wait until `Dirty` +
   `Writeback` and the 1-minute load are under the host's thresholds and,
   on the Pi, the SoC is under its start temperature. Record the wait.
9. Probe both hosts.
10. Run the transfer under `measure.py` on the client, with the peer wrapped
    by `measure.py` through `--rsync-path`. Always `--no-fallback`, with
    `XSYNC_CONFIG` and `XSYNC_OPTS` blanked.
11. Time `syncfs` on the destination separately; `wall + syncfs` is the
    time-to-durable.
12. Probe both hosts again.
13. Verify, untimed, by `corpus.py verify` of the destination against the
    corpus manifest, which depends on neither tool. A fresh copy is re-read
    in full; screening specs may do that on the first and last block only
    and compare names, sizes, modes and times otherwise. The record says
    which.
14. Append the record.

A sample is **invalid** only for reasons recorded independently of its
timing: nonzero exit, failed verification, path-proof change, a throttle
flag raised during the sample, or a probe outside its gate. An invalid
sample voids its whole block, which is re-run; pairing is never broken and
no sample is dropped for being slow.

### 4.4 What a record contains

One JSON line per sample, in one schema for every experiment. Records are
never aggregated in place; the tables the paper's figures use are derived
from them (section 9).

- **Identity**: experiment, spec hash, run id, seed, block, position in
  block, previous arm, arm, and each cell field.
- **Timing**: wall, time-to-durable, user and system CPU on both ends.
- **Resources**: peak RSS on both ends, context switches, block I/O counts
  from rusage.
- **Wire**: parsed `--stats` bytes sent and received, NIC byte-counter
  deltas, TCP retransmit delta.
- **Engine metrics** (once section 4.7 lands): per-stage nanoseconds and
  phase timers from both ends.
- **Host state before and after**: load, `MemAvailable`, `Dirty`,
  `Writeback`, CPU frequency and governor; on neo SoC temperature and
  `vcgencmd get_throttled`; on a wireless interface signal, bitrate and
  retry counters.
- **Provenance**: binary hashes, tool versions, full argv and environment
  for both ends, UTC and monotonic timestamps, verification mode and result,
  validity and reason.

### 4.5 Corpora

The existing synthetic fixtures are a single file size and trivially
compressible, and only congress is real. The generator takes a seed, a file
count, a size distribution, a directory shape, a content mix and a name
style, and writes a manifest whose digest pins the corpus.

| Corpus | Shape | Tests |
|---|---|---|
| `tiny-one` | One 19-byte file | Fixed startup and teardown cost |
| `small-flat` | 100,000 files, 304 MiB, log-normal sizes (median 1 KiB, 90% under 7.3 KiB), 100 directories, text-like (zstd-3 ratio 4.2) | Pure per-file cost |
| `small-deep` | The same files, one per directory, depth 6: 116,667 directories | Per-directory cost (H2, H17) |
| `small-real` | Congresses 116–118 of the congress corpus: 118,594 files, 59,336 directories, 1.03 GiB; median file 6.1 KiB, 90% under 24 KiB; real JSON and XML | Realistic compressible small files, with a directory for every two files |
| `small-opaque` | `small-flat` shape, random bytes, half with skip-list suffixes (`.jpg`, `.gz`) | Compression skip paths (H14) |
| `mixed-bimodal` | 20,000 files, 1.33 GiB: 83% of files under 8 KiB, 68% of bytes in 74 files over 8 MiB; two thirds text-like, the rest random | The old `cb7` shape, scaled to fit a block |
| `mixed-threshold` | 1,500 files, 1.43 GiB, sizes log-uniform from 1 KiB to 8 MiB (469 files over 512 KiB); half text-like | Behaviour around `SMALL_MAX` and `BLOCK_TARGET` (H22) |
| `real-holochart` | Frozen copy of `~/projects/holochart`, a JavaScript monorepo: 249,602 files, 33,012 directories, 10,607 symlinks, 7.3 GiB; median file 2.2 KiB, 90% under 33 KiB, largest 76 MB; over half the files are `node_modules` | A real small-file-dominated working tree, with pnpm's symlinks |
| `real-laikav2` | Frozen copy of `~/projects/laikav2`, a Rust project: 54,691 files, 3,106 directories, 42.2 GiB (33 GiB on disk: 19,345 names are hard links); median file 88 KiB, 10% over 1.3 MiB, largest 214 MB; almost all of it is the `target` build directory | A real mixed tree whose sizes straddle `SMALL_MAX` and `BLOCK_TARGET`, with many hard links |

The generated corpora are built by `benchmarks/lab/corpus.py`, which draws
everything from SHAKE-256 with integer arithmetic so that a name and tier
give the same bytes, names, modes and times on any host. Their digests are
pinned in `benchmarks/lab/corpora.json`. E8's series are generated the same
way as `scale-size-BYTES` and `scale-count-FILES`; the count series is a
prefix of `small-flat`, so its points nest.

Sizes target 3–20 s per sample on the LAN: long enough that the ~170 ms
fixed cost and the 25 ms teardown quantum are not the result, short enough
for a dozen blocks per cell. Each corpus also has a 10× smaller smoke tier
for harness tests and a 500× smaller one for unit tests.

The three real corpora are frozen copies. `small-real` was taken from the
congress snapshot already on freya. `real-holochart` and `real-laikav2` are
live working trees, so each was copied once, whole, including `.git`,
`node_modules` and build output, from the Mac to freya on 2026-10-11. The
copy on freya is the definition from then on: neo's copy was made from it
and every later host's will be, and all are pinned by manifest digest in
`corpora.json` like the generated ones. Transfers of `real-laikav2` need
`-H` to be comparable, because a fifth of its bytes are hard links.

The two `real-` trees are far larger than the 3–20 s target —
`real-laikav2` is about five minutes per sample at wire rate on the LAN —
so they run in E1 and E6 with a small block count, and tuning experiments
use a pinned subtree of each. Their per-file listings stay on the hosts;
published tables carry sizes and depths but no file names.

### 4.6 Cache states

- `warm`: the source is pre-read before each sample. The default.
- `cold`: the helper's `drop-caches` runs on both ends before each sample.
  Available on ext4 (neo, freya's `/mnt/nvme`, and mars once inventoried). ZFS
  cells stay warm-only. `purge` on the Mac is deferred with the rest of
  phase C access (section 10).
- `/dev/shm` is tmpfs and needs no privilege, so a tmpfs destination control
  is available on every Linux host for corpora that fit in half of RAM.

### 4.7 Engine changes the experiments need

None of the engine's tuning constants could be changed at run time, and `-j`
always applies to both ends. Two additions, built in M7, both behind a build
option (`-DXSYNC_TUNABLES=ON`) that release binaries do not enable. In a
release build the constants are one `constexpr` table (`src/tune.h`) and the
two variables below are never read.

1. **`XSYNC_TUNE`**, a `key=value` list read at start-up. An unknown key or
   a value out of range ends the run with code 1 before anything is written.

   | Key | Default | What it sets |
   |---|---|---|
   | `block_target` | 1 MiB | raw bytes per DATA frame |
   | `small_max` | 512 KiB | files up to this size share blocks; same on both ends |
   | `send_queue` | 48 MiB | frames waiting for the transport writer |
   | `recv_queue` | 16 MiB | DATA waiting for receiver workers |
   | `listing_window` | 65,536 entries | source entries retained before scanning further |
   | `read_batch_files` / `_bytes` | 64 / 8 MiB | size of one read task |
   | `q1_soft_send` / `_recv` | 64 / 16 | backlog that takes workers off scanning or generating |
   | `write_chunk` | 64 KiB | largest single write to the transport |
   | `coalesce_under` / `_to` | 32 KiB / 256 KiB | small frames gathered into one write |
   | `pipe_size` | unset | `F_SETPIPE_SZ` on the transport pipes |
   | `jobs` | auto | workers on this end, whatever `-j` says |
   | `scan_workers` | half of `jobs` | workers that prefer scanning |
   | `zstd_fast_at` / `_slow_at` | 64 / 8 MiB/s | rates at which `-z` picks level 1 or 6 |
   | `wait_peer_poll_ms` | 25 | how often the client polls for the peer's exit |

   The environment does not cross SSH, so `measure.py` has an `--env K=V`
   option and the agent sets each end through its wrapper. A spec arm gives
   `tune = "..."` for both ends or `tune = { sender = "...", receiver =
   "..." }`; `jobs` on one end is how the two ends get different worker
   counts. Not built: a switch for the block hash, which was diagnostic
   only, and a knob for parallel ranges within one file, which the default
   never uses (they need an explicit `-j`).

2. **`XSYNC_METRICS=path`**, one JSON line appended at exit by each end:
   the `read_ns`/`network_ns`/`write_ns` stage timers, phase marks
   (`connected`, `scanned`, `transferred`, `finalized`), CPU time, context
   switches, wire bytes, the size the kernel granted each transport pipe,
   and the constants in force. Before this the stage timers ran only under
   `-vv`, which also turns on per-file output frames and so perturbs
   exactly the workloads being measured. An arm asks for it with
   `metrics = true`, and the sample record gains an `engine` object with
   one entry per end.

A tunables build is `REV-tune` wherever the harness takes a revision; it is
a separate build with its own record, staged as `xs-<rev12>-tune`, and
`--version` says `tunables`. It is used for an experiment only after E0c
shows it is equivalent to the release build at default values.

### 4.8 Privileged helper

One root-owned script, `/usr/local/sbin/xsbench-helper`, on neo, freya and
mars, allowed by a single `sudoers` entry for the benchmark user. The script
is kept in `benchmarks/lab/` for review and installed by hand by the
operator; the harness never edits `sudoers` and never installs anything as
root. It accepts only these verbs:

| Verb | Does | Used for |
|---|---|---|
| `drop-caches` | `sync`, then writes 3 to `/proc/sys/vm/drop_caches` | The `cold` cache state |
| `governor performance`, `governor restore` | Sets and restores the cpufreq governor | Run start and exit |
| `netem set <delay-ms> <loss-%> <lifetime-s>`, `netem clear` | Adds or removes a `netem` qdisc | E7b |
| `mount-scratch` | Mounts the configured scratch mount point if it is not mounted | freya's benchmark root |
| `trim-scratch` | Runs `fstrim` on the scratch filesystem | The start of every run |
| `status` | Prints governor, qdisc and mount state | Preflight and exit checks |

The network interface, the mount point and the filesystem UUID are fixed in
a root-owned file, `/etc/xsbench-helper.conf`; a caller cannot name another.
`mount-scratch` mounts what `fstab` defines for the mount point, or failing
that the configured UUID, and never chooses or formats a device. `netem set`
refuses to replace a qdisc that someone configured, and arms a timer that
clears its own after the stated lifetime, so a crashed run cannot leave a
host's network degraded. `governor` also saves and restores the
energy-performance preference that `amd-pstate-epp` ties to the governor.
Installation steps are in `benchmarks/lab/README.md`.

## 5. Statistical method

### 5.1 Estimand

For an arm A and control C in one cell: the ratio of typical time,
`A / C`. Below 1 means A is faster. The primary metric is wall time for
comparisons between `xs` configurations and time-to-durable for comparisons
with rsync. A spec may name a different primary metric (CPU seconds for the
no-op anomaly, wire bytes for compression) but only one.

### 5.2 Design

Randomized complete blocks. Within block *b* the paired log-ratio is
`d_b = ln(t_A,b) − ln(t_C,b)`. Blocks are the unit of replication; the *n*
in every formula is the number of valid blocks, not samples.

- At most six arms per block including the control, so a block stays inside
  one thermal and link regime. Larger sweeps are split into experiments that
  share the control.
- Cells are interleaved across a session rather than run to completion one
  after another, so time-of-day does not alias with a cell.
- Position in block and the previous arm are recorded so that order and
  carry-over effects can be tested rather than assumed away.

### 5.3 Estimate, interval and test

- **Estimate**: `exp(mean(d_b))`, the geometric mean ratio.
- **Interval**: the paired *t* interval on `d_b`, exponentiated.
- **Robust check**: the Hodges–Lehmann estimate with its distribution-free
  interval, and an exact sign-flip permutation p-value. With fewer than six
  blocks an exact two-sided test cannot reach p < 0.05 at all, so no
  experiment runs fewer than eight.
- If the *t* and robust intervals lead to different verdicts, the verdict is
  *inconclusive* and blocks are added.

### 5.4 Verdicts

Each spec declares δ, the smallest effect worth acting on (suggested: 3% on
the LAN, 5–10% on Wi-Fi, set after E0a). With the interval `[lo, hi]`:

| Interval | Verdict |
|---|---|
| `hi < 1/(1+δ)` | **faster** |
| `lo > 1+δ` | **slower** |
| inside `[1/(1+δ), 1+δ]` | **equivalent** |
| otherwise | **inconclusive** — add blocks or stop at the budget |

"Statistically different from 1" is reported but is not a verdict. A 1%
effect that is real is still not a reason to change a default.

### 5.5 Sample size

From the noise floor σ_d (the standard deviation of `d_b` in an A/A run):

`n ≈ ((1.96 + 0.84) · σ_d / ln(1+δ))² + 2`, with a floor of 8.

| σ_d | δ = 2% | 3% | 5% | 10% | 20% |
|---|---:|---:|---:|---:|---:|
| 0.02 | 10 | 8 | 8 | 8 | 8 |
| 0.05 | 52 | 25 | 11 | 8 | 8 |
| 0.10 | 202 | 92 | 35 | 11 | 8 |
| 0.20 | 802 | 361 | 134 | 37 | 12 |

v4's existing n=3 runs show a typical spread of 1–10% with outliers of
30–148%, so σ_d on the LAN is probably 0.03–0.08 and unknown on Wi-Fi. The
table is why the Wi-Fi phase uses a larger δ and tests fewer factors.

What that many blocks buys, confirmed by simulation in `selftest.py` at
σ_d = 0.05 and δ = 3% (25 blocks):

- If the true ratio is 1 + δ, the interval excludes 1 about 80% of the
  time. That is the power the formula is built for.
- The verdict *faster* or *slower* needs the interval to clear δ, which is
  stricter. A true ratio of exactly 1 + δ earns it about 2% of the time;
  a true ratio of (1 + δ)², about 6%, earns it about 77% of the time. So δ
  is the smallest effect that can be *noticed*, and twice δ the smallest
  that is reliably *called*.
- With no true effect, the verdict *equivalent* needs about a third more
  blocks for 80% power: `((1.96 + 1.28) · σ_d / ln(1+δ))² + 2`, 33 here.
- An exact two-sided p-value cannot be smaller than 2^(1−n). Under Holm's
  correction across m comparisons, nothing can be significant unless
  2^(1−n) · m is below 0.05: eight blocks cannot survive ten comparisons.

### 5.6 Adding blocks without fooling ourselves

Each spec declares an initial block count, a maximum and at most three
analysis looks. Every look uses a `1 − 0.05/looks` interval. Data are not
inspected between looks.

### 5.7 Many comparisons

- **Screening** experiments are exploratory. They report unadjusted
  intervals and choose candidates; they make no claims.
- **Confirmatory** experiments apply Holm's correction across all arm × cell
  comparisons in the spec.
- A screened winner is always re-estimated in a confirmatory run on fresh
  blocks against the control alone.

### 5.8 Adopting a change

A tuning change is adopted only if, in confirmatory runs:

1. It is **faster** in at least one target cell.
2. It is not **slower** in any cell of the confirmation matrix, including
   the other direction and the `noop` scenario.
3. Guardrails hold: verification passes everywhere, and peak RSS on either
   end does not rise more than 10%.

### 5.9 Comparing links and hosts

Whether a LAN-tuned setting holds on Wi-Fi is an arm × link interaction:
the ratio of the two per-link ratios, with the interval from the two
independent sets of block log-ratios. The same construction compares
receivers (H7, H19). Blocks are never pooled across links.

### 5.10 Calibrating the framework itself

Before any result is believed (experiment E0):

- **A/A**: one binary under two arm labels must come out *equivalent*, in
  every cell. This also measures σ_d.
- **Known effect**: an arm that sleeps for 2δ of the control's median before
  exec must come out *slower* at the planned block count, and one that
  sleeps for δ must give an interval that excludes 1 without earning a
  verdict (section 5.5).
- **Synthetic**: `selftest.py` simulates experiments with known ratios and
  a large shared drift per block. It checks interval coverage (95.2%,
  94.8% and 95.4% at 8, 12 and 24 blocks), coverage under heavy-tailed and
  outlier noise, the rate of wrong verdicts, the power figures above, and
  Holm's family-wise error.

## 6. Experiment catalogue

**E0 — calibration.** (a) A/A noise floor per cell, 20 blocks. (b) Injected
slowdowns of δ and 2δ (section 5.10). (c) Tunables build vs release build at defaults, expecting
*equivalent*. (d) Position and carry-over effects from the E0a data. (e) The
one-second host sampler on vs off, expecting *equivalent*.

**E1 — baseline matrix.** `xs` release defaults vs `rsync -a`, every corpus
× {fresh, noop, update-1pct} × {push, pull}, plus the `-z` pair on
`small-real`, `small-opaque` and `mixed-bimodal`. Confirmatory. Reports wall
and durable ratios, CPU and RSS. Covers H1, H2, H6–H9, H21 and replaces the
n=3 table in `benchmarks/README.md`.

**E1b — client role.** A subset of E1 (`small-real` and `mixed-bimodal`,
fresh and noop, both directions) with each end as the SSH client. Arms:
sender-initiated push and receiver-initiated pull of the same transfer. If
client role is *equivalent*, later experiments use the sender as client; if
not, it stays a factor in every cell.

**E2 — attribution.** Diagnostic runs that explain E1, not timing claims.
(a) Stage nanoseconds and link utilisation (wire rate ÷ `stream_probe`
capacity) per cell — decides whether H10 and multi-stream are worth
revisiting. (b) Syscalls and futex calls per file on both ends under
`strace -c -f`, against rsync. (c) tmpfs destination vs the real filesystem
on each receiver; this one is timed and inferential, and gives the storage
share of receive time. On freya it compares tmpfs, ext4 at `/mnt/nvme` and ZFS
on one host, which is the cleanest test of H19. (d) Frame counts by type via
`tests/compression_proxy.py`.

**E3 — flag-only factors** (no engine change; screening, then confirm).

| ID | Arms | Cells | Hypotheses |
|---|---|---|---|
| E3a | `-j` 1, 2, 4, 8, 16 | small and mixed, fresh and noop, both directions, warm and cold | H5, H18 |
| E3b | no `-z`; `-z` adaptive; levels 1, 3, 6; `--skip-compress=''` | `small-real`, `small-opaque`, `mixed-bimodal`, both directions | H13–H15 |
| E3c | default vs `--no-atomic` | small corpora, fresh | H16 |
| E3d | `-rt`; `-a`; `-a -O`; `-aH`; `-aX` | `small-flat`, `small-deep`, fresh | H17 |
| E3e | default; absolute `--rsync-path`; ControlMaster; both | `tiny-one`, `small-flat` noop | H11 |
| E3f | chacha20-poly1305; aes128-gcm; aes256-gcm | `mixed-bimodal`, both directions | H12 |
| E3g | `-q --no-progress`; `--progress=json`; `-v` | small corpora, fresh | H23 |
| E3h | default vs `-W`; with and without `--partial` | mixed corpora, update-1pct | — |
| E3i | static musl release vs glibc native build | `small-flat`, `mixed-bimodal` | — |

**E4 — tunables** (needs section 4.7).

| ID | Factor | Design | Hypotheses |
|---|---|---|---|
| E4a | `block_target` {256 KiB, 1 MiB, 4 MiB} × `small_max` {64 KiB, 512 KiB, 1 MiB} | 3×3 factorial in two experiments sharing the control; mixed corpora | H22 |
| E4b | `recv_queue`, `send_queue`, `read_batch_*`, `q1_soft_*` | One factor at a time, 3 levels each; repeated under added delay in E7b | H3 |
| E4c | `write_chunk` {64 KiB, 256 KiB, 1 MiB} × `pipe_size` {unset, 1 MiB} | 3×2 factorial; mixed corpora | — |
| E4d | `listing_window`, `scan_workers` | One factor at a time; `small-deep`, noop | H2, H21 |
| E4e | Sender `jobs` × receiver `jobs` | 3×3; small corpora, both directions | H4–H6 |
| E4f | `zstd_fast_at`, `zstd_slow_at` | Mainly phase B | H15 |
| E4g | `wait_peer_poll_ms` 25 vs 1 | `tiny-one`, 50 blocks | H11 |
| E4h | `block_hash` on vs off | Small corpora, Pi sending | H8 |

Factors that plausibly interact get a small factorial; independent
mechanisms are swept one at a time around the default.

**E5 — code candidates.** One build per arm, chosen by what E2–E4 show.
Current candidates: (a) narrow the `output_mu` critical sections in
`out_open`/`out_finish`; (b) parallel `finalize_tree`; (c) `openat`-relative
reads on the sender; (d) coalescing per-directory `F_NEED` frames.

**E6 — confirmation.** The chosen configuration vs release defaults, and vs
rsync, across the full E1 matrix on fresh blocks, with the adoption rule of
section 5.8.

**E7 — cross-link.** The E6 ratios on LAN, Wi-Fi and the Mac leg compared as
interactions (section 5.9). Also answers H1: if small-file time carries a
per-file RTT term, the Wi-Fi/LAN ratio grows with file count.

**E7b — controlled delay and loss.** On the wired link, `netem` on neo's
interface adds 0, 2, 5 and 20 ms to the round trip, and separately 0.5%
loss at 5 ms. Each level is an arm, applied by the helper before its
sample. Cells: `tiny-one`, `small-flat` and `small-deep`, fresh and noop.
This gives H1 and H2 a dose–response that Wi-Fi cannot, because Wi-Fi
differs from the LAN in rate, jitter and loss at once. E4b's window sweep is
repeated at 5 and 20 ms for H3.

**E8 — scaling curves.** Descriptive, for the paper's central figure. Arms:
`rsync -a`, `xs` release defaults and the adopted configuration. Two
series, each fresh and noop, both directions, on every link:

- **File size**: 256 MiB of text-like data in equal-sized files of 1 KiB,
  4 KiB, 16 KiB, 64 KiB, 256 KiB, 1 MiB, 4 MiB and 16 MiB (262,144 files
  down to 16). The sweep crosses `small_max` and `block_target`.
- **File count**: the `small-flat` size distribution at 1,000, 3,000,
  10,000, 30,000, 100,000, 300,000 and 1,000,000 files; the top point is
  dropped on Wi-Fi.

Each point is its own cell with the usual blocks, so every point on a curve
carries an interval.

## 7. Campaign

Redesigned on 2026-10-13: the wired pair is measured continuously, not in a
nightly window, and the other links are measured on demand.

### 7.1 neo ↔ freya: continuous

A runner on neo works a backlog around the clock (section 4.2, and
`benchmarks/lab/README.md`). Three kinds of run share the hosts, one at a
time:

| Lane | What | When |
|---|---|---|
| Backlog | Experiments from the catalogue, in the order they are queued; a spec can be put at the front | Whenever the hosts are free |
| Sentinel | `S0-sentinel`: xs twice and rsync on a small and a mixed corpus, fresh and no-op, both directions, 3 blocks, about 20 minutes | Every 6 hours, whatever is waiting |
| By hand | A test someone runs directly | After `runner pause`; the queue resumes afterwards |

What continuous running changes, and how the design answers it:

- **The hosts are no longer quiet by arrangement.** Day and night differ in
  what else the machines and the network are doing. Blocks already carry
  that: every arm of a block runs within minutes of the others, the
  quiet-host gate still voids a sample taken on a busy host, and the
  sentinel measures the noise floor at each hour. The sentinel series is
  the evidence that a ratio measured at 3 pm means what one measured at
  3 am does. If it shows a period that is reliably noisier, that period is
  given to screening and confirmatory runs wait.
- **Drives wear.** A byte-bound sample writes its corpus to the receiver,
  and at full duty the pair could write several terabytes a day to freya's
  QLC scratch drive (rated for 800 TB) and to neo's system drive. Each plan
  states the bytes it will write per host; the runner keeps a 24-hour total
  and passes over a run that would exceed a host's allowance, 750 GiB a day
  to start with. No-op and small-file experiments are nearly free and fill
  the time that byte-bound ones may not.
- **There is no morning.** Nothing waits for a person: a failed run does
  not stop the queue, three in a row halt it rather than burn the backlog,
  scripts and builds can be staged while it runs, and the runner can be
  replaced under a run in progress. Results are collected whenever someone
  asks.
- **More data invites more looks.** Continuous running makes it easy to
  add blocks until a verdict appears. The rule of section 5.6 stands: a
  confirmatory spec declares its blocks, is queued once, and is analysed
  once; more blocks are a new run with a declared look. The sentinel is
  never tested; it is read as a control chart.
- **An empty backlog is the planner's failure, not the hosts' rest.** The
  backlog is kept a few days deep. Screens that need no new code (E3, E4
  factors, repeat cells with high noise) are the filler between
  experiments that wait on analysis or on a build.

Order of work: what remains of phase A as it was, E1 on the current
baseline first, then the E4 tunables, T1 candidates, E7b once the agent can
set `netem` per arm, and E8 once its corpora are generated (generation
runs through the queue as a maintenance job, since it loads the hosts).
freya's cells use the ext4 scratch drive at `/mnt/nvme`.

### 7.2 orion ↔ mars, a wireless mesh hop

The Wi-Fi pair, from 2026-10-13: orion (Raspberry Pi 4, NVMe behind a USB
bridge) and mars (Ryzen 9 7900X, NVMe), each wired to a mesh node, with the
wireless backhaul between the nodes as the only radio on the path. It
replaces neo ↔ mars as the Wi-Fi leg. The pair is a Pi and a desktop like
the wired pair (Pi 5 and 7950X), so the question is put as a comparison:
the same experiments on both, and where the ratios agree the hop needs no
special tuning; where they part is where Wi-Fi tuning starts. mars drives,
with its own runner and backlog, and results go to
`benchmarks/results/wifi/`. Measured before the first run: 1.7 to 4 ms
round trips and 440 to 490 Mbit/s each way through an SSH stream, about half
the wired pair's rate. orion's own Wi-Fi radio is off; with it on, its name
resolved to two addresses and replies left by Ethernet whichever one a
packet arrived on. orion's drive cannot be trimmed through its USB bridge,
so its write speed is watched instead, and its write allowance is 300 GiB a
day. Noise is higher and the link is the likely bottleneck, so:

- Re-run E0 first; nothing from the wired noise floor carries over.
- Shorter blocks (smoke-tier corpora where needed), more of them, and δ set
  from the measured σ_d.
- Wireless statistics, retransmits and the per-block link probe are
  recorded; a block whose probe falls outside a declared band is void.
- Run E1, then only the link-sensitive experiments: E3a (brief), E3b, E3e,
  E4b, E4f. Then E6 for the wired configuration, E7 and E8.

W0a (the noise floor, 12 blocks, four corpora, fresh and no-op, both
directions) started on 2026-10-13; W1 is E1's matrix on this pair.
`small-real` is copied from freya when the wired pair is idle.

### 7.3 Mac ↔ mars: on demand, supplementary

Started by hand with `plan.py start` when a question needs APFS or a
workstation in the loop, never queued, and kept in
`benchmarks/results/supplementary/`. Small-file corpora only. A run there
waits while a path experiment marks mars as in use.

### 7.4 neo ↔ Mac, wired: deferred

E0, E1, E3a (the APFS worker cap), E6, E7, E8, when the Mac is on the wire.
Mac-specific handling: destination under a `.noindex` directory so Spotlight
stays out, load gate, free-space check, and `purge` for cold runs.

## 7.5 Open research questions

Questions raised while running the campaign, with what would answer them.
Each names the runs queued for it; findings go in the progress log.

**RQ-Z1. Does zstd level 3 have enough throughput for 10 GbE?**
rsync `-z` compresses at about level 3 on one thread; `xs -z` picks level 1
above 64 MiB/s and level 3 only below it or when asked. To fill a 10 Gb/s
link the sender must emit about 1.25 GB/s of compressed data, so on data
that compresses r times it must compress r × 1.25 GB/s of input: about
5 GB/s on `large-text` (4.2×), across all its workers together. The
receiver must decompress as fast, though zstd decompresses much faster than
it compresses.
- Evidence so far (Z1, one block, Mac to mars, the Mac loaded):
  `large-text` at level 3 delivered 2.96 Gb/s of data, against 7.27 Gb/s
  at level 1 and 3.13 Gb/s without `-z`; rsync `-z` 0.94 Gb/s. At level 3
  the Mac's eight performance cores could not keep up: compressing slowed
  the copy below not compressing at all.
- To answer it: `codec-bench`, a job on the Mac and mars measuring zstd
  levels 1 to 3 on one thread and on eight, the zstd fast levels and LZ4,
  on a 1 GiB file of `large-text`; Z1b (no `-z`, adaptive, levels 1 and 3,
  both directions, `large-text` and `large-half`); Z2b (`-j16` and larger
  blocks at levels 1 and 3, with engine metrics, so each end's CPU is
  recorded); and on gigabit, Z3 from neo and freya, where level 3 may be
  affordable except on the Pi.
- Answer in the form: the highest data rate each host delivers at level 3
  with all its workers, against line rate, and which end limits it.

**RQ-Z2. Should zstd level 1 be compared with LZ4, and is LZ4 worth adding?**
LZ4 compresses several times faster than zstd level 1 per core but less
well. At 10 Gb/s the trade is CPU against bytes, and which wins depends on
the data and the cores. `xs` speaks only zstd, but zstd's negative ("fast")
levels trade ratio for speed in LZ4's direction while keeping the format,
and `xs --compress-level` already accepts them; rsync can use LZ4 itself
(`--zc=lz4`).
- To answer it: `codec-bench` (ratio and MB/s of `lz4 -1` against zstd 1
  and `--fast=1`, `5`, `20`); Z4 end to end at 10 Gb/s (`xs` at levels 1,
  -1, -5 and -20 against rsync with zstd and with LZ4, both directions,
  `large-text` and `large-half`).
- Decision rule: add an LZ4 codec to `xs` only if no zstd fast level matches
  LZ4's delivered rate at a similar ratio. Otherwise extend the adaptive
  policy to choose a negative level at high link rates, which needs no
  protocol change.

## 8. Build order

| Milestone | Deliverable | Done when |
|---|---|---|
| M0 | Operator setup: baseline revision committed on `main`; helper reviewed and installed with its `sudoers` entry on neo, freya and mars; SSH keys in both directions for each pair; a benchmark root owned by the benchmark user on each host | `preflight.py` reports no problem for the link |
| M1 | `hosts.toml`, `preflight.py`, `probe.py` | Inventory and path proof recorded for all three Linux hosts; a deliberately wrong interface fails the proof |
| M2 | `corpus.py` and manifests | Same seed gives the same digest on neo, freya and the Mac |
| M3 | `stage.py` | A stale or dirty binary on either end is refused |
| M4 | `plan.py`, `agent.py`, record schema | A smoke experiment runs detached on neo and survives the controller disconnecting |
| M5 | `analyze.py`, `report.py`, `selftest.py` | Synthetic selftests pass; coverage of the 95% interval is 93–97% |
| M6 | E0a, E0b on phase A | A/A is *equivalent*; an injected 2δ is called *slower* and an injected δ excludes 1; σ_d table published |
| M7 | `XSYNC_TUNE`, `XSYNC_METRICS`, `measure.py --env` | Existing tests pass; E0c is *equivalent* |
| M8 | `export.py`, table schemas, one figure spec | F2 and F3 render in holochart from E0a and smoke E1 data with no hand-edited numbers |
| M9 | E1 onward | — |

Progress, 2026-10-12: M0 to M6 are done for the LAN pair, and E1 and E1b have their first night of data.

- The helper is installed on neo and freya and was checked there: `netem`
  adds the stated delay and its timer clears it unprompted, the governor
  and freya's energy-performance preference are set and restored exactly,
  and `drop-caches` and `mount-scratch` work.
- `preflight.py --link lan` passes with SSH in both directions and rejects
  a wrong interface.
- All six generated corpora and two scale points were built at full size on
  the Mac, neo and freya, and every digest matches across the three.
- The three real corpora are frozen on freya, mirrored to neo and verified
  there by a full re-read against the pinned digests.
- The baseline revision is `bf596d28c5c9`. Its static release was built
  from `git archive` for both architectures and staged on neo and freya;
  the hashes are in `benchmarks/results/lab/builds/`. Replacing neo's copy
  with an older build made both `stage.py check` and `preflight.py --rev`
  fail.
- M4: `plan.py` expands a spec into randomized, interleaved blocks and
  `agent.py` runs them detached on neo. The smoke experiment
  (`benchmarks/experiments/E00-smoke.toml`: both tools, both directions,
  either end as SSH client, fresh and noop) produced 64 valid samples in 32
  valid blocks, each destination verified against its corpus manifest, with
  the agent running under PID 1 after the launching session ended. An arm
  with a bad option was recorded as void with the tool's own error, never
  as a timing. Both hosts were left with their governors restored and work
  directories removed.
- M5: `analyze.py` computes the paired ratios, intervals, robust checks and
  verdicts and writes the effects, absolutes, pairs and noise tables;
  `report.py` renders them; `selftest.py` passes all 20 of its simulated
  checks. The simulations showed that the block counts of section 5.5 give
  power to notice δ, not to earn a verdict at δ, so that section and E0b
  were corrected.
- M6, E0a (noise floor): 144 of 144 blocks valid, 12 per cell, in
  `benchmarks/results/lab/E0a-noise/`. No A/A pair was called faster or
  slower. At δ = 3% the pair was *equivalent* in 3 of 12 cells for xs and 5
  of 12 for rsync, and *inconclusive* in the rest, because the noise differs
  enormously by cell:
  - σ_d is 0.009 to 0.014 when neo receives a fresh copy, so 8 blocks
    suffice there.
  - σ_d is 0.12 to 0.26 when freya receives a fresh copy. The cause is
    occasional slow samples, not steady spread: one block had 23.0 s and
    15.7 s transfers among dozens at 12 to 13 s, and rsync's 100,000-file
    receive on freya ranges from 3.6 to 7.9 s. The robust interval stays
    narrow in those cells while the t interval does not, which is why the
    verdict is inconclusive.
  - No-op and one-file cells sit at 0.03 to 0.06, needing 16 to 46 blocks
    for a 3% question.
  - The first sample of a block is 1.35% slower on average (±0.42), up to
    6.7% in the noisiest cell. Random order keeps that from biasing a
    comparison but it adds noise; an untimed warm-up per block would
    remove it at the cost of one more sample.
  - Three block attempts were voided and retried because freya briefly
    resolved neo to an address routed through a Docker bridge.
- M6, E0b (known effects), 12 blocks: in three of four cells the injected
  6% was called *slower* (estimates 1.054 to 1.080) and the injected 3%
  gave an interval that excludes 1 (1.030 to 1.046) with no verdict, as
  section 5.5 predicts. In the fourth, a fresh 100,000-file copy to freya
  with σ_d near 0.15, neither was detected.
- Unattended running: `plan.py enqueue` and `plan.py night` put specs on
  the driver's queue and `overnight.py` runs them inside a time window.
  The first night ran E0b, E1 and E1b to completion, 464 of 464 blocks
  valid, eleven minutes inside its 22:00 to 04:00 window.
- E1 (baseline, time-to-durable, 12 blocks, 28 cells, Holm-adjusted): xs
  is *faster* than `rsync -a` in 21 cells, *inconclusive* in 7 and
  *slower* in none.
  - No-op: faster everywhere, by 2.3 to 2.5 times on 100,000 small files
    and by 6.5 times on the deep and the congress trees pulled to neo
    (20.0 s against 3.1 s, and 10.1 s against 1.55 s).
  - Fresh small files: about twice as fast to freya, 10 to 25% faster to
    neo.
  - Fresh mixed trees: no difference shown. With neo sending
    `mixed-bimodal` the ratio is 1.048 [1.026, 1.071]: about 5% slower,
    short of a verdict at δ = 3%.
  - The seven inconclusive cells are fresh copies, five of them to freya,
    where σ_d reached 0.24 to 0.53.
  - Cost: xs uses 1.3 to 2.4 times rsync's CPU on most cells and 5 to 8
    times on a no-op of a deep tree from neo, and 4 to 10 times its memory
    on fresh copies (110 to 200 MiB against 14 to 20).
  - Time-to-durable and wall time give nearly the same ratios here; the
    sync adds 0.1 to 1.2 s to either tool.
- E1b (client role, 10 blocks): for fresh copies, which end starts the
  transfer makes no detectable difference. For no-ops it does: both tools
  are 15 to 38% slower when freya is the SSH client and neo the server.
  One-file transfers show the same 40 to 50 ms, so it is a fixed
  session-setup cost on neo's side, large only against sub-second runs.
- Not yet in the agent: the `update-1pct` scenario, a throughput probe per
  block (only ping statistics so far), the once-a-second host sampler,
  resuming a run whose agent died, and a per-block warm-up.
- Why freya is noisy as a receiver (investigated 2026-10-12 from the 1,616
  valid samples of E0a, E0b, E1 and E1b): its scratch drive stalls.
  - 11 to 13% of fresh copies to freya run more than 15% over their cell's
    median, against 2 to 5% of fresh copies to neo.
  - Those slow samples go with I/O wait on freya (2.5 CPUs waiting on
    average, against 0.75) and with a slow sync afterwards (2.3 s against
    0.36 s). They do not go with network retransmits, with other processes'
    CPU on either host, with neo's temperature, with position in the
    block, or with how much was written in the minutes before.
  - A direct test with nothing else running shows it: fourteen 512 MiB
    synced writes to `/mnt/nvme` took 0.17 s at best and 10.0 s at worst,
    a 60-fold swing between about 3,000 and 51 MB/s. The same test on
    freya's other drive (ZFS) varied 1.2-fold around 1,500 MB/s, and on
    neo's drive 1.0-fold at 359 MB/s.
  - The drive is a Solidigm P41 Plus, a QLC drive whose fast write cache
    is small when the drive believes it is full. The filesystem is 86%
    full, is mounted without `discard`, and has had no TRIM in 37 days of
    uptime (zero discards in `/proc/diskstats`), because the weekly
    `fstrim` only covers `fstab` entries and this mount has none. In its
    slow state the drive writes below the speed of the gigabit link, so
    the transfer itself waits on it.
  - Fixed on 2026-10-12: the drive was reformatted and given an `fstab`
    entry, so the weekly `fstrim` now covers it. Twenty 512 MiB synced
    writes then took 0.18 to 0.27 s each, a 1.5-fold spread at about
    2,700 MB/s. The corpora were regenerated or copied back from neo and
    verified against their pinned digests.
  - For a few minutes after the reformat the same test still showed 7 to
    8 s rounds: the kernel was zeroing the new filesystem's inode tables
    in the background (`ext4lazyinit`). Preflight now refuses a host where
    that is running.
  - The drive should be re-tested if it fills up again.
- E1f (the seven fresh-copy-to-freya cells of E1, re-measured on the
  reformatted drive, 12 blocks, all valid, in
  `benchmarks/results/lab/E1f-fresh-to-freya/`). These replace E1's
  figures for those cells.
  - Noise fell sharply: σ_d went from 0.29 to 0.04 for `small-flat`, 0.53
    to 0.07 for `small-deep`, 0.24 to 0.02 for `mixed-threshold` and 0.03
    to 0.015 for `mixed-bimodal`.
  - *Faster*: `small-flat` 0.458 [0.447, 0.468], `small-opaque` 0.486
    [0.465, 0.508], `small-deep` 0.834 [0.797, 0.873].
  - Mixed trees with neo sending: xs is slightly slower, `mixed-bimodal`
    1.036 [1.026, 1.046] and `mixed-threshold` 1.028 [1.015, 1.042]. Both
    intervals exclude 1 (Holm-adjusted p 0.003) but neither clears δ = 3%,
    so the verdict is *inconclusive*: a real deficit of about 3%.
  - `small-real` is still *inconclusive*, 0.948 [0.820, 1.096]. Nine of
    its twelve blocks have both tools at 11.0 to 11.4 s; three early ones
    have a sample at 15 to 21 s with heavy I/O wait on freya, as does the
    first `small-deep` block. Those fall in the first quarter-hour of the
    run, which began minutes after 50 GB of corpora had been copied onto
    the drive, so the drive was probably still moving that data out of its
    write cache. The cell needs blocks from a run that starts on an idle
    drive.
  - `tiny-one` is now *inconclusive*, 0.922 [0.864, 0.985]: 0.17 s against
    0.18 s with σ_d of 0.10.
  - `probe.py storage --path DIR` is that write test, and every snapshot
    now records per-device write counts, write time and discards.

Tuning target T1, set on 2026-10-12: the Pi sending bytes. With neo sending
a mixed tree to freya, rsync runs at 113.9 MB/s and xs at 110.2 MB/s, a
ratio of 1.036 [1.026, 1.046]. First diagnostics, run by hand:

- A raw SSH stream on this link carries 115.0 to 115.9 MB/s whatever the
  cipher, so rsync is within 1% of the link and the best xs can do on an
  incompressible byte-bound transfer is parity.
- xs reports its limiting stage as the network, and sends the same bytes
  as rsync (1,396 MB), so the gap is not protocol overhead.
- On neo, xs uses 14.3 s of CPU where rsync uses 6.4 s, and 8.3 s of that
  is kernel time against rsync's 2.5 s.
- Under `strace`, the xs sender makes 135,000 writes for 1.33 GiB, 31% of
  them failing with EAGAIN, plus 98,000 `ppoll` calls: it feeds SSH
  through a non-blocking 64 KiB pipe in pieces of about 15 KiB. rsync
  makes 72,000 writes and none fail. This is H25, the transport write
  path, and needs the tunables of section 4.7 to test (`pipe_size`,
  `write_chunk`).
- AES-GCM costs the Pi half the CPU of the default ChaCha20-Poly1305 for
  the same throughput (4.0 s against 8.3 s for 2 GiB).
- T1a (screening, 12 blocks, both mixed corpora, all blocks valid, σ_d of
  0.003 to 0.008) tested the two suspects that need no engine change:
  - Fewer worker threads close the gap. Against rsync, xs with `-j1` is
    0.999 [0.997, 1.002] and 0.997 [0.996, 0.998], and with `-j2` 1.002
    and 0.998: *equivalent*, at link rate. Default xs in the same blocks
    is 1.023 [1.020, 1.027] and 1.014 [1.009, 1.019].
  - The Pi's kernel time falls with the thread count: 7.8 s by default,
    6.7 s at `-j2`, 4.7 s at `-j1`, against rsync's 2.3 s. So about half
    of the excess is thread contention and the rest is the write path.
  - AES-GCM makes xs about 1% faster (0.992 and 0.989 against default xs)
    and cuts its user CPU on the Pi from 6.0 s to 3.6 s. It does nothing
    for rsync's time, which is already at the link's limit.
  - `-j` applies to both ends and to every workload, so this is not yet a
    setting to adopt: small-file and no-op cells may want more workers,
    not fewer. That is what the wider `-j` sweep (E3a) must show.
- The larger lever for this workload is compression, since the link is
  the limit and two thirds of `mixed-bimodal` is compressible.
- E3b (screening, 10 blocks, three corpora, both directions, all blocks
  valid), fresh copies with `-z`:
  - xs with `-z --compress-level=1` against plain xs: `mixed-bimodal`
    0.783 [0.779, 0.788] from neo and 0.794 from freya; `small-real` 0.489
    [0.445, 0.537] from neo and 0.807 from freya. All *faster*.
  - On random data (`small-opaque`) `-z` costs xs about 5% with neo
    sending, 1.054 [1.034, 1.074], and 2 to 3% the other way.
  - `rsync -z` is *slower* than plain rsync whenever neo sends anything
    not highly compressible: 1.368 [1.324, 1.413] on `mixed-bimodal` and
    2.025 [1.751, 2.342] on `small-opaque`. H14 reproduces for rsync; xs
    avoids it.
  - Against plain rsync, xs with `-z` is 0.501 [0.461, 0.545] on
    `small-real` from neo and 0.607 from freya.
  - **The adaptive level misfires on the Pi.** In two of ten blocks of
    `mixed-bimodal` from neo, xs with plain `-z` took 18.0 and 16.6 s
    against 9.9 s, burning 61 to 68 s of CPU on neo against 19 s, for 6%
    fewer bytes. Level 1 fixed never did this (σ_d 0.008 against 0.235).
    Reproduced by hand with `-vv`: the slow runs report level 3 for the
    whole transfer. The policy starts at 3 and leaves it only when
    transport writes measure at 64 MiB/s or more. On the Pi, four
    compressor threads at level 3 take CPU from ssh, the gigabit link then
    measures at about 46 MiB/s, and the transfer stays at level 3, which
    the Pi can only produce at 68 MB/s of input. How often varies by
    session: 2 of 14 runs in one, 11 of 16 in another.
  - Fix, on the `adaptive-compression` branch (not merged), final build
    `e1f05b518049`: the original rate rule is kept unchanged, and a cap is
    added. When the writer has kept up with everything produced for 16 MiB
    in a row, the level in force is more than this machine can sustain
    against this link, so the level is capped a step lower and the rate
    the machine was producing at is kept. The cap lifts when the link is
    seen, while it is the bottleneck, to carry distinctly less than that.
    `-vv` now reports the level that compressed the most input, with the
    split.
  - Three earlier attempts were discarded, each for a measured reason:
    starting at level 1 was 14% slower under a 4 or 20 MiB/s limit, where
    level 3 sends 30% fewer bytes of text and most of a transfer is
    compressed before the first decision; judging starvation by the
    writer's waiting time dropped the level during the scan phase; and
    replacing the rate rule outright (build `5aa5555ec8dd`, tested in
    T2a) removed the slow runs but cost the Pi about half a second on
    every transfer, since the original rule usually leaves level 3 after
    256 KiB. T2a: with neo sending, `mixed-bimodal` median 10.4 s against
    10.0 s but worst case 11.4 s against 19.5 s; `small-flat` 1.137
    [1.035, 1.249]; with freya sending, *equivalent* in two cells of three.
  - Hand checks of the final build on neo, single runs: ten alternating
    `mixed-bimodal` runs 9.7 to 10.4 s against 9.6 to 10.4 s for the old
    build, which did not trap in that session; `--bwlimit` 4 MiB/s 21.4 s
    against 21.8 s, 20 MiB/s 6.7 s both, 40 MiB/s 4.7 s against 6.6 s.
  - T2b (confirmatory, 12 blocks, all valid): the final build against the
    old one with `-z`.
    - freya sending: *equivalent* on `mixed-bimodal` (1.000 [0.996,
      1.003]) and `small-flat` (0.996 [0.986, 1.007]); `small-real`
      *inconclusive* (1.027 [0.967, 1.091]).
    - neo sending `mixed-bimodal`: 0.902 [0.806, 1.010], *inconclusive*.
      The old build had three slow runs in twelve (13.8, 14.5, 18.6 s);
      the new build's twelve lie between 9.7 and 11.0 s. Mean 10.29 s
      against 11.66 s.
    - neo sending `small-flat`: 0.957 [0.912, 1.004], *inconclusive*.
    - neo sending `small-real`: 1.007 [0.907, 1.118], *inconclusive*, and
      not a test of the fix: all three arms, fixed level 1 included, slowed
      from 6 to 10 s early in the run to 14 to 20 s by its end, with I/O
      wait on freya (see below).
    - So the fix costs nothing where it has nothing to do and removes the
      slow runs where it does, but twelve blocks cannot turn an
      intermittent fault into a verdict: the interval is as wide as the
      fault is rare.
- **freya's scratch drive degraded again within a day.** After the
  reformat it wrote 512 MiB in 0.18 to 0.27 s; by the end of 2026-10-12,
  after several hundred GB of corpora written and deleted, every round
  took 2.6 to 5.6 s (155 MB/s). The filesystem is 3% full, but nothing has
  been trimmed since `mkfs` (`/proc/diskstats` still shows the same 955
  discards): the weekly `fstrim` is far too rare for this write volume.
  Small-file copies to freya late in the day are affected; byte-bound ones
  are not yet, since 155 MB/s is still above the link. One `fstrim`
  (1.96 TB discarded) restored 3,000 MB/s. The helper now has a
  `trim-scratch` verb and the agent calls it at the start of every run.
- Supplementary experiments between this Mac and mars (2026-10-12): the
  harness now drives a local macOS endpoint without SSH, builds its own
  binary from the same commit, and writes to
  `benchmarks/results/supplementary/`. The Mac accepts no SSH, so it is the
  driver and the SSH client in both directions; it has no helper, no cold
  cache and no quiet-host gate, so these runs are noisier than the path
  experiments and are kept apart from them. Only small-file corpora are
  run. A background run waits whenever a path experiment marks one of its
  hosts as in use. `S1-mac-mars-small.toml` is the first.
- mars's login shell is fish, so every remote script now runs under `sh`.
- The adaptive-compression fix was merged into `main` on 2026-10-12 as a
  fast-forward to `e1f05b518049`, the build already staged on neo and
  freya, which is the baseline revision from here on.
  - **xs compresses small files much less well from a fast sender.** For
    `small-real` it sends 84 MB from neo but 123 to 197 MB from freya,
    against rsync's 64 MB either way, and the figure varies run to run
    even at a fixed level. xs compresses each block alone, and with many
    workers the blocks are flushed smaller. This is a lead for the block
    size and idle-flush tunables (E4a).
- Queue of 2026-10-12 (started 21:09 UTC because both hosts were free,
  finished 05:59 UTC, baseline `e1f05b518049`): five runs, 1,120 samples,
  332 of 332 blocks valid, none voided. The scratch drive was trimmed at
  the start of each run.
- E1f, second run of 12 blocks. The report pools both runs (24 blocks);
  that is a second look at a confirmatory experiment, so the pooled
  intervals should be read at `--looks 2`.
  - Mixed trees with neo sending, last night alone: `mixed-bimodal` 1.038
    [1.034, 1.043] with σ_d 0.007, `mixed-threshold` 1.031 [1.021, 1.041].
    Pooled: 1.037 [1.032, 1.042], *slower*, and 1.030 [1.022, 1.037],
    *inconclusive*. The deficit of T1 is real and is 3 to 4%.
  - `small-flat` 0.520 [0.487, 0.556], `small-opaque` 0.514 [0.493, 0.537],
    `small-deep` 0.812 [0.750, 0.879], `tiny-one` 0.902 [0.872, 0.933]:
    all *faster* (pooled).
  - `small-real` is still *inconclusive* by the t interval, 0.951 [0.884,
    1.023], because of one rsync sample at 16.0 s in the first block; the
    other eleven blocks have rsync at 11.0 to 11.7 s and xs at 11.1 to
    11.3 s, and the robust estimate is 0.984 [0.971, 0.992]. The two tools
    are within 2% of each other on this cell.
  - **Trimming did not remove the first-blocks effect.** The first two
    `small-deep` blocks had samples at 16 to 18 s against 6 to 8 s
    afterwards, and rsync's small-file times to freya still vary (5.2 to
    7.7 s on `small-flat`) while xs's do not (3.4 to 3.7 s). The noise in
    these cells is now mostly rsync's own, and what is left of the drive's
    is in the first minutes after a trim. A run should discard a warm-up
    block per cell (the per-block warm-up of M5, not yet built).
- E3a (screening, 10 blocks, `-j` 1, 2, 4, 8 against the default, three
  corpora, fresh and no-op, both directions). `-j` applies to both ends;
  the default is the core count capped at 16, so 4 on neo and 16 on freya.
  - **No single worker count is right, and one is clearly wrong.** `-j1`
    recovers the byte-bound deficit with neo sending (`mixed-bimodal` 0.966
    [0.955, 0.977]; `-j2` 0.973, `-j4` 1.003 *equivalent*, `-j8` 1.027) but
    is *slower* on every no-op (1.15 to 1.58), on `small-flat` from neo
    (1.93 [1.60, 2.33]) and on `small-real` from freya (1.12). The time on
    the Pi is monotone in the worker count for large files and the reverse
    for small ones.
  - With freya sending bytes, the count does not matter (0.989 to 0.993,
    all intervals include 1).
  - **Sixteen workers are too many for a no-op on freya.** `small-real`
    no-op from neo to freya takes 1.63 s by default and 1.01 s at `-j4`
    (0.624 [0.537, 0.724], *faster*), 1.09 s at `-j2`, 1.18 s at `-j8`. No
    such effect on `small-flat` or with neo receiving.
  - `-j2` is 5% *faster* than the default for `small-flat` from freya to
    neo (0.948 [0.938, 0.958]), where neo is the receiver.
  - What to build from this: the worker count should be chosen per side and
    per kind of work, not once. Candidates for M7 and a confirmatory run:
    one or two data workers per large file on a sender with four cores or
    fewer, the present count for scanning and small files, and a default
    cap below 16.
- E3b-confirm (confirmatory, 12 blocks, Holm over 16 comparisons), `-z`
  against plain xs on fresh copies, with the merged adaptive level:
  - *Faster* on compressible data in both directions: `mixed-bimodal` 0.773
    [0.768, 0.779] from freya and 0.794 [0.779, 0.809] from neo;
    `small-real` 0.844 [0.785, 0.906] from freya and 0.505 [0.481, 0.530]
    from neo; `small-flat` from freya 0.932 [0.917, 0.947].
  - No trapped runs: `mixed-bimodal` from neo has σ_d 0.030 against 0.235
    for the old build in E3b.
  - The second half of the hypothesis fails. On random data `-z` costs more
    than 3% with neo sending: `small-opaque` 1.054 [1.043, 1.065],
    *slower*; from freya 1.035 [1.024, 1.046], *inconclusive*.
    `small-flat` from neo is 1.050 [1.028, 1.073], *inconclusive*. So `-z`
    is not yet safe to enable by default on a gigabit link; skipping
    blocks that do not compress is the missing piece.
  - Plain rsync against plain xs in the same blocks: 1.36 on `small-real`
    from freya, 1.73 and 1.62 on `small-flat` and `small-opaque` from neo
    (all *slower*), *equivalent* on `mixed-bimodal` both ways (1.009 and
    0.981; the 0.981 is T1 again).
- E1r, real trees with `-aH` (screening; 6 and 4 blocks, so estimates
  only):
  - `real-holochart` (249,602 files, 7.3 GiB): fresh copies are link-bound
    at about 70 s, 0.953 [0.936, 0.971] from freya and 1.003 [0.993,
    1.013] from neo. No-ops are 0.207 [0.191, 0.225] to neo (1.6 s against
    7.6 s) and 0.373 [0.356, 0.392] to freya (1.3 s against 3.6 s). The
    synthetic small corpora predicted both.
  - **`real-laikav2`: xs is 19 to 24% slower, because it sends hard-linked
    data once per name.** 1.190 [1.173, 1.207] from freya and 1.242 [1.240,
    1.245] from neo, 392 s against 316 to 330 s. The tree has 19,345 hard
    links. rsync `-H` transfers 35,346 files and 36.7 GB; xs `-H`
    transfers all 54,691 names and 45.3 GB, then links them at the
    destination (verification, which checks the links, passes for both).
    Both tools run at link rate, 116 MB/s, so the whole difference is the
    23% of extra bytes. This is a defect in the remote `-H` path, not a
    tuning matter, and it hides how xs compares on the rest of that tree.
    The run should be repeated after the fix, or meanwhile without `-H`.
  - On the Pi, sending `real-laikav2` costs xs 357 s of CPU against
    rsync's 150 s.
- The `-H` defect is fixed in build `8cc75bbdb801`, merged into `main` on
  2026-10-13 and the baseline revision from here on. The decision to transfer a file is made in
  one place for local and remote copies, so the fix is there: the first
  name of a source inode that is transferred, or is already up to date,
  holds its data; a later name with nothing at the destination is left off
  the transfer list and linked to the holder after the last transfer, with
  the same pinned and verified temporary link as before, and without
  replacing anything that has appeared at the name. Itemized output and
  `--stats` now match rsync's (one transfer per inode, the same anchor).
  If the holder is not transferred, the names waiting on it are reported
  and the run exits with code 23; rsync would try the next name instead.
  - Checked on the Mac: the differential hard-link tests against rsync, two
    new ones (data sent once; a late name is linked, not sent), the
    publication-race test extended to the new link path, 231 differential
    scenarios, and 3,000 link groups over 60 directories with 16 workers,
    nine runs, identical contents and link topology each time.
  - Checked by hand between neo and freya over SSH, both directions: a
    20 MB file with three names sends 20 MB where the old build sent 60 MB.
  - E1r-laikav2-linked (screening, the same cells and four blocks with
    the fixed build, 8 of 8 blocks valid, full verification passing): xs
    now transfers the same 35,346 files and 36.8 GB as rsync. The ratio is
    0.970 [0.953, 0.988] from freya (318 s against 327 s) and 1.006 [1.003,
    1.009] from neo (317.5 s against 315.7 s), where it was 1.190 and
    1.242. With the links out of the way the tree behaves like the
    synthetic mixed corpora: level with rsync at link rate, a fraction
    behind when the Pi sends.
  - CPU on the Pi sending this tree is still 1.84 times rsync's (about
    285 s against 153 s), which is tuning target T1.
- S1 (supplementary, the Mac and mars over mesh Wi-Fi, 12 blocks, 192 of
  192 valid, in `benchmarks/results/supplementary/S1-mac-mars-small/`;
  caveats in the `README.md` beside it). σ_d is 0.16 to 0.55 on the
  100,000-file corpora, against 0.01 to 0.19 in the path experiments, so
  only large effects show.
  - Pushing from the Mac to ext4: xs is 2.7 to 3.4 times faster on fresh
    copies (`small-flat` 4.4 s against 15.0 s) and 1.9 to 3.3 times faster
    on no-ops.
  - Pulling onto APFS, `small-flat` and `small-opaque`: 0.805 [0.726,
    0.892] and 0.775 [0.669, 0.899] fresh, about 21 s against 28 s; no-ops
    2.5 times faster.
  - **Pulling a deep tree onto APFS, xs is slower:** `small-deep` fresh
    1.75 [1.53, 1.99] (57 s against 33 s) and no-op 3.66 [2.87, 4.66]
    (11.3 s against 3.1 s). The Mac spends 89 s of kernel time on the
    fresh copy against rsync's 42 s, and 27 s on the no-op against 1.9 s.
    The tree has 116,667 directories; the same files in a flat tree show
    no such cost, and neither does a Linux receiver (E1). A lead for the
    macOS receiver's per-directory work, to be looked at on the Mac leg.
  - `tiny-one` is noise: σ_d 0.6 to 0.8 on a 0.3 s transfer over Wi-Fi.

- M7 is done (2026-10-13), on the `tunables` branch, engine commit
  `ddefa041364e`, not yet merged. Section 4.7 describes what was built.
  - The existing differential and wire tests pass on both builds; a new
    engine test covers refused settings, extreme settings in both
    directions and locally, and the metrics lines.
  - E0c (confirmatory, 16 blocks, 64 of 64 valid): the tunables build at
    default values against the release build of the same commit, and
    again with its metrics file on. *Equivalent* in all eight comparisons;
    the widest interval is 0.978 to 1.016, and the ratios on
    `mixed-bimodal` are 1.000 [0.996, 1.004] and 0.999 [0.992, 1.006].
    Collecting metrics costs nothing measurable. So `ddefa041364e-tune`
    may be used for experiments.
  - By hand over the LAN: both ends' transport descriptors are pipes, the
    kernel grants 1 MiB when asked, and a sender with one worker faces a
    receiver with sixteen.
  - Queued for the night of 2026-10-13, 22:00 to 04:00 Central, both on
    the tunables build with metrics: T1b (write path: pipe size, write
    size, one sending worker, against default xs and rsync, on the two
    mixed corpora, both directions, 240 samples) and T1c (worker counts
    one end at a time: sender 1 or 2, receiver 2, 4 or 8, on three corpora,
    fresh and no-op, both directions, 720 samples).

  - Started on the afternoon of 2026-10-13, in the hours before the queue
    opens, as a chain of three tunables screens on the LAN pair: E4g
    (peer-exit poll of 25, 5 and 1 ms on no-ops, 40 blocks), E4a with `-z`
    (block size, `small_max` and read-task size on compressible small
    files), and E4b/E4d for small files (read-task size, scanning workers,
    listing window; fresh and no-op). Each has a latest start time so that
    none runs into the queue.
  - In the background on the Mac and mars, S2: the deep-tree pull onto
    APFS with one, two, four (the default) and eight receiving workers on
    the Mac, and with one scanning worker, against rsync.

- Continuous running began on 2026-10-13 (section 7.1). The windowed
  queue and `overnight.py` are gone; `runner.py` works neo's backlog with
  a sentinel every 6 hours and 750 GiB a day of writes allowed per host.
  Scripts are staged as immutable bundles, so staging no longer breaks
  queued plans. Checked by 12 runner tests and by a live run on the Mac and
  mars: sentinel and backlog runs in turn, a pause, and two replacements of
  the runner under a run in progress. First backlog: T1b and T1c (made for
  the old window, run under their original scripts), E4g confirmation, E1
  on the current baseline, and the holochart tree at 8 blocks.

- Results of the first continuous night, 2026-10-14 (all blocks valid):
  - T1b (write path, screening): a 1 MiB pipe and 256 KiB or 1 MiB writes
    change nothing, *equivalent* or within 1% in every cell. One sending
    worker on neo is 5% *faster* on both mixed corpora (0.947 [0.934,
    0.961] and 0.944 [0.933, 0.956]), the same as rsync in the same blocks
    (0.951, 0.947). From freya nothing differs. So the write path is not
    T1's cause; the number of workers feeding the one stream is.
  - T1c (workers per end, screening): one sending worker helps only that:
    on neo it is 5% faster for byte-bound copies but 11 to 39% *slower* on
    small-file no-ops and up to 36% slower on small fresh copies, and from
    freya 16% slower on a `small-flat` no-op. Two sending workers sit in
    between. Fewer receiving workers on freya make a `small-real` no-op
    26 to 32% *faster* (recv2 0.680, recv4 0.689, recv8 0.741), as in E3a;
    elsewhere receiver counts are inconclusive. The candidates for an
    engine change: limit how many workers stream large files at once on
    a sender with few cores, leaving the rest for small files and
    scanning; and cap the receiver's default below 16. T1e confirms the
    second with tunables before any code changes.
  - E4g confirmation (Holm over 12): polling for the peer's exit every
    1 ms is *faster* for the one-file tree from neo, 0.868 [0.854, 0.882]
    fresh and 0.899 [0.876, 0.922] no-op, and *equivalent* on `small-flat`
    fresh copies. The other cells are inconclusive at their noise. A small,
    safe gain on tiny transfers; better than a shorter poll is to wait for
    the peer's exit without polling (an E5 candidate).
  - E4b/E4d (small-file pipeline, screening): no read-task size, scanning
    share or listing window moves a small-file copy or no-op by a
    detectable amount; σ_d is 0.08 to 0.4 in those cells.
  - W0a (Wi-Fi noise floor): mars to orion behaves (A/A σ_d 0.02 on tiny
    and `small-flat` fresh), but orion to mars does not: σ_d 0.4 to 1.9,
    and one A/A cell even called *faster*. Of the 288 samples orion
    started, 31 took 5 or 10 s longer than their cell's median. That is
    orion's multicast DNS: a lookup of `mars.local` takes 5,017 ms when
    its cache has lapsed and 8 ms otherwise. orion's SSH handshake with
    mars also takes about 0.68 s, which pads every transfer it starts.
    Neither is the radio. The agent now looks each peer's IPv4 address up
    once per run and connects to it, checking the host key under the
    peer's name. On the wired pair the same kind of spike is rare (1 in
    100 to 1 in 400 samples) and only when neo starts the transfer.
  - Early contrasts on the Wi-Fi pair, to be confirmed by W1: a fresh
    `small-deep` copy into orion takes xs 36.6 s against rsync's 23.8 s,
    where on the wired pair xs is the faster; and no-ops into orion are 1.4
    to 2.3 times faster with xs, as on the wired pair.
  - Queued 2026-10-14: on mars W0b (the noise floor again, with the lookup
    fixed) then W1; on neo T1e after the holochart run. orion's write
    allowance was raised to 400 GiB a day so that W1 follows W0b.

- The sending-worker cap, on the `tunables` branch (`453704a64528`), not
  merged: `send_streams=N` lets at most N sender workers read files larger
  than `small_max` at once. A worker that meets a large file while every
  stream is busy sets it aside, finishes the small files of its task and
  queues the large ones again, so no worker idles while small files wait.
  Release builds compile it away. The metrics line now reports the most
  streams that ran at once and how many files waited; the engine test
  checks that with one stream, nine large files never overlap and the tree
  still copies exactly. T1f (screening, 600 samples) is at the front of
  neo's backlog: the cap at 1 and 2 against default xs, the one-worker
  sender and rsync, on `mixed-bimodal`, `small-flat` and `small-real`,
  fresh and no-op, both directions. If it holds, the default becomes a cap
  for senders with four cores or fewer, measured again on the Wi-Fi pair,
  where the sender is a Pi 4.

- T1f (the stream cap, screening, 120 of 120 blocks valid): the cap is
  harmless and nearly useless. Capping the sender at one large-file stream
  is *equivalent* or inconclusive everywhere, including small files and
  no-ops, but from neo it gains only 1.3% on `mixed-bimodal` (0.987
  [0.977, 0.998]) where one sending worker gains 3.5% (0.965) and rsync is
  level with that. The counters say why: with the cap, the Pi's sender
  still used 12.9 s of CPU and 5,020 involuntary context switches a run,
  against 9.7 s and 120 with one worker. The other workers keep reading
  small files beside the one stream, and four workers plus the writer
  thread share four cores with ssh. One sending worker again cost 13 to
  61% on small files. So the contention is xs's workers against ssh, not
  large-file readers against each other. T1g (queued) tries three and two
  sending workers, and three with the cap, on the Pi only.
- E1v2 (confirmatory, the baseline matrix on `8cc75bbdb801`, 336 of 336
  blocks valid, Holm over 28): xs is *faster* than rsync in 20 of 28
  cells, *equivalent* in two (byte-bound from freya), and slower in none.
  The only cells where xs is behind are the four byte-bound copies from
  neo, 3.7% on both mixed corpora (inconclusive at δ = 3%), which is T1.
  No-ops are 1.1 to 6.7 times faster (`small-real` from freya 1.39 s
  against 9.16 s), and small fresh copies from the Pi 1.6 to 1.7 times
  faster. Against E1 on `bf596d28c5c9` nothing moved beyond its interval;
  `mixed-threshold` from neo went from 0.955 to 1.037, which E1 had
  inconclusive at higher noise.
- Daily write allowances raised to 2,500 GiB on neo and freya
  (2026-10-14): data collection is planned for one to two weeks, so drive
  wear is not a constraint at that rate.

- T1g (fewer sending workers on the Pi, screening): neither three nor two
  sending workers, nor three with one stream, recovers the byte-bound gap
  on `mixed-bimodal`; on `mixed-threshold` two workers and three with one
  stream come to 0.969 and 0.966 against rsync's 0.962. Two workers cost
  14% on a `small-flat` no-op, three cost 24% on a `small-real` no-op. No
  setting of the existing knobs is a free win; T1h repeats the byte-bound
  cells at 20 blocks.
- T1e (receiver workers on freya, confirmatory, Holm over 28): four
  receiving workers are *faster* than sixteen on a `small-real` no-op
  (0.649 [0.562, 0.749]) and a `small-opaque` fresh copy (0.955 [0.942,
  0.969]); eight are faster on the `small-real` no-op (0.721). Nothing is
  slower. This is ready to become the receiver's default on many-core
  hosts, an engine change.
- A week unattended, from 2026-10-14 17:00 Central, neo and freya only
  (orion and mars are paused while orion is used for other work).
  The runner now retries a run that failed before its first sample (up to
  three times), lifts a halt by itself after an hour, settles runs left
  unfinished by a reboot, and runs maintenance jobs between experiments;
  `plan.py runner start` writes `runner.sh`, which neo's crontab runs at
  boot. The backlog, in order, about 175 hours with the sentinel every six
  hours: generate the 13 scaling corpora on both hosts (pinned from a run
  on the Mac); E3f ciphers; E8a and E8b, the size and count curves; E1c,
  the baseline with cold caches; E1b2, push against pull; E3d metadata
  flags; E3c `--no-atomic`; E3g output; E4b and E4b2, queue sizes and soft
  limits; E4a2, block size and small-file cutoff without `-z`; E1r3,
  `laikav2` at 8 blocks; T1h; E1z, the `-z` baseline; the two curves with
  cold caches; the holochart tree cold; then 80 alternating pairs of R1
  (the baseline matrix, 4 blocks) and R2 (`small-real` and holochart, 2
  blocks) as day-to-day replicates.

- Direct cable, Mac and mars, 2026-10-14/15 (`benchmarks/results/direct/`;
  the Mac's USB adapter holds TCP to about 3 Gb/s; times include the final
  sync; rates are corpus bytes over durable time):
  - Large files, mars to the Mac: xs runs at the link's ceiling, 3.0 to
    3.16 Gb/s on all three large corpora, against rsync's 1.7 to 1.9 Gb/s
    (ratios 0.56 to 0.61, *faster*). Nothing in X2 or X3 (`-j4`, `-j8`,
    4 MiB blocks, 1 MiB writes and pipes, deeper queues) changes that:
    there is nothing left to gain below the link.
  - Large files, Mac to mars: xs 2.3 to 2.6 Gb/s on the ISO but 1.25 to
    1.84 Gb/s on the four-file and mixed corpora, with wide intervals and
    the same arm differing by a third between runs. The Mac as a sender
    is noisy; X3b's tuning arms are not readable there.
  - ChaCha20 costs both tools 1.4 to 1.7 times AES-128-GCM, the Mac's
    default; AES-256-GCM costs nothing measurable. rsync `--inplace` and
    `-W` do not close its gap.
  - Small files onto mars's NVMe (N1): xs is twice as fast as rsync fresh
    (`small-flat` 0.71 Gb/s against 0.41, mixed 2.6 to 2.9 against 1.3)
    and 3 to 4 times on no-ops. Only four receiving workers with
    `--no-atomic` reach 1 Gb/s on `small-flat` (1.01 Gb/s, 0.689 [0.517,
    0.918], *faster*, N3); `--no-atomic` alone 0.85, inconclusive.
    `small-deep` stays at 0.27 to 0.38 Gb/s whatever the setting.
  - Small files onto the Mac (N2, cold on mars): 5 to 7 times slower than
    onto mars, 0.04 to 0.12 Gb/s, and xs no better than rsync on fresh
    small trees. APFS creating files is the limit, as in S2. Mixed trees
    still 1.7 to 2.3 times faster with xs; no-ops 4 times.

- Direct cable at 10 Gb/s, 2026-10-15/16. The earlier 3 Gb/s ceiling was
  mars's X540 in a chipset PCIe 2.0 x1 slot, not the Mac's USB adapter;
  moved to an x8 slot, raw TCP is 9.41 Gb/s each way on one stream with
  the Mac's Thunderbolt 4 adapter (Aquantia, en13), and 4.3 to 5.2 Gb/s
  with the USB adapter. One ssh connection carries 7.7 to 8.6 Gb/s with
  AES-GCM and 2.2 with ChaCha20.
  - X5 (6 blocks a cell, stopped early): mars to the Mac, xs 8.1 to 8.7
    Gb/s against rsync's 2.8 to 2.9, ratios 0.33 to 0.36 with narrow
    intervals. That is one ssh connection's ceiling. Mac to mars, xs 5.6
    to 7.0 Gb/s against about 3, but with intervals from 0.29 to 0.98.
  - X6 (tuning at 10 Gb/s): mars to the Mac, nothing moves by more than
    2% (`-j4` and 1 MiB writes 0.982 to 0.989); there is no headroom left
    under ssh. Mac to mars is unreadable: the default arm itself took 9.8
    to 28 s, and the engine's counters show the Mac's sender spending the
    whole run writing into ssh. mars's NVMe takes synced writes at 3.1
    GB/s median, so the receiving disk is not the limit; the Mac was
    heavily loaded (load average 75 to 200) through these runs.
  - rsync stays at 2.8 to 3.2 Gb/s on every large corpus in both
    directions, with its Mac side at about one core: a single thread's
    limit.
  - End of the 10 Gb/s phase, 2026-10-16: Z4 (codecs) is the last run on
    mars; Z2b was dropped. The GPU goes back in mars's x8 slot and the X540
    comes out; later Mac-to-mars work (the HDD set, H1–H5) uses mars's
    onboard 2.5GbE. A Thunderbolt/USB4 host link between the Mac and mars's
    ASM4242 was tried: it trains at 2 × 10 Gb/s and logs in, but drops every
    few seconds, so it is not usable. On 2026-10-17 freya's and mars's
    motherboards are swapped (thermal paste arriving), which puts a free
    PCIe 4.0 x4 slot in mars for the X540; freya's later runs are a new
    hardware configuration and are marked as such.

M0 is done by the operator, not by the harness. M1–M6 need no engine
change, so flag-only experiments (E1–E3) can start before M7.

## 9. Datasets for the paper

The findings are to be written up with figures drawn in holochart
(`~/projects/holochart`). Holochart takes Plotly-shaped figure JSON, and its
Express API builds a figure from a table — rows, columns or CSV text — by
column name: `x`, `y`, `color`, `symbol`, `lineDash`, `facetRow`,
`facetCol`, `errorY`/`errorYMinus`, `hoverData`. A figure can therefore only
facet, colour or draw an interval from a column that was recorded. This
section fixes the tables the framework exports and the collection rules that
the statistics alone would not force.

The paper is a scientific report first. Showing what holochart can do is a
secondary aim and is kept to the places listed in section 9.6.

### 9.1 Collection rules

1. **Raw samples are the dataset.** Strip, violin, box, histogram and ECDF
   charts are computed from individual observations, so every valid sample
   is kept and exported. Summaries are derived tables and can always be
   rebuilt; raw rows cannot.
2. **One row per observation, one meaning per column.** Holochart infers
   each column as numeric, categorical or date. A column never mixes them:
   `jobs` is a number, with a separate `jobs_auto` flag, not `"auto"` among
   integers. Missing is an empty cell, never `0` or `-1`.
3. **Base units, named in the column.** `wall_s`, `wire_bytes`,
   `rss_bytes`, `temp_c`. No pre-formatted strings such as `"5.4 s"` or
   `"1.12x"`.
4. **Every factor on every row.** Link, direction, client role, cache
   state, added delay and loss, host roles and filesystem are columns even where a phase holds them constant, so
   tables from the three phases concatenate without repair.
5. **A numeric level and a label for every swept factor.** `level` (for a
   log axis and a fitted line) beside `arm` (for a legend and a categorical
   axis).
6. **One vocabulary, declared once.** Arm, corpus, scenario and host-role
   names and their display order live in one file, are never renamed after
   data exists, and are exported for holochart's `categoryOrders` and
   `labels`.
7. **Bounds and distances.** Interval tables carry `lo` and `hi` and also
   `err_minus = est − lo` and `err_plus = hi − est`, because holochart error
   bars take distances from the point. Ratios are asymmetric on a linear
   axis, so both are needed.
8. **Ratios and absolutes.** Inference is on ratios, but tables and scaling
   curves need per-arm files/s, MB/s and seconds with their own intervals.
9. **Complete grids.** A heatmap or surface needs every cell of a
   factorial. The void-block rule already re-runs holes; the export fails
   rather than writing a ragged grid.
10. **UTC timestamps.** ISO 8601 on every sample and probe, for date axes
    and for joining samples to host-state series.
11. **Provenance on every row.** Run id, block, position and short binary
    hash travel with each row so a hover label can identify any point.
12. **Voids are data too.** Voided blocks are exported in their own table
    with the reason, for the data-quality table in the paper.

### 9.2 Tables

`export.py` derives these from the sample store. Each is a CSV with a
`schema.json` giving column types, units and vocabulary order.

| Table | One row per | Main columns | Source |
|---|---|---|---|
| `samples` | valid timed transfer | cell fields, arm, level, block, position, `wall_s`, `durable_s`, CPU and RSS per side, wire bytes, retransmits, `files_per_s`, `mb_per_s`, timestamps | every experiment |
| `pairs` | block × non-control arm | cell fields, arm, block, `t_arm_s`, `t_ctl_s`, `log_ratio`, `ratio` | derived from `samples` |
| `effects` | experiment × cell × arm × metric | `ratio`, `lo`, `hi`, `err_minus`, `err_plus`, robust interval, `n_blocks`, `delta`, `p`, `p_holm`, `verdict`, kind (screening or confirmatory) | `analyze.py` |
| `effects_by_look` | as `effects`, × cumulative block count | same, plus `n_blocks` as the x value | `analyze.py` |
| `absolutes` | experiment × cell × arm × metric | geometric mean, `lo`, `hi`, distances | `analyze.py` |
| `phases` | sample × side × stage | `stage` (handshake, scan, generate, read, network, write, finalize, unaccounted), `seconds` | `XSYNC_METRICS` |
| `timeline` | host × second (or probe) | timestamp, sample id, `temp_c`, `freq_mhz`, throttle flags, load, `dirty_bytes`, NIC rx/tx rate, wireless signal and bitrate | `probe.py` |
| `links` | block | RTT min/avg/max/mdev, probe throughput, interface, link speed | preflight |
| `noise` | cell × link | `sigma_d`, `n_blocks`, required blocks per δ | E0a |
| `scaling` | E8 point × tool × block | swept variable, file count, file size, total bytes, rates, times | E8 |
| `syscalls` | run × side × tool × syscall | calls, seconds, calls per file | E2b |
| `frames` | run × frame type | count, bytes | E2d |
| `corpus_files` | file in a corpus | corpus, `size_bytes`, depth, content class, suffix class | corpus manifests |
| `corpora` | corpus | files, directories, bytes, zstd-3 ratio, digest | corpus manifests |
| `progress` | diagnostic run × tick | `elapsed_ms`, files, bytes, wire bytes, phase | `--progress=json`, untimed runs only |
| `arms` | experiment × arm | one numeric column per tunable and flag | specs |
| `runs`, `hosts` | run; host | revisions, hashes, tool versions; hardware, kernel, filesystem | manifests |
| `voids` | voided block | cell, reason, gate value | agent |

`phases` always includes an `unaccounted` row so the stages sum to wall time
and a stacked bar is honest about what was not measured.

### 9.3 Collection the figures need beyond the inference plan

- **Scaling curves (E8).** The standard small-file figure — throughput
  against file size and against file count — is not produced by any tuning
  experiment, so it gets its own.
- **Five or more log-spaced levels** for any one-dimensional sweep that
  becomes a figure. Three levels support a verdict and a heatmap cell, not a
  curve; the confirmatory re-run of a chosen factor widens the sweep.
- **Within-sample host series.** `probe.py` samples temperature, CPU
  frequency, dirty bytes and NIC counters once a second during a sample, to
  show thermal and writeback behaviour inside a transfer. E0e checks that
  the sampler itself is *equivalent* to no sampler before it is left on.
- **Progress traces** from a few separate diagnostic runs per cell.
  `--progress=json` perturbs small-file runs (H23), so these never count as
  timing samples.
- **Per-file corpus manifests**, so file-size distributions are drawn from
  the files actually transferred.
- **Estimates at every cumulative block count**, not only at the declared
  looks, so the narrowing of an interval can be drawn. These are
  descriptive; verdicts still come only from the declared looks.
- **The A/A data.** It is the null distribution every effect is read
  against and belongs in the paper.
- **The rsync baseline in every cell that will be plotted as a speedup**,
  including cells of experiments that otherwise compare only `xs` arms.

### 9.4 Figures and the table behind each

| Figure | Shows | Table | Holochart chart |
|---|---|---|---|
| F1 | File-size distribution of each corpus | `corpus_files` | `ecdf`, log x, colour by corpus |
| F2 | Noise floor: A/A paired ratios per cell and link | `pairs` (E0a) | `strip` or `violin`, facet by link |
| F3 | Speedup over rsync, every cell | `effects` (E1) | Forest plot: `scatter` with `errorX`/`errorXMinus`, log x, a line at 1 and a ±δ band |
| F4 | Wall time against time-to-durable | `effects` (E1, both metrics) | Dumbbell |
| F5 | Throughput against file size and file count | `scaling` | `line`, log–log, error bars, colour by tool, dash by link |
| F6 | Where the time goes, per cell and side | `phases` | Stacked `bar`, or waterfall |
| F7 | Worker scaling by receiver filesystem and cache state | `effects` (E3a) | `line` with error bars, faceted |
| F8 | Compression level by link and corpus | `effects` (E3b) | `line` or grouped `bar`, facet row corpus, column link |
| F9 | `block_target` × `small_max` | `effects` (E4a) | `imshow` heatmap, verdict annotated |
| F10 | Drift, and why blocks: wall time over a session with SoC temperature | `samples`, `timeline` | `scatter` over a date axis, second y axis |
| F11 | Wi-Fi: wall time against probed link rate | `samples` joined to `links` | `scatter`, marginal histograms, OLS trendline |
| F12 | An interval narrowing as blocks accumulate | `effects_by_look` | `line` with an error band |
| F13 | Does the LAN tuning hold on Wi-Fi and on the Mac | `effects` (E6, E7) | Forest plot grouped by link |
| F14 | Syscalls per file, `xs` against rsync | `syscalls` | Grouped `bar` |
| F15 | The screened configuration space | `arms` joined to `effects` | `parallelCoordinates`, colour by log ratio |
| F16 | Speed against memory and CPU cost | `effects` (wall, RSS, CPU) | `scatter`, error bars on both axes |
| F17 | Sensitivity to added round-trip time and loss | `effects` (E7b) | `line` with error bars, one line per corpus |
| F18 | One host, three receiver filesystems | `effects` (E2c on freya) | Forest plot grouped by filesystem |

### 9.5 Export and rendering

- A figure is a committed spec that names a table and its columns. No
  number is typed into figure code; a changed dataset redraws every figure.
  Specs live in `paper/figures/` in this repository, beside the exported
  tables in `paper/data/`.
- Each export records the hash of the sample store it was built from, and
  each figure records the export it used.
- Holochart renders through WebGL2 and exports raster images only (PNG,
  JPEG, WebP through `toImage`); there is no SVG or PDF output. Print
  figures are therefore rendered headless at a fixed CSS size and a `scale`
  chosen for the target resolution: a 3.4-inch column at 600 dpi is 2,040
  pixels, for example 510 CSS px at `scale: 4`.
- Holochart's default theme is dark. Print figures use a light template
  (`plotly-classic`, `seaborn` or `high-contrast`).
- The same specs and CSVs can back an interactive companion, where hover
  shows the provenance columns of rule 11.
- Hostnames and the network layout are published as they are.
  `export.py --public` removes only usernames, home-directory paths, and IP
  and MAC addresses.

### 9.6 Presentation

Print figures follow scientific convention; the showcase is separate.

- Print figures are static, two-dimensional and light-themed, and remain
  readable in greyscale: tool and arm are encoded by colour and also by
  symbol or dash.
- One colour per tool and per host across every figure, fixed in the
  vocabulary file.
- Every estimate is drawn with its interval. Every caption states the
  blocks per point, the interval level and δ.
- Ratio axes are logarithmic with a reference line at 1 and the ±δ band.
- Where the number of blocks is small enough to show, raw points are drawn
  over any box or violin.
- No 3D and no animation in print, and a second y axis only in F10.

The showcase is limited to an interactive companion built from the same
specs and tables, where it costs nothing extra to collect:

- Hover shows the provenance of any point (rule 11).
- F1 is drawn from every file of every corpus, about a million points,
  instead of a binned summary.
- F9 is also offered as a rotatable response surface.
- F12 is also offered as an animation over the block count.

In the paper itself these three appear only in their static forms.

## 10. Decisions

Settled on 2026-10-11:

| Question | Decision |
|---|---|
| Privileged helper | Yes, as specified in section 4.8. Cold-cache runs, a fixed governor and `netem` are all available. |
| Reverse SSH keys | Set up in both directions for each pair before the campaign (M0). Client role becomes a measured factor (E1b). |
| freya's destination filesystem | ext4 mounted at `/mnt/nvme`, mounted through the helper if it is not already. ZFS is kept as a warm-only comparison. |
| Baseline revision | A commit on `main`, not a separate clean worktree. Every run is pinned to a commit and the harness refuses a dirty tree. |
| Paper scope | A scientific report first, with a slight showcase of holochart (section 9.6). |
| Public naming | Hostnames may be published. |
| Which holochart | The original, `~/projects/holochart`. |

Still open:

1. **Phase C access**, deferred until phases A and B are done: Remote Login
   on the Mac for neo → Mac transfers, free space for the corpora, and
   whether cold runs with `purge` are wanted there.
2. **mars.** Its hardware, filesystem and whether it is wired into a mesh
   node or has its own wireless interface are unknown until the M1
   inventory. The last decides which wireless statistics can be recorded.
3. **Corpus naming.** This plan assumes the congress corpus, which is public
   govinfo data, may be named and described in the paper.
