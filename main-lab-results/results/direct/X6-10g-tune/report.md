# X6-10g-tune

At 10 Gb/s, parallel ranges, larger blocks or writes, or deeper queues bring xs closer to the ssh ceiling.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T032059Z-X6-10g-tune.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 6 | 0.798 [0.583, 1.093] | 0.797 [0.526, 1.137] | 0.1875 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 6 | 0.692 [0.507, 0.945] | 0.662 [0.511, 1.137] | 0.0625 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 6 | 0.557 [0.376, 0.823] | 0.538 [0.364, 1.073] | 0.0625 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 6 | 0.542 [0.305, 0.962] | 0.541 [0.289, 1.014] | 0.0625 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 6 | 0.527 [0.345, 0.805] | 0.552 [0.284, 0.803] | 0.0312 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 6 | 0.984 [0.976, 0.992] | 0.984 [0.974, 0.993] | 0.0312 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 6 | 0.985 [0.967, 1.004] | 0.990 [0.955, 1.004] | 0.0625 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 6 | 0.997 [0.984, 1.010] | 0.998 [0.977, 1.010] | 0.5938 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 6 | 0.982 [0.967, 0.996] | 0.984 [0.956, 0.995] | 0.0312 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 6 | 1.009 [0.991, 1.027] | 1.013 [0.976, 1.022] | 0.2812 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | j4 | 6 | 1.402 [0.669, 2.936] | 1.193 [0.720, 5.243] | 0.3125 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 6 | 1.314 [0.611, 2.824] | 1.055 [0.768, 5.493] | 0.5625 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 6 | 1.251 [0.600, 2.608] | 1.142 [0.696, 4.355] | 0.5938 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 6 | 1.107 [0.529, 2.315] | 0.928 [0.686, 4.472] | 0.9688 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | queues | 6 | 1.185 [0.505, 2.782] | 0.935 [0.705, 6.019] | 0.9375 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 6 | 0.989 [0.982, 0.996] | 0.989 [0.978, 0.996] | 0.0312 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 6 | 0.995 [0.984, 1.007] | 0.994 [0.981, 1.014] | 0.4062 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 6 | 0.992 [0.981, 1.004] | 0.992 [0.980, 1.012] | 0.1562 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 6 | 0.989 [0.982, 0.997] | 0.990 [0.978, 1.000] | 0.0625 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 6 | 1.016 [1.011, 1.021] | 1.017 [1.008, 1.022] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 0.923 [0.844, 1.010] | 0.992 [0.908, 1.084] | 0.799 [0.583, 1.096] |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 0.921 [0.840, 1.010] | 0.952 [0.845, 1.073] | 0.692 [0.507, 0.944] |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 0.808 [0.729, 0.895] | 0.860 [0.808, 0.915] | 0.555 [0.376, 0.820] |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 0.874 [0.788, 0.969] | 0.905 [0.808, 1.014] | 0.538 [0.302, 0.959] |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 0.873 [0.802, 0.949] | 2.587 [2.384, 2.806] | 0.527 [0.345, 0.803] |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 0.780 [0.760, 0.800] | 0.987 [0.905, 1.077] | 0.983 [0.975, 0.992] |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 0.867 [0.857, 0.878] | 0.982 [0.892, 1.082] | 0.985 [0.966, 1.004] |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 0.960 [0.936, 0.985] | 1.350 [1.231, 1.481] | 0.997 [0.983, 1.011] |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 0.997 [0.972, 1.022] | 0.895 [0.783, 1.022] | 0.982 [0.966, 0.997] |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 1.001 [0.973, 1.031] | 2.450 [2.234, 2.687] | 1.009 [0.990, 1.028] |
| `large-one.fresh.mac-mars.sender.warm` | j4 | 1.069 [0.950, 1.203] | 0.744 [0.618, 0.897] | 1.402 [0.669, 2.936] |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 1.088 [0.955, 1.239] | 0.943 [0.783, 1.136] | 1.306 [0.606, 2.811] |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 0.951 [0.849, 1.066] | 0.661 [0.550, 0.795] | 1.247 [0.599, 2.597] |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 1.057 [0.930, 1.200] | 0.937 [0.700, 1.256] | 1.106 [0.528, 2.314] |
| `large-one.fresh.mac-mars.sender.warm` | queues | 1.061 [0.916, 1.229] | 3.039 [2.363, 3.909] | 1.177 [0.499, 2.776] |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 1.006 [0.983, 1.028] | 0.962 [0.917, 1.008] | 0.989 [0.982, 0.996] |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 1.150 [1.118, 1.182] | 1.016 [0.918, 1.123] | 0.995 [0.984, 1.007] |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 0.938 [0.911, 0.965] | 0.980 [0.853, 1.128] | 0.993 [0.981, 1.005] |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 1.008 [0.981, 1.036] | 0.959 [0.871, 1.056] | 0.989 [0.983, 0.996] |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 0.992 [0.971, 1.012] | 2.467 [2.263, 2.690] | 1.017 [1.012, 1.021] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | block4m | chunk1m | j4 | j8 | queues | xs |
|---|---|---|---|---|---|---|
| `large-mixed.fresh.mac-mars.sender.warm` | 15.747 | 15.333 | 22.588 | 19.581 | 14.907 | 28.290 |
| `large-mixed.fresh.mars-mac.receiver.warm` | 8.222 | 8.098 | 8.115 | 8.127 | 8.318 | 8.247 |
| `large-one.fresh.mac-mars.sender.warm` | 12.238 | 10.824 | 13.706 | 12.849 | 11.591 | 9.779 |
| `large-one.fresh.mars-mac.receiver.warm` | 7.159 | 7.138 | 7.134 | 7.180 | 7.330 | 7.214 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 0.2992 | 806 | 1079 |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 0.2966 | 792 | 1061 |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 0.3729 | 1251 | 1675 |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 0.5464 | 2681 | 3593 |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 0.4032 | 1462 | 1958 |
| `large-mixed.fresh.mars-mac.receiver.warm` | j4 | 0.0076 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | j8 | 0.0180 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | block4m | 0.0125 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | chunk1m | 0.0141 | 8 | 8 |
| `large-mixed.fresh.mars-mac.receiver.warm` | queues | 0.0169 | 8 | 8 |
| `large-one.fresh.mac-mars.sender.warm` | j4 | 0.7045 | 4456 | 5971 |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 0.7290 | 4771 | 6393 |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 0.6998 | 4397 | 5892 |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 0.7030 | 4437 | 5946 |
| `large-one.fresh.mac-mars.sender.warm` | queues | 0.8129 | 5932 | 7950 |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 0.0064 | 8 | 8 |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 0.0113 | 8 | 8 |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 0.0110 | 8 | 8 |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 0.0071 | 8 | 8 |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 0.0047 | 8 | 8 |
