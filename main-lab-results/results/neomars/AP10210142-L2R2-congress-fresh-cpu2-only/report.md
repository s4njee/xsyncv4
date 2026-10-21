# AP10210142-L2R2-congress-fresh-cpu2-only

The 2-CPU cap alone, which leaves four workers competing for two cores, pulls xs's time to within 5% of rsync's or behind it, unlike the plain link where xs led by 1.39x.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T014245Z-AP10210142-L2R2-congress-fresh-cpu2-only.
- Valid blocks: 10. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 10 | 1.390 [1.380, 1.400] | 1.389 [1.379, 1.401] | 0.0020 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 1.159 [1.149, 1.169] | 0.206 [0.198, 0.215] | 1.395 [1.385, 1.406] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | 41.911 | 30.156 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 0.0101 | 8 | 8 |
