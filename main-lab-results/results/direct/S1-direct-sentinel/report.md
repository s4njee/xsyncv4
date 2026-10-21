# S1-direct-sentinel

The A/A ratio on the direct link stays within 3% of 1.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T113217Z-S1-direct-sentinel-s0001.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | again | 2 | 1.124 [0.275, 4.596] | 1.124 | 0.5000 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | rsync | 2 | 3.002 [2.757, 3.268] | 3.002 | 0.5000 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 2 | 0.989 [0.816, 1.198] | 0.989 | 1.0000 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 2 | 1.197 [0.710, 2.018] | 1.197 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | again | 1.074 [0.418, 2.756] | 1.006 [0.990, 1.022] | 1.124 [0.278, 4.534] |
| `large-one.fresh.mars-mac.receiver.warm` | rsync | 1.940 [1.712, 2.199] | 1.405 [1.221, 1.617] | 3.015 [2.790, 3.258] |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 0.984 [0.768, 1.261] | 1.006 [0.510, 1.985] | 0.990 [0.793, 1.237] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.038 [0.741, 1.455] | 1.486 [0.878, 2.515] | 1.200 [0.677, 2.127] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | 8.344 | 22.280 | 7.423 |
| `small-flat.fresh.mars-mac.receiver.warm` | 15.098 | 18.277 | 15.272 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | again | 0.1567 | 223 | 298 |
| `large-one.fresh.mars-mac.receiver.warm` | rsync | 0.0095 | 8 | 8 |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 0.0214 | 8 | 8 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.0582 | 33 | 43 |
