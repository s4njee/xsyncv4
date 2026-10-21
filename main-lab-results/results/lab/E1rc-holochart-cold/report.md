# E1rc-holochart-cold

On a real JavaScript working tree, xs -aH differs from rsync -aH as it does on the small synthetic corpora.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220946Z-E1rc-holochart-cold.
- Valid blocks: 16. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.cold` | xs | 4 | 0.934 [0.916, 0.952] | 0.930 | 0.1250 | too few blocks |
| `real-holochart.fresh.neo-freya.sender.cold` | xs | 4 | 0.976 [0.973, 0.979] | 0.975 | 0.1250 | too few blocks |
| `real-holochart.noop.freya-neo.sender.cold` | xs | 4 | 0.227 [0.220, 0.235] | 0.227 | 0.1250 | too few blocks |
| `real-holochart.noop.neo-freya.sender.cold` | xs | 4 | 0.268 [0.251, 0.285] | 0.267 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.cold` | xs | 1.409 [1.365, 1.455] | 1.113 [1.092, 1.135] | 0.936 [0.919, 0.953] |
| `real-holochart.fresh.neo-freya.sender.cold` | xs | 1.596 [1.559, 1.635] | 6.001 [5.885, 6.120] | 0.976 [0.973, 0.979] |
| `real-holochart.noop.freya-neo.sender.cold` | xs | 1.197 [1.183, 1.211] | 0.728 [0.704, 0.754] | 0.226 [0.219, 0.234] |
| `real-holochart.noop.neo-freya.sender.cold` | xs | 2.081 [1.954, 2.216] | 3.147 [3.047, 3.250] | 0.268 [0.251, 0.285] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-holochart.fresh.freya-neo.sender.cold` | 74.464 | 69.566 |
| `real-holochart.fresh.neo-freya.sender.cold` | 69.731 | 68.059 |
| `real-holochart.noop.freya-neo.sender.cold` | 10.426 | 2.368 |
| `real-holochart.noop.neo-freya.sender.cold` | 7.276 | 1.948 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.cold` | xs | 0.0122 | 8 | 8 |
| `real-holochart.fresh.neo-freya.sender.cold` | xs | 0.0018 | 8 | 8 |
| `real-holochart.noop.freya-neo.sender.cold` | xs | 0.0211 | 8 | 8 |
| `real-holochart.noop.neo-freya.sender.cold` | xs | 0.0396 | 17 | 21 |
