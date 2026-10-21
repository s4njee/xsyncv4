# LC1-psample-local-baseline

Copying psample locally from NVMe to the T5 with cold caches, xs -aH is faster than rsync -aH and cp -a, and near a single tar stream.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T180924Z-LC1-psample-local-baseline, 20261018T184002Z-LC1-psample-local-baseline.
- Valid blocks: 4. Voided block attempts: 3.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 4 | 1.121 [1.014, 1.239] | 1.107 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-a | 4 | 1.155 [1.111, 1.202] | 1.156 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-r | 4 | 1.146 [1.098, 1.196] | 1.141 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | tar | 4 | 1.251 [1.173, 1.334] | 1.251 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 1.121 [1.013, 1.240] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-a | 1.155 [1.110, 1.202] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-r | 1.146 [1.099, 1.195] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | tar | 1.253 [1.175, 1.337] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | cp-a | cp-r | rsync | tar | xs |
|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 245.1 | 243.2 | 212.2 | 265.4 | 237.9 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 0.0629 | 38 | 50 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-a | 0.0248 | 8 | 10 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | cp-r | 0.0269 | 9 | 11 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | tar | 0.0405 | 17 | 22 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: 
- tar: the destination does not match the corpus manifest: 
- xs: the destination does not match the corpus manifest: 
