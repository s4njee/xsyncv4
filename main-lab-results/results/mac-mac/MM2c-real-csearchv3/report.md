# MM2c-real-csearchv3

On the user's csearchv3 tree (14 GB, 1,345,908 files, 472,330 directories), rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T114747Z-MM2c-real-csearchv3.
- Valid blocks: 1. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-csearchv3.fresh.mac-mars.sender.warm` | xs-cpp | 1 | 0.289 |  |  | too few blocks |
| `real-csearchv3.fresh.mac-mars.sender.warm` | xs-rs | 1 | 0.298 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-csearchv3.fresh.mac-mars.sender.warm` | xs-cpp | 0.765 | 4.103 | 0.289 |
| `real-csearchv3.fresh.mac-mars.sender.warm` | xs-rs | 0.676 | 7.499 | 0.297 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `real-csearchv3.fresh.mac-mars.sender.warm` | 322.9 | 93.291 | 96.109 |

## Voided attempts

- stopped
