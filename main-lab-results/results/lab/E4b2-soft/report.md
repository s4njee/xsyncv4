# E4b2-soft

The soft backlog limits are not critical: a quarter or four times the default changes no copy by more than 3%.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220733Z-E4b2-soft.
- Valid blocks: 50. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send16 | 4 | 0.996 [0.986, 1.006] | 0.999 | 0.1250 | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send256 | 4 | 0.999 [0.999, 1.000] | 0.999 | 0.1250 | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv4 | 4 | 1.000 [0.999, 1.001] | 1.000 | 0.7500 | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv64 | 4 | 1.000 [0.998, 1.003] | 1.001 | 0.6250 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send16 | 5 | 0.989 [0.970, 1.008] | 0.989 | 0.1875 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send256 | 5 | 0.994 [0.971, 1.017] | 0.992 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv4 | 5 | 0.988 [0.956, 1.022] | 0.988 | 0.4375 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv64 | 5 | 0.991 [0.965, 1.018] | 0.991 | 0.5000 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send16 | 4 | 1.042 [0.959, 1.131] | 1.028 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send256 | 4 | 1.050 [1.027, 1.073] | 1.050 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv4 | 4 | 1.030 [0.997, 1.064] | 1.025 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv64 | 4 | 1.048 [0.974, 1.127] | 1.026 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send16 | 4 | 1.024 [0.965, 1.085] | 1.029 | 0.3750 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send256 | 4 | 1.012 [1.004, 1.019] | 1.013 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv4 | 4 | 1.003 [0.954, 1.054] | 1.003 | 0.8750 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv64 | 4 | 1.002 [0.967, 1.039] | 1.002 | 0.7500 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send16 | 4 | 1.014 [0.995, 1.034] | 1.015 | 0.2500 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send256 | 4 | 1.004 [0.993, 1.017] | 1.004 | 0.3750 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv4 | 4 | 1.004 [0.990, 1.017] | 1.004 | 0.5000 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv64 | 4 | 1.004 [0.990, 1.019] | 1.005 | 0.3750 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send16 | 5 | 0.999 [0.945, 1.056] | 0.998 | 0.9375 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send256 | 5 | 1.011 [0.961, 1.064] | 1.008 | 0.5625 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv4 | 5 | 0.989 [0.953, 1.026] | 0.991 | 0.5000 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv64 | 5 | 1.016 [0.955, 1.081] | 1.020 | 0.5000 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | soft-send16 | 4 | 0.968 [0.888, 1.055] | 0.968 | 0.3750 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | soft-send256 | 4 | 1.009 [0.921, 1.105] | 1.015 | 0.8750 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv4 | 4 | 0.976 [0.923, 1.033] | 0.976 | 0.3750 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv64 | 4 | 0.977 [0.915, 1.044] | 0.967 | 0.3750 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | soft-send16 | 4 | 1.059 [0.842, 1.333] | 1.079 | 0.5000 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | soft-send256 | 4 | 1.030 [0.835, 1.270] | 1.055 | 0.7500 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv4 | 4 | 0.987 [0.841, 1.158] | 1.000 | 0.8750 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv64 | 4 | 1.096 [0.851, 1.412] | 1.144 | 0.3750 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | soft-send16 | 4 | 1.018 [0.965, 1.074] | 1.027 | 0.3750 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | soft-send256 | 4 | 1.016 [0.875, 1.179] | 1.016 | 0.7500 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv4 | 4 | 0.993 [0.876, 1.126] | 0.993 | 1.0000 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv64 | 4 | 0.980 [0.919, 1.045] | 0.985 | 0.3750 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | soft-send16 | 4 | 1.072 [0.935, 1.229] | 1.072 | 0.5000 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | soft-send256 | 4 | 1.033 [0.965, 1.106] | 1.033 | 0.5000 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv4 | 4 | 1.327 [0.578, 3.048] | 1.052 | 0.3750 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv64 | 4 | 1.000 [0.995, 1.004] | 1.000 | 1.0000 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | soft-send16 | 4 | 1.089 [0.997, 1.190] | 1.089 | 0.1250 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | soft-send256 | 4 | 1.034 [0.949, 1.127] | 1.015 | 0.2500 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | soft-recv4 | 4 | 0.977 [0.942, 1.013] | 0.976 | 0.2500 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | soft-recv64 | 4 | 1.054 [0.985, 1.127] | 1.054 | 0.1250 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | soft-send16 | 4 | 1.009 [0.851, 1.195] | 1.032 | 0.8750 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | soft-send256 | 4 | 0.956 [0.790, 1.158] | 0.976 | 0.7500 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | soft-recv4 | 4 | 0.969 [0.785, 1.196] | 0.969 | 0.6250 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | soft-recv64 | 4 | 1.075 [0.814, 1.418] | 1.073 | 0.6250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send16 | 0.997 [0.994, 1.000] | 0.996 [0.984, 1.008] | 0.990 [0.969, 1.012] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send256 | 1.004 [0.978, 1.031] | 0.997 [0.983, 1.010] | 1.005 [0.972, 1.038] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv4 | 1.004 [0.962, 1.049] | 1.000 [0.993, 1.007] | 0.995 [0.969, 1.021] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv64 | 1.002 [0.974, 1.031] | 1.004 [0.998, 1.011] | 0.993 [0.979, 1.007] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send16 | 0.963 [0.888, 1.045] | 0.989 [0.971, 1.008] | 0.994 [0.988, 1.000] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send256 | 0.997 [0.905, 1.098] | 0.994 [0.971, 1.017] | 1.001 [0.998, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv4 | 0.965 [0.872, 1.069] | 0.988 [0.956, 1.022] | 1.001 [0.997, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv64 | 0.981 [0.853, 1.128] | 0.992 [0.965, 1.019] | 0.999 [0.994, 1.004] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send16 | 0.999 [0.946, 1.055] | 1.042 [0.975, 1.113] | 1.019 [0.961, 1.082] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send256 | 1.008 [0.970, 1.047] | 1.048 [1.020, 1.078] | 1.008 [0.974, 1.044] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv4 | 0.999 [0.960, 1.040] | 1.029 [0.999, 1.060] | 1.013 [0.989, 1.039] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv64 | 0.996 [0.954, 1.040] | 1.046 [0.973, 1.125] | 1.008 [0.981, 1.036] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send16 | 1.029 [0.947, 1.117] | 1.023 [0.965, 1.085] | 1.013 [0.996, 1.030] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send256 | 0.967 [0.895, 1.046] | 1.013 [1.005, 1.022] | 1.013 [0.996, 1.030] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv4 | 1.008 [0.901, 1.127] | 1.003 [0.955, 1.052] | 1.008 [0.982, 1.035] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv64 | 0.992 [0.889, 1.107] | 1.002 [0.968, 1.039] | 1.014 [0.987, 1.042] |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send16 | 1.003 [0.964, 1.043] | 1.009 [0.983, 1.035] | 0.984 [0.892, 1.084] |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send256 | 0.990 [0.958, 1.022] | 1.001 [0.986, 1.016] | 1.022 [1.008, 1.036] |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv4 | 0.995 [0.974, 1.017] | 0.997 [0.982, 1.012] | 0.999 [0.971, 1.028] |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv64 | 0.991 [0.962, 1.021] | 1.001 [0.991, 1.010] | 1.019 [0.986, 1.054] |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send16 | 0.984 [0.912, 1.061] | 0.996 [0.942, 1.052] | 1.052 [0.817, 1.354] |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send256 | 1.016 [0.912, 1.132] | 1.006 [0.952, 1.064] | 1.085 [0.856, 1.376] |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv4 | 1.014 [0.922, 1.115] | 0.983 [0.947, 1.020] | 0.982 [0.675, 1.428] |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv64 | 0.988 [0.862, 1.133] | 1.008 [0.945, 1.075] | 1.062 [0.823, 1.371] |
| `small-flat.noop.freya-neo.sender.warm` | soft-send16 | 0.988 [0.968, 1.009] | 0.970 [0.894, 1.052] | 0.988 [0.970, 1.006] |
| `small-flat.noop.freya-neo.sender.warm` | soft-send256 | 0.990 [0.966, 1.015] | 1.007 [0.926, 1.097] | 0.992 [0.984, 0.999] |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv4 | 0.984 [0.971, 0.996] | 0.979 [0.925, 1.037] | 1.010 [0.976, 1.045] |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv64 | 0.985 [0.905, 1.072] | 0.977 [0.919, 1.038] | 0.994 [0.971, 1.018] |
| `small-flat.noop.neo-freya.sender.warm` | soft-send16 | 1.045 [0.750, 1.456] | 1.094 [0.948, 1.261] | 1.000 [0.972, 1.028] |
| `small-flat.noop.neo-freya.sender.warm` | soft-send256 | 1.032 [0.771, 1.381] | 1.030 [0.836, 1.269] | 0.992 [0.957, 1.028] |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv4 | 0.987 [0.800, 1.218] | 0.986 [0.841, 1.157] | 1.012 [0.983, 1.041] |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv64 | 1.146 [0.808, 1.625] | 1.095 [0.851, 1.408] | 1.012 [1.003, 1.022] |
| `small-real.fresh.freya-neo.sender.warm` | soft-send16 | 0.993 [0.977, 1.009] | 1.022 [0.976, 1.069] | 1.009 [0.978, 1.040] |
| `small-real.fresh.freya-neo.sender.warm` | soft-send256 | 1.004 [0.965, 1.044] | 1.018 [0.907, 1.142] | 1.004 [0.971, 1.038] |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv4 | 0.992 [0.944, 1.043] | 0.999 [0.896, 1.114] | 1.009 [0.969, 1.050] |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv64 | 1.001 [0.961, 1.042] | 0.980 [0.934, 1.028] | 1.005 [0.962, 1.050] |
| `small-real.fresh.neo-freya.sender.warm` | soft-send16 | 0.977 [0.962, 0.993] | 1.076 [0.928, 1.247] | 1.047 [0.944, 1.162] |
| `small-real.fresh.neo-freya.sender.warm` | soft-send256 | 0.985 [0.967, 1.004] | 1.033 [0.964, 1.106] | 1.011 [0.899, 1.138] |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv4 | 0.988 [0.953, 1.025] | 1.325 [0.577, 3.039] | 1.052 [0.978, 1.131] |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv64 | 0.972 [0.946, 1.000] | 0.998 [0.994, 1.002] | 1.060 [0.953, 1.179] |
| `small-real.noop.freya-neo.sender.warm` | soft-send16 | 0.969 [0.920, 1.020] | 1.089 [0.997, 1.189] | 1.005 [0.992, 1.017] |
| `small-real.noop.freya-neo.sender.warm` | soft-send256 | 0.997 [0.972, 1.023] | 1.034 [0.949, 1.126] | 1.006 [1.001, 1.010] |
| `small-real.noop.freya-neo.sender.warm` | soft-recv4 | 0.984 [0.970, 0.998] | 0.977 [0.943, 1.013] | 1.004 [0.998, 1.010] |
| `small-real.noop.freya-neo.sender.warm` | soft-recv64 | 0.994 [0.973, 1.016] | 1.053 [0.985, 1.126] | 1.005 [0.992, 1.019] |
| `small-real.noop.neo-freya.sender.warm` | soft-send16 | 1.014 [0.988, 1.041] | 1.009 [0.852, 1.195] | 0.961 [0.909, 1.017] |
| `small-real.noop.neo-freya.sender.warm` | soft-send256 | 0.997 [0.975, 1.019] | 0.957 [0.790, 1.158] | 0.968 [0.926, 1.011] |
| `small-real.noop.neo-freya.sender.warm` | soft-recv4 | 0.993 [0.944, 1.044] | 0.969 [0.786, 1.196] | 0.979 [0.922, 1.040] |
| `small-real.noop.neo-freya.sender.warm` | soft-recv64 | 1.008 [0.960, 1.059] | 1.074 [0.815, 1.417] | 0.944 [0.841, 1.060] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | soft-recv4 | soft-recv64 | soft-send16 | soft-send256 | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.266 | 12.274 | 12.217 | 12.261 | 12.268 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.390 | 12.424 | 12.397 | 12.464 | 12.538 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.203 | 0.207 | 0.206 | 0.207 | 0.197 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.173 | 0.173 | 0.176 | 0.174 | 0.172 |
| `small-flat.fresh.freya-neo.sender.warm` | 5.395 | 5.399 | 5.453 | 5.400 | 5.375 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.355 | 3.446 | 3.388 | 3.430 | 3.392 |
| `small-flat.noop.freya-neo.sender.warm` | 0.261 | 0.261 | 0.259 | 0.270 | 0.267 |
| `small-flat.noop.neo-freya.sender.warm` | 0.230 | 0.256 | 0.247 | 0.240 | 0.233 |
| `small-real.fresh.freya-neo.sender.warm` | 12.908 | 12.731 | 13.234 | 13.202 | 12.995 |
| `small-real.fresh.neo-freya.sender.warm` | 14.520 | 10.937 | 11.729 | 11.307 | 10.942 |
| `small-real.noop.freya-neo.sender.warm` | 1.123 | 1.212 | 1.253 | 1.189 | 1.150 |
| `small-real.noop.neo-freya.sender.warm` | 1.407 | 1.559 | 1.464 | 1.388 | 1.451 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send16 | 0.0062 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-send256 | 0.0003 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv4 | 0.0007 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | soft-recv64 | 0.0015 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send16 | 0.0154 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-send256 | 0.0187 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv4 | 0.0270 | 9 | 11 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | soft-recv64 | 0.0215 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send16 | 0.0518 | 27 | 35 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-send256 | 0.0137 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv4 | 0.0202 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | soft-recv64 | 0.0460 | 21 | 28 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send16 | 0.0368 | 15 | 19 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-send256 | 0.0046 | 8 | 8 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv4 | 0.0312 | 11 | 14 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | soft-recv64 | 0.0226 | 8 | 9 |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send16 | 0.0122 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | soft-send256 | 0.0075 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv4 | 0.0083 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | soft-recv64 | 0.0090 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send16 | 0.0448 | 21 | 27 |
| `small-flat.fresh.neo-freya.sender.warm` | soft-send256 | 0.0409 | 17 | 23 |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv4 | 0.0297 | 10 | 13 |
| `small-flat.fresh.neo-freya.sender.warm` | soft-recv64 | 0.0500 | 25 | 33 |
| `small-flat.noop.freya-neo.sender.warm` | soft-send16 | 0.0541 | 29 | 38 |
| `small-flat.noop.freya-neo.sender.warm` | soft-send256 | 0.0573 | 32 | 42 |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv4 | 0.0357 | 14 | 18 |
| `small-flat.noop.freya-neo.sender.warm` | soft-recv64 | 0.0417 | 18 | 23 |
| `small-flat.noop.neo-freya.sender.warm` | soft-send16 | 0.1443 | 189 | 253 |
| `small-flat.noop.neo-freya.sender.warm` | soft-send256 | 0.1318 | 158 | 212 |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv4 | 0.1008 | 94 | 125 |
| `small-flat.noop.neo-freya.sender.warm` | soft-recv64 | 0.1588 | 229 | 306 |
| `small-real.fresh.freya-neo.sender.warm` | soft-send16 | 0.0336 | 13 | 16 |
| `small-real.fresh.freya-neo.sender.warm` | soft-send256 | 0.0937 | 81 | 108 |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv4 | 0.0789 | 58 | 77 |
| `small-real.fresh.freya-neo.sender.warm` | soft-recv64 | 0.0404 | 17 | 22 |
| `small-real.fresh.neo-freya.sender.warm` | soft-send16 | 0.0862 | 69 | 92 |
| `small-real.fresh.neo-freya.sender.warm` | soft-send256 | 0.0429 | 19 | 25 |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv4 | 0.5226 | 2453 | 3287 |
| `small-real.fresh.neo-freya.sender.warm` | soft-recv64 | 0.0027 | 8 | 8 |
| `small-real.noop.freya-neo.sender.warm` | soft-send16 | 0.0557 | 30 | 40 |
| `small-real.noop.freya-neo.sender.warm` | soft-send256 | 0.0541 | 29 | 38 |
| `small-real.noop.freya-neo.sender.warm` | soft-recv4 | 0.0226 | 8 | 9 |
| `small-real.noop.freya-neo.sender.warm` | soft-recv64 | 0.0421 | 18 | 24 |
| `small-real.noop.neo-freya.sender.warm` | soft-send16 | 0.1066 | 105 | 139 |
| `small-real.noop.neo-freya.sender.warm` | soft-send256 | 0.1201 | 132 | 176 |
| `small-real.noop.neo-freya.sender.warm` | soft-recv4 | 0.1322 | 159 | 213 |
| `small-real.noop.neo-freya.sender.warm` | soft-recv64 | 0.1743 | 275 | 368 |
