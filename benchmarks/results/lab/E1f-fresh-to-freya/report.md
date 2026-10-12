# E1f-fresh-to-freya

xs -a differs from rsync -a by more than 3% in time-to-durable for a fresh copy from neo to freya, per corpus.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T111938Z-E1f-fresh-to-freya.
- Valid blocks: 84. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 12 | 1.036 [1.026, 1.046] | 1.035 [1.026, 1.046] | 0.0005 | 0.0034 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 12 | 1.028 [1.015, 1.042] | 1.026 [1.015, 1.043] | 0.0005 | 0.0034 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 12 | 0.834 [0.797, 0.873] | 0.825 [0.799, 0.862] | 0.0010 | 0.0034 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 12 | 0.458 [0.447, 0.468] | 0.457 [0.447, 0.469] | 0.0005 | 0.0034 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 12 | 0.486 [0.465, 0.508] | 0.485 [0.463, 0.510] | 0.0005 | 0.0034 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 12 | 0.948 [0.820, 1.096] | 0.987 [0.850, 1.034] | 0.5015 | 0.5015 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 12 | 0.922 [0.864, 0.985] | 0.904 [0.871, 0.965] | 0.0249 | 0.0498 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.123 [2.069, 2.178] | 8.174 [8.074, 8.275] | 1.036 [1.025, 1.046] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 2.053 [1.981, 2.127] | 7.706 [7.435, 7.988] | 1.029 [1.016, 1.042] |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 2.306 [2.230, 2.385] | 5.779 [4.997, 6.684] | 0.824 [0.784, 0.867] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.495 [1.478, 1.511] | 4.318 [3.851, 4.841] | 0.451 [0.440, 0.461] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.516 [1.488, 1.545] | 4.700 [4.196, 5.266] | 0.478 [0.456, 0.501] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.941 [1.919, 1.963] | 10.531 [10.341, 10.725] | 0.944 [0.816, 1.092] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.331 [1.285, 1.379] | 1.343 [1.315, 1.370] | 0.907 [0.881, 0.935] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.265 | 12.702 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.174 | 13.549 |
| `small-deep.fresh.neo-freya.sender.warm` | 8.775 | 7.318 |
| `small-flat.fresh.neo-freya.sender.warm` | 7.619 | 3.488 |
| `small-opaque.fresh.neo-freya.sender.warm` | 7.209 | 3.507 |
| `small-real.fresh.neo-freya.sender.warm` | 12.226 | 11.596 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.182 | 0.168 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0155 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.0202 | 8 | 8 |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 0.0713 | 48 | 64 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.0360 | 14 | 18 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.0696 | 46 | 61 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.2282 | 470 | 629 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.1034 | 98 | 131 |
