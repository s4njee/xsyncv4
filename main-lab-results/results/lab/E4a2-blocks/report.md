# E4a2-blocks

The block size and small-file cutoff are near their best: no level moves a copy by more than 3%.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220736Z-E4a2-blocks.
- Valid blocks: 60. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block256k | 10 | 1.001 [0.998, 1.005] | 1.001 [0.998, 1.006] | 0.5176 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block4m | 10 | 1.001 [1.000, 1.002] | 1.001 [0.999, 1.002] | 0.1504 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small64k | 10 | 0.999 [0.997, 1.001] | 0.999 [0.997, 1.001] | 0.4004 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small2m | 10 | 0.998 [0.995, 1.001] | 0.999 [0.994, 1.000] | 0.1875 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block256k | 10 | 0.982 [0.971, 0.994] | 0.983 [0.970, 0.993] | 0.0078 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block4m | 10 | 1.001 [0.989, 1.014] | 0.999 [0.991, 1.013] | 0.8105 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small64k | 10 | 1.000 [0.988, 1.013] | 1.001 [0.988, 1.015] | 0.9238 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small2m | 10 | 0.997 [0.981, 1.012] | 0.996 [0.979, 1.014] | 0.6406 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block256k | 10 | 1.008 [1.001, 1.015] | 1.009 [1.001, 1.016] | 0.0352 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block4m | 10 | 1.002 [0.997, 1.008] | 1.000 [0.999, 1.012] | 0.6543 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small64k | 10 | 1.001 [0.994, 1.007] | 1.000 [0.996, 1.008] | 0.8145 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small2m | 10 | 1.002 [1.000, 1.005] | 1.002 [1.000, 1.005] | 0.0859 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block256k | 10 | 0.988 [0.976, 0.999] | 0.990 [0.975, 0.998] | 0.0176 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block4m | 10 | 1.008 [0.997, 1.018] | 1.006 [0.998, 1.019] | 0.1152 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small64k | 10 | 0.998 [0.990, 1.007] | 0.997 [0.990, 1.006] | 0.6562 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small2m | 10 | 0.999 [0.990, 1.009] | 1.000 [0.990, 1.010] | 0.8906 | equivalent |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 10 | 1.011 [0.970, 1.054] | 1.006 [0.966, 1.053] | 0.5605 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 10 | 0.974 [0.924, 1.026] | 0.975 [0.919, 1.033] | 0.2832 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 10 | 1.034 [0.987, 1.083] | 1.032 [0.986, 1.088] | 0.1484 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 10 | 1.039 [0.971, 1.111] | 1.045 [0.971, 1.110] | 0.2246 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 10 | 1.021 [0.895, 1.165] | 0.993 [0.891, 1.276] | 0.9805 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 10 | 0.977 [0.927, 1.029] | 0.998 [0.895, 1.004] | 0.4160 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 10 | 0.967 [0.834, 1.122] | 0.997 [0.802, 1.111] | 0.6348 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 10 | 1.022 [0.901, 1.158] | 0.995 [0.896, 1.261] | 0.9707 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block256k | 0.893 [0.879, 0.908] | 0.998 [0.990, 1.007] | 0.900 [0.892, 0.907] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block4m | 0.997 [0.970, 1.025] | 0.997 [0.988, 1.005] | 1.727 [1.695, 1.760] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small64k | 1.026 [1.009, 1.043] | 1.001 [0.995, 1.008] | 0.925 [0.916, 0.935] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small2m | 0.989 [0.973, 1.006] | 1.000 [0.994, 1.006] | 1.005 [0.997, 1.012] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block256k | 0.856 [0.814, 0.901] | 0.984 [0.972, 0.997] | 0.993 [0.989, 0.997] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block4m | 1.005 [0.956, 1.056] | 1.003 [0.991, 1.015] | 1.247 [1.236, 1.259] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small64k | 0.989 [0.927, 1.056] | 1.001 [0.988, 1.014] | 1.001 [0.996, 1.006] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small2m | 0.987 [0.918, 1.061] | 0.997 [0.982, 1.013] | 1.003 [0.997, 1.008] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block256k | 0.860 [0.838, 0.882] | 0.998 [0.981, 1.014] | 0.918 [0.913, 0.922] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block4m | 1.134 [1.109, 1.160] | 0.998 [0.986, 1.011] | 1.639 [1.625, 1.654] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small64k | 1.007 [0.996, 1.017] | 1.006 [0.995, 1.016] | 0.995 [0.990, 1.001] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small2m | 1.008 [0.991, 1.025] | 0.994 [0.982, 1.007] | 1.157 [1.147, 1.167] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block256k | 0.888 [0.824, 0.956] | 0.988 [0.977, 1.000] | 1.006 [1.003, 1.008] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block4m | 1.099 [1.027, 1.176] | 1.008 [0.997, 1.019] | 1.211 [1.202, 1.219] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small64k | 1.006 [0.950, 1.067] | 0.999 [0.991, 1.007] | 1.000 [0.996, 1.003] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small2m | 1.014 [0.962, 1.069] | 0.999 [0.989, 1.009] | 1.055 [1.051, 1.058] |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 1.027 [0.996, 1.059] | 1.012 [0.973, 1.053] | 0.953 [0.936, 0.971] |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 0.928 [0.903, 0.953] | 0.971 [0.924, 1.021] | 1.375 [1.324, 1.427] |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 1.030 [1.006, 1.054] | 1.031 [0.984, 1.080] | 0.982 [0.961, 1.003] |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 0.998 [0.969, 1.029] | 1.035 [0.976, 1.097] | 1.002 [0.976, 1.029] |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 1.002 [0.975, 1.028] | 1.021 [0.893, 1.167] | 0.987 [0.950, 1.025] |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 1.015 [0.993, 1.038] | 0.977 [0.932, 1.023] | 1.089 [1.066, 1.113] |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 1.015 [0.991, 1.041] | 0.967 [0.835, 1.120] | 0.996 [0.967, 1.025] |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 1.028 [0.992, 1.064] | 1.024 [0.901, 1.165] | 0.992 [0.948, 1.037] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | block256k | block4m | small2m | small64k | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.334 | 12.328 | 12.291 | 12.306 | 12.317 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.244 | 12.481 | 12.424 | 12.470 | 12.464 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 13.364 | 13.284 | 13.287 | 13.263 | 13.256 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.204 | 13.475 | 13.362 | 13.348 | 13.369 |
| `small-real.fresh.freya-neo.sender.warm` | 13.413 | 12.912 | 13.775 | 13.714 | 13.262 |
| `small-real.fresh.neo-freya.sender.warm` | 12.077 | 11.555 | 12.087 | 11.443 | 11.830 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block256k | 0.0051 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | block4m | 0.0018 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small64k | 0.0029 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | small2m | 0.0044 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block256k | 0.0161 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | block4m | 0.0169 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small64k | 0.0179 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | small2m | 0.0217 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block256k | 0.0098 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | block4m | 0.0078 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small64k | 0.0086 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | small2m | 0.0036 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block256k | 0.0161 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | block4m | 0.0146 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small64k | 0.0115 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | small2m | 0.0135 | 8 | 8 |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 0.0579 | 33 | 43 |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 0.0736 | 51 | 68 |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 0.0646 | 40 | 53 |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 0.0941 | 82 | 109 |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 0.1844 | 308 | 412 |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 0.0727 | 50 | 66 |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 0.2077 | 389 | 521 |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 0.1753 | 278 | 372 |
