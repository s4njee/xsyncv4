# E1r-laikav2

On a real 42 GiB mixed tree, xs -aH is within a few percent of rsync -aH, as on the synthetic mixed corpora.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T210907Z-E1r-laikav2.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 4 | 1.190 [1.173, 1.207] | 1.185 | 0.1250 | too few blocks |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 4 | 1.242 [1.240, 1.245] | 1.242 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 2.689 [2.521, 2.868] | 1.057 [1.038, 1.076] | 1.190 [1.173, 1.208] |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 2.347 [2.317, 2.377] | 7.565 [6.769, 8.455] | 1.242 [1.240, 1.245] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | 330.4 | 393.0 |
| `real-laikav2.fresh.neo-freya.sender.warm` | 315.7 | 392.2 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 0.0090 | 8 | 8 |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 0.0013 | 8 | 8 |
