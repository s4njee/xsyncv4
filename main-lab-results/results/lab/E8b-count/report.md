# E8b-count

Descriptive: the xs to rsync ratio as a smooth function of the swept variable, each point with its interval.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220715Z-E8b-count.
- Valid blocks: 168. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.warm` | xs | 6 | 0.858 [0.784, 0.938] | 0.843 [0.779, 0.987] | 0.0312 | too few blocks |
| `scale-count-1000.fresh.neo-freya.sender.warm` | xs | 6 | 1.020 [0.870, 1.197] | 0.973 [0.932, 1.383] | 0.9688 | too few blocks |
| `scale-count-1000.noop.freya-neo.sender.warm` | xs | 6 | 0.954 [0.905, 1.005] | 0.959 [0.897, 1.027] | 0.0938 | too few blocks |
| `scale-count-1000.noop.neo-freya.sender.warm` | xs | 6 | 0.871 [0.793, 0.956] | 0.891 [0.736, 0.941] | 0.0312 | too few blocks |
| `scale-count-10000.fresh.freya-neo.sender.warm` | xs | 6 | 0.783 [0.683, 0.897] | 0.799 [0.620, 0.880] | 0.0312 | too few blocks |
| `scale-count-10000.fresh.neo-freya.sender.warm` | xs | 6 | 0.900 [0.811, 0.998] | 0.895 [0.798, 1.046] | 0.0938 | too few blocks |
| `scale-count-10000.noop.freya-neo.sender.warm` | xs | 6 | 0.838 [0.786, 0.894] | 0.841 [0.771, 0.893] | 0.0312 | too few blocks |
| `scale-count-10000.noop.neo-freya.sender.warm` | xs | 6 | 0.743 [0.714, 0.772] | 0.750 [0.691, 0.765] | 0.0312 | too few blocks |
| `scale-count-100000.fresh.freya-neo.sender.warm` | xs | 6 | 0.990 [0.925, 1.059] | 1.007 [0.876, 1.042] | 0.8750 | too few blocks |
| `scale-count-100000.fresh.neo-freya.sender.warm` | xs | 6 | 0.586 [0.398, 0.863] | 0.613 [0.354, 0.925] | 0.0312 | too few blocks |
| `scale-count-100000.noop.freya-neo.sender.warm` | xs | 6 | 0.430 [0.390, 0.475] | 0.438 [0.362, 0.483] | 0.0312 | too few blocks |
| `scale-count-100000.noop.neo-freya.sender.warm` | xs | 6 | 0.362 [0.335, 0.390] | 0.358 [0.335, 0.414] | 0.0312 | too few blocks |
| `scale-count-1000000.fresh.freya-neo.sender.warm` | xs | 6 | 0.973 [0.959, 0.987] | 0.975 [0.951, 0.985] | 0.0312 | too few blocks |
| `scale-count-1000000.fresh.neo-freya.sender.warm` | xs | 6 | 0.381 [0.377, 0.386] | 0.381 [0.378, 0.388] | 0.0312 | too few blocks |
| `scale-count-1000000.noop.freya-neo.sender.warm` | xs | 6 | 0.255 [0.198, 0.328] | 0.253 [0.187, 0.358] | 0.0312 | too few blocks |
| `scale-count-1000000.noop.neo-freya.sender.warm` | xs | 6 | 0.334 [0.320, 0.348] | 0.334 [0.316, 0.353] | 0.0312 | too few blocks |
| `scale-count-3000.fresh.freya-neo.sender.warm` | xs | 6 | 0.719 [0.659, 0.784] | 0.714 [0.652, 0.832] | 0.0312 | too few blocks |
| `scale-count-3000.fresh.neo-freya.sender.warm` | xs | 6 | 0.904 [0.819, 0.998] | 0.883 [0.833, 1.077] | 0.0938 | too few blocks |
| `scale-count-3000.noop.freya-neo.sender.warm` | xs | 6 | 0.846 [0.800, 0.894] | 0.847 [0.802, 0.897] | 0.0312 | too few blocks |
| `scale-count-3000.noop.neo-freya.sender.warm` | xs | 6 | 0.861 [0.817, 0.907] | 0.870 [0.788, 0.908] | 0.0312 | too few blocks |
| `scale-count-30000.fresh.freya-neo.sender.warm` | xs | 6 | 0.922 [0.881, 0.965] | 0.928 [0.859, 0.967] | 0.0312 | too few blocks |
| `scale-count-30000.fresh.neo-freya.sender.warm` | xs | 6 | 0.941 [0.882, 1.004] | 0.950 [0.851, 1.024] | 0.0625 | too few blocks |
| `scale-count-30000.noop.freya-neo.sender.warm` | xs | 6 | 0.646 [0.601, 0.693] | 0.644 [0.585, 0.709] | 0.0312 | too few blocks |
| `scale-count-30000.noop.neo-freya.sender.warm` | xs | 6 | 0.593 [0.541, 0.649] | 0.612 [0.497, 0.621] | 0.0312 | too few blocks |
| `scale-count-300000.fresh.freya-neo.sender.warm` | xs | 6 | 0.969 [0.942, 0.997] | 0.969 [0.928, 0.997] | 0.0312 | too few blocks |
| `scale-count-300000.fresh.neo-freya.sender.warm` | xs | 6 | 0.376 [0.357, 0.396] | 0.376 [0.356, 0.405] | 0.0312 | too few blocks |
| `scale-count-300000.noop.freya-neo.sender.warm` | xs | 6 | 0.292 [0.263, 0.323] | 0.296 [0.268, 0.334] | 0.0312 | too few blocks |
| `scale-count-300000.noop.neo-freya.sender.warm` | xs | 6 | 0.327 [0.302, 0.355] | 0.329 [0.286, 0.354] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.warm` | xs | 1.273 [1.041, 1.557] | 1.547 [1.501, 1.594] | 0.841 [0.765, 0.924] |
| `scale-count-1000.fresh.neo-freya.sender.warm` | xs | 1.270 [1.170, 1.379] | 1.505 [1.444, 1.569] | 1.020 [0.865, 1.202] |
| `scale-count-1000.noop.freya-neo.sender.warm` | xs | 1.433 [1.362, 1.507] | 1.322 [1.259, 1.389] | 0.949 [0.899, 1.002] |
| `scale-count-1000.noop.neo-freya.sender.warm` | xs | 1.329 [1.250, 1.412] | 1.350 [1.299, 1.403] | 0.869 [0.791, 0.955] |
| `scale-count-10000.fresh.freya-neo.sender.warm` | xs | 1.271 [1.106, 1.462] | 3.422 [3.294, 3.554] | 0.721 [0.618, 0.840] |
| `scale-count-10000.fresh.neo-freya.sender.warm` | xs | 1.406 [1.341, 1.474] | 2.481 [2.252, 2.733] | 0.900 [0.870, 0.932] |
| `scale-count-10000.noop.freya-neo.sender.warm` | xs | 1.245 [1.161, 1.336] | 1.438 [1.400, 1.478] | 0.831 [0.779, 0.886] |
| `scale-count-10000.noop.neo-freya.sender.warm` | xs | 1.281 [1.100, 1.491] | 1.541 [1.488, 1.597] | 0.740 [0.708, 0.772] |
| `scale-count-100000.fresh.freya-neo.sender.warm` | xs | 1.508 [1.401, 1.624] | 10.056 [9.683, 10.444] | 0.988 [0.921, 1.059] |
| `scale-count-100000.fresh.neo-freya.sender.warm` | xs | 1.486 [1.401, 1.575] | 5.276 [3.628, 7.674] | 0.581 [0.392, 0.860] |
| `scale-count-100000.noop.freya-neo.sender.warm` | xs | 1.260 [1.204, 1.319] | 2.149 [2.076, 2.224] | 0.423 [0.384, 0.466] |
| `scale-count-100000.noop.neo-freya.sender.warm` | xs | 1.103 [1.004, 1.213] | 1.710 [1.664, 1.757] | 0.360 [0.334, 0.389] |
| `scale-count-1000000.fresh.freya-neo.sender.warm` | xs | 1.454 [1.420, 1.488] | 10.658 [10.285, 11.045] | 0.973 [0.960, 0.986] |
| `scale-count-1000000.fresh.neo-freya.sender.warm` | xs | 1.410 [1.385, 1.435] | 2.389 [1.863, 3.065] | 0.381 [0.376, 0.385] |
| `scale-count-1000000.noop.freya-neo.sender.warm` | xs | 1.123 [0.932, 1.354] | 2.246 [2.195, 2.297] | 0.254 [0.197, 0.327] |
| `scale-count-1000000.noop.neo-freya.sender.warm` | xs | 1.322 [1.290, 1.355] | 1.767 [1.708, 1.827] | 0.334 [0.320, 0.348] |
| `scale-count-3000.fresh.freya-neo.sender.warm` | xs | 1.068 [0.959, 1.190] | 2.055 [1.958, 2.157] | 0.689 [0.622, 0.763] |
| `scale-count-3000.fresh.neo-freya.sender.warm` | xs | 1.422 [1.364, 1.482] | 1.680 [1.601, 1.762] | 0.928 [0.770, 1.118] |
| `scale-count-3000.noop.freya-neo.sender.warm` | xs | 1.327 [1.259, 1.397] | 1.354 [1.268, 1.446] | 0.841 [0.791, 0.895] |
| `scale-count-3000.noop.neo-freya.sender.warm` | xs | 1.334 [1.211, 1.469] | 1.369 [1.341, 1.398] | 0.860 [0.815, 0.906] |
| `scale-count-30000.fresh.freya-neo.sender.warm` | xs | 1.486 [1.413, 1.563] | 7.564 [7.264, 7.876] | 0.924 [0.878, 0.973] |
| `scale-count-30000.fresh.neo-freya.sender.warm` | xs | 1.484 [1.375, 1.602] | 5.023 [4.415, 5.714] | 0.936 [0.892, 0.982] |
| `scale-count-30000.noop.freya-neo.sender.warm` | xs | 1.276 [1.165, 1.399] | 1.581 [1.492, 1.674] | 0.640 [0.596, 0.688] |
| `scale-count-30000.noop.neo-freya.sender.warm` | xs | 1.263 [1.171, 1.362] | 1.641 [1.615, 1.668] | 0.591 [0.539, 0.647] |
| `scale-count-300000.fresh.freya-neo.sender.warm` | xs | 1.452 [1.408, 1.497] | 10.728 [10.345, 11.126] | 0.968 [0.937, 1.001] |
| `scale-count-300000.fresh.neo-freya.sender.warm` | xs | 1.385 [1.353, 1.419] | 2.424 [1.765, 3.331] | 0.375 [0.356, 0.396] |
| `scale-count-300000.noop.freya-neo.sender.warm` | xs | 1.262 [1.098, 1.452] | 2.216 [2.171, 2.262] | 0.289 [0.260, 0.321] |
| `scale-count-300000.noop.neo-freya.sender.warm` | xs | 1.325 [1.270, 1.381] | 1.670 [1.637, 1.704] | 0.327 [0.302, 0.355] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.warm` | 0.343 | 0.294 |
| `scale-count-1000.fresh.neo-freya.sender.warm` | 0.228 | 0.232 |
| `scale-count-1000.noop.freya-neo.sender.warm` | 0.233 | 0.223 |
| `scale-count-1000.noop.neo-freya.sender.warm` | 0.189 | 0.165 |
| `scale-count-10000.fresh.freya-neo.sender.warm` | 1.222 | 0.957 |
| `scale-count-10000.fresh.neo-freya.sender.warm` | 0.653 | 0.587 |
| `scale-count-10000.noop.freya-neo.sender.warm` | 0.278 | 0.233 |
| `scale-count-10000.noop.neo-freya.sender.warm` | 0.228 | 0.169 |
| `scale-count-100000.fresh.freya-neo.sender.warm` | 6.929 | 6.856 |
| `scale-count-100000.fresh.neo-freya.sender.warm` | 5.961 | 3.495 |
| `scale-count-100000.noop.freya-neo.sender.warm` | 0.744 | 0.320 |
| `scale-count-100000.noop.neo-freya.sender.warm` | 0.760 | 0.275 |
| `scale-count-1000000.fresh.freya-neo.sender.warm` | 67.057 | 65.246 |
| `scale-count-1000000.fresh.neo-freya.sender.warm` | 103.8 | 39.550 |
| `scale-count-1000000.noop.freya-neo.sender.warm` | 9.951 | 2.534 |
| `scale-count-1000000.noop.neo-freya.sender.warm` | 11.382 | 3.799 |
| `scale-count-3000.fresh.freya-neo.sender.warm` | 0.624 | 0.449 |
| `scale-count-3000.fresh.neo-freya.sender.warm` | 0.364 | 0.329 |
| `scale-count-3000.noop.freya-neo.sender.warm` | 0.255 | 0.216 |
| `scale-count-3000.noop.neo-freya.sender.warm` | 0.192 | 0.165 |
| `scale-count-30000.fresh.freya-neo.sender.warm` | 2.554 | 2.355 |
| `scale-count-30000.fresh.neo-freya.sender.warm` | 1.328 | 1.250 |
| `scale-count-30000.noop.freya-neo.sender.warm` | 0.388 | 0.251 |
| `scale-count-30000.noop.neo-freya.sender.warm` | 0.324 | 0.192 |
| `scale-count-300000.fresh.freya-neo.sender.warm` | 20.226 | 19.601 |
| `scale-count-300000.fresh.neo-freya.sender.warm` | 29.247 | 10.998 |
| `scale-count-300000.noop.freya-neo.sender.warm` | 2.197 | 0.641 |
| `scale-count-300000.noop.neo-freya.sender.warm` | 2.829 | 0.926 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.warm` | xs | 0.0857 | 68 | 91 |
| `scale-count-1000.fresh.neo-freya.sender.warm` | xs | 0.1520 | 210 | 280 |
| `scale-count-1000.noop.freya-neo.sender.warm` | xs | 0.0499 | 25 | 32 |
| `scale-count-1000.noop.neo-freya.sender.warm` | xs | 0.0896 | 74 | 99 |
| `scale-count-10000.fresh.freya-neo.sender.warm` | xs | 0.1294 | 153 | 204 |
| `scale-count-10000.fresh.neo-freya.sender.warm` | xs | 0.0989 | 90 | 120 |
| `scale-count-10000.noop.freya-neo.sender.warm` | xs | 0.0613 | 36 | 48 |
| `scale-count-10000.noop.neo-freya.sender.warm` | xs | 0.0372 | 15 | 19 |
| `scale-count-100000.fresh.freya-neo.sender.warm` | xs | 0.0647 | 40 | 53 |
| `scale-count-100000.fresh.neo-freya.sender.warm` | xs | 0.3686 | 1222 | 1637 |
| `scale-count-100000.noop.freya-neo.sender.warm` | xs | 0.0944 | 82 | 110 |
| `scale-count-100000.noop.neo-freya.sender.warm` | xs | 0.0729 | 50 | 66 |
| `scale-count-1000000.fresh.freya-neo.sender.warm` | xs | 0.0137 | 8 | 8 |
| `scale-count-1000000.fresh.neo-freya.sender.warm` | xs | 0.0116 | 8 | 8 |
| `scale-count-1000000.noop.freya-neo.sender.warm` | xs | 0.2411 | 524 | 701 |
| `scale-count-1000000.noop.neo-freya.sender.warm` | xs | 0.0410 | 18 | 23 |
| `scale-count-3000.fresh.freya-neo.sender.warm` | xs | 0.0829 | 64 | 85 |
| `scale-count-3000.fresh.neo-freya.sender.warm` | xs | 0.0943 | 82 | 109 |
| `scale-count-3000.noop.freya-neo.sender.warm` | xs | 0.0531 | 28 | 36 |
| `scale-count-3000.noop.neo-freya.sender.warm` | xs | 0.0496 | 25 | 32 |
| `scale-count-30000.fresh.freya-neo.sender.warm` | xs | 0.0435 | 19 | 25 |
| `scale-count-30000.fresh.neo-freya.sender.warm` | xs | 0.0617 | 37 | 48 |
| `scale-count-30000.noop.freya-neo.sender.warm` | xs | 0.0680 | 44 | 58 |
| `scale-count-30000.noop.neo-freya.sender.warm` | xs | 0.0868 | 70 | 93 |
| `scale-count-300000.fresh.freya-neo.sender.warm` | xs | 0.0273 | 9 | 11 |
| `scale-count-300000.fresh.neo-freya.sender.warm` | xs | 0.0497 | 25 | 32 |
| `scale-count-300000.noop.freya-neo.sender.warm` | xs | 0.0972 | 87 | 116 |
| `scale-count-300000.noop.neo-freya.sender.warm` | xs | 0.0783 | 57 | 76 |
