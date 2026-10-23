# RW2-checksum-noop-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. No-ops with --checksum, where every file is read and hashed at both ends. xs-rs has no -c, so it sits out.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162410Z-RW2-checksum-noop-apollo, 20261023T040631Z-RW2-checksum-noop-apollo.
- Valid blocks: 12. Voided block attempts: 18.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.424 [0.308, 0.583] | 0.428 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.376 [0.231, 0.613] | 0.376 | 0.2500 | too few blocks |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.431 [0.390, 0.476] | 0.432 | 0.2500 | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.315 [0.233, 0.424] | 0.319 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 1.650 [1.591, 1.711] | 3.812 [3.610, 4.025] | 0.422 [0.305, 0.586] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 1.641 [1.451, 1.855] | 3.036 [2.024, 4.553] | 0.373 [0.225, 0.620] |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 1.671 [1.566, 1.784] | 3.968 [3.481, 4.524] | 0.431 [0.389, 0.477] |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 1.287 [1.074, 1.541] | 3.812 [3.630, 4.004] | 0.314 [0.232, 0.424] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp |
|---|---|---|
| `real-congress.noop.apollo-mac.receiver.warm` | 19.487 | 8.263 |
| `real-congress.noop.mac-apollo.sender.warm` | 17.924 | 6.736 |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | 144.6 | 62.329 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | 223.6 | 70.326 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 0.1283 | 150 | 201 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.1967 | 350 | 468 |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0403 | 17 | 22 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 0.1203 | 132 | 177 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
