# H4-pair-pi-receive

Fewer receiving workers, larger writes or no compression land small trees on the Pi faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T130118Z-H4-pair-pi-receive.
- Valid blocks: 4. Voided block attempts: 60.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | recv1 | 1 | 1.198 |  |  | too few blocks |
| `real-congress.fresh.mars-neo.sender.warm` | recv2 | 1 | 1.036 |  |  | too few blocks |
| `real-congress.fresh.mars-neo.sender.warm` | coalesce1m | 1 | 0.995 |  |  | too few blocks |
| `real-congress.fresh.mars-neo.sender.warm` | xs-best | 1 | 1.202 |  |  | too few blocks |
| `small-deep.fresh.mars-neo.sender.warm` | recv1 | 1 | 1.320 |  |  | too few blocks |
| `small-deep.fresh.mars-neo.sender.warm` | recv2 | 1 | 1.065 |  |  | too few blocks |
| `small-deep.fresh.mars-neo.sender.warm` | coalesce1m | 1 | 1.023 |  |  | too few blocks |
| `small-deep.fresh.mars-neo.sender.warm` | xs-best | 1 | 1.024 |  |  | too few blocks |
| `small-flat.fresh.mars-neo.sender.warm` | recv1 | 2 | 1.057 [0.845, 1.322] | 1.057 | 0.5000 | too few blocks |
| `small-flat.fresh.mars-neo.sender.warm` | recv2 | 2 | 0.980 [0.867, 1.107] | 0.980 | 0.5000 | too few blocks |
| `small-flat.fresh.mars-neo.sender.warm` | coalesce1m | 2 | 1.009 [0.929, 1.097] | 1.009 | 0.5000 | too few blocks |
| `small-flat.fresh.mars-neo.sender.warm` | xs-best | 2 | 1.036 [0.948, 1.131] | 1.036 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | recv1 | 0.880 | 1.402 | 1.208 |
| `real-congress.fresh.mars-neo.sender.warm` | recv2 | 0.972 | 1.040 | 1.033 |
| `real-congress.fresh.mars-neo.sender.warm` | coalesce1m | 0.989 | 1.325 | 0.993 |
| `real-congress.fresh.mars-neo.sender.warm` | xs-best | 1.006 | 0.676 | 1.209 |
| `small-deep.fresh.mars-neo.sender.warm` | recv1 | 0.897 | 0.922 | 1.343 |
| `small-deep.fresh.mars-neo.sender.warm` | recv2 | 0.952 | 0.981 | 1.072 |
| `small-deep.fresh.mars-neo.sender.warm` | coalesce1m | 1.009 | 1.001 | 1.034 |
| `small-deep.fresh.mars-neo.sender.warm` | xs-best | 0.910 | 0.994 | 1.033 |
| `small-flat.fresh.mars-neo.sender.warm` | recv1 | 0.809 [0.674, 0.970] | 1.065 [0.029, 38.889] | 1.076 [0.715, 1.620] |
| `small-flat.fresh.mars-neo.sender.warm` | recv2 | 0.954 [0.728, 1.249] | 1.353 [0.787, 2.326] | 0.978 [0.863, 1.108] |
| `small-flat.fresh.mars-neo.sender.warm` | coalesce1m | 1.003 [0.979, 1.027] | 1.149 [1.134, 1.163] | 1.008 [0.908, 1.119] |
| `small-flat.fresh.mars-neo.sender.warm` | xs-best | 0.952 [0.871, 1.040] | 0.805 [0.419, 1.546] | 1.052 [0.974, 1.136] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | coalesce1m | recv1 | recv2 | xs-best | xs-z-best |
|---|---|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | 10.591 | 12.750 | 11.025 | 12.790 | 10.644 |
| `small-deep.fresh.mars-neo.sender.warm` | 12.925 | 16.686 | 13.466 | 12.945 | 12.639 |
| `small-flat.fresh.mars-neo.sender.warm` | 3.618 | 3.789 | 3.514 | 3.713 | 3.585 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.mars-neo.sender.warm` | recv1 | 0.0249 | 8 | 10 |
| `small-flat.fresh.mars-neo.sender.warm` | recv2 | 0.0136 | 8 | 8 |
| `small-flat.fresh.mars-neo.sender.warm` | coalesce1m | 0.0093 | 8 | 8 |
| `small-flat.fresh.mars-neo.sender.warm` | xs-best | 0.0098 | 8 | 8 |

## Voided attempts

- round trip is 2.093 ms, above 2.0
- round trip is 2.118 ms, above 2.0
- round trip is 2.123 ms, above 2.0
- round trip is 2.133 ms, above 2.0
- round trip is 2.159 ms, above 2.0
- round trip is 2.204 ms, above 2.0
- round trip is 2.212 ms, above 2.0
- round trip is 2.244 ms, above 2.0
- round trip is 2.248 ms, above 2.0
- round trip is 2.259 ms, above 2.0
- round trip is 2.282 ms, above 2.0
- round trip is 2.283 ms, above 2.0
- round trip is 2.29 ms, above 2.0
- round trip is 2.322 ms, above 2.0
- round trip is 2.324 ms, above 2.0
- round trip is 2.359 ms, above 2.0
- round trip is 2.363 ms, above 2.0
- round trip is 2.383 ms, above 2.0
- round trip is 2.392 ms, above 2.0
- round trip is 2.411 ms, above 2.0
- round trip is 2.443 ms, above 2.0
- round trip is 2.466 ms, above 2.0
- round trip is 2.477 ms, above 2.0
- round trip is 2.485 ms, above 2.0
- round trip is 2.493 ms, above 2.0
- round trip is 2.498 ms, above 2.0
- round trip is 2.503 ms, above 2.0
- round trip is 2.505 ms, above 2.0
- round trip is 2.509 ms, above 2.0
- round trip is 2.516 ms, above 2.0
- round trip is 2.524 ms, above 2.0
- round trip is 2.528 ms, above 2.0
- round trip is 2.531 ms, above 2.0
- round trip is 2.534 ms, above 2.0
- round trip is 2.544 ms, above 2.0
- round trip is 2.553 ms, above 2.0
- round trip is 2.554 ms, above 2.0
- round trip is 2.557 ms, above 2.0
- round trip is 2.561 ms, above 2.0
- round trip is 2.567 ms, above 2.0
- round trip is 2.597 ms, above 2.0
- round trip is 2.622 ms, above 2.0
- round trip is 2.628 ms, above 2.0
- round trip is 2.653 ms, above 2.0
- round trip is 2.695 ms, above 2.0
- round trip is 2.702 ms, above 2.0
- round trip is 2.724 ms, above 2.0
- round trip is 2.761 ms, above 2.0
- round trip is 2.776 ms, above 2.0
- round trip is 2.778 ms, above 2.0
- round trip is 2.796 ms, above 2.0
- round trip is 2.848 ms, above 2.0
- round trip is 2.883 ms, above 2.0
- round trip is 2.896 ms, above 2.0
- round trip is 3.02 ms, above 2.0
- round trip is 3.089 ms, above 2.0
- round trip is 3.561 ms, above 2.0
- xs-best: the transfer exited 255: Connection reset by [address] port 22
xs: connection unexpectedly closed (remote shell exited with code 255)
xs: error summary
