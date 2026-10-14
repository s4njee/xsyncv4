# T1g-send-cores

Three sending workers on a four-core sender keep most of one worker's gain on byte-bound copies and lose nothing on small files or no-ops.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T175325Z-T1g-send-cores.
- Valid blocks: 80. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 10 | 0.991 [0.983, 0.998] | 0.989 [0.983, 0.998] | 0.0234 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 10 | 0.990 [0.957, 1.025] | 0.980 [0.968, 1.044] | 0.6074 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 10 | 0.983 [0.976, 0.989] | 0.981 [0.976, 0.989] | 0.0020 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 10 | 0.971 [0.963, 0.979] | 0.973 [0.962, 0.979] | 0.0020 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3 | 10 | 0.993 [0.942, 1.046] | 0.978 [0.945, 1.046] | 0.7598 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 10 | 1.023 [1.000, 1.046] | 1.022 [1.003, 1.048] | 0.0527 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3s1 | 10 | 0.993 [0.961, 1.026] | 0.993 [0.961, 1.020] | 0.6348 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 10 | 1.480 [1.442, 1.518] | 1.477 [1.441, 1.520] | 0.0020 | slower |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 10 | 0.987 [0.977, 0.996] | 0.988 [0.978, 0.998] | 0.0078 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 10 | 0.969 [0.961, 0.977] | 0.968 [0.962, 0.977] | 0.0020 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 10 | 0.966 [0.957, 0.974] | 0.964 [0.959, 0.974] | 0.0020 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 10 | 0.962 [0.955, 0.970] | 0.961 [0.955, 0.971] | 0.0020 | faster |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3 | 10 | 1.000 [0.973, 1.027] | 1.000 [0.971, 1.029] | 0.9863 | equivalent |
| `mixed-threshold.noop.neo-freya.sender.warm` | send2 | 10 | 1.013 [0.983, 1.043] | 1.011 [0.985, 1.044] | 0.3711 | inconclusive |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3s1 | 10 | 1.006 [0.974, 1.038] | 1.006 [0.971, 1.038] | 0.6777 | inconclusive |
| `mixed-threshold.noop.neo-freya.sender.warm` | rsync | 10 | 1.138 [1.121, 1.156] | 1.137 [1.121, 1.156] | 0.0020 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 10 | 0.984 [0.958, 1.010] | 0.979 [0.955, 1.015] | 0.1484 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 10 | 1.043 [0.985, 1.103] | 1.025 [0.989, 1.105] | 0.1562 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | send3s1 | 10 | 0.994 [0.970, 1.018] | 0.995 [0.972, 1.020] | 0.5781 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 10 | 1.419 [1.216, 1.655] | 1.391 [1.226, 1.651] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | send3 | 10 | 1.032 [0.939, 1.134] | 1.030 [0.945, 1.134] | 0.4648 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 10 | 1.138 [1.055, 1.228] | 1.135 [1.068, 1.228] | 0.0078 | slower |
| `small-flat.noop.neo-freya.sender.warm` | send3s1 | 10 | 1.027 [0.968, 1.089] | 1.039 [0.965, 1.088] | 0.3223 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 10 | 2.418 [2.239, 2.613] | 2.448 [2.235, 2.602] | 0.0020 | slower |
| `small-real.fresh.neo-freya.sender.warm` | send3 | 10 | 1.108 [0.961, 1.279] | 1.001 [0.992, 1.272] | 0.2480 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 10 | 1.098 [0.965, 1.250] | 1.024 [0.994, 1.247] | 0.1328 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | send3s1 | 10 | 1.052 [0.976, 1.133] | 1.006 [0.997, 1.150] | 0.1523 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 10 | 1.225 [1.114, 1.346] | 1.230 [1.086, 1.380] | 0.0020 | slower |
| `small-real.noop.neo-freya.sender.warm` | send3 | 10 | 1.242 [1.049, 1.471] | 1.203 [1.044, 1.474] | 0.0137 | slower |
| `small-real.noop.neo-freya.sender.warm` | send2 | 10 | 0.954 [0.792, 1.149] | 0.958 [0.794, 1.132] | 0.5625 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | send3s1 | 10 | 1.226 [1.009, 1.488] | 1.237 [1.018, 1.489] | 0.0430 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | rsync | 10 | 1.530 [1.303, 1.796] | 1.528 [1.291, 1.818] | 0.0020 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 0.966 [0.939, 0.995] | 0.990 [0.983, 0.997] | 0.981 [0.976, 0.986] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.874 [0.850, 0.899] | 0.991 [0.958, 1.024] | 0.963 [0.959, 0.966] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 0.896 [0.883, 0.908] | 0.983 [0.974, 0.993] | 0.986 [0.981, 0.990] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.474 [0.462, 0.485] | 0.974 [0.966, 0.982] | 0.125 [0.120, 0.130] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3 | 0.904 [0.857, 0.953] | 0.994 [0.944, 1.047] | 1.006 [0.993, 1.020] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 0.825 [0.778, 0.874] | 1.025 [1.002, 1.048] | 0.995 [0.980, 1.011] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3s1 | 0.906 [0.852, 0.963] | 0.995 [0.963, 1.028] | 0.995 [0.980, 1.009] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.534 [0.503, 0.566] | 1.475 [1.438, 1.513] | 0.718 [0.692, 0.745] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 0.959 [0.929, 0.991] | 0.987 [0.978, 0.996] | 0.981 [0.978, 0.984] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 0.852 [0.825, 0.880] | 0.969 [0.961, 0.977] | 0.964 [0.961, 0.968] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 0.726 [0.702, 0.752] | 0.966 [0.958, 0.974] | 0.980 [0.974, 0.987] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.464 [0.450, 0.478] | 0.962 [0.955, 0.970] | 0.126 [0.123, 0.129] |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3 | 0.924 [0.875, 0.976] | 1.028 [0.952, 1.111] | 0.994 [0.969, 1.020] |
| `mixed-threshold.noop.neo-freya.sender.warm` | send2 | 0.838 [0.799, 0.879] | 1.013 [0.984, 1.044] | 0.994 [0.974, 1.016] |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3s1 | 0.949 [0.916, 0.983] | 1.005 [0.975, 1.037] | 0.991 [0.976, 1.008] |
| `mixed-threshold.noop.neo-freya.sender.warm` | rsync | 0.549 [0.519, 0.582] | 1.137 [1.121, 1.154] | 0.742 [0.731, 0.752] |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 0.963 [0.943, 0.983] | 0.969 [0.944, 0.996] | 0.919 [0.826, 1.021] |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 0.875 [0.838, 0.914] | 1.028 [0.966, 1.094] | 0.561 [0.505, 0.623] |
| `small-flat.fresh.neo-freya.sender.warm` | send3s1 | 0.972 [0.952, 0.992] | 0.979 [0.950, 1.010] | 0.886 [0.805, 0.974] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.651 [0.633, 0.670] | 1.389 [1.190, 1.621] | 0.148 [0.122, 0.179] |
| `small-flat.noop.neo-freya.sender.warm` | send3 | 0.977 [0.859, 1.110] | 1.033 [0.940, 1.135] | 0.987 [0.972, 1.002] |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 0.861 [0.780, 0.950] | 1.156 [1.067, 1.254] | 0.979 [0.964, 0.995] |
| `small-flat.noop.neo-freya.sender.warm` | send3s1 | 0.961 [0.862, 1.071] | 1.028 [0.970, 1.088] | 0.983 [0.966, 1.000] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.736 [0.673, 0.805] | 2.409 [2.231, 2.601] | 0.574 [0.563, 0.585] |
| `small-real.fresh.neo-freya.sender.warm` | send3 | 0.970 [0.957, 0.983] | 1.108 [0.963, 1.275] | 0.995 [0.961, 1.030] |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 0.904 [0.881, 0.928] | 1.099 [0.966, 1.251] | 0.832 [0.788, 0.879] |
| `small-real.fresh.neo-freya.sender.warm` | send3s1 | 0.958 [0.942, 0.976] | 1.052 [0.975, 1.136] | 1.011 [0.990, 1.033] |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.505 [0.498, 0.512] | 1.219 [1.108, 1.340] | 0.097 [0.097, 0.098] |
| `small-real.noop.neo-freya.sender.warm` | send3 | 0.913 [0.836, 0.997] | 1.241 [1.049, 1.469] | 1.048 [0.999, 1.099] |
| `small-real.noop.neo-freya.sender.warm` | send2 | 0.948 [0.888, 1.013] | 0.954 [0.792, 1.149] | 1.060 [1.003, 1.120] |
| `small-real.noop.neo-freya.sender.warm` | send3s1 | 0.959 [0.881, 1.043] | 1.225 [1.009, 1.487] | 1.068 [1.003, 1.138] |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.127 [0.121, 0.133] | 1.529 [1.302, 1.794] | 0.217 [0.204, 0.232] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | send2 | send3 | send3s1 | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.263 | 12.504 | 12.510 | 12.409 | 12.628 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.284 | 0.196 | 0.190 | 0.190 | 0.192 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.151 | 13.243 | 13.489 | 13.200 | 13.669 |
| `mixed-threshold.noop.neo-freya.sender.warm` | 0.185 | 0.164 | 0.162 | 0.163 | 0.162 |
| `small-flat.fresh.neo-freya.sender.warm` | 4.864 | 3.574 | 3.372 | 3.408 | 3.428 |
| `small-flat.noop.neo-freya.sender.warm` | 0.660 | 0.311 | 0.282 | 0.280 | 0.273 |
| `small-real.fresh.neo-freya.sender.warm` | 13.599 | 12.193 | 12.308 | 11.679 | 11.104 |
| `small-real.noop.neo-freya.sender.warm` | 2.275 | 1.418 | 1.847 | 1.823 | 1.487 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 0.0105 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.0482 | 23 | 30 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 0.0097 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0119 | 8 | 8 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3 | 0.0735 | 51 | 68 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 0.0317 | 12 | 15 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send3s1 | 0.0456 | 21 | 28 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.0358 | 14 | 18 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 0.0133 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 0.0113 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 0.0121 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.0109 | 8 | 8 |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3 | 0.0379 | 15 | 20 |
| `mixed-threshold.noop.neo-freya.sender.warm` | send2 | 0.0416 | 18 | 23 |
| `mixed-threshold.noop.neo-freya.sender.warm` | send3s1 | 0.0447 | 20 | 26 |
| `mixed-threshold.noop.neo-freya.sender.warm` | rsync | 0.0214 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 0.0366 | 14 | 19 |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 0.0787 | 58 | 77 |
| `small-flat.fresh.neo-freya.sender.warm` | send3s1 | 0.0337 | 13 | 16 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.2155 | 419 | 561 |
| `small-flat.noop.neo-freya.sender.warm` | send3 | 0.1322 | 159 | 213 |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 0.1067 | 105 | 139 |
| `small-flat.noop.neo-freya.sender.warm` | send3s1 | 0.0822 | 63 | 84 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1079 | 107 | 142 |
| `small-real.fresh.neo-freya.sender.warm` | send3 | 0.1999 | 361 | 483 |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 0.1809 | 296 | 396 |
| `small-real.fresh.neo-freya.sender.warm` | send3s1 | 0.1041 | 100 | 133 |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.1317 | 158 | 211 |
| `small-real.noop.neo-freya.sender.warm` | send3 | 0.2361 | 503 | 673 |
| `small-real.noop.neo-freya.sender.warm` | send2 | 0.2606 | 612 | 819 |
| `small-real.noop.neo-freya.sender.warm` | send3s1 | 0.2714 | 663 | 888 |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.2245 | 455 | 608 |
