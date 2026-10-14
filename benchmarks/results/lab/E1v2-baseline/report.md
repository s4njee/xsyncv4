# E1v2-baseline

xs -a differs from rsync -a by more than 3% in time-to-durable, per corpus, scenario and direction.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020834Z-E1v2-baseline.
- Valid blocks: 200. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 7 | 0.988 [0.969, 1.008] | 0.992 [0.967, 1.006] | 0.2656 | 0.5312 | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 7 | 1.037 [1.022, 1.053] | 1.037 [1.022, 1.055] | 0.0156 | 0.4062 | too few blocks |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 7 | 0.633 [0.602, 0.665] | 0.627 [0.602, 0.671] | 0.0156 | 0.4062 | too few blocks |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 8 | 0.641 [0.615, 0.669] | 0.639 [0.611, 0.666] | 0.0078 | 0.2188 | faster |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 7 | 0.989 [0.974, 1.003] | 0.990 [0.973, 1.002] | 0.0625 | 0.4062 | too few blocks |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 7 | 1.031 [1.020, 1.043] | 1.031 [1.017, 1.042] | 0.0156 | 0.4062 | too few blocks |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 7 | 0.947 [0.908, 0.987] | 0.951 [0.908, 1.002] | 0.0625 | 0.4062 | too few blocks |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 7 | 0.871 [0.845, 0.898] | 0.871 [0.843, 0.902] | 0.0156 | 0.4062 | too few blocks |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 7 | 0.793 [0.743, 0.847] | 0.794 [0.749, 0.847] | 0.0156 | 0.4062 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 8 | 0.955 [0.709, 1.286] | 0.894 [0.733, 1.386] | 0.7500 | 0.7500 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | xs | 7 | 0.144 [0.122, 0.170] | 0.144 [0.122, 0.172] | 0.0156 | 0.4062 | too few blocks |
| `small-deep.noop.neo-freya.sender.warm` | xs | 7 | 0.505 [0.456, 0.561] | 0.512 [0.444, 0.561] | 0.0156 | 0.4062 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 7 | 0.951 [0.923, 0.980] | 0.947 [0.924, 0.987] | 0.0156 | 0.4062 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 7 | 0.616 [0.469, 0.808] | 0.604 [0.487, 0.907] | 0.0156 | 0.4062 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | xs | 7 | 0.422 [0.391, 0.455] | 0.427 [0.391, 0.452] | 0.0156 | 0.4062 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | xs | 7 | 0.377 [0.334, 0.424] | 0.366 [0.344, 0.429] | 0.0156 | 0.4062 | too few blocks |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 7 | 0.898 [0.795, 1.014] | 0.921 [0.779, 0.994] | 0.0312 | 0.4062 | too few blocks |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 7 | 0.527 [0.451, 0.616] | 0.528 [0.443, 0.624] | 0.0156 | 0.4062 | too few blocks |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 7 | 0.419 [0.392, 0.449] | 0.420 [0.390, 0.450] | 0.0156 | 0.4062 | too few blocks |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 7 | 0.454 [0.395, 0.522] | 0.451 [0.389, 0.533] | 0.0156 | 0.4062 | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | xs | 7 | 0.711 [0.664, 0.761] | 0.713 [0.662, 0.756] | 0.0156 | 0.4062 | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | xs | 7 | 0.943 [0.884, 1.006] | 0.944 [0.879, 1.012] | 0.1094 | 0.4062 | too few blocks |
| `small-real.noop.freya-neo.sender.warm` | xs | 7 | 0.156 [0.136, 0.180] | 0.153 [0.136, 0.183] | 0.0156 | 0.4062 | too few blocks |
| `small-real.noop.neo-freya.sender.warm` | xs | 8 | 0.692 [0.627, 0.764] | 0.695 [0.624, 0.771] | 0.0078 | 0.2188 | faster |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 8 | 0.913 [0.874, 0.953] | 0.903 [0.875, 0.957] | 0.0156 | 0.4062 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 7 | 0.889 [0.838, 0.943] | 0.899 [0.841, 0.943] | 0.0156 | 0.4062 | too few blocks |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 7 | 0.941 [0.894, 0.990] | 0.941 [0.893, 0.992] | 0.0469 | 0.4062 | too few blocks |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 7 | 0.884 [0.852, 0.917] | 0.893 [0.847, 0.905] | 0.0156 | 0.4062 | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.940 [1.902, 1.980] | 10.013 [9.762, 10.271] | 0.985 [0.966, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.076 [1.968, 2.190] | 8.190 [8.053, 8.329] | 1.036 [1.020, 1.053] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 1.714 [1.618, 1.815] | 1.413 [1.373, 1.453] | 0.624 [0.590, 0.660] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 1.686 [1.519, 1.872] | 1.347 [1.313, 1.383] | 0.640 [0.613, 0.667] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 2.289 [2.229, 2.352] | 8.117 [8.003, 8.232] | 0.983 [0.968, 0.998] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 2.074 [1.960, 2.195] | 7.773 [7.538, 8.015] | 1.031 [1.020, 1.043] |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 2.096 [1.964, 2.238] | 1.314 [1.286, 1.343] | 0.947 [0.906, 0.990] |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 1.783 [1.693, 1.878] | 1.345 [1.301, 1.390] | 0.869 [0.842, 0.897] |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.890 [0.827, 0.959] | 0.579 [0.536, 0.625] | 0.792 [0.743, 0.844] |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 2.288 [2.145, 2.441] | 6.089 [4.848, 7.648] | 0.952 [0.701, 1.292] |
| `small-deep.noop.freya-neo.sender.warm` | xs | 1.088 [0.990, 1.196] | 1.062 [1.041, 1.084] | 0.144 [0.122, 0.170] |
| `small-deep.noop.neo-freya.sender.warm` | xs | 5.260 [4.986, 5.549] | 5.671 [5.419, 5.935] | 0.505 [0.455, 0.560] |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 1.458 [1.412, 1.505] | 10.000 [9.407, 10.630] | 0.950 [0.919, 0.982] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.501 [1.417, 1.590] | 6.305 [5.134, 7.743] | 0.610 [0.466, 0.798] |
| `small-flat.noop.freya-neo.sender.warm` | xs | 1.218 [1.117, 1.328] | 2.161 [2.099, 2.224] | 0.414 [0.384, 0.445] |
| `small-flat.noop.neo-freya.sender.warm` | xs | 1.167 [1.012, 1.346] | 1.685 [1.645, 1.726] | 0.375 [0.333, 0.423] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 1.423 [1.362, 1.486] | 9.924 [9.642, 10.214] | 0.888 [0.779, 1.013] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.546 [1.483, 1.612] | 4.140 [3.748, 4.574] | 0.522 [0.445, 0.612] |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 1.177 [1.043, 1.328] | 2.106 [2.064, 2.149] | 0.412 [0.385, 0.442] |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 1.512 [1.258, 1.818] | 1.693 [1.642, 1.745] | 0.452 [0.393, 0.520] |
| `small-real.fresh.freya-neo.sender.warm` | xs | 1.024 [0.991, 1.058] | 0.763 [0.744, 0.783] | 0.704 [0.657, 0.754] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.926 [1.887, 1.965] | 10.237 [9.950, 10.532] | 0.942 [0.885, 1.003] |
| `small-real.noop.freya-neo.sender.warm` | xs | 1.294 [1.211, 1.384] | 0.632 [0.610, 0.656] | 0.155 [0.135, 0.179] |
| `small-real.noop.neo-freya.sender.warm` | xs | 8.440 [8.130, 8.762] | 4.268 [4.047, 4.500] | 0.688 [0.625, 0.757] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 1.558 [1.390, 1.747] | 1.325 [1.290, 1.361] | 0.912 [0.872, 0.955] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.364 [1.300, 1.430] | 1.349 [1.298, 1.401] | 0.888 [0.837, 0.942] |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 1.589 [1.420, 1.778] | 1.328 [1.287, 1.369] | 0.939 [0.891, 0.989] |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 1.310 [1.237, 1.388] | 1.310 [1.285, 1.335] | 0.883 [0.851, 0.916] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 13.122 | 12.969 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.260 | 12.716 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.381 | 0.241 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.301 | 0.193 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 13.876 | 13.719 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.171 | 13.584 |
| `mixed-threshold.noop.freya-neo.sender.warm` | 0.239 | 0.227 |
| `mixed-threshold.noop.neo-freya.sender.warm` | 0.189 | 0.164 |
| `small-deep.fresh.freya-neo.sender.warm` | 25.263 | 20.041 |
| `small-deep.fresh.neo-freya.sender.warm` | 7.925 | 7.568 |
| `small-deep.noop.freya-neo.sender.warm` | 18.519 | 2.672 |
| `small-deep.noop.neo-freya.sender.warm` | 3.146 | 1.590 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.995 | 6.652 |
| `small-flat.fresh.neo-freya.sender.warm` | 5.571 | 3.431 |
| `small-flat.noop.freya-neo.sender.warm` | 0.761 | 0.321 |
| `small-flat.noop.neo-freya.sender.warm` | 0.751 | 0.283 |
| `small-opaque.fresh.freya-neo.sender.warm` | 7.537 | 6.767 |
| `small-opaque.fresh.neo-freya.sender.warm` | 6.632 | 3.496 |
| `small-opaque.noop.freya-neo.sender.warm` | 0.778 | 0.326 |
| `small-opaque.noop.neo-freya.sender.warm` | 0.668 | 0.303 |
| `small-real.fresh.freya-neo.sender.warm` | 24.005 | 17.067 |
| `small-real.fresh.neo-freya.sender.warm` | 11.925 | 11.247 |
| `small-real.noop.freya-neo.sender.warm` | 9.222 | 1.441 |
| `small-real.noop.neo-freya.sender.warm` | 2.214 | 1.533 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.234 | 0.214 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.182 | 0.162 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.230 | 0.216 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.183 | 0.162 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.0216 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0160 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 0.0540 | 29 | 38 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 0.0503 | 25 | 33 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 0.0157 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.0123 | 8 | 8 |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 0.0453 | 21 | 27 |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 0.0331 | 12 | 16 |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.0714 | 48 | 64 |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 0.3565 | 1143 | 1531 |
| `small-deep.noop.freya-neo.sender.warm` | xs | 0.1786 | 289 | 386 |
| `small-deep.noop.neo-freya.sender.warm` | xs | 0.1120 | 115 | 153 |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 0.0321 | 12 | 15 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.2939 | 778 | 1041 |
| `small-flat.noop.freya-neo.sender.warm` | xs | 0.0816 | 62 | 83 |
| `small-flat.noop.neo-freya.sender.warm` | xs | 0.1289 | 152 | 202 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 0.1318 | 158 | 212 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.1678 | 255 | 341 |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 0.0728 | 50 | 66 |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 0.1506 | 206 | 275 |
| `small-real.fresh.freya-neo.sender.warm` | xs | 0.0734 | 51 | 67 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.0700 | 47 | 61 |
| `small-real.noop.freya-neo.sender.warm` | xs | 0.1532 | 213 | 285 |
| `small-real.noop.neo-freya.sender.warm` | xs | 0.1185 | 128 | 171 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 0.0514 | 26 | 34 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.0640 | 39 | 52 |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 0.0551 | 30 | 39 |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 0.0398 | 17 | 22 |
