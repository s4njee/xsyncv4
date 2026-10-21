# E3d-metadata

Each metadata flag costs xs less than 5% on small files, and xs -aH and -aX stay faster than rsync -a.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs-a`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220721Z-E3d-metadata.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | xs-rt | 10 | 0.975 [0.913, 1.041] | 0.966 [0.909, 1.057] | 0.4160 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aH | 10 | 0.992 [0.916, 1.075] | 0.980 [0.920, 1.073] | 0.8398 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aX | 10 | 1.011 [0.935, 1.094] | 1.010 [0.940, 1.102] | 0.7422 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | rsync | 10 | 1.234 [1.134, 1.343] | 1.240 [1.133, 1.352] | 0.0020 | slower |
| `small-deep.fresh.neo-freya.sender.warm` | xs-rt | 10 | 1.116 [0.923, 1.350] | 1.050 [0.962, 1.452] | 0.2090 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aH | 10 | 1.029 [0.980, 1.080] | 1.021 [0.983, 1.081] | 0.2266 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aX | 10 | 1.431 [1.050, 1.951] | 1.405 [1.064, 1.826] | 0.0039 | slower |
| `small-deep.fresh.neo-freya.sender.warm` | rsync | 10 | 1.329 [1.059, 1.668] | 1.226 [1.121, 1.776] | 0.0020 | slower |
| `small-deep.noop.freya-neo.sender.warm` | xs-rt | 10 | 1.092 [1.022, 1.167] | 1.095 [1.013, 1.170] | 0.0195 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | xs-aH | 10 | 1.114 [0.901, 1.379] | 1.066 [0.926, 1.453] | 0.3066 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | xs-aX | 10 | 1.226 [1.144, 1.314] | 1.227 [1.143, 1.305] | 0.0020 | slower |
| `small-deep.noop.freya-neo.sender.warm` | rsync | 10 | 6.385 [5.799, 7.029] | 6.324 [5.755, 7.030] | 0.0020 | slower |
| `small-deep.noop.neo-freya.sender.warm` | xs-rt | 10 | 0.894 [0.810, 0.987] | 0.916 [0.814, 0.980] | 0.0078 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | xs-aH | 10 | 0.972 [0.891, 1.061] | 1.000 [0.886, 1.053] | 0.4902 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | xs-aX | 10 | 1.101 [0.949, 1.278] | 1.117 [0.964, 1.222] | 0.1660 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 10 | 1.759 [1.490, 2.077] | 1.758 [1.470, 2.041] | 0.0020 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | xs-rt | 10 | 0.995 [0.980, 1.010] | 0.995 [0.980, 1.011] | 0.4707 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aH | 10 | 1.025 [1.015, 1.036] | 1.026 [1.014, 1.037] | 0.0020 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aX | 10 | 1.058 [1.041, 1.075] | 1.057 [1.041, 1.076] | 0.0020 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 10 | 1.046 [1.008, 1.086] | 1.038 [1.013, 1.095] | 0.0078 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-rt | 10 | 1.013 [0.994, 1.033] | 1.014 [0.995, 1.033] | 0.1504 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aH | 10 | 1.036 [1.014, 1.058] | 1.037 [1.020, 1.057] | 0.0098 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aX | 10 | 1.069 [1.049, 1.090] | 1.071 [1.050, 1.091] | 0.0020 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 10 | 1.846 [1.623, 2.100] | 1.835 [1.599, 2.103] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | xs-rt | 10 | 1.012 [0.939, 1.090] | 1.012 [0.938, 1.087] | 0.7129 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | xs-aH | 10 | 1.215 [1.133, 1.303] | 1.212 [1.131, 1.307] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | xs-aX | 10 | 1.690 [1.620, 1.762] | 1.695 [1.623, 1.754] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 10 | 2.367 [2.174, 2.577] | 2.365 [2.174, 2.577] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | xs-rt | 10 | 1.029 [0.969, 1.094] | 1.013 [0.976, 1.102] | 0.3555 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | xs-aH | 10 | 1.209 [1.078, 1.356] | 1.163 [1.116, 1.423] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | xs-aX | 10 | 1.345 [1.275, 1.418] | 1.345 [1.268, 1.429] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 10 | 2.547 [2.368, 2.740] | 2.541 [2.335, 2.751] | 0.0020 | slower |
| `small-real.fresh.freya-neo.sender.warm` | xs-rt | 10 | 1.019 [0.949, 1.094] | 1.008 [0.948, 1.084] | 0.5898 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-aH | 10 | 1.023 [0.983, 1.065] | 1.015 [0.987, 1.071] | 0.2363 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-aX | 10 | 1.042 [0.987, 1.101] | 1.051 [0.981, 1.101] | 0.1191 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 10 | 1.388 [1.308, 1.472] | 1.386 [1.305, 1.476] | 0.0020 | slower |
| `small-real.fresh.neo-freya.sender.warm` | xs-rt | 10 | 1.034 [0.939, 1.139] | 0.997 [0.979, 1.221] | 0.7461 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-aH | 10 | 1.073 [0.941, 1.224] | 0.997 [0.982, 1.235] | 0.4805 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-aX | 10 | 1.009 [0.979, 1.040] | 1.006 [0.983, 1.047] | 0.5137 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 10 | 1.064 [0.968, 1.169] | 1.028 [0.981, 1.176] | 0.2246 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs-rt | 10 | 1.011 [0.980, 1.042] | 1.009 [0.978, 1.044] | 0.4531 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs-aH | 10 | 1.117 [0.973, 1.283] | 1.078 [1.000, 1.315] | 0.0645 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs-aX | 10 | 1.348 [1.255, 1.448] | 1.361 [1.254, 1.448] | 0.0020 | slower |
| `small-real.noop.freya-neo.sender.warm` | rsync | 10 | 6.455 [6.056, 6.880] | 6.521 [6.075, 6.751] | 0.0020 | slower |
| `small-real.noop.neo-freya.sender.warm` | xs-rt | 10 | 0.940 [0.838, 1.054] | 0.932 [0.821, 1.066] | 0.2539 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | xs-aH | 10 | 0.792 [0.690, 0.910] | 0.804 [0.683, 0.924] | 0.0039 | faster |
| `small-real.noop.neo-freya.sender.warm` | xs-aX | 10 | 0.959 [0.838, 1.098] | 0.966 [0.833, 1.093] | 0.5234 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | rsync | 10 | 1.331 [1.166, 1.519] | 1.358 [1.147, 1.504] | 0.0039 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | xs-rt | 1.017 [0.990, 1.044] | 0.972 [0.911, 1.036] | 1.001 [0.953, 1.050] |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aH | 1.038 [1.005, 1.072] | 0.991 [0.915, 1.073] | 0.992 [0.948, 1.038] |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aX | 1.158 [1.110, 1.209] | 1.007 [0.932, 1.088] | 1.062 [0.994, 1.134] |
| `small-deep.fresh.freya-neo.sender.warm` | rsync | 1.132 [1.084, 1.182] | 1.223 [1.125, 1.328] | 1.741 [1.661, 1.824] |
| `small-deep.fresh.neo-freya.sender.warm` | xs-rt | 0.932 [0.900, 0.965] | 1.113 [0.929, 1.333] | 1.152 [0.910, 1.458] |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aH | 1.029 [1.009, 1.051] | 1.012 [0.973, 1.053] | 1.140 [0.953, 1.364] |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aX | 1.103 [1.033, 1.177] | 1.413 [1.046, 1.910] | 1.158 [0.918, 1.461] |
| `small-deep.fresh.neo-freya.sender.warm` | rsync | 0.413 [0.402, 0.424] | 1.307 [1.057, 1.618] | 0.179 [0.162, 0.198] |
| `small-deep.noop.freya-neo.sender.warm` | xs-rt | 0.995 [0.943, 1.051] | 1.093 [1.023, 1.167] | 1.007 [0.988, 1.026] |
| `small-deep.noop.freya-neo.sender.warm` | xs-aH | 1.041 [0.965, 1.124] | 1.115 [0.901, 1.379] | 0.980 [0.916, 1.050] |
| `small-deep.noop.freya-neo.sender.warm` | xs-aX | 1.332 [1.281, 1.384] | 1.226 [1.144, 1.314] | 1.093 [1.072, 1.114] |
| `small-deep.noop.freya-neo.sender.warm` | rsync | 0.857 [0.819, 0.897] | 6.371 [5.788, 7.012] | 0.952 [0.933, 0.970] |
| `small-deep.noop.neo-freya.sender.warm` | xs-rt | 0.994 [0.974, 1.015] | 0.894 [0.810, 0.987] | 0.986 [0.908, 1.071] |
| `small-deep.noop.neo-freya.sender.warm` | xs-aH | 0.994 [0.949, 1.042] | 0.973 [0.892, 1.062] | 1.013 [0.885, 1.160] |
| `small-deep.noop.neo-freya.sender.warm` | xs-aX | 1.447 [1.409, 1.486] | 1.101 [0.949, 1.278] | 1.003 [0.968, 1.039] |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 0.185 [0.173, 0.198] | 1.758 [1.490, 2.075] | 0.179 [0.172, 0.186] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-rt | 0.991 [0.973, 1.008] | 0.993 [0.980, 1.005] | 0.997 [0.984, 1.010] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aH | 1.014 [0.992, 1.037] | 1.022 [1.010, 1.034] | 1.003 [0.991, 1.014] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aX | 1.185 [1.152, 1.219] | 1.053 [1.035, 1.071] | 1.049 [1.028, 1.071] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.687 [0.664, 0.710] | 1.039 [0.998, 1.082] | 0.100 [0.098, 0.102] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-rt | 1.013 [0.984, 1.043] | 1.022 [1.001, 1.043] | 0.944 [0.765, 1.165] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aH | 1.027 [1.008, 1.046] | 1.041 [1.016, 1.067] | 0.971 [0.853, 1.106] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aX | 1.067 [1.050, 1.083] | 1.068 [1.046, 1.091] | 1.114 [0.911, 1.361] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.647 [0.633, 0.661] | 1.819 [1.600, 2.068] | 0.206 [0.178, 0.240] |
| `small-flat.noop.freya-neo.sender.warm` | xs-rt | 0.987 [0.880, 1.108] | 1.012 [0.941, 1.089] | 0.997 [0.977, 1.017] |
| `small-flat.noop.freya-neo.sender.warm` | xs-aH | 1.337 [1.188, 1.505] | 1.208 [1.128, 1.294] | 1.033 [1.013, 1.053] |
| `small-flat.noop.freya-neo.sender.warm` | xs-aX | 4.810 [4.474, 5.172] | 1.670 [1.602, 1.741] | 1.227 [1.202, 1.252] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.812 [0.710, 0.928] | 2.334 [2.146, 2.537] | 0.472 [0.462, 0.483] |
| `small-flat.noop.neo-freya.sender.warm` | xs-rt | 1.097 [1.006, 1.197] | 1.029 [0.969, 1.093] | 0.991 [0.975, 1.007] |
| `small-flat.noop.neo-freya.sender.warm` | xs-aH | 1.386 [1.229, 1.564] | 1.208 [1.077, 1.354] | 0.999 [0.986, 1.012] |
| `small-flat.noop.neo-freya.sender.warm` | xs-aX | 2.453 [2.319, 2.595] | 1.343 [1.274, 1.416] | 0.995 [0.978, 1.012] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.789 [0.712, 0.874] | 2.537 [2.359, 2.728] | 0.589 [0.575, 0.602] |
| `small-real.fresh.freya-neo.sender.warm` | xs-rt | 1.000 [0.973, 1.028] | 1.018 [0.949, 1.093] | 1.003 [0.965, 1.043] |
| `small-real.fresh.freya-neo.sender.warm` | xs-aH | 1.007 [0.988, 1.027] | 1.024 [0.983, 1.066] | 1.008 [0.981, 1.036] |
| `small-real.fresh.freya-neo.sender.warm` | xs-aX | 1.109 [1.080, 1.139] | 1.045 [0.989, 1.105] | 1.031 [1.007, 1.056] |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.943 [0.920, 0.967] | 1.377 [1.300, 1.459] | 1.315 [1.287, 1.344] |
| `small-real.fresh.neo-freya.sender.warm` | xs-rt | 0.950 [0.925, 0.975] | 1.035 [0.940, 1.140] | 1.010 [0.965, 1.056] |
| `small-real.fresh.neo-freya.sender.warm` | xs-aH | 0.972 [0.941, 1.004] | 1.071 [0.940, 1.221] | 1.040 [1.000, 1.083] |
| `small-real.fresh.neo-freya.sender.warm` | xs-aX | 1.068 [1.043, 1.093] | 1.010 [0.978, 1.043] | 1.031 [0.994, 1.070] |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.499 [0.487, 0.512] | 1.059 [0.964, 1.165] | 0.100 [0.097, 0.104] |
| `small-real.noop.freya-neo.sender.warm` | xs-rt | 0.987 [0.975, 0.998] | 1.011 [0.981, 1.041] | 0.977 [0.949, 1.006] |
| `small-real.noop.freya-neo.sender.warm` | xs-aH | 1.065 [1.040, 1.090] | 1.117 [0.974, 1.282] | 1.008 [0.987, 1.030] |
| `small-real.noop.freya-neo.sender.warm` | xs-aX | 1.394 [1.350, 1.439] | 1.346 [1.254, 1.445] | 1.033 [1.008, 1.058] |
| `small-real.noop.freya-neo.sender.warm` | rsync | 0.789 [0.741, 0.839] | 6.428 [6.034, 6.847] | 1.599 [1.555, 1.645] |
| `small-real.noop.neo-freya.sender.warm` | xs-rt | 1.040 [0.953, 1.134] | 0.940 [0.838, 1.054] | 0.940 [0.879, 1.006] |
| `small-real.noop.neo-freya.sender.warm` | xs-aH | 0.656 [0.606, 0.710] | 0.793 [0.690, 0.911] | 1.011 [0.941, 1.087] |
| `small-real.noop.neo-freya.sender.warm` | xs-aX | 1.397 [1.309, 1.490] | 0.959 [0.838, 1.098] | 1.064 [0.970, 1.167] |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.119 [0.110, 0.129] | 1.330 [1.166, 1.518] | 0.205 [0.192, 0.219] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-a | xs-aH | xs-aX | xs-rt |
|---|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | 25.935 | 21.010 | 20.845 | 21.251 | 20.486 |
| `small-deep.fresh.neo-freya.sender.warm` | 8.487 | 6.385 | 6.569 | 9.138 | 7.128 |
| `small-deep.noop.freya-neo.sender.warm` | 17.231 | 2.699 | 3.008 | 3.310 | 2.948 |
| `small-deep.noop.neo-freya.sender.warm` | 3.182 | 1.809 | 1.759 | 1.992 | 1.618 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.939 | 6.632 | 6.801 | 7.014 | 6.598 |
| `small-flat.fresh.neo-freya.sender.warm` | 6.282 | 3.403 | 3.525 | 3.638 | 3.448 |
| `small-flat.noop.freya-neo.sender.warm` | 0.759 | 0.321 | 0.390 | 0.542 | 0.324 |
| `small-flat.noop.neo-freya.sender.warm` | 0.727 | 0.286 | 0.345 | 0.384 | 0.294 |
| `small-real.fresh.freya-neo.sender.warm` | 24.014 | 17.306 | 17.707 | 18.036 | 17.629 |
| `small-real.fresh.neo-freya.sender.warm` | 11.988 | 11.268 | 12.090 | 11.372 | 11.654 |
| `small-real.noop.freya-neo.sender.warm` | 9.358 | 1.450 | 1.620 | 1.954 | 1.465 |
| `small-real.noop.neo-freya.sender.warm` | 2.038 | 1.531 | 1.213 | 1.469 | 1.439 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-deep.fresh.freya-neo.sender.warm` | xs-rt | 0.0921 | 79 | 104 |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aH | 0.1116 | 114 | 152 |
| `small-deep.fresh.freya-neo.sender.warm` | xs-aX | 0.1097 | 110 | 147 |
| `small-deep.fresh.freya-neo.sender.warm` | rsync | 0.1183 | 128 | 171 |
| `small-deep.fresh.neo-freya.sender.warm` | xs-rt | 0.2658 | 636 | 852 |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aH | 0.0678 | 44 | 58 |
| `small-deep.fresh.neo-freya.sender.warm` | xs-aX | 0.4331 | 1685 | 2258 |
| `small-deep.fresh.neo-freya.sender.warm` | rsync | 0.3172 | 906 | 1213 |
| `small-deep.noop.freya-neo.sender.warm` | xs-rt | 0.0926 | 80 | 106 |
| `small-deep.noop.freya-neo.sender.warm` | xs-aH | 0.2975 | 797 | 1067 |
| `small-deep.noop.freya-neo.sender.warm` | xs-aX | 0.0968 | 87 | 115 |
| `small-deep.noop.freya-neo.sender.warm` | rsync | 0.1345 | 165 | 220 |
| `small-deep.noop.neo-freya.sender.warm` | xs-rt | 0.1379 | 173 | 231 |
| `small-deep.noop.neo-freya.sender.warm` | xs-aH | 0.1218 | 136 | 181 |
| `small-deep.noop.neo-freya.sender.warm` | xs-aX | 0.2081 | 391 | 523 |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 0.2320 | 485 | 650 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-rt | 0.0215 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aH | 0.0146 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-aX | 0.0225 | 8 | 9 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0519 | 27 | 35 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-rt | 0.0266 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aH | 0.0296 | 10 | 13 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-aX | 0.0270 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.1802 | 294 | 393 |
| `small-flat.noop.freya-neo.sender.warm` | xs-rt | 0.1046 | 101 | 134 |
| `small-flat.noop.freya-neo.sender.warm` | xs-aH | 0.0973 | 87 | 116 |
| `small-flat.noop.freya-neo.sender.warm` | xs-aX | 0.0589 | 34 | 44 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.1186 | 129 | 172 |
| `small-flat.noop.neo-freya.sender.warm` | xs-rt | 0.0849 | 67 | 89 |
| `small-flat.noop.neo-freya.sender.warm` | xs-aH | 0.1605 | 234 | 312 |
| `small-flat.noop.neo-freya.sender.warm` | xs-aX | 0.0743 | 52 | 69 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1022 | 96 | 128 |
| `small-real.fresh.freya-neo.sender.warm` | xs-rt | 0.0996 | 91 | 122 |
| `small-real.fresh.freya-neo.sender.warm` | xs-aH | 0.0561 | 31 | 40 |
| `small-real.fresh.freya-neo.sender.warm` | xs-aX | 0.0764 | 55 | 73 |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.0827 | 64 | 85 |
| `small-real.fresh.neo-freya.sender.warm` | xs-rt | 0.1350 | 166 | 222 |
| `small-real.fresh.neo-freya.sender.warm` | xs-aH | 0.1836 | 305 | 408 |
| `small-real.fresh.neo-freya.sender.warm` | xs-aX | 0.0421 | 18 | 24 |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.1317 | 158 | 211 |
| `small-real.noop.freya-neo.sender.warm` | xs-rt | 0.0424 | 19 | 24 |
| `small-real.noop.freya-neo.sender.warm` | xs-aH | 0.1933 | 338 | 452 |
| `small-real.noop.freya-neo.sender.warm` | xs-aX | 0.1000 | 92 | 123 |
| `small-real.noop.freya-neo.sender.warm` | rsync | 0.0892 | 74 | 98 |
| `small-real.noop.neo-freya.sender.warm` | xs-rt | 0.1603 | 233 | 312 |
| `small-real.noop.neo-freya.sender.warm` | xs-aH | 0.1941 | 340 | 455 |
| `small-real.noop.neo-freya.sender.warm` | xs-aX | 0.1890 | 323 | 432 |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.1847 | 309 | 413 |
