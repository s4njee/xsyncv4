# SM1c-small-onto-mac-confirm

xs-cpp-noatomic is more than 5% faster than xs-cpp on real-congress, scale-count-1000000 (from SM1-small-onto-mac-apollo, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T103613Z-SM1c-small-onto-mac-confirm.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 8 | 0.699 [0.688, 0.710] | 0.697 [0.687, 0.713] | 0.0078 | 0.0312 | faster |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 8 | 1.009 [0.986, 1.032] | 1.013 [0.984, 1.029] | 0.3984 | 0.3984 | equivalent |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 8 | 0.591 [0.578, 0.604] | 0.591 [0.575, 0.606] | 0.0078 | 0.0312 | faster |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 8 | 0.980 [0.951, 1.009] | 0.974 [0.952, 1.015] | 0.1562 | 0.3125 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.718 [0.712, 0.723] | 0.912 [0.674, 1.234] | 0.710 [0.697, 0.724] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1.001 [0.989, 1.014] | 0.996 [0.984, 1.008] | 1.004 [0.986, 1.022] |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.617 [0.611, 0.623] | 1.006 [0.932, 1.086] | 0.592 [0.580, 0.603] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1.057 [1.015, 1.101] | 1.005 [0.987, 1.023] | 0.971 [0.946, 0.998] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-cpp | xs-cpp-noatomic |
|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | 19.326 | 13.510 |
| `real-congress.noop.apollo-mac.receiver.warm` | 2.313 | 2.332 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | 71.991 | 42.539 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | 3.465 | 3.394 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0186 | 8 | 8 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0276 | 9 | 12 |
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0258 | 8 | 11 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.0356 | 14 | 18 |
