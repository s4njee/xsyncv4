# E0b-known

An injected slowdown of twice delta is called slower; one of delta excludes 1 but earns no verdict.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T003157Z-E0b-known.
- Valid blocks: 48. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-3pct | 12 | 1.035 [1.016, 1.055] | 1.032 [1.015, 1.058] | 0.0010 | 0.0039 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-6pct | 12 | 1.061 [1.037, 1.085] | 1.057 [1.037, 1.084] | 0.0005 | 0.0039 | slower |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-3pct | 12 | 1.046 [1.023, 1.069] | 1.044 [1.022, 1.071] | 0.0010 | 0.0039 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-6pct | 12 | 1.080 [1.043, 1.118] | 1.066 [1.053, 1.091] | 0.0005 | 0.0039 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-3pct | 12 | 1.030 [1.020, 1.039] | 1.031 [1.020, 1.040] | 0.0005 | 0.0039 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-6pct | 12 | 1.054 [1.042, 1.065] | 1.053 [1.041, 1.066] | 0.0005 | 0.0039 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-3pct | 12 | 0.963 [0.877, 1.056] | 0.999 [0.869, 1.036] | 0.4443 | 0.8887 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-6pct | 12 | 1.033 [0.921, 1.158] | 1.045 [0.923, 1.107] | 0.5693 | 0.8887 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-3pct | 1.005 [0.988, 1.021] | 1.036 [1.021, 1.052] | 1.002 [0.992, 1.013] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-6pct | 1.001 [0.982, 1.020] | 1.062 [1.036, 1.088] | 1.001 [0.990, 1.012] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-3pct | 1.040 [0.998, 1.085] | 1.045 [1.022, 1.068] | 1.000 [0.997, 1.002] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-6pct | 1.029 [0.990, 1.070] | 1.093 [1.026, 1.165] | 1.004 [1.000, 1.008] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-3pct | 1.000 [0.992, 1.009] | 1.024 [1.013, 1.035] | 0.989 [0.972, 1.007] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-6pct | 0.999 [0.977, 1.023] | 1.049 [1.038, 1.060] | 0.997 [0.985, 1.009] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-3pct | 1.028 [0.995, 1.063] | 0.871 [0.710, 1.069] | 0.989 [0.933, 1.048] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-6pct | 1.022 [0.985, 1.059] | 0.895 [0.698, 1.148] | 1.030 [0.983, 1.079] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-plus-3pct | xs-plus-6pct |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.645 | 13.090 | 13.411 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 13.151 | 13.754 | 14.202 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.475 | 6.667 | 6.824 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.835 | 3.692 | 3.961 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-3pct | 0.0300 | 11 | 13 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-plus-6pct | 0.0353 | 14 | 18 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-3pct | 0.0343 | 13 | 17 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-plus-6pct | 0.0541 | 29 | 38 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-3pct | 0.0147 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-plus-6pct | 0.0171 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-3pct | 0.1458 | 193 | 258 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-plus-6pct | 0.1801 | 293 | 392 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
