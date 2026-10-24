# CZ1-compress-pr34-apollo

On 10 GbE with fast CPUs, xs-rs -z at its automatic level (PR #34) is within 5% of the fastest fixed level and of no compression.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-z`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T163747Z-CZ1-compress-pr34-apollo.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 3 | 7.110 [5.866, 8.618] | 7.140 | 0.2500 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 2.299 [1.883, 2.807] | 2.311 | 0.2500 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 3 | 0.945 [0.774, 1.153] | 0.948 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 3 | 0.856 [0.627, 1.169] | 0.869 | 0.2500 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 3 | 1.068 [0.826, 1.381] | 1.080 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 3 | 1.595 [0.317, 8.040] | 1.628 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 1.239 [1.111, 1.383] | 1.247 | 0.2500 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 3 | 0.454 [0.055, 3.718] | 0.448 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 3 | 0.707 [0.055, 9.015] | 0.818 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 3 | 0.945 [0.207, 4.318] | 0.973 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 3.451 [3.350, 3.556] | 3.454 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 1.024 [0.877, 1.195] | 1.019 | 0.7500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 3 | 1.055 [0.891, 1.248] | 1.047 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 3 | 1.027 [0.887, 1.190] | 1.026 | 0.7500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 3 | 1.031 [0.746, 1.424] | 1.012 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 3.000 [0.939, 9.581] | 3.048 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.586 [0.133, 2.582] | 0.620 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 3 | 0.914 [0.353, 2.369] | 0.883 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 3 | 0.868 [0.221, 3.409] | 0.862 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 3 | 0.824 [0.087, 7.763] | 0.781 | 0.7500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 1.267 [1.199, 1.340] | 2.085 [1.799, 2.415] | 7.202 [5.817, 8.917] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.403 [0.396, 0.411] | 1.677 [1.246, 2.257] | 2.316 [1.869, 2.869] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.998 [0.934, 1.065] | 1.042 [0.964, 1.126] | 0.943 [0.767, 1.160] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.246 [1.172, 1.326] | 0.789 [0.145, 4.306] | 0.852 [0.627, 1.157] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.928 [0.892, 0.966] | 0.605 [0.293, 1.251] | 1.066 [0.823, 1.380] |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 1.045 [0.794, 1.375] | 0.050 [0.004, 0.590] | 3.205 [1.647, 6.238] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.280 [0.212, 0.370] | 0.863 [0.015, 48.647] | 1.277 [0.397, 4.110] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.933 [0.762, 1.143] | 0.435 [0.029, 6.461] | 0.684 [0.275, 1.702] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.261 [1.015, 1.567] | 0.960 [0.008, 109.323] | 0.898 [0.489, 1.650] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.891 [0.707, 1.123] | 0.593 [0.092, 3.825] | 0.848 [0.594, 1.212] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.368 [1.302, 1.438] | 1.104 [0.980, 1.243] | 3.496 [3.428, 3.567] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.977 [0.950, 1.004] | 1.238 [1.043, 1.470] | 1.028 [0.882, 1.198] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 1.009 [0.970, 1.049] | 1.004 [0.811, 1.244] | 1.052 [0.880, 1.258] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.006 [0.955, 1.061] | 1.010 [0.960, 1.062] | 1.028 [0.865, 1.220] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.976 [0.959, 0.993] | 0.986 [0.831, 1.171] | 1.030 [0.767, 1.382] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.014 [0.892, 1.152] | 0.141 [0.110, 0.181] | 5.607 [4.695, 6.695] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.967 [0.958, 0.976] | 0.978 [0.927, 1.032] | 1.013 [0.793, 1.294] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.986 [0.880, 1.106] | 0.965 [0.773, 1.205] | 1.002 [0.926, 1.084] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.984 [0.907, 1.067] | 1.000 [0.961, 1.040] | 1.068 [0.812, 1.405] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.703 [0.597, 0.828] | 0.951 [0.776, 1.166] | 1.096 [0.778, 1.546] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-base-z | xs-rs-z | xs-rs-z1 | xs-rs-z3 |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | 27.350 | 8.844 | 4.107 | 3.847 | 3.634 | 3.294 |
| `large-text.fresh.mac-apollo.sender.warm` | 25.952 | 20.163 | 15.371 | 16.268 | 7.385 | 11.500 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 77.696 | 23.047 | 23.207 | 22.513 | 23.747 | 23.131 |
| `real-congress.fresh.mac-apollo.sender.warm` | 31.636 | 6.184 | 8.687 | 10.545 | 9.641 | 9.157 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 0.0774 | 56 | 75 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0803 | 60 | 80 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0801 | 60 | 80 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.1253 | 143 | 191 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.1034 | 99 | 131 |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 0.6511 | 3807 | 5101 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.0441 | 20 | 26 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.8465 | 6433 | 8621 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.0248 | 9426 | 12633 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.6117 | 3360 | 4502 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.0120 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0622 | 37 | 49 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0678 | 44 | 58 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.0590 | 34 | 44 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.1300 | 154 | 206 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.4674 | 1963 | 2630 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.5967 | 3197 | 4284 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.3833 | 1321 | 1769 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.5506 | 2722 | 3648 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.9030 | 7320 | 9810 |
