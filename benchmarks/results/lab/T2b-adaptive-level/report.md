# T2b-adaptive-level

With -z, the new adaptive policy is faster than the old one when neo sends over gigabit, and no slower when freya sends.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs-z-old`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T181159Z-T2b-adaptive-level.
- Valid blocks: 72. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 1.000 [0.996, 1.003] | 0.999 [0.996, 1.003] | 0.7588 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 0.999 [0.995, 1.003] | 0.999 [0.995, 1.004] | 0.6250 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 0.902 [0.806, 1.010] | 0.950 [0.779, 1.004] | 0.0576 | 0.5186 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 0.889 [0.786, 1.005] | 0.935 [0.762, 0.990] | 0.0073 | 0.0806 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 0.996 [0.986, 1.007] | 0.995 [0.986, 1.007] | 0.4766 | 1.0000 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 1.009 [1.001, 1.018] | 1.009 [1.000, 1.019] | 0.0337 | 0.3369 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 0.957 [0.912, 1.004] | 0.958 [0.910, 1.002] | 0.0693 | 0.5273 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 0.918 [0.876, 0.962] | 0.932 [0.874, 0.966] | 0.0005 | 0.0059 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 12 | 1.027 [0.967, 1.091] | 1.028 [0.961, 1.099] | 0.3462 | 1.0000 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 12 | 1.043 [0.996, 1.092] | 1.034 [0.993, 1.097] | 0.0659 | 0.5273 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 12 | 1.007 [0.907, 1.118] | 1.011 [0.903, 1.117] | 0.8823 | 1.0000 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 12 | 1.065 [0.927, 1.223] | 1.083 [0.928, 1.214] | 0.3394 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 1.008 [0.988, 1.029] | 1.002 [0.996, 1.008] | 1.010 [0.976, 1.047] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 1.008 [0.993, 1.023] | 1.000 [0.993, 1.007] | 0.987 [0.951, 1.024] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 0.819 [0.648, 1.033] | 0.909 [0.805, 1.027] | 1.012 [0.981, 1.044] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 0.774 [0.602, 0.995] | 0.905 [0.796, 1.028] | 1.001 [0.963, 1.041] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 0.993 [0.982, 1.005] | 0.995 [0.986, 1.005] | 0.959 [0.860, 1.071] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 0.987 [0.975, 0.999] | 1.007 [0.999, 1.016] | 0.869 [0.785, 0.961] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 0.973 [0.852, 1.110] | 0.950 [0.844, 1.070] | 1.065 [0.875, 1.298] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 0.844 [0.769, 0.926] | 0.946 [0.814, 1.100] | 1.111 [0.877, 1.408] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 1.006 [0.987, 1.025] | 1.022 [0.963, 1.085] | 0.986 [0.579, 1.680] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 1.001 [0.975, 1.027] | 1.042 [0.995, 1.090] | 1.303 [0.768, 2.208] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 0.894 [0.837, 0.955] | 0.986 [0.896, 1.084] | 1.016 [0.737, 1.399] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 0.846 [0.791, 0.904] | 1.063 [0.950, 1.188] | 1.124 [0.741, 1.706] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-z-new | xs-z-old | xs-z1-old |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 9.404 | 9.409 | 9.400 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 10.299 | 11.419 | 10.149 |
| `small-flat.fresh.freya-neo.sender.warm` | 5.936 | 5.957 | 6.012 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.646 | 3.810 | 3.497 |
| `small-real.fresh.freya-neo.sender.warm` | 14.132 | 13.762 | 14.355 |
| `small-real.fresh.neo-freya.sender.warm` | 10.964 | 10.887 | 11.593 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-new | 0.0055 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0069 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-new | 0.1774 | 285 | 381 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1-old | 0.1934 | 338 | 452 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-new | 0.0171 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0129 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-new | 0.0762 | 55 | 72 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z1-old | 0.0742 | 52 | 69 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z-new | 0.0948 | 83 | 111 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1-old | 0.0726 | 50 | 66 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z-new | 0.1646 | 246 | 328 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1-old | 0.2179 | 429 | 573 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
