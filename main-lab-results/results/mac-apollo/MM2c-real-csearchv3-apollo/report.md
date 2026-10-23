# MM2c-real-csearchv3-apollo

On the user's csearchv3 tree (14 GB, 1,345,908 files, 472,330 directories), rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162409Z-MM2c-real-csearchv3-apollo, 20261023T040630Z-MM2c-real-csearchv3-apollo.
- Valid blocks: 19. Voided block attempts: 36.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-cpp | 4 | 0.286 [0.268, 0.306] | 0.286 | 0.1250 | too few blocks |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs | 4 | 0.287 [0.273, 0.301] | 0.289 | 0.1250 | too few blocks |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.323 [0.275, 0.379] | 0.326 | 0.2500 | too few blocks |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.289 [0.226, 0.370] | 0.288 | 0.2500 | too few blocks |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 4 | 0.597 [0.454, 0.785] | 0.558 | 0.1250 | too few blocks |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-rs | 4 | 0.441 [0.410, 0.475] | 0.437 | 0.1250 | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.297 [0.266, 0.331] | 0.297 | 0.5000 | too few blocks |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs | 2 | 0.267 [0.158, 0.451] | 0.267 | 0.5000 | too few blocks |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 4 | 0.522 [0.490, 0.556] | 0.519 | 0.1250 | too few blocks |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs | 4 | 0.503 [0.477, 0.531] | 0.496 | 0.1250 | too few blocks |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.250 [0.159, 0.392] | 0.250 | 0.5000 | too few blocks |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.216 [0.134, 0.348] | 0.216 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.721 [0.677, 0.767] | 2.522 [2.508, 2.535] | 0.286 [0.267, 0.306] |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs | 0.634 [0.600, 0.671] | 7.673 [7.510, 7.840] | 0.287 [0.273, 0.301] |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-cpp | 0.689 [0.647, 0.733] | 6.041 [5.636, 6.475] | 0.298 [0.243, 0.364] |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs | 0.651 [0.585, 0.725] | 10.894 [8.420, 14.094] | 0.252 [0.205, 0.310] |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 1.985 [1.850, 2.130] | 4.227 [3.754, 4.759] | 0.596 [0.452, 0.784] |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-rs | 1.413 [1.368, 1.460] | 13.485 [11.960, 15.205] | 0.440 [0.410, 0.473] |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 0.986 [0.855, 1.138] | 4.100 [3.909, 4.300] | 0.297 [0.263, 0.335] |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs | 0.863 [0.693, 1.073] | 11.999 [11.171, 12.888] | 0.267 [0.158, 0.451] |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.214 [1.159, 1.271] | 2.965 [2.668, 3.295] | 0.521 [0.488, 0.555] |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.994 [0.939, 1.052] | 9.049 [8.149, 10.047] | 0.502 [0.475, 0.530] |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.783 [0.290, 2.109] | 3.389 [3.051, 3.763] | 0.239 [0.231, 0.247] |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.729 [0.637, 0.833] | 8.686 [7.456, 10.119] | 0.215 [0.131, 0.355] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | 527.1 | 150.8 | 151.2 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | 297.4 | 96.012 | 85.984 |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | 41.076 | 24.518 | 18.125 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | 85.570 | 25.412 | 22.849 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | 104.1 | 54.345 | 52.409 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | 148.3 | 37.040 | 32.067 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0420 | 18 | 24 |
| `real-csearchv3.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0312 | 11 | 14 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-cpp | 0.0651 | 40 | 53 |
| `real-csearchv3.fresh.mac-apollo.sender.warm` | xs-rs | 0.0998 | 92 | 122 |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-cpp | 0.1722 | 269 | 359 |
| `real-csearchv3.noop.apollo-mac.receiver.warm` | xs-rs | 0.0459 | 21 | 28 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-cpp | 0.0122 | 8 | 8 |
| `real-csearchv3.noop.mac-apollo.sender.warm` | xs-rs | 0.0584 | 33 | 44 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0402 | 17 | 22 |
| `real-csearchv3.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.0338 | 13 | 16 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.0503 | 25 | 33 |
| `real-csearchv3.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.0529 | 28 | 36 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
