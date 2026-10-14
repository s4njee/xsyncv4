# S0-sentinel

Hour by hour, the A/A ratio stays within 3% of 1 and the xs to rsync ratio stays where the baseline put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020701Z-S0-sentinel-s0001, 20261014T020707Z-S0-sentinel-s0002.
- Valid blocks: 48. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 6 | 0.995 [0.989, 1.001] | 0.994 [0.987, 1.000] | 0.1250 | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 6 | 1.005 [0.997, 1.012] | 1.004 [0.995, 1.013] | 0.1875 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 6 | 0.995 [0.969, 1.022] | 0.997 [0.950, 1.027] | 0.7500 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 6 | 0.958 [0.938, 0.978] | 0.964 [0.921, 0.977] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 6 | 1.032 [0.954, 1.116] | 1.023 [0.935, 1.132] | 0.3438 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 6 | 1.605 [1.533, 1.681] | 1.597 [1.534, 1.716] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 6 | 1.019 [0.968, 1.073] | 1.028 [0.935, 1.062] | 0.4375 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 6 | 1.525 [1.473, 1.579] | 1.521 [1.465, 1.614] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | again | 6 | 1.003 [0.990, 1.017] | 1.001 [0.993, 1.027] | 0.6875 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 6 | 1.058 [0.981, 1.142] | 1.060 [0.976, 1.197] | 0.1250 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | again | 6 | 0.978 [0.945, 1.012] | 0.975 [0.941, 1.026] | 0.1562 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 6 | 1.264 [0.929, 1.720] | 1.231 [1.013, 2.139] | 0.0312 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | again | 6 | 0.992 [0.914, 1.076] | 1.007 [0.893, 1.104] | 0.9375 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 6 | 2.379 [2.225, 2.544] | 2.373 [2.192, 2.631] | 0.0312 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | again | 6 | 0.991 [0.909, 1.081] | 0.999 [0.858, 1.065] | 0.8438 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 6 | 2.454 [2.112, 2.851] | 2.461 [2.128, 2.993] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 0.992 [0.975, 1.009] | 1.000 [0.992, 1.008] | 1.001 [0.988, 1.014] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.507 [0.493, 0.522] | 1.003 [0.985, 1.021] | 0.099 [0.095, 0.102] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 0.971 [0.886, 1.065] | 0.994 [0.968, 1.021] | 1.007 [0.991, 1.024] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.467 [0.440, 0.496] | 0.957 [0.937, 0.978] | 0.122 [0.119, 0.126] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 0.991 [0.919, 1.068] | 1.031 [0.957, 1.110] | 1.013 [0.986, 1.042] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.548 [0.521, 0.577] | 1.584 [1.516, 1.656] | 0.694 [0.651, 0.739] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 1.031 [0.908, 1.171] | 1.019 [0.968, 1.073] | 0.998 [0.987, 1.008] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.574 [0.521, 0.634] | 1.521 [1.469, 1.575] | 0.720 [0.693, 0.749] |
| `small-flat.fresh.freya-neo.sender.warm` | again | 1.010 [0.997, 1.023] | 1.011 [0.995, 1.027] | 1.002 [0.974, 1.030] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.687 [0.648, 0.727] | 1.059 [0.991, 1.131] | 0.100 [0.098, 0.101] |
| `small-flat.fresh.neo-freya.sender.warm` | again | 0.976 [0.932, 1.022] | 0.982 [0.949, 1.016] | 1.119 [0.867, 1.446] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.667 [0.640, 0.697] | 1.250 [0.924, 1.690] | 0.142 [0.102, 0.197] |
| `small-flat.noop.freya-neo.sender.warm` | again | 0.999 [0.920, 1.086] | 0.993 [0.919, 1.073] | 1.000 [0.980, 1.021] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.811 [0.753, 0.873] | 2.342 [2.197, 2.496] | 0.471 [0.462, 0.481] |
| `small-flat.noop.neo-freya.sender.warm` | again | 0.990 [0.868, 1.129] | 0.991 [0.910, 1.080] | 0.988 [0.966, 1.011] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.769 [0.616, 0.961] | 2.445 [2.103, 2.842] | 0.579 [0.555, 0.604] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.143 | 12.265 | 12.208 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.717 | 12.240 | 12.779 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.238 | 0.370 | 0.230 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.186 | 0.279 | 0.183 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.388 | 6.738 | 6.366 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.362 | 4.346 | 3.438 |
| `small-flat.noop.freya-neo.sender.warm` | 0.302 | 0.725 | 0.305 |
| `small-flat.noop.neo-freya.sender.warm` | 0.261 | 0.646 | 0.263 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 0.0056 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0073 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 0.0258 | 8 | 11 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0202 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 0.0747 | 53 | 70 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.0439 | 20 | 26 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 0.0490 | 24 | 31 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.0330 | 12 | 16 |
| `small-flat.fresh.freya-neo.sender.warm` | again | 0.0125 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0724 | 50 | 66 |
| `small-flat.fresh.neo-freya.sender.warm` | again | 0.0324 | 12 | 15 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.2933 | 775 | 1037 |
| `small-flat.noop.freya-neo.sender.warm` | again | 0.0779 | 57 | 76 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.0639 | 39 | 52 |
| `small-flat.noop.neo-freya.sender.warm` | again | 0.0825 | 64 | 84 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1430 | 186 | 248 |
