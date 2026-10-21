# E1r3-laikav2

Once xs -aH sends linked data once, it is within a few percent of rsync -aH on the real 42 GiB tree.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220738Z-E1r3-laikav2.
- Valid blocks: 5. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 2 | 0.975 [0.904, 1.052] | 0.975 | 0.5000 | 0.5000 | too few blocks |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 3 | 1.001 [0.999, 1.002] | 1.001 | 0.2500 | 0.5000 | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 1.980 [1.816, 2.157] | 1.060 [0.968, 1.160] | 0.975 [0.899, 1.057] |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 1.461 [1.414, 1.509] | 8.101 [7.532, 8.714] | 1.001 [0.999, 1.002] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | 330.6 | 322.3 |
| `real-laikav2.fresh.neo-freya.sender.warm` | 315.6 | 315.8 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 0.0085 | 8 | 8 |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 0.0005 | 8 | 8 |

## Voided attempts

- stopped
