# Benchmark lab

The measurement framework planned in [experiments.md](../../experiments.md).
So far this holds the privileged helper, milestone M1 (host declarations,
endpoint probes and the preflight check), milestone M2 (corpora) and
milestone M3 (building and staging binaries), milestone M4 (plans, the run
agent and the sample record) and milestone M5 (analysis and reports).

| File | Runs on | Purpose |
|---|---|---|
| `hosts.toml` | controller | Hosts, benchmark roots, and the interface each host must use on each link |
| `probe.py` | endpoint | JSON reports: `inventory`, `snapshot`, `route`, `staged`, `sample` for a once-a-second series, and `storage`, a write test |
| `preflight.py` | controller | Runs the probes over SSH, checks them against `hosts.toml`, and writes a record under `benchmarks/results/lab/preflight/` |
| `stage.py` | controller | Builds `xs` from a commit, stages it and the lab scripts on the hosts, and checks what they hold |
| `plan.py` | controller | Expands an experiment spec into a randomized block plan; starts, follows and fetches a run |
| `agent.py` | driver endpoint | Executes a plan detached and writes one record per sample |
| `overnight.py` | driver endpoint | Runs queued plans one after another inside a time window |
| `analyze.py` | controller | Paired ratios, intervals, robust checks and verdicts from the valid blocks; writes the tables |
| `report.py` | controller | Renders an experiment's analysis as Markdown |
| `selftest.py` | anywhere | Checks the analysis on simulated experiments with known ratios |
| `corpus.py` | endpoint | Generates the seeded corpora, and pins any tree by a manifest digest |
| `corpora.json` | — | The pinned digests of the generated and the frozen real corpora |
| `xsbench-helper` | endpoint, as root | The only root operations a run performs |
| `test_lab.py` | anywhere | Unit tests for the parsers, the preflight verdicts and the helper's argument checks |
| `test_helper_container.sh` | a disposable container | Exercises the helper for real |

## Preflight

```sh
python3 benchmarks/lab/preflight.py --link lan
```

It inventories both hosts on the link and probes the path in each direction.
For each direction it makes an SSH connection from one host to the other,
exactly as a transfer would, and checks that the connection reached the
expected host, left by the declared interface, and that the interface is up,
of the declared medium and at the declared speed, with no `netem` qdisc and
a round trip inside the declared limit. It exits nonzero and prints one
`PROBLEM` line per failed check. A run may start only when it prints
`preflight passed`.

## Building and staging

```sh
python3 benchmarks/lab/stage.py build --rev REV
python3 benchmarks/lab/stage.py push --rev REV
python3 benchmarks/lab/stage.py check --rev REV
```

`build` exports the commit with `git archive` and builds its static musl
release for linux/amd64 and linux/arm64 in Docker, using that commit's own
`tools/release.Dockerfile`. The working tree is never built, so a binary
cannot contain uncommitted changes, whatever state the tree is in. The
binaries go to `.bench/lab/builds/<rev12>/` and their hashes to
`benchmarks/results/lab/builds/<rev12>.json`, which is tracked. An existing
build is kept unless `--rebuild` is given, since a rebuild need not be
bit-identical.

`push` copies the binary for each host's architecture to
`ROOT/bin/xs-<rev12>`, checking its SHA-256 on the host before it takes that
name, along with `probe.py`, `corpus.py`, `corpora.json` and `measure.py`.

`check` fails for a host whose `xs-<rev12>` is missing, is not byte-for-byte
the recorded build, reports another revision or a `-dirty` one, or whose
scripts differ from the working copy. It also records each host's rsync
path, version and hash. `preflight.py --rev REV` runs the same check.

## Running an experiment

A spec in `benchmarks/experiments/` names the arms, the cell matrix, the
control arm and a block budget. `E00-smoke.toml` is the harness's own check.

```sh
python3 benchmarks/lab/plan.py make benchmarks/experiments/E00-smoke.toml
python3 benchmarks/lab/plan.py start benchmarks/experiments/E00-smoke.toml
python3 benchmarks/lab/plan.py status RUN_ID
python3 benchmarks/lab/plan.py fetch RUN_ID
python3 benchmarks/lab/plan.py stop RUN_ID
```

