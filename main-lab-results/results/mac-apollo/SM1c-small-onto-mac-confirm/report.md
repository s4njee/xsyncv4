# SM1c-small-onto-mac-confirm

xs-cpp-noatomic is more than 5% faster than xs-cpp on real-congress, scale-count-1000000 (from SM1-small-onto-mac-apollo, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T103613Z-SM1c-small-onto-mac-confirm.
- Valid blocks: 1. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1 | 0.576 |  |  |  | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.614 | 1.067 | 0.578 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-cpp | xs-cpp-noatomic |
|---|---|---|
| `scale-count-1000000.fresh.apollo-mac.receiver.warm` | 76.681 | 44.173 |
