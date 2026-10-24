# RW8a-delta-wan-apollo

Over a 20 ms round trip, rsync is at least 5% faster than xs in some delta cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T185557Z-RW8a-delta-wan-apollo.
- Valid blocks: 16. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 1.283 [0.986, 1.669] | 1.283 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.188 [0.946, 1.491] | 1.188 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 3.565 [2.672, 4.755] | 3.565 | 0.5000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.808 [0.005, 130.477] | 0.808 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.677 [0.003, 139.236] | 0.677 | 1.0000 | too few blocks |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 1.434 [0.734, 2.803] | 1.434 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 1.194 [0.900, 1.583] | 1.194 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.162 [1.106, 1.220] | 1.162 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 3.824 [3.234, 4.521] | 3.824 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.556 [0.023, 104.677] | 1.556 | 0.5000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.013 [0.672, 1.527] | 1.013 | 1.0000 | too few blocks |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 2.777 [0.030, 255.572] | 2.777 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.020 [1.939, 2.104] | 2.020 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.212 [1.106, 1.329] | 1.212 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 6.774 [4.972, 9.228] | 6.774 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 1.598 [0.095, 26.792] | 1.598 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.683 [0.148, 3.162] | 0.683 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 1.210 [0.077, 18.942] | 1.210 | 1.0000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.119 [1.296, 3.465] | 2.119 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.102 [0.549, 2.211] | 1.102 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 2 | 6.668 [4.080, 10.897] | 6.668 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.508 [0.072, 3.607] | 0.508 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.490 [0.006, 42.327] | 0.490 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2 | 0.642 [0.594, 0.694] | 0.642 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.505 [0.757, 2.992] | 1.001 [0.975, 1.027] | 1.313 [1.041, 1.655] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.210 [0.687, 2.130] | 1.000 [0.836, 1.196] | 1.203 [0.974, 1.486] |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 1.443 [0.583, 3.575] | 5.985 [5.897, 6.074] | 3.758 [2.951, 4.785] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.680 [0.613, 4.599] | 1.012 [0.854, 1.198] | 0.818 [0.005, 128.221] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.217 [0.470, 3.150] | 0.987 [0.894, 1.090] | 0.686 [0.003, 137.663] |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 1.211 [0.102, 14.408] | 7.645 [5.262, 11.107] | 1.454 [0.774, 2.732] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.333 [0.736, 2.413] | 0.986 [0.958, 1.015] | 1.206 [0.859, 1.695] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.255 [0.972, 1.621] | 0.995 [0.897, 1.102] | 1.172 [1.135, 1.209] |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 1.353 [0.190, 9.612] | 5.928 [5.374, 6.540] | 4.036 [3.366, 4.839] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.168 [1.003, 1.360] | 0.999 [0.993, 1.005] | 1.526 [0.030, 78.025] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.013 [1.006, 1.020] | 1.003 [0.972, 1.036] | 1.017 [0.717, 1.444] |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 1.248 [0.562, 2.771] | 7.713 [7.214, 8.246] | 2.797 [0.032, 244.661] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.513 [1.227, 1.866] | 1.004 [0.993, 1.016] | 2.041 [1.838, 2.267] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.106 [1.069, 1.145] | 1.001 [0.804, 1.245] | 1.217 [1.110, 1.334] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 1.337 [0.174, 10.256] | 5.999 [5.801, 6.204] | 6.957 [5.141, 9.415] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.569 [1.480, 1.664] | 1.010 [0.809, 1.262] | 1.573 [0.090, 27.374] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.126 [0.977, 1.298] | 0.998 [0.684, 1.458] | 0.681 [0.140, 3.310] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 2.675 [2.426, 2.949] | 5.458 [4.535, 6.569] | 1.210 [0.077, 18.978] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.445 [1.059, 1.973] | 0.989 [0.966, 1.013] | 2.297 [1.692, 3.119] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.135 [0.902, 1.428] | 0.987 [0.962, 1.012] | 1.178 [1.068, 1.300] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 1.553 [0.664, 3.631] | 5.951 [5.524, 6.412] | 7.312 [5.456, 9.799] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.078 [0.883, 1.317] | 1.007 [0.923, 1.099] | 0.506 [0.071, 3.584] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.042 [0.996, 1.090] | 0.993 [0.892, 1.105] | 0.491 [0.006, 40.461] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 2.699 [2.221, 3.280] | 5.918 [3.702, 9.461] | 0.644 [0.618, 0.670] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs | xs-rs-W |
|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | 0.977 | 1.253 | 1.160 | 3.482 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | 2.527 | 2.042 | 1.712 | 3.625 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | 0.918 | 1.096 | 1.066 | 3.510 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | 1.500 | 2.335 | 1.519 | 4.166 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.829 | 3.693 | 2.217 | 12.387 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 4.960 | 7.926 | 3.389 | 6.003 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.856 | 3.934 | 2.044 | 12.375 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 8.732 | 4.435 | 4.280 | 5.605 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0293 | 10 | 13 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0253 | 8 | 10 |
| `hs-16x256m.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0321 | 12 | 15 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.5659 | 2876 | 3854 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.5928 | 3156 | 4228 |
| `hs-16x256m.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.0746 | 52 | 69 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0314 | 11 | 14 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0054 | 8 | 8 |
| `hs-16x256m.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0186 | 8 | 8 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.4684 | 1971 | 2641 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.0457 | 21 | 28 |
| `hs-16x256m.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.5033 | 2276 | 3049 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0045 | 8 | 8 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0102 | 8 | 8 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0344 | 13 | 17 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.3138 | 886 | 1187 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.1705 | 263 | 352 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.3061 | 843 | 1130 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0547 | 29 | 39 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0775 | 56 | 75 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0547 | 29 | 38 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.2182 | 430 | 575 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.4962 | 2212 | 2964 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.0087 | 8 | 8 |
