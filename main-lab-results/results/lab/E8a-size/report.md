# E8a-size

Descriptive: the xs to rsync ratio as a smooth function of the swept variable, each point with its interval.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220713Z-E8a-size.
- Valid blocks: 192. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.warm` | xs | 6 | 1.018 [1.000, 1.037] | 1.020 [0.987, 1.036] | 0.0938 | too few blocks |
| `scale-size-1024.fresh.neo-freya.sender.warm` | xs | 6 | 0.374 [0.358, 0.390] | 0.375 [0.351, 0.389] | 0.0312 | too few blocks |
| `scale-size-1024.noop.freya-neo.sender.warm` | xs | 6 | 0.331 [0.280, 0.392] | 0.326 [0.277, 0.422] | 0.0312 | too few blocks |
| `scale-size-1024.noop.neo-freya.sender.warm` | xs | 6 | 0.345 [0.325, 0.366] | 0.346 [0.321, 0.377] | 0.0312 | too few blocks |
| `scale-size-1048576.fresh.freya-neo.sender.warm` | xs | 6 | 1.010 [0.902, 1.132] | 1.021 [0.833, 1.117] | 0.8750 | too few blocks |
| `scale-size-1048576.fresh.neo-freya.sender.warm` | xs | 6 | 1.057 [1.050, 1.064] | 1.057 [1.050, 1.066] | 0.0312 | too few blocks |
| `scale-size-1048576.noop.freya-neo.sender.warm` | xs | 6 | 0.932 [0.914, 0.950] | 0.933 [0.912, 0.955] | 0.0312 | too few blocks |
| `scale-size-1048576.noop.neo-freya.sender.warm` | xs | 6 | 0.902 [0.876, 0.929] | 0.902 [0.868, 0.940] | 0.0312 | too few blocks |
| `scale-size-16384.fresh.freya-neo.sender.warm` | xs | 6 | 0.958 [0.919, 0.999] | 0.961 [0.898, 0.996] | 0.0312 | too few blocks |
| `scale-size-16384.fresh.neo-freya.sender.warm` | xs | 6 | 1.035 [1.015, 1.057] | 1.034 [1.013, 1.066] | 0.0312 | too few blocks |
| `scale-size-16384.noop.freya-neo.sender.warm` | xs | 6 | 0.731 [0.710, 0.752] | 0.732 [0.700, 0.751] | 0.0312 | too few blocks |
| `scale-size-16384.noop.neo-freya.sender.warm` | xs | 6 | 0.717 [0.696, 0.738] | 0.717 [0.700, 0.749] | 0.0312 | too few blocks |
| `scale-size-16777216.fresh.freya-neo.sender.warm` | xs | 6 | 0.983 [0.937, 1.032] | 0.993 [0.900, 1.032] | 0.5312 | too few blocks |
| `scale-size-16777216.fresh.neo-freya.sender.warm` | xs | 6 | 1.082 [1.059, 1.105] | 1.077 [1.058, 1.122] | 0.0312 | too few blocks |
| `scale-size-16777216.noop.freya-neo.sender.warm` | xs | 6 | 0.908 [0.873, 0.946] | 0.912 [0.857, 0.945] | 0.0312 | too few blocks |
| `scale-size-16777216.noop.neo-freya.sender.warm` | xs | 6 | 0.900 [0.882, 0.919] | 0.900 [0.877, 0.921] | 0.0312 | too few blocks |
| `scale-size-262144.fresh.freya-neo.sender.warm` | xs | 6 | 1.000 [0.891, 1.122] | 0.998 [0.885, 1.143] | 1.0000 | too few blocks |
| `scale-size-262144.fresh.neo-freya.sender.warm` | xs | 6 | 1.068 [1.048, 1.089] | 1.066 [1.050, 1.101] | 0.0312 | too few blocks |
| `scale-size-262144.noop.freya-neo.sender.warm` | xs | 6 | 0.941 [0.910, 0.973] | 0.940 [0.907, 0.981] | 0.0312 | too few blocks |
| `scale-size-262144.noop.neo-freya.sender.warm` | xs | 6 | 0.907 [0.879, 0.935] | 0.903 [0.871, 0.931] | 0.0312 | too few blocks |
| `scale-size-4096.fresh.freya-neo.sender.warm` | xs | 6 | 0.978 [0.901, 1.061] | 0.995 [0.844, 1.044] | 0.7188 | too few blocks |
| `scale-size-4096.fresh.neo-freya.sender.warm` | xs | 6 | 0.797 [0.634, 1.002] | 0.801 [0.590, 0.994] | 0.0312 | too few blocks |
| `scale-size-4096.noop.freya-neo.sender.warm` | xs | 6 | 0.512 [0.471, 0.556] | 0.509 [0.467, 0.582] | 0.0312 | too few blocks |
| `scale-size-4096.noop.neo-freya.sender.warm` | xs | 6 | 0.475 [0.400, 0.564] | 0.478 [0.408, 0.597] | 0.0312 | too few blocks |
| `scale-size-4194304.fresh.freya-neo.sender.warm` | xs | 6 | 0.996 [0.920, 1.078] | 0.993 [0.886, 1.113] | 0.8438 | too few blocks |
| `scale-size-4194304.fresh.neo-freya.sender.warm` | xs | 6 | 1.077 [1.062, 1.091] | 1.078 [1.055, 1.091] | 0.0312 | too few blocks |
| `scale-size-4194304.noop.freya-neo.sender.warm` | xs | 6 | 0.916 [0.863, 0.973] | 0.921 [0.842, 0.994] | 0.0312 | too few blocks |
| `scale-size-4194304.noop.neo-freya.sender.warm` | xs | 6 | 0.925 [0.894, 0.958] | 0.928 [0.879, 0.956] | 0.0312 | too few blocks |
| `scale-size-65536.fresh.freya-neo.sender.warm` | xs | 6 | 0.972 [0.940, 1.005] | 0.976 [0.920, 1.001] | 0.0625 | too few blocks |
| `scale-size-65536.fresh.neo-freya.sender.warm` | xs | 6 | 1.078 [1.063, 1.093] | 1.078 [1.056, 1.093] | 0.0312 | too few blocks |
| `scale-size-65536.noop.freya-neo.sender.warm` | xs | 6 | 0.896 [0.858, 0.936] | 0.896 [0.845, 0.941] | 0.0312 | too few blocks |
| `scale-size-65536.noop.neo-freya.sender.warm` | xs | 6 | 0.849 [0.826, 0.873] | 0.849 [0.822, 0.877] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.warm` | xs | 1.544 [1.522, 1.566] | 7.675 [7.205, 8.176] | 1.017 [1.001, 1.034] |
| `scale-size-1024.fresh.neo-freya.sender.warm` | xs | 1.259 [1.237, 1.281] | 4.418 [3.882, 5.028] | 0.372 [0.356, 0.389] |
| `scale-size-1024.noop.freya-neo.sender.warm` | xs | 1.286 [1.128, 1.468] | 2.202 [2.146, 2.259] | 0.328 [0.276, 0.390] |
| `scale-size-1024.noop.neo-freya.sender.warm` | xs | 1.345 [1.282, 1.411] | 1.680 [1.624, 1.739] | 0.344 [0.325, 0.365] |
| `scale-size-1048576.fresh.freya-neo.sender.warm` | xs | 2.483 [2.376, 2.595] | 9.328 [9.018, 9.647] | 0.994 [0.984, 1.005] |
| `scale-size-1048576.fresh.neo-freya.sender.warm` | xs | 2.069 [1.959, 2.185] | 7.847 [7.710, 7.987] | 1.057 [1.051, 1.064] |
| `scale-size-1048576.noop.freya-neo.sender.warm` | xs | 1.685 [1.553, 1.828] | 1.283 [1.237, 1.331] | 0.931 [0.912, 0.950] |
| `scale-size-1048576.noop.neo-freya.sender.warm` | xs | 1.415 [1.382, 1.448] | 1.352 [1.306, 1.399] | 0.902 [0.877, 0.927] |
| `scale-size-16384.fresh.freya-neo.sender.warm` | xs | 1.574 [1.478, 1.675] | 9.646 [9.306, 9.998] | 0.988 [0.956, 1.021] |
| `scale-size-16384.fresh.neo-freya.sender.warm` | xs | 1.769 [1.670, 1.873] | 7.877 [7.715, 8.042] | 1.035 [1.018, 1.053] |
| `scale-size-16384.noop.freya-neo.sender.warm` | xs | 1.362 [1.308, 1.418] | 1.462 [1.400, 1.527] | 0.722 [0.701, 0.744] |
| `scale-size-16384.noop.neo-freya.sender.warm` | xs | 1.352 [1.244, 1.468] | 1.629 [1.554, 1.706] | 0.715 [0.694, 0.736] |
| `scale-size-16777216.fresh.freya-neo.sender.warm` | xs | 2.498 [2.417, 2.581] | 9.295 [9.108, 9.485] | 0.999 [0.981, 1.018] |
| `scale-size-16777216.fresh.neo-freya.sender.warm` | xs | 2.130 [2.028, 2.238] | 7.808 [7.588, 8.035] | 1.071 [1.055, 1.086] |
| `scale-size-16777216.noop.freya-neo.sender.warm` | xs | 1.554 [1.420, 1.701] | 1.330 [1.284, 1.379] | 0.902 [0.860, 0.946] |
| `scale-size-16777216.noop.neo-freya.sender.warm` | xs | 1.379 [1.242, 1.530] | 1.341 [1.311, 1.371] | 0.900 [0.881, 0.919] |
| `scale-size-262144.fresh.freya-neo.sender.warm` | xs | 2.162 [2.001, 2.336] | 9.309 [9.030, 9.597] | 0.987 [0.952, 1.023] |
| `scale-size-262144.fresh.neo-freya.sender.warm` | xs | 2.324 [2.189, 2.468] | 7.938 [7.636, 8.252] | 1.069 [1.049, 1.089] |
| `scale-size-262144.noop.freya-neo.sender.warm` | xs | 1.429 [1.278, 1.598] | 1.316 [1.249, 1.386] | 0.938 [0.907, 0.970] |
| `scale-size-262144.noop.neo-freya.sender.warm` | xs | 1.325 [1.249, 1.406] | 1.354 [1.309, 1.402] | 0.905 [0.879, 0.932] |
| `scale-size-4096.fresh.freya-neo.sender.warm` | xs | 1.554 [1.434, 1.685] | 9.761 [9.467, 10.063] | 0.982 [0.901, 1.072] |
| `scale-size-4096.fresh.neo-freya.sender.warm` | xs | 1.488 [1.336, 1.656] | 7.897 [7.463, 8.357] | 0.785 [0.620, 0.995] |
| `scale-size-4096.noop.freya-neo.sender.warm` | xs | 1.289 [1.136, 1.463] | 1.929 [1.867, 1.993] | 0.504 [0.463, 0.548] |
| `scale-size-4096.noop.neo-freya.sender.warm` | xs | 1.280 [0.967, 1.695] | 1.714 [1.678, 1.751] | 0.473 [0.398, 0.563] |
| `scale-size-4194304.fresh.freya-neo.sender.warm` | xs | 2.459 [2.344, 2.581] | 9.297 [9.137, 9.459] | 0.997 [0.991, 1.004] |
| `scale-size-4194304.fresh.neo-freya.sender.warm` | xs | 2.123 [2.067, 2.180] | 7.863 [7.582, 8.154] | 1.070 [1.057, 1.085] |
| `scale-size-4194304.noop.freya-neo.sender.warm` | xs | 1.656 [1.477, 1.857] | 1.349 [1.319, 1.380] | 0.915 [0.862, 0.971] |
| `scale-size-4194304.noop.neo-freya.sender.warm` | xs | 1.419 [1.337, 1.506] | 1.305 [1.250, 1.363] | 0.924 [0.893, 0.955] |
| `scale-size-65536.fresh.freya-neo.sender.warm` | xs | 2.012 [1.857, 2.180] | 9.558 [9.036, 10.110] | 0.991 [0.979, 1.004] |
| `scale-size-65536.fresh.neo-freya.sender.warm` | xs | 2.206 [2.130, 2.285] | 7.820 [7.713, 7.928] | 1.080 [1.065, 1.096] |
| `scale-size-65536.noop.freya-neo.sender.warm` | xs | 1.343 [1.290, 1.399] | 1.374 [1.342, 1.408] | 0.893 [0.853, 0.935] |
| `scale-size-65536.noop.neo-freya.sender.warm` | xs | 1.354 [1.302, 1.408] | 1.431 [1.384, 1.480] | 0.847 [0.823, 0.872] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.warm` | 14.985 | 15.257 |
| `scale-size-1024.fresh.neo-freya.sender.warm` | 23.029 | 8.613 |
| `scale-size-1024.noop.freya-neo.sender.warm` | 1.760 | 0.583 |
| `scale-size-1024.noop.neo-freya.sender.warm` | 2.471 | 0.852 |
| `scale-size-1048576.fresh.freya-neo.sender.warm` | 2.971 | 3.002 |
| `scale-size-1048576.fresh.neo-freya.sender.warm` | 2.495 | 2.637 |
| `scale-size-1048576.noop.freya-neo.sender.warm` | 0.232 | 0.217 |
| `scale-size-1048576.noop.neo-freya.sender.warm` | 0.178 | 0.161 |
| `scale-size-16384.fresh.freya-neo.sender.warm` | 3.238 | 3.103 |
| `scale-size-16384.fresh.neo-freya.sender.warm` | 2.515 | 2.604 |
| `scale-size-16384.noop.freya-neo.sender.warm` | 0.332 | 0.242 |
| `scale-size-16384.noop.neo-freya.sender.warm` | 0.251 | 0.180 |
| `scale-size-16777216.fresh.freya-neo.sender.warm` | 3.155 | 3.101 |
| `scale-size-16777216.fresh.neo-freya.sender.warm` | 2.476 | 2.679 |
| `scale-size-16777216.noop.freya-neo.sender.warm` | 0.236 | 0.214 |
| `scale-size-16777216.noop.neo-freya.sender.warm` | 0.178 | 0.161 |
| `scale-size-262144.fresh.freya-neo.sender.warm` | 2.958 | 2.958 |
| `scale-size-262144.fresh.neo-freya.sender.warm` | 2.485 | 2.656 |
| `scale-size-262144.noop.freya-neo.sender.warm` | 0.235 | 0.222 |
| `scale-size-262144.noop.neo-freya.sender.warm` | 0.182 | 0.165 |
| `scale-size-4096.fresh.freya-neo.sender.warm` | 4.802 | 4.696 |
| `scale-size-4096.fresh.neo-freya.sender.warm` | 3.261 | 2.598 |
| `scale-size-4096.noop.freya-neo.sender.warm` | 0.559 | 0.286 |
| `scale-size-4096.noop.neo-freya.sender.warm` | 0.512 | 0.243 |
| `scale-size-4194304.fresh.freya-neo.sender.warm` | 3.009 | 2.998 |
| `scale-size-4194304.fresh.neo-freya.sender.warm` | 2.484 | 2.675 |
| `scale-size-4194304.noop.freya-neo.sender.warm` | 0.233 | 0.213 |
| `scale-size-4194304.noop.neo-freya.sender.warm` | 0.177 | 0.163 |
| `scale-size-65536.fresh.freya-neo.sender.warm` | 3.170 | 3.081 |
| `scale-size-65536.fresh.neo-freya.sender.warm` | 2.495 | 2.690 |
| `scale-size-65536.noop.freya-neo.sender.warm` | 0.253 | 0.227 |
| `scale-size-65536.noop.neo-freya.sender.warm` | 0.199 | 0.169 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.warm` | xs | 0.0173 | 8 | 8 |
| `scale-size-1024.fresh.neo-freya.sender.warm` | xs | 0.0406 | 17 | 22 |
| `scale-size-1024.noop.freya-neo.sender.warm` | xs | 0.1604 | 233 | 312 |
| `scale-size-1024.noop.neo-freya.sender.warm` | xs | 0.0556 | 30 | 40 |
| `scale-size-1048576.fresh.freya-neo.sender.warm` | xs | 0.1083 | 108 | 144 |
| `scale-size-1048576.fresh.neo-freya.sender.warm` | xs | 0.0062 | 8 | 8 |
| `scale-size-1048576.noop.freya-neo.sender.warm` | xs | 0.0184 | 8 | 8 |
| `scale-size-1048576.noop.neo-freya.sender.warm` | xs | 0.0279 | 9 | 12 |
| `scale-size-16384.fresh.freya-neo.sender.warm` | xs | 0.0400 | 17 | 22 |
| `scale-size-16384.fresh.neo-freya.sender.warm` | xs | 0.0193 | 8 | 8 |
| `scale-size-16384.noop.freya-neo.sender.warm` | xs | 0.0273 | 9 | 11 |
| `scale-size-16384.noop.neo-freya.sender.warm` | xs | 0.0278 | 9 | 12 |
| `scale-size-16777216.fresh.freya-neo.sender.warm` | xs | 0.0460 | 21 | 28 |
| `scale-size-16777216.fresh.neo-freya.sender.warm` | xs | 0.0203 | 8 | 8 |
| `scale-size-16777216.noop.freya-neo.sender.warm` | xs | 0.0381 | 16 | 20 |
| `scale-size-16777216.noop.neo-freya.sender.warm` | xs | 0.0197 | 8 | 8 |
| `scale-size-262144.fresh.freya-neo.sender.warm` | xs | 0.1096 | 110 | 147 |
| `scale-size-262144.fresh.neo-freya.sender.warm` | xs | 0.0185 | 8 | 8 |
| `scale-size-262144.noop.freya-neo.sender.warm` | xs | 0.0320 | 12 | 15 |
| `scale-size-262144.noop.neo-freya.sender.warm` | xs | 0.0292 | 10 | 13 |
| `scale-size-4096.fresh.freya-neo.sender.warm` | xs | 0.0777 | 57 | 75 |
| `scale-size-4096.fresh.neo-freya.sender.warm` | xs | 0.2181 | 429 | 574 |
| `scale-size-4096.noop.freya-neo.sender.warm` | xs | 0.0793 | 59 | 78 |
| `scale-size-4096.noop.neo-freya.sender.warm` | xs | 0.1630 | 241 | 322 |
| `scale-size-4194304.fresh.freya-neo.sender.warm` | xs | 0.0756 | 54 | 71 |
| `scale-size-4194304.fresh.neo-freya.sender.warm` | xs | 0.0129 | 8 | 8 |
| `scale-size-4194304.noop.freya-neo.sender.warm` | xs | 0.0575 | 32 | 42 |
| `scale-size-4194304.noop.neo-freya.sender.warm` | xs | 0.0329 | 12 | 16 |
| `scale-size-65536.fresh.freya-neo.sender.warm` | xs | 0.0321 | 12 | 15 |
| `scale-size-65536.fresh.neo-freya.sender.warm` | xs | 0.0134 | 8 | 8 |
| `scale-size-65536.noop.freya-neo.sender.warm` | xs | 0.0418 | 18 | 23 |
| `scale-size-65536.noop.neo-freya.sender.warm` | xs | 0.0268 | 9 | 11 |
