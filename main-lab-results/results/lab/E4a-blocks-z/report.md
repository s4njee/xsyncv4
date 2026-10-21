# E4a-blocks-z

With -z, larger blocks or larger read tasks send fewer bytes for small compressible files, and are no slower.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T213303Z-E4a-blocks-z.
- Valid blocks: 40. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | block256k | 10 | 1.006 [0.997, 1.014] | 1.007 [0.998, 1.014] | 0.1445 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | block4m | 10 | 1.007 [0.997, 1.017] | 1.007 [0.995, 1.019] | 0.1230 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | small64k | 10 | 1.002 [0.991, 1.012] | 1.002 [0.992, 1.012] | 0.7188 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | small2m | 10 | 1.005 [0.999, 1.011] | 1.005 [0.999, 1.011] | 0.0879 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | batch512 | 10 | 1.004 [0.995, 1.013] | 1.002 [0.993, 1.013] | 0.3516 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | block256k | 10 | 0.988 [0.945, 1.032] | 1.006 [0.941, 1.026] | 0.5293 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | block4m | 10 | 1.117 [1.043, 1.195] | 1.113 [1.047, 1.223] | 0.0039 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | small64k | 10 | 1.014 [0.966, 1.064] | 1.021 [0.967, 1.062] | 0.5352 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | small2m | 10 | 0.983 [0.941, 1.028] | 0.985 [0.940, 1.032] | 0.4121 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | batch512 | 10 | 0.998 [0.935, 1.065] | 0.995 [0.933, 1.073] | 0.9434 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 10 | 0.976 [0.891, 1.070] | 0.971 [0.883, 1.077] | 0.5605 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 10 | 1.022 [0.938, 1.114] | 1.019 [0.939, 1.116] | 0.5820 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 10 | 0.976 [0.916, 1.040] | 0.972 [0.907, 1.046] | 0.4219 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 10 | 0.973 [0.894, 1.060] | 0.978 [0.889, 1.095] | 0.4688 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | batch512 | 10 | 0.988 [0.918, 1.063] | 0.985 [0.915, 1.069] | 0.7090 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 10 | 1.177 [0.918, 1.510] | 1.029 [0.964, 1.511] | 0.2402 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 10 | 1.097 [0.920, 1.309] | 1.040 [0.958, 1.404] | 0.2656 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 10 | 1.168 [1.035, 1.318] | 1.147 [1.044, 1.320] | 0.0137 | slower |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 10 | 1.112 [0.976, 1.268] | 1.105 [0.958, 1.254] | 0.1328 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | batch512 | 10 | 1.045 [0.971, 1.124] | 1.041 [0.972, 1.130] | 0.2012 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | block256k | 0.995 [0.983, 1.007] | 1.002 [0.992, 1.012] | 0.845 [0.748, 0.955] |
| `small-flat.fresh.freya-neo.sender.warm` | block4m | 1.030 [1.012, 1.049] | 1.004 [0.992, 1.015] | 1.565 [1.451, 1.688] |
| `small-flat.fresh.freya-neo.sender.warm` | small64k | 1.022 [1.007, 1.037] | 0.999 [0.992, 1.007] | 1.178 [1.075, 1.291] |
| `small-flat.fresh.freya-neo.sender.warm` | small2m | 1.005 [0.996, 1.013] | 0.996 [0.984, 1.008] | 0.896 [0.811, 0.991] |
| `small-flat.fresh.freya-neo.sender.warm` | batch512 | 0.984 [0.972, 0.995] | 1.004 [0.993, 1.015] | 1.132 [1.030, 1.243] |
| `small-flat.fresh.neo-freya.sender.warm` | block256k | 0.916 [0.825, 1.018] | 0.979 [0.930, 1.031] | 1.192 [0.937, 1.516] |
| `small-flat.fresh.neo-freya.sender.warm` | block4m | 1.050 [0.899, 1.226] | 1.100 [1.024, 1.182] | 1.676 [1.378, 2.038] |
| `small-flat.fresh.neo-freya.sender.warm` | small64k | 1.006 [0.935, 1.083] | 1.005 [0.955, 1.058] | 1.384 [1.104, 1.735] |
| `small-flat.fresh.neo-freya.sender.warm` | small2m | 0.905 [0.817, 1.003] | 0.976 [0.925, 1.030] | 1.050 [0.834, 1.322] |
| `small-flat.fresh.neo-freya.sender.warm` | batch512 | 0.944 [0.819, 1.089] | 0.993 [0.921, 1.071] | 1.069 [0.877, 1.302] |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 0.995 [0.959, 1.034] | 0.976 [0.895, 1.064] | 0.421 [0.280, 0.633] |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 1.010 [0.953, 1.070] | 1.023 [0.938, 1.114] | 1.588 [0.878, 2.875] |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 1.007 [0.963, 1.052] | 0.975 [0.919, 1.035] | 1.091 [0.747, 1.594] |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 0.995 [0.951, 1.041] | 0.975 [0.898, 1.059] | 1.231 [0.898, 1.687] |
| `small-real.fresh.freya-neo.sender.warm` | batch512 | 1.001 [0.967, 1.037] | 0.984 [0.913, 1.060] | 1.265 [0.773, 2.070] |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 1.043 [1.024, 1.062] | 1.173 [0.918, 1.497] | 0.916 [0.833, 1.009] |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 0.982 [0.961, 1.003] | 1.097 [0.921, 1.306] | 1.809 [1.378, 2.376] |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 1.072 [1.052, 1.091] | 1.166 [1.034, 1.314] | 1.083 [0.888, 1.321] |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 0.979 [0.958, 1.000] | 1.110 [0.972, 1.268] | 1.170 [0.979, 1.397] |
| `small-real.fresh.neo-freya.sender.warm` | batch512 | 0.984 [0.967, 1.003] | 1.053 [0.983, 1.128] | 1.025 [0.930, 1.131] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | batch512 | block256k | block4m | small2m | small64k | xs |
|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | 6.041 | 6.052 | 6.061 | 6.047 | 6.028 | 6.018 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.614 | 3.577 | 4.045 | 3.562 | 3.672 | 3.622 |
| `small-real.fresh.freya-neo.sender.warm` | 14.479 | 14.309 | 14.982 | 14.267 | 14.307 | 14.656 |
| `small-real.fresh.neo-freya.sender.warm` | 6.770 | 7.626 | 7.109 | 7.206 | 7.567 | 6.479 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | block256k | 0.0116 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | block4m | 0.0136 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | small64k | 0.0146 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | small2m | 0.0081 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | batch512 | 0.0127 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | block256k | 0.0613 | 36 | 48 |
| `small-flat.fresh.neo-freya.sender.warm` | block4m | 0.0950 | 84 | 111 |
| `small-flat.fresh.neo-freya.sender.warm` | small64k | 0.0672 | 43 | 57 |
| `small-flat.fresh.neo-freya.sender.warm` | small2m | 0.0618 | 37 | 48 |
| `small-flat.fresh.neo-freya.sender.warm` | batch512 | 0.0913 | 77 | 103 |
| `small-real.fresh.freya-neo.sender.warm` | block256k | 0.1286 | 151 | 201 |
| `small-real.fresh.freya-neo.sender.warm` | block4m | 0.1207 | 133 | 178 |
| `small-real.fresh.freya-neo.sender.warm` | small64k | 0.0885 | 73 | 97 |
| `small-real.fresh.freya-neo.sender.warm` | small2m | 0.1184 | 128 | 171 |
| `small-real.fresh.freya-neo.sender.warm` | batch512 | 0.1025 | 97 | 129 |
| `small-real.fresh.neo-freya.sender.warm` | block256k | 0.3481 | 1090 | 1459 |
| `small-real.fresh.neo-freya.sender.warm` | block4m | 0.2468 | 549 | 735 |
| `small-real.fresh.neo-freya.sender.warm` | small64k | 0.1694 | 260 | 348 |
| `small-real.fresh.neo-freya.sender.warm` | small2m | 0.1830 | 303 | 405 |
| `small-real.fresh.neo-freya.sender.warm` | batch512 | 0.1025 | 97 | 129 |
