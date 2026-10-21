# E1n-neo-mars-baseline

xs -a differs from rsync -a by more than 3% in time-to-durable, both ways between neo and mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261020T055457Z-E1n-neo-mars-baseline.
- Valid blocks: 48. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 4 | 1.001 [0.994, 1.009] | 1.002 | 0.6250 | too few blocks |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 4 | 0.996 [0.985, 1.008] | 0.994 | 0.3750 | too few blocks |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 4 | 0.579 [0.556, 0.602] | 0.583 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 4 | 0.676 [0.630, 0.725] | 0.664 | 0.1250 | too few blocks |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 4 | 0.824 [0.789, 0.861] | 0.821 | 0.1250 | too few blocks |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 4 | 0.892 [0.771, 1.032] | 0.892 | 0.1250 | too few blocks |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 4 | 0.120 [0.113, 0.126] | 0.121 | 0.1250 | too few blocks |
| `small-deep.noop.neo-mars.sender.warm` | xs | 4 | 1.047 [1.010, 1.086] | 1.047 | 0.1250 | too few blocks |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 4 | 1.033 [0.933, 1.143] | 1.033 | 0.5000 | too few blocks |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 4 | 0.737 [0.730, 0.745] | 0.738 | 0.1250 | too few blocks |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 4 | 0.306 [0.294, 0.319] | 0.309 | 0.1250 | too few blocks |
| `small-flat.noop.neo-mars.sender.warm` | xs | 4 | 0.312 [0.265, 0.368] | 0.310 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 1.397 [1.347, 1.448] | 24.744 [22.908, 26.728] | 0.997 [0.990, 1.003] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 1.371 [1.323, 1.420] | 7.565 [7.255, 7.888] | 0.996 [0.987, 1.005] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 1.802 [1.714, 1.895] | 2.146 [2.117, 2.175] | 0.573 [0.551, 0.595] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 1.157 [1.000, 1.338] | 1.000 [0.999, 1.001] | 0.626 [0.566, 0.693] |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 1.595 [1.499, 1.696] | 1.043 [1.028, 1.057] | 0.818 [0.781, 0.857] |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 1.020 [0.879, 1.184] | 4.916 [4.327, 5.585] | 0.892 [0.774, 1.028] |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 1.801 [1.704, 1.904] | 0.740 [0.730, 0.750] | 0.119 [0.113, 0.126] |
| `small-deep.noop.neo-mars.sender.warm` | xs | 3.668 [3.542, 3.798] | 5.239 [4.030, 6.810] | 1.048 [1.010, 1.087] |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 2.961 [2.887, 3.036] | 14.148 [12.184, 16.430] | 1.032 [0.926, 1.151] |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.915 [0.896, 0.934] | 9.618 [8.887, 10.409] | 0.735 [0.727, 0.743] |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 1.516 [1.404, 1.637] | 3.111 [3.024, 3.200] | 0.304 [0.293, 0.316] |
| `small-flat.noop.neo-mars.sender.warm` | xs | 0.990 [0.601, 1.630] | 1.295 [0.972, 1.725] | 0.280 [0.223, 0.353] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | 12.682 | 12.699 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | 12.405 | 12.358 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | 0.304 | 0.176 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | 0.335 | 0.227 |
| `small-deep.fresh.mars-neo.receiver.warm` | 17.450 | 14.386 |
| `small-deep.fresh.neo-mars.sender.warm` | 28.251 | 25.202 |
| `small-deep.noop.mars-neo.receiver.warm` | 16.977 | 2.030 |
| `small-deep.noop.neo-mars.sender.warm` | 3.417 | 3.579 |
| `small-flat.fresh.mars-neo.receiver.warm` | 5.545 | 5.725 |
| `small-flat.fresh.neo-mars.sender.warm` | 16.863 | 12.436 |
| `small-flat.noop.mars-neo.receiver.warm` | 0.767 | 0.235 |
| `small-flat.noop.neo-mars.sender.warm` | 1.141 | 0.357 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 0.0047 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 0.0071 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 0.0251 | 8 | 10 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 0.0441 | 20 | 26 |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 0.0272 | 9 | 11 |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 0.0918 | 78 | 104 |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 0.0331 | 12 | 16 |
| `small-deep.noop.neo-mars.sender.warm` | xs | 0.0227 | 8 | 9 |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 0.0637 | 39 | 51 |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.0065 | 8 | 8 |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 0.0254 | 8 | 10 |
| `small-flat.noop.neo-mars.sender.warm` | xs | 0.1025 | 97 | 129 |
