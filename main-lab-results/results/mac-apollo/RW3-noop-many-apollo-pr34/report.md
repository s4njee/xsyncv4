# RW3-noop-many-apollo-pr34

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. No-ops of many files, where NT1021 saw rsync pull real-psample in 75.7 s against xs-cpp 151.6 s; -j1 arms for a per-core comparison.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T092441Z-RW3-noop-many-apollo-pr34.
- Valid blocks: 5. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.721 [0.063, 8.301] | 0.721 | 0.5000 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 2 | 1.276 [0.386, 4.212] | 1.276 | 0.5000 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 2 | 0.490 [0.265, 0.906] | 0.490 | 0.5000 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 2 | 0.915 [0.331, 2.527] | 0.915 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.358 |  |  | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 1 | 0.525 |  |  | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 1 | 0.211 |  |  | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 1 | 0.461 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.169 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1 | 0.380 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 1 | 0.174 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1 | 0.375 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.177 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 1 | 0.697 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 1 | 0.083 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 1 | 0.680 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 2.580 [0.148, 44.826] | 4.613 [4.253, 5.003] | 0.719 [0.062, 8.331] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1.497 [0.653, 3.433] | 4.649 [4.397, 4.915] | 1.277 [0.387, 4.214] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 1.720 [1.087, 2.723] | 10.231 [9.653, 10.845] | 0.488 [0.265, 0.899] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1.104 [0.398, 3.066] | 10.561 [7.060, 15.797] | 0.914 [0.331, 2.525] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 1.069 | 4.313 | 0.358 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.589 | 4.307 | 0.525 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 1.301 | 11.841 | 0.211 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.489 | 11.899 | 0.440 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 0.658 | 1.075 | 0.165 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.459 | 0.995 | 0.377 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 0.755 | 29.817 | 0.169 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.481 | 21.821 | 0.372 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 0.449 | 0.998 | 0.177 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.607 | 0.988 | 0.697 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 0.525 | 21.107 | 0.083 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.598 | 21.040 | 0.680 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-rs | xs-rs-j1 |
|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | 36.215 | 26.094 | 46.204 | 17.748 | 33.119 |
| `real-psample.noop.mac-apollo.sender.warm` | 81.481 | 29.208 | 42.784 | 17.179 | 37.532 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | 17.137 | 2.905 | 6.510 | 2.975 | 6.431 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | 76.638 | 13.569 | 53.382 | 6.362 | 52.115 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 0.2720 | 667 | 892 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.1329 | 161 | 215 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 0.0683 | 44 | 59 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.1131 | 117 | 156 |
