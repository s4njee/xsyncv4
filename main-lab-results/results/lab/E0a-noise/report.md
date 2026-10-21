# E0a-noise

Two labels on one binary are equivalent within 3% in every cell.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T001524Z-E0a-noise.
- Valid blocks: 144. Voided block attempts: 3.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 12 | 1.005 [0.999, 1.010] | 1.005 [0.999, 1.011] | 0.1084 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 12 | 1.009 [1.003, 1.016] | 1.007 [1.004, 1.012] | 0.0005 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 12 | 1.005 [1.002, 1.009] | 1.006 [1.002, 1.009] | 0.0107 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 12 | 1.052 [0.942, 1.175] | 1.004 [0.988, 1.038] | 0.4365 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 12 | 0.937 [0.921, 0.954] | 0.940 [0.920, 0.955] | 0.0005 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 12 | 0.958 [0.907, 1.012] | 0.940 [0.921, 0.968] | 0.1104 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 12 | 0.988 [0.963, 1.014] | 0.994 [0.959, 1.013] | 0.3716 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 12 | 1.632 [1.573, 1.693] | 1.639 [1.570, 1.698] | 0.0005 | slower |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 12 | 1.618 [1.556, 1.682] | 1.617 [1.555, 1.684] | 0.0005 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 12 | 1.040 [1.014, 1.066] | 1.035 [1.010, 1.072] | 0.0093 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 12 | 1.508 [1.468, 1.549] | 1.505 [1.468, 1.546] | 0.0005 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 12 | 1.500 [1.457, 1.544] | 1.491 [1.458, 1.551] | 0.0005 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 12 | 1.013 [1.005, 1.022] | 1.013 [1.005, 1.022] | 0.0112 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 12 | 1.036 [1.008, 1.065] | 1.032 [1.007, 1.063] | 0.0107 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 12 | 1.089 [1.023, 1.161] | 1.078 [1.018, 1.168] | 0.0034 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 12 | 0.981 [0.909, 1.058] | 1.007 [0.979, 1.032] | 0.9312 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 12 | 1.233 [0.996, 1.527] | 1.255 [1.013, 1.566] | 0.0581 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 12 | 1.309 [1.049, 1.634] | 1.276 [1.073, 1.626] | 0.0190 | slower |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 12 | 0.998 [0.944, 1.056] | 1.009 [0.943, 1.051] | 0.9512 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 12 | 2.371 [2.228, 2.523] | 2.357 [2.283, 2.483] | 0.0005 | slower |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 12 | 2.426 [2.255, 2.609] | 2.440 [2.271, 2.588] | 0.0005 | slower |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 12 | 1.038 [0.999, 1.078] | 1.042 [1.001, 1.091] | 0.0488 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 12 | 2.415 [2.335, 2.497] | 2.420 [2.329, 2.508] | 0.0005 | slower |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 12 | 2.570 [2.384, 2.771] | 2.574 [2.350, 2.783] | 0.0005 | slower |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 12 | 0.989 [0.955, 1.026] | 0.986 [0.951, 1.029] | 0.5186 | inconclusive |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync | 12 | 1.072 [1.046, 1.099] | 1.075 [1.043, 1.102] | 0.0005 | slower |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 12 | 1.083 [1.045, 1.122] | 1.082 [1.041, 1.124] | 0.0010 | slower |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 12 | 1.004 [0.977, 1.032] | 1.012 [0.975, 1.031] | 0.7441 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync | 12 | 1.108 [1.084, 1.132] | 1.109 [1.082, 1.132] | 0.0005 | slower |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 12 | 1.103 [1.084, 1.122] | 1.097 [1.085, 1.125] | 0.0005 | slower |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 12 | 0.998 [0.973, 1.024] | 0.998 [0.972, 1.028] | 0.8862 | equivalent |
| `tiny-one.noop.freya-neo.sender.warm` | rsync | 12 | 1.094 [1.068, 1.120] | 1.098 [1.067, 1.122] | 0.0005 | slower |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 12 | 1.088 [1.055, 1.121] | 1.085 [1.067, 1.117] | 0.0010 | slower |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 12 | 1.017 [0.993, 1.042] | 1.017 [0.992, 1.046] | 0.1489 | inconclusive |
| `tiny-one.noop.neo-freya.sender.warm` | rsync | 12 | 1.118 [1.092, 1.145] | 1.116 [1.088, 1.147] | 0.0005 | slower |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 12 | 1.123 [1.093, 1.154] | 1.120 [1.091, 1.157] | 0.0005 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 1.023 [0.995, 1.052] | 1.001 [0.990, 1.011] | 1.005 [0.996, 1.015] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.517 [0.506, 0.528] | 1.007 [1.001, 1.013] | 0.099 [0.097, 0.100] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 0.508 [0.497, 0.519] | 1.003 [0.998, 1.008] | 0.099 [0.097, 0.100] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 1.003 [0.962, 1.046] | 1.067 [0.928, 1.228] | 1.001 [0.996, 1.006] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.438 [0.430, 0.446] | 0.945 [0.928, 0.962] | 0.126 [0.123, 0.129] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 0.441 [0.428, 0.455] | 0.961 [0.910, 1.015] | 0.125 [0.122, 0.127] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 1.008 [0.982, 1.035] | 0.988 [0.963, 1.013] | 1.014 [0.993, 1.036] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.579 [0.562, 0.596] | 1.623 [1.565, 1.684] | 0.690 [0.672, 0.709] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 0.585 [0.567, 0.604] | 1.609 [1.549, 1.670] | 0.709 [0.698, 0.721] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 1.026 [0.973, 1.083] | 1.034 [1.005, 1.063] | 0.991 [0.985, 0.997] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.557 [0.537, 0.577] | 1.494 [1.451, 1.537] | 0.717 [0.709, 0.726] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 0.547 [0.522, 0.574] | 1.486 [1.448, 1.524] | 0.722 [0.710, 0.735] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 1.015 [1.007, 1.023] | 1.016 [1.004, 1.027] | 0.980 [0.960, 1.001] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.674 [0.659, 0.689] | 1.027 [1.002, 1.053] | 0.099 [0.096, 0.101] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 0.679 [0.661, 0.698] | 1.083 [1.020, 1.151] | 0.097 [0.095, 0.099] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 1.012 [0.975, 1.052] | 0.989 [0.948, 1.032] | 1.005 [0.919, 1.099] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.672 [0.643, 0.702] | 1.211 [0.985, 1.489] | 0.133 [0.110, 0.161] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 0.674 [0.657, 0.692] | 1.276 [1.043, 1.561] | 0.134 [0.111, 0.161] |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 0.993 [0.896, 1.100] | 0.999 [0.945, 1.056] | 0.999 [0.983, 1.015] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.808 [0.721, 0.904] | 2.357 [2.216, 2.508] | 0.457 [0.449, 0.465] |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 0.838 [0.749, 0.938] | 2.411 [2.243, 2.592] | 0.465 [0.458, 0.473] |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 1.024 [0.955, 1.098] | 1.051 [0.999, 1.105] | 0.999 [0.984, 1.014] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.739 [0.706, 0.774] | 2.406 [2.325, 2.489] | 0.584 [0.575, 0.593] |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 0.797 [0.722, 0.881] | 2.570 [2.374, 2.781] | 0.578 [0.564, 0.592] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 0.973 [0.894, 1.060] | 0.990 [0.956, 1.025] | 1.011 [0.989, 1.033] |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync | 0.617 [0.578, 0.659] | 1.070 [1.043, 1.098] | 0.745 [0.728, 0.762] |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 0.619 [0.588, 0.651] | 1.082 [1.045, 1.122] | 0.749 [0.732, 0.766] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 0.986 [0.942, 1.033] | 1.016 [0.983, 1.049] | 1.010 [1.001, 1.020] |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync | 0.735 [0.706, 0.764] | 1.111 [1.083, 1.139] | 0.732 [0.715, 0.749] |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 0.727 [0.706, 0.750] | 1.106 [1.084, 1.128] | 0.736 [0.724, 0.747] |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 1.052 [0.993, 1.114] | 0.999 [0.974, 1.025] | 1.002 [0.981, 1.024] |
| `tiny-one.noop.freya-neo.sender.warm` | rsync | 0.668 [0.645, 0.691] | 1.093 [1.067, 1.119] | 0.752 [0.736, 0.769] |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 0.677 [0.650, 0.705] | 1.087 [1.055, 1.120] | 0.735 [0.713, 0.759] |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 0.968 [0.926, 1.013] | 1.016 [0.991, 1.041] | 1.005 [0.992, 1.017] |
| `tiny-one.noop.neo-freya.sender.warm` | rsync | 0.724 [0.701, 0.748] | 1.139 [1.093, 1.187] | 0.746 [0.735, 0.757] |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 0.724 [0.685, 0.765] | 1.122 [1.092, 1.152] | 0.739 [0.723, 0.755] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-same | xs | xs-same |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.362 | 12.314 | 12.251 | 12.307 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.270 | 12.539 | 13.088 | 13.773 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.379 | 0.376 | 0.232 | 0.230 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.278 | 0.277 | 0.185 | 0.192 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.675 | 7.020 | 6.443 | 6.530 |
| `small-flat.fresh.neo-freya.sender.warm` | 4.540 | 4.819 | 3.682 | 3.611 |
| `small-flat.noop.freya-neo.sender.warm` | 0.733 | 0.750 | 0.309 | 0.309 |
| `small-flat.noop.neo-freya.sender.warm` | 0.654 | 0.696 | 0.271 | 0.281 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.221 | 0.224 | 0.207 | 0.204 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.178 | 0.177 | 0.161 | 0.161 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.222 | 0.221 | 0.203 | 0.203 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.177 | 0.177 | 0.158 | 0.161 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 0.0088 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0102 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 0.0054 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 0.1737 | 273 | 365 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0279 | 9 | 12 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 0.0865 | 70 | 92 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 0.0406 | 17 | 22 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.0578 | 32 | 43 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 0.0609 | 36 | 47 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 0.0400 | 17 | 22 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.0422 | 18 | 24 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 0.0455 | 21 | 27 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 0.0139 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0434 | 19 | 25 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 0.0998 | 92 | 122 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 0.1200 | 132 | 176 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.3365 | 1018 | 1364 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 0.3487 | 1094 | 1465 |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 0.0882 | 72 | 96 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.0977 | 88 | 117 |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 0.1146 | 120 | 161 |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 0.0598 | 35 | 46 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.0528 | 28 | 36 |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 0.1185 | 128 | 171 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 0.0566 | 31 | 41 |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync | 0.0394 | 16 | 21 |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 0.0559 | 31 | 40 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 0.0428 | 19 | 25 |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync | 0.0347 | 13 | 17 |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 0.0270 | 9 | 11 |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 0.0398 | 17 | 22 |
| `tiny-one.noop.freya-neo.sender.warm` | rsync | 0.0370 | 15 | 19 |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 0.0475 | 23 | 30 |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 0.0383 | 16 | 20 |
| `tiny-one.noop.neo-freya.sender.warm` | rsync | 0.0374 | 15 | 19 |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 0.0429 | 19 | 25 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
