# X3-large-tune-many

The settings that help one large file also help several, or matter less there.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T030432Z-X3-large-tune-many.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | j4 | 6 | 0.997 [0.970, 1.026] | 0.995 [0.968, 1.041] | 0.8438 | too few blocks |
| `large-four.fresh.mars-mac.receiver.warm` | j8 | 6 | 0.971 [0.920, 1.024] | 0.983 [0.879, 1.017] | 0.1562 | too few blocks |
| `large-four.fresh.mars-mac.receiver.warm` | block4m | 6 | 1.000 [0.948, 1.054] | 0.995 [0.946, 1.099] | 0.9688 | too few blocks |
| `large-four.fresh.mars-mac.receiver.warm` | chunk1m | 6 | 0.993 [0.965, 1.022] | 0.993 [0.965, 1.042] | 0.4688 | too few blocks |
| `large-four.fresh.mars-mac.receiver.warm` | queues | 6 | 0.974 [0.941, 1.009] | 0.974 [0.923, 1.000] | 0.0312 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 6 | 1.005 [0.986, 1.024] | 1.005 [0.977, 1.026] | 0.5000 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 6 | 1.026 [0.981, 1.072] | 1.020 [0.989, 1.105] | 0.1562 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 6 | 0.991 [0.979, 1.003] | 0.992 [0.976, 1.005] | 0.1250 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 6 | 1.018 [0.968, 1.072] | 1.009 [0.977, 1.114] | 0.5000 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 6 | 1.000 [0.992, 1.008] | 1.000 [0.991, 1.009] | 0.9375 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | j4 | 0.993 [0.969, 1.018] | 0.881 [0.680, 1.141] | 1.001 [0.975, 1.027] |
| `large-four.fresh.mars-mac.receiver.warm` | j8 | 0.995 [0.980, 1.010] | 0.928 [0.842, 1.023] | 0.974 [0.922, 1.029] |
| `large-four.fresh.mars-mac.receiver.warm` | block4m | 0.942 [0.909, 0.976] | 1.009 [0.890, 1.144] | 1.003 [0.952, 1.056] |
| `large-four.fresh.mars-mac.receiver.warm` | chunk1m | 0.987 [0.969, 1.004] | 0.825 [0.682, 0.998] | 0.996 [0.970, 1.023] |
| `large-four.fresh.mars-mac.receiver.warm` | queues | 0.987 [0.969, 1.006] | 2.256 [2.019, 2.522] | 0.978 [0.940, 1.018] |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 0.844 [0.816, 0.874] | 1.047 [0.867, 1.264] | 1.005 [0.986, 1.024] |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 0.894 [0.863, 0.927] | 1.014 [0.828, 1.242] | 1.009 [0.986, 1.031] |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 0.963 [0.939, 0.987] | 1.315 [1.113, 1.553] | 0.991 [0.978, 1.003] |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 0.972 [0.934, 1.012] | 0.922 [0.747, 1.138] | 1.019 [0.967, 1.073] |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 1.009 [0.959, 1.061] | 2.389 [2.033, 2.807] | 1.000 [0.991, 1.008] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | block4m | chunk1m | j4 | j8 | queues | xs |
|---|---|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | 22.927 | 22.766 | 22.869 | 22.259 | 22.338 | 22.933 |
| `large-mixed.fresh.mars-mac.receiver.warm` | 22.786 | 23.419 | 23.105 | 23.585 | 22.989 | 22.993 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | j4 | 0.0268 | 9 | 11 |
| `large-four.fresh.mars-mac.receiver.warm` | j8 | 0.0513 | 26 | 34 |
| `large-four.fresh.mars-mac.receiver.warm` | block4m | 0.0507 | 26 | 33 |
| `large-four.fresh.mars-mac.receiver.warm` | chunk1m | 0.0274 | 9 | 12 |
| `large-four.fresh.mars-mac.receiver.warm` | queues | 0.0333 | 12 | 16 |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 0.0181 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 0.0421 | 18 | 24 |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 0.0112 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 0.0489 | 24 | 31 |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 0.0074 | 8 | 8 |
