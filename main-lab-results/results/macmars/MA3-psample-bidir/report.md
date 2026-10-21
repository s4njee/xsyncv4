# MA3-psample-bidir

On the Mac/mars 10GbE link, xs copies the pinned psample tree faster than rsync -aH, fresh, in both directions.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T023003Z-MA3-psample-bidir.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 4 | 0.276 [0.170, 0.447] | 0.254 | 0.1250 | too few blocks |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 4 | 0.778 [0.470, 1.289] | 0.709 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 1.009 [0.868, 1.173] | 0.275 [0.162, 0.464] | 3.470 [2.450, 4.914] |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 1.105 [0.776, 1.573] | 0.778 [0.470, 1.289] | 2.529 [2.464, 2.597] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | 299.4 | 82.544 |
| `real-psample.fresh.mars-mac.receiver.warm` | 500.1 | 389.3 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 0.3030 | 826 | 1107 |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 0.3170 | 904 | 1211 |
