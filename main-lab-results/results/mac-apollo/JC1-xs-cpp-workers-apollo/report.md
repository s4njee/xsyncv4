# JC1-xs-cpp-workers-apollo

Some worker count is at least 5% faster than xs-c++'s default of 4 in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T102540Z-JC1-xs-cpp-workers-apollo.
- Valid blocks: 4. Voided block attempts: 6.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 1 | 0.997 |  |  | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 1 | 0.993 |  |  | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 1.032 |  |  | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 1 | 1.074 |  |  | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 1 | 2.648 |  |  | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 1 | 0.379 |  |  | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 1 | 0.987 |  |  | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 2.225 |  |  | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 1 | 2.411 |  |  | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1 | 0.826 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 1 | 1.931 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 1 | 1.937 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 1.056 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 1 | 2.464 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1 | 3.331 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 1 | 2.454 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 1 | 1.305 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 1.030 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 1 | 1.646 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1 | 3.980 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.917 | 0.887 | 0.996 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.963 | 0.979 | 0.994 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.263 | 1.085 | 1.033 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 1.633 | 0.980 | 1.075 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 1.671 | 1.388 | 2.677 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.904 | 1.312 | 1.004 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 1.021 | 1.253 | 1.014 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1.011 | 0.942 | 1.008 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 1.208 | 1.085 | 1.023 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1.523 | 0.110 | 2.377 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.572 | 0.790 | 1.953 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.875 | 0.848 | 1.955 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.541 | 1.068 | 1.057 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 2.378 | 1.156 | 2.487 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.195 | 1.247 | 3.390 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.722 | 0.385 | 2.891 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.846 | 0.415 | 1.593 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1.506 | 0.763 | 1.059 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 2.155 | 1.547 | 1.305 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.342 | 0.120 | 4.899 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-cpp-j16 | xs-cpp-j2 | xs-cpp-j8 |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 11.093 | 4.189 | 4.177 | 4.500 | 4.161 | 4.322 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 10.177 | 12.327 | 4.676 | 29.720 | 12.163 | 27.427 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 68.543 | 20.576 | 39.739 | 50.708 | 39.855 | 21.718 |
| `real-congress.fresh.mac-apollo.sender.warm` | 27.241 | 6.844 | 16.799 | 11.267 | 8.932 | 7.049 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp-j16: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7n
- xs-cpp-j1: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nk
- xs-cpp: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/0
