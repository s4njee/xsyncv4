# T1h-send-cores-bytes

Three sending workers on a four-core sender keep most of one worker's gain on byte-bound copies and lose nothing on small files or no-ops.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220935Z-T1h-send-cores-bytes.
- Valid blocks: 40. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 20 | 0.995 [0.990, 1.001] | 0.994 [0.988, 1.001] | 0.0834 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 20 | 0.979 [0.974, 0.984] | 0.979 [0.974, 0.985] | 0.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 20 | 0.993 [0.981, 1.005] | 0.990 [0.983, 0.997] | 0.2688 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 20 | 0.978 [0.972, 0.985] | 0.979 [0.973, 0.986] | 0.0000 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 20 | 0.984 [0.970, 0.999] | 0.990 [0.983, 0.996] | 0.0010 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 20 | 0.974 [0.959, 0.990] | 0.980 [0.974, 0.986] | 0.0000 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 20 | 0.979 [0.972, 0.986] | 0.979 [0.974, 0.986] | 0.0000 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 20 | 0.972 [0.957, 0.987] | 0.978 [0.971, 0.984] | 0.0000 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 0.982 [0.960, 1.004] | 0.995 [0.989, 1.001] | 0.975 [0.971, 0.978] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.835 [0.809, 0.861] | 0.981 [0.976, 0.985] | 0.956 [0.953, 0.960] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 0.860 [0.839, 0.881] | 0.993 [0.980, 1.005] | 0.982 [0.979, 0.986] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.488 [0.477, 0.500] | 0.979 [0.973, 0.986] | 0.134 [0.131, 0.137] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 0.956 [0.929, 0.985] | 0.983 [0.969, 0.998] | 0.979 [0.977, 0.981] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 0.852 [0.824, 0.880] | 0.973 [0.958, 0.988] | 0.962 [0.960, 0.964] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 0.705 [0.680, 0.731] | 0.978 [0.970, 0.985] | 0.980 [0.975, 0.985] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.490 [0.470, 0.511] | 0.971 [0.955, 0.986] | 0.140 [0.139, 0.142] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | send2 | send3 | send3s1 | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.225 | 12.232 | 12.433 | 12.408 | 12.494 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.117 | 13.148 | 13.285 | 13.215 | 13.498 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3 | 0.0120 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send2 | 0.0118 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send3s1 | 0.0262 | 9 | 11 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0135 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3 | 0.0312 | 11 | 14 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send2 | 0.0336 | 13 | 16 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send3s1 | 0.0149 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.0331 | 12 | 16 |

## Voided attempts

- round trip is 2.74 ms, above 2.0
