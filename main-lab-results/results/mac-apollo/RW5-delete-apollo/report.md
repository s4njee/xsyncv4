# RW5-delete-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. A backup whose source lost 10% of its files: --delete must remove them. xs-rs has no --delete, so it sits out.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162412Z-RW5-delete-apollo, 20261023T040632Z-RW5-delete-apollo.
- Valid blocks: 6. Voided block attempts: 9.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.405 [0.340, 0.482] | 0.405 | 0.2500 | too few blocks |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.283 [0.134, 0.600] | 0.275 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.439 [1.390, 1.490] | 2.952 [2.069, 4.213] | 0.401 [0.332, 0.484] |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 1.142 [1.113, 1.172] | 3.320 [2.869, 3.841] | 0.225 [0.195, 0.260] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp |
|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | 12.521 | 5.072 |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | 6.565 | 1.860 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0700 | 46 | 61 |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 0.3020 | 821 | 1099 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
