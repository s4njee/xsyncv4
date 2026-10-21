# W0-neo-mars-wan-smoke

With 11 ms added and neo held to 2 CPUs, both tools complete every block and the link probe passes.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T011813Z-W0-neo-mars-wan-smoke.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.fresh.neo-mars.sender.warm` | xs | 2 | 0.780 [0.673, 0.905] | 0.780 | 0.5000 | too few blocks |
| `small-flat.noop.neo-mars.sender.warm` | xs | 2 | 0.231 [0.112, 0.479] | 0.231 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.947 [0.781, 1.148] | 9.299 [5.721, 15.116] | 0.779 [0.691, 0.879] |
| `small-flat.noop.neo-mars.sender.warm` | xs | 0.698 [0.076, 6.398] | 1.286 [0.861, 1.921] | 0.197 [0.091, 0.425] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `small-flat.fresh.neo-mars.sender.warm` | 16.050 | 12.521 |
| `small-flat.noop.neo-mars.sender.warm` | 2.364 | 0.547 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.neo-mars.sender.warm` | xs | 0.0165 | 8 | 8 |
| `small-flat.noop.neo-mars.sender.warm` | xs | 0.0810 | 61 | 81 |
