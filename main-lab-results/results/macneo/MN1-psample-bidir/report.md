# MN1-psample-bidir

On the direct Mac/neo link, xs or compression reduces fresh-copy time for the same pinned psample tree compared with rsync -aH; the effect may differ by direction.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T012805Z-MN1-psample-bidir, 20261018T020103Z-MN1-psample-bidir.
- Valid blocks: 0. Voided block attempts: 2.
- **The runs were made from different versions of the spec.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell |
|---|

## Voided attempts

- stopped
- xs: harness error: neo: `python3 ~/benchmarks/xsyncv4/lab/lib/021ae1ff14be/probe.py snapshot --interface eth1` exited 255: ssh: connect to host 10.27
