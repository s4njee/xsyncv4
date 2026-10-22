# CL-A1-c5b765eb54fc

A1 (c5b765eb54fc) changes the time to copy real-congress by more than 5%.

- Kind: screening. Primary metric: `durable_s`. Control arm: `parent`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T211140Z-CL-A1-c5b765eb54fc.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 8 | 0.411 [0.406, 0.415] | 0.411 [0.405, 0.416] | 0.0078 | faster |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 8 | 1.007 [0.962, 1.055] | 1.009 [0.950, 1.057] | 0.7031 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 1.019 [1.004, 1.035] | 0.999 [0.896, 1.112] | 0.404 [0.398, 0.410] |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 1.008 [0.986, 1.030] | 0.994 [0.862, 1.146] | 1.015 [0.964, 1.069] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | candidate | parent |
|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | 12.404 | 30.200 |
| `real-congress.noop.mac-mars.sender.warm` | 1.767 | 1.754 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | candidate | 0.0130 | 8 | 8 |
| `real-congress.noop.mac-mars.sender.warm` | candidate | 0.0556 | 30 | 40 |
