# E8a2-size-cold

Descriptive: the xs to rsync ratio as a smooth function of the swept variable, each point with its interval.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220941Z-E8a2-size-cold.
- Valid blocks: 128. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.cold` | xs | 4 | 0.746 [0.721, 0.772] | 0.751 | 0.1250 | too few blocks |
| `scale-size-1024.fresh.neo-freya.sender.cold` | xs | 4 | 0.381 [0.370, 0.392] | 0.381 | 0.1250 | too few blocks |
| `scale-size-1024.noop.freya-neo.sender.cold` | xs | 4 | 0.211 [0.196, 0.228] | 0.214 | 0.1250 | too few blocks |
| `scale-size-1024.noop.neo-freya.sender.cold` | xs | 4 | 0.226 [0.208, 0.245] | 0.226 | 0.1250 | too few blocks |
| `scale-size-1048576.fresh.freya-neo.sender.cold` | xs | 4 | 0.976 [0.973, 0.980] | 0.977 | 0.1250 | too few blocks |
| `scale-size-1048576.fresh.neo-freya.sender.cold` | xs | 4 | 1.001 [0.985, 1.017] | 1.001 | 0.8750 | too few blocks |
| `scale-size-1048576.noop.freya-neo.sender.cold` | xs | 4 | 0.924 [0.852, 1.001] | 0.924 | 0.1250 | too few blocks |
| `scale-size-1048576.noop.neo-freya.sender.cold` | xs | 4 | 0.927 [0.826, 1.041] | 0.927 | 0.1250 | too few blocks |
| `scale-size-16384.fresh.freya-neo.sender.cold` | xs | 4 | 0.974 [0.955, 0.994] | 0.975 | 0.1250 | too few blocks |
| `scale-size-16384.fresh.neo-freya.sender.cold` | xs | 4 | 0.997 [0.980, 1.014] | 0.994 | 0.6250 | too few blocks |
| `scale-size-16384.noop.freya-neo.sender.cold` | xs | 4 | 0.593 [0.485, 0.727] | 0.601 | 0.1250 | too few blocks |
| `scale-size-16384.noop.neo-freya.sender.cold` | xs | 4 | 0.579 [0.563, 0.596] | 0.580 | 0.1250 | too few blocks |
| `scale-size-16777216.fresh.freya-neo.sender.cold` | xs | 4 | 0.978 [0.965, 0.992] | 0.979 | 0.1250 | too few blocks |
| `scale-size-16777216.fresh.neo-freya.sender.cold` | xs | 4 | 0.999 [0.985, 1.012] | 1.000 | 0.8750 | too few blocks |
| `scale-size-16777216.noop.freya-neo.sender.cold` | xs | 4 | 0.974 [0.934, 1.016] | 0.974 | 0.2500 | too few blocks |
| `scale-size-16777216.noop.neo-freya.sender.cold` | xs | 4 | 0.936 [0.892, 0.983] | 0.936 | 0.1250 | too few blocks |
| `scale-size-262144.fresh.freya-neo.sender.cold` | xs | 4 | 0.969 [0.950, 0.988] | 0.969 | 0.1250 | too few blocks |
| `scale-size-262144.fresh.neo-freya.sender.cold` | xs | 4 | 1.001 [0.990, 1.013] | 1.001 | 1.0000 | too few blocks |
| `scale-size-262144.noop.freya-neo.sender.cold` | xs | 4 | 0.993 [0.959, 1.028] | 0.990 | 0.5000 | too few blocks |
| `scale-size-262144.noop.neo-freya.sender.cold` | xs | 4 | 0.926 [0.889, 0.964] | 0.924 | 0.1250 | too few blocks |
| `scale-size-4096.fresh.freya-neo.sender.cold` | xs | 4 | 0.427 [0.417, 0.438] | 0.427 | 0.1250 | too few blocks |
| `scale-size-4096.fresh.neo-freya.sender.cold` | xs | 4 | 0.448 [0.435, 0.461] | 0.448 | 0.1250 | too few blocks |
| `scale-size-4096.noop.freya-neo.sender.cold` | xs | 4 | 0.329 [0.309, 0.349] | 0.328 | 0.1250 | too few blocks |
| `scale-size-4096.noop.neo-freya.sender.cold` | xs | 4 | 0.334 [0.314, 0.355] | 0.334 | 0.1250 | too few blocks |
| `scale-size-4194304.fresh.freya-neo.sender.cold` | xs | 4 | 0.977 [0.967, 0.988] | 0.977 | 0.1250 | too few blocks |
| `scale-size-4194304.fresh.neo-freya.sender.cold` | xs | 4 | 1.001 [0.989, 1.012] | 1.001 | 0.8750 | too few blocks |
| `scale-size-4194304.noop.freya-neo.sender.cold` | xs | 4 | 1.012 [0.886, 1.156] | 0.989 | 1.0000 | too few blocks |
| `scale-size-4194304.noop.neo-freya.sender.cold` | xs | 4 | 0.937 [0.910, 0.965] | 0.938 | 0.1250 | too few blocks |
| `scale-size-65536.fresh.freya-neo.sender.cold` | xs | 4 | 0.970 [0.949, 0.992] | 0.971 | 0.1250 | too few blocks |
| `scale-size-65536.fresh.neo-freya.sender.cold` | xs | 4 | 1.003 [0.994, 1.012] | 1.005 | 0.3750 | too few blocks |
| `scale-size-65536.noop.freya-neo.sender.cold` | xs | 4 | 0.843 [0.801, 0.887] | 0.851 | 0.1250 | too few blocks |
| `scale-size-65536.noop.neo-freya.sender.cold` | xs | 4 | 0.821 [0.780, 0.864] | 0.821 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.cold` | xs | 1.315 [1.304, 1.325] | 7.159 [6.183, 8.289] | 0.744 [0.721, 0.767] |
| `scale-size-1024.fresh.neo-freya.sender.cold` | xs | 1.134 [1.120, 1.147] | 4.832 [4.559, 5.121] | 0.379 [0.367, 0.392] |
| `scale-size-1024.noop.freya-neo.sender.cold` | xs | 1.205 [1.188, 1.221] | 2.189 [2.042, 2.347] | 0.210 [0.194, 0.226] |
| `scale-size-1024.noop.neo-freya.sender.cold` | xs | 1.173 [1.158, 1.189] | 1.782 [1.622, 1.958] | 0.226 [0.208, 0.245] |
| `scale-size-1048576.fresh.freya-neo.sender.cold` | xs | 1.892 [1.866, 1.919] | 9.660 [8.958, 10.417] | 0.971 [0.966, 0.975] |
| `scale-size-1048576.fresh.neo-freya.sender.cold` | xs | 1.453 [1.348, 1.568] | 7.914 [7.809, 8.021] | 1.003 [0.994, 1.013] |
| `scale-size-1048576.noop.freya-neo.sender.cold` | xs | 1.410 [1.377, 1.444] | 1.328 [1.259, 1.401] | 0.920 [0.848, 1.000] |
| `scale-size-1048576.noop.neo-freya.sender.cold` | xs | 1.329 [1.259, 1.404] | 1.302 [1.292, 1.313] | 0.925 [0.826, 1.036] |
| `scale-size-16384.fresh.freya-neo.sender.cold` | xs | 1.314 [1.202, 1.436] | 9.655 [9.419, 9.897] | 0.968 [0.945, 0.993] |
| `scale-size-16384.fresh.neo-freya.sender.cold` | xs | 1.321 [1.267, 1.377] | 8.042 [7.826, 8.264] | 0.995 [0.984, 1.006] |
| `scale-size-16384.noop.freya-neo.sender.cold` | xs | 1.259 [1.226, 1.293] | 1.492 [1.385, 1.608] | 0.586 [0.477, 0.719] |
| `scale-size-16384.noop.neo-freya.sender.cold` | xs | 1.195 [1.171, 1.220] | 1.589 [1.537, 1.643] | 0.579 [0.562, 0.596] |
| `scale-size-16777216.fresh.freya-neo.sender.cold` | xs | 1.809 [1.743, 1.877] | 9.676 [9.354, 10.009] | 0.977 [0.969, 0.985] |
| `scale-size-16777216.fresh.neo-freya.sender.cold` | xs | 1.395 [1.330, 1.464] | 7.850 [7.630, 8.075] | 1.001 [0.995, 1.008] |
| `scale-size-16777216.noop.freya-neo.sender.cold` | xs | 1.491 [1.472, 1.511] | 1.328 [1.272, 1.387] | 0.973 [0.932, 1.016] |
| `scale-size-16777216.noop.neo-freya.sender.cold` | xs | 1.368 [1.303, 1.438] | 1.300 [1.252, 1.351] | 0.934 [0.890, 0.981] |
| `scale-size-262144.fresh.freya-neo.sender.cold` | xs | 1.667 [1.590, 1.748] | 9.659 [9.302, 10.030] | 0.964 [0.940, 0.988] |
| `scale-size-262144.fresh.neo-freya.sender.cold` | xs | 1.443 [1.329, 1.566] | 7.847 [7.785, 7.910] | 1.001 [0.989, 1.012] |
| `scale-size-262144.noop.freya-neo.sender.cold` | xs | 1.259 [1.223, 1.295] | 1.320 [1.249, 1.396] | 0.992 [0.950, 1.036] |
| `scale-size-262144.noop.neo-freya.sender.cold` | xs | 1.238 [1.209, 1.269] | 1.343 [1.286, 1.402] | 0.925 [0.890, 0.962] |
| `scale-size-4096.fresh.freya-neo.sender.cold` | xs | 1.381 [1.363, 1.398] | 8.333 [8.179, 8.490] | 0.413 [0.401, 0.426] |
| `scale-size-4096.fresh.neo-freya.sender.cold` | xs | 1.179 [1.158, 1.200] | 7.093 [6.286, 8.002] | 0.439 [0.431, 0.446] |
| `scale-size-4096.noop.freya-neo.sender.cold` | xs | 1.229 [1.216, 1.242] | 1.902 [1.713, 2.112] | 0.325 [0.307, 0.344] |
| `scale-size-4096.noop.neo-freya.sender.cold` | xs | 1.172 [1.149, 1.194] | 1.618 [1.541, 1.699] | 0.333 [0.313, 0.354] |
| `scale-size-4194304.fresh.freya-neo.sender.cold` | xs | 1.766 [1.727, 1.805] | 9.537 [8.831, 10.300] | 0.972 [0.958, 0.986] |
| `scale-size-4194304.fresh.neo-freya.sender.cold` | xs | 1.384 [1.246, 1.539] | 8.109 [7.896, 8.327] | 1.001 [0.994, 1.008] |
| `scale-size-4194304.noop.freya-neo.sender.cold` | xs | 1.419 [1.205, 1.671] | 1.335 [1.286, 1.386] | 1.011 [0.880, 1.160] |
| `scale-size-4194304.noop.neo-freya.sender.cold` | xs | 1.342 [1.302, 1.383] | 1.304 [1.277, 1.332] | 0.940 [0.914, 0.966] |
| `scale-size-65536.fresh.freya-neo.sender.cold` | xs | 1.470 [1.358, 1.590] | 9.754 [9.374, 10.149] | 0.957 [0.938, 0.976] |
| `scale-size-65536.fresh.neo-freya.sender.cold` | xs | 1.446 [1.369, 1.527] | 7.935 [7.804, 8.069] | 0.999 [0.992, 1.005] |
| `scale-size-65536.noop.freya-neo.sender.cold` | xs | 1.236 [1.191, 1.283] | 1.363 [1.280, 1.452] | 0.839 [0.796, 0.884] |
| `scale-size-65536.noop.neo-freya.sender.cold` | xs | 1.245 [1.189, 1.303] | 1.383 [1.292, 1.480] | 0.819 [0.776, 0.863] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.cold` | 17.118 | 12.767 |
| `scale-size-1024.fresh.neo-freya.sender.cold` | 22.926 | 8.730 |
| `scale-size-1024.noop.freya-neo.sender.cold` | 3.827 | 0.808 |
| `scale-size-1024.noop.neo-freya.sender.cold` | 3.607 | 0.815 |
| `scale-size-1048576.fresh.freya-neo.sender.cold` | 3.243 | 3.167 |
| `scale-size-1048576.fresh.neo-freya.sender.cold` | 2.490 | 2.492 |
| `scale-size-1048576.noop.freya-neo.sender.cold` | 0.246 | 0.227 |
| `scale-size-1048576.noop.neo-freya.sender.cold` | 0.189 | 0.175 |
| `scale-size-16384.fresh.freya-neo.sender.cold` | 3.349 | 3.262 |
| `scale-size-16384.fresh.neo-freya.sender.cold` | 2.540 | 2.532 |
| `scale-size-16384.noop.freya-neo.sender.cold` | 0.463 | 0.274 |
| `scale-size-16384.noop.neo-freya.sender.cold` | 0.377 | 0.218 |
| `scale-size-16777216.fresh.freya-neo.sender.cold` | 3.241 | 3.170 |
| `scale-size-16777216.fresh.neo-freya.sender.cold` | 2.489 | 2.486 |
| `scale-size-16777216.noop.freya-neo.sender.cold` | 0.235 | 0.229 |
| `scale-size-16777216.noop.neo-freya.sender.cold` | 0.182 | 0.171 |
| `scale-size-262144.fresh.freya-neo.sender.cold` | 3.281 | 3.180 |
| `scale-size-262144.fresh.neo-freya.sender.cold` | 2.494 | 2.496 |
| `scale-size-262144.noop.freya-neo.sender.cold` | 0.243 | 0.241 |
| `scale-size-262144.noop.neo-freya.sender.cold` | 0.200 | 0.185 |
| `scale-size-4096.fresh.freya-neo.sender.cold` | 8.903 | 3.805 |
| `scale-size-4096.fresh.neo-freya.sender.cold` | 5.945 | 2.664 |
| `scale-size-4096.noop.freya-neo.sender.cold` | 1.149 | 0.378 |
| `scale-size-4096.noop.neo-freya.sender.cold` | 0.992 | 0.331 |
| `scale-size-4194304.fresh.freya-neo.sender.cold` | 3.230 | 3.157 |
| `scale-size-4194304.fresh.neo-freya.sender.cold` | 2.488 | 2.490 |
| `scale-size-4194304.noop.freya-neo.sender.cold` | 0.238 | 0.241 |
| `scale-size-4194304.noop.neo-freya.sender.cold` | 0.181 | 0.170 |
| `scale-size-65536.fresh.freya-neo.sender.cold` | 3.341 | 3.241 |
| `scale-size-65536.fresh.neo-freya.sender.cold` | 2.498 | 2.506 |
| `scale-size-65536.noop.freya-neo.sender.cold` | 0.295 | 0.248 |
| `scale-size-65536.noop.neo-freya.sender.cold` | 0.231 | 0.190 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `scale-size-1024.fresh.freya-neo.sender.cold` | xs | 0.0216 | 8 | 8 |
| `scale-size-1024.fresh.neo-freya.sender.cold` | xs | 0.0184 | 8 | 8 |
| `scale-size-1024.noop.freya-neo.sender.cold` | xs | 0.0475 | 23 | 30 |
| `scale-size-1024.noop.neo-freya.sender.cold` | xs | 0.0515 | 26 | 34 |
| `scale-size-1048576.fresh.freya-neo.sender.cold` | xs | 0.0022 | 8 | 8 |
| `scale-size-1048576.fresh.neo-freya.sender.cold` | xs | 0.0102 | 8 | 8 |
| `scale-size-1048576.noop.freya-neo.sender.cold` | xs | 0.0508 | 26 | 34 |
| `scale-size-1048576.noop.neo-freya.sender.cold` | xs | 0.0727 | 50 | 66 |
| `scale-size-16384.fresh.freya-neo.sender.cold` | xs | 0.0126 | 8 | 8 |
| `scale-size-16384.fresh.neo-freya.sender.cold` | xs | 0.0109 | 8 | 8 |
| `scale-size-16384.noop.freya-neo.sender.cold` | xs | 0.1274 | 148 | 198 |
| `scale-size-16384.noop.neo-freya.sender.cold` | xs | 0.0177 | 8 | 8 |
| `scale-size-16777216.fresh.freya-neo.sender.cold` | xs | 0.0086 | 8 | 8 |
| `scale-size-16777216.fresh.neo-freya.sender.cold` | xs | 0.0083 | 8 | 8 |
| `scale-size-16777216.noop.freya-neo.sender.cold` | xs | 0.0264 | 9 | 11 |
| `scale-size-16777216.noop.neo-freya.sender.cold` | xs | 0.0307 | 11 | 14 |
| `scale-size-262144.fresh.freya-neo.sender.cold` | xs | 0.0124 | 8 | 8 |
| `scale-size-262144.fresh.neo-freya.sender.cold` | xs | 0.0073 | 8 | 8 |
| `scale-size-262144.noop.freya-neo.sender.cold` | xs | 0.0218 | 8 | 8 |
| `scale-size-262144.noop.neo-freya.sender.cold` | xs | 0.0252 | 8 | 10 |
| `scale-size-4096.fresh.freya-neo.sender.cold` | xs | 0.0150 | 8 | 8 |
| `scale-size-4096.fresh.neo-freya.sender.cold` | xs | 0.0180 | 8 | 8 |
| `scale-size-4096.noop.freya-neo.sender.cold` | xs | 0.0383 | 16 | 20 |
| `scale-size-4096.noop.neo-freya.sender.cold` | xs | 0.0387 | 16 | 21 |
| `scale-size-4194304.fresh.freya-neo.sender.cold` | xs | 0.0066 | 8 | 8 |
| `scale-size-4194304.fresh.neo-freya.sender.cold` | xs | 0.0074 | 8 | 8 |
| `scale-size-4194304.noop.freya-neo.sender.cold` | xs | 0.0835 | 65 | 86 |
| `scale-size-4194304.noop.neo-freya.sender.cold` | xs | 0.0186 | 8 | 8 |
| `scale-size-65536.fresh.freya-neo.sender.cold` | xs | 0.0138 | 8 | 8 |
| `scale-size-65536.fresh.neo-freya.sender.cold` | xs | 0.0057 | 8 | 8 |
| `scale-size-65536.noop.freya-neo.sender.cold` | xs | 0.0322 | 12 | 15 |
| `scale-size-65536.noop.neo-freya.sender.cold` | xs | 0.0322 | 12 | 15 |
