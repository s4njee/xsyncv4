# E1f-fresh-to-freya

xs -a differs from rsync -a by more than 3% in time-to-durable for a fresh copy from neo to freya, per corpus.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T111938Z-E1f-fresh-to-freya, 20261012T210902Z-E1f-fresh-to-freya.
- Valid blocks: 168. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 24 | 1.037 [1.032, 1.042] | 1.037 [1.032, 1.042] | 0.0000 | 0.0001 | slower |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 24 | 1.030 [1.022, 1.037] | 1.029 [1.023, 1.036] | 0.0000 | 0.0001 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 24 | 0.812 [0.750, 0.879] | 0.822 [0.798, 0.856] | 0.0000 | 0.0001 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 24 | 0.520 [0.487, 0.556] | 0.520 [0.473, 0.553] | 0.0000 | 0.0001 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 24 | 0.514 [0.493, 0.537] | 0.514 [0.492, 0.536] | 0.0000 | 0.0001 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 24 | 0.951 [0.884, 1.023] | 0.984 [0.971, 0.992] | 0.1355 | 0.1355 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 24 | 0.902 [0.872, 0.933] | 0.891 [0.874, 0.913] | 0.0000 | 0.0001 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.108 [2.078, 2.139] | 7.945 [7.771, 8.123] | 1.037 [1.032, 1.042] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 2.079 [2.038, 2.122] | 7.615 [7.468, 7.766] | 1.030 [1.022, 1.037] |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 2.335 [2.272, 2.400] | 5.685 [5.223, 6.188] | 0.804 [0.741, 0.871] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.503 [1.482, 1.523] | 5.060 [4.574, 5.599] | 0.512 [0.479, 0.547] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.497 [1.472, 1.521] | 5.282 [4.778, 5.839] | 0.506 [0.484, 0.528] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.931 [1.911, 1.951] | 10.396 [10.274, 10.520] | 0.947 [0.881, 1.019] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.328 [1.297, 1.361] | 1.351 [1.336, 1.366] | 0.894 [0.876, 0.912] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.260 | 12.714 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.191 | 13.581 |
| `small-deep.fresh.neo-freya.sender.warm` | 8.602 | 6.985 |
| `small-flat.fresh.neo-freya.sender.warm` | 6.708 | 3.490 |
| `small-opaque.fresh.neo-freya.sender.warm` | 6.807 | 3.502 |
| `small-real.fresh.neo-freya.sender.warm` | 11.972 | 11.386 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.182 | 0.164 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0118 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.0175 | 8 | 8 |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 0.1877 | 319 | 426 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.1559 | 221 | 295 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.1024 | 97 | 129 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.1722 | 269 | 359 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.0807 | 61 | 81 |
