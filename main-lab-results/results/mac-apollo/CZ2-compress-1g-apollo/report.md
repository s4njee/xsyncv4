# CZ2-compress-1g-apollo

Held to 1 Gb/s, xs-rs -z at its automatic level is within 5% of the fastest fixed level.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-z`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T040404Z-CZ2-compress-1g-apollo.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 2 | 1.945 [1.939, 1.951] | 1.945 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 2.725 [2.691, 2.759] | 2.725 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 2 | 1.000 [0.989, 1.012] | 1.000 | 1.0000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 2 | 0.695 [0.695, 0.696] | 0.695 | 0.5000 | too few blocks |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 2 | 0.997 [0.953, 1.042] | 0.997 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 2 | 1.476 [0.168, 12.950] | 1.476 | 0.5000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 2 | 0.862 [0.006, 123.577] | 0.862 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 2 | 0.980 [0.008, 119.226] | 0.980 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 2 | 0.873 [0.002, 326.968] | 0.873 | 1.0000 | too few blocks |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 2 | 0.852 [0.002, 376.619] | 0.852 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 2 | 3.560 [1.250, 10.139] | 3.560 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 1.056 [0.552, 2.020] | 1.056 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 2 | 0.991 [0.555, 1.769] | 0.991 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 2 | 1.001 [0.830, 1.207] | 1.001 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 2 | 1.027 [0.607, 1.738] | 1.027 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 2 | 4.055 [0.204, 80.789] | 4.055 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 2 | 0.864 [0.009, 85.140] | 0.864 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 2 | 1.089 [0.007, 173.056] | 1.089 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 2 | 1.241 [0.008, 187.441] | 1.241 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 2 | 1.281 [0.201, 8.182] | 1.281 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 1.149 [1.031, 1.282] | 1.746 [1.660, 1.836] | 1.948 [1.936, 1.960] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.542 [0.431, 0.682] | 1.260 [0.550, 2.886] | 2.730 [2.690, 2.770] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.998 [0.922, 1.082] | 0.995 [0.970, 1.020] | 1.001 [0.982, 1.019] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.173 [1.116, 1.233] | 0.992 [0.901, 1.092] | 0.694 [0.689, 0.700] |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.977 [0.875, 1.090] | 0.857 [0.841, 0.873] | 0.997 [0.955, 1.041] |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 1.056 [0.610, 1.830] | 0.778 [0.069, 8.801] | 1.966 [1.748, 2.211] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.968 [0.537, 1.744] | 0.951 [0.709, 1.274] | 1.012 [0.631, 1.625] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.920 [0.489, 1.730] | 0.909 [0.856, 0.965] | 1.003 [0.935, 1.076] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.201 [0.723, 1.995] | 0.951 [0.538, 1.681] | 0.783 [0.666, 0.920] |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.884 [0.555, 1.407] | 0.839 [0.737, 0.955] | 0.950 [0.868, 1.040] |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.334 [0.890, 1.998] | 1.110 [1.050, 1.173] | 3.639 [1.268, 10.441] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 1.020 [0.789, 1.319] | 2.347 [1.954, 2.819] | 1.057 [0.508, 2.200] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.999 [0.920, 1.086] | 1.011 [0.782, 1.307] | 0.996 [0.524, 1.894] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.011 [0.887, 1.153] | 1.005 [0.713, 1.416] | 0.998 [0.791, 1.258] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 1.009 [0.748, 1.362] | 0.985 [0.868, 1.118] | 1.037 [0.677, 1.588] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.190 [0.984, 1.440] | 0.156 [0.150, 0.161] | 6.279 [3.170, 12.436] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.999 [0.656, 1.521] | 1.039 [0.706, 1.531] | 1.007 [0.756, 1.341] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 1.008 [0.361, 2.818] | 1.026 [0.656, 1.605] | 0.959 [0.772, 1.190] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.028 [0.788, 1.342] | 1.002 [0.885, 1.134] | 1.014 [0.175, 5.867] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.796 [0.753, 0.841] | 1.000 [0.802, 1.247] | 1.268 [1.153, 1.394] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-base-z | xs-rs-z | xs-rs-z1 | xs-rs-z3 |
|---|---|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | 69.010 | 96.674 | 35.357 | 35.479 | 35.487 | 24.675 |
| `large-text.fresh.mac-apollo.sender.warm` | 77.602 | 45.322 | 44.818 | 52.574 | 51.519 | 45.881 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 75.117 | 22.276 | 21.675 | 21.101 | 20.910 | 21.121 |
| `real-congress.fresh.mac-apollo.sender.warm` | 42.270 | 9.003 | 13.357 | 10.423 | 11.350 | 12.936 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.apollo-mac.receiver.warm` | rsync | 0.0003 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0014 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0013 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.0000 | 8 | 8 |
| `large-text.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.0050 | 8 | 8 |
| `large-text.fresh.mac-apollo.sender.warm` | rsync | 0.2417 | 527 | 705 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs | 0.5526 | 2743 | 3675 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.5344 | 2565 | 3437 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.6596 | 3906 | 5234 |
| `large-text.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.6779 | 4126 | 5529 |
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.1165 | 124 | 166 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0722 | 49 | 65 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0645 | 40 | 53 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.0209 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-base-z | 0.0585 | 33 | 44 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.3330 | 997 | 1336 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.5110 | 2345 | 3142 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.5641 | 2858 | 3830 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.5584 | 2801 | 3753 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-base-z | 0.2063 | 385 | 515 |
