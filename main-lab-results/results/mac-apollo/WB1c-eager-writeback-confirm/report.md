# WB1c-eager-writeback-confirm

xs-cpp-eager is more than 5% faster than xs-cpp on real-congress (from WB1-eager-writeback-apollo, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T160501Z-WB1c-eager-writeback-confirm.
- Valid blocks: 8. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 8 | 0.812 [0.662, 0.998] | 0.801 [0.654, 1.022] | 0.0469 | 0.0469 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 1.005 [0.964, 1.048] | 1.293 [0.963, 1.737] | 1.006 [0.831, 1.218] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-cpp | xs-cpp-eager |
|---|---|---|
| `real-congress.fresh.mac-apollo.sender.warm` | 12.942 | 10.515 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 0.2456 | 544 | 728 |
