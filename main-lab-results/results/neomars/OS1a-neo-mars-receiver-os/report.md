# OS1a-neo-mars-receiver-os

xs's time-to-durable relative to rsync differs by more than 5% between a macOS and a Linux receiver on small and deep trees, and e51c1df1329a beats its parent only when macOS receives.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T055601Z-OS1a-neo-mars-receiver-os.
- Valid blocks: 48. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-parent | 4 | 1.004 [0.999, 1.009] | 1.005 | 0.2500 | too few blocks |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 4 | 1.009 [0.999, 1.018] | 1.010 | 0.1250 | too few blocks |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-parent | 4 | 1.005 [0.986, 1.025] | 1.005 | 0.6250 | too few blocks |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 4 | 1.011 [0.984, 1.039] | 1.011 | 0.5000 | too few blocks |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-parent | 4 | 0.590 [0.530, 0.658] | 0.576 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 4 | 0.563 [0.546, 0.580] | 0.564 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-parent | 4 | 0.725 [0.669, 0.785] | 0.725 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 4 | 0.730 [0.671, 0.795] | 0.730 | 0.1250 | too few blocks |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-parent | 4 | 0.907 [0.680, 1.212] | 0.854 | 0.3750 | too few blocks |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 4 | 0.870 [0.772, 0.980] | 0.858 | 0.1250 | too few blocks |
| `small-deep.fresh.neo-mars.sender.warm` | xs-parent | 4 | 0.918 [0.744, 1.131] | 0.918 | 0.3750 | too few blocks |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 4 | 0.898 [0.745, 1.083] | 0.898 | 0.2500 | too few blocks |
| `small-deep.noop.mars-neo.receiver.warm` | xs-parent | 4 | 0.127 [0.120, 0.135] | 0.128 | 0.1250 | too few blocks |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 4 | 0.129 [0.122, 0.136] | 0.129 | 0.1250 | too few blocks |
| `small-deep.noop.neo-mars.sender.warm` | xs-parent | 4 | 1.433 [1.364, 1.505] | 1.429 | 0.1250 | too few blocks |
| `small-deep.noop.neo-mars.sender.warm` | xs | 4 | 0.982 [0.873, 1.105] | 0.985 | 0.8750 | too few blocks |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-parent | 4 | 1.036 [0.958, 1.119] | 1.036 | 0.3750 | too few blocks |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 4 | 1.021 [0.932, 1.119] | 1.017 | 0.6250 | too few blocks |
| `small-flat.fresh.neo-mars.sender.warm` | xs-parent | 4 | 0.725 [0.705, 0.746] | 0.727 | 0.1250 | too few blocks |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 4 | 0.720 [0.687, 0.755] | 0.721 | 0.1250 | too few blocks |
| `small-flat.noop.mars-neo.receiver.warm` | xs-parent | 4 | 0.313 [0.288, 0.341] | 0.312 | 0.1250 | too few blocks |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 4 | 0.320 [0.289, 0.355] | 0.316 | 0.1250 | too few blocks |
| `small-flat.noop.neo-mars.sender.warm` | xs-parent | 4 | 0.350 [0.301, 0.408] | 0.351 | 0.1250 | too few blocks |
| `small-flat.noop.neo-mars.sender.warm` | xs | 4 | 0.351 [0.283, 0.435] | 0.365 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-parent | 1.389 [1.343, 1.437] | 23.680 [21.933, 25.567] | 0.999 [0.994, 1.004] |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 1.356 [1.306, 1.407] | 23.344 [21.564, 25.270] | 0.998 [0.991, 1.006] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-parent | 1.474 [1.309, 1.659] | 7.427 [6.835, 8.071] | 1.005 [0.985, 1.026] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 1.500 [1.294, 1.739] | 7.458 [6.990, 7.956] | 1.010 [0.983, 1.038] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-parent | 1.723 [1.659, 1.790] | 2.153 [2.109, 2.199] | 0.588 [0.528, 0.655] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 1.708 [1.615, 1.807] | 2.140 [2.115, 2.165] | 0.560 [0.541, 0.580] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-parent | 1.303 [1.199, 1.417] | 1.000 [1.000, 1.000] | 0.690 [0.629, 0.757] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 1.281 [1.172, 1.400] | 0.999 [0.998, 1.001] | 0.679 [0.612, 0.753] |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-parent | 1.748 [1.592, 1.920] | 1.035 [1.006, 1.066] | 0.902 [0.673, 1.208] |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 1.698 [1.557, 1.851] | 0.989 [0.885, 1.105] | 0.864 [0.768, 0.972] |
| `small-deep.fresh.neo-mars.sender.warm` | xs-parent | 1.180 [0.906, 1.538] | 4.845 [4.211, 5.574] | 0.917 [0.741, 1.136] |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 1.028 [0.831, 1.272] | 5.262 [4.878, 5.677] | 0.900 [0.743, 1.090] |
| `small-deep.noop.mars-neo.receiver.warm` | xs-parent | 1.936 [1.864, 2.012] | 0.684 [0.607, 0.772] | 0.127 [0.119, 0.134] |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 1.899 [1.813, 1.989] | 0.739 [0.714, 0.764] | 0.128 [0.121, 0.136] |
| `small-deep.noop.neo-mars.sender.warm` | xs-parent | 5.147 [4.967, 5.333] | 5.148 [4.118, 6.435] | 1.440 [1.369, 1.516] |
| `small-deep.noop.neo-mars.sender.warm` | xs | 3.594 [3.324, 3.885] | 4.693 [4.075, 5.404] | 0.978 [0.861, 1.112] |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-parent | 2.984 [2.793, 3.189] | 13.306 [10.507, 16.852] | 1.037 [0.963, 1.117] |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 3.053 [2.992, 3.115] | 13.625 [11.111, 16.708] | 1.027 [0.938, 1.125] |
| `small-flat.fresh.neo-mars.sender.warm` | xs-parent | 0.909 [0.876, 0.943] | 9.708 [9.283, 10.153] | 0.722 [0.701, 0.742] |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.905 [0.859, 0.953] | 9.782 [9.207, 10.393] | 0.716 [0.684, 0.749] |
| `small-flat.noop.mars-neo.receiver.warm` | xs-parent | 1.506 [1.457, 1.557] | 3.181 [3.058, 3.309] | 0.311 [0.286, 0.338] |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 1.523 [1.453, 1.597] | 3.151 [3.060, 3.244] | 0.318 [0.286, 0.353] |
| `small-flat.noop.neo-mars.sender.warm` | xs-parent | 1.052 [0.879, 1.258] | 1.278 [0.982, 1.662] | 0.312 [0.275, 0.354] |
| `small-flat.noop.neo-mars.sender.warm` | xs | 1.005 [0.819, 1.233] | 1.327 [0.982, 1.792] | 0.296 [0.250, 0.351] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-parent |
|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | 12.633 | 12.741 | 12.686 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | 12.385 | 12.517 | 12.445 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | 0.312 | 0.176 | 0.184 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | 0.314 | 0.229 | 0.228 |
| `small-deep.fresh.mars-neo.receiver.warm` | 16.521 | 14.369 | 14.991 |
| `small-deep.fresh.neo-mars.sender.warm` | 28.741 | 25.807 | 26.370 |
| `small-deep.noop.mars-neo.receiver.warm` | 16.725 | 2.150 | 2.122 |
| `small-deep.noop.neo-mars.sender.warm` | 3.533 | 3.469 | 5.062 |
| `small-flat.fresh.mars-neo.receiver.warm` | 5.485 | 5.601 | 5.681 |
| `small-flat.fresh.neo-mars.sender.warm` | 17.520 | 12.620 | 12.704 |
| `small-flat.noop.mars-neo.receiver.warm` | 0.750 | 0.240 | 0.235 |
| `small-flat.noop.neo-mars.sender.warm` | 1.073 | 0.376 | 0.376 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-parent | 0.0032 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs | 0.0057 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-parent | 0.0122 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs | 0.0171 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-parent | 0.0681 | 44 | 58 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs | 0.0190 | 8 | 8 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-parent | 0.0503 | 25 | 33 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs | 0.0536 | 28 | 37 |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-parent | 0.1817 | 299 | 399 |
| `small-deep.fresh.mars-neo.receiver.warm` | xs | 0.0750 | 53 | 70 |
| `small-deep.fresh.neo-mars.sender.warm` | xs-parent | 0.1315 | 158 | 210 |
| `small-deep.fresh.neo-mars.sender.warm` | xs | 0.1177 | 127 | 169 |
| `small-deep.noop.mars-neo.receiver.warm` | xs-parent | 0.0373 | 15 | 19 |
| `small-deep.noop.mars-neo.receiver.warm` | xs | 0.0352 | 14 | 17 |
| `small-deep.noop.neo-mars.sender.warm` | xs-parent | 0.0309 | 11 | 14 |
| `small-deep.noop.neo-mars.sender.warm` | xs | 0.0741 | 52 | 68 |
| `small-flat.fresh.mars-neo.receiver.warm` | xs-parent | 0.0489 | 24 | 31 |
| `small-flat.fresh.mars-neo.receiver.warm` | xs | 0.0573 | 32 | 42 |
| `small-flat.fresh.neo-mars.sender.warm` | xs-parent | 0.0179 | 8 | 8 |
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.0295 | 10 | 13 |
| `small-flat.noop.mars-neo.receiver.warm` | xs-parent | 0.0528 | 28 | 36 |
| `small-flat.noop.mars-neo.receiver.warm` | xs | 0.0644 | 40 | 52 |
| `small-flat.noop.neo-mars.sender.warm` | xs-parent | 0.0961 | 85 | 114 |
| `small-flat.noop.neo-mars.sender.warm` | xs | 0.1351 | 166 | 222 |
