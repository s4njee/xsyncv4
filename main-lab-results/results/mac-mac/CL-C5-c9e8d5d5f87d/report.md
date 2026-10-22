# CL-C5-c9e8d5d5f87d

C5 (c9e8d5d5f87d) changes the time to copy real-congress by more than 5%.

- Kind: screening. Primary metric: `durable_s`. Control arm: `parent`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T214317Z-CL-C5-c9e8d5d5f87d.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 8 | 1.001 [0.974, 1.030] | 1.001 [0.967, 1.028] | 0.9062 | equivalent |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 8 | 0.991 [0.942, 1.043] | 0.989 [0.939, 1.045] | 0.6719 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 1.005 [0.991, 1.019] | 1.026 [0.944, 1.116] | 1.010 [0.988, 1.032] |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 0.992 [0.967, 1.017] | 1.003 [0.966, 1.042] | 0.987 [0.950, 1.026] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | candidate | parent |
|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | 12.420 | 12.402 |
| `real-congress.noop.mac-mars.sender.warm` | 1.714 | 1.730 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 0.0333 | 12 | 16 |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 0.0611 | 36 | 47 |
