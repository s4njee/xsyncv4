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

| Host | Hardware (to be re-inventoried) | Role |
|---|---|---|
| `neo.local` | Raspberry Pi 5, 4 cores, 4 GiB, ext4 on NVMe | One end of every pair |
| `freya.local` | Ryzen 9 7950X, 32 threads, 64 GiB; benchmark root on ext4 at `/mnt`; ZFS home; runs other services | Phase A peer |
| `mars.local` | amd64 Linux; old docs say Ryzen 9 7900X, ext4 on NVMe, dual-boots Windows | Phase B peer |
| this Mac | M1 Max, 10 cores, 64 GiB, APFS (98–99% full in past runs), USB gigabit adapter | Phase C peer; controller for A and B |

| Phase | Pair | Link | Purpose |
|---|---|---|---|
| A | neo ↔ freya | wired LAN, 1 Gb/s | Build and calibrate the framework; main tuning |
| B | neo ↔ mars | mesh Wi-Fi | Re-test link-sensitive factors; check the LAN tuning holds |
| C | neo ↔ Mac | wired LAN | macOS/APFS endpoint; final confirmation |

Known constraints:

- These hostnames did not resolve from the session that wrote this plan, so
  the table above comes from `backlog.md` and the old docs. Milestone M1
  replaces it with a recorded inventory.
- The old topology notes put freya behind the mesh hop and mars on the
  switch, the reverse of the layout above. The path proof must confirm the
  current wiring rather than trust either description.
- Today neo can authenticate to freya but not the reverse, so every recorded
  v4 run has neo as the SSH client and direction is confounded with client
  role. SSH keys are set up in both directions for each pair before the
  campaign (M0), and E1b measures whether client role matters.
- freya's benchmark root is an ext4 filesystem mounted at `/mnt`. Preflight
  checks the mount and its type, and mounts it through the helper if it is
  absent. The device behind it is recorded in the inventory. The ZFS home
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
| `stage.py` | controller | Builds via `tools/release.py`, stages `xs-<rev12>` by hash, verifies SHA-256 remotely |
| `preflight.py` | controller + agent | Inventory, path proof, link probe, tool versions |
| `plan.py` | controller | Spec + seed → block plan (JSON) |
| `agent.py` | client endpoint | Executes a plan with no controller in the timed path; appends JSONL after every sample |
| `probe.py` | both endpoints | Host-state snapshot before and after each sample |
| `analyze.py` | controller | Estimates, intervals, tests, verdicts |
| `report.py` | controller | Markdown report per experiment |
| `export.py` | controller | Tidy tables for figures (section 9) |
| `selftest.py` | controller | Statistics tested on synthetic data with known effects |

The agent and probes use only the Python standard library, as the existing
harness does, so they run unchanged on neo. The analysis is also standard
library only; the estimators in section 5 need nothing more.

The controller ships a plan to the client endpoint and collects results
afterwards. The agent runs detached, so a sleeping laptop or a Wi-Fi drop on
the controller cannot perturb or abort a block.

### 4.3 Sample lifecycle

Before a run:

1. Refuse a dirty tree or a non-release build. Record the revision and the
   binary hash on both ends, and the rsync and OpenSSH versions.
2. Check each corpus against its pinned manifest digest and file count.
3. Path proof: resolve the peer name fresh, record `ip route get <peer>`
   (interface, source address), link speed and MTU, and the peer's
   `$SSH_CONNECTION`. Fail if the interface is not the one `hosts.toml`
   declares for the link.

The run also sets the `performance` governor through the helper, checks
that freya's root is ext4 at `/mnt`, and refuses to start if the helper
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
13. Verify with `rsync -anci --delete`, untimed. Screening specs may verify
    by checksum on the first and last block and by size, time and mode
    otherwise; the record says which.
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
| `small-flat` | 100,000 files, log-normal sizes (median 1 KiB), 100 directories, text-like | Pure per-file cost |
| `small-deep` | Same files and bytes, one file per directory, depth 6 | Per-directory cost (H2, H17) |
| `small-real` | congress-100k: 109,615 files, 25,851 directories, real JSON/XML | Realistic compressible small files |
| `small-opaque` | `small-flat` shape, random bytes, half with skip-list suffixes (`.jpg`, `.gz`) | Compression skip paths (H14) |
| `mixed-bimodal` | ~20,000 files, ~1.5 GB: 83% of files under 8 KiB, about two thirds of bytes in files over 8 MiB | The old `cb7` shape, scaled to fit a block |
| `mixed-threshold` | Sizes log-uniform from 1 KiB to 8 MiB | Behaviour around `SMALL_MAX` and `BLOCK_TARGET` (H22) |
| `mixed-modules` | Regenerated from the size and depth histogram of a real `node_modules` tree | A shape neither project measured |

