# E1r-holochart

On a real JavaScript working tree, xs -aH differs from rsync -aH as it does on the small synthetic corpora.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T210906Z-E1r-holochart.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 6 | 0.953 [0.936, 0.971] | 0.958 [0.921, 0.965] | 0.0312 | too few blocks |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 6 | 1.003 [0.993, 1.013] | 1.004 [0.994, 1.015] | 0.4375 | too few blocks |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 6 | 0.207 [0.191, 0.225] | 0.211 [0.185, 0.230] | 0.0312 | too few blocks |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 6 | 0.373 [0.356, 0.392] | 0.369 [0.350, 0.399] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 1.574 [1.511, 1.639] | 1.146 [1.103, 1.192] | 0.952 [0.935, 0.970] |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 2.035 [1.973, 2.100] | 5.968 [5.727, 6.220] | 1.002 [0.993, 1.011] |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 1.222 [1.136, 1.315] | 0.729 [0.722, 0.736] | 0.207 [0.191, 0.224] |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 2.958 [2.875, 3.044] | 3.177 [3.072, 3.286] | 0.373 [0.355, 0.391] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | 74.401 | 70.913 |
| `real-holochart.fresh.neo-freya.sender.warm` | 68.944 | 69.151 |
| `real-holochart.noop.freya-neo.sender.warm` | 7.641 | 1.584 |
| `real-holochart.noop.neo-freya.sender.warm` | 3.601 | 1.344 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 0.0176 | 8 | 8 |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 0.0092 | 8 | 8 |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 0.0776 | 56 | 75 |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 0.0461 | 22 | 28 |
