# PR1r-pr34-regression-apollo

xs-rs at PR #34 is within 5% of its base or faster in every cell at 10 GbE.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-base`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T040403Z-PR1r-pr34-regression-apollo.
- Valid blocks: 80. Voided block attempts: 48.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 8 | 0.973 [0.889, 1.065] | 0.977 [0.871, 1.089] | 0.4766 | inconclusive |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 8 | 0.946 [0.877, 1.022] | 0.946 [0.872, 1.021] | 0.1875 | inconclusive |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 8 | 2.928 [2.689, 3.187] | 2.898 [2.699, 3.235] | 0.0078 | slower |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 8 | 1.437 [0.822, 2.513] | 1.521 [0.779, 2.719] | 0.1719 | inconclusive |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 8 | 1.054 [0.548, 2.028] | 1.040 [0.541, 2.263] | 0.8516 | inconclusive |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 8 | 1.879 [1.349, 2.617] | 1.881 [1.261, 2.710] | 0.0078 | slower |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 8 | 0.910 [0.720, 1.150] | 0.876 [0.721, 1.197] | 0.3984 | inconclusive |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 8 | 1.083 [0.779, 1.505] | 1.024 [0.792, 1.587] | 0.5547 | inconclusive |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 8 | 1.293 [0.944, 1.771] | 1.247 [0.949, 1.743] | 0.0859 | inconclusive |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 8 | 1.116 [0.688, 1.811] | 1.211 [0.613, 1.656] | 0.6172 | inconclusive |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 8 | 1.272 [0.723, 2.237] | 1.297 [0.626, 2.321] | 0.3438 | inconclusive |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 8 | 1.591 [0.972, 2.605] | 1.730 [0.884, 2.468] | 0.0781 | inconclusive |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 8 | 1.004 [0.802, 1.257] | 0.984 [0.811, 1.347] | 0.9531 | inconclusive |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 8 | 0.924 [0.796, 1.072] | 0.919 [0.788, 1.098] | 0.2422 | inconclusive |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 8 | 1.570 [1.378, 1.790] | 1.578 [1.351, 1.809] | 0.0078 | slower |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 8 | 1.034 [0.714, 1.499] | 1.019 [0.683, 1.478] | 0.8125 | inconclusive |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 8 | 1.055 [0.706, 1.576] | 1.052 [0.673, 1.659] | 0.5781 | inconclusive |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 8 | 1.898 [1.391, 2.589] | 2.054 [1.318, 2.518] | 0.0156 | slower |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 8 | 1.025 [0.988, 1.063] | 1.027 [0.984, 1.065] | 0.1641 | inconclusive |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 8 | 1.024 [0.971, 1.081] | 1.024 [0.963, 1.078] | 0.2969 | inconclusive |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 8 | 3.813 [3.165, 4.593] | 3.580 [3.368, 4.876] | 0.0078 | slower |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 8 | 1.006 [0.716, 1.414] | 1.019 [0.694, 1.443] | 0.9688 | inconclusive |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 8 | 0.901 [0.681, 1.194] | 0.917 [0.670, 1.251] | 0.3516 | inconclusive |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 8 | 3.754 [2.819, 4.998] | 3.743 [2.606, 5.111] | 0.0078 | slower |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 8 | 0.956 [0.796, 1.147] | 0.938 [0.798, 1.183] | 0.5625 | inconclusive |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 8 | 0.955 [0.840, 1.086] | 0.938 [0.845, 1.119] | 0.4219 | inconclusive |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 8 | 2.748 [2.475, 3.051] | 2.706 [2.458, 3.054] | 0.0078 | slower |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 8 | 0.811 [0.640, 1.028] | 0.808 [0.613, 1.055] | 0.0938 | inconclusive |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 8 | 1.036 [0.813, 1.321] | 1.062 [0.775, 1.332] | 0.7344 | inconclusive |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 8 | 4.292 [3.649, 5.047] | 4.309 [3.528, 5.244] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 1.259 [1.230, 1.290] | 1.074 [0.994, 1.159] | 0.975 [0.890, 1.069] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.998 [0.977, 1.020] | 0.931 [0.861, 1.006] | 0.951 [0.876, 1.033] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 4.182 [3.985, 4.389] | 1.348 [1.283, 1.417] | 2.973 [2.731, 3.238] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 1.011 [0.935, 1.094] | 1.051 [0.997, 1.107] | 1.053 [0.975, 1.138] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.970 [0.918, 1.025] | 1.032 [0.933, 1.141] | 1.042 [0.989, 1.099] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 4.233 [3.895, 4.601] | 0.108 [0.105, 0.111] | 2.953 [2.768, 3.150] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 0.942 [0.812, 1.093] | 1.003 [0.979, 1.028] | 0.922 [0.694, 1.226] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.938 [0.778, 1.130] | 1.004 [0.978, 1.031] | 1.072 [0.756, 1.520] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 3.172 [2.729, 3.686] | 1.007 [0.991, 1.022] | 1.453 [0.995, 2.123] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 0.996 [0.804, 1.233] | 1.003 [0.998, 1.008] | 1.119 [0.687, 1.822] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.963 [0.820, 1.130] | 1.003 [0.995, 1.011] | 1.275 [0.721, 2.255] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 3.168 [2.834, 3.542] | 0.999 [0.985, 1.014] | 1.602 [0.976, 2.631] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.998 [0.951, 1.048] | 0.993 [0.982, 1.005] | 0.995 [0.761, 1.302] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 1.002 [0.913, 1.100] | 1.004 [0.998, 1.010] | 0.914 [0.786, 1.063] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 1.067 [0.990, 1.151] | 0.993 [0.979, 1.007] | 1.780 [1.552, 2.042] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 1.073 [0.961, 1.199] | 0.994 [0.984, 1.004] | 1.013 [0.680, 1.510] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.975 [0.883, 1.077] | 0.993 [0.984, 1.002] | 1.049 [0.699, 1.573] |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 1.133 [1.039, 1.235] | 0.991 [0.985, 0.997] | 1.903 [1.393, 2.600] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 1.011 [0.997, 1.025] | 1.154 [0.973, 1.368] | 1.030 [0.993, 1.068] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 1.007 [0.992, 1.022] | 1.000 [0.937, 1.067] | 1.032 [0.979, 1.088] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.515 [1.317, 1.744] | 0.960 [0.898, 1.025] | 3.882 [3.239, 4.653] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.177 [1.141, 1.214] | 1.028 [0.969, 1.090] | 0.737 [0.607, 0.896] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.983 [0.950, 1.017] | 1.001 [0.981, 1.022] | 0.911 [0.787, 1.055] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.582 [1.515, 1.653] | 0.154 [0.150, 0.158] | 4.540 [3.930, 5.244] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.994 [0.940, 1.051] | 1.015 [0.959, 1.075] | 0.959 [0.793, 1.160] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 1.003 [0.965, 1.043] | 0.953 [0.913, 0.995] | 0.957 [0.837, 1.094] |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.841 [0.808, 0.876] | 0.169 [0.158, 0.181] | 2.825 [2.530, 3.154] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.116 [1.045, 1.193] | 0.996 [0.989, 1.004] | 0.809 [0.637, 1.026] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.999 [0.949, 1.052] | 0.999 [0.993, 1.006] | 1.037 [0.813, 1.322] |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 1.119 [1.069, 1.171] | 0.118 [0.115, 0.121] | 4.298 [3.653, 5.057] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-base | xs-rs-j4 |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 15.854 | 5.269 | 5.415 | 5.125 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 13.445 | 10.288 | 7.157 | 7.542 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | 0.350 | 0.247 | 0.271 | 0.293 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | 0.294 | 0.206 | 0.185 | 0.235 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.478 | 0.305 | 0.304 | 0.281 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.435 | 0.237 | 0.229 | 0.242 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 90.695 | 24.385 | 23.785 | 24.367 |
| `real-congress.fresh.mac-apollo.sender.warm` | 44.348 | 11.889 | 11.815 | 10.651 |
| `real-congress.noop.apollo-mac.receiver.warm` | 4.658 | 1.620 | 1.695 | 1.619 |
| `real-congress.noop.mac-apollo.sender.warm` | 6.703 | 1.267 | 1.562 | 1.618 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1086 | 108 | 144 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.0916 | 78 | 103 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 0.1016 | 95 | 127 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.6680 | 4006 | 5368 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.7828 | 5501 | 7372 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.3964 | 1413 | 1893 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 0.2805 | 708 | 949 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.3940 | 1396 | 1870 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 0.3763 | 1273 | 1705 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 0.5793 | 3014 | 4039 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.6759 | 4101 | 5496 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 0.5894 | 3119 | 4180 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.2691 | 652 | 873 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.1779 | 287 | 383 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 0.1563 | 222 | 296 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.4440 | 1772 | 2374 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.4797 | 2067 | 2770 |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 0.3717 | 1242 | 1664 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0438 | 20 | 26 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.0646 | 40 | 53 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.2227 | 448 | 599 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.4072 | 1490 | 1997 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.3362 | 1017 | 1362 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.3426 | 1056 | 1414 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.2188 | 432 | 578 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.1539 | 215 | 287 |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.1250 | 143 | 191 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.2828 | 720 | 965 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.2903 | 759 | 1016 |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 0.1940 | 340 | 455 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-rs-base: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7n
- xs-rs-j4: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
