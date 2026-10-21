# W1-baseline

xs -a against rsync -a on the Wi-Fi pair gives the ratios it gives on the wired pair, cell by cell.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T112851Z-W1-baseline.
- Valid blocks: 101. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | xs | 5 | 1.032 [0.975, 1.092] | 1.030 | 0.2500 | 1.0000 | too few blocks |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | xs | 4 | 1.001 [0.808, 1.239] | 0.987 | 0.8750 | 1.0000 | too few blocks |
| `mixed-bimodal.noop.mars-orion.sender.warm` | xs | 4 | 0.704 [0.692, 0.716] | 0.704 | 0.1250 | 1.0000 | too few blocks |
| `mixed-bimodal.noop.orion-mars.sender.warm` | xs | 4 | 0.589 [0.382, 0.910] | 0.589 | 0.1250 | 1.0000 | too few blocks |
| `mixed-threshold.fresh.mars-orion.sender.warm` | xs | 4 | 0.993 [0.900, 1.097] | 0.993 | 0.7500 | 1.0000 | too few blocks |
| `mixed-threshold.fresh.orion-mars.sender.warm` | xs | 5 | 1.033 [0.874, 1.221] | 1.012 | 0.8125 | 1.0000 | too few blocks |
| `mixed-threshold.noop.mars-orion.sender.warm` | xs | 4 | 0.922 [0.908, 0.937] | 0.922 | 0.1250 | 1.0000 | too few blocks |
| `mixed-threshold.noop.orion-mars.sender.warm` | xs | 4 | 1.571 [0.703, 3.512] | 1.571 | 0.2500 | 1.0000 | too few blocks |
| `small-deep.fresh.mars-orion.sender.warm` | xs | 4 | 1.556 [1.439, 1.683] | 1.556 | 0.1250 | 1.0000 | too few blocks |
| `small-deep.fresh.orion-mars.sender.warm` | xs | 4 | 0.448 [0.270, 0.744] | 0.456 | 0.1250 | 1.0000 | too few blocks |
| `small-deep.noop.mars-orion.sender.warm` | xs | 4 | 1.234 [0.579, 2.629] | 1.143 | 0.6250 | 1.0000 | too few blocks |
| `small-deep.noop.orion-mars.sender.warm` | xs | 5 | 0.497 [0.313, 0.788] | 0.511 | 0.0625 | 1.0000 | too few blocks |
| `small-flat.fresh.mars-orion.sender.warm` | xs | 4 | 0.876 [0.843, 0.911] | 0.874 | 0.1250 | 1.0000 | too few blocks |
| `small-flat.fresh.orion-mars.sender.warm` | xs | 4 | 0.302 [0.181, 0.505] | 0.340 | 0.1250 | 1.0000 | too few blocks |
| `small-flat.noop.mars-orion.sender.warm` | xs | 4 | 0.462 [0.444, 0.481] | 0.462 | 0.1250 | 1.0000 | too few blocks |
| `small-flat.noop.orion-mars.sender.warm` | xs | 4 | 0.780 [0.489, 1.243] | 0.780 | 0.2500 | 1.0000 | too few blocks |
| `small-opaque.fresh.mars-orion.sender.warm` | xs | 4 | 0.853 [0.792, 0.917] | 0.853 | 0.1250 | 1.0000 | too few blocks |
| `small-opaque.fresh.orion-mars.sender.warm` | xs | 4 | 0.439 [0.287, 0.671] | 0.401 | 0.1250 | 1.0000 | too few blocks |
| `small-opaque.noop.mars-orion.sender.warm` | xs | 4 | 0.453 [0.420, 0.489] | 0.447 | 0.1250 | 1.0000 | too few blocks |
| `small-opaque.noop.orion-mars.sender.warm` | xs | 5 | 1.244 [0.113, 13.642] | 1.143 | 0.8125 | 1.0000 | too few blocks |
| `tiny-one.fresh.mars-orion.sender.warm` | xs | 4 | 0.958 [0.903, 1.016] | 0.958 | 0.1250 | 1.0000 | too few blocks |
| `tiny-one.fresh.orion-mars.sender.warm` | xs | 4 | 1.430 [0.121, 16.940] | 0.901 | 1.0000 | 1.0000 | too few blocks |
| `tiny-one.noop.mars-orion.sender.warm` | xs | 5 | 0.969 [0.927, 1.013] | 0.961 | 0.1250 | 1.0000 | too few blocks |
| `tiny-one.noop.orion-mars.sender.warm` | xs | 4 | 0.756 [0.220, 2.597] | 0.894 | 0.7500 | 1.0000 | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | xs | 1.357 [1.310, 1.406] | 7.786 [7.559, 8.020] | 1.028 [0.950, 1.113] |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | xs | 1.538 [1.270, 1.862] | 6.363 [6.294, 6.432] | 1.000 [0.807, 1.239] |
| `mixed-bimodal.noop.mars-orion.sender.warm` | xs | 1.634 [1.443, 1.851] | 1.199 [1.155, 1.244] | 0.699 [0.677, 0.720] |
| `mixed-bimodal.noop.orion-mars.sender.warm` | xs | 1.533 [1.219, 1.928] | 1.051 [1.023, 1.081] | 0.568 [0.391, 0.824] |
| `mixed-threshold.fresh.mars-orion.sender.warm` | xs | 1.656 [1.584, 1.733] | 7.283 [7.140, 7.429] | 0.992 [0.903, 1.089] |
| `mixed-threshold.fresh.orion-mars.sender.warm` | xs | 1.474 [1.335, 1.626] | 6.083 [6.020, 6.146] | 1.033 [0.874, 1.221] |
| `mixed-threshold.noop.mars-orion.sender.warm` | xs | 1.752 [1.568, 1.959] | 0.991 [0.968, 1.014] | 0.939 [0.891, 0.990] |
| `mixed-threshold.noop.orion-mars.sender.warm` | xs | 1.484 [1.414, 1.558] | 1.007 [0.974, 1.041] | 1.205 [0.620, 2.342] |
| `small-deep.fresh.mars-orion.sender.warm` | xs | 1.682 [1.617, 1.750] | 6.976 [6.163, 7.896] | 1.568 [1.453, 1.692] |
| `small-deep.fresh.orion-mars.sender.warm` | xs | 1.521 [1.240, 1.864] | 4.115 [3.694, 4.584] | 0.444 [0.266, 0.743] |
| `small-deep.noop.mars-orion.sender.warm` | xs | 4.138 [3.569, 4.797] | 7.047 [6.908, 7.189] | 1.234 [0.579, 2.631] |
| `small-deep.noop.orion-mars.sender.warm` | xs | 2.623 [2.340, 2.940] | 4.884 [4.686, 5.091] | 0.506 [0.305, 0.841] |
| `small-flat.fresh.mars-orion.sender.warm` | xs | 1.113 [1.057, 1.172] | 7.891 [7.791, 7.993] | 0.839 [0.792, 0.888] |
| `small-flat.fresh.orion-mars.sender.warm` | xs | 1.302 [1.154, 1.469] | 3.140 [0.980, 10.063] | 0.302 [0.180, 0.505] |
| `small-flat.noop.mars-orion.sender.warm` | xs | 0.998 [0.983, 1.014] | 1.704 [1.654, 1.756] | 0.460 [0.442, 0.480] |
| `small-flat.noop.orion-mars.sender.warm` | xs | 1.225 [0.860, 1.744] | 1.306 [1.275, 1.338] | 0.777 [0.480, 1.256] |
| `small-opaque.fresh.mars-orion.sender.warm` | xs | 1.108 [1.061, 1.158] | 7.916 [7.644, 8.198] | 0.837 [0.804, 0.873] |
| `small-opaque.fresh.orion-mars.sender.warm` | xs | 1.527 [1.392, 1.675] | 2.759 [1.122, 6.787] | 0.438 [0.286, 0.670] |
| `small-opaque.noop.mars-orion.sender.warm` | xs | 0.940 [0.833, 1.061] | 1.696 [1.641, 1.754] | 0.451 [0.418, 0.486] |
| `small-opaque.noop.orion-mars.sender.warm` | xs | 1.168 [0.759, 1.798] | 1.271 [1.237, 1.307] | 1.237 [0.111, 13.782] |
| `tiny-one.fresh.mars-orion.sender.warm` | xs | 1.366 [1.288, 1.448] | 1.027 [1.004, 1.051] | 0.957 [0.901, 1.017] |
| `tiny-one.fresh.orion-mars.sender.warm` | xs | 1.195 [1.130, 1.264] | 1.013 [0.998, 1.029] | 2.125 [0.267, 16.890] |
| `tiny-one.noop.mars-orion.sender.warm` | xs | 1.389 [1.277, 1.512] | 1.004 [0.998, 1.009] | 0.966 [0.923, 1.011] |
| `tiny-one.noop.orion-mars.sender.warm` | xs | 1.210 [1.092, 1.340] | 1.000 [0.986, 1.016] | 0.736 [0.206, 2.635] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | 22.428 | 23.137 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | 29.645 | 29.666 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | 0.641 | 0.451 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | 0.833 | 0.491 |
| `mixed-threshold.fresh.mars-orion.sender.warm` | 23.560 | 23.404 |
| `mixed-threshold.fresh.orion-mars.sender.warm` | 32.141 | 33.201 |
| `mixed-threshold.noop.mars-orion.sender.warm` | 0.421 | 0.388 |
| `mixed-threshold.noop.orion-mars.sender.warm` | 0.450 | 0.706 |
| `small-deep.fresh.mars-orion.sender.warm` | 24.759 | 38.525 |
| `small-deep.fresh.orion-mars.sender.warm` | 27.815 | 12.471 |
| `small-deep.noop.mars-orion.sender.warm` | 7.773 | 9.590 |
| `small-deep.noop.orion-mars.sender.warm` | 10.486 | 5.212 |
| `small-flat.fresh.mars-orion.sender.warm` | 19.295 | 16.911 |
| `small-flat.fresh.orion-mars.sender.warm` | 23.325 | 7.054 |
| `small-flat.noop.mars-orion.sender.warm` | 1.547 | 0.714 |
| `small-flat.noop.orion-mars.sender.warm` | 1.337 | 1.042 |
| `small-opaque.fresh.mars-orion.sender.warm` | 19.319 | 16.471 |
| `small-opaque.fresh.orion-mars.sender.warm` | 19.687 | 8.634 |
| `small-opaque.noop.mars-orion.sender.warm` | 1.535 | 0.695 |
| `small-opaque.noop.orion-mars.sender.warm` | 2.331 | 2.899 |
| `tiny-one.fresh.mars-orion.sender.warm` | 0.388 | 0.372 |
| `tiny-one.fresh.orion-mars.sender.warm` | 0.804 | 1.149 |
| `tiny-one.noop.mars-orion.sender.warm` | 0.390 | 0.378 |
| `tiny-one.noop.orion-mars.sender.warm` | 0.629 | 0.475 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | xs | 0.0456 | 21 | 28 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | xs | 0.1342 | 164 | 219 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | xs | 0.0108 | 8 | 8 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | xs | 0.2731 | 672 | 899 |
| `mixed-threshold.fresh.mars-orion.sender.warm` | xs | 0.0623 | 37 | 49 |
| `mixed-threshold.fresh.orion-mars.sender.warm` | xs | 0.1348 | 166 | 221 |
| `mixed-threshold.noop.mars-orion.sender.warm` | xs | 0.0099 | 8 | 8 |
| `mixed-threshold.noop.orion-mars.sender.warm` | xs | 0.5054 | 2294 | 3074 |
| `small-deep.fresh.mars-orion.sender.warm` | xs | 0.0491 | 24 | 32 |
| `small-deep.fresh.orion-mars.sender.warm` | xs | 0.3186 | 913 | 1223 |
| `small-deep.noop.mars-orion.sender.warm` | xs | 0.4755 | 2031 | 2722 |
| `small-deep.noop.orion-mars.sender.warm` | xs | 0.3712 | 1239 | 1660 |
| `small-flat.fresh.mars-orion.sender.warm` | xs | 0.0245 | 8 | 10 |
| `small-flat.fresh.orion-mars.sender.warm` | xs | 0.3227 | 937 | 1255 |
| `small-flat.noop.mars-orion.sender.warm` | xs | 0.0254 | 8 | 10 |
| `small-flat.noop.orion-mars.sender.warm` | xs | 0.2931 | 773 | 1036 |
| `small-opaque.fresh.mars-orion.sender.warm` | xs | 0.0461 | 22 | 28 |
| `small-opaque.fresh.orion-mars.sender.warm` | xs | 0.2673 | 644 | 862 |
| `small-opaque.noop.mars-orion.sender.warm` | xs | 0.0480 | 23 | 30 |
| `small-opaque.noop.orion-mars.sender.warm` | xs | 1.9290 | 33393 | 44754 |
| `tiny-one.fresh.mars-orion.sender.warm` | xs | 0.0373 | 15 | 19 |
| `tiny-one.fresh.orion-mars.sender.warm` | xs | 1.5536 | 21661 | 29030 |
| `tiny-one.noop.mars-orion.sender.warm` | xs | 0.0358 | 14 | 18 |
| `tiny-one.noop.orion-mars.sender.warm` | xs | 0.7755 | 5399 | 7236 |

## Voided attempts

- stopped