`make` prints the plan: every arm once per block in an order drawn from the
seed, cells interleaved round by round, and two spare orders per block for
retries. `start` runs preflight (with `--rev` for each `xs` arm), copies the
plan to the driver host and launches `agent.py` there with `setsid`, so it
keeps running when the controller disconnects. `fetch` copies the records to
`benchmarks/results/lab/EXPERIMENT/RUN_ID/`.

The agent, for each sample: empties or seeds the destination, pre-reads the
source (or drops caches for a cold cell), flushes the destination filesystem
and waits until both hosts are idle, cool and have nothing dirty, then runs
the transfer under `measure.py` on the client host with the peer wrapped by
`measure.py` through `--rsync-path`. Afterwards it times a `sync -f` of the
destination, snapshots both hosts again and verifies the destination against
the corpus manifest. It sets the `performance` governor for the run and
restores it at the end.

A sample is void, with a reason and no timing, if the transfer or the peer
failed, the destination does not verify, a host throttled, or the hosts did
not settle. A void sample ends its block attempt; the block is tried again
in a fresh order up to twice. `samples.jsonl` holds one record per sample,
`blocks.jsonl` one per block attempt with its link probe, and `run.json` the
plan as executed.

Only one run at a time holds the driver's lock. Scenarios are `fresh` and
`noop` so far.

An arm with `inject_fraction = 0.06` sleeps, inside the measured command,
for that share of the time a baseline arm usually takes in the same cell.
The spec's `[baseline]` table names the analysed experiment and arm the
times come from. It exists to give the analysis a known effect to find
(`E0b-known.toml`).

## Running unattended overnight

```sh
python3 benchmarks/lab/plan.py enqueue benchmarks/experiments/E1-baseline.toml
python3 benchmarks/lab/plan.py night --from 2026-10-11T22:00-05:00 --until 2026-10-12T04:00-05:00
python3 benchmarks/lab/plan.py queue
python3 benchmarks/lab/plan.py collect
python3 benchmarks/lab/plan.py stop-queue
```

`enqueue` makes a plan and puts it on the driver's queue without starting
it. `night` checks the hosts once, then starts `overnight.py` on the driver,
detached. Nothing after that needs the controller: it may sleep or be off.

`overnight.py` waits for the window to open, then gives each queued run to
the agent in order. It waits for any experiment still running, never repeats
a run that already has a status, and carries on past a run that fails. The
agent gets the window's end as a deadline and starts no block that might run
past it, so a run cut short still holds whole blocks, spread evenly over its
cells, and a later night's run of the same spec pools with it in the
analysis. It will not start a run with less than five minutes left.

`queue` shows what the queue is doing. `collect` fetches every queued run
and writes each experiment's report. `stop-queue` ends it after the current
sample, with the hosts restored.

## Analysis

```sh
python3 benchmarks/lab/report.py benchmarks/results/lab/EXPERIMENT
python3 benchmarks/lab/selftest.py
```

`report.py` analyses every fetched run of the experiment together, writes
`analysis/{effects,absolutes,pairs,noise}.{json,csv}` and renders
`report.md`. `analyze.py` does the same without the report.

Only valid blocks count, and a block is one observation: for each cell and
arm it gives one log-ratio to the control. The estimate is the mean of
those, exponentiated; the interval is the paired t interval. The robust
check is the Hodges-Lehmann estimate with its distribution-free interval,
and the p-value is an exact sign-flip test (sampled above 20 blocks). A
verdict needs at least eight blocks and both intervals to agree:

| Verdict | The interval of ratios is |
|---|---|
| faster | entirely below 1/(1+δ) |
| slower | entirely above 1+δ |
| equivalent | entirely inside [1/(1+δ), 1+δ] |
| inconclusive | anything else, or the two intervals disagree |

Only the spec's primary metric is judged; durable time, CPU seconds and
peak memory are reported with the same intervals as descriptive. A
confirmatory experiment's p-values are Holm-adjusted across its cells and
arms; a screening experiment's are not and make no claim. `--looks N` widens
every interval to 1 − 0.05/N for an experiment analysed N times.

