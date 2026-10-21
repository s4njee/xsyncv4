# E1v2-baseline

xs -a differs from rsync -a by more than 3% in time-to-durable, per corpus, scenario and direction.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020834Z-E1v2-baseline.
- Valid blocks: 336. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 12 | 0.988 [0.977, 0.999] | 0.991 [0.976, 0.999] | 0.0283 | 0.0938 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 12 | 1.037 [1.028, 1.047] | 1.037 [1.027, 1.047] | 0.0005 | 0.0137 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 12 | 0.619 [0.596, 0.642] | 0.619 [0.598, 0.645] | 0.0005 | 0.0137 | faster |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 12 | 0.652 [0.632, 0.673] | 0.656 [0.633, 0.679] | 0.0005 | 0.0137 | faster |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 12 | 0.991 [0.982, 1.001] | 0.991 [0.984, 1.002] | 0.0669 | 0.1338 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 12 | 1.037 [1.025, 1.050] | 1.037 [1.027, 1.048] | 0.0005 | 0.0137 | inconclusive |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 12 | 0.930 [0.903, 0.958] | 0.927 [0.906, 0.959] | 0.0020 | 0.0156 | faster |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 12 | 0.867 [0.850, 0.885] | 0.867 [0.848, 0.887] | 0.0005 | 0.0137 | faster |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 12 | 0.774 [0.743, 0.807] | 0.771 [0.739, 0.806] | 0.0005 | 0.0137 | faster |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 12 | 0.922 [0.745, 1.141] | 0.888 [0.743, 1.140] | 0.4272 | 0.4272 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | xs | 12 | 0.150 [0.136, 0.165] | 0.150 [0.135, 0.166] | 0.0005 | 0.0137 | faster |
| `small-deep.noop.neo-freya.sender.warm` | xs | 12 | 0.564 [0.498, 0.639] | 0.555 [0.498, 0.650] | 0.0005 | 0.0137 | faster |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 12 | 0.955 [0.933, 0.978] | 0.953 [0.931, 0.976] | 0.0024 | 0.0171 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 12 | 0.614 [0.521, 0.724] | 0.605 [0.511, 0.731] | 0.0005 | 0.0137 | faster |
| `small-flat.noop.freya-neo.sender.warm` | xs | 12 | 0.426 [0.409, 0.444] | 0.430 [0.410, 0.442] | 0.0005 | 0.0137 | faster |
| `small-flat.noop.neo-freya.sender.warm` | xs | 12 | 0.383 [0.347, 0.422] | 0.371 [0.344, 0.423] | 0.0005 | 0.0137 | faster |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 12 | 0.925 [0.865, 0.990] | 0.948 [0.864, 0.984] | 0.0015 | 0.0137 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 12 | 0.580 [0.505, 0.667] | 0.575 [0.500, 0.670] | 0.0005 | 0.0137 | faster |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 12 | 0.416 [0.395, 0.438] | 0.421 [0.392, 0.440] | 0.0005 | 0.0137 | faster |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 12 | 0.423 [0.381, 0.469] | 0.419 [0.377, 0.475] | 0.0005 | 0.0137 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs | 12 | 0.718 [0.687, 0.750] | 0.715 [0.689, 0.751] | 0.0005 | 0.0137 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 12 | 0.945 [0.910, 0.981] | 0.945 [0.905, 0.987] | 0.0112 | 0.0562 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs | 12 | 0.152 [0.141, 0.164] | 0.148 [0.142, 0.164] | 0.0005 | 0.0137 | faster |
| `small-real.noop.neo-freya.sender.warm` | xs | 12 | 0.732 [0.660, 0.813] | 0.722 [0.654, 0.813] | 0.0010 | 0.0137 | faster |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 12 | 0.923 [0.885, 0.962] | 0.917 [0.880, 0.962] | 0.0044 | 0.0264 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 12 | 0.885 [0.856, 0.914] | 0.890 [0.856, 0.909] | 0.0005 | 0.0137 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 12 | 0.959 [0.926, 0.993] | 0.960 [0.922, 0.994] | 0.0234 | 0.0938 | inconclusive |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 12 | 0.888 [0.870, 0.906] | 0.894 [0.880, 0.902] | 0.0005 | 0.0137 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.939 [1.882, 1.996] | 9.993 [9.849, 10.139] | 0.987 [0.977, 0.997] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.076 [2.008, 2.146] | 8.128 [7.972, 8.287] | 1.037 [1.027, 1.046] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 1.691 [1.615, 1.770] | 1.412 [1.391, 1.433] | 0.610 [0.586, 0.635] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 1.707 [1.593, 1.829] | 1.348 [1.322, 1.373] | 0.650 [0.630, 0.671] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 2.311 [2.263, 2.360] | 8.146 [8.065, 8.227] | 0.984 [0.974, 0.994] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 2.078 [1.998, 2.162] | 7.802 [7.676, 7.930] | 1.037 [1.025, 1.050] |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 2.083 [1.974, 2.198] | 1.306 [1.278, 1.334] | 0.930 [0.901, 0.959] |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 1.773 [1.718, 1.830] | 1.351 [1.324, 1.379] | 0.866 [0.848, 0.884] |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.894 [0.861, 0.929] | 0.576 [0.549, 0.605] | 0.771 [0.739, 0.804] |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 2.354 [2.224, 2.491] | 5.734 [4.932, 6.666] | 0.916 [0.733, 1.145] |
| `small-deep.noop.freya-neo.sender.warm` | xs | 1.100 [1.044, 1.159] | 1.063 [1.051, 1.075] | 0.149 [0.135, 0.165] |
| `small-deep.noop.neo-freya.sender.warm` | xs | 5.491 [5.225, 5.771] | 5.413 [5.146, 5.695] | 0.564 [0.498, 0.639] |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 1.457 [1.416, 1.499] | 10.018 [9.679, 10.369] | 0.956 [0.932, 0.980] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.521 [1.468, 1.575] | 5.922 [4.992, 7.027] | 0.604 [0.514, 0.710] |
| `small-flat.noop.freya-neo.sender.warm` | xs | 1.215 [1.148, 1.285] | 2.166 [2.132, 2.202] | 0.418 [0.401, 0.435] |
| `small-flat.noop.neo-freya.sender.warm` | xs | 1.191 [1.047, 1.354] | 1.683 [1.650, 1.716] | 0.381 [0.346, 0.421] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 1.430 [1.395, 1.467] | 9.911 [9.755, 10.070] | 0.919 [0.855, 0.988] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.529 [1.475, 1.584] | 4.963 [4.085, 6.030] | 0.576 [0.494, 0.672] |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 1.180 [1.102, 1.263] | 2.099 [2.073, 2.126] | 0.410 [0.389, 0.432] |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 1.380 [1.188, 1.602] | 1.680 [1.650, 1.710] | 0.421 [0.379, 0.468] |
| `small-real.fresh.freya-neo.sender.warm` | xs | 1.029 [1.008, 1.050] | 0.765 [0.753, 0.777] | 0.709 [0.679, 0.741] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.959 [1.925, 1.993] | 10.080 [9.792, 10.375] | 0.945 [0.911, 0.980] |
| `small-real.noop.freya-neo.sender.warm` | xs | 1.289 [1.243, 1.337] | 0.620 [0.605, 0.635] | 0.151 [0.140, 0.163] |
| `small-real.noop.neo-freya.sender.warm` | xs | 8.381 [8.139, 8.630] | 4.544 [4.109, 5.025] | 0.730 [0.657, 0.810] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 1.560 [1.426, 1.707] | 1.330 [1.304, 1.357] | 0.922 [0.884, 0.962] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.362 [1.320, 1.404] | 1.338 [1.309, 1.369] | 0.884 [0.855, 0.913] |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 1.601 [1.498, 1.711] | 1.323 [1.294, 1.353] | 0.955 [0.923, 0.987] |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 1.300 [1.250, 1.353] | 1.328 [1.302, 1.354] | 0.887 [0.870, 0.905] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 13.010 | 12.857 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.278 | 12.734 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.383 | 0.237 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.296 | 0.193 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 13.935 | 13.815 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.175 | 13.668 |
| `mixed-threshold.noop.freya-neo.sender.warm` | 0.240 | 0.223 |
| `mixed-threshold.noop.neo-freya.sender.warm` | 0.191 | 0.165 |
| `small-deep.fresh.freya-neo.sender.warm` | 25.198 | 19.513 |
| `small-deep.fresh.neo-freya.sender.warm` | 7.856 | 7.242 |
| `small-deep.noop.freya-neo.sender.warm` | 18.225 | 2.726 |
| `small-deep.noop.neo-freya.sender.warm` | 2.971 | 1.676 |
| `small-flat.fresh.freya-neo.sender.warm` | 7.002 | 6.685 |
| `small-flat.fresh.neo-freya.sender.warm` | 5.594 | 3.435 |
| `small-flat.noop.freya-neo.sender.warm` | 0.751 | 0.320 |
| `small-flat.noop.neo-freya.sender.warm` | 0.738 | 0.283 |
| `small-opaque.fresh.freya-neo.sender.warm` | 7.300 | 6.755 |
| `small-opaque.fresh.neo-freya.sender.warm` | 6.016 | 3.492 |
| `small-opaque.noop.freya-neo.sender.warm` | 0.768 | 0.320 |
| `small-opaque.noop.neo-freya.sender.warm` | 0.696 | 0.294 |
| `small-real.fresh.freya-neo.sender.warm` | 23.644 | 16.980 |
| `small-real.fresh.neo-freya.sender.warm` | 11.866 | 11.210 |
| `small-real.noop.freya-neo.sender.warm` | 9.162 | 1.391 |
| `small-real.noop.neo-freya.sender.warm` | 2.181 | 1.598 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.233 | 0.215 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.182 | 0.161 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.228 | 0.219 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.182 | 0.162 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.0172 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0142 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 0.0589 | 34 | 44 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 0.0492 | 24 | 32 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 0.0151 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.0185 | 8 | 8 |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 0.0467 | 22 | 29 |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 0.0320 | 12 | 15 |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.0651 | 40 | 53 |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 0.3363 | 1017 | 1362 |
| `small-deep.noop.freya-neo.sender.warm` | xs | 0.1538 | 215 | 287 |
| `small-deep.noop.neo-freya.sender.warm` | xs | 0.1962 | 348 | 465 |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 0.0372 | 15 | 19 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.2598 | 608 | 814 |
| `small-flat.noop.freya-neo.sender.warm` | xs | 0.0651 | 41 | 53 |
| `small-flat.noop.neo-freya.sender.warm` | xs | 0.1543 | 216 | 289 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 0.1055 | 102 | 136 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.2196 | 435 | 583 |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 0.0815 | 62 | 82 |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 0.1636 | 243 | 324 |
| `small-real.fresh.freya-neo.sender.warm` | xs | 0.0687 | 45 | 59 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.0588 | 33 | 44 |
| `small-real.noop.freya-neo.sender.warm` | xs | 0.1199 | 132 | 176 |
| `small-real.noop.neo-freya.sender.warm` | xs | 0.1644 | 245 | 328 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 0.0659 | 42 | 55 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.0518 | 27 | 35 |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 0.0548 | 29 | 39 |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 0.0312 | 11 | 14 |

## Voided attempts

- round trip is 2.021 ms, above 2.0
