# T1c-side-jobs

The sender's and the receiver's worker counts matter separately: fewer sending workers help only byte-bound copies from neo, and fewer receiving workers help no-ops on freya.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T201556Z-T1c-side-jobs.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 10 | 0.998 [0.989, 1.008] | 1.001 [0.986, 1.005] | 0.8672 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send2 | 10 | 0.999 [0.987, 1.011] | 1.001 [0.983, 1.009] | 0.8965 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 10 | 0.998 [0.992, 1.004] | 1.000 [0.989, 1.002] | 0.7969 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.000 [0.991, 1.008] | 1.002 [0.987, 1.006] | 0.9863 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 10 | 0.998 [0.989, 1.008] | 1.000 [0.986, 1.005] | 0.8867 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 10 | 0.953 [0.940, 0.967] | 0.955 [0.939, 0.969] | 0.0020 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 10 | 0.956 [0.943, 0.969] | 0.956 [0.943, 0.971] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 10 | 1.006 [0.987, 1.025] | 1.001 [0.989, 1.031] | 0.6523 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 10 | 1.002 [0.988, 1.015] | 0.999 [0.990, 1.014] | 0.8262 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.993 [0.978, 1.007] | 0.992 [0.976, 1.008] | 0.2637 | equivalent |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 10 | 1.055 [1.023, 1.087] | 1.051 [1.021, 1.089] | 0.0020 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send2 | 10 | 0.978 [0.947, 1.011] | 0.977 [0.933, 1.016] | 0.1621 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv2 | 10 | 1.056 [1.005, 1.109] | 1.041 [1.018, 1.136] | 0.0039 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv4 | 10 | 0.996 [0.972, 1.020] | 0.997 [0.971, 1.021] | 0.6895 | equivalent |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv8 | 10 | 1.061 [0.990, 1.138] | 1.038 [0.992, 1.135] | 0.1016 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 10 | 1.109 [1.052, 1.168] | 1.130 [1.032, 1.154] | 0.0059 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 10 | 1.037 [0.947, 1.136] | 1.052 [0.926, 1.113] | 0.3984 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv2 | 10 | 0.972 [0.899, 1.050] | 0.990 [0.883, 1.036] | 0.5586 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 10 | 0.976 [0.882, 1.081] | 0.982 [0.858, 1.098] | 0.5254 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 10 | 0.959 [0.880, 1.044] | 0.980 [0.854, 1.021] | 0.3164 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 10 | 0.993 [0.982, 1.003] | 0.990 [0.983, 1.002] | 0.1328 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | send2 | 10 | 0.998 [0.981, 1.015] | 0.997 [0.981, 1.016] | 0.7969 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 10 | 0.976 [0.965, 0.987] | 0.976 [0.968, 0.987] | 0.0039 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.010 [1.000, 1.021] | 1.011 [1.000, 1.020] | 0.0488 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.034 [1.014, 1.054] | 1.031 [1.015, 1.053] | 0.0020 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 10 | 1.358 [1.053, 1.750] | 1.334 [0.978, 1.793] | 0.0332 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 10 | 1.059 [0.980, 1.145] | 1.049 [0.983, 1.152] | 0.1172 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 10 | 0.961 [0.933, 0.990] | 0.964 [0.934, 0.990] | 0.0117 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 10 | 0.951 [0.923, 0.980] | 0.958 [0.923, 0.980] | 0.0020 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.978 [0.952, 1.005] | 0.971 [0.954, 1.005] | 0.0957 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 10 | 1.156 [1.059, 1.261] | 1.158 [1.064, 1.259] | 0.0117 | slower |
| `small-flat.noop.freya-neo.sender.warm` | send2 | 10 | 1.003 [0.950, 1.059] | 1.001 [0.950, 1.051] | 0.9199 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | recv2 | 10 | 1.076 [1.015, 1.140] | 1.101 [1.002, 1.134] | 0.0293 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | recv4 | 10 | 1.001 [0.930, 1.077] | 1.018 [0.921, 1.061] | 0.9902 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | recv8 | 10 | 1.100 [1.008, 1.201] | 1.085 [1.018, 1.205] | 0.0273 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 10 | 1.388 [1.262, 1.528] | 1.400 [1.264, 1.528] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 10 | 1.094 [0.989, 1.211] | 1.093 [0.992, 1.218] | 0.0801 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | recv2 | 10 | 1.030 [0.895, 1.186] | 1.032 [0.880, 1.178] | 0.6152 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 10 | 1.035 [0.947, 1.131] | 1.042 [0.949, 1.134] | 0.4102 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 10 | 0.951 [0.868, 1.043] | 0.966 [0.857, 1.039] | 0.2715 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 10 | 1.054 [0.982, 1.131] | 1.051 [0.985, 1.131] | 0.1211 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | send2 | 10 | 1.035 [0.953, 1.125] | 1.024 [0.951, 1.134] | 0.4004 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 10 | 1.018 [0.939, 1.104] | 1.033 [0.938, 1.111] | 0.6230 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.021 [0.936, 1.114] | 1.005 [0.941, 1.117] | 0.6719 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.021 [0.945, 1.103] | 1.018 [0.934, 1.103] | 0.5566 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 10 | 1.272 [1.131, 1.429] | 1.290 [1.153, 1.423] | 0.0039 | slower |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 10 | 0.980 [0.840, 1.143] | 0.992 [0.803, 1.150] | 0.5488 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 10 | 1.029 [0.841, 1.259] | 0.991 [0.840, 1.293] | 0.8750 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 10 | 0.947 [0.831, 1.080] | 0.975 [0.786, 1.043] | 0.4004 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.940 [0.842, 1.050] | 0.987 [0.798, 1.016] | 0.2676 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | send1 | 10 | 1.095 [0.996, 1.204] | 1.097 [0.995, 1.202] | 0.0586 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | send2 | 10 | 1.047 [0.949, 1.155] | 1.049 [0.945, 1.165] | 0.3145 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | recv2 | 10 | 1.125 [1.030, 1.229] | 1.143 [1.012, 1.216] | 0.0156 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | recv4 | 10 | 1.023 [0.904, 1.157] | 1.004 [0.916, 1.150] | 0.7148 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | recv8 | 10 | 1.003 [0.945, 1.065] | 0.999 [0.935, 1.068] | 0.9629 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | send1 | 10 | 1.161 [0.943, 1.430] | 1.141 [0.908, 1.427] | 0.1367 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | send2 | 10 | 0.958 [0.778, 1.179] | 0.944 [0.762, 1.171] | 0.6445 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | recv2 | 10 | 0.680 [0.577, 0.801] | 0.676 [0.568, 0.815] | 0.0020 | faster |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 10 | 0.689 [0.594, 0.798] | 0.697 [0.600, 0.799] | 0.0020 | faster |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 10 | 0.741 [0.640, 0.857] | 0.737 [0.633, 0.858] | 0.0020 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.862 [0.828, 0.896] | 0.997 [0.987, 1.008] | 0.777 [0.765, 0.790] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send2 | 0.867 [0.832, 0.904] | 0.999 [0.993, 1.005] | 0.784 [0.773, 0.796] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 0.997 [0.958, 1.038] | 1.002 [0.997, 1.008] | 1.009 [0.997, 1.021] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 1.010 [0.974, 1.048] | 0.995 [0.983, 1.007] | 1.004 [0.993, 1.016] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 0.992 [0.963, 1.022] | 0.996 [0.985, 1.007] | 1.013 [0.999, 1.026] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.708 [0.680, 0.738] | 0.952 [0.937, 0.967] | 0.945 [0.940, 0.950] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.850 [0.818, 0.883] | 0.954 [0.940, 0.969] | 0.955 [0.950, 0.959] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 1.012 [0.952, 1.076] | 1.004 [0.988, 1.021] | 1.002 [0.996, 1.008] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 1.017 [0.988, 1.047] | 1.000 [0.988, 1.012] | 1.003 [0.997, 1.009] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.978 [0.944, 1.014] | 0.991 [0.977, 1.005] | 1.004 [0.997, 1.010] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 0.483 [0.445, 0.524] | 1.053 [1.022, 1.085] | 0.705 [0.683, 0.728] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send2 | 0.493 [0.474, 0.513] | 0.977 [0.949, 1.006] | 0.714 [0.699, 0.728] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv2 | 0.987 [0.954, 1.021] | 1.055 [1.007, 1.106] | 0.983 [0.960, 1.007] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv4 | 1.010 [0.990, 1.031] | 0.996 [0.975, 1.018] | 0.984 [0.956, 1.013] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv8 | 1.057 [1.028, 1.087] | 1.060 [0.992, 1.132] | 0.996 [0.963, 1.030] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 0.754 [0.705, 0.806] | 1.108 [1.052, 1.167] | 1.004 [0.992, 1.017] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 0.838 [0.789, 0.889] | 1.038 [0.949, 1.137] | 1.007 [0.994, 1.021] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv2 | 0.787 [0.762, 0.813] | 0.972 [0.899, 1.050] | 0.726 [0.712, 0.740] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 0.830 [0.782, 0.881] | 0.978 [0.884, 1.082] | 0.735 [0.723, 0.746] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 0.883 [0.835, 0.933] | 0.960 [0.882, 1.044] | 0.725 [0.709, 0.740] |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 0.858 [0.841, 0.876] | 0.996 [0.981, 1.011] | 0.748 [0.670, 0.835] |
| `small-flat.fresh.freya-neo.sender.warm` | send2 | 0.865 [0.847, 0.883] | 0.997 [0.983, 1.011] | 0.819 [0.809, 0.829] |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 0.989 [0.967, 1.011] | 0.981 [0.970, 0.992] | 0.989 [0.973, 1.004] |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 1.003 [0.983, 1.023] | 1.010 [0.999, 1.021] | 1.009 [0.996, 1.021] |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 1.019 [1.001, 1.037] | 1.033 [1.014, 1.052] | 1.014 [0.999, 1.030] |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 0.778 [0.742, 0.815] | 1.341 [1.042, 1.726] | 0.424 [0.283, 0.634] |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 0.919 [0.865, 0.977] | 1.059 [0.981, 1.143] | 0.575 [0.434, 0.762] |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 0.999 [0.961, 1.038] | 0.961 [0.934, 0.989] | 0.978 [0.730, 1.312] |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.999 [0.972, 1.027] | 0.954 [0.927, 0.983] | 0.958 [0.797, 1.151] |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 1.010 [0.984, 1.036] | 0.976 [0.951, 1.003] | 1.003 [0.896, 1.123] |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 0.851 [0.724, 1.000] | 1.153 [1.057, 1.257] | 0.474 [0.463, 0.485] |
| `small-flat.noop.freya-neo.sender.warm` | send2 | 0.859 [0.784, 0.940] | 1.002 [0.950, 1.057] | 0.478 [0.467, 0.489] |
| `small-flat.noop.freya-neo.sender.warm` | recv2 | 0.855 [0.791, 0.925] | 1.074 [1.015, 1.136] | 0.991 [0.975, 1.007] |
| `small-flat.noop.freya-neo.sender.warm` | recv4 | 1.023 [0.937, 1.116] | 1.002 [0.933, 1.076] | 1.005 [0.994, 1.016] |
| `small-flat.noop.freya-neo.sender.warm` | recv8 | 1.161 [1.055, 1.277] | 1.098 [1.008, 1.196] | 0.993 [0.971, 1.016] |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 0.736 [0.644, 0.840] | 1.385 [1.260, 1.522] | 0.983 [0.963, 1.003] |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 0.867 [0.769, 0.977] | 1.094 [0.991, 1.208] | 0.984 [0.965, 1.004] |
| `small-flat.noop.neo-freya.sender.warm` | recv2 | 0.962 [0.829, 1.116] | 1.029 [0.895, 1.184] | 0.587 [0.572, 0.602] |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 0.968 [0.858, 1.092] | 1.034 [0.947, 1.130] | 0.579 [0.563, 0.596] |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 0.923 [0.826, 1.031] | 0.951 [0.869, 1.042] | 0.591 [0.575, 0.607] |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 0.771 [0.739, 0.805] | 1.055 [0.985, 1.131] | 0.822 [0.809, 0.834] |
| `small-real.fresh.freya-neo.sender.warm` | send2 | 0.773 [0.739, 0.809] | 1.036 [0.956, 1.122] | 0.815 [0.790, 0.841] |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 0.961 [0.933, 0.990] | 1.022 [0.945, 1.106] | 1.015 [0.992, 1.038] |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 1.024 [0.982, 1.068] | 1.020 [0.936, 1.113] | 1.011 [0.990, 1.032] |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 1.035 [1.010, 1.061] | 1.019 [0.942, 1.102] | 1.020 [1.006, 1.034] |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 0.846 [0.806, 0.887] | 1.267 [1.129, 1.422] | 0.509 [0.420, 0.617] |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 0.920 [0.886, 0.955] | 0.978 [0.838, 1.142] | 0.878 [0.816, 0.944] |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 0.801 [0.776, 0.827] | 1.025 [0.837, 1.256] | 1.038 [1.010, 1.067] |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.833 [0.809, 0.857] | 0.946 [0.830, 1.079] | 1.005 [0.975, 1.035] |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.921 [0.891, 0.951] | 0.938 [0.840, 1.047] | 1.022 [0.985, 1.060] |
| `small-real.noop.freya-neo.sender.warm` | send1 | 0.435 [0.390, 0.485] | 1.094 [0.996, 1.202] | 0.866 [0.806, 0.929] |
| `small-real.noop.freya-neo.sender.warm` | send2 | 0.448 [0.401, 0.500] | 1.047 [0.949, 1.154] | 0.923 [0.867, 0.983] |
| `small-real.noop.freya-neo.sender.warm` | recv2 | 0.956 [0.889, 1.027] | 1.124 [1.029, 1.228] | 0.943 [0.903, 0.985] |
| `small-real.noop.freya-neo.sender.warm` | recv4 | 1.004 [0.972, 1.038] | 1.023 [0.904, 1.156] | 0.991 [0.951, 1.032] |
| `small-real.noop.freya-neo.sender.warm` | recv8 | 1.080 [0.983, 1.187] | 1.003 [0.945, 1.064] | 1.057 [1.018, 1.097] |
| `small-real.noop.neo-freya.sender.warm` | send1 | 0.447 [0.403, 0.497] | 1.161 [0.943, 1.429] | 0.987 [0.910, 1.071] |
| `small-real.noop.neo-freya.sender.warm` | send2 | 0.906 [0.828, 0.991] | 0.958 [0.778, 1.179] | 0.972 [0.883, 1.070] |
| `small-real.noop.neo-freya.sender.warm` | recv2 | 0.266 [0.250, 0.282] | 0.680 [0.578, 0.801] | 0.872 [0.776, 0.979] |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 0.326 [0.300, 0.355] | 0.689 [0.594, 0.798] | 0.940 [0.807, 1.095] |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 0.578 [0.550, 0.608] | 0.741 [0.641, 0.857] | 0.889 [0.794, 0.996] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | recv2 | recv4 | recv8 | send1 | send2 | xs |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.186 | 12.204 | 12.187 | 12.186 | 12.194 | 12.208 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.939 | 12.886 | 12.772 | 12.268 | 12.302 | 12.867 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.244 | 0.230 | 0.245 | 0.244 | 0.226 | 0.231 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.188 | 0.189 | 0.186 | 0.215 | 0.201 | 0.194 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.401 | 6.626 | 6.779 | 6.509 | 6.545 | 6.558 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.275 | 3.240 | 3.332 | 4.625 | 3.608 | 3.407 |
| `small-flat.noop.freya-neo.sender.warm` | 0.347 | 0.323 | 0.355 | 0.373 | 0.324 | 0.323 |
| `small-flat.noop.neo-freya.sender.warm` | 0.292 | 0.293 | 0.269 | 0.393 | 0.310 | 0.283 |
| `small-real.fresh.freya-neo.sender.warm` | 17.384 | 17.434 | 17.432 | 17.995 | 17.681 | 17.076 |
| `small-real.fresh.neo-freya.sender.warm` | 12.182 | 11.216 | 11.131 | 15.052 | 11.601 | 11.838 |
| `small-real.noop.freya-neo.sender.warm` | 1.646 | 1.497 | 1.468 | 1.602 | 1.532 | 1.463 |
| `small-real.noop.neo-freya.sender.warm` | 1.066 | 1.080 | 1.162 | 1.821 | 1.502 | 1.568 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.0130 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send2 | 0.0169 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 0.0084 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 0.0119 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 0.0134 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.0192 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.0193 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 0.0267 | 9 | 11 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 0.0190 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.0202 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 0.0422 | 18 | 24 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send2 | 0.0462 | 22 | 28 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv2 | 0.0688 | 45 | 59 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv4 | 0.0332 | 12 | 16 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | recv8 | 0.0974 | 88 | 117 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 0.0727 | 50 | 66 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send2 | 0.1271 | 148 | 197 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv2 | 0.1087 | 108 | 145 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 0.1415 | 182 | 243 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 0.1195 | 131 | 174 |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 0.0144 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | send2 | 0.0241 | 8 | 10 |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 0.0156 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 0.0141 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 0.0271 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 0.3551 | 1134 | 1519 |
| `small-flat.fresh.neo-freya.sender.warm` | send2 | 0.1087 | 108 | 145 |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 0.0414 | 18 | 23 |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.0417 | 18 | 23 |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 0.0380 | 15 | 20 |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 0.1222 | 137 | 182 |
| `small-flat.noop.freya-neo.sender.warm` | send2 | 0.0757 | 54 | 71 |
| `small-flat.noop.freya-neo.sender.warm` | recv2 | 0.0810 | 61 | 81 |
| `small-flat.noop.freya-neo.sender.warm` | recv4 | 0.1023 | 96 | 128 |
| `small-flat.noop.freya-neo.sender.warm` | recv8 | 0.1220 | 136 | 182 |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 0.1335 | 163 | 217 |
| `small-flat.noop.neo-freya.sender.warm` | send2 | 0.1414 | 182 | 243 |
| `small-flat.noop.neo-freya.sender.warm` | recv2 | 0.1969 | 350 | 469 |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 0.1244 | 141 | 189 |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 0.1283 | 150 | 200 |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 0.0988 | 90 | 120 |
| `small-real.fresh.freya-neo.sender.warm` | send2 | 0.1164 | 124 | 165 |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 0.1128 | 117 | 155 |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 0.1221 | 136 | 182 |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 0.1086 | 108 | 144 |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 0.1636 | 243 | 324 |
| `small-real.fresh.neo-freya.sender.warm` | send2 | 0.2153 | 418 | 560 |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 0.2822 | 717 | 961 |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.1834 | 304 | 407 |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.1546 | 217 | 290 |
| `small-real.noop.freya-neo.sender.warm` | send1 | 0.1323 | 160 | 213 |
| `small-real.noop.freya-neo.sender.warm` | send2 | 0.1375 | 172 | 230 |
| `small-real.noop.freya-neo.sender.warm` | recv2 | 0.1237 | 140 | 187 |
| `small-real.noop.freya-neo.sender.warm` | recv4 | 0.1725 | 270 | 360 |
| `small-real.noop.freya-neo.sender.warm` | recv8 | 0.0834 | 65 | 86 |
| `small-real.noop.neo-freya.sender.warm` | send1 | 0.2914 | 764 | 1023 |
| `small-real.noop.neo-freya.sender.warm` | send2 | 0.2908 | 761 | 1019 |
| `small-real.noop.neo-freya.sender.warm` | recv2 | 0.2287 | 472 | 632 |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 0.2064 | 385 | 515 |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 0.2034 | 374 | 500 |
