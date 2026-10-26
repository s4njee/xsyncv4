# JC1-xs-cpp-workers-apollo

Some worker count is at least 5% faster than xs-c++'s default of 4 in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T102540Z-JC1-xs-cpp-workers-apollo.
- Valid blocks: 12. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.964 [0.838, 1.110] | 0.972 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 3 | 0.976 [0.889, 1.072] | 0.980 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.983 [0.848, 1.141] | 0.988 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 3 | 1.018 [0.853, 1.215] | 1.025 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 3 | 2.593 [2.266, 2.966] | 2.607 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 1.340 [0.039, 46.597] | 1.246 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 3 | 1.246 [0.480, 3.232] | 1.182 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 3 | 1.645 [0.575, 4.710] | 1.722 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 3 | 1.690 [0.553, 5.165] | 1.755 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3 | 2.339 [0.168, 32.611] | 2.317 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 1.637 [0.785, 3.415] | 1.706 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 3 | 1.277 [0.394, 4.141] | 1.309 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 1.028 [0.942, 1.122] | 1.032 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 3 | 1.268 [0.273, 5.893] | 1.234 | 0.7500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 3.434 [3.137, 3.760] | 3.425 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 1.931 [1.148, 3.250] | 1.888 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 3 | 1.593 [0.738, 3.436] | 1.531 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 3 | 1.070 [0.774, 1.478] | 1.060 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 3 | 1.392 [0.714, 2.714] | 1.443 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 4.162 [3.040, 5.697] | 4.116 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.899 [0.858, 0.942] | 1.007 [0.752, 1.349] | 0.993 [0.984, 1.003] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.945 [0.895, 0.998] | 1.101 [0.759, 1.596] | 1.006 [0.968, 1.045] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.220 [1.130, 1.316] | 1.088 [1.040, 1.138] | 1.010 [0.963, 1.060] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 1.598 [1.524, 1.675] | 1.051 [0.758, 1.457] | 1.050 [0.996, 1.108] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 1.631 [1.529, 1.739] | 1.504 [1.204, 1.877] | 2.693 [2.635, 2.752] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.922 [0.864, 0.984] | 1.233 [0.966, 1.575] | 1.006 [0.990, 1.023] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.966 [0.856, 1.090] | 1.107 [0.841, 1.458] | 1.003 [0.978, 1.028] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1.011 [0.984, 1.039] | 0.951 [0.874, 1.035] | 1.005 [1.001, 1.010] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 1.105 [0.907, 1.346] | 1.061 [1.009, 1.115] | 1.020 [1.014, 1.026] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1.569 [1.441, 1.708] | 0.109 [0.106, 0.112] | 2.427 [2.272, 2.592] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.531 [0.375, 0.753] | 0.916 [0.665, 1.262] | 1.653 [0.791, 3.455] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.720 [0.415, 1.250] | 0.889 [0.730, 1.083] | 1.287 [0.397, 4.175] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.473 [1.234, 1.759] | 0.983 [0.801, 1.207] | 1.029 [0.943, 1.123] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 1.845 [1.023, 3.328] | 1.078 [0.925, 1.255] | 1.272 [0.271, 5.972] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.302 [0.923, 1.837] | 1.212 [1.134, 1.296] | 3.488 [3.196, 3.806] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.679 [0.594, 0.775] | 0.539 [0.170, 1.706] | 2.102 [1.059, 4.174] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.796 [0.695, 0.912] | 0.725 [0.214, 2.454] | 1.398 [1.027, 1.902] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 1.527 [1.452, 1.607] | 1.210 [0.307, 4.768] | 0.968 [0.787, 1.190] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 2.046 [1.792, 2.335] | 1.850 [0.744, 4.598] | 1.079 [0.716, 1.626] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.294 [1.195, 1.402] | 0.154 [0.056, 0.424] | 4.679 [3.879, 5.643] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-cpp-j16 | xs-cpp-j2 | xs-cpp-j8 |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 11.136 | 4.295 | 4.142 | 4.374 | 4.192 | 4.224 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 14.848 | 6.347 | 8.503 | 10.728 | 7.909 | 10.442 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 83.061 | 24.187 | 39.595 | 30.661 | 30.896 | 24.873 |
| `real-congress.fresh.mac-apollo.sender.warm` | 27.742 | 6.666 | 12.875 | 9.281 | 10.618 | 7.130 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0566 | 31 | 41 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.0378 | 15 | 20 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0598 | 35 | 45 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 0.0711 | 48 | 63 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 0.0542 | 29 | 38 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 1.4287 | 18319 | 24552 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.3837 | 1324 | 1773 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 0.4235 | 1612 | 2159 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 0.4497 | 1817 | 2434 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1.0607 | 10097 | 13532 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.2960 | 789 | 1056 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j2 | 0.4735 | 2014 | 2699 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0352 | 14 | 17 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j16 | 0.6185 | 3436 | 4604 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.0365 | 14 | 19 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.2095 | 396 | 531 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.3095 | 862 | 1154 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j8 | 0.1303 | 155 | 207 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j16 | 0.2687 | 650 | 871 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.1264 | 146 | 195 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp-j16: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7n
- xs-cpp-j1: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nk
- xs-cpp-j8: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nk
- xs-cpp: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/0
