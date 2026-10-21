# E3c-atomic

--no-atomic makes small fresh copies more than 3% faster and is no slower elsewhere.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220725Z-E3c-atomic.
- Valid blocks: 96. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 12 | 1.000 [0.998, 1.003] | 1.001 [0.998, 1.003] | 0.9126 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 12 | 1.007 [1.000, 1.013] | 1.006 [1.000, 1.014] | 0.0488 | equivalent |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 12 | 0.954 [0.882, 1.031] | 0.950 [0.887, 1.036] | 0.2109 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 12 | 1.091 [0.927, 1.285] | 1.033 [0.948, 1.209] | 0.2842 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 12 | 0.755 [0.741, 0.769] | 0.754 [0.740, 0.769] | 0.0005 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 12 | 0.947 [0.910, 0.985] | 0.951 [0.910, 0.988] | 0.0122 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 12 | 0.906 [0.858, 0.958] | 0.912 [0.854, 0.962] | 0.0015 | faster |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 12 | 1.012 [0.981, 1.044] | 0.999 [0.993, 1.011] | 0.7847 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 0.987 [0.965, 1.011] | 1.002 [0.997, 1.006] | 1.003 [0.996, 1.010] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 1.015 [0.988, 1.044] | 1.007 [1.000, 1.013] | 0.999 [0.993, 1.006] |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 0.984 [0.955, 1.014] | 0.953 [0.883, 1.027] | 1.002 [0.968, 1.036] |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 0.967 [0.938, 0.997] | 1.093 [0.930, 1.284] | 1.134 [0.989, 1.299] |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 0.853 [0.842, 0.865] | 0.771 [0.759, 0.783] | 1.000 [0.984, 1.016] |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 0.843 [0.819, 0.866] | 0.949 [0.911, 0.988] | 0.558 [0.425, 0.731] |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 0.962 [0.940, 0.985] | 0.911 [0.864, 0.961] | 0.991 [0.977, 1.006] |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 0.977 [0.955, 0.999] | 1.012 [0.981, 1.044] | 1.002 [0.974, 1.029] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | no-atomic | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.178 | 12.177 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.784 | 12.700 |
| `small-deep.fresh.freya-neo.sender.warm` | 19.837 | 20.801 |
| `small-deep.fresh.neo-freya.sender.warm` | 8.129 | 7.450 |
| `small-flat.fresh.freya-neo.sender.warm` | 4.863 | 6.443 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.276 | 3.459 |
| `small-real.fresh.freya-neo.sender.warm` | 15.327 | 16.911 |
| `small-real.fresh.neo-freya.sender.warm` | 11.213 | 11.083 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 0.0038 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 0.0101 | 8 | 8 |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 0.1234 | 139 | 186 |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 0.2573 | 597 | 799 |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 0.0294 | 10 | 13 |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 0.0623 | 37 | 49 |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 0.0864 | 70 | 92 |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 0.0490 | 24 | 31 |
