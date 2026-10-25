# HS2-high-speed-pr34-apollo

On 4 GiB of incompressible data, xs-rs at PR #34 is at least as fast as its base in every file count.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-base`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T022919Z-HS2-high-speed-pr34-apollo.
- Valid blocks: 32. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 4 | 2.933 [2.653, 3.243] | 2.975 | 0.1250 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 4 | 1.038 [0.906, 1.191] | 1.038 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 4 | 1.114 [0.897, 1.383] | 1.068 | 0.1250 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 4 | 1.951 [0.923, 4.123] | 2.417 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 4 | 1.002 [0.294, 3.418] | 1.008 | 0.8750 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 4 | 1.257 [0.280, 5.637] | 1.257 | 1.0000 | too few blocks |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | rsync | 4 | 2.613 [1.933, 3.532] | 2.410 | 0.1250 | too few blocks |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 4 | 0.854 [0.784, 0.929] | 0.849 | 0.1250 | too few blocks |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 4 | 0.844 [0.685, 1.041] | 0.835 | 0.2500 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 4 | 2.072 [1.234, 3.477] | 2.375 | 0.1250 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 4 | 0.789 [0.462, 1.348] | 0.916 | 0.1250 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 4 | 1.039 [0.342, 3.157] | 1.009 | 0.6250 | too few blocks |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | rsync | 4 | 2.748 [2.371, 3.186] | 2.748 | 0.1250 | too few blocks |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 4 | 1.003 [0.956, 1.051] | 1.005 | 0.7500 | too few blocks |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 4 | 0.925 [0.698, 1.227] | 0.958 | 0.7500 | too few blocks |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | rsync | 4 | 2.047 [0.739, 5.672] | 2.047 | 0.2500 | too few blocks |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 4 | 0.957 [0.267, 3.432] | 0.936 | 1.0000 | too few blocks |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 4 | 0.717 [0.345, 1.493] | 0.737 | 0.3750 | too few blocks |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | rsync | 4 | 2.921 [2.593, 3.290] | 2.921 | 0.1250 | too few blocks |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 4 | 1.025 [0.978, 1.074] | 1.034 | 0.2500 | too few blocks |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 4 | 1.045 [1.007, 1.085] | 1.050 | 0.1250 | too few blocks |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | rsync | 4 | 1.409 [0.539, 3.684] | 1.409 | 0.5000 | too few blocks |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 4 | 0.730 [0.181, 2.940] | 0.663 | 0.3750 | too few blocks |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 4 | 0.687 [0.355, 1.330] | 0.797 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 3.720 [3.477, 3.980] | 1.608 [1.259, 2.054] | 2.944 [2.662, 3.257] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 2.274 [2.148, 2.407] | 1.071 [0.840, 1.367] | 1.039 [0.906, 1.192] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 1.274 [1.147, 1.415] | 1.319 [1.038, 1.676] | 1.114 [0.898, 1.382] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 4.183 [3.805, 4.599] | 0.112 [0.104, 0.120] | 2.849 [2.735, 2.968] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 2.384 [2.279, 2.494] | 0.939 [0.885, 0.996] | 1.011 [0.969, 1.054] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 1.047 [0.992, 1.105] | 1.040 [0.971, 1.114] | 0.982 [0.953, 1.013] |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | rsync | 3.080 [2.447, 3.878] | 0.062 [0.060, 0.064] | 2.633 [1.943, 3.567] |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 1.790 [1.760, 1.821] | 0.046 [0.045, 0.047] | 0.858 [0.789, 0.933] |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.664 [0.621, 0.709] | 0.027 [0.026, 0.027] | 0.848 [0.687, 1.046] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 3.191 [3.146, 3.238] | 0.004 [0.004, 0.004] | 2.602 [2.418, 2.799] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 1.765 [1.696, 1.837] | 0.034 [0.033, 0.035] | 0.934 [0.907, 0.962] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.683 [0.651, 0.716] | 0.036 [0.030, 0.044] | 0.909 [0.860, 0.961] |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | rsync | 3.608 [3.266, 3.985] | 1.862 [1.590, 2.181] | 2.758 [2.377, 3.200] |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 2.264 [2.201, 2.329] | 1.289 [1.123, 1.479] | 1.003 [0.957, 1.052] |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.938 [0.794, 1.109] | 1.004 [0.831, 1.214] | 0.925 [0.697, 1.228] |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | rsync | 4.152 [3.776, 4.566] | 0.108 [0.094, 0.124] | 2.865 [2.601, 3.156] |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 2.471 [2.281, 2.677] | 0.964 [0.785, 1.184] | 1.097 [0.985, 1.221] |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 0.977 [0.896, 1.065] | 1.016 [0.847, 1.219] | 1.013 [0.928, 1.105] |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | rsync | 3.792 [3.564, 4.035] | 1.729 [1.466, 2.039] | 2.931 [2.593, 3.312] |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 2.297 [2.211, 2.387] | 1.258 [1.000, 1.583] | 1.025 [0.980, 1.072] |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 1.268 [1.203, 1.337] | 1.196 [0.978, 1.463] | 1.046 [1.009, 1.086] |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | rsync | 4.268 [3.871, 4.706] | 0.108 [0.097, 0.119] | 2.745 [2.440, 3.088] |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 2.455 [2.306, 2.613] | 0.920 [0.825, 1.025] | 0.980 [0.902, 1.064] |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 1.086 [1.026, 1.150] | 1.013 [0.927, 1.108] | 0.965 [0.907, 1.027] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs | xs-rs-base |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 14.293 | 5.060 | 5.429 | 4.873 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 12.061 | 6.197 | 7.774 | 6.183 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | 14.613 | 4.775 | 4.721 | 5.593 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | 12.399 | 4.722 | 6.217 | 5.985 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | 13.937 | 5.084 | 4.691 | 5.071 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | 14.115 | 6.601 | 4.948 | 6.896 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | 15.114 | 5.303 | 5.409 | 5.174 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | 12.104 | 6.270 | 5.905 | 8.592 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | rsync | 0.0630 | 38 | 50 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0861 | 69 | 92 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1359 | 168 | 225 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.4704 | 1988 | 2664 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.7710 | 5336 | 7151 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.9429 | 7981 | 10696 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | rsync | 0.1895 | 325 | 434 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0533 | 28 | 37 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1317 | 158 | 211 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 0.3254 | 953 | 1276 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3366 | 1019 | 1365 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.6985 | 4381 | 5870 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | rsync | 0.0929 | 80 | 106 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0297 | 10 | 13 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1772 | 284 | 380 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | rsync | 0.6405 | 3684 | 4937 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.8025 | 5782 | 7748 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 0.4604 | 1905 | 2552 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | rsync | 0.0748 | 53 | 70 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0293 | 10 | 13 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0234 | 8 | 9 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | rsync | 0.6042 | 3279 | 4393 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.8756 | 6883 | 9224 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 0.4150 | 1548 | 2073 |
