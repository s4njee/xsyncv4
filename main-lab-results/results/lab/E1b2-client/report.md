# E1b2-client

A transfer started by the receiver takes the same time, within 3%, as the same transfer started by the sender.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs-push`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220719Z-E1b2-client.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 10 | 0.998 [0.995, 1.002] | 0.997 [0.995, 1.002] | 0.3047 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 10 | 1.010 [1.004, 1.015] | 1.010 [1.004, 1.015] | 0.0059 | 0.0879 | equivalent |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 1.000 [0.996, 1.004] | 1.000 [0.995, 1.005] | 0.9902 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 10 | 1.020 [1.004, 1.036] | 1.021 [1.003, 1.037] | 0.0215 | 0.2148 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 10 | 0.963 [0.952, 0.974] | 0.964 [0.952, 0.973] | 0.0020 | 0.0703 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 0.966 [0.954, 0.979] | 0.968 [0.952, 0.979] | 0.0020 | 0.0703 | inconclusive |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.805 [0.766, 0.845] | 0.815 [0.756, 0.836] | 0.0020 | 0.0703 | faster |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 10 | 1.610 [1.547, 1.674] | 1.615 [1.554, 1.671] | 0.0020 | 0.0703 | slower |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 10 | 1.325 [1.239, 1.416] | 1.314 [1.241, 1.411] | 0.0020 | 0.0703 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 10 | 1.365 [1.297, 1.437] | 1.364 [1.304, 1.440] | 0.0020 | 0.0703 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 10 | 1.508 [1.483, 1.534] | 1.507 [1.485, 1.535] | 0.0020 | 0.0703 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 10 | 1.654 [1.625, 1.684] | 1.653 [1.629, 1.682] | 0.0020 | 0.0703 | slower |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 10 | 0.993 [0.982, 1.005] | 0.993 [0.982, 1.006] | 0.2285 | 1.0000 | equivalent |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 10 | 1.049 [1.007, 1.093] | 1.040 [1.007, 1.094] | 0.0156 | 0.1719 | inconclusive |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 1.066 [1.028, 1.105] | 1.068 [1.027, 1.108] | 0.0059 | 0.0879 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 10 | 1.010 [0.982, 1.039] | 1.010 [0.983, 1.036] | 0.4551 | 1.0000 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 10 | 1.743 [1.412, 2.152] | 1.816 [1.431, 2.220] | 0.0020 | 0.0703 | slower |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 1.847 [1.580, 2.159] | 1.901 [1.569, 2.144] | 0.0020 | 0.0703 | slower |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.871 [0.808, 0.939] | 0.874 [0.806, 0.944] | 0.0059 | 0.0879 | faster |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 10 | 2.355 [2.257, 2.457] | 2.358 [2.272, 2.459] | 0.0020 | 0.0703 | slower |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 10 | 2.179 [2.075, 2.288] | 2.177 [2.088, 2.286] | 0.0020 | 0.0703 | slower |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 10 | 1.308 [1.208, 1.415] | 1.315 [1.220, 1.420] | 0.0020 | 0.0703 | slower |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 10 | 2.454 [2.317, 2.599] | 2.456 [2.325, 2.593] | 0.0020 | 0.0703 | slower |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 10 | 2.627 [2.407, 2.867] | 2.620 [2.437, 2.857] | 0.0020 | 0.0703 | slower |
| `small-real.fresh.freya-neo.arm.warm` | xs-pull | 10 | 0.982 [0.928, 1.040] | 0.971 [0.931, 1.045] | 0.4922 | 1.0000 | inconclusive |
| `small-real.fresh.freya-neo.arm.warm` | rsync-push | 10 | 1.365 [1.313, 1.419] | 1.354 [1.316, 1.426] | 0.0020 | 0.0703 | slower |
| `small-real.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 1.372 [1.319, 1.428] | 1.373 [1.314, 1.432] | 0.0020 | 0.0703 | slower |
| `small-real.fresh.neo-freya.arm.warm` | xs-pull | 10 | 1.026 [0.935, 1.126] | 1.005 [0.957, 1.168] | 0.7598 | 1.0000 | inconclusive |
| `small-real.fresh.neo-freya.arm.warm` | rsync-push | 10 | 1.127 [0.957, 1.328] | 1.047 [0.992, 1.409] | 0.0723 | 0.6504 | inconclusive |
| `small-real.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 1.082 [0.931, 1.258] | 1.049 [0.929, 1.386] | 0.3262 | 1.0000 | inconclusive |
| `small-real.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.969 [0.912, 1.029] | 0.968 [0.923, 1.028] | 0.2695 | 1.0000 | inconclusive |
| `small-real.noop.freya-neo.arm.warm` | rsync-push | 10 | 6.736 [6.466, 7.017] | 6.716 [6.453, 7.041] | 0.0020 | 0.0703 | slower |
| `small-real.noop.freya-neo.arm.warm` | rsync-pull | 10 | 6.858 [6.565, 7.165] | 6.792 [6.591, 7.184] | 0.0020 | 0.0703 | slower |
| `small-real.noop.neo-freya.arm.warm` | xs-pull | 10 | 1.141 [1.047, 1.244] | 1.154 [1.046, 1.244] | 0.0117 | 0.1406 | slower |
| `small-real.noop.neo-freya.arm.warm` | rsync-push | 10 | 1.306 [1.201, 1.421] | 1.297 [1.189, 1.440] | 0.0020 | 0.0703 | slower |
| `small-real.noop.neo-freya.arm.warm` | rsync-pull | 10 | 1.345 [1.226, 1.476] | 1.350 [1.201, 1.497] | 0.0020 | 0.0703 | slower |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 1.677 [1.621, 1.735] | 0.996 [0.990, 1.002] | 0.996 [0.988, 1.004] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 0.514 [0.500, 0.528] | 1.006 [1.001, 1.010] | 0.099 [0.098, 0.101] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 1.096 [1.072, 1.120] | 0.994 [0.988, 1.000] | 0.101 [0.099, 0.104] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 0.748 [0.728, 0.769] | 1.018 [1.001, 1.035] | 1.005 [0.999, 1.012] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 0.467 [0.446, 0.490] | 0.961 [0.950, 0.972] | 0.122 [0.118, 0.126] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.313 [0.299, 0.328] | 0.965 [0.952, 0.978] | 0.118 [0.115, 0.120] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 1.054 [1.025, 1.083] | 0.813 [0.775, 0.854] | 1.005 [0.975, 1.036] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 0.571 [0.547, 0.595] | 1.588 [1.527, 1.652] | 0.710 [0.692, 0.728] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 0.629 [0.609, 0.650] | 1.313 [1.230, 1.401] | 0.706 [0.696, 0.717] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 0.925 [0.856, 1.000] | 1.360 [1.292, 1.432] | 0.996 [0.981, 1.011] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 0.556 [0.533, 0.580] | 1.502 [1.477, 1.527] | 0.730 [0.723, 0.737] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.507 [0.485, 0.530] | 1.646 [1.617, 1.675] | 0.726 [0.713, 0.739] |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 1.163 [1.145, 1.181] | 0.990 [0.979, 1.002] | 1.009 [0.987, 1.031] |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 0.688 [0.665, 0.712] | 1.039 [1.003, 1.076] | 0.099 [0.097, 0.102] |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 0.861 [0.838, 0.885] | 1.060 [1.021, 1.101] | 0.122 [0.115, 0.129] |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 0.877 [0.849, 0.905] | 1.023 [0.998, 1.050] | 1.065 [0.943, 1.202] |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 0.665 [0.649, 0.681] | 1.721 [1.398, 2.119] | 0.187 [0.151, 0.231] |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.609 [0.595, 0.624] | 1.822 [1.560, 2.129] | 0.194 [0.159, 0.237] |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 1.086 [0.980, 1.203] | 0.876 [0.813, 0.944] | 1.003 [0.985, 1.021] |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 0.785 [0.737, 0.837] | 2.318 [2.216, 2.425] | 0.465 [0.454, 0.476] |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 0.849 [0.790, 0.913] | 2.151 [2.049, 2.258] | 0.474 [0.465, 0.484] |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 0.988 [0.885, 1.102] | 1.306 [1.206, 1.414] | 1.013 [1.002, 1.025] |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 0.756 [0.693, 0.824] | 2.441 [2.301, 2.589] | 0.591 [0.582, 0.601] |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 0.749 [0.681, 0.824] | 2.613 [2.392, 2.856] | 0.588 [0.578, 0.599] |
| `small-real.fresh.freya-neo.arm.warm` | xs-pull | 1.197 [1.174, 1.220] | 0.977 [0.926, 1.030] | 0.991 [0.977, 1.005] |
| `small-real.fresh.freya-neo.arm.warm` | rsync-push | 0.960 [0.942, 0.978] | 1.352 [1.302, 1.403] | 1.295 [1.274, 1.317] |
| `small-real.fresh.freya-neo.arm.warm` | rsync-pull | 1.204 [1.164, 1.246] | 1.359 [1.307, 1.413] | 1.295 [1.273, 1.318] |
| `small-real.fresh.neo-freya.arm.warm` | xs-pull | 0.863 [0.851, 0.876] | 1.028 [0.937, 1.127] | 0.987 [0.930, 1.046] |
| `small-real.fresh.neo-freya.arm.warm` | rsync-push | 0.504 [0.492, 0.515] | 1.124 [0.955, 1.324] | 0.098 [0.094, 0.102] |
| `small-real.fresh.neo-freya.arm.warm` | rsync-pull | 0.431 [0.424, 0.439] | 1.079 [0.930, 1.253] | 0.100 [0.096, 0.103] |
| `small-real.noop.freya-neo.arm.warm` | xs-pull | 0.953 [0.892, 1.019] | 0.969 [0.913, 1.029] | 0.989 [0.959, 1.020] |
| `small-real.noop.freya-neo.arm.warm` | rsync-push | 0.825 [0.771, 0.882] | 6.703 [6.441, 6.976] | 1.630 [1.605, 1.655] |
| `small-real.noop.freya-neo.arm.warm` | rsync-pull | 0.850 [0.792, 0.911] | 6.826 [6.539, 7.126] | 1.630 [1.604, 1.656] |
| `small-real.noop.neo-freya.arm.warm` | xs-pull | 1.045 [1.019, 1.071] | 1.144 [1.050, 1.245] | 0.953 [0.881, 1.031] |
| `small-real.noop.neo-freya.arm.warm` | rsync-push | 0.112 [0.107, 0.117] | 1.306 [1.201, 1.420] | 0.218 [0.210, 0.226] |
| `small-real.noop.neo-freya.arm.warm` | rsync-pull | 0.112 [0.108, 0.117] | 1.345 [1.225, 1.476] | 0.219 [0.212, 0.226] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-pull | rsync-push | xs-pull | xs-push |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | 12.229 | 12.346 | 12.207 | 12.228 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | 12.302 | 12.259 | 12.983 | 12.730 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | 0.311 | 0.378 | 0.189 | 0.235 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | 0.310 | 0.283 | 0.256 | 0.188 |
| `small-flat.fresh.freya-neo.arm.warm` | 6.857 | 6.751 | 6.392 | 6.434 |
| `small-flat.fresh.neo-freya.arm.warm` | 6.275 | 5.922 | 3.432 | 3.398 |
| `small-flat.noop.freya-neo.arm.warm` | 0.687 | 0.742 | 0.275 | 0.315 |
| `small-flat.noop.neo-freya.arm.warm` | 0.713 | 0.667 | 0.355 | 0.272 |
| `small-real.fresh.freya-neo.arm.warm` | 23.666 | 23.542 | 16.936 | 17.245 |
| `small-real.fresh.neo-freya.arm.warm` | 12.432 | 12.950 | 11.788 | 11.489 |
| `small-real.noop.freya-neo.arm.warm` | 9.627 | 9.456 | 1.360 | 1.404 |
| `small-real.noop.neo-freya.arm.warm` | 2.103 | 2.042 | 1.783 | 1.563 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 0.0049 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 0.0072 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 0.0056 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 0.0213 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 0.0153 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.0179 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 0.0687 | 45 | 59 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 0.0551 | 30 | 39 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 0.0935 | 81 | 108 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 0.0718 | 49 | 65 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 0.0235 | 8 | 9 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.0248 | 8 | 10 |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 0.0162 | 8 | 8 |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 0.0570 | 32 | 42 |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 0.0501 | 25 | 33 |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 0.0396 | 17 | 21 |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 0.2946 | 781 | 1046 |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.2184 | 430 | 576 |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 0.1048 | 101 | 135 |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 0.0593 | 34 | 45 |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 0.0684 | 44 | 59 |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 0.1102 | 111 | 148 |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 0.0802 | 60 | 80 |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 0.1221 | 136 | 182 |
| `small-real.fresh.freya-neo.arm.warm` | xs-pull | 0.0795 | 59 | 78 |
| `small-real.fresh.freya-neo.arm.warm` | rsync-push | 0.0539 | 29 | 37 |
| `small-real.fresh.freya-neo.arm.warm` | rsync-pull | 0.0552 | 30 | 39 |
| `small-real.fresh.neo-freya.arm.warm` | xs-pull | 0.1300 | 154 | 206 |
| `small-real.fresh.neo-freya.arm.warm` | rsync-push | 0.2288 | 472 | 632 |
| `small-real.fresh.neo-freya.arm.warm` | rsync-pull | 0.2102 | 399 | 534 |
| `small-real.noop.freya-neo.arm.warm` | xs-pull | 0.0840 | 66 | 87 |
| `small-real.noop.freya-neo.arm.warm` | rsync-push | 0.0571 | 32 | 42 |
| `small-real.noop.freya-neo.arm.warm` | rsync-pull | 0.0612 | 36 | 47 |
| `small-real.noop.neo-freya.arm.warm` | xs-pull | 0.1206 | 133 | 177 |
| `small-real.noop.neo-freya.arm.warm` | rsync-push | 0.1174 | 126 | 168 |
| `small-real.noop.neo-freya.arm.warm` | rsync-pull | 0.1301 | 154 | 206 |
