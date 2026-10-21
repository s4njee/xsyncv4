# LC4-psample-local-resync

Re-syncing the psample backup locally with cold caches, xs -aH is faster than rsync -aH at a no-op and after a 1% change.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T215454Z-LC4-psample-local-resync.
- Valid blocks: 6. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 6 | 0.520 [0.517, 0.524] | 0.520 [0.518, 0.526] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 0.520 [0.517, 0.524] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-psample.noop.neo-neo-ssd.receiver.cold` | 126.2 | 65.661 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 0.0059 | 8 | 8 |

## Voided attempts

- rsync: harness error: neo-ssd: `python3 /mnt/ssd/xsbench/lib/736894f6f725/corpus.py stale /mnt/ssd/xsbench/work/20261018T215454Z-LC4-psample-local-resync/real-p
- xs: harness error: neo-ssd: `python3 /mnt/ssd/xsbench/lib/736894f6f725/corpus.py stale /mnt/ssd/xsbench/work/20261018T215454Z-LC4-psample-local-resync/real-psam
