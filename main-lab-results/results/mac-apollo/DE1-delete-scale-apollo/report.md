# DE1-delete-scale-apollo

rsync --delete is at least 5% faster than xs --delete when 10% of a large tree's files are gone.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T083458Z-DE1-delete-scale-apollo.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.439 |  |  | too few blocks |
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 0.400 |  |  | too few blocks |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.151 |  |  | too few blocks |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 0.307 |  |  | too few blocks |
| `real-csearchv3.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.451 |  |  | too few blocks |
| `real-csearchv3.delete-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 0.379 |  |  | too few blocks |
| `real-csearchv3.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.295 |  |  | too few blocks |
| `real-csearchv3.delete-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 0.248 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.412 | 3.150 | 0.434 |
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 2.186 | 3.382 | 0.391 |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 0.878 | 3.288 | 0.144 |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.424 | 3.495 | 0.177 |
| `real-csearchv3.delete-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.378 | 3.986 | 0.451 |
| `real-csearchv3.delete-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.945 | 4.103 | 0.378 |
| `real-csearchv3.delete-10pct.mac-apollo.sender.warm` | xs-cpp | 0.890 | 4.101 | 0.261 |
| `real-csearchv3.delete-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.077 | 4.167 | 0.245 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j8 |
|---|---|---|---|
| `real-congress.delete-10pct.apollo-mac.receiver.warm` | 12.367 | 5.430 | 4.943 |
| `real-congress.delete-10pct.mac-apollo.sender.warm` | 10.130 | 1.526 | 3.112 |
| `real-csearchv3.delete-10pct.apollo-mac.receiver.warm` | 136.3 | 61.534 | 51.608 |
| `real-csearchv3.delete-10pct.mac-apollo.sender.warm` | 124.6 | 36.733 | 30.870 |
