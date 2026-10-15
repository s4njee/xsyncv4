# X3b-large-tune-many-to-mars

The settings that help one large file also help several, or matter less there.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T131341Z-X3b-large-tune-many-to-mars.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | j4 | 6 | 0.991 [0.783, 1.255] | 0.996 [0.694, 1.368] | 0.8750 | too few blocks |
| `large-four.fresh.mac-mars.sender.warm` | j8 | 6 | 0.771 [0.385, 1.543] | 0.907 [0.213, 1.182] | 0.5000 | too few blocks |
| `large-four.fresh.mac-mars.sender.warm` | block4m | 6 | 0.828 [0.526, 1.303] | 0.862 [0.410, 1.366] | 0.3750 | too few blocks |
| `large-four.fresh.mac-mars.sender.warm` | chunk1m | 6 | 0.832 [0.433, 1.600] | 0.924 [0.261, 1.542] | 0.6250 | too few blocks |
| `large-four.fresh.mac-mars.sender.warm` | queues | 6 | 0.793 [0.442, 1.424] | 0.900 [0.266, 1.192] | 0.4062 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 6 | 1.247 [1.040, 1.494] | 1.224 [1.021, 1.685] | 0.0312 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 6 | 1.313 [0.841, 2.050] | 1.243 [0.795, 2.798] | 0.1250 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 6 | 1.291 [0.883, 1.888] | 1.314 [0.748, 1.990] | 0.1562 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 6 | 1.429 [0.946, 2.158] | 1.351 [0.975, 2.836] | 0.0938 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 6 | 0.995 [0.823, 1.203] | 1.026 [0.728, 1.200] | 0.9062 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | j4 | 1.018 [0.966, 1.072] | 0.984 [0.893, 1.085] | 0.989 [0.787, 1.242] |
| `large-four.fresh.mac-mars.sender.warm` | j8 | 0.964 [0.818, 1.136] | 0.993 [0.922, 1.070] | 0.772 [0.385, 1.545] |
| `large-four.fresh.mac-mars.sender.warm` | block4m | 0.916 [0.816, 1.028] | 0.796 [0.740, 0.856] | 0.828 [0.526, 1.303] |
| `large-four.fresh.mac-mars.sender.warm` | chunk1m | 0.962 [0.813, 1.137] | 0.993 [0.864, 1.142] | 0.831 [0.433, 1.598] |
| `large-four.fresh.mac-mars.sender.warm` | queues | 0.945 [0.809, 1.105] | 3.128 [2.742, 3.570] | 0.788 [0.440, 1.410] |
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 1.052 [1.007, 1.099] | 0.980 [0.927, 1.036] | 1.246 [1.036, 1.499] |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 1.023 [0.955, 1.096] | 0.988 [0.920, 1.061] | 1.314 [0.841, 2.053] |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 1.029 [0.907, 1.166] | 0.972 [0.934, 1.011] | 1.292 [0.880, 1.895] |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 1.136 [1.013, 1.275] | 1.020 [0.964, 1.080] | 1.430 [0.948, 2.159] |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 1.012 [0.927, 1.104] | 2.798 [2.590, 3.022] | 0.996 [0.823, 1.205] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | block4m | chunk1m | j4 | j8 | queues | xs |
|---|---|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | 45.384 | 45.594 | 54.317 | 42.231 | 43.458 | 54.807 |
| `large-mixed.fresh.mac-mars.sender.warm` | 50.449 | 55.821 | 48.725 | 51.325 | 38.880 | 39.076 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | j4 | 0.2247 | 456 | 610 |
| `large-four.fresh.mac-mars.sender.warm` | j8 | 0.6615 | 3929 | 5265 |
| `large-four.fresh.mac-mars.sender.warm` | block4m | 0.4316 | 1674 | 2243 |
| `large-four.fresh.mac-mars.sender.warm` | chunk1m | 0.6232 | 3487 | 4673 |
| `large-four.fresh.mac-mars.sender.warm` | queues | 0.5578 | 2794 | 3744 |
| `large-mixed.fresh.mac-mars.sender.warm` | j4 | 0.1725 | 270 | 360 |
| `large-mixed.fresh.mac-mars.sender.warm` | j8 | 0.4244 | 1619 | 2169 |
| `large-mixed.fresh.mac-mars.sender.warm` | block4m | 0.3620 | 1179 | 1579 |
| `large-mixed.fresh.mac-mars.sender.warm` | chunk1m | 0.3929 | 1388 | 1859 |
| `large-mixed.fresh.mac-mars.sender.warm` | queues | 0.1809 | 296 | 396 |
