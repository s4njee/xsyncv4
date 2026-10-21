# D1-mac-sender-knobs

Larger read batches, more scanning workers or larger coalesced frames on the Mac make xs deliver small trees to mars faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T005544Z-D1-mac-sender-knobs.
- Valid blocks: 8. Voided block attempts: 48.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | batch256 | 3 | 1.006 [0.737, 1.373] | 1.017 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | scan-all | 3 | 0.979 [0.760, 1.263] | 0.989 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | coalesce1m | 3 | 1.011 [0.340, 3.008] | 1.049 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | soft256 | 3 | 0.946 [0.326, 2.746] | 0.965 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | all-three | 3 | 1.001 [0.868, 1.155] | 1.002 | 1.0000 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | batch256 | 3 | 1.145 [0.563, 2.327] | 1.142 | 0.7500 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | scan-all | 3 | 1.025 [0.670, 1.568] | 1.025 | 0.7500 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | coalesce1m | 3 | 1.066 [0.841, 1.352] | 1.066 | 0.5000 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | soft256 | 3 | 1.383 [0.510, 3.748] | 1.359 | 0.5000 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | all-three | 3 | 0.955 [0.880, 1.036] | 0.951 | 0.2500 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | batch256 | 2 | 1.322 [0.473, 3.691] | 1.322 | 0.5000 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | scan-all | 2 | 1.019 [0.241, 4.303] | 1.019 | 1.0000 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | coalesce1m | 2 | 1.147 [0.697, 1.886] | 1.147 | 0.5000 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | soft256 | 2 | 1.144 [0.056, 23.345] | 1.144 | 1.0000 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | all-three | 2 | 1.200 [0.054, 26.478] | 1.200 | 1.0000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | batch256 | 0.997 [0.973, 1.022] | 0.860 [0.719, 1.027] | 1.003 [0.742, 1.356] |
| `real-congress.fresh.mac-mars.sender.warm` | scan-all | 0.993 [0.948, 1.040] | 0.796 [0.529, 1.198] | 0.977 [0.763, 1.252] |
| `real-congress.fresh.mac-mars.sender.warm` | coalesce1m | 1.006 [0.932, 1.086] | 0.730 [0.463, 1.149] | 0.989 [0.351, 2.783] |
| `real-congress.fresh.mac-mars.sender.warm` | soft256 | 1.011 [0.931, 1.097] | 0.733 [0.645, 0.834] | 0.941 [0.323, 2.739] |
| `real-congress.fresh.mac-mars.sender.warm` | all-three | 0.993 [0.975, 1.011] | 0.973 [0.933, 1.015] | 0.997 [0.867, 1.147] |
| `small-deep.fresh.mac-mars.sender.warm` | batch256 | 0.962 [0.928, 0.998] | 1.221 [0.695, 2.145] | 1.145 [0.560, 2.340] |
| `small-deep.fresh.mac-mars.sender.warm` | scan-all | 0.985 [0.967, 1.003] | 1.186 [0.554, 2.540] | 1.024 [0.671, 1.562] |
| `small-deep.fresh.mac-mars.sender.warm` | coalesce1m | 0.988 [0.915, 1.067] | 1.198 [0.725, 1.979] | 1.070 [0.848, 1.350] |
| `small-deep.fresh.mac-mars.sender.warm` | soft256 | 1.014 [0.997, 1.032] | 1.566 [0.799, 3.070] | 1.385 [0.511, 3.756] |
| `small-deep.fresh.mac-mars.sender.warm` | all-three | 0.969 [0.922, 1.019] | 1.238 [0.696, 2.202] | 0.953 [0.882, 1.031] |
| `small-flat.fresh.mac-mars.sender.warm` | batch256 | 1.002 [0.774, 1.296] | 1.498 [0.034, 66.016] | 1.325 [0.482, 3.641] |
| `small-flat.fresh.mac-mars.sender.warm` | scan-all | 0.991 [0.664, 1.478] | 1.094 [0.602, 1.987] | 1.020 [0.236, 4.414] |
| `small-flat.fresh.mac-mars.sender.warm` | coalesce1m | 1.000 [0.790, 1.267] | 1.079 [0.759, 1.534] | 1.148 [0.693, 1.903] |
| `small-flat.fresh.mac-mars.sender.warm` | soft256 | 0.984 [0.957, 1.011] | 1.020 [0.400, 2.606] | 1.148 [0.057, 23.299] |
| `small-flat.fresh.mac-mars.sender.warm` | all-three | 0.973 [0.865, 1.094] | 1.175 [0.549, 2.518] | 1.205 [0.055, 26.384] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | all-three | batch256 | coalesce1m | scan-all | soft256 | xs-best |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | 12.016 | 12.076 | 12.141 | 11.757 | 11.350 | 12.003 |
| `small-deep.fresh.mac-mars.sender.warm` | 10.464 | 12.544 | 11.687 | 11.230 | 15.152 | 10.959 |
| `small-flat.fresh.mac-mars.sender.warm` | 3.899 | 4.293 | 3.724 | 3.309 | 3.715 | 3.248 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | batch256 | 0.1250 | 143 | 191 |
| `real-congress.fresh.mac-mars.sender.warm` | scan-all | 0.1024 | 97 | 129 |
| `real-congress.fresh.mac-mars.sender.warm` | coalesce1m | 0.4388 | 1730 | 2318 |
| `real-congress.fresh.mac-mars.sender.warm` | soft256 | 0.4291 | 1655 | 2217 |
| `real-congress.fresh.mac-mars.sender.warm` | all-three | 0.0576 | 32 | 42 |
| `small-deep.fresh.mac-mars.sender.warm` | batch256 | 0.2856 | 734 | 983 |
| `small-deep.fresh.mac-mars.sender.warm` | scan-all | 0.1711 | 265 | 355 |
| `small-deep.fresh.mac-mars.sender.warm` | coalesce1m | 0.0955 | 84 | 112 |
| `small-deep.fresh.mac-mars.sender.warm` | soft256 | 0.4014 | 1448 | 1940 |
| `small-deep.fresh.mac-mars.sender.warm` | all-three | 0.0327 | 12 | 15 |
| `small-flat.fresh.mac-mars.sender.warm` | batch256 | 0.1143 | 120 | 160 |
| `small-flat.fresh.mac-mars.sender.warm` | scan-all | 0.1604 | 233 | 312 |
| `small-flat.fresh.mac-mars.sender.warm` | coalesce1m | 0.0554 | 30 | 39 |
| `small-flat.fresh.mac-mars.sender.warm` | soft256 | 0.3357 | 1014 | 1358 |
| `small-flat.fresh.mac-mars.sender.warm` | all-three | 0.3443 | 1066 | 1428 |

## Voided attempts

- mac reaches mars by en0, not en13
- xs-best: harness error: mars: `sync -f ~/benchmarks/xsyncv4/lab/work/20261017T005544Z-D1-mac-sender-knobs/small-flat.fresh.mac-mars.sender.warm` exit
