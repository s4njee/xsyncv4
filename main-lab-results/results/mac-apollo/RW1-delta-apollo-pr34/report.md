# RW1-delta-apollo-pr34

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Delta updates of large files: a 4 KiB edit in a file (update-1pct), and a file grown at its end (append-1pct).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T092441Z-RW1-delta-apollo-pr34.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.281 [2.211, 2.353] | 2.281 | 0.2500 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.223 [1.111, 1.346] | 1.219 | 0.2500 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 1.117 [0.686, 1.818] | 1.135 | 0.5000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.915 [0.495, 1.689] | 0.930 | 0.7500 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.528 [2.340, 2.732] | 2.537 | 0.2500 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.252 [1.215, 1.289] | 1.252 | 0.2500 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.820 [0.356, 1.885] | 0.819 | 0.5000 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.955 [0.169, 5.415] | 0.886 | 1.0000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.227 [1.998, 2.482] | 2.222 | 0.2500 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.232 [1.130, 1.343] | 1.230 | 0.2500 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 1.576 [0.036, 68.048] | 1.606 | 0.7500 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.423 [0.885, 2.289] | 1.396 | 0.2500 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.494 [2.358, 2.639] | 2.488 | 0.2500 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.213 [1.178, 1.249] | 1.212 | 0.2500 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 1.007 [0.452, 2.243] | 1.054 | 1.0000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.039 [0.017, 63.262] | 1.054 | 0.7500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.389 [1.358, 1.420] | 0.997 [0.955, 1.040] | 2.305 [2.233, 2.379] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.078 [0.982, 1.184] | 0.994 [0.977, 1.012] | 1.228 [1.111, 1.357] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.483 [1.371, 1.605] | 1.002 [0.978, 1.027] | 1.047 [0.492, 2.229] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.068 [0.994, 1.148] | 0.991 [0.936, 1.049] | 0.915 [0.497, 1.686] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.280 [1.228, 1.333] | 0.988 [0.962, 1.014] | 2.552 [2.362, 2.757] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.125 [1.084, 1.168] | 1.011 [0.984, 1.040] | 1.255 [1.220, 1.292] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.098 [1.045, 1.154] | 1.000 [0.952, 1.051] | 0.786 [0.395, 1.564] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.031 [0.980, 1.085] | 0.997 [0.974, 1.021] | 0.955 [0.168, 5.419] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.543 [1.376, 1.729] | 0.993 [0.941, 1.048] | 2.282 [2.044, 2.547] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.129 [1.061, 1.202] | 1.013 [0.981, 1.046] | 1.245 [1.124, 1.378] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.567 [1.471, 1.670] | 0.994 [0.967, 1.022] | 1.911 [0.042, 87.610] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.190 [1.123, 1.262] | 0.989 [0.953, 1.026] | 1.526 [0.658, 3.540] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.482 [1.437, 1.528] | 0.992 [0.939, 1.047] | 2.586 [2.445, 2.735] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.183 [1.131, 1.237] | 1.002 [0.975, 1.031] | 1.224 [1.184, 1.265] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.206 [0.976, 1.491] | 1.010 [0.982, 1.039] | 1.000 [0.455, 2.199] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.091 [0.999, 1.192] | 0.992 [0.930, 1.057] | 1.040 [0.017, 63.305] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | 4.583 | 10.452 | 5.603 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | 15.410 | 17.209 | 14.098 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | 4.382 | 11.079 | 5.484 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | 18.359 | 15.045 | 17.542 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.395 | 3.106 | 1.718 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 3.913 | 6.166 | 5.570 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.330 | 3.318 | 1.613 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 4.615 | 4.646 | 4.793 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0126 | 8 | 8 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0386 | 16 | 20 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.1962 | 348 | 465 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.2469 | 550 | 736 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0312 | 11 | 14 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0119 | 8 | 8 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.3352 | 1011 | 1354 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.6983 | 4378 | 5867 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0436 | 20 | 25 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0347 | 13 | 17 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.5159 | 20621 | 27637 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.1914 | 331 | 443 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0227 | 8 | 9 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0118 | 8 | 8 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.3224 | 935 | 1252 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.6542 | 24557 | 32913 |
