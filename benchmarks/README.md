# Performance evidence

P3 benchmarks run directly between neo (Raspberry Pi 5, ext4) and freya
(x86_64, ZFS). Results and metadata belong in `results/`; source corpora and
transfer destinations stay in benchmark-owned remote directories. The current
static `xs` releases are staged there with explicit paths.

`run.py` alternates xs and rsync order, records wall time, CPU and peak RSS
for the client and remote helper, and checks every result with a checksum
rsync dry run. Setup, deletion of owned destinations and verification are not
timed. A nonzero transfer or nonempty verification output fails the run.
The JSON file is updated after every verified sample and marked complete only
after every requested scenario finishes.

`bench/bench.py --target host:absolute-root` invokes this SSH runner. Pass
`--corpus`, `--work`, `--remote-xs`, `--remote-measure` and `--output`;
`--direction=push` or `pull` controls data flow. The two hosts use the same
absolute corpus path for these paired runs. Neo can authenticate to freya,
so both data directions can be measured without changing SSH authorization.

The default cache policy retains existing OS caches; it does not imply that
a corpus larger than RAM is entirely resident. A `cold` run requires explicit
reset commands on both endpoints. A cache-reset command is not proof of a cold ZFS workload: ARC residency
and storage reads must be verified independently. The Linux ARC shrinker
respects an ARC minimum when reclaiming clean buffers; see the
[OpenZFS implementation](https://github.com/openzfs/zfs/blob/zfs-2.4.3/module/os/linux/zfs/arc_os.c).

The initial Congress-slice/APFS table in the main README is historical. New
measurements identify source revisions, architectures, filesystems, corpus
sizes, tool versions and verification outcomes. They must not be merged with
old results without those labels.
