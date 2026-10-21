# E1z-compress

xs -az differs from rsync -az by more than 3% in time-to-durable on fresh copies.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220939Z-E1z-compress.
- Valid blocks: 60. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 10 | 1.053 [1.036, 1.070] | 1.053 [1.036, 1.070] | 0.0020 | 0.0117 | slower |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 10 | 0.685 [0.656, 0.714] | 0.678 [0.661, 0.720] | 0.0020 | 0.0117 | faster |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 10 | 0.966 [0.929, 1.005] | 0.964 [0.926, 1.006] | 0.0879 | 0.0879 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 10 | 0.354 [0.316, 0.396] | 0.344 [0.314, 0.397] | 0.0020 | 0.0117 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs | 10 | 0.760 [0.726, 0.795] | 0.755 [0.721, 0.792] | 0.0020 | 0.0117 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 10 | 0.502 [0.467, 0.539] | 0.512 [0.462, 0.534] | 0.0020 | 0.0117 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.185 [1.162, 1.209] | 12.231 [11.920, 12.551] | 1.063 [1.055, 1.072] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 1.187 [1.088, 1.295] | 12.469 [12.001, 12.954] | 0.683 [0.654, 0.713] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 1.695 [1.642, 1.749] | 10.741 [9.984, 11.554] | 0.965 [0.927, 1.005] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.024 [0.993, 1.055] | 6.132 [4.177, 9.002] | 0.346 [0.313, 0.384] |
| `small-real.fresh.freya-neo.sender.warm` | xs | 1.446 [1.415, 1.477] | 0.858 [0.608, 1.209] | 0.751 [0.716, 0.787] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.679 [1.630, 1.729] | 3.873 [3.599, 4.167] | 0.493 [0.458, 0.530] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 9.465 | 9.965 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 14.187 | 9.711 |
| `small-opaque.fresh.freya-neo.sender.warm` | 6.062 | 5.857 |
| `small-opaque.fresh.neo-freya.sender.warm` | 10.306 | 3.646 |
| `small-real.fresh.freya-neo.sender.warm` | 14.704 | 11.169 |
| `small-real.fresh.neo-freya.sender.warm` | 11.755 | 5.899 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.0220 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0590 | 34 | 44 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 0.0556 | 30 | 40 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.1573 | 224 | 300 |
| `small-real.fresh.freya-neo.sender.warm` | xs | 0.0629 | 38 | 50 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.0992 | 91 | 121 |
