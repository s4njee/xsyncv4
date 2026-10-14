# E1r2-holochart

On a real JavaScript working tree, xs -aH differs from rsync -aH as it does on the small synthetic corpora.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020836Z-E1r2-holochart.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 8 | 0.950 [0.939, 0.961] | 0.952 [0.939, 0.959] | 0.0078 | faster |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 8 | 0.997 [0.992, 1.002] | 0.997 [0.992, 1.002] | 0.2188 | equivalent |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 8 | 0.230 [0.217, 0.245] | 0.232 [0.218, 0.247] | 0.0078 | faster |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 8 | 0.377 [0.344, 0.414] | 0.370 [0.347, 0.422] | 0.0078 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 1.565 [1.502, 1.631] | 1.191 [1.145, 1.237] | 0.951 [0.940, 0.963] |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 1.978 [1.943, 2.014] | 5.693 [4.965, 6.528] | 0.997 [0.992, 1.002] |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 1.191 [1.144, 1.240] | 0.722 [0.715, 0.728] | 0.230 [0.217, 0.244] |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 3.166 [3.054, 3.283] | 3.202 [3.086, 3.322] | 0.377 [0.343, 0.414] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | 74.960 | 71.220 |
| `real-holochart.fresh.neo-freya.sender.warm` | 69.052 | 68.856 |
| `real-holochart.noop.freya-neo.sender.warm` | 8.025 | 1.850 |
| `real-holochart.noop.neo-freya.sender.warm` | 3.777 | 1.425 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-holochart.fresh.freya-neo.sender.warm` | xs | 0.0137 | 8 | 8 |
| `real-holochart.fresh.neo-freya.sender.warm` | xs | 0.0062 | 8 | 8 |
| `real-holochart.noop.freya-neo.sender.warm` | xs | 0.0710 | 48 | 63 |
| `real-holochart.noop.neo-freya.sender.warm` | xs | 0.1121 | 115 | 154 |
