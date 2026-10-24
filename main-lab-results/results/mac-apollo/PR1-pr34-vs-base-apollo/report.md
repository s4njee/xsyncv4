# PR1-pr34-vs-base-apollo

xs-rs at PR #34 is within 5% of its base or faster in every cell at 10 GbE.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-base`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T025320Z-PR1-pr34-vs-base-apollo.
- Valid blocks: 30. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 1.020 [1.004, 1.037] | 1.020 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 1.013 [0.895, 1.147] | 1.008 | 1.0000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 3 | 3.448 [2.584, 4.602] | 3.466 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.797 [0.293, 2.172] | 0.842 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 0.715 [0.376, 1.359] | 0.741 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3 | 1.095 [0.182, 6.583] | 1.107 | 0.7500 | too few blocks |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 1.220 [0.428, 3.480] | 1.267 | 0.5000 | too few blocks |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 1.032 [0.359, 2.964] | 0.984 | 1.0000 | too few blocks |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 3 | 1.261 [0.627, 2.537] | 1.231 | 0.2500 | too few blocks |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 3 | 1.038 [0.848, 1.272] | 1.037 | 0.7500 | too few blocks |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 1.000 [0.988, 1.012] | 1.001 | 1.0000 | too few blocks |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 3 | 1.450 [1.239, 1.697] | 1.445 | 0.2500 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 1.240 [0.458, 3.356] | 1.286 | 0.5000 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 1.434 [0.355, 5.801] | 1.475 | 0.5000 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 3 | 1.700 [0.469, 6.161] | 1.608 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.705 [0.214, 2.322] | 0.741 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 0.938 [0.143, 6.144] | 0.923 | 0.7500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 3 | 1.599 [0.708, 3.609] | 1.676 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.975 [0.160, 5.953] | 0.957 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 1.009 [0.538, 1.894] | 0.991 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 2.426 [0.459, 12.810] | 2.576 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.740 [0.326, 1.683] | 0.754 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 0.703 [0.236, 2.091] | 0.685 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 2.905 [0.711, 11.873] | 2.880 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.960 [0.513, 1.794] | 0.968 | 0.7500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 3 | 0.928 [0.663, 1.297] | 0.923 | 0.5000 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 3 | 2.660 [1.401, 5.049] | 2.741 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.883 [0.772, 1.011] | 0.889 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 3 | 0.974 [0.632, 1.501] | 0.984 | 1.0000 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 3 | 4.516 [2.386, 8.550] | 4.636 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 1.286 [1.220, 1.355] | 1.155 [0.887, 1.503] | 1.020 [1.002, 1.039] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 1.016 [0.975, 1.059] | 1.143 [0.960, 1.361] | 1.013 [0.895, 1.148] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 4.254 [3.474, 5.208] | 1.640 [1.550, 1.735] | 3.482 [2.592, 4.678] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.939 [0.715, 1.231] | 1.007 [0.858, 1.183] | 0.968 [0.933, 1.004] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.898 [0.724, 1.113] | 1.002 [0.873, 1.149] | 0.980 [0.861, 1.117] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 4.121 [3.583, 4.739] | 0.106 [0.097, 0.116] | 2.940 [2.663, 3.246] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 1.122 [0.939, 1.341] | 0.990 [0.936, 1.048] | 1.357 [0.336, 5.487] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.882 [0.732, 1.062] | 1.001 [0.985, 1.017] | 0.924 [0.478, 1.783] |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 3.382 [2.397, 4.770] | 0.979 [0.904, 1.061] | 1.410 [0.505, 3.938] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 1.014 [0.530, 1.939] | 1.007 [0.986, 1.028] | 1.032 [0.852, 1.250] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.985 [0.844, 1.151] | 0.998 [0.934, 1.066] | 0.997 [0.981, 1.013] |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 3.108 [2.521, 3.832] | 1.006 [0.980, 1.033] | 1.448 [1.259, 1.665] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.964 [0.705, 1.319] | 1.002 [0.965, 1.041] | 1.289 [0.397, 4.187] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.973 [0.836, 1.132] | 0.999 [0.990, 1.008] | 1.603 [0.296, 8.686] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 1.028 [0.746, 1.417] | 0.992 [0.970, 1.015] | 1.933 [0.417, 8.973] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 1.134 [0.852, 1.510] | 1.007 [0.965, 1.051] | 0.722 [0.207, 2.522] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.970 [0.643, 1.465] | 0.995 [0.948, 1.044] | 0.977 [0.125, 7.610] |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 1.127 [0.780, 1.629] | 0.996 [0.959, 1.034] | 1.670 [0.667, 4.184] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.930 [0.419, 2.067] | 1.386 [0.782, 2.456] | 0.987 [0.156, 6.248] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.901 [0.734, 1.105] | 1.079 [0.703, 1.658] | 1.023 [0.532, 1.966] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.093 [0.418, 2.856] | 1.018 [0.953, 1.088] | 2.481 [0.452, 13.606] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.358 [1.212, 1.521] | 1.048 [0.891, 1.233] | 1.067 [0.849, 1.340] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 1.025 [0.913, 1.152] | 0.986 [0.897, 1.084] | 1.070 [0.641, 1.784] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.554 [1.406, 1.718] | 0.149 [0.136, 0.164] | 5.414 [3.525, 8.315] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 1.026 [0.838, 1.256] | 0.947 [0.840, 1.067] | 0.973 [0.511, 1.853] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 1.012 [0.924, 1.109] | 0.994 [0.753, 1.313] | 0.934 [0.680, 1.284] |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.835 [0.680, 1.024] | 0.160 [0.137, 0.186] | 2.770 [1.495, 5.131] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.156 [0.907, 1.475] | 1.002 [0.986, 1.018] | 0.884 [0.775, 1.008] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.990 [0.954, 1.027] | 0.993 [0.988, 0.999] | 0.975 [0.635, 1.497] |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 1.106 [0.927, 1.320] | 0.120 [0.113, 0.127] | 4.526 [2.399, 8.539] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-base | xs-rs-j4 |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 15.181 | 4.492 | 4.402 | 4.460 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 18.279 | 13.304 | 16.686 | 11.928 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | 0.332 | 0.321 | 0.263 | 0.271 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | 0.219 | 0.157 | 0.151 | 0.151 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.498 | 0.363 | 0.293 | 0.420 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.444 | 0.196 | 0.278 | 0.260 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 75.034 | 30.150 | 30.930 | 31.217 |
| `real-congress.fresh.mac-apollo.sender.warm` | 33.206 | 8.463 | 11.431 | 8.033 |
| `real-congress.noop.apollo-mac.receiver.warm` | 4.513 | 1.628 | 1.697 | 1.574 |
| `real-congress.noop.mac-apollo.sender.warm` | 6.537 | 1.279 | 1.447 | 1.410 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0064 | 8 | 8 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.0501 | 25 | 33 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 0.1161 | 124 | 165 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.4034 | 1463 | 1960 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.2587 | 603 | 808 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.7219 | 4678 | 6269 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs | 0.4221 | 1601 | 2145 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.4248 | 1622 | 2173 |
| `hs-16x256m.noop.apollo-mac.receiver.warm` | rsync | 0.2814 | 713 | 955 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs | 0.0817 | 62 | 83 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.0048 | 8 | 8 |
| `hs-16x256m.noop.mac-apollo.sender.warm` | rsync | 0.0634 | 39 | 51 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.4007 | 1443 | 1933 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.5625 | 2842 | 3808 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | rsync | 0.5183 | 2413 | 3234 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.4799 | 2069 | 2772 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.7566 | 5139 | 6886 |
| `local-laikav2.noop.mac-apollo.sender.warm` | rsync | 0.3278 | 967 | 1295 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.7284 | 4763 | 6383 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-j4 | 0.2535 | 579 | 775 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.6698 | 4029 | 5399 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.3305 | 982 | 1316 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j4 | 0.4389 | 1731 | 2319 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.5667 | 2884 | 3865 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.2519 | 572 | 766 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs-j4 | 0.1350 | 166 | 222 |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.2580 | 600 | 803 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.0544 | 29 | 38 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j4 | 0.1741 | 275 | 367 |
| `real-congress.noop.mac-apollo.sender.warm` | rsync | 0.2569 | 595 | 796 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-rs-base: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7n
- xs-rs-j4: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
