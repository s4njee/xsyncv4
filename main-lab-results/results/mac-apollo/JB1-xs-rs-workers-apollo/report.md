# JB1-xs-rs-workers-apollo

Some worker count is at least 5% faster than xs-rs's default of 8 in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T013958Z-JB1-xs-rs-workers-apollo.
- Valid blocks: 12. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.979 [0.839, 1.143] | 0.985 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 3 | 0.926 [0.759, 1.128] | 0.926 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 0.957 [0.725, 1.263] | 0.957 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 3 | 1.001 [0.776, 1.291] | 0.993 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 3 | 2.952 [2.481, 3.512] | 2.975 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.990 [0.087, 11.305] | 1.059 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 3 | 1.660 [0.469, 5.872] | 1.755 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 1.599 [0.380, 6.733] | 1.605 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 3 | 0.939 [0.077, 11.377] | 0.965 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3 | 2.118 [1.216, 3.690] | 2.144 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 1.686 [1.475, 1.928] | 1.680 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 3 | 1.296 [0.910, 1.847] | 1.282 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 1.187 [0.498, 2.829] | 1.145 | 0.7500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 3 | 1.134 [0.896, 1.435] | 1.149 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 3.337 [2.548, 4.369] | 3.324 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 2.061 [0.383, 11.085] | 2.152 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 3 | 1.407 [0.422, 4.693] | 1.337 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 1.120 [0.123, 10.220] | 1.089 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 3 | 0.784 [0.220, 2.803] | 0.828 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 3.797 [1.270, 11.351] | 3.967 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.646 [0.612, 0.683] | 0.618 [0.495, 0.772] | 0.975 [0.831, 1.144] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 0.675 [0.649, 0.702] | 0.739 [0.526, 1.037] | 0.924 [0.758, 1.126] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.783 [0.707, 0.866] | 0.823 [0.752, 0.900] | 0.957 [0.722, 1.266] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 1.445 [1.320, 1.583] | 1.321 [1.048, 1.665] | 0.999 [0.771, 1.293] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 3.106 [2.994, 3.221] | 1.408 [1.104, 1.796] | 2.982 [2.500, 3.556] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.773 [0.663, 0.902] | 0.820 [0.733, 0.918] | 0.922 [0.712, 1.195] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.861 [0.772, 0.961] | 0.900 [0.814, 0.996] | 1.058 [0.730, 1.531] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.910 [0.850, 0.975] | 0.961 [0.929, 0.994] | 0.958 [0.743, 1.236] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 1.082 [0.984, 1.190] | 1.169 [0.943, 1.450] | 0.992 [0.937, 1.051] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3.783 [3.370, 4.248] | 0.104 [0.097, 0.112] | 2.686 [2.232, 3.233] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.558 [0.512, 0.607] | 0.812 [0.436, 1.510] | 1.695 [1.472, 1.952] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 0.756 [0.583, 0.980] | 0.985 [0.701, 1.384] | 1.294 [0.887, 1.887] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 1.126 [0.647, 1.959] | 0.914 [0.557, 1.500] | 1.178 [0.473, 2.936] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 1.626 [1.336, 1.979] | 2.655 [0.588, 11.991] | 1.126 [0.901, 1.408] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.368 [1.214, 1.542] | 0.909 [0.548, 1.509] | 3.370 [2.565, 4.427] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.452 [0.399, 0.512] | 0.953 [0.560, 1.620] | 2.289 [1.456, 3.600] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.549 [0.416, 0.725] | 0.920 [0.601, 1.410] | 1.517 [0.585, 3.933] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.720 [0.626, 0.829] | 0.923 [0.585, 1.456] | 1.112 [0.781, 1.582] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 1.187 [0.986, 1.429] | 1.179 [0.588, 2.364] | 0.956 [0.688, 1.329] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.034 [0.889, 1.202] | 0.143 [0.092, 0.220] | 5.022 [4.036, 6.250] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-j1 | xs-rs-j16 | xs-rs-j2 | xs-rs-j4 |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 14.068 | 4.766 | 4.667 | 4.771 | 4.411 | 4.560 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 15.342 | 7.244 | 7.174 | 6.800 | 12.022 | 11.586 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 81.262 | 24.355 | 41.062 | 27.627 | 31.566 | 28.897 |
| `real-congress.fresh.mac-apollo.sender.warm` | 27.924 | 7.354 | 15.158 | 5.769 | 10.349 | 8.238 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0622 | 37 | 49 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 0.0796 | 59 | 79 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.1118 | 115 | 153 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 0.1024 | 97 | 129 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 0.0699 | 46 | 61 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.9802 | 8623 | 11556 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.5087 | 2324 | 3114 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.5786 | 3007 | 4029 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 1.0043 | 9053 | 12133 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.2234 | 451 | 603 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0539 | 29 | 37 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j2 | 0.1426 | 185 | 247 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.3498 | 1101 | 1474 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j16 | 0.0948 | 83 | 111 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.1086 | 108 | 144 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.6773 | 4118 | 5519 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.4849 | 2112 | 2830 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.8900 | 7110 | 9529 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j16 | 0.5127 | 2361 | 3163 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.4408 | 1746 | 2340 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-rs-j16: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nk
- xs-rs-j1: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs-j2: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs-j4: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
