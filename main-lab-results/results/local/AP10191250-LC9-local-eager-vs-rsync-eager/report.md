# AP10191250-LC9-local-eager-vs-rsync-eager

With eager writeback on both sides, xs -aH reaches a durable copy of psample on the T5 at least 5% sooner than rsync -aH. LC3's screening implies a time ratio near 0.77.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync-eager`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261019T125032Z-AP10191250-LC9-local-eager-vs-rsync-eager.
- Valid blocks: 6. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 6 | 0.771 [0.764, 0.779] | 0.772 [0.760, 0.779] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.770 [0.763, 0.778] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-eager | xs-eager |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 180.5 | 139.2 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.0093 | 8 | 8 |
