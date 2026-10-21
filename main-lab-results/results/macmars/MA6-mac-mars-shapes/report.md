# MA6-mac-mars-shapes

The mac/mars tool ranking from psample holds on other real trees: many small compressible files, and a large compressible file.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T075636Z-MA6-mac-mars-shapes.
- Valid blocks: 16. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 4 | 0.413 [0.368, 0.462] | 0.413 | 0.1250 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 4 | 0.315 [0.202, 0.491] | 0.315 | 0.1250 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 4 | 0.253 [0.184, 0.348] | 0.265 | 0.1250 | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 4 | 0.591 [0.445, 0.783] | 0.596 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.649 [0.571, 0.738] | 0.446 [0.398, 0.499] | 9.554 [7.821, 11.672] |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.564 [0.393, 0.809] | 0.316 [0.203, 0.493] | 0.715 [0.623, 0.821] |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 1.165 [0.926, 1.466] | 0.287 [0.214, 0.385] | 8.992 [7.503, 10.776] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 0.693 [0.550, 0.872] | 0.596 [0.447, 0.794] | 0.769 [0.680, 0.870] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | 20.274 | 8.366 |
| `large-text.fresh.mars-mac.receiver.warm` | 28.849 | 9.085 |
| `real-congress.fresh.mac-mars.sender.warm` | 30.394 | 7.691 |
| `real-congress.fresh.mars-mac.receiver.warm` | 92.515 | 54.653 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.0715 | 48 | 64 |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.2795 | 704 | 942 |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 0.2007 | 364 | 487 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 0.1774 | 285 | 381 |
