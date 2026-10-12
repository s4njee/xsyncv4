# T2a-adaptive-level

With -z, the new adaptive policy is faster than the old one when neo sends over gigabit, and no slower when freya sends.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs-z-old`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T164504Z-T2a-adaptive-level.
- Valid blocks: 72. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 0.993 [0.984, 1.001] | 0.993 [0.984, 1.002] | 0.0869 | 0.5708 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 0.996 [0.986, 1.006] | 0.995 [0.985, 1.007] | 0.3652 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 0.956 [0.818, 1.116] | 1.030 [0.784, 1.085] | 0.5312 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 0.900 [0.777, 1.042] | 0.985 [0.769, 1.000] | 0.0303 | 0.3027 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 0.989 [0.979, 1.000] | 0.989 [0.978, 1.002] | 0.0586 | 0.4688 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 1.011 [1.001, 1.022] | 1.012 [1.001, 1.023] | 0.0381 | 0.3428 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 1.137 [1.035, 1.249] | 1.149 [1.021, 1.251] | 0.0156 | 0.1719 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 0.919 [0.865, 0.977] | 0.941 [0.864, 0.979] | 0.0039 | 0.0469 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 1.002 [0.974, 1.031] | 1.001 [0.974, 1.032] | 0.8760 | 1.0000 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 1.009 [0.968, 1.053] | 1.012 [0.968, 1.055] | 0.6294 | 1.0000 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 1.078 [0.987, 1.178] | 1.099 [0.987, 1.177] | 0.0815 | 0.5708 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 1.032 [0.879, 1.212] | 1.079 [0.885, 1.242] | 0.6401 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 1.009 [0.997, 1.020] | 0.993 [0.982, 1.004] | 1.029 [1.003, 1.055] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 0.993 [0.976, 1.010] | 0.993 [0.981, 1.005] | 0.970 [0.950, 0.991] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 0.925 [0.673, 1.270] | 0.953 [0.813, 1.117] | 1.022 [0.976, 1.070] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 0.795 [0.591, 1.071] | 0.897 [0.773, 1.041] | 1.013 [0.974, 1.054] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 0.986 [0.977, 0.996] | 0.990 [0.981, 0.999] | 1.006 [0.894, 1.132] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 0.984 [0.972, 0.996] | 1.009 [0.999, 1.019] | 1.010 [0.932, 1.095] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 1.152 [0.977, 1.358] | 1.119 [1.002, 1.250] | 0.930 [0.833, 1.039] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 0.833 [0.719, 0.964] | 0.916 [0.835, 1.005] | 0.977 [0.815, 1.173] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 1.005 [0.977, 1.034] | 1.006 [0.978, 1.034] | 0.770 [0.509, 1.165] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 0.982 [0.955, 1.009] | 1.015 [0.972, 1.059] | 0.958 [0.665, 1.380] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 0.994 [0.930, 1.063] | 1.057 [0.923, 1.211] | 1.258 [0.909, 1.742] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 0.931 [0.879, 0.986] | 1.126 [0.985, 1.288] | 1.117 [0.793, 1.574] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-z-new | xs-z-old | xs-z1-old |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 9.431 | 9.500 | 9.460 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 10.491 | 10.977 | 9.880 |
| `small-flat.fresh.freya-neo.sender.warm` | 5.854 | 5.916 | 5.984 |
| `small-flat.fresh.neo-freya.sender.warm` | 4.300 | 3.782 | 3.477 |
| `small-real.fresh.freya-neo.sender.warm` | 13.609 | 13.581 | 13.709 |
| `small-real.fresh.neo-freya.sender.warm` | 7.034 | 6.525 | 6.736 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 0.0135 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0157 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 0.2439 | 536 | 718 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 0.2305 | 479 | 642 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 0.0172 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0170 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 0.1482 | 200 | 267 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 0.0964 | 86 | 114 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 0.0447 | 20 | 27 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0659 | 41 | 55 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 0.1389 | 176 | 235 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 0.2525 | 575 | 769 |
