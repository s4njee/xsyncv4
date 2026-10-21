# AP10191250-LC11-local-eager-noatomic

Adding --no-atomic to xs -aH with eager writeback makes the durable psample copy to the T5 at least 5% faster than eager writeback alone.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-eager`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261019T125035Z-AP10191250-LC11-local-eager-noatomic.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager-noatomic | 4 | 0.993 [0.961, 1.026] | 0.992 | 0.3750 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager-noatomic | 0.993 [0.959, 1.027] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs-eager | xs-eager-noatomic |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 137.9 | 136.9 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager-noatomic | 0.0206 | 8 | 8 |