`--control ARM` compares against another arm than the spec's control and
writes to `analysis-vs-ARM/` and `report-vs-ARM.md`, leaving the declared
analysis untouched.

`selftest.py` takes about a minute and a half. It must pass before a change
to `analyze.py` is trusted.

## Corpora

```sh
python3 corpus.py list
python3 corpus.py generate small-flat --root ROOT/corpora
python3 corpus.py verify ROOT/corpora/small-flat --manifest ROOT/corpora/small-flat.manifest.json
```

`generate` builds `ROOT/NAME/` and writes `ROOT/NAME.manifest.json` (counts,
size quantiles, a sampled zstd ratio and two digests) and
`ROOT/NAME.files.jsonl` (one line per entry) beside it. It writes only into
a directory it created or one carrying its `.xsbench-corpora` marker, and
fails if the result differs from the digest pinned in `corpora.json`.

A generated corpus depends only on its name and tier. Every size, name and
byte is drawn from SHAKE-256 with integer arithmetic, with no floating point
and no `random` module, so the Mac, neo and freya produce identical trees.
File times are fixed (1,700,000,000 plus the file's index) and modes are
0644 and 0755. `--tier smoke` is ten times smaller and `--tier test` five
hundred times.

The digest covers each entry's path, type, mode, size, modification time,
content hash (or symlink target) and hard-link group. `quick_digest` leaves
out content, so `verify --quick` checks a tree without reading it; a full
`verify` re-reads everything. Ownership, extended attributes and ACLs are
not covered.

A real tree is pinned with `manifest`, which treats it the same way:

```sh
python3 corpus.py manifest /path/to/tree --name real-holochart --output ROOT/corpora/real-holochart
```

The three real corpora (`small-real`, `real-holochart`, `real-laikav2`) were
frozen on freya, and freya's copy defines them. A new host gets them from
there with `rsync -aH`, hard links included, and checks them with `verify`.
`corpora.json` records their digests and counts; their file listings stay
on the hosts.

After a change that alters generated output, bump `GENERATOR`, regenerate
and run `python3 corpus.py pin ROOT/corpora`, which records every manifest
it finds there.

## Checking a destination drive

```sh
ssh HOST python3 - storage --path /dir/on/the/drive < benchmarks/lab/probe.py
```

This writes, syncs and deletes a 512 MiB file fourteen times and reports
each round's time. A steady drive gives a slowest round within a few tens
of percent of the fastest. A drive whose write cache runs out gives a
slowest round many times longer, and makes a noisy destination. freya's
scratch drive, a QLC drive that was 86% full and had never been trimmed,
showed a 60-fold swing; reformatted, it shows 1.5-fold. Every other probe
command only reads; this one writes about 7 GB.

A newly formatted ext4 filesystem zeroes its inode tables in the background
for some minutes after it is first mounted, and writes are several times
slower until that finishes. Preflight refuses a host where that is still
running.

## Operator setup (milestone M0)

The harness never edits `sudoers`, `authorized_keys` or anything else owned
by root. These steps are done once by hand on each Linux host. Read
`xsbench-helper` first: the `sudoers` entry lets the benchmark user run it
as root with any arguments, and the script itself is what limits them.

On neo:

```sh
scp benchmarks/lab/xsbench-helper neo.local:/tmp/xsbench-helper
ssh -t neo.local '
  sudo install -o root -g root -m 0755 /tmp/xsbench-helper /usr/local/sbin/xsbench-helper &&
  printf "interface=eth0\n" | sudo install -o root -g root -m 0644 /dev/stdin /etc/xsbench-helper.conf &&
  echo "sanjee ALL=(root) NOPASSWD: /usr/local/sbin/xsbench-helper" |
    sudo install -o root -g root -m 0440 /dev/stdin /etc/sudoers.d/xsbench-helper &&
  sudo visudo -cf /etc/sudoers.d/xsbench-helper &&
  mkdir -p ~/benchmarks/xsyncv4/lab'
```

On freya, whose benchmark root is the ext4 filesystem at `/mnt/nvme`, mounted
from `fstab` (so the weekly `fstrim` covers it):

```sh
scp benchmarks/lab/xsbench-helper freya.local:/tmp/xsbench-helper
ssh -t freya.local '
  sudo install -o root -g root -m 0755 /tmp/xsbench-helper /usr/local/sbin/xsbench-helper &&
  printf "%s\n" interface=enp10s0 scratch=/mnt/nvme scratch_fstype=ext4 |
    sudo install -o root -g root -m 0644 /dev/stdin /etc/xsbench-helper.conf &&
  echo "sanjee ALL=(root) NOPASSWD: /usr/local/sbin/xsbench-helper" |
    sudo install -o root -g root -m 0440 /dev/stdin /etc/sudoers.d/xsbench-helper &&
  sudo visudo -cf /etc/sudoers.d/xsbench-helper &&
  sudo install -d -o sanjee -g sanjee /mnt/nvme/xsbench'
```

A scratch mount with no `fstab` entry can instead be named in the helper's
configuration as `scratch_source=UUID=...`, but then nothing trims it.

SSH from freya to neo, using the key freya already has (done on 2026-10-11):

```sh
ssh freya.local cat .ssh/id_ed25519.pub | ssh neo.local 'cat >> .ssh/authorized_keys'
```

mars gets the same three steps once it has been inventoried and
`hosts.toml` names its interface and root.

After any change to `xsbench-helper`, reinstall it: preflight compares the
installed copy's SHA-256 with the one in this directory.

## What the helper does

`sudo -n /usr/local/sbin/xsbench-helper VERB`:

| Verb | Effect |
|---|---|
| `status` | Prints its state as `key=value` lines. Needs no root. |
| `drop-caches` | `sync`, then drops the page, dentry and inode caches. Does not empty a ZFS ARC. |
| `governor performance` | Saves each cpufreq policy's governor and energy-performance preference, then sets `performance`. |
| `governor restore` | Puts the saved values back. |
| `netem set DELAY_MS LOSS_PCT LIFETIME_S` | Installs a `netem` root qdisc on the configured interface, and a timer that removes it after `LIFETIME_S` (at most 3600). Delay applies to outgoing packets only, so it adds `DELAY_MS` to the round trip. Refuses if the interface already has a qdisc someone configured. |
| `netem clear` | Removes that qdisc and its timer. |
| `mount-scratch` | Mounts the configured scratch mount point if it is not mounted, from `fstab` or else from `scratch_source`, and checks its type. |
| `trim-scratch` | Runs `fstrim` on the scratch filesystem. The agent calls it at the start of every run: freya's QLC scratch drive fell from 3,000 MB/s to 155 MB/s within a day of write-and-delete cycles without it. |

Exit status: 0 done, 1 failed, 2 usage, 3 not configured or not supported
on this host, 4 refused. Each change is logged to syslog with the calling
user.

## Tests

```sh
python3 benchmarks/lab/test_lab.py
```

The container test changes a qdisc, mounts a loop device and drops caches,
so it runs only inside a disposable privileged container:

```sh
docker run --rm --privileged -v "$PWD/benchmarks/lab:/lab:ro" xsync-p0-rig:latest \
  sh /lab/test_helper_container.sh
```

That container has no systemd and no cpufreq, so two paths are not covered
by it: the `systemd-run` timer that clears `netem`, and setting and
restoring a real governor. Both were checked on neo and freya on 2026-10-11;
repeat them on any new host after installing:

```sh
ssh neo.local 'sudo -n /usr/local/sbin/xsbench-helper netem set 5 0 5; sleep 8; sudo -n /usr/local/sbin/xsbench-helper status'
```

```sh
ssh neo.local 'sudo -n /usr/local/sbin/xsbench-helper governor performance; sudo -n /usr/local/sbin/xsbench-helper governor restore; sudo -n /usr/local/sbin/xsbench-helper status'
```

The first must end with `netem=off` and `netem_timer=off`; the second with
the original governor and `governor_saved=no`.
