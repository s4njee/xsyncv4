# SM1-small-onto-mac-apollo

Pulling small files onto the Mac, xs --no-atomic is at least 5% faster than xs's default, and xs is at least as fast as rsync.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T082417Z-SM1-small-onto-mac-apollo.
- Valid blocks: 18. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 0.967 [0.866, 1.080] | 0.966 | 0.5000 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.958 [0.806, 1.139] | 0.952 | 0.5000 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.942 [0.691, 1.284] | 0.949 | 0.7500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | rsync | 3 | 1.997 [1.639, 2.432] | 2.002 | 0.2500 | too few blocks |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 1.291 [0.649, 2.567] | 1.275 | 0.2500 | too few blocks |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 1.087 [0.721, 1.640] | 1.099 | 0.5000 | too few blocks |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 1.023 [0.697, 1.500] | 1.002 | 1.0000 | too few blocks |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | rsync | 3 | 1.222 [0.873, 1.710] | 1.244 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 0.706 [0.689, 0.725] | 0.706 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 1.162 [1.065, 1.269] | 1.159 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 1.043 [1.011, 1.077] | 1.045 | 0.2500 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 3 | 3.322 [3.063, 3.602] | 3.334 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 0.928 [0.614, 1.401] | 0.945 | 1.0000 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.844 [0.635, 1.123] | 0.858 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.600 [0.395, 0.912] | 0.593 | 0.2500 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 3 | 1.702 [1.507, 1.922] | 1.700 | 0.2500 | too few blocks |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 0.567 [0.537, 0.599] | 0.565 | 0.2500 | too few blocks |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 1.061 [0.938, 1.200] | 1.068 | 0.2500 | too few blocks |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 1.014 [0.893, 1.151] | 1.017 | 0.7500 | too few blocks |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | rsync | 3 | 2.876 [2.320, 3.565] | 2.883 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 3 | 1.026 [0.935, 1.126] | 1.022 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.974 [0.816, 1.163] | 0.980 | 0.7500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.939 [0.796, 1.107] | 0.938 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | rsync | 3 | 4.841 [4.767, 4.917] | 4.841 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.943 [0.865, 1.029] | 0.995 [0.424, 2.337] | 0.966 [0.867, 1.078] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.106 [0.994, 1.231] | 0.864 [0.390, 1.910] | 0.932 [0.727, 1.194] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.666 [0.569, 0.779] | 1.508 [0.734, 3.100] | 0.941 [0.687, 1.289] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | rsync | 1.383 [1.295, 1.477] | 0.741 [0.026, 20.838] | 2.022 [1.683, 2.430] |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1.130 [0.706, 1.806] | 1.010 [0.963, 1.059] | 1.325 [0.558, 3.146] |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.398 [0.928, 2.107] | 1.003 [0.932, 1.080] | 1.070 [0.674, 1.699] |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-rs | 0.720 [0.308, 1.682] | 1.005 [0.926, 1.091] | 1.029 [0.695, 1.525] |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | rsync | 0.834 [0.774, 0.899] | 1.007 [0.970, 1.044] | 1.244 [0.818, 1.892] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.722 [0.714, 0.730] | 0.917 [0.479, 1.752] | 0.714 [0.684, 0.745] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.924 [1.754, 2.110] | 0.983 [0.968, 0.998] | 1.173 [1.067, 1.288] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.962 [0.867, 1.067] | 1.656 [1.376, 1.994] | 1.047 [1.000, 1.096] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.154 [1.040, 1.281] | 1.290 [1.011, 1.646] | 3.389 [3.131, 3.668] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.991 [0.923, 1.063] | 0.999 [0.970, 1.029] | 0.932 [0.626, 1.388] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.520 [1.378, 1.677] | 1.077 [1.035, 1.120] | 0.844 [0.640, 1.113] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.601 [0.545, 0.662] | 2.437 [2.250, 2.639] | 0.564 [0.447, 0.711] |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.470 [0.398, 0.556] | 0.319 [0.158, 0.642] | 1.729 [1.515, 1.973] |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.605 [0.579, 0.632] | 0.966 [0.760, 1.227] | 0.567 [0.540, 0.596] |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.864 [1.807, 1.923] | 0.995 [0.801, 1.237] | 1.060 [0.933, 1.204] |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-rs | 1.015 [0.989, 1.041] | 3.262 [1.844, 5.768] | 1.012 [0.897, 1.141] |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | rsync | 0.885 [0.789, 0.992] | 1.407 [0.990, 1.999] | 2.885 [2.330, 3.571] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1.097 [1.016, 1.183] | 1.010 [0.978, 1.042] | 1.023 [0.920, 1.139] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 2.089 [1.593, 2.738] | 1.227 [1.170, 1.287] | 0.967 [0.831, 1.127] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 1.075 [0.915, 1.262] | 27.815 [26.558, 29.132] | 0.933 [0.794, 1.096] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | rsync | 1.320 [1.143, 1.524] | 0.909 [0.898, 0.921] | 4.913 [4.710, 5.126] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j8 | xs-cpp-noatomic | xs-rs |
|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | 3.419 | 1.712 | 1.640 | 1.656 | 1.613 |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | 0.256 | 0.209 | 0.227 | 0.270 | 0.214 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 64.691 | 19.475 | 22.638 | 13.759 | 20.321 |
| `real-congress.noop.apollo-mac.receiver.warm` | 4.470 | 2.626 | 2.218 | 2.436 | 1.575 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | 227.7 | 79.172 | 84.007 | 44.886 | 80.273 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | 16.526 | 3.414 | 3.326 | 3.503 | 3.205 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0445 | 20 | 26 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0694 | 46 | 60 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1246 | 142 | 189 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | rsync | 0.0794 | 59 | 78 |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.2768 | 690 | 924 |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.1654 | 248 | 331 |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | xs-rs | 0.1543 | 216 | 289 |
| `mixed-threshold.noop.apollo-mac.receiver.warm` | rsync | 0.1353 | 167 | 223 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0102 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0353 | 14 | 17 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0128 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.0326 | 12 | 15 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.1661 | 250 | 334 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.1149 | 121 | 161 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.1685 | 257 | 344 |
| `real-congress.noop.apollo-mac.receiver.warm` | rsync | 0.0490 | 24 | 31 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0221 | 8 | 8 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0495 | 24 | 32 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0510 | 26 | 34 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | rsync | 0.0865 | 70 | 92 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0375 | 15 | 19 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.0713 | 48 | 64 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 0.0664 | 42 | 56 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | rsync | 0.0062 | 8 | 8 |
