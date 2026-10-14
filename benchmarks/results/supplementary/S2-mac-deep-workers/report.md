# S2-mac-deep-workers

Pulling a deep tree onto APFS, xs with one or two receiving workers is faster than with its default of four.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261013T205523Z-S2-mac-deep-workers.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 8 | 0.560 [0.460, 0.683] | 0.575 [0.434, 0.657] | 0.0078 | faster |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 8 | 1.227 [1.042, 1.444] | 1.267 [1.035, 1.434] | 0.0312 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 8 | 1.077 [0.907, 1.279] | 1.129 [0.871, 1.243] | 0.3516 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 8 | 0.947 [0.846, 1.060] | 0.943 [0.831, 1.082] | 0.3203 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.warm` | scan1 | 8 | 1.030 [0.839, 1.266] | 1.012 [0.828, 1.336] | 0.7109 | inconclusive |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 8 | 0.257 [0.189, 0.349] | 0.252 [0.176, 0.361] | 0.0078 | faster |
| `small-deep.noop.mars-mac.receiver.warm` | recv1 | 8 | 1.844 [1.530, 2.222] | 1.835 [1.471, 2.297] | 0.0078 | slower |
| `small-deep.noop.mars-mac.receiver.warm` | recv2 | 8 | 1.122 [0.977, 1.290] | 1.160 [0.948, 1.273] | 0.1016 | inconclusive |
| `small-deep.noop.mars-mac.receiver.warm` | recv8 | 8 | 1.035 [0.763, 1.404] | 1.032 [0.754, 1.494] | 0.7891 | inconclusive |
| `small-deep.noop.mars-mac.receiver.warm` | scan1 | 8 | 1.001 [0.860, 1.167] | 1.003 [0.833, 1.184] | 0.9844 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.434 [0.413, 0.455] | 0.565 [0.467, 0.683] | 0.199 [0.188, 0.211] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 0.759 [0.733, 0.786] | 1.226 [1.041, 1.443] | 0.948 [0.905, 0.993] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 0.900 [0.885, 0.915] | 1.077 [0.907, 1.279] | 0.988 [0.958, 1.019] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 1.044 [1.020, 1.069] | 0.949 [0.849, 1.060] | 1.030 [0.990, 1.071] |
| `small-deep.fresh.mars-mac.receiver.warm` | scan1 | 0.999 [0.981, 1.018] | 1.032 [0.841, 1.266] | 0.981 [0.938, 1.026] |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 0.104 [0.095, 0.114] | 0.264 [0.196, 0.356] | 0.151 [0.148, 0.153] |
| `small-deep.noop.mars-mac.receiver.warm` | recv1 | 0.800 [0.741, 0.864] | 1.853 [1.520, 2.259] | 0.942 [0.892, 0.995] |
| `small-deep.noop.mars-mac.receiver.warm` | recv2 | 0.823 [0.800, 0.846] | 1.122 [0.977, 1.288] | 0.994 [0.979, 1.009] |
| `small-deep.noop.mars-mac.receiver.warm` | recv8 | 1.188 [1.054, 1.338] | 1.035 [0.764, 1.401] | 0.994 [0.940, 1.050] |
| `small-deep.noop.mars-mac.receiver.warm` | scan1 | 0.999 [0.939, 1.063] | 1.002 [0.861, 1.165] | 1.015 [0.998, 1.033] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | recv1 | recv2 | recv8 | rsync | scan1 | xs |
|---|---|---|---|---|---|---|
| `small-deep.fresh.mars-mac.receiver.warm` | 73.440 | 64.485 | 56.713 | 33.557 | 61.680 | 59.872 |
| `small-deep.noop.mars-mac.receiver.warm` | 21.122 | 12.858 | 11.852 | 2.943 | 11.473 | 11.456 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.2358 | 501 | 671 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 0.1954 | 345 | 461 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 0.2055 | 382 | 511 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 0.1350 | 166 | 222 |
| `small-deep.fresh.mars-mac.receiver.warm` | scan1 | 0.2462 | 546 | 731 |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 0.3652 | 1199 | 1606 |
| `small-deep.noop.mars-mac.receiver.warm` | recv1 | 0.2230 | 449 | 601 |
| `small-deep.noop.mars-mac.receiver.warm` | recv2 | 0.1664 | 251 | 336 |
| `small-deep.noop.mars-mac.receiver.warm` | recv8 | 0.3649 | 1198 | 1604 |
| `small-deep.noop.mars-mac.receiver.warm` | scan1 | 0.1826 | 302 | 403 |
