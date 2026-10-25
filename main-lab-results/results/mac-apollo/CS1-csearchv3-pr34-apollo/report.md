# CS1-csearchv3-pr34-apollo

On csearchv3, xs-rs at PR #34 is at least as fast as its base and faster than rsync at fresh, no-op and a 10% update.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T204310Z-CS1-csearchv3-pr34-apollo.
- Valid blocks: 5. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.296 |  |  | too few blocks |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs | 1 | 0.300 |  |  | too few blocks |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs-base | 1 | 0.297 |  |  | too few blocks |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-cpp | 1 | 0.373 |  |  | too few blocks |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs | 1 | 0.386 |  |  | too few blocks |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs-base | 1 | 0.527 |  |  | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.257 |  |  | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs | 1 | 0.193 |  |  | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs-base | 1 | 0.275 |  |  | too few blocks |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.504 |  |  | too few blocks |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs | 1 | 0.493 |  |  | too few blocks |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs-base | 1 | 0.462 |  |  | too few blocks |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.336 |  |  | too few blocks |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs | 1 | 0.286 |  |  | too few blocks |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs-base | 1 | 0.299 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.738 | 2.464 | 0.296 |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs | 0.661 | 7.747 | 0.300 |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs-base | 0.657 | 7.266 | 0.296 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-cpp | 0.622 | 5.913 | 0.371 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs | 0.732 | 25.805 | 0.347 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs-base | 0.600 | 12.402 | 0.460 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 0.860 | 4.134 | 0.257 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs | 0.951 | 11.995 | 0.193 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs-base | 0.854 | 12.091 | 0.275 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.177 | 3.063 | 0.502 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.979 | 9.474 | 0.491 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs-base | 0.966 | 9.630 | 0.460 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.801 | 3.290 | 0.316 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs | 1.031 | 8.799 | 0.220 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs-base | 0.708 | 8.662 | 0.236 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs | xs-rs-base |
|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | 504.6 | 149.6 | 151.3 | 149.8 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | 381.8 | 142.3 | 147.2 | 201.3 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | 106.8 | 27.491 | 20.625 | 29.311 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | 98.947 | 49.856 | 48.778 | 45.726 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | 117.5 | 39.460 | 33.621 | 35.149 |
