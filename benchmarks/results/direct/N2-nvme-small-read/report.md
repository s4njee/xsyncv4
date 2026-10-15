# N2-nvme-small-read

xs -a reads small and mixed trees off a cold NVMe drive faster than rsync -a.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T034426Z-N2-nvme-small-read.
- Valid blocks: 27. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 3 | 0.489 [0.186, 1.288] | 0.474 | 0.2500 | too few blocks |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 2 | 0.329 [0.001, 138.072] | 0.329 | 0.5000 | too few blocks |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 2 | 0.440 [0.000, 16091.148] | 0.440 | 1.0000 | too few blocks |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 2 | 0.951 [0.245, 3.687] | 0.951 | 1.0000 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 2 | 1.434 [0.491, 4.186] | 1.434 | 0.5000 | too few blocks |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 2 | 1.501 [0.364, 6.181] | 1.501 | 0.5000 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 2 | 0.716 [0.005, 105.175] | 0.716 | 1.0000 | too few blocks |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 3 | 0.231 [0.147, 0.363] | 0.225 | 0.2500 | too few blocks |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 3 | 1.342 [0.328, 5.485] | 1.257 | 0.7500 | too few blocks |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 2 | 0.258 [0.018, 3.759] | 0.258 | 0.5000 | too few blocks |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 2 | 1.001 [0.081, 12.318] | 1.001 | 1.0000 | too few blocks |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 2 | 0.967 [0.606, 1.545] | 0.967 | 1.0000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 0.707 [0.612, 0.817] | 0.816 [0.668, 0.998] | 0.451 [0.237, 0.859] |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 1.275 [0.093, 17.561] | 1.162 [0.895, 1.509] | 0.261 [0.000, 176.243] |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 0.542 [0.072, 4.065] | 0.748 [0.528, 1.060] | 0.436 [0.000, 17806.449] |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 1.520 [0.986, 2.345] | 0.993 [0.888, 1.110] | 0.884 [0.230, 3.391] |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 1.970 [1.187, 3.270] | 0.880 [0.740, 1.046] | 1.455 [0.444, 4.766] |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 7.162 [5.388, 9.519] | 4.791 [2.671, 8.591] | 1.506 [0.370, 6.136] |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 0.850 [0.123, 5.878] | 0.798 [0.392, 1.622] | 0.706 [0.005, 95.565] |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 0.869 [0.702, 1.076] | 1.684 [1.617, 1.754] | 0.213 [0.156, 0.292] |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 0.945 [0.870, 1.027] | 0.400 [0.035, 4.558] | 1.345 [0.328, 5.507] |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.912 [0.312, 2.668] | 1.671 [0.881, 3.171] | 0.238 [0.021, 2.769] |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 1.078 [0.640, 1.817] | 0.997 [0.970, 1.026] | 1.084 [0.312, 3.767] |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 1.055 [0.958, 1.163] | 1.009 [0.961, 1.060] | 0.996 [0.577, 1.720] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | 23.982 | 11.729 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | 1.564 | 0.514 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | 17.647 | 7.758 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | 0.385 | 0.367 |
| `small-deep.fresh.mars-mac.receiver.cold` | 65.427 | 93.797 |
| `small-deep.noop.mars-mac.receiver.cold` | 9.574 | 14.367 |
| `small-flat.fresh.mars-mac.receiver.cold` | 45.403 | 32.520 |
| `small-flat.noop.mars-mac.receiver.cold` | 3.142 | 0.727 |
| `small-opaque.fresh.mars-mac.receiver.cold` | 61.233 | 82.175 |
| `small-opaque.noop.mars-mac.receiver.cold` | 2.689 | 0.695 |
| `tiny-one.fresh.mars-mac.receiver.cold` | 0.335 | 0.336 |
| `tiny-one.noop.mars-mac.receiver.cold` | 0.344 | 0.333 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 0.3897 | 1365 | 1829 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 0.6723 | 4059 | 5439 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 1.1695 | 12276 | 16452 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 0.1508 | 207 | 276 |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 0.1193 | 130 | 174 |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 0.1576 | 225 | 301 |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 0.5553 | 2770 | 3711 |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 0.1812 | 297 | 398 |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 0.5667 | 2885 | 3865 |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.2980 | 799 | 1071 |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 0.2794 | 703 | 941 |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 0.0521 | 27 | 35 |

## Voided attempts

- stopped
