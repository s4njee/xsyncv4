# P3b-hdd-writeback

On the hard drive, eager writeback shortens xs's time to durable for small and mixed trees.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T223339Z-P3b-hdd-writeback.
- Valid blocks: 24. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 6 | 0.954 [0.874, 1.042] | 0.975 [0.810, 1.023] | 0.1875 | too few blocks |
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs | 6 | 0.897 [0.812, 0.990] | 0.894 [0.787, 0.981] | 0.0312 | too few blocks |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 6 | 1.002 [0.618, 1.625] | 0.990 [0.525, 1.584] | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs | 6 | 1.078 [0.691, 1.684] | 1.018 [0.578, 1.766] | 0.7812 | too few blocks |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 6 | 0.967 [0.623, 1.499] | 1.020 [0.458, 1.435] | 0.8438 | too few blocks |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs | 6 | 0.858 [0.579, 1.273] | 0.906 [0.547, 1.455] | 0.3125 | too few blocks |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 6 | 0.846 [0.591, 1.211] | 0.843 [0.501, 1.196] | 0.3438 | too few blocks |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs | 6 | 0.738 [0.542, 1.006] | 0.746 [0.459, 1.083] | 0.0625 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.978 [0.955, 1.002] | 0.952 [0.907, 0.999] | 1.000 [0.867, 1.154] |
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs | 1.068 [1.041, 1.097] | 0.962 [0.899, 1.030] | 0.915 [0.793, 1.057] |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.996 [0.965, 1.027] | 1.036 [0.824, 1.302] | 1.026 [0.809, 1.303] |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs | 1.230 [1.191, 1.270] | 0.944 [0.788, 1.132] | 1.177 [0.997, 1.390] |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 1.024 [0.987, 1.063] | 0.996 [0.844, 1.175] | 1.131 [0.859, 1.489] |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs | 1.287 [1.266, 1.308] | 0.995 [0.831, 1.191] | 1.223 [0.894, 1.673] |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 1.024 [0.981, 1.069] | 0.998 [0.721, 1.381] | 1.134 [0.889, 1.445] |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs | 1.223 [1.184, 1.264] | 1.184 [0.768, 1.824] | 1.094 [0.804, 1.488] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-best | xs-best-eager |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | 9.402 | 10.482 | 10.005 |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | 24.828 | 23.027 | 23.078 |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | 18.088 | 21.071 | 20.367 |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | 7.863 | 10.648 | 9.006 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.0841 | 66 | 87 |
| `mixed-bimodal.fresh.mac-mars-hdd.sender.warm` | xs | 0.0944 | 82 | 110 |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.4603 | 1903 | 2550 |
| `real-congress.fresh.mac-mars-hdd.sender.warm` | xs | 0.4246 | 1620 | 2171 |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.4183 | 1572 | 2107 |
| `small-deep.fresh.mac-mars-hdd.sender.warm` | xs | 0.3752 | 1265 | 1695 |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs-best-eager | 0.3417 | 1050 | 1407 |
| `small-flat.fresh.mac-mars-hdd.sender.warm` | xs | 0.2944 | 780 | 1045 |

## Voided attempts

- round trip is 3.075 ms, above 2.0
