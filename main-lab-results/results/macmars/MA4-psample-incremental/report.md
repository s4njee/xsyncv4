# MA4-psample-incremental

On mac/mars, xs re-syncs the psample tree faster than rsync -aH, warm: a no-op, and after 1% of the files change.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T032414Z-MA4-psample-incremental.
- Valid blocks: 15. Voided block attempts: 3.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.mac-mars.sender.warm` | xs | 4 | 0.272 [0.209, 0.355] | 0.286 | 0.1250 | too few blocks |
| `real-psample.noop.mars-mac.receiver.warm` | xs | 3 | 1.690 [1.280, 2.232] | 1.670 | 0.2500 | too few blocks |
| `real-psample.update-1pct.mac-mars.sender.warm` | xs | 4 | 0.268 [0.225, 0.319] | 0.263 | 0.1250 | too few blocks |
| `real-psample.update-1pct.mars-mac.receiver.warm` | xs | 4 | 1.301 [1.146, 1.477] | 1.301 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `real-psample.noop.mac-mars.sender.warm` | xs | 1.779 [1.308, 2.419] | 0.272 [0.209, 0.355] | 4.486 [4.357, 4.620] |
| `real-psample.noop.mars-mac.receiver.warm` | xs | 6.609 [5.078, 8.601] | 1.689 [1.284, 2.222] | 4.374 [3.878, 4.933] |
| `real-psample.update-1pct.mac-mars.sender.warm` | xs | 1.842 [1.569, 2.162] | 0.268 [0.226, 0.319] | 4.120 [3.993, 4.250] |
| `real-psample.update-1pct.mars-mac.receiver.warm` | xs | 5.195 [4.772, 5.657] | 1.301 [1.145, 1.477] | 3.695 [3.586, 3.807] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-psample.noop.mac-mars.sender.warm` | 96.723 | 26.343 |
| `real-psample.noop.mars-mac.receiver.warm` | 38.516 | 65.091 |
| `real-psample.update-1pct.mac-mars.sender.warm` | 96.640 | 25.902 |
| `real-psample.update-1pct.mars-mac.receiver.warm` | 45.720 | 59.488 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.mac-mars.sender.warm` | xs | 0.1665 | 251 | 336 |
| `real-psample.noop.mars-mac.receiver.warm` | xs | 0.1119 | 115 | 153 |
| `real-psample.update-1pct.mac-mars.sender.warm` | xs | 0.1089 | 109 | 145 |
| `real-psample.update-1pct.mars-mac.receiver.warm` | xs | 0.0798 | 60 | 79 |

## Voided attempts

- rsync: did not settle: mars has 603 MiB dirty
- xs: did not settle: mars has 349 MiB dirty
- xs: did not settle: mars has 469 MiB dirty
