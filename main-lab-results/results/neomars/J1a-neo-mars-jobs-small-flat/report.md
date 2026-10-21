# J1a-neo-mars-jobs-small-flat

-j4 and -j8 differ from each other, and from the default, by more than 5% in time-to-durable on small-file and no-op copies between neo and mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T170928Z-J1a-neo-mars-jobs-small-flat, 20261020T172300Z-J1a-neo-mars-jobs-small-flat, 20261020T174155Z-J1a-neo-mars-jobs-small-flat.
- Valid blocks: 41. Voided block attempts: 4.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j4 | 10 | 0.982 [0.972, 0.992] | 0.982 [0.972, 0.992] | 0.0059 | equivalent |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j8 | 10 | 0.992 [0.981, 1.003] | 0.992 [0.982, 1.004] | 0.1445 | equivalent |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 10 | 0.998 [0.963, 1.034] | 0.998 [0.962, 1.034] | 0.9160 | equivalent |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j4 | 11 | 0.991 [0.971, 1.010] | 0.994 [0.969, 1.009] | 0.3242 | equivalent |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j8 | 11 | 1.008 [0.997, 1.019] | 1.006 [0.997, 1.020] | 0.1416 | equivalent |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 11 | 1.296 [1.265, 1.328] | 1.293 [1.264, 1.329] | 0.0010 | slower |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j4 | 10 | 0.977 [0.891, 1.071] | 0.965 [0.896, 1.064] | 0.5742 | inconclusive |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j8 | 10 | 0.988 [0.954, 1.024] | 0.988 [0.952, 1.027] | 0.4648 | inconclusive |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 10 | 3.047 [2.898, 3.204] | 3.054 [2.878, 3.225] | 0.0020 | slower |
| `small-flat.noop.neo-mars.sender.warm` | xs-j4 | 10 | 0.971 [0.844, 1.117] | 0.992 [0.815, 1.113] | 0.6211 | inconclusive |
| `small-flat.noop.neo-mars.sender.warm` | xs-j8 | 10 | 0.996 [0.844, 1.175] | 1.013 [0.840, 1.168] | 0.9414 | inconclusive |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 10 | 2.539 [2.120, 3.040] | 2.575 [2.163, 3.039] | 0.0020 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j4 | 0.527 [0.487, 0.570] | 0.847 [0.814, 0.881] | 0.984 [0.966, 1.002] |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j8 | 0.579 [0.572, 0.587] | 0.860 [0.831, 0.890] | 0.992 [0.984, 1.000] |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.447 [0.400, 0.499] | 0.068 [0.063, 0.074] | 0.998 [0.961, 1.037] |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j4 | 0.995 [0.977, 1.013] | 1.010 [0.998, 1.021] | 0.988 [0.969, 1.008] |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j8 | 1.027 [1.012, 1.041] | 1.089 [1.075, 1.103] | 1.007 [0.997, 1.018] |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 1.030 [1.002, 1.059] | 0.100 [0.099, 0.101] | 1.299 [1.268, 1.331] |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j4 | 0.436 [0.338, 0.563] | 0.530 [0.493, 0.570] | 0.977 [0.891, 1.071] |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j8 | 0.631 [0.575, 0.693] | 0.658 [0.612, 0.707] | 0.989 [0.954, 1.026] |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 0.541 [0.417, 0.702] | 0.333 [0.310, 0.359] | 3.070 [2.920, 3.228] |
| `small-flat.noop.neo-mars.sender.warm` | xs-j4 | 1.003 [0.779, 1.291] | 1.031 [0.928, 1.145] | 1.005 [0.852, 1.186] |
| `small-flat.noop.neo-mars.sender.warm` | xs-j8 | 1.281 [0.961, 1.708] | 1.426 [1.300, 1.565] | 0.944 [0.825, 1.081] |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 0.870 [0.651, 1.162] | 0.817 [0.717, 0.931] | 2.985 [2.460, 3.621] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-j4 | xs-j8 |
|---|---|---|---|---|
| `small-flat.fresh.mars-neo.receiver.warm` | 5.675 | 5.685 | 5.583 | 5.641 |
| `small-flat.fresh.neo-mars.sender.warm` | 16.432 | 12.676 | 12.556 | 12.775 |
| `small-flat.noop.mars-neo.receiver.warm` | 0.763 | 0.250 | 0.245 | 0.247 |
| `small-flat.noop.neo-mars.sender.warm` | 0.986 | 0.388 | 0.377 | 0.387 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j4 | 0.0145 | 8 | 8 |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-j8 | 0.0155 | 8 | 8 |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.0496 | 25 | 32 |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j4 | 0.0291 | 10 | 13 |
| `small-flat.fresh.neo-mars.sender.warm` | xs-j8 | 0.0162 | 8 | 8 |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 0.0360 | 14 | 18 |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j4 | 0.1287 | 151 | 202 |
| `small-flat.noop.mars-neo.receiver.warm` | xs-j8 | 0.0498 | 25 | 32 |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 0.0701 | 47 | 62 |
| `small-flat.noop.neo-mars.sender.warm` | xs-j4 | 0.1960 | 347 | 464 |
| `small-flat.noop.neo-mars.sender.warm` | xs-j8 | 0.2310 | 481 | 644 |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 0.2520 | 572 | 766 |

## Voided attempts

- stopped
- xs-j8: harness error: mars: `rm -rf -- /Volumes/xsbench/lab/work/20261020T172300Z-J1a-neo-mars-jobs-small-flat/small-flat.fresh.neo-mars.sender.warm/xs-j8` exit
- xs: harness error: mars: `rm -rf -- /Volumes/xsbench/lab/work/20261020T172300Z-J1a-neo-mars-jobs-small-flat/small-flat.fresh.neo-mars.sender.warm/xs` exited 255
