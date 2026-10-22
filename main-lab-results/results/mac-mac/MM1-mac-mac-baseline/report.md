# MM1-mac-mac-baseline

With both ends on macOS, xs's time relative to rsync differs by more than 10% from E6b's, with mars on Linux, in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T133436Z-MM1-mac-mac-baseline, 20261021T140436Z-MM1-mac-mac-baseline.
- Valid blocks: 100. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-e6b | 7 | 0.584 [0.412, 0.829] | 0.585 [0.415, 0.911] | 0.0156 | too few blocks |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-cpp | 7 | 0.538 [0.368, 0.785] | 0.549 [0.349, 0.773] | 0.0156 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-e6b | 6 | 0.445 [0.429, 0.463] | 0.444 [0.428, 0.470] | 0.0312 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-cpp | 6 | 0.419 [0.368, 0.476] | 0.425 [0.346, 0.477] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-e6b | 6 | 0.778 [0.668, 0.906] | 0.789 [0.618, 0.918] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-cpp | 6 | 0.701 [0.635, 0.773] | 0.698 [0.610, 0.793] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-e6b | 7 | 0.945 [0.862, 1.036] | 0.941 [0.851, 1.058] | 0.1719 | too few blocks |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-cpp | 7 | 0.738 [0.679, 0.801] | 0.736 [0.667, 0.807] | 0.0156 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-e6b | 6 | 0.734 [0.710, 0.759] | 0.734 [0.698, 0.762] | 0.0312 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-cpp | 6 | 0.714 [0.693, 0.734] | 0.715 [0.683, 0.737] | 0.0312 | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-e6b | 6 | 0.578 [0.526, 0.635] | 0.578 [0.508, 0.632] | 0.0312 | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-cpp | 6 | 0.540 [0.502, 0.580] | 0.540 [0.510, 0.602] | 0.0312 | too few blocks |
| `real-congress.noop.mac-mars.sender.warm` | xs-e6b | 6 | 0.383 [0.323, 0.453] | 0.390 [0.293, 0.468] | 0.0312 | too few blocks |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp | 6 | 0.297 [0.252, 0.349] | 0.293 [0.249, 0.376] | 0.0312 | too few blocks |
| `real-congress.noop.mars-mac.receiver.warm` | xs-e6b | 6 | 0.573 [0.501, 0.656] | 0.582 [0.486, 0.697] | 0.0312 | too few blocks |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp | 6 | 0.437 [0.368, 0.518] | 0.422 [0.372, 0.587] | 0.0312 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | xs-e6b | 6 | 0.851 [0.730, 0.991] | 0.883 [0.642, 0.952] | 0.0312 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | xs-cpp | 6 | 0.828 [0.706, 0.971] | 0.866 [0.614, 0.917] | 0.0312 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-e6b | 6 | 0.930 [0.879, 0.985] | 0.926 [0.862, 0.996] | 0.0312 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-cpp | 6 | 1.026 [0.859, 1.227] | 0.986 [0.912, 1.418] | 0.9062 | too few blocks |
| `small-deep.noop.mac-mars.sender.warm` | xs-e6b | 6 | 0.335 [0.289, 0.387] | 0.342 [0.271, 0.393] | 0.0312 | too few blocks |
| `small-deep.noop.mac-mars.sender.warm` | xs-cpp | 6 | 0.313 [0.264, 0.371] | 0.317 [0.258, 0.389] | 0.0312 | too few blocks |
| `small-deep.noop.mars-mac.receiver.warm` | xs-e6b | 7 | 1.012 [0.933, 1.097] | 1.011 [0.936, 1.122] | 0.6875 | too few blocks |
| `small-deep.noop.mars-mac.receiver.warm` | xs-cpp | 7 | 1.051 [0.923, 1.197] | 1.048 [0.915, 1.233] | 0.3281 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | xs-e6b | 6 | 0.790 [0.737, 0.847] | 0.790 [0.711, 0.853] | 0.0312 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | xs-cpp | 6 | 0.791 [0.704, 0.888] | 0.790 [0.688, 0.951] | 0.0312 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-e6b | 6 | 0.647 [0.596, 0.702] | 0.649 [0.584, 0.720] | 0.0312 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-cpp | 6 | 0.662 [0.631, 0.694] | 0.661 [0.616, 0.708] | 0.0312 | too few blocks |
| `small-flat.noop.mac-mars.sender.warm` | xs-e6b | 6 | 0.456 [0.374, 0.556] | 0.467 [0.337, 0.557] | 0.0312 | too few blocks |
| `small-flat.noop.mac-mars.sender.warm` | xs-cpp | 6 | 0.288 [0.228, 0.365] | 0.291 [0.208, 0.364] | 0.0312 | too few blocks |
| `small-flat.noop.mars-mac.receiver.warm` | xs-e6b | 7 | 0.564 [0.488, 0.652] | 0.570 [0.487, 0.643] | 0.0156 | too few blocks |
| `small-flat.noop.mars-mac.receiver.warm` | xs-cpp | 7 | 0.349 [0.329, 0.370] | 0.350 [0.329, 0.369] | 0.0156 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-e6b | 0.742 [0.699, 0.788] | 20.530 [20.033, 21.040] | 0.578 [0.405, 0.826] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-cpp | 0.683 [0.631, 0.739] | 20.116 [19.263, 21.006] | 0.531 [0.360, 0.781] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-e6b | 0.809 [0.763, 0.858] | 1.555 [1.500, 1.611] | 0.440 [0.422, 0.459] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-cpp | 0.661 [0.621, 0.704] | 1.814 [1.649, 1.994] | 0.413 [0.363, 0.469] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-e6b | 1.892 [1.661, 2.154] | 1.649 [1.555, 1.748] | 0.694 [0.621, 0.775] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-cpp | 0.931 [0.833, 1.041] | 1.069 [0.975, 1.170] | 0.593 [0.512, 0.686] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-e6b | 3.432 [3.156, 3.733] | 2.566 [2.506, 2.627] | 0.938 [0.850, 1.034] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-cpp | 1.055 [0.916, 1.216] | 1.099 [1.072, 1.127] | 0.700 [0.645, 0.760] |
| `real-congress.fresh.mac-mars.sender.warm` | xs-e6b | 0.934 [0.904, 0.965] | 5.754 [4.986, 6.641] | 0.732 [0.710, 0.754] |
| `real-congress.fresh.mac-mars.sender.warm` | xs-cpp | 0.799 [0.787, 0.811] | 5.459 [4.851, 6.143] | 0.707 [0.687, 0.728] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-e6b | 0.750 [0.679, 0.830] | 1.747 [1.683, 1.813] | 0.577 [0.524, 0.634] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-cpp | 0.605 [0.593, 0.618] | 1.507 [1.355, 1.676] | 0.537 [0.499, 0.578] |
| `real-congress.noop.mac-mars.sender.warm` | xs-e6b | 2.067 [1.847, 2.313] | 1.717 [1.505, 1.959] | 0.370 [0.311, 0.439] |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp | 1.324 [1.231, 1.424] | 1.793 [1.628, 1.974] | 0.275 [0.244, 0.311] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-e6b | 4.784 [4.303, 5.319] | 2.868 [2.527, 3.256] | 0.568 [0.496, 0.652] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp | 1.728 [1.568, 1.906] | 2.613 [2.299, 2.970] | 0.429 [0.361, 0.511] |
| `small-deep.fresh.mac-mars.sender.warm` | xs-e6b | 1.073 [1.001, 1.150] | 4.653 [4.287, 5.050] | 0.851 [0.728, 0.995] |
| `small-deep.fresh.mac-mars.sender.warm` | xs-cpp | 0.925 [0.899, 0.951] | 4.559 [4.200, 4.948] | 0.830 [0.708, 0.973] |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-e6b | 1.920 [1.730, 2.132] | 1.066 [0.782, 1.454] | 0.929 [0.877, 0.985] |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-cpp | 1.180 [1.019, 1.366] | 1.048 [0.767, 1.431] | 1.028 [0.859, 1.230] |
| `small-deep.noop.mac-mars.sender.warm` | xs-e6b | 1.895 [1.765, 2.034] | 2.348 [2.076, 2.656] | 0.327 [0.281, 0.379] |
| `small-deep.noop.mac-mars.sender.warm` | xs-cpp | 1.506 [1.407, 1.611] | 2.277 [1.963, 2.642] | 0.307 [0.258, 0.365] |
| `small-deep.noop.mars-mac.receiver.warm` | xs-e6b | 8.003 [7.566, 8.465] | 5.019 [4.393, 5.736] | 1.012 [0.932, 1.098] |
| `small-deep.noop.mars-mac.receiver.warm` | xs-cpp | 3.605 [3.426, 3.795] | 5.015 [4.490, 5.601] | 1.051 [0.922, 1.199] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-e6b | 1.071 [0.963, 1.192] | 17.729 [16.707, 18.813] | 0.781 [0.732, 0.833] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-cpp | 0.916 [0.892, 0.940] | 16.017 [15.041, 17.056] | 0.781 [0.698, 0.875] |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-e6b | 0.985 [0.850, 1.142] | 1.022 [0.980, 1.065] | 0.643 [0.592, 0.699] |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-cpp | 0.717 [0.695, 0.739] | 0.867 [0.827, 0.910] | 0.660 [0.628, 0.693] |
| `small-flat.noop.mac-mars.sender.warm` | xs-e6b | 2.063 [1.809, 2.352] | 2.366 [2.082, 2.690] | 0.420 [0.348, 0.507] |
| `small-flat.noop.mac-mars.sender.warm` | xs-cpp | 0.790 [0.635, 0.983] | 1.775 [1.482, 2.125] | 0.251 [0.197, 0.319] |
| `small-flat.noop.mars-mac.receiver.warm` | xs-e6b | 2.976 [2.783, 3.184] | 4.114 [3.691, 4.585] | 0.542 [0.456, 0.645] |
| `small-flat.noop.mars-mac.receiver.warm` | xs-cpp | 0.841 [0.661, 1.070] | 2.104 [1.989, 2.225] | 0.313 [0.290, 0.337] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-e6b |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 9.945 | 5.346 | 5.809 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 10.016 | 4.192 | 4.462 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.539 | 0.378 | 0.419 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | 0.455 | 0.335 | 0.430 |
| `real-congress.fresh.mac-mars.sender.warm` | 44.129 | 31.487 | 32.388 |
| `real-congress.fresh.mars-mac.receiver.warm` | 84.859 | 45.783 | 49.034 |
| `real-congress.noop.mac-mars.sender.warm` | 6.763 | 2.007 | 2.589 |
| `real-congress.noop.mars-mac.receiver.warm` | 5.699 | 2.489 | 3.268 |
| `small-deep.fresh.mac-mars.sender.warm` | 28.934 | 23.962 | 24.612 |
| `small-deep.fresh.mars-mac.receiver.warm` | 47.248 | 48.496 | 43.954 |
| `small-deep.noop.mac-mars.sender.warm` | 11.855 | 3.711 | 3.967 |
| `small-deep.noop.mars-mac.receiver.warm` | 8.940 | 9.394 | 9.046 |
| `small-flat.fresh.mac-mars.sender.warm` | 17.416 | 13.770 | 13.763 |
| `small-flat.fresh.mars-mac.receiver.warm` | 28.582 | 18.926 | 18.479 |
| `small-flat.noop.mac-mars.sender.warm` | 1.715 | 0.495 | 0.782 |
| `small-flat.noop.mars-mac.receiver.warm` | 1.460 | 0.510 | 0.824 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-e6b | 0.3784 | 1287 | 1724 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-cpp | 0.4096 | 1508 | 2020 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-e6b | 0.0365 | 14 | 19 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-cpp | 0.1223 | 137 | 182 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-e6b | 0.1452 | 192 | 256 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-cpp | 0.0943 | 82 | 109 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-e6b | 0.0998 | 92 | 122 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-cpp | 0.0887 | 73 | 97 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-e6b | 0.0320 | 12 | 15 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-cpp | 0.0273 | 9 | 11 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-e6b | 0.0896 | 75 | 99 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-cpp | 0.0685 | 45 | 59 |
| `real-congress.noop.mac-mars.sender.warm` | xs-e6b | 0.1612 | 236 | 315 |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp | 0.1543 | 216 | 289 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-e6b | 0.1283 | 150 | 201 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp | 0.1628 | 240 | 321 |
| `small-deep.fresh.mac-mars.sender.warm` | xs-e6b | 0.1454 | 192 | 257 |
| `small-deep.fresh.mac-mars.sender.warm` | xs-cpp | 0.1515 | 208 | 279 |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-e6b | 0.0545 | 29 | 38 |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-cpp | 0.1701 | 262 | 351 |
| `small-deep.noop.mac-mars.sender.warm` | xs-e6b | 0.1389 | 176 | 235 |
| `small-deep.noop.mac-mars.sender.warm` | xs-cpp | 0.1627 | 240 | 321 |
| `small-deep.noop.mars-mac.receiver.warm` | xs-e6b | 0.0875 | 71 | 95 |
| `small-deep.noop.mars-mac.receiver.warm` | xs-cpp | 0.1408 | 180 | 241 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-e6b | 0.0660 | 42 | 55 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-cpp | 0.1106 | 112 | 150 |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-e6b | 0.0783 | 58 | 76 |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-cpp | 0.0453 | 21 | 27 |
| `small-flat.noop.mac-mars.sender.warm` | xs-e6b | 0.1899 | 326 | 436 |
| `small-flat.noop.mac-mars.sender.warm` | xs-cpp | 0.2247 | 456 | 610 |
| `small-flat.noop.mars-mac.receiver.warm` | xs-e6b | 0.1566 | 223 | 297 |
| `small-flat.noop.mars-mac.receiver.warm` | xs-cpp | 0.0633 | 38 | 51 |

## Voided attempts

- stopped
