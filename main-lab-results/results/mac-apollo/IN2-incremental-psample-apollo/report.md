# IN2-incremental-psample-apollo

rsync -aH is at least 5% faster than xs -aH at a 1% update of psample.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T051236Z-IN2-incremental-psample-apollo.
- Valid blocks: 3. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.703 [0.014, 36.394] | 0.703 | 0.5000 | too few blocks |
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 2 | 0.627 [0.146, 2.686] | 0.627 | 0.5000 | too few blocks |
| `real-psample.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.376 |  |  | too few blocks |
| `real-psample.update-1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 0.335 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2.205 [0.030, 163.653] | 3.941 [1.973, 7.871] | 0.703 [0.013, 36.660] |
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 2.462 [0.045, 135.625] | 4.117 [2.164, 7.833] | 0.624 [0.139, 2.807] |
| `real-psample.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.323 | 3.921 | 0.376 |
| `real-psample.update-1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.697 | 4.032 | 0.334 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j8 |
|---|---|---|---|
| `real-psample.update-1pct.apollo-mac.receiver.warm` | 57.844 | 40.676 | 36.253 |
| `real-psample.update-1pct.mac-apollo.sender.warm` | 89.310 | 33.597 | 29.879 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.4392 | 1734 | 2323 |
| `real-psample.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.1620 | 238 | 318 |
