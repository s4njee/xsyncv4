# AP10191250-LC10-local-resync-1pct

xs -aH finishes the 1% update re-sync of psample onto the T5 faster than rsync -aH, as it did for the no-op re-sync (time ratio 0.52).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261019T125034Z-AP10191250-LC10-local-resync-1pct.
- Valid blocks: 0. Voided block attempts: 12.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell |
|---|

## Voided attempts

- rsync: harness error: neo-ssd: `python3 /mnt/ssd/xsbench/lib/736894f6f725/corpus.py stale /mnt/ssd/xsbench/work/20261019T125034Z-AP10191250-LC10-local-resync-1p
- xs: harness error: neo-ssd: `python3 /mnt/ssd/xsbench/lib/736894f6f725/corpus.py stale /mnt/ssd/xsbench/work/20261019T125034Z-AP10191250-LC10-local-resync-1pct/
