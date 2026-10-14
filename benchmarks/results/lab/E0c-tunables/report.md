# E0c-tunables

At default values the tunables build of ddefa041364e is within 3% of the release build, with and without XSYNC_METRICS.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `release`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T191931Z-E0c-tunables.
- Valid blocks: 64. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | tunables | 16 | 1.000 [0.996, 1.004] | 0.999 [0.996, 1.004] | 0.9163 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | metrics | 16 | 1.002 [0.998, 1.005] | 1.001 [0.998, 1.006] | 0.2676 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | tunables | 16 | 0.999 [0.992, 1.006] | 0.998 [0.992, 1.004] | 0.8119 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | metrics | 16 | 1.000 [0.991, 1.009] | 1.001 [0.991, 1.009] | 0.9752 | 1.0000 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | tunables | 16 | 0.989 [0.978, 1.001] | 0.988 [0.978, 1.001] | 0.0720 | 0.5759 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | metrics | 16 | 0.996 [0.985, 1.008] | 0.997 [0.986, 1.008] | 0.5067 | 1.0000 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | tunables | 16 | 1.002 [0.987, 1.016] | 1.001 [0.987, 1.015] | 0.7961 | 1.0000 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | metrics | 16 | 0.995 [0.982, 1.009] | 0.997 [0.982, 1.010] | 0.4759 | 1.0000 | equivalent |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | tunables | 1.000 [0.987, 1.013] | 1.000 [0.991, 1.009] | 1.004 [0.998, 1.010] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | metrics | 1.001 [0.984, 1.019] | 0.998 [0.989, 1.007] | 1.003 [0.995, 1.011] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | tunables | 1.007 [0.983, 1.032] | 0.999 [0.991, 1.006] | 1.001 [0.997, 1.006] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | metrics | 1.007 [0.976, 1.039] | 1.000 [0.991, 1.009] | 1.002 [0.997, 1.008] |
| `small-flat.fresh.freya-neo.sender.warm` | tunables | 0.995 [0.975, 1.015] | 0.988 [0.978, 0.998] | 1.009 [0.994, 1.024] |
| `small-flat.fresh.freya-neo.sender.warm` | metrics | 0.999 [0.983, 1.015] | 0.995 [0.983, 1.008] | 1.011 [0.996, 1.026] |
| `small-flat.fresh.neo-freya.sender.warm` | tunables | 1.003 [0.976, 1.031] | 1.002 [0.987, 1.017] | 1.002 [0.986, 1.018] |
| `small-flat.fresh.neo-freya.sender.warm` | metrics | 1.032 [0.998, 1.066] | 0.996 [0.980, 1.011] | 0.953 [0.890, 1.019] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | metrics | release | tunables |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.204 | 12.181 | 12.179 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.901 | 12.899 | 12.888 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.310 | 6.333 | 6.266 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.382 | 3.398 | 3.404 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | tunables | 0.0074 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | metrics | 0.0064 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | tunables | 0.0135 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | metrics | 0.0164 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | tunables | 0.0217 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | metrics | 0.0210 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | tunables | 0.0271 | 9 | 11 |
| `small-flat.fresh.neo-freya.sender.warm` | metrics | 0.0251 | 8 | 10 |
