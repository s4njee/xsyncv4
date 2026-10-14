# E4bd-small-pipeline

On small-file trees, read-task size, the share of scanning workers and the listing window each change fresh-copy or no-op time by more than 3%.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T230746Z-E4bd-small-pipeline.
- Valid blocks: 80. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | batch16 | 10 | 0.996 [0.923, 1.074] | 0.979 [0.930, 1.088] | 0.9160 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | batch256 | 10 | 1.030 [0.961, 1.105] | 1.024 [0.961, 1.106] | 0.3320 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | scan1 | 10 | 0.982 [0.925, 1.042] | 0.979 [0.920, 1.041] | 0.5098 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | scanall | 10 | 0.981 [0.912, 1.055] | 0.985 [0.912, 1.050] | 0.5762 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | window4k | 10 | 0.989 [0.908, 1.077] | 0.993 [0.904, 1.081] | 0.7598 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | batch16 | 10 | 1.014 [0.888, 1.157] | 1.001 [0.889, 1.187] | 0.8418 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 10 | 1.014 [0.873, 1.179] | 0.989 [0.892, 1.176] | 0.8086 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | scan1 | 10 | 1.141 [0.845, 1.539] | 1.012 [0.912, 1.714] | 0.4414 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | scanall | 10 | 0.932 [0.784, 1.108] | 0.964 [0.771, 1.075] | 0.4238 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | window4k | 10 | 1.087 [0.968, 1.221] | 1.058 [0.974, 1.239] | 0.1387 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | batch16 | 10 | 0.942 [0.823, 1.078] | 0.976 [0.807, 1.058] | 0.4062 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | batch256 | 10 | 0.957 [0.885, 1.035] | 0.974 [0.875, 1.029] | 0.2773 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | scan1 | 10 | 1.044 [0.929, 1.172] | 1.059 [0.942, 1.160] | 0.4336 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | scanall | 10 | 1.065 [0.924, 1.227] | 1.048 [0.967, 1.235] | 0.3320 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | window4k | 10 | 0.959 [0.849, 1.082] | 0.957 [0.844, 1.085] | 0.4453 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | batch16 | 10 | 0.989 [0.906, 1.080] | 0.997 [0.904, 1.085] | 0.8066 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | batch256 | 10 | 1.026 [0.922, 1.141] | 0.999 [0.937, 1.162] | 0.7207 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | scan1 | 10 | 1.021 [0.946, 1.102] | 1.002 [0.952, 1.112] | 0.5859 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | scanall | 10 | 0.960 [0.901, 1.024] | 0.962 [0.908, 1.019] | 0.1816 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | window4k | 10 | 1.027 [0.926, 1.139] | 1.012 [0.943, 1.153] | 0.5977 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | batch16 | 10 | 0.993 [0.982, 1.004] | 0.993 [0.981, 1.009] | 0.1953 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | batch256 | 10 | 0.986 [0.968, 1.004] | 0.986 [0.966, 1.006] | 0.1133 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | scan1 | 10 | 0.997 [0.980, 1.014] | 1.000 [0.979, 1.014] | 0.6621 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | scanall | 10 | 0.995 [0.981, 1.008] | 0.995 [0.981, 1.010] | 0.4023 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | window4k | 10 | 0.987 [0.971, 1.002] | 0.989 [0.972, 1.001] | 0.0664 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | batch16 | 10 | 0.995 [0.974, 1.016] | 0.995 [0.975, 1.018] | 0.5625 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 10 | 0.994 [0.972, 1.016] | 0.988 [0.971, 1.015] | 0.5254 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | scan1 | 10 | 1.002 [0.976, 1.028] | 0.997 [0.974, 1.030] | 0.8750 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | scanall | 10 | 1.003 [0.984, 1.022] | 1.003 [0.985, 1.024] | 0.7266 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | window4k | 10 | 0.995 [0.971, 1.020] | 0.996 [0.967, 1.020] | 0.6445 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | batch16 | 10 | 0.972 [0.856, 1.104] | 1.018 [0.800, 1.071] | 0.9141 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | batch256 | 10 | 0.958 [0.889, 1.032] | 0.986 [0.857, 1.008] | 0.1738 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | scan1 | 10 | 0.965 [0.844, 1.103] | 1.008 [0.806, 1.067] | 0.7812 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | scanall | 10 | 0.915 [0.818, 1.024] | 0.941 [0.785, 0.995] | 0.0664 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | window4k | 10 | 0.984 [0.868, 1.116] | 1.009 [0.812, 1.095] | 0.9141 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | batch16 | 10 | 1.021 [0.932, 1.118] | 1.009 [0.958, 1.140] | 0.6328 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | batch256 | 10 | 1.027 [0.912, 1.155] | 1.027 [0.921, 1.181] | 0.6250 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | scan1 | 10 | 0.946 [0.888, 1.008] | 0.963 [0.871, 0.996] | 0.0293 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | scanall | 10 | 0.968 [0.912, 1.027] | 0.985 [0.898, 1.017] | 0.2383 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | window4k | 10 | 1.018 [0.936, 1.108] | 1.033 [0.913, 1.089] | 0.6758 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | batch16 | 1.009 [0.979, 1.040] | 0.994 [0.922, 1.071] | 1.021 [0.946, 1.102] |
| `small-deep.fresh.freya-neo.sender.warm` | batch256 | 1.021 [0.983, 1.061] | 1.028 [0.961, 1.099] | 0.994 [0.944, 1.048] |
| `small-deep.fresh.freya-neo.sender.warm` | scan1 | 0.997 [0.977, 1.017] | 0.979 [0.925, 1.037] | 1.020 [0.952, 1.092] |
| `small-deep.fresh.freya-neo.sender.warm` | scanall | 0.998 [0.963, 1.035] | 0.977 [0.911, 1.047] | 1.011 [0.917, 1.115] |
| `small-deep.fresh.freya-neo.sender.warm` | window4k | 0.969 [0.930, 1.009] | 0.988 [0.910, 1.073] | 0.669 [0.625, 0.717] |
| `small-deep.fresh.neo-freya.sender.warm` | batch16 | 1.028 [0.992, 1.065] | 1.032 [0.912, 1.168] | 0.966 [0.841, 1.109] |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 0.996 [0.950, 1.044] | 1.026 [0.893, 1.178] | 0.966 [0.870, 1.072] |
| `small-deep.fresh.neo-freya.sender.warm` | scan1 | 0.971 [0.912, 1.034] | 1.142 [0.862, 1.511] | 0.951 [0.787, 1.150] |
| `small-deep.fresh.neo-freya.sender.warm` | scanall | 1.074 [1.022, 1.128] | 0.949 [0.800, 1.125] | 0.868 [0.659, 1.145] |
| `small-deep.fresh.neo-freya.sender.warm` | window4k | 1.020 [0.994, 1.047] | 1.100 [0.988, 1.226] | 0.739 [0.631, 0.865] |
| `small-deep.noop.freya-neo.sender.warm` | batch16 | 1.041 [0.971, 1.115] | 0.942 [0.823, 1.078] | 1.017 [1.002, 1.032] |
| `small-deep.noop.freya-neo.sender.warm` | batch256 | 1.030 [0.979, 1.083] | 0.957 [0.885, 1.035] | 1.015 [0.994, 1.035] |
| `small-deep.noop.freya-neo.sender.warm` | scan1 | 1.011 [0.947, 1.080] | 1.043 [0.929, 1.172] | 1.003 [0.979, 1.027] |
| `small-deep.noop.freya-neo.sender.warm` | scanall | 1.031 [0.950, 1.119] | 1.064 [0.924, 1.226] | 0.975 [0.919, 1.034] |
| `small-deep.noop.freya-neo.sender.warm` | window4k | 0.892 [0.827, 0.961] | 0.959 [0.850, 1.082] | 0.658 [0.607, 0.714] |
| `small-deep.noop.neo-freya.sender.warm` | batch16 | 1.006 [0.969, 1.044] | 0.989 [0.906, 1.080] | 0.986 [0.841, 1.155] |
| `small-deep.noop.neo-freya.sender.warm` | batch256 | 0.998 [0.979, 1.018] | 1.026 [0.922, 1.141] | 0.967 [0.856, 1.093] |
| `small-deep.noop.neo-freya.sender.warm` | scan1 | 1.011 [0.976, 1.049] | 1.021 [0.946, 1.102] | 0.965 [0.818, 1.138] |
| `small-deep.noop.neo-freya.sender.warm` | scanall | 1.000 [0.967, 1.034] | 0.961 [0.901, 1.024] | 0.955 [0.838, 1.088] |
| `small-deep.noop.neo-freya.sender.warm` | window4k | 1.001 [0.984, 1.019] | 1.027 [0.926, 1.139] | 0.924 [0.816, 1.047] |
| `small-flat.fresh.freya-neo.sender.warm` | batch16 | 1.011 [0.986, 1.037] | 0.993 [0.983, 1.003] | 0.993 [0.978, 1.009] |
| `small-flat.fresh.freya-neo.sender.warm` | batch256 | 0.986 [0.961, 1.012] | 0.989 [0.976, 1.002] | 1.010 [0.999, 1.022] |
| `small-flat.fresh.freya-neo.sender.warm` | scan1 | 1.001 [0.977, 1.025] | 0.993 [0.979, 1.006] | 0.962 [0.929, 0.997] |
| `small-flat.fresh.freya-neo.sender.warm` | scanall | 1.004 [0.984, 1.025] | 0.994 [0.981, 1.007] | 0.999 [0.987, 1.012] |
| `small-flat.fresh.freya-neo.sender.warm` | window4k | 0.996 [0.977, 1.016] | 0.986 [0.973, 0.999] | 0.568 [0.524, 0.616] |
| `small-flat.fresh.neo-freya.sender.warm` | batch16 | 0.996 [0.966, 1.027] | 0.997 [0.977, 1.017] | 0.894 [0.760, 1.052] |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 0.989 [0.942, 1.038] | 0.995 [0.973, 1.017] | 1.043 [0.815, 1.333] |
| `small-flat.fresh.neo-freya.sender.warm` | scan1 | 0.979 [0.947, 1.011] | 1.002 [0.981, 1.024] | 1.053 [0.836, 1.328] |
| `small-flat.fresh.neo-freya.sender.warm` | scanall | 0.997 [0.949, 1.047] | 1.007 [0.986, 1.028] | 0.994 [0.774, 1.277] |
| `small-flat.fresh.neo-freya.sender.warm` | window4k | 0.982 [0.947, 1.018] | 0.993 [0.968, 1.019] | 0.593 [0.489, 0.718] |
| `small-flat.noop.freya-neo.sender.warm` | batch16 | 0.909 [0.768, 1.077] | 0.973 [0.859, 1.103] | 1.002 [0.995, 1.008] |
| `small-flat.noop.freya-neo.sender.warm` | batch256 | 0.889 [0.797, 0.991] | 0.960 [0.892, 1.033] | 0.990 [0.973, 1.007] |
| `small-flat.noop.freya-neo.sender.warm` | scan1 | 0.915 [0.789, 1.062] | 0.962 [0.844, 1.096] | 0.992 [0.980, 1.004] |
| `small-flat.noop.freya-neo.sender.warm` | scanall | 0.839 [0.729, 0.966] | 0.917 [0.821, 1.025] | 0.996 [0.983, 1.010] |
| `small-flat.noop.freya-neo.sender.warm` | window4k | 0.890 [0.754, 1.051] | 0.984 [0.870, 1.114] | 0.713 [0.705, 0.722] |
| `small-flat.noop.neo-freya.sender.warm` | batch16 | 1.002 [0.864, 1.162] | 1.021 [0.933, 1.118] | 1.004 [0.990, 1.019] |
| `small-flat.noop.neo-freya.sender.warm` | batch256 | 1.040 [0.868, 1.246] | 1.028 [0.914, 1.157] | 1.007 [0.993, 1.021] |
| `small-flat.noop.neo-freya.sender.warm` | scan1 | 0.935 [0.834, 1.049] | 0.947 [0.889, 1.009] | 1.003 [0.982, 1.025] |
| `small-flat.noop.neo-freya.sender.warm` | scanall | 0.961 [0.862, 1.072] | 0.969 [0.913, 1.028] | 1.001 [0.990, 1.012] |
| `small-flat.noop.neo-freya.sender.warm` | window4k | 0.964 [0.839, 1.107] | 1.019 [0.937, 1.108] | 0.995 [0.974, 1.017] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | batch16 | batch256 | scan1 | scanall | window4k | xs |
|---|---|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | 22.027 | 22.792 | 21.720 | 21.702 | 21.874 | 22.122 |
| `small-deep.fresh.neo-freya.sender.warm` | 6.770 | 6.774 | 7.617 | 6.224 | 7.263 | 6.678 |
| `small-deep.noop.freya-neo.sender.warm` | 2.625 | 2.666 | 2.908 | 2.967 | 2.671 | 2.786 |
| `small-deep.noop.neo-freya.sender.warm` | 1.612 | 1.672 | 1.664 | 1.565 | 1.674 | 1.630 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.492 | 6.446 | 6.516 | 6.504 | 6.450 | 6.538 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.393 | 3.390 | 3.418 | 3.422 | 3.394 | 3.412 |
| `small-flat.noop.freya-neo.sender.warm` | 0.324 | 0.319 | 0.322 | 0.305 | 0.328 | 0.333 |
| `small-flat.noop.neo-freya.sender.warm` | 0.297 | 0.299 | 0.275 | 0.282 | 0.296 | 0.291 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | batch16 | 0.1054 | 102 | 136 |
| `small-deep.fresh.freya-neo.sender.warm` | batch256 | 0.0976 | 88 | 117 |
| `small-deep.fresh.freya-neo.sender.warm` | scan1 | 0.0833 | 65 | 86 |
| `small-deep.fresh.freya-neo.sender.warm` | scanall | 0.1019 | 96 | 127 |
| `small-deep.fresh.freya-neo.sender.warm` | window4k | 0.1194 | 130 | 174 |
| `small-deep.fresh.neo-freya.sender.warm` | batch16 | 0.1846 | 308 | 412 |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 0.2099 | 398 | 532 |
| `small-deep.fresh.neo-freya.sender.warm` | scan1 | 0.4193 | 1580 | 2117 |
| `small-deep.fresh.neo-freya.sender.warm` | scanall | 0.2414 | 525 | 703 |
| `small-deep.fresh.neo-freya.sender.warm` | window4k | 0.1623 | 239 | 319 |
| `small-deep.noop.freya-neo.sender.warm` | batch16 | 0.1891 | 323 | 433 |
| `small-deep.noop.freya-neo.sender.warm` | batch256 | 0.1093 | 110 | 146 |
| `small-deep.noop.freya-neo.sender.warm` | scan1 | 0.1626 | 240 | 321 |
| `small-deep.noop.freya-neo.sender.warm` | scanall | 0.1977 | 353 | 473 |
| `small-deep.noop.freya-neo.sender.warm` | window4k | 0.1690 | 259 | 346 |
| `small-deep.noop.neo-freya.sender.warm` | batch16 | 0.1226 | 137 | 183 |
| `small-deep.noop.neo-freya.sender.warm` | batch256 | 0.1489 | 201 | 269 |
| `small-deep.noop.neo-freya.sender.warm` | scan1 | 0.1070 | 105 | 140 |
| `small-deep.noop.neo-freya.sender.warm` | scanall | 0.0892 | 74 | 98 |
| `small-deep.noop.neo-freya.sender.warm` | window4k | 0.1445 | 190 | 254 |
| `small-flat.fresh.freya-neo.sender.warm` | batch16 | 0.0157 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | batch256 | 0.0258 | 8 | 11 |
| `small-flat.fresh.freya-neo.sender.warm` | scan1 | 0.0234 | 8 | 9 |
| `small-flat.fresh.freya-neo.sender.warm` | scanall | 0.0190 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | window4k | 0.0223 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | batch16 | 0.0294 | 10 | 13 |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 0.0313 | 11 | 14 |
| `small-flat.fresh.neo-freya.sender.warm` | scan1 | 0.0361 | 14 | 18 |
| `small-flat.fresh.neo-freya.sender.warm` | scanall | 0.0265 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | window4k | 0.0345 | 13 | 17 |
| `small-flat.noop.freya-neo.sender.warm` | batch16 | 0.1782 | 287 | 384 |
| `small-flat.noop.freya-neo.sender.warm` | batch256 | 0.1048 | 101 | 134 |
| `small-flat.noop.freya-neo.sender.warm` | scan1 | 0.1868 | 316 | 422 |
| `small-flat.noop.freya-neo.sender.warm` | scanall | 0.1568 | 223 | 298 |
| `small-flat.noop.freya-neo.sender.warm` | window4k | 0.1758 | 280 | 374 |
| `small-flat.noop.neo-freya.sender.warm` | batch16 | 0.1268 | 147 | 196 |
| `small-flat.noop.neo-freya.sender.warm` | batch256 | 0.1651 | 247 | 330 |
| `small-flat.noop.neo-freya.sender.warm` | scan1 | 0.0888 | 73 | 97 |
| `small-flat.noop.neo-freya.sender.warm` | scanall | 0.0827 | 64 | 85 |
| `small-flat.noop.neo-freya.sender.warm` | window4k | 0.1180 | 128 | 170 |
