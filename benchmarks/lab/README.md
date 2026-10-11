# Benchmark lab

The measurement framework planned in [experiments.md](../../experiments.md).
So far this holds the privileged helper, milestone M1 (host declarations,
endpoint probes and the preflight check) and milestone M2 (corpora).

| File | Runs on | Purpose |
|---|---|---|
| `hosts.toml` | controller | Hosts, benchmark roots, and the interface each host must use on each link |
| `probe.py` | endpoint | Read-only JSON reports: `inventory`, `snapshot`, `route`, and `sample` for a once-a-second series |
| `preflight.py` | controller | Runs the probes over SSH, checks them against `hosts.toml`, and writes a record under `benchmarks/results/lab/preflight/` |
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

On freya, whose benchmark root is the ext4 filesystem at `/mnt/nvme`. That
mount has no `fstab` entry, so its UUID goes in the configuration:

```sh
scp benchmarks/lab/xsbench-helper freya.local:/tmp/xsbench-helper
ssh -t freya.local '
  sudo install -o root -g root -m 0755 /tmp/xsbench-helper /usr/local/sbin/xsbench-helper &&
  printf "%s\n" interface=enp10s0 scratch=/mnt/nvme scratch_fstype=ext4 \
    scratch_source=UUID=82f82f32-5131-4711-a23e-31a19c468950 |
    sudo install -o root -g root -m 0644 /dev/stdin /etc/xsbench-helper.conf &&
  echo "sanjee ALL=(root) NOPASSWD: /usr/local/sbin/xsbench-helper" |
    sudo install -o root -g root -m 0440 /dev/stdin /etc/sudoers.d/xsbench-helper &&
  sudo visudo -cf /etc/sudoers.d/xsbench-helper &&
  sudo install -d -o sanjee -g sanjee /mnt/nvme/xsbench'
```

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
