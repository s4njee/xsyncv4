# RW1-delta-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Delta updates of large files: a 4 KiB edit in a file (update-1pct), and a file grown at its end (append-1pct).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162410Z-RW1-delta-apollo, 20261023T040630Z-RW1-delta-apollo.
- Valid blocks: 24. Voided block attempts: 36.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.305 [1.850, 2.872] | 2.294 | 0.2500 | too few blocks |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.263 [0.886, 1.802] | 1.257 | 0.2500 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 1.702 [0.207, 13.975] | 1.532 | 0.5000 | too few blocks |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.473 [0.099, 21.972] | 1.358 | 0.7500 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.616 [2.236, 3.060] | 2.606 | 0.2500 | too few blocks |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.297 [1.260, 1.336] | 1.296 | 0.2500 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 1.389 [0.205, 9.422] | 1.289 | 0.7500 | too few blocks |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.344 [0.148, 12.242] | 1.199 | 1.0000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 3.041 [0.832, 11.112] | 2.829 | 0.2500 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.300 [1.204, 1.403] | 1.295 | 0.2500 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 2.465 [0.026, 234.655] | 3.136 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.334 [0.019, 95.993] | 1.364 | 0.7500 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 2.546 [2.303, 2.816] | 2.535 | 0.2500 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 1.177 [1.035, 1.340] | 1.186 | 0.2500 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 3.583 [0.369, 34.795] | 4.001 | 0.2500 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 1.610 [0.269, 9.623] | 1.460 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.395 [1.295, 1.504] | 1.003 [0.947, 1.061] | 2.314 [1.871, 2.861] |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.140 [0.880, 1.478] | 1.003 [0.976, 1.030] | 1.269 [0.887, 1.815] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.464 [1.294, 1.655] | 1.019 [0.938, 1.107] | 1.799 [0.240, 13.464] |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.071 [0.890, 1.290] | 0.999 [0.922, 1.084] | 1.559 [0.123, 19.716] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.292 [1.176, 1.420] | 0.999 [0.986, 1.011] | 2.620 [2.231, 3.076] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.142 [1.129, 1.155] | 1.005 [0.979, 1.031] | 1.299 [1.258, 1.341] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.069 [1.002, 1.140] | 1.007 [0.962, 1.054] | 1.388 [0.204, 9.436] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.090 [1.022, 1.163] | 0.995 [0.959, 1.032] | 1.296 [0.130, 12.941] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.639 [1.514, 1.774] | 0.998 [0.964, 1.033] | 3.081 [0.849, 11.180] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.154 [1.126, 1.183] | 0.994 [0.936, 1.056] | 1.310 [1.232, 1.393] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.588 [1.532, 1.646] | 1.002 [0.997, 1.006] | 2.491 [0.040, 156.026] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.156 [1.066, 1.253] | 0.994 [0.953, 1.036] | 1.409 [0.027, 74.899] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.475 [1.360, 1.600] | 0.998 [0.972, 1.025] | 2.565 [2.315, 2.842] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.152 [1.040, 1.276] | 0.991 [0.961, 1.023] | 1.179 [1.022, 1.360] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.990 [0.892, 1.098] | 1.003 [0.980, 1.027] | 3.603 [0.327, 39.665] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.921 [0.799, 1.062] | 1.006 [0.987, 1.026] | 1.649 [0.290, 9.385] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | 4.687 | 10.804 | 5.922 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | 11.035 | 18.777 | 16.259 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | 4.281 | 11.200 | 5.553 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | 14.555 | 20.209 | 19.562 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.387 | 4.219 | 1.803 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 2.581 | 6.363 | 3.444 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.346 | 3.428 | 1.585 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 1.554 | 5.567 | 2.502 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0885 | 73 | 97 |
| `large-solo.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.1428 | 186 | 248 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.8477 | 6450 | 8644 |
| `large-solo.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.0878 | 10620 | 14233 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0632 | 38 | 51 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0118 | 8 | 8 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.7708 | 5334 | 7148 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.8893 | 7099 | 9514 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.5216 | 2444 | 3274 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0308 | 11 | 14 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.8339 | 30182 | 40451 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.7212 | 26587 | 35632 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0405 | 17 | 22 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0520 | 27 | 35 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.9151 | 7517 | 10074 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.7197 | 4650 | 6231 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
