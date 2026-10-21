# Z3-1g-compress

On a gigabit link, xs -z delivers text-like data faster than the link, and faster than rsync -z, even from the Pi.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T162239Z-Z3-1g-compress, 20261017T161616Z-Z3-1g-compress.
- Valid blocks: 10. Voided block attempts: 7.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | xs-z | 4 | 0.401 [0.345, 0.467] | 0.401 | 0.1250 | too few blocks |
| `large-text.fresh.freya-neo.sender.warm` | xs-z1 | 4 | 0.429 [0.370, 0.499] | 0.439 | 0.1250 | too few blocks |
| `large-text.fresh.freya-neo.sender.warm` | xs-z3 | 4 | 0.326 [0.259, 0.410] | 0.326 | 0.1250 | too few blocks |
| `large-text.fresh.freya-neo.sender.warm` | rsync | 4 | 1.014 [0.979, 1.051] | 1.014 | 0.3750 | too few blocks |
| `large-text.fresh.freya-neo.sender.warm` | rsync-z | 4 | 0.387 [0.349, 0.429] | 0.387 | 0.1250 | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | xs-z | 6 | 0.433 [0.396, 0.472] | 0.426 [0.391, 0.492] | 0.0312 | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | xs-z1 | 6 | 0.444 [0.403, 0.488] | 0.437 [0.393, 0.511] | 0.0312 | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | xs-z3 | 6 | 2.174 [1.642, 2.879] | 2.231 [1.415, 2.808] | 0.0312 | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | rsync | 6 | 1.000 [0.999, 1.001] | 1.000 [0.999, 1.001] | 0.9688 | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | rsync-z | 6 | 1.520 [1.440, 1.604] | 1.518 [1.421, 1.608] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | xs-z | 1.282 [1.103, 1.490] | 2.529 [2.514, 2.545] | 0.395 [0.339, 0.460] |
| `large-text.fresh.freya-neo.sender.warm` | xs-z1 | 1.247 [1.186, 1.311] | 2.477 [2.467, 2.487] | 0.425 [0.365, 0.495] |
| `large-text.fresh.freya-neo.sender.warm` | xs-z3 | 1.723 [1.547, 1.920] | 3.453 [3.438, 3.467] | 0.318 [0.251, 0.403] |
| `large-text.fresh.freya-neo.sender.warm` | rsync | 0.478 [0.464, 0.493] | 0.114 [0.113, 0.115] | 1.010 [0.977, 1.043] |
| `large-text.fresh.freya-neo.sender.warm` | rsync-z | 1.354 [1.295, 1.416] | 0.112 [0.108, 0.116] | 0.379 [0.343, 0.419] |
| `large-text.fresh.neo-freya.sender.warm` | xs-z | 2.172 [2.057, 2.294] | 0.357 [0.352, 0.362] | 0.432 [0.396, 0.472] |
| `large-text.fresh.neo-freya.sender.warm` | xs-z1 | 2.235 [2.115, 2.362] | 0.387 [0.333, 0.449] | 0.444 [0.403, 0.488] |
| `large-text.fresh.neo-freya.sender.warm` | xs-z3 | 10.620 [8.502, 13.265] | 0.357 [0.354, 0.361] | 2.175 [1.642, 2.880] |
| `large-text.fresh.neo-freya.sender.warm` | rsync | 0.639 [0.594, 0.687] | 0.138 [0.129, 0.147] | 1.000 [0.999, 1.001] |
| `large-text.fresh.neo-freya.sender.warm` | rsync-z | 2.350 [2.263, 2.441] | 0.128 [0.127, 0.129] | 1.520 [1.440, 1.604] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z | xs-z1 | xs-z3 |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | 76.883 | 29.342 | 75.823 | 30.420 | 32.563 | 24.720 |
| `large-text.fresh.neo-freya.sender.warm` | 73.918 | 112.4 | 73.917 | 31.978 | 32.795 | 160.7 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | xs-z | 0.0949 | 83 | 111 |
| `large-text.fresh.freya-neo.sender.warm` | xs-z1 | 0.0940 | 82 | 109 |
| `large-text.fresh.freya-neo.sender.warm` | xs-z3 | 0.1447 | 190 | 254 |
| `large-text.fresh.freya-neo.sender.warm` | rsync | 0.0223 | 8 | 8 |
| `large-text.fresh.freya-neo.sender.warm` | rsync-z | 0.0652 | 41 | 54 |
| `large-text.fresh.neo-freya.sender.warm` | xs-z | 0.0836 | 65 | 87 |
| `large-text.fresh.neo-freya.sender.warm` | xs-z1 | 0.0908 | 76 | 102 |
| `large-text.fresh.neo-freya.sender.warm` | xs-z3 | 0.2676 | 645 | 864 |
| `large-text.fresh.neo-freya.sender.warm` | rsync | 0.0008 | 8 | 8 |
| `large-text.fresh.neo-freya.sender.warm` | rsync-z | 0.0512 | 26 | 34 |

## Voided attempts

- neo does not answer ping
- rsync: harness error: freya: `python3 /mnt/nvme/xsbench/lib/c4b227526aa5/probe.py snapshot --interface enp10s0` exited 255: ssh: Could not resolve hostname frey
