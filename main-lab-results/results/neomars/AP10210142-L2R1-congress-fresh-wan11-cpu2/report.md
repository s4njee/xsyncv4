# AP10210142-L2R1-congress-fresh-wan11-cpu2

Under lab2's latency and a 2-CPU sender, xs -a -j4's lead over rsync on a fresh real-congress copy shrinks from the plain link's 1.39x (J1d) to a loss of at least 5%.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T014243Z-AP10210142-L2R1-congress-fresh-wan11-cpu2.
- Valid blocks: 12. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 12 | 1.397 [1.387, 1.408] | 1.395 [1.386, 1.408] | 0.0005 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 1.156 [1.149, 1.164] | 0.212 [0.204, 0.221] | 1.403 [1.393, 1.413] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | 42.364 | 30.317 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 0.0116 | 8 | 8 |
