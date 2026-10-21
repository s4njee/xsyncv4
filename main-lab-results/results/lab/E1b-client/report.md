# E1b-client

A transfer started by the receiver takes the same time, within 3%, as the same transfer started by the sender.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs-push`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T003200Z-E1b-client.
- Valid blocks: 80. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 10 | 1.004 [0.972, 1.036] | 0.996 [0.981, 1.051] | 0.9805 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 10 | 0.993 [0.984, 1.002] | 0.994 [0.983, 1.002] | 0.1250 | 0.8750 | equivalent |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 0.988 [0.979, 0.997] | 0.988 [0.978, 0.998] | 0.0195 | 0.1758 | equivalent |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 10 | 0.990 [0.948, 1.033] | 0.997 [0.946, 1.033] | 0.6230 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 10 | 0.950 [0.837, 1.077] | 0.902 [0.880, 1.166] | 0.4121 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 0.903 [0.878, 0.929] | 0.899 [0.884, 0.927] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.781 [0.745, 0.819] | 0.787 [0.735, 0.812] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 10 | 1.630 [1.563, 1.698] | 1.627 [1.557, 1.708] | 0.0020 | 0.0469 | slower |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 10 | 1.317 [1.281, 1.354] | 1.319 [1.281, 1.355] | 0.0020 | 0.0469 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 10 | 1.380 [1.321, 1.442] | 1.371 [1.326, 1.447] | 0.0020 | 0.0469 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 10 | 1.476 [1.427, 1.527] | 1.477 [1.427, 1.528] | 0.0020 | 0.0469 | slower |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 10 | 1.696 [1.612, 1.786] | 1.706 [1.600, 1.784] | 0.0020 | 0.0469 | slower |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 10 | 0.984 [0.961, 1.007] | 0.986 [0.962, 1.005] | 0.1562 | 0.9375 | inconclusive |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 10 | 1.032 [0.977, 1.089] | 1.029 [0.974, 1.091] | 0.2305 | 1.0000 | inconclusive |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 1.002 [0.978, 1.027] | 1.005 [0.975, 1.029] | 0.8496 | 1.0000 | equivalent |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 10 | 1.051 [0.999, 1.106] | 1.039 [1.014, 1.130] | 0.0078 | 0.0859 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 10 | 1.245 [1.003, 1.546] | 1.187 [1.025, 1.499] | 0.0527 | 0.4219 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 1.400 [1.158, 1.691] | 1.431 [1.144, 1.743] | 0.0020 | 0.0469 | slower |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.832 [0.781, 0.886] | 0.841 [0.778, 0.879] | 0.0020 | 0.0469 | faster |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 10 | 2.354 [2.131, 2.601] | 2.339 [2.128, 2.639] | 0.0020 | 0.0469 | slower |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 10 | 2.068 [1.811, 2.362] | 2.000 [1.821, 2.395] | 0.0020 | 0.0469 | slower |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 10 | 1.194 [1.081, 1.318] | 1.196 [1.088, 1.329] | 0.0078 | 0.0859 | slower |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 10 | 2.360 [2.063, 2.701] | 2.367 [2.061, 2.704] | 0.0020 | 0.0469 | slower |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 10 | 2.568 [2.235, 2.951] | 2.567 [2.237, 3.001] | 0.0020 | 0.0469 | slower |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 1.656 [1.557, 1.762] | 1.006 [0.973, 1.040] | 1.001 [0.992, 1.011] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 0.483 [0.458, 0.509] | 0.996 [0.985, 1.007] | 0.100 [0.098, 0.101] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 0.994 [0.947, 1.045] | 0.990 [0.974, 1.005] | 0.101 [0.100, 0.103] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 0.741 [0.680, 0.808] | 1.001 [0.920, 1.089] | 1.001 [0.996, 1.007] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 0.412 [0.380, 0.446] | 0.947 [0.793, 1.130] | 0.122 [0.120, 0.124] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.281 [0.263, 0.299] | 0.903 [0.839, 0.971] | 0.120 [0.119, 0.122] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 0.995 [0.907, 1.092] | 0.785 [0.749, 0.823] | 0.988 [0.964, 1.013] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 0.584 [0.556, 0.613] | 1.622 [1.556, 1.690] | 0.693 [0.680, 0.705] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 0.632 [0.602, 0.665] | 1.314 [1.277, 1.352] | 0.705 [0.684, 0.727] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 0.878 [0.765, 1.008] | 1.381 [1.325, 1.439] | 0.981 [0.968, 0.994] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 0.540 [0.496, 0.589] | 1.470 [1.423, 1.519] | 0.722 [0.707, 0.737] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.500 [0.448, 0.558] | 1.701 [1.620, 1.787] | 0.732 [0.722, 0.742] |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 1.160 [1.129, 1.192] | 0.986 [0.962, 1.011] | 1.010 [0.980, 1.041] |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 0.674 [0.646, 0.703] | 1.033 [0.985, 1.083] | 0.101 [0.098, 0.105] |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 0.825 [0.805, 0.846] | 0.998 [0.973, 1.023] | 0.129 [0.120, 0.139] |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 0.852 [0.825, 0.881] | 0.958 [0.857, 1.071] | 1.006 [0.743, 1.362] |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 0.605 [0.562, 0.651] | 1.181 [0.951, 1.465] | 0.172 [0.132, 0.224] |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.557 [0.523, 0.593] | 1.317 [1.088, 1.594] | 0.185 [0.143, 0.239] |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 1.039 [0.946, 1.141] | 0.833 [0.783, 0.887] | 0.997 [0.984, 1.010] |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 0.812 [0.706, 0.934] | 2.342 [2.120, 2.586] | 0.478 [0.472, 0.484] |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 0.814 [0.686, 0.966] | 2.059 [1.804, 2.350] | 0.463 [0.452, 0.474] |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 0.928 [0.789, 1.091] | 1.189 [1.082, 1.306] | 0.995 [0.982, 1.009] |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 0.718 [0.595, 0.867] | 2.340 [2.052, 2.670] | 0.592 [0.584, 0.600] |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 0.720 [0.585, 0.887] | 2.554 [2.224, 2.933] | 0.585 [0.576, 0.595] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-pull | rsync-push | xs-pull | xs-push |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | 12.223 | 12.288 | 12.420 | 12.374 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | 12.432 | 13.071 | 13.626 | 13.764 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | 0.320 | 0.396 | 0.190 | 0.243 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | 0.326 | 0.283 | 0.265 | 0.192 |
| `small-flat.fresh.freya-neo.arm.warm` | 6.785 | 6.987 | 6.663 | 6.771 |
| `small-flat.fresh.neo-freya.arm.warm` | 5.573 | 4.959 | 4.187 | 3.982 |
| `small-flat.noop.freya-neo.arm.warm` | 0.724 | 0.824 | 0.291 | 0.350 |
| `small-flat.noop.neo-freya.arm.warm` | 0.786 | 0.723 | 0.365 | 0.306 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 0.0447 | 20 | 27 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-push | 0.0126 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 0.0125 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 0.0601 | 35 | 46 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-push | 0.1758 | 280 | 374 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.0391 | 16 | 21 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 0.0655 | 41 | 54 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-push | 0.0579 | 33 | 43 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 0.0388 | 16 | 21 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 0.0613 | 36 | 48 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-push | 0.0472 | 22 | 29 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.0715 | 48 | 64 |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 0.0327 | 12 | 15 |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-push | 0.0758 | 54 | 72 |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 0.0340 | 13 | 16 |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 0.0708 | 47 | 63 |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-push | 0.3024 | 823 | 1102 |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.2646 | 631 | 845 |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 0.0880 | 72 | 96 |
| `small-flat.noop.freya-neo.arm.warm` | rsync-push | 0.1394 | 177 | 236 |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 0.1856 | 311 | 417 |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 0.1380 | 173 | 231 |
| `small-flat.noop.neo-freya.arm.warm` | rsync-push | 0.1883 | 321 | 429 |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 0.1944 | 342 | 457 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
