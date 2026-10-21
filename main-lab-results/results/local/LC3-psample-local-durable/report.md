# LC3-psample-local-durable

Eager writeback or skipping the temp-file rename gets the psample backup safely onto the T5 sooner.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T215452Z-LC3-psample-local-durable.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 4 | 0.618 [0.563, 0.679] | 0.629 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-noatomic | 4 | 0.968 [0.805, 1.163] | 0.968 | 0.7500 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync | 4 | 0.936 [0.852, 1.029] | 0.936 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync-eager | 4 | 0.804 [0.738, 0.875] | 0.812 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.619 [0.564, 0.680] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-noatomic | 0.969 [0.807, 1.165] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync | 0.936 [0.852, 1.030] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync-eager | 0.806 [0.740, 0.877] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-eager | xs | xs-eager | xs-noatomic |
|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 212.3 | 182.3 | 226.8 | 140.2 | 219.4 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.0590 | 34 | 44 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-noatomic | 0.1155 | 122 | 163 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync | 0.0596 | 34 | 45 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | rsync-eager | 0.0532 | 28 | 37 |
