# L2-noatomic-confirm

--no-atomic makes fresh copies of flat small-file trees more than 3% faster.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T152054Z-L2-noatomic-confirm.
- Valid blocks: 7. Voided block attempts: 3.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 1 | 0.731 |  |  |  | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 1 | 0.921 |  |  |  | too few blocks |
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 2 | 0.705 [0.697, 0.714] | 0.705 | 0.5000 | 0.5000 | too few blocks |
| `small-opaque.fresh.neo-freya.sender.warm` | no-atomic | 1 | 0.860 |  |  |  | too few blocks |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 1 | 0.978 |  |  |  | too few blocks |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 1 | 0.599 |  |  |  | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 0.850 | 0.746 | 1.012 |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 0.844 | 0.903 | 0.975 |
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 0.819 [0.782, 0.857] | 0.717 [0.638, 0.806] | 1.095 [0.294, 4.079] |
| `small-opaque.fresh.neo-freya.sender.warm` | no-atomic | 0.750 | 0.866 | 1.381 |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 1.017 | 0.989 | 1.014 |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 0.973 | 0.598 | 0.932 |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | no-atomic | xs |
|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | 4.020 | 5.501 |
| `small-flat.fresh.neo-freya.sender.warm` | 2.957 | 3.212 |
| `small-opaque.fresh.freya-neo.sender.warm` | 3.854 | 5.464 |
| `small-opaque.fresh.neo-freya.sender.warm` | 2.935 | 3.414 |
| `small-real.fresh.freya-neo.sender.warm` | 12.292 | 12.566 |
| `small-real.fresh.neo-freya.sender.warm` | 11.010 | 18.394 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 0.0013 | 8 | 8 |

## Voided attempts

- no-atomic: harness error: freya: `rm -rf -- /mnt/nvme/xsbench/work/20261016T152054Z-L2-noatomic-confirm/small-opaque.fresh.neo-freya.sender.warm/no-atomic` exit
- xs: harness error: freya: `rm -rf -- /mnt/nvme/xsbench/work/20261016T152054Z-L2-noatomic-confirm/small-opaque.fresh.neo-freya.sender.warm/xs` exited 255: ssh: c
- xs: harness error: freya: `sync -f /mnt/nvme/xsbench/work/20261016T152054Z-L2-noatomic-confirm/small-opaque.fresh.neo-freya.sender.warm` exited 1: sync: error o
