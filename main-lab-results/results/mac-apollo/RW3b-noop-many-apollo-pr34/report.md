# RW3b-noop-many-apollo-pr34

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. No-ops of many files, where NT1021 saw rsync pull real-psample in 75.7 s against xs-cpp 151.6 s; -j1 arms for a per-core comparison.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T204057Z-RW3b-noop-many-apollo-pr34.
- Valid blocks: 6. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.954 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1 | 1.041 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 1 | 0.567 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1 | 0.935 |  |  | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.303 [0.244, 0.376] | 0.303 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 2 | 0.603 [0.373, 0.974] | 0.603 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 2 | 0.206 [0.086, 0.491] | 0.206 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 2 | 0.464 [0.443, 0.486] | 0.464 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.231 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1 | 0.559 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 1 | 0.209 |  |  | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1 | 0.477 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.157 [0.152, 0.162] | 0.157 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 2 | 0.744 [0.597, 0.927] | 0.744 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 2 | 0.098 [0.062, 0.155] | 0.098 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 2 | 0.710 [0.464, 1.087] | 0.710 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 3.483 | 4.920 | 0.955 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1.195 | 4.865 | 1.042 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 1.783 | 11.478 | 0.567 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1.092 | 10.681 | 0.934 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 1.002 [0.676, 1.486] | 4.283 [4.042, 4.540] | 0.303 [0.244, 0.376] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.696 [0.280, 1.728] | 4.247 [3.805, 4.741] | 0.603 [0.374, 0.974] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 1.246 [0.260, 5.971] | 11.625 [10.181, 13.275] | 0.206 [0.086, 0.492] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.535 [0.491, 0.582] | 11.654 [10.304, 13.179] | 0.464 [0.443, 0.486] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 0.836 | 1.097 | 0.227 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.539 | 1.001 | 0.556 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 0.758 | 30.125 | 0.204 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.488 | 24.462 | 0.475 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 0.475 [0.193, 1.172] | 1.005 [0.907, 1.113] | 0.157 [0.152, 0.161] |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.711 [0.356, 1.419] | 0.997 [0.821, 1.211] | 0.744 [0.597, 0.927] |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 0.677 [0.089, 5.181] | 21.211 [19.496, 23.076] | 0.097 [0.061, 0.155] |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.674 [0.495, 0.917] | 21.210 [19.523, 23.043] | 0.710 [0.464, 1.087] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-rs | xs-rs-j1 |
|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | 32.066 | 30.602 | 33.381 | 18.192 | 29.973 |
| `real-psample.noop.mac-apollo.sender.warm` | 80.908 | 24.503 | 48.806 | 16.655 | 37.573 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | 16.475 | 3.805 | 9.209 | 3.444 | 7.864 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | 73.043 | 11.450 | 54.352 | 7.122 | 51.891 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 0.0241 | 8 | 10 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.0534 | 28 | 37 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 0.0969 | 87 | 115 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.0051 | 8 | 8 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 0.0033 | 8 | 8 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.0244 | 8 | 10 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 0.0512 | 26 | 34 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.0474 | 23 | 29 |
