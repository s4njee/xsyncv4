# N1b-10g-small-write

At 10 Gb/s xs writes small and mixed trees onto NVMe faster than rsync, durably.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T113049Z-N1b-10g-small-write, 20261016T113316Z-N1b-10g-small-write.
- Valid blocks: 53. Voided block attempts: 2.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 4 | 0.337 [0.261, 0.434] | 0.337 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 5 | 0.633 [0.375, 1.067] | 0.731 | 0.0625 | too few blocks |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 5 | 0.435 [0.371, 0.511] | 0.414 | 0.0625 | too few blocks |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 4 | 0.960 [0.755, 1.221] | 0.960 | 0.6250 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 4 | 0.545 [0.281, 1.055] | 0.545 | 0.1250 | too few blocks |
| `small-deep.noop.mac-mars.sender.warm` | xs | 6 | 0.541 [0.516, 0.567] | 0.538 [0.518, 0.583] | 0.0312 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 4 | 0.685 [0.234, 2.005] | 0.945 | 0.1250 | too few blocks |
| `small-flat.noop.mac-mars.sender.warm` | xs | 4 | 0.305 [0.206, 0.452] | 0.305 | 0.1250 | too few blocks |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 5 | 0.955 [0.888, 1.026] | 0.960 | 0.1250 | too few blocks |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 4 | 0.319 [0.268, 0.379] | 0.319 | 0.1250 | too few blocks |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 4 | 1.047 [1.008, 1.087] | 1.054 | 0.1250 | too few blocks |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 4 | 0.890 [0.759, 1.044] | 0.887 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 0.821 [0.704, 0.958] | 12.259 [11.554, 13.007] | 0.335 [0.259, 0.434] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 1.489 [1.342, 1.651] | 1.110 [1.094, 1.127] | 0.630 [0.372, 1.065] |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 0.639 [0.608, 0.670] | 9.020 [8.568, 9.496] | 0.432 [0.368, 0.508] |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 1.695 [1.430, 2.010] | 1.070 [1.058, 1.082] | 0.958 [0.750, 1.223] |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 2.314 [1.840, 2.909] | 3.992 [3.725, 4.280] | 0.540 [0.278, 1.050] |
| `small-deep.noop.mac-mars.sender.warm` | xs | 4.571 [4.420, 4.728] | 4.156 [3.998, 4.321] | 0.541 [0.515, 0.567] |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 1.671 [1.205, 2.316] | 10.346 [9.032, 11.850] | 0.685 [0.234, 2.010] |
| `small-flat.noop.mac-mars.sender.warm` | xs | 0.893 [0.828, 0.962] | 1.405 [1.375, 1.437] | 0.301 [0.203, 0.446] |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 1.759 [1.392, 2.222] | 9.934 [8.514, 11.590] | 0.953 [0.891, 1.020] |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 0.895 [0.825, 0.971] | 1.376 [1.353, 1.399] | 0.314 [0.266, 0.371] |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 1.246 [1.097, 1.414] | 1.060 [1.044, 1.077] | 1.048 [1.006, 1.091] |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 1.158 [1.027, 1.307] | 1.062 [1.052, 1.071] | 0.885 [0.750, 1.046] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 4.820 | 1.624 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.354 | 0.224 |
| `mixed-threshold.fresh.mac-mars.sender.warm` | 3.882 | 1.690 |
| `mixed-threshold.noop.mac-mars.sender.warm` | 0.213 | 0.204 |
| `small-deep.fresh.mac-mars.sender.warm` | 11.888 | 6.476 |
| `small-deep.noop.mac-mars.sender.warm` | 4.203 | 2.275 |
| `small-flat.fresh.mac-mars.sender.warm` | 5.229 | 3.583 |
| `small-flat.noop.mac-mars.sender.warm` | 0.868 | 0.265 |
| `small-opaque.fresh.mac-mars.sender.warm` | 3.967 | 3.787 |
| `small-opaque.noop.mac-mars.sender.warm` | 0.832 | 0.265 |
| `tiny-one.fresh.mac-mars.sender.warm` | 0.202 | 0.212 |
| `tiny-one.noop.mac-mars.sender.warm` | 0.237 | 0.211 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 0.1591 | 230 | 307 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 0.4211 | 1594 | 2135 |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 0.1297 | 153 | 205 |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 0.1510 | 207 | 277 |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 0.4156 | 1552 | 2080 |
| `small-deep.noop.mac-mars.sender.warm` | xs | 0.0450 | 21 | 27 |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 0.6749 | 4089 | 5480 |
| `small-flat.noop.mac-mars.sender.warm` | xs | 0.2460 | 545 | 730 |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 0.0583 | 33 | 43 |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 0.1086 | 108 | 144 |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 0.0237 | 8 | 9 |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 0.1004 | 93 | 124 |

## Voided attempts

- stopped
