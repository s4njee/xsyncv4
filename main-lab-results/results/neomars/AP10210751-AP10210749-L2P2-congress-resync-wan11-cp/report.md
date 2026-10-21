# AP10210751-AP10210749-L2P2-congress-resync-wan11-cp

Under 11 ms and a 2-CPU sender, xs -a -j4 stays at least 5% faster than rsync -a at both the no-op and the 1% update of real-congress.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T075213Z-AP10210751-AP10210749-L2P2-congress-resync-wan11-cp.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.noop.neo-mars.sender.warm` | rsync | 8 | 3.016 [2.842, 3.201] | 3.008 [2.814, 3.231] | 0.0078 | slower |
| `real-congress.update-1pct.neo-mars.sender.warm` | rsync | 8 | 3.175 [3.052, 3.302] | 3.162 [3.055, 3.347] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.noop.neo-mars.sender.warm` | rsync | 0.652 [0.606, 0.701] | 0.534 [0.478, 0.597] | 3.189 [2.982, 3.411] |
| `real-congress.update-1pct.neo-mars.sender.warm` | rsync | 0.778 [0.759, 0.797] | 0.603 [0.572, 0.636] | 3.272 [3.183, 3.364] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `real-congress.noop.neo-mars.sender.warm` | 4.756 | 1.577 |
| `real-congress.update-1pct.neo-mars.sender.warm` | 6.167 | 1.943 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.noop.neo-mars.sender.warm` | rsync | 0.0712 | 48 | 63 |
| `real-congress.update-1pct.neo-mars.sender.warm` | rsync | 0.0470 | 22 | 29 |
