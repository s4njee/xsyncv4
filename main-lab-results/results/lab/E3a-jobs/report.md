# E3a-jobs

The best worker count differs by workload: fewer than the default for byte-bound copies from neo, no fewer for small files and no-ops.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T210903Z-E3a-jobs.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j1 | 10 | 0.992 [0.971, 1.014] | 1.000 [0.961, 1.006] | 0.7402 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j2 | 10 | 0.989 [0.968, 1.011] | 0.998 [0.953, 1.001] | 0.1387 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j4 | 10 | 0.992 [0.969, 1.015] | 1.001 [0.953, 1.005] | 0.8086 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j8 | 10 | 0.993 [0.969, 1.017] | 1.001 [0.953, 1.007] | 0.9316 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 10 | 0.966 [0.955, 0.977] | 0.967 [0.957, 0.977] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 10 | 0.973 [0.960, 0.986] | 0.973 [0.960, 0.986] | 0.0039 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j4 | 10 | 1.003 [0.991, 1.014] | 1.003 [0.990, 1.015] | 0.6172 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j8 | 10 | 1.027 [1.014, 1.040] | 1.028 [1.012, 1.038] | 0.0039 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j1 | 10 | 1.147 [1.100, 1.196] | 1.147 [1.096, 1.194] | 0.0020 | slower |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j2 | 10 | 1.007 [0.946, 1.071] | 1.002 [0.952, 1.069] | 0.7988 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j4 | 10 | 0.972 [0.931, 1.015] | 0.969 [0.931, 1.024] | 0.1621 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j8 | 10 | 0.976 [0.950, 1.003] | 0.989 [0.948, 0.997] | 0.0215 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j1 | 10 | 1.169 [1.115, 1.225] | 1.180 [1.112, 1.228] | 0.0020 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j2 | 10 | 1.038 [1.005, 1.073] | 1.040 [1.003, 1.078] | 0.0215 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j4 | 10 | 1.004 [0.972, 1.038] | 0.996 [0.977, 1.040] | 0.8320 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j8 | 10 | 1.007 [0.987, 1.028] | 1.009 [0.988, 1.026] | 0.4492 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j1 | 10 | 0.991 [0.975, 1.008] | 0.987 [0.977, 1.011] | 0.2715 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j2 | 10 | 0.948 [0.938, 0.958] | 0.947 [0.937, 0.959] | 0.0020 | faster |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j4 | 10 | 0.983 [0.974, 0.992] | 0.983 [0.972, 0.992] | 0.0039 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j8 | 10 | 1.011 [1.002, 1.021] | 1.011 [1.002, 1.022] | 0.0234 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j1 | 10 | 1.930 [1.603, 2.325] | 2.020 [1.622, 2.336] | 0.0020 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j2 | 10 | 1.123 [1.027, 1.227] | 1.111 [1.024, 1.234] | 0.0156 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j4 | 10 | 0.962 [0.937, 0.987] | 0.961 [0.935, 0.991] | 0.0117 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j8 | 10 | 1.010 [0.982, 1.038] | 1.009 [0.981, 1.039] | 0.4648 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | xs-j1 | 10 | 1.300 [1.222, 1.383] | 1.304 [1.221, 1.385] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | xs-j2 | 10 | 1.028 [0.959, 1.101] | 1.030 [0.961, 1.093] | 0.3789 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | xs-j4 | 10 | 0.948 [0.887, 1.012] | 0.950 [0.887, 1.018] | 0.1035 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | xs-j8 | 10 | 0.990 [0.912, 1.074] | 0.995 [0.914, 1.086] | 0.7617 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | xs-j1 | 10 | 1.585 [1.416, 1.774] | 1.585 [1.439, 1.782] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | xs-j2 | 10 | 1.182 [1.036, 1.348] | 1.166 [1.030, 1.338] | 0.0176 | slower |
| `small-flat.noop.neo-freya.sender.warm` | xs-j4 | 10 | 1.012 [0.914, 1.120] | 0.988 [0.920, 1.142] | 0.8125 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | xs-j8 | 10 | 1.026 [0.960, 1.096] | 1.024 [0.960, 1.088] | 0.4473 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-j1 | 10 | 1.117 [1.058, 1.181] | 1.114 [1.056, 1.187] | 0.0039 | slower |
| `small-real.fresh.freya-neo.sender.warm` | xs-j2 | 10 | 0.974 [0.906, 1.047] | 0.957 [0.908, 1.055] | 0.4160 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-j4 | 10 | 1.023 [0.962, 1.088] | 1.009 [0.965, 1.097] | 0.4551 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-j8 | 10 | 1.008 [0.956, 1.063] | 1.000 [0.962, 1.065] | 0.7598 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-j1 | 10 | 1.132 [0.983, 1.303] | 1.045 [1.031, 1.379] | 0.0156 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-j2 | 10 | 1.019 [0.947, 1.095] | 0.979 [0.968, 1.130] | 0.6816 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-j4 | 10 | 1.084 [0.942, 1.248] | 1.047 [0.971, 1.286] | 0.2441 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-j8 | 10 | 1.018 [0.986, 1.052] | 1.030 [0.970, 1.042] | 0.2402 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs-j1 | 10 | 1.520 [1.368, 1.688] | 1.544 [1.377, 1.667] | 0.0020 | slower |
| `small-real.noop.freya-neo.sender.warm` | xs-j2 | 10 | 1.135 [1.037, 1.242] | 1.137 [1.038, 1.250] | 0.0176 | slower |
| `small-real.noop.freya-neo.sender.warm` | xs-j4 | 10 | 1.072 [0.848, 1.355] | 0.981 [0.936, 1.569] | 0.9238 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs-j8 | 10 | 1.128 [0.980, 1.298] | 1.083 [1.038, 1.370] | 0.0488 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | xs-j1 | 10 | 1.110 [0.861, 1.431] | 1.115 [0.833, 1.457] | 0.3652 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | xs-j2 | 10 | 0.673 [0.554, 0.816] | 0.665 [0.550, 0.795] | 0.0039 | faster |
| `small-real.noop.neo-freya.sender.warm` | xs-j4 | 10 | 0.624 [0.537, 0.724] | 0.610 [0.544, 0.726] | 0.0020 | faster |
| `small-real.noop.neo-freya.sender.warm` | xs-j8 | 10 | 0.726 [0.625, 0.843] | 0.722 [0.626, 0.836] | 0.0039 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j1 | 0.869 [0.848, 0.891] | 0.987 [0.963, 1.012] | 0.770 [0.761, 0.779] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j2 | 0.872 [0.844, 0.900] | 0.984 [0.962, 1.008] | 0.787 [0.779, 0.795] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j4 | 0.897 [0.870, 0.926] | 0.990 [0.964, 1.016] | 0.817 [0.809, 0.824] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j8 | 0.927 [0.905, 0.949] | 0.991 [0.967, 1.016] | 0.886 [0.879, 0.894] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 0.716 [0.691, 0.743] | 0.966 [0.955, 0.977] | 0.945 [0.942, 0.949] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 0.866 [0.830, 0.904] | 0.973 [0.960, 0.986] | 0.959 [0.953, 0.965] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j4 | 1.008 [0.974, 1.043] | 1.003 [0.992, 1.014] | 1.001 [0.998, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j8 | 1.050 [1.021, 1.080] | 1.027 [1.014, 1.040] | 1.079 [1.071, 1.086] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j1 | 0.452 [0.421, 0.484] | 1.145 [1.098, 1.193] | 0.698 [0.680, 0.716] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j2 | 0.466 [0.430, 0.505] | 1.006 [0.946, 1.068] | 0.703 [0.687, 0.719] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j4 | 0.563 [0.517, 0.613] | 0.972 [0.932, 1.013] | 0.691 [0.672, 0.711] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j8 | 0.660 [0.624, 0.698] | 0.976 [0.951, 1.001] | 0.711 [0.697, 0.726] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j1 | 0.644 [0.598, 0.694] | 1.167 [1.113, 1.223] | 0.716 [0.701, 0.731] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j2 | 0.722 [0.660, 0.789] | 1.038 [1.004, 1.072] | 0.738 [0.722, 0.755] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j4 | 0.817 [0.747, 0.893] | 1.004 [0.972, 1.037] | 0.722 [0.703, 0.741] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j8 | 0.954 [0.913, 0.998] | 1.007 [0.987, 1.027] | 0.717 [0.694, 0.740] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j1 | 0.705 [0.684, 0.725] | 0.989 [0.972, 1.007] | 0.792 [0.777, 0.809] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j2 | 0.818 [0.801, 0.835] | 0.951 [0.943, 0.959] | 0.815 [0.802, 0.829] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j4 | 0.860 [0.840, 0.880] | 0.982 [0.974, 0.991] | 0.847 [0.834, 0.859] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j8 | 0.909 [0.888, 0.931] | 1.005 [1.001, 1.010] | 0.889 [0.879, 0.899] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j1 | 0.731 [0.700, 0.763] | 1.906 [1.585, 2.291] | 0.177 [0.141, 0.222] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j2 | 0.859 [0.821, 0.899] | 1.125 [1.030, 1.230] | 0.292 [0.206, 0.412] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j4 | 1.006 [0.972, 1.041] | 0.966 [0.941, 0.993] | 0.786 [0.539, 1.145] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j8 | 1.063 [1.040, 1.086] | 1.012 [0.983, 1.042] | 1.597 [1.276, 1.999] |
| `small-flat.noop.freya-neo.sender.warm` | xs-j1 | 0.619 [0.577, 0.665] | 1.297 [1.219, 1.379] | 0.465 [0.454, 0.475] |
| `small-flat.noop.freya-neo.sender.warm` | xs-j2 | 0.695 [0.658, 0.735] | 1.027 [0.960, 1.099] | 0.471 [0.463, 0.480] |
| `small-flat.noop.freya-neo.sender.warm` | xs-j4 | 0.841 [0.750, 0.943] | 0.948 [0.889, 1.011] | 0.543 [0.530, 0.556] |
| `small-flat.noop.freya-neo.sender.warm` | xs-j8 | 0.907 [0.823, 1.001] | 0.991 [0.913, 1.074] | 0.708 [0.696, 0.721] |
| `small-flat.noop.neo-freya.sender.warm` | xs-j1 | 0.742 [0.655, 0.840] | 1.554 [1.399, 1.725] | 0.584 [0.574, 0.593] |
| `small-flat.noop.neo-freya.sender.warm` | xs-j2 | 0.843 [0.714, 0.995] | 1.161 [1.004, 1.344] | 0.594 [0.588, 0.600] |
| `small-flat.noop.neo-freya.sender.warm` | xs-j4 | 0.997 [0.855, 1.162] | 0.993 [0.888, 1.111] | 0.588 [0.581, 0.595] |
| `small-flat.noop.neo-freya.sender.warm` | xs-j8 | 1.009 [0.898, 1.134] | 1.007 [0.928, 1.093] | 0.606 [0.589, 0.624] |
| `small-real.fresh.freya-neo.sender.warm` | xs-j1 | 0.599 [0.578, 0.621] | 1.121 [1.063, 1.181] | 0.829 [0.817, 0.841] |
| `small-real.fresh.freya-neo.sender.warm` | xs-j2 | 0.695 [0.673, 0.717] | 0.973 [0.906, 1.045] | 0.830 [0.814, 0.848] |
| `small-real.fresh.freya-neo.sender.warm` | xs-j4 | 0.788 [0.765, 0.812] | 1.020 [0.964, 1.079] | 0.867 [0.855, 0.879] |
| `small-real.fresh.freya-neo.sender.warm` | xs-j8 | 0.860 [0.820, 0.903] | 1.008 [0.957, 1.062] | 0.924 [0.909, 0.938] |
| `small-real.fresh.neo-freya.sender.warm` | xs-j1 | 0.630 [0.610, 0.650] | 1.129 [0.981, 1.299] | 0.857 [0.811, 0.905] |
| `small-real.fresh.neo-freya.sender.warm` | xs-j2 | 0.706 [0.691, 0.722] | 1.017 [0.946, 1.094] | 0.943 [0.899, 0.989] |
| `small-real.fresh.neo-freya.sender.warm` | xs-j4 | 0.819 [0.795, 0.843] | 1.083 [0.940, 1.248] | 1.009 [0.987, 1.030] |
| `small-real.fresh.neo-freya.sender.warm` | xs-j8 | 0.984 [0.946, 1.023] | 1.018 [0.985, 1.052] | 1.060 [1.034, 1.086] |
| `small-real.noop.freya-neo.sender.warm` | xs-j1 | 0.375 [0.333, 0.424] | 1.518 [1.367, 1.686] | 0.885 [0.857, 0.914] |
| `small-real.noop.freya-neo.sender.warm` | xs-j2 | 0.412 [0.359, 0.473] | 1.134 [1.037, 1.241] | 0.924 [0.899, 0.950] |
| `small-real.noop.freya-neo.sender.warm` | xs-j4 | 0.500 [0.429, 0.582] | 1.072 [0.849, 1.354] | 0.979 [0.936, 1.024] |
| `small-real.noop.freya-neo.sender.warm` | xs-j8 | 0.723 [0.653, 0.801] | 1.128 [0.981, 1.298] | 1.043 [0.991, 1.098] |
| `small-real.noop.neo-freya.sender.warm` | xs-j1 | 0.292 [0.257, 0.333] | 1.110 [0.861, 1.431] | 0.966 [0.862, 1.084] |
| `small-real.noop.neo-freya.sender.warm` | xs-j2 | 0.269 [0.236, 0.306] | 0.673 [0.555, 0.817] | 0.879 [0.746, 1.036] |
| `small-real.noop.neo-freya.sender.warm` | xs-j4 | 0.353 [0.308, 0.404] | 0.625 [0.538, 0.725] | 0.921 [0.777, 1.091] |
| `small-real.noop.neo-freya.sender.warm` | xs-j8 | 0.652 [0.582, 0.729] | 0.726 [0.625, 0.843] | 1.025 [0.910, 1.154] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-j1 | xs-j2 | xs-j4 | xs-j8 |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.302 | 12.209 | 12.168 | 12.199 | 12.212 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.671 | 12.241 | 12.324 | 12.703 | 13.008 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.233 | 0.267 | 0.234 | 0.226 | 0.227 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.187 | 0.218 | 0.194 | 0.188 | 0.188 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.473 | 6.418 | 6.136 | 6.362 | 6.547 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.394 | 6.552 | 3.811 | 3.263 | 3.426 |
| `small-flat.noop.freya-neo.sender.warm` | 0.324 | 0.421 | 0.333 | 0.307 | 0.321 |
| `small-flat.noop.neo-freya.sender.warm` | 0.283 | 0.449 | 0.335 | 0.287 | 0.291 |
| `small-real.fresh.freya-neo.sender.warm` | 17.246 | 19.271 | 16.796 | 17.643 | 17.386 |
| `small-real.fresh.neo-freya.sender.warm` | 11.326 | 12.816 | 11.536 | 12.281 | 11.536 |
| `small-real.noop.freya-neo.sender.warm` | 1.411 | 2.144 | 1.601 | 1.513 | 1.591 |
| `small-real.noop.neo-freya.sender.warm` | 1.625 | 1.805 | 1.093 | 1.013 | 1.179 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j1 | 0.0299 | 11 | 13 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j2 | 0.0305 | 11 | 14 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j4 | 0.0322 | 12 | 15 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-j8 | 0.0335 | 13 | 16 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 0.0160 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 0.0187 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j4 | 0.0159 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j8 | 0.0176 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j1 | 0.0583 | 33 | 43 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j2 | 0.0865 | 70 | 93 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j4 | 0.0601 | 35 | 46 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-j8 | 0.0375 | 15 | 19 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j1 | 0.0655 | 41 | 54 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j2 | 0.0457 | 21 | 28 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j4 | 0.0456 | 21 | 28 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-j8 | 0.0279 | 9 | 12 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j1 | 0.0235 | 8 | 9 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j2 | 0.0144 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j4 | 0.0126 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-j8 | 0.0127 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j1 | 0.2599 | 609 | 815 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j2 | 0.1246 | 142 | 189 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j4 | 0.0367 | 15 | 19 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-j8 | 0.0385 | 16 | 20 |
| `small-flat.noop.freya-neo.sender.warm` | xs-j1 | 0.0862 | 69 | 92 |
| `small-flat.noop.freya-neo.sender.warm` | xs-j2 | 0.0964 | 86 | 114 |
| `small-flat.noop.freya-neo.sender.warm` | xs-j4 | 0.0921 | 79 | 104 |
| `small-flat.noop.freya-neo.sender.warm` | xs-j8 | 0.1143 | 120 | 160 |
| `small-flat.noop.neo-freya.sender.warm` | xs-j1 | 0.1576 | 225 | 301 |
| `small-flat.noop.neo-freya.sender.warm` | xs-j2 | 0.1841 | 307 | 410 |
| `small-flat.noop.neo-freya.sender.warm` | xs-j4 | 0.1419 | 183 | 245 |
| `small-flat.noop.neo-freya.sender.warm` | xs-j8 | 0.0926 | 79 | 106 |
| `small-real.fresh.freya-neo.sender.warm` | xs-j1 | 0.0771 | 56 | 74 |
| `small-real.fresh.freya-neo.sender.warm` | xs-j2 | 0.1009 | 94 | 125 |
| `small-real.fresh.freya-neo.sender.warm` | xs-j4 | 0.0857 | 68 | 91 |
| `small-real.fresh.freya-neo.sender.warm` | xs-j8 | 0.0741 | 52 | 69 |
| `small-real.fresh.neo-freya.sender.warm` | xs-j1 | 0.1973 | 352 | 471 |
| `small-real.fresh.neo-freya.sender.warm` | xs-j2 | 0.1017 | 95 | 127 |
| `small-real.fresh.neo-freya.sender.warm` | xs-j4 | 0.1966 | 349 | 467 |
| `small-real.fresh.neo-freya.sender.warm` | xs-j8 | 0.0457 | 21 | 28 |
| `small-real.noop.freya-neo.sender.warm` | xs-j1 | 0.1471 | 197 | 263 |
| `small-real.noop.freya-neo.sender.warm` | xs-j2 | 0.1257 | 144 | 193 |
| `small-real.noop.freya-neo.sender.warm` | xs-j4 | 0.3272 | 963 | 1290 |
| `small-real.noop.freya-neo.sender.warm` | xs-j8 | 0.1961 | 348 | 465 |
| `small-real.noop.neo-freya.sender.warm` | xs-j1 | 0.3551 | 1134 | 1519 |
| `small-real.noop.neo-freya.sender.warm` | xs-j2 | 0.2704 | 659 | 882 |
| `small-real.noop.neo-freya.sender.warm` | xs-j4 | 0.2092 | 395 | 529 |
| `small-real.noop.neo-freya.sender.warm` | xs-j8 | 0.2095 | 396 | 530 |
