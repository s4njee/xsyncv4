# AP10210751-AP10210749-L2R7-congress-pull-wan11-cpu2

With neo receiving under an 11 ms round trip and a 2-CPU cap, rsync -a's time-to-durable comes within 5% of xs -a -j4 or beats it, unlike the plain mars>neo cell where rsync was 1.34x slower (J1d).

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T075208Z-AP10210751-AP10210749-L2R7-congress-pull-wan11-cpu2.
- Valid blocks: 12. Voided block attempts: 6.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 12 | 1.289 [1.190, 1.398] | 1.273 [1.188, 1.380] | 0.0005 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 1.199 [1.165, 1.233] | 0.677 [0.656, 0.698] | 1.295 [1.193, 1.405] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | 23.322 | 18.086 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 0.1270 | 147 | 196 |

## Voided attempts

- rsync: did not settle: neo is 15% busy
- rsync: did not settle: neo is 79% busy
- xs-j4: did not settle: neo is 11% busy
- xs-j4: did not settle: neo is 15% busy
- xs-j4: did not settle: neo is 57% busy
- xs-j4: did not settle: neo is 74% busy
