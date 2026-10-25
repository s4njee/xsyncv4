# LT1-latency20-apollo

Over a 20 ms round trip, rsync is at least 5% faster than xs in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T160502Z-LT1-latency20-apollo.
- Valid blocks: 30. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.747 [0.656, 0.851] | 0.749 | 0.2500 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.602 [0.595, 0.609] | 0.602 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.704 [0.468, 1.060] | 0.694 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.635 [0.518, 0.779] | 0.628 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.762 [0.718, 0.809] | 0.765 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.738 [0.564, 0.965] | 0.734 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.694 [0.605, 0.797] | 0.697 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.620 [0.559, 0.687] | 0.618 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.238 [0.082, 0.689] | 0.245 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.286 [0.157, 0.520] | 0.289 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.387 [0.084, 1.784] | 0.365 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.233 [0.035, 1.545] | 0.212 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.433 [0.289, 0.647] | 0.425 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.277 [0.160, 0.479] | 0.269 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.183 [0.145, 0.231] | 0.184 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.148 [0.128, 0.170] | 0.149 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.478 [0.362, 0.632] | 0.482 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.280 [0.218, 0.361] | 0.278 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.139 [0.110, 0.175] | 0.140 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.117 [0.074, 0.185] | 0.117 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1.631 [1.230, 2.163] | 0.988 [0.936, 1.043] | 0.720 [0.680, 0.763] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.952 [0.647, 1.402] | 0.978 [0.946, 1.010] | 0.582 [0.545, 0.623] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.991 [0.853, 1.152] | 1.004 [0.930, 1.084] | 0.704 [0.470, 1.057] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.954 [0.773, 1.177] | 1.199 [1.061, 1.354] | 0.628 [0.535, 0.736] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.876 [1.733, 2.032] | 1.054 [0.963, 1.153] | 0.738 [0.646, 0.844] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.138 [0.883, 1.468] | 1.424 [1.144, 1.772] | 0.717 [0.554, 0.929] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.122 [0.915, 1.377] | 1.524 [1.497, 1.551] | 0.696 [0.603, 0.804] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.088 [0.809, 1.464] | 2.155 [1.765, 2.632] | 0.621 [0.566, 0.680] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.565 [0.259, 1.232] | 0.672 [0.611, 0.738] | 0.237 [0.082, 0.681] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.588 [0.326, 1.059] | 2.150 [0.492, 9.388] | 0.285 [0.157, 0.517] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.616 [0.387, 0.981] | 12.532 [11.571, 13.572] | 0.290 [0.128, 0.659] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.789 [0.403, 1.546] | 6.353 [5.900, 6.841] | 0.160 [0.097, 0.264] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 1.942 [1.592, 2.369] | 2.811 [1.477, 5.348] | 0.426 [0.280, 0.648] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 1.122 [0.859, 1.466] | 5.176 [5.140, 5.212] | 0.269 [0.153, 0.470] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 1.097 [0.925, 1.300] | 3.420 [3.240, 3.609] | 0.182 [0.145, 0.230] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.092 [1.035, 1.152] | 8.333 [7.967, 8.715] | 0.148 [0.128, 0.170] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.666 [1.318, 2.107] | 2.535 [1.635, 3.931] | 0.472 [0.357, 0.625] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.033 [0.897, 1.190] | 4.292 [3.712, 4.963] | 0.270 [0.206, 0.355] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.770 [0.561, 1.057] | 2.835 [2.287, 3.513] | 0.138 [0.108, 0.175] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.837 [0.637, 1.101] | 5.927 [5.491, 6.397] | 0.115 [0.073, 0.183] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.980 | 0.732 | 0.590 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.977 | 0.688 | 0.621 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | 1.086 | 0.828 | 0.802 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | 1.153 | 0.801 | 0.715 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 153.3 | 36.524 | 43.894 |
| `real-congress.fresh.mac-apollo.sender.warm` | 46.617 | 18.018 | 10.879 |
| `real-congress.noop.apollo-mac.receiver.warm` | 7.906 | 3.422 | 2.189 |
| `real-congress.noop.mac-apollo.sender.warm` | 10.625 | 1.945 | 1.570 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | 10.159 | 4.861 | 2.847 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | 15.310 | 2.124 | 1.790 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0523 | 27 | 35 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.0046 | 8 | 8 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.1647 | 246 | 329 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.0819 | 63 | 83 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0241 | 8 | 9 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.1082 | 108 | 143 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.0554 | 30 | 39 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.0414 | 18 | 23 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.4273 | 1641 | 2199 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.2407 | 522 | 699 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.6157 | 3404 | 4562 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.7608 | 5197 | 6964 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 0.1620 | 238 | 318 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.2205 | 439 | 587 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.0937 | 81 | 108 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.0570 | 32 | 42 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.1120 | 115 | 153 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.1018 | 96 | 127 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.0927 | 80 | 106 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.1851 | 310 | 414 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/0
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
