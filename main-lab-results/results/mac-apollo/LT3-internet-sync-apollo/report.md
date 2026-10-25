# LT3-internet-sync-apollo

Over a 40 ms, 1 Gb/s path, xs-rs -z at its automatic level is at least as fast as rsync -az and xs-c++ -z.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync-z`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T025625Z-LT3-internet-sync-apollo.
- Valid blocks: 18. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 3 | 0.679 [0.539, 0.857] | 0.683 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 3 | 0.623 [0.498, 0.780] | 0.631 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.704 [0.617, 0.803] | 0.705 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | rsync | 3 | 0.988 [0.916, 1.066] | 0.987 | 0.7500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 3 | 0.920 [0.737, 1.147] | 0.930 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 3 | 0.780 [0.614, 0.991] | 0.782 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.670 [0.439, 1.023] | 0.668 | 0.2500 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | rsync | 3 | 0.904 [0.617, 1.323] | 0.916 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-z | 3 | 0.338 [0.204, 0.560] | 0.332 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z | 3 | 0.393 [0.129, 1.200] | 0.369 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.333 [0.288, 0.385] | 0.334 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 0.961 [0.663, 1.395] | 0.970 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-z | 3 | 0.407 [0.100, 1.650] | 0.381 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z | 3 | 0.344 [0.074, 1.601] | 0.327 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.325 [0.095, 1.116] | 0.308 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 1.377 [0.652, 2.910] | 1.338 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 3 | 0.239 [0.192, 0.296] | 0.240 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 3 | 0.167 [0.132, 0.212] | 0.165 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.163 [0.155, 0.172] | 0.163 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | rsync | 3 | 0.960 [0.845, 1.092] | 0.967 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 3 | 0.115 [0.088, 0.149] | 0.116 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 3 | 0.105 [0.080, 0.138] | 0.105 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.097 [0.080, 0.116] | 0.096 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | rsync | 3 | 1.016 [0.946, 1.092] | 1.018 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 1.583 [1.094, 2.288] | 1.094 [0.922, 1.298] | 0.661 [0.532, 0.821] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 1.046 [0.835, 1.312] | 1.360 [1.216, 1.519] | 0.608 [0.489, 0.755] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.055 [0.840, 1.325] | 1.290 [1.197, 1.390] | 0.672 [0.520, 0.869] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | rsync | 0.959 [0.889, 1.035] | 0.989 [0.950, 1.030] | 0.986 [0.933, 1.042] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 1.148 [0.865, 1.523] | 2.062 [1.128, 3.768] | 0.887 [0.759, 1.038] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 1.037 [0.795, 1.353] | 2.160 [1.834, 2.544] | 0.770 [0.621, 0.954] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.931 [0.617, 1.404] | 2.179 [1.956, 2.428] | 0.673 [0.452, 1.002] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | rsync | 0.892 [0.631, 1.262] | 0.997 [0.973, 1.022] | 0.909 [0.635, 1.301] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-z | 0.963 [0.910, 1.020] | 1.929 [1.190, 3.128] | 0.333 [0.196, 0.566] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z | 1.014 [0.486, 2.115] | 3.507 [3.096, 3.974] | 0.388 [0.124, 1.213] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.813 [0.675, 0.981] | 5.487 [4.764, 6.319] | 0.331 [0.286, 0.383] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.170 [0.870, 1.573] | 3.129 [2.816, 3.477] | 0.961 [0.663, 1.391] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-z | 0.900 [0.445, 1.823] | 5.192 [3.092, 8.720] | 0.310 [0.108, 0.894] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z | 1.010 [0.623, 1.636] | 6.652 [5.743, 7.705] | 0.250 [0.119, 0.526] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.029 [0.535, 1.977] | 6.462 [5.824, 7.170] | 0.259 [0.126, 0.530] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.259 [0.834, 1.899] | 0.988 [0.885, 1.104] | 1.335 [0.813, 2.190] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 1.561 [1.465, 1.664] | 1.652 [1.437, 1.900] | 0.234 [0.187, 0.291] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 0.928 [0.747, 1.153] | 4.181 [3.622, 4.827] | 0.162 [0.128, 0.205] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.933 [0.764, 1.140] | 4.260 [3.818, 4.753] | 0.158 [0.151, 0.165] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | rsync | 0.935 [0.834, 1.048] | 0.944 [0.783, 1.139] | 0.961 [0.847, 1.090] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 0.884 [0.805, 0.970] | 2.762 [2.462, 3.098] | 0.114 [0.087, 0.148] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 1.020 [0.823, 1.264] | 5.807 [5.405, 6.240] | 0.104 [0.079, 0.136] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.035 [0.957, 1.120] | 5.818 [5.483, 6.174] | 0.096 [0.079, 0.115] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | rsync | 1.007 [0.952, 1.064] | 1.006 [0.941, 1.075] | 1.016 [0.946, 1.092] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs-cpp-z | xs-rs | xs-rs-z |
|---|---|---|---|---|---|
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | 1.862 | 1.885 | 1.281 | 1.327 | 1.174 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | 1.789 | 1.979 | 1.820 | 1.327 | 1.544 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 84.579 | 87.975 | 29.717 | 29.296 | 34.554 |
| `real-congress.fresh.mac-apollo.sender.warm` | 45.288 | 32.880 | 13.386 | 10.696 | 11.300 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | 15.270 | 15.900 | 3.793 | 2.595 | 2.656 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | 20.624 | 20.297 | 2.330 | 1.962 | 2.130 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 0.0935 | 81 | 108 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 0.0905 | 76 | 101 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0531 | 28 | 36 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | rsync | 0.0305 | 11 | 14 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 0.0889 | 73 | 98 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 0.0963 | 86 | 114 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.1702 | 262 | 351 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | rsync | 0.1535 | 214 | 286 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-z | 0.2036 | 375 | 501 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z | 0.4496 | 1817 | 2434 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0583 | 33 | 43 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.1497 | 204 | 272 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-z | 0.5633 | 2849 | 3818 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z | 0.6195 | 3446 | 4618 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.4962 | 2212 | 2964 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.3012 | 816 | 1093 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-z | 0.0873 | 71 | 94 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs-z | 0.0962 | 85 | 114 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0210 | 8 | 8 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | rsync | 0.0517 | 26 | 35 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-z | 0.1062 | 104 | 138 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs-z | 0.1095 | 110 | 147 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.0740 | 52 | 68 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | rsync | 0.0289 | 10 | 13 |

## Voided attempts

- rsync-z: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/
- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp-z: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs-z: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