Sizes target 3–20 s per sample on the LAN: long enough that the ~170 ms
fixed cost and the 25 ms teardown quantum are not the result, short enough
for a dozen blocks per cell. Each corpus also has a 10× smaller smoke tier
for harness tests. `mixed-modules` is regenerated from a histogram rather
than copied so that every host can build the identical tree.

Scenarios: `fresh` (empty destination), `noop` (identical destination) and
`update-1pct` (1% of files replaced). `fresh` and `noop` are primary.

### 4.6 Cache states

- `warm`: the source is pre-read before each sample. The default.
- `cold`: the helper's `drop-caches` runs on both ends before each sample.
  Available on ext4 (neo, freya's `/mnt`, and mars once inventoried). ZFS
  cells stay warm-only. `purge` on the Mac is deferred with the rest of
  phase C access (section 10).
- `/dev/shm` is tmpfs and needs no privilege, so a tmpfs destination control
  is available on every Linux host for corpora that fit in half of RAM.

### 4.7 Engine changes the experiments need

None of the engine's tuning constants can be changed at run time, and `-j`
always applies to both ends. Two additions, both behind a build option that
release binaries do not enable:

1. **`XSYNC_TUNE`**, a `key=value` list read at start-up when built with
   `-DXSYNC_TUNABLES=ON`. Keys, with today's values:

   | Key | Default | Defined at |
   |---|---|---|
   | `block_target` | 1 MiB | `src/remote.cpp:57` |
   | `small_max` | 512 KiB | `src/remote.cpp:58` |
   | `send_queue` | 48 MiB | `src/remote.cpp:254` |
   | `recv_queue` | 16 MiB | `src/remote.cpp:2601` |
   | `listing_window` | 65,536 entries | `src/remote.cpp:1680` |
   | `read_batch_files` / `_bytes` | 64 / 8 MiB | `src/remote.cpp:1285` |
   | `q1_soft_send` / `_recv` | 64 / 16 | `src/remote.cpp:1675,2603` |
   | `write_chunk` | 64 KiB | `src/remote.cpp:359` |
   | `coalesce_under` / `_to` | 32 KiB / 256 KiB | `src/remote.cpp:414-416` |
   | `pipe_size` | unset | new (`F_SETPIPE_SZ`) |
   | `jobs`, `scan_workers` | auto, n/2 | `src/local.cpp:32-59` |
   | `zstd_fast_at` / `_slow_at` | 64 / 8 MiB/s | `src/compression.cpp:79-84` |
   | `wait_peer_poll_ms` | 25 | `src/remote.cpp:314` |
   | `block_hash` | on | diagnostic only |

   The environment does not cross SSH, so `measure.py` gains an `--env K=V`
   option and the harness sets each end through its wrapper. That also
   allows a different `jobs` on each end.

2. **`XSYNC_METRICS=path`**, one JSON line at exit: the existing
   `read_ns`/`network_ns`/`write_ns` counters for both ends, plus new timers
   for handshake, scan, generate and `finalize_tree`. Today those counters
   run only under `-vv`, which also turns on per-file output frames and so
   perturbs exactly the workloads being measured.

A tunables build is used for an experiment only after E0c shows it is
equivalent to the release build at default values.

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
| `mount-scratch` | Mounts the `fstab` entry for `/mnt` if it is not mounted | freya's benchmark root |
| `status` | Prints governor, qdisc and mount state | Preflight and exit checks |

The network interface and the mount point are fixed in a root-owned
configuration file beside the script; a caller cannot name another.
`mount-scratch` mounts only what `fstab` already defines for `/mnt` and
never chooses or formats a device. `netem set` arms a timer that clears the
qdisc after the stated lifetime, so a crashed run cannot leave a host's
network degraded.

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

`n ≈ ((1.96 + 0.84) · σ_d / ln(1+δ))² + 2` for 80% power at 95% confidence,
with a floor of 8.

| σ_d | δ = 2% | 3% | 5% | 10% | 20% |
|---|---:|---:|---:|---:|---:|
| 0.02 | 10 | 8 | 8 | 8 | 8 |
| 0.05 | 52 | 25 | 11 | 8 | 8 |
| 0.10 | 202 | 92 | 35 | 11 | 8 |
| 0.20 | 802 | 361 | 134 | 37 | 12 |

v4's existing n=3 runs show a typical spread of 1–10% with outliers of
30–148%, so σ_d on the LAN is probably 0.03–0.08 and unknown on Wi-Fi. The
table is why the Wi-Fi phase uses a larger δ and tests fewer factors.
Showing *equivalence* needs more blocks than showing a difference of the
same size.

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
- **Known effect**: an arm that sleeps for 3% of the control's median before
  exec must come out *slower* at the planned block count.
- **Synthetic**: `selftest.py` checks interval coverage and verdict rates on
  generated data with known ratios, including heavy-tailed noise.

## 6. Experiment catalogue

**E0 — calibration.** (a) A/A noise floor per cell, 20 blocks. (b) Injected
3% slowdown. (c) Tunables build vs release build at defaults, expecting
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
share of receive time. On freya it compares tmpfs, ext4 at `/mnt` and ZFS
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

**Phase A — neo ↔ freya, wired.** Everything: E0, E1, E1b, E2, E3, E4, E5,
E6, then E7b and E8. freya's cells use the ext4 root at `/mnt` unless the
experiment names ZFS.
Rough cost at ~30 s per sample cycle (transfer, settle, verify): a 4-arm,
12-block cell is about 25 minutes, so E1 is roughly a day of unattended
running and each E3/E4 screen is one to three hours.

**Phase B — neo ↔ mars, mesh Wi-Fi.** Noise is higher and the link is the
likely bottleneck, so:

- Re-run E0 first; nothing from phase A's noise floor carries over.
- Shorter blocks (smoke-tier corpora where needed), more of them, and δ set
  from the measured σ_d.
- Wireless statistics, retransmits and the per-block link probe are
  recorded; a block whose probe falls outside a declared band is void.
- Run E1, then only the link-sensitive experiments: E3a (brief), E3b, E3e,
  E4b, E4f. Then E6 for the phase A configuration, E7 and E8.

**Phase C — neo ↔ Mac, wired.** E0, E1, E3a (the APFS worker cap), E6, E7,
E8.
Mac-specific handling: destination under a `.noindex` directory so Spotlight
stays out, load gate, free-space check, and `purge` for cold runs.

## 8. Build order

| Milestone | Deliverable | Done when |
|---|---|---|
| M0 | Operator setup: baseline revision committed on `main`; helper reviewed and installed with its `sudoers` entry on neo, freya and mars; SSH keys in both directions for each pair; ext4 at `/mnt` on freya | From each host, `xsbench-helper status` answers under `sudo -n` and a non-interactive SSH to its peer succeeds; `/mnt` on freya reports ext4 |
| M1 | `hosts.toml`, `preflight.py`, `probe.py` | Inventory and path proof recorded for all three Linux hosts; a deliberately wrong interface fails the proof |
| M2 | `corpus.py` and manifests | Same seed gives the same digest on neo, freya and the Mac |
| M3 | `stage.py` | A stale or dirty binary on either end is refused |
| M4 | `plan.py`, `agent.py`, record schema | A smoke experiment runs detached on neo and survives the controller disconnecting |
| M5 | `analyze.py`, `report.py`, `selftest.py` | Synthetic selftests pass; coverage of the 95% interval is 93–97% |
| M6 | E0a, E0b on phase A | A/A is *equivalent*; the injected 3% is detected; σ_d table published |
| M7 | `XSYNC_TUNE`, `XSYNC_METRICS`, `measure.py --env` | Existing tests pass; E0c is *equivalent* |
| M8 | `export.py`, table schemas, one figure spec | F2 and F3 render in holochart from E0a and smoke E1 data with no hand-edited numbers |
| M9 | E1 onward | — |

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
| freya's destination filesystem | ext4 mounted at `/mnt`, mounted through the helper if it is not already. ZFS is kept as a warm-only comparison. |
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
