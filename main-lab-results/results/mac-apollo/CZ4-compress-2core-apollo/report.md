# CZ4-compress-2core-apollo

With apollo held to 2 cores, xs-rs -z at its automatic level is within 5% of the fastest fixed level.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-z`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T075240Z-CZ4-compress-2core-apollo.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 2 | 2.558 [2.462, 2.656] | 2.558 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 1.007 [0.899, 1.128] | 1.007 | 1.0000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 2 | 1.004 [0.963, 1.046] | 1.004 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 2 | 1.456 [1.217, 1.743] | 1.456 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 2 | 0.965 [0.939, 0.992] | 0.965 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 2 | 0.918 [0.598, 1.409] | 0.918 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 2 | 0.589 [0.276, 1.256] | 0.589 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 2 | 0.696 [0.001, 374.533] | 0.696 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 2 | 1.214 [0.889, 1.657] | 1.214 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 2 | 1.137 [0.981, 1.317] | 1.137 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 2 | 3.081 [2.160, 4.393] | 3.081 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 0.965 [0.776, 1.199] | 0.965 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 2 | 0.998 [0.774, 1.287] | 0.998 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 2 | 1.026 [0.971, 1.084] | 1.026 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 2 | 1.021 [0.840, 1.242] | 1.021 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 2 | 4.039 [0.620, 26.327] | 4.039 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 2 | 2.174 [2.053, 2.303] | 2.174 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 2 | 1.712 [0.234, 12.537] | 1.712 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 2 | 1.703 [0.096, 30.196] | 1.703 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 2 | 1.320 [1.038, 1.680] | 1.320 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 1.080 [0.999, 1.168] | 4.922 [1.981, 12.231] | 2.566 [2.496, 2.637] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.270 [0.231, 0.315] | 5.152 [1.585, 16.743] | 1.001 [0.980, 1.021] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 1.005 [0.932, 1.083] | 1.583 [0.009, 271.868] | 1.003 [0.967, 1.039] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.378 [1.248, 1.522] | 1.265 [0.011, 143.368] | 1.459 [1.212, 1.756] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.970 [0.961, 0.979] | 0.808 [0.082, 7.924] | 0.965 [0.940, 0.990] |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 0.948 [0.741, 1.213] | 0.080 [0.002, 2.807] | 3.252 [0.756, 13.990] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.300 [0.209, 0.430] | 0.862 [0.051, 14.522] | 1.265 [0.364, 4.392] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.981 [0.973, 0.988] | 0.802 [0.018, 35.502] | 0.940 [0.259, 3.411] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.317 [1.230, 1.410] | 7.212 [1.334, 38.998] | 1.701 [0.053, 54.328] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.954 [0.651, 1.397] | 3.825 [0.001, 10561.443] | 1.251 [0.037, 42.533] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.209 [1.122, 1.302] | 1.098 [1.066, 1.131] | 3.096 [2.289, 4.188] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.966 [0.852, 1.094] | 1.171 [0.513, 2.673] | 0.944 [0.702, 1.270] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.994 [0.857, 1.153] | 0.989 [0.699, 1.399] | 0.997 [0.798, 1.245] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.009 [0.952, 1.069] | 1.010 [0.962, 1.061] | 1.007 [0.863, 1.176] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 1.007 [0.990, 1.026] | 0.986 [0.944, 1.030] | 1.011 [0.771, 1.325] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.864 [0.327, 2.285] | 0.160 [0.150, 0.171] | 4.708 [2.051, 10.808] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.934 [0.750, 1.164] | 0.973 [0.831, 1.139] | 1.131 [0.760, 1.683] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.999 [0.578, 1.728] | 1.130 [0.328, 3.897] | 1.197 [0.993, 1.443] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.975 [0.784, 1.213] | 1.088 [0.491, 2.415] | 1.058 [0.559, 2.000] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.631 [0.356, 1.120] | 0.977 [0.714, 1.336] | 1.099 [0.905, 1.335] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-base-z | xs-rs-z | xs-rs-z1 | xs-rs-z3 |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | 21.106 | 8.308 | 7.963 | 8.252 | 8.282 | 12.019 |
| `large-text.fresh.mac-apollo.sender.warm` | 25.292 | 16.232 | 31.324 | 27.559 | 19.195 | 33.446 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 63.816 | 19.981 | 21.161 | 20.716 | 20.676 | 21.258 |
| `real-congress.fresh.mac-apollo.sender.warm` | 28.992 | 15.605 | 9.476 | 7.178 | 12.289 | 12.222 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 0.0042 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0126 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0046 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.0200 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.0031 | 8 | 8 |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 0.0477 | 23 | 30 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.0843 | 66 | 88 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.6998 | 4397 | 5892 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.0347 | 13 | 17 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.0164 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.0395 | 17 | 21 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0242 | 8 | 10 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0283 | 10 | 12 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.0061 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.0218 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.2086 | 393 | 526 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.0064 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.2216 | 443 | 593 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.3200 | 922 | 1234 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.0268 | 9 | 11 |
