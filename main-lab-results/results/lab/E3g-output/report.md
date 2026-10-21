# E3g-output

Printing every file name with -v costs xs more than 3% on small trees; -q costs nothing.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220728Z-E3g-output.
- Valid blocks: 35. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | verbose | 5 | 1.125 [1.096, 1.155] | 1.124 | 0.0625 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | quiet | 5 | 0.995 [0.946, 1.046] | 0.985 | 0.8750 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-v | 5 | 1.026 [0.992, 1.061] | 1.024 | 0.0625 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | verbose | 4 | 1.112 [1.022, 1.209] | 1.112 | 0.1250 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | quiet | 4 | 0.971 [0.920, 1.026] | 0.971 | 0.2500 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-v | 4 | 1.359 [0.867, 2.129] | 1.359 | 0.1250 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | verbose | 5 | 1.101 [0.964, 1.257] | 1.092 | 0.1250 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | quiet | 5 | 1.038 [0.804, 1.342] | 1.018 | 0.6250 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | rsync-v | 5 | 2.254 [1.937, 2.623] | 2.252 | 0.0625 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | verbose | 4 | 1.010 [0.786, 1.297] | 1.010 | 1.0000 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | quiet | 4 | 0.920 [0.726, 1.167] | 0.920 | 0.3750 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | rsync-v | 4 | 2.190 [1.588, 3.021] | 2.190 | 0.1250 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | verbose | 4 | 1.079 [0.902, 1.292] | 1.089 | 0.2500 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | quiet | 4 | 0.948 [0.806, 1.116] | 0.948 | 0.5000 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | rsync-v | 4 | 1.347 [1.237, 1.466] | 1.347 | 0.1250 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | verbose | 4 | 1.473 [1.206, 1.801] | 1.403 | 0.1250 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | quiet | 4 | 1.000 [0.987, 1.013] | 0.998 | 1.0000 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | rsync-v | 4 | 1.142 [0.893, 1.459] | 1.076 | 0.1250 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | verbose | 4 | 1.356 [0.838, 2.195] | 1.194 | 0.1250 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | quiet | 4 | 1.063 [0.812, 1.391] | 1.029 | 0.7500 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | rsync-v | 4 | 6.709 [6.585, 6.835] | 6.698 | 0.1250 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | verbose | 5 | 0.838 [0.627, 1.121] | 0.839 | 0.1875 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | quiet | 5 | 0.851 [0.713, 1.015] | 0.806 | 0.1250 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | rsync-v | 5 | 1.239 [1.011, 1.519] | 1.222 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | verbose | 1.292 [1.273, 1.311] | 1.115 [1.092, 1.139] | 1.061 [1.040, 1.083] |
| `small-flat.fresh.freya-neo.sender.warm` | quiet | 0.997 [0.967, 1.028] | 0.992 [0.954, 1.030] | 0.992 [0.951, 1.035] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-v | 0.676 [0.660, 0.693] | 1.019 [0.986, 1.053] | 0.100 [0.097, 0.102] |
| `small-flat.fresh.neo-freya.sender.warm` | verbose | 1.239 [1.176, 1.305] | 1.104 [1.028, 1.186] | 1.263 [1.055, 1.511] |
| `small-flat.fresh.neo-freya.sender.warm` | quiet | 1.007 [0.912, 1.112] | 0.974 [0.900, 1.055] | 1.012 [0.652, 1.570] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-v | 0.664 [0.626, 0.705] | 1.340 [0.870, 2.066] | 0.155 [0.106, 0.228] |
| `small-flat.noop.freya-neo.sender.warm` | verbose | 2.291 [1.912, 2.745] | 1.099 [0.971, 1.245] | 1.054 [1.014, 1.095] |
| `small-flat.noop.freya-neo.sender.warm` | quiet | 1.037 [0.769, 1.399] | 1.040 [0.809, 1.336] | 1.005 [0.985, 1.025] |
| `small-flat.noop.freya-neo.sender.warm` | rsync-v | 0.762 [0.624, 0.930] | 2.218 [1.916, 2.568] | 0.467 [0.448, 0.487] |
| `small-flat.noop.neo-freya.sender.warm` | verbose | 1.060 [0.784, 1.433] | 1.009 [0.787, 1.295] | 1.050 [1.023, 1.078] |
| `small-flat.noop.neo-freya.sender.warm` | quiet | 0.910 [0.737, 1.123] | 0.921 [0.727, 1.168] | 1.003 [0.973, 1.035] |
| `small-flat.noop.neo-freya.sender.warm` | rsync-v | 0.663 [0.438, 1.004] | 2.184 [1.585, 3.008] | 0.585 [0.557, 0.615] |
| `small-real.fresh.freya-neo.sender.warm` | verbose | 1.196 [1.098, 1.304] | 1.069 [0.907, 1.259] | 1.087 [0.983, 1.203] |
| `small-real.fresh.freya-neo.sender.warm` | quiet | 0.965 [0.902, 1.032] | 0.952 [0.815, 1.112] | 1.009 [0.938, 1.087] |
| `small-real.fresh.freya-neo.sender.warm` | rsync-v | 0.945 [0.886, 1.009] | 1.333 [1.219, 1.459] | 1.304 [1.215, 1.400] |
| `small-real.fresh.neo-freya.sender.warm` | verbose | 1.313 [1.149, 1.500] | 1.475 [1.206, 1.803] | 1.110 [1.023, 1.204] |
| `small-real.fresh.neo-freya.sender.warm` | quiet | 1.015 [0.984, 1.046] | 1.002 [0.992, 1.012] | 1.018 [0.936, 1.108] |
| `small-real.fresh.neo-freya.sender.warm` | rsync-v | 0.520 [0.508, 0.533] | 1.138 [0.895, 1.447] | 0.099 [0.093, 0.105] |
| `small-real.noop.freya-neo.sender.warm` | verbose | 1.242 [1.072, 1.439] | 1.356 [0.842, 2.185] | 1.168 [1.048, 1.302] |
| `small-real.noop.freya-neo.sender.warm` | quiet | 0.990 [0.910, 1.077] | 1.064 [0.816, 1.388] | 0.985 [0.928, 1.046] |
| `small-real.noop.freya-neo.sender.warm` | rsync-v | 0.778 [0.685, 0.883] | 6.677 [6.554, 6.802] | 1.603 [1.487, 1.729] |
| `small-real.noop.neo-freya.sender.warm` | verbose | 0.971 [0.929, 1.015] | 0.832 [0.621, 1.116] | 1.185 [1.024, 1.371] |
| `small-real.noop.neo-freya.sender.warm` | quiet | 0.993 [0.942, 1.047] | 0.845 [0.706, 1.012] | 1.064 [0.919, 1.231] |
| `small-real.noop.neo-freya.sender.warm` | rsync-v | 0.116 [0.109, 0.122] | 1.230 [1.000, 1.514] | 0.229 [0.203, 0.258] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | quiet | rsync-v | verbose | xs |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | 6.567 | 6.772 | 7.426 | 6.601 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.330 | 4.657 | 3.811 | 3.428 |
| `small-flat.noop.freya-neo.sender.warm` | 0.340 | 0.737 | 0.360 | 0.327 |
| `small-flat.noop.neo-freya.sender.warm` | 0.288 | 0.686 | 0.316 | 0.313 |
| `small-real.fresh.freya-neo.sender.warm` | 16.601 | 23.570 | 18.892 | 17.504 |
| `small-real.fresh.neo-freya.sender.warm` | 11.094 | 12.662 | 16.344 | 11.092 |
| `small-real.noop.freya-neo.sender.warm` | 1.471 | 9.285 | 1.877 | 1.384 |
| `small-real.noop.neo-freya.sender.warm` | 1.475 | 2.147 | 1.453 | 1.733 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | verbose | 0.0210 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | quiet | 0.0408 | 17 | 23 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-v | 0.0269 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | verbose | 0.0528 | 27 | 36 |
| `small-flat.fresh.neo-freya.sender.warm` | quiet | 0.0341 | 13 | 17 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-v | 0.2823 | 718 | 961 |
| `small-flat.noop.freya-neo.sender.warm` | verbose | 0.1071 | 105 | 141 |
| `small-flat.noop.freya-neo.sender.warm` | quiet | 0.2065 | 385 | 515 |
| `small-flat.noop.freya-neo.sender.warm` | rsync-v | 0.1221 | 136 | 182 |
| `small-flat.noop.neo-freya.sender.warm` | verbose | 0.1572 | 224 | 300 |
| `small-flat.noop.neo-freya.sender.warm` | quiet | 0.1492 | 202 | 270 |
| `small-flat.noop.neo-freya.sender.warm` | rsync-v | 0.2022 | 369 | 494 |
| `small-real.fresh.freya-neo.sender.warm` | verbose | 0.1130 | 117 | 156 |
| `small-real.fresh.freya-neo.sender.warm` | quiet | 0.1025 | 97 | 129 |
| `small-real.fresh.freya-neo.sender.warm` | rsync-v | 0.0533 | 28 | 37 |
| `small-real.fresh.neo-freya.sender.warm` | verbose | 0.1261 | 145 | 194 |
| `small-real.fresh.neo-freya.sender.warm` | quiet | 0.0081 | 8 | 8 |
| `small-real.fresh.neo-freya.sender.warm` | rsync-v | 0.1541 | 215 | 288 |
| `small-real.noop.freya-neo.sender.warm` | verbose | 0.3025 | 823 | 1103 |
| `small-real.noop.freya-neo.sender.warm` | quiet | 0.1692 | 259 | 347 |
| `small-real.noop.freya-neo.sender.warm` | rsync-v | 0.0117 | 8 | 8 |
| `small-real.noop.neo-freya.sender.warm` | verbose | 0.2337 | 493 | 660 |
| `small-real.noop.neo-freya.sender.warm` | quiet | 0.1420 | 183 | 245 |
| `small-real.noop.neo-freya.sender.warm` | rsync-v | 0.1641 | 244 | 326 |
