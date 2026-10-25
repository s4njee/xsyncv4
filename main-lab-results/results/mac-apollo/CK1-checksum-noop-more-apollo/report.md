# CK1-checksum-noop-more-apollo

rsync -c is at least 5% faster than xs -c at a no-op on a tree of large files.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T065118Z-CK1-checksum-noop-more-apollo.
- Valid blocks: 6. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.637 |  |  | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 0.528 |  |  | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.620 |  |  | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp-j8 | 1 | 0.534 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.472 [0.349, 0.639] | 0.472 | 0.5000 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 2 | 0.338 [0.149, 0.766] | 0.338 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.284 [0.075, 1.074] | 0.284 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j8 | 2 | 0.238 [0.158, 0.359] | 0.238 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1.170 | 1.114 | 0.624 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.206 | 1.443 | 0.520 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1.116 | 0.995 | 0.628 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp-j8 | 1.227 | 1.122 | 0.534 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 1.700 [1.500, 1.926] | 4.067 [2.350, 7.039] | 0.472 [0.348, 0.640] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 2.050 [1.411, 2.977] | 4.306 [4.070, 4.556] | 0.337 [0.148, 0.767] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 1.098 [0.507, 2.375] | 3.991 [3.896, 4.088] | 0.284 [0.075, 1.075] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j8 | 1.324 [1.061, 1.652] | 4.077 [4.076, 4.079] | 0.238 [0.158, 0.359] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j8 |
|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | 5.268 | 3.355 | 2.780 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 3.147 | 1.953 | 1.681 |
| `real-psample.noop.apollo-mac.receiver.warm` | 126.7 | 59.829 | 42.814 |
| `real-psample.noop.mac-apollo.sender.warm` | 208.2 | 59.226 | 49.660 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0338 | 13 | 16 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0911 | 77 | 102 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 0.1479 | 199 | 265 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j8 | 0.0457 | 21 | 28 |
