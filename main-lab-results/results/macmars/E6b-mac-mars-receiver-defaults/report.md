# E6b-mac-mars-receiver-defaults

xs with at most four receiving workers and a backed-off peer wait is faster than its parent in at least one cell into mars and slower in none, both ways.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T144630Z-E6b-mac-mars-receiver-defaults.
- Valid blocks: 240. Voided block attempts: 2.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-recv4 | 12 | 1.006 [0.944, 1.073] | 0.988 [0.933, 1.083] | 0.8379 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 12 | 3.008 [2.595, 3.487] | 2.979 [2.554, 3.510] | 0.0005 | 0.0195 | slower |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.980 [0.854, 1.126] | 0.994 [0.840, 1.083] | 0.7437 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 12 | 2.074 [1.906, 2.256] | 2.114 [1.900, 2.264] | 0.0005 | 0.0195 | slower |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-recv4 | 12 | 0.927 [0.853, 1.007] | 0.921 [0.853, 1.010] | 0.0698 | 1.0000 | inconclusive |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 12 | 1.377 [1.289, 1.470] | 1.369 [1.286, 1.479] | 0.0005 | 0.0195 | slower |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.951 [0.866, 1.044] | 0.927 [0.863, 1.048] | 0.2515 | 1.0000 | inconclusive |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 12 | 1.141 [1.007, 1.293] | 1.140 [1.006, 1.240] | 0.0264 | 0.4746 | inconclusive |
| `real-congress.fresh.mac-mars.sender.warm` | xs-recv4 | 12 | 0.997 [0.947, 1.049] | 1.006 [0.950, 1.050] | 0.9097 | 1.0000 | inconclusive |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 12 | 4.753 [4.330, 5.218] | 4.661 [4.329, 5.253] | 0.0005 | 0.0195 | slower |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.910 [0.773, 1.071] | 0.960 [0.773, 1.078] | 0.2505 | 1.0000 | inconclusive |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 12 | 1.384 [1.099, 1.744] | 1.488 [1.114, 1.734] | 0.0132 | 0.2637 | slower |
| `real-congress.noop.mac-mars.sender.warm` | xs-recv4 | 12 | 0.959 [0.880, 1.045] | 0.977 [0.875, 1.047] | 0.3325 | 1.0000 | inconclusive |
| `real-congress.noop.mac-mars.sender.warm` | rsync | 12 | 3.993 [3.537, 4.509] | 3.981 [3.535, 4.505] | 0.0005 | 0.0195 | slower |
| `real-congress.noop.mars-mac.receiver.warm` | xs-recv4 | 12 | 1.026 [0.916, 1.150] | 1.014 [0.915, 1.175] | 0.6406 | 1.0000 | inconclusive |
| `real-congress.noop.mars-mac.receiver.warm` | rsync | 12 | 1.402 [1.216, 1.616] | 1.368 [1.209, 1.633] | 0.0005 | 0.0195 | slower |
| `small-deep.fresh.mac-mars.sender.warm` | xs-recv4 | 12 | 0.938 [0.855, 1.029] | 0.943 [0.861, 1.031] | 0.1558 | 1.0000 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 12 | 3.926 [3.492, 4.414] | 3.886 [3.486, 4.425] | 0.0005 | 0.0195 | slower |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.961 [0.810, 1.140] | 0.975 [0.889, 1.062] | 0.5610 | 1.0000 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 12 | 1.164 [1.047, 1.294] | 1.158 [1.053, 1.276] | 0.0063 | 0.1460 | inconclusive |
| `small-deep.noop.mac-mars.sender.warm` | xs-recv4 | 12 | 0.960 [0.906, 1.016] | 0.981 [0.891, 1.012] | 0.1631 | 1.0000 | inconclusive |
| `small-deep.noop.mac-mars.sender.warm` | rsync | 12 | 4.519 [4.104, 4.975] | 4.473 [4.092, 4.962] | 0.0005 | 0.0195 | slower |
| `small-deep.noop.mars-mac.receiver.warm` | xs-recv4 | 12 | 1.013 [0.955, 1.075] | 1.000 [0.961, 1.045] | 0.7700 | 1.0000 | inconclusive |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 12 | 0.536 [0.495, 0.580] | 0.541 [0.487, 0.583] | 0.0005 | 0.0195 | faster |
| `small-flat.fresh.mac-mars.sender.warm` | xs-recv4 | 12 | 0.986 [0.954, 1.020] | 0.974 [0.956, 1.025] | 0.3828 | 1.0000 | equivalent |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 12 | 2.692 [1.950, 3.716] | 2.703 [1.812, 3.973] | 0.0005 | 0.0195 | slower |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.887 [0.690, 1.139] | 0.981 [0.906, 1.028] | 0.3477 | 1.0000 | inconclusive |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 12 | 1.460 [1.159, 1.840] | 1.625 [1.344, 1.708] | 0.0103 | 0.2153 | slower |
| `small-flat.noop.mac-mars.sender.warm` | xs-recv4 | 12 | 0.862 [0.812, 0.915] | 0.872 [0.807, 0.910] | 0.0010 | 0.0254 | faster |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 12 | 2.291 [2.036, 2.579] | 2.214 [2.063, 2.562] | 0.0005 | 0.0195 | slower |
| `small-flat.noop.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.960 [0.905, 1.018] | 0.977 [0.900, 1.019] | 0.1479 | 1.0000 | inconclusive |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 12 | 1.546 [1.399, 1.708] | 1.564 [1.410, 1.712] | 0.0005 | 0.0195 | slower |
| `tiny-one.fresh.mac-mars.sender.warm` | xs-recv4 | 12 | 0.913 [0.857, 0.973] | 0.914 [0.851, 0.983] | 0.0098 | 0.2148 | inconclusive |
| `tiny-one.fresh.mac-mars.sender.warm` | rsync | 12 | 1.106 [1.046, 1.171] | 1.090 [1.046, 1.180] | 0.0005 | 0.0195 | inconclusive |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.846 [0.797, 0.899] | 0.833 [0.794, 0.905] | 0.0015 | 0.0366 | faster |
| `tiny-one.fresh.mars-mac.receiver.warm` | rsync | 12 | 1.011 [0.940, 1.087] | 0.994 [0.941, 1.086] | 0.8159 | 1.0000 | inconclusive |
| `tiny-one.noop.mac-mars.sender.warm` | xs-recv4 | 12 | 0.864 [0.794, 0.940] | 0.885 [0.785, 0.935] | 0.0005 | 0.0195 | faster |
| `tiny-one.noop.mac-mars.sender.warm` | rsync | 12 | 1.149 [1.023, 1.291] | 1.130 [1.013, 1.306] | 0.0161 | 0.3062 | inconclusive |
| `tiny-one.noop.mars-mac.receiver.warm` | xs-recv4 | 12 | 0.878 [0.816, 0.944] | 0.878 [0.811, 0.954] | 0.0034 | 0.0820 | inconclusive |
| `tiny-one.noop.mars-mac.receiver.warm` | rsync | 12 | 0.994 [0.912, 1.083] | 0.965 [0.912, 1.081] | 0.8711 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-recv4 | 0.987 [0.946, 1.030] | 1.001 [0.949, 1.056] | 1.021 [0.972, 1.071] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.303 [1.113, 1.524] | 2.762 [2.276, 3.353] | 0.077 [0.075, 0.079] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-recv4 | 1.005 [0.938, 1.077] | 0.980 [0.853, 1.124] | 1.029 [0.986, 1.075] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.256 [1.183, 1.333] | 2.048 [1.886, 2.223] | 1.507 [1.423, 1.595] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-recv4 | 0.498 [0.456, 0.544] | 0.927 [0.855, 1.007] | 0.903 [0.892, 0.915] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.289 [0.249, 0.336] | 1.370 [1.283, 1.462] | 0.899 [0.891, 0.907] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-recv4 | 1.024 [0.962, 1.090] | 0.962 [0.883, 1.047] | 0.998 [0.976, 1.020] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.386 [0.348, 0.428] | 1.126 [1.013, 1.251] | 0.816 [0.797, 0.835] |
| `real-congress.fresh.mac-mars.sender.warm` | xs-recv4 | 0.920 [0.879, 0.963] | 0.997 [0.952, 1.045] | 0.919 [0.772, 1.094] |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 0.974 [0.866, 1.096] | 4.258 [3.820, 4.747] | 0.131 [0.113, 0.151] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.924 [0.817, 1.046] | 0.911 [0.773, 1.073] | 0.956 [0.876, 1.044] |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 1.211 [1.020, 1.438] | 1.383 [1.098, 1.741] | 1.261 [1.187, 1.339] |
| `real-congress.noop.mac-mars.sender.warm` | xs-recv4 | 0.761 [0.738, 0.784] | 0.959 [0.880, 1.045] | 1.000 [0.989, 1.013] |
| `real-congress.noop.mac-mars.sender.warm` | rsync | 0.479 [0.400, 0.575] | 3.985 [3.529, 4.500] | 0.367 [0.360, 0.374] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-recv4 | 1.010 [0.945, 1.080] | 1.025 [0.916, 1.147] | 0.913 [0.658, 1.266] |
| `real-congress.noop.mars-mac.receiver.warm` | rsync | 0.322 [0.283, 0.366] | 1.394 [1.209, 1.607] | 0.280 [0.212, 0.368] |
| `small-deep.fresh.mac-mars.sender.warm` | xs-recv4 | 0.872 [0.803, 0.946] | 0.897 [0.774, 1.040] | 0.915 [0.781, 1.072] |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 0.806 [0.739, 0.880] | 3.527 [3.131, 3.972] | 0.189 [0.162, 0.220] |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.959 [0.856, 1.074] | 0.961 [0.811, 1.140] | 1.012 [1.000, 1.023] |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.923 [0.849, 1.003] | 1.164 [1.047, 1.295] | 0.922 [0.750, 1.134] |
| `small-deep.noop.mac-mars.sender.warm` | xs-recv4 | 0.809 [0.788, 0.831] | 0.960 [0.906, 1.016] | 0.974 [0.921, 1.030] |
| `small-deep.noop.mac-mars.sender.warm` | rsync | 0.553 [0.464, 0.660] | 4.513 [4.099, 4.969] | 0.278 [0.272, 0.285] |
| `small-deep.noop.mars-mac.receiver.warm` | xs-recv4 | 1.008 [0.971, 1.047] | 1.014 [0.955, 1.076] | 1.031 [0.992, 1.072] |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 0.149 [0.141, 0.157] | 0.540 [0.498, 0.584] | 0.204 [0.197, 0.211] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-recv4 | 0.915 [0.818, 1.024] | 0.987 [0.957, 1.017] | 0.828 [0.604, 1.135] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.707 [0.623, 0.802] | 2.478 [1.825, 3.366] | 0.113 [0.099, 0.128] |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.925 [0.768, 1.114] | 0.888 [0.693, 1.137] | 1.021 [0.911, 1.144] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.306 [1.102, 1.549] | 1.453 [1.156, 1.827] | 1.623 [1.485, 1.774] |
| `small-flat.noop.mac-mars.sender.warm` | xs-recv4 | 0.427 [0.364, 0.501] | 0.850 [0.795, 0.910] | 0.673 [0.657, 0.689] |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.233 [0.187, 0.289] | 2.237 [1.967, 2.545] | 0.667 [0.647, 0.687] |
| `small-flat.noop.mars-mac.receiver.warm` | xs-recv4 | 1.017 [0.994, 1.040] | 0.967 [0.911, 1.026] | 1.513 [1.008, 2.270] |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.425 [0.390, 0.463] | 1.505 [1.380, 1.642] | 0.428 [0.322, 0.568] |
| `tiny-one.fresh.mac-mars.sender.warm` | xs-recv4 | 0.803 [0.743, 0.868] | 0.913 [0.859, 0.971] | 0.922 [0.910, 0.934] |
| `tiny-one.fresh.mac-mars.sender.warm` | rsync | 0.881 [0.815, 0.953] | 1.101 [1.041, 1.166] | 0.930 [0.921, 0.938] |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs-recv4 | 1.020 [0.973, 1.070] | 0.869 [0.826, 0.914] | 0.996 [0.982, 1.011] |
| `tiny-one.fresh.mars-mac.receiver.warm` | rsync | 0.928 [0.844, 1.020] | 1.281 [0.772, 2.124] | 0.934 [0.926, 0.942] |
| `tiny-one.noop.mac-mars.sender.warm` | xs-recv4 | 0.781 [0.721, 0.847] | 0.869 [0.800, 0.944] | 0.926 [0.917, 0.934] |
| `tiny-one.noop.mac-mars.sender.warm` | rsync | 0.894 [0.805, 0.993] | 1.149 [1.026, 1.288] | 0.922 [0.913, 0.931] |
| `tiny-one.noop.mars-mac.receiver.warm` | xs-recv4 | 0.961 [0.900, 1.026] | 0.917 [0.873, 0.964] | 1.000 [0.990, 1.010] |
| `tiny-one.noop.mars-mac.receiver.warm` | rsync | 0.945 [0.870, 1.025] | 0.986 [0.927, 1.048] | 0.933 [0.923, 0.944] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-recv4 |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 5.960 | 1.981 | 1.993 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 10.762 | 5.190 | 5.087 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.359 | 0.261 | 0.242 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | 0.435 | 0.381 | 0.362 |
| `real-congress.fresh.mac-mars.sender.warm` | 41.264 | 8.681 | 8.656 |
| `real-congress.fresh.mars-mac.receiver.warm` | 93.576 | 67.596 | 61.500 |
| `real-congress.noop.mac-mars.sender.warm` | 7.617 | 1.907 | 1.830 |
| `real-congress.noop.mars-mac.receiver.warm` | 5.570 | 3.973 | 4.077 |
| `small-deep.fresh.mac-mars.sender.warm` | 30.803 | 7.846 | 7.359 |
| `small-deep.fresh.mars-mac.receiver.warm` | 62.576 | 53.757 | 51.677 |
| `small-deep.noop.mac-mars.sender.warm` | 13.973 | 3.092 | 2.968 |
| `small-deep.noop.mars-mac.receiver.warm` | 5.684 | 10.611 | 10.748 |
| `small-flat.fresh.mac-mars.sender.warm` | 10.220 | 3.797 | 3.745 |
| `small-flat.fresh.mars-mac.receiver.warm` | 30.148 | 20.646 | 18.308 |
| `small-flat.noop.mac-mars.sender.warm` | 0.834 | 0.364 | 0.314 |
| `small-flat.noop.mars-mac.receiver.warm` | 1.321 | 0.855 | 0.820 |
| `tiny-one.fresh.mac-mars.sender.warm` | 0.240 | 0.217 | 0.198 |
| `tiny-one.fresh.mars-mac.receiver.warm` | 0.229 | 0.226 | 0.192 |
| `tiny-one.noop.mac-mars.sender.warm` | 0.257 | 0.223 | 0.193 |
| `tiny-one.noop.mars-mac.receiver.warm` | 0.229 | 0.230 | 0.202 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-recv4 | 0.1008 | 94 | 125 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.2325 | 488 | 653 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.2177 | 428 | 573 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.1325 | 160 | 214 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs-recv4 | 0.1301 | 154 | 206 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.1035 | 99 | 131 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | xs-recv4 | 0.1467 | 196 | 261 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.1962 | 348 | 466 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-recv4 | 0.0807 | 61 | 81 |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 0.1467 | 196 | 261 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.2570 | 595 | 797 |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 0.3637 | 1190 | 1594 |
| `real-congress.noop.mac-mars.sender.warm` | xs-recv4 | 0.1355 | 167 | 223 |
| `real-congress.noop.mac-mars.sender.warm` | rsync | 0.1911 | 330 | 442 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-recv4 | 0.1787 | 289 | 386 |
| `real-congress.noop.mars-mac.receiver.warm` | rsync | 0.2238 | 452 | 605 |
| `small-deep.fresh.mac-mars.sender.warm` | xs-recv4 | 0.1453 | 192 | 257 |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 0.1844 | 308 | 411 |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.2689 | 652 | 872 |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.1672 | 253 | 339 |
| `small-deep.noop.mac-mars.sender.warm` | xs-recv4 | 0.0903 | 76 | 100 |
| `small-deep.noop.mac-mars.sender.warm` | rsync | 0.1514 | 208 | 278 |
| `small-deep.noop.mars-mac.receiver.warm` | xs-recv4 | 0.0933 | 81 | 107 |
| `small-deep.noop.mars-mac.receiver.warm` | rsync | 0.1254 | 144 | 192 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-recv4 | 0.0526 | 27 | 36 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.5077 | 2315 | 3102 |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.3941 | 1396 | 1870 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.3634 | 1188 | 1591 |
| `small-flat.noop.mac-mars.sender.warm` | xs-recv4 | 0.0948 | 83 | 111 |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.1859 | 313 | 418 |
| `small-flat.noop.mars-mac.receiver.warm` | xs-recv4 | 0.0932 | 81 | 107 |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.1570 | 224 | 299 |
| `tiny-one.fresh.mac-mars.sender.warm` | xs-recv4 | 0.1000 | 92 | 123 |
| `tiny-one.fresh.mac-mars.sender.warm` | rsync | 0.0890 | 74 | 98 |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs-recv4 | 0.0944 | 82 | 110 |
| `tiny-one.fresh.mars-mac.receiver.warm` | rsync | 0.1144 | 120 | 160 |
| `tiny-one.noop.mac-mars.sender.warm` | xs-recv4 | 0.1331 | 161 | 215 |
| `tiny-one.noop.mac-mars.sender.warm` | rsync | 0.1824 | 301 | 403 |
| `tiny-one.noop.mars-mac.receiver.warm` | xs-recv4 | 0.1149 | 121 | 161 |
| `tiny-one.noop.mars-mac.receiver.warm` | rsync | 0.1355 | 167 | 223 |

## Voided attempts

- round trip is 2.278 ms, above 2.0
- round trip is 2.369 ms, above 2.0
