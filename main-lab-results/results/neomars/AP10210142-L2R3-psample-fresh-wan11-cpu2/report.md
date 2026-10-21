# AP10210142-L2R3-psample-fresh-wan11-cpu2

Under lab2's latency and a 2-CPU sender, xs -a -j4 reaches a durable fresh copy of real-psample at least 5% later than rsync -a, with more block-to-block spread than rsync.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T014247Z-AP10210142-L2R3-psample-fresh-wan11-cpu2.
- Valid blocks: 0. Voided block attempts: 24.

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

- rsync: the destination does not match the corpus manifest: DIFFERS github/acritty/target/debug/incremental/alacritty-0apbfib5r6rer/s-hnarn3fo0v-1bemmqn-embc6e4s
- xs-j4: the destination does not match the corpus manifest: DIFFERS github/acritty/target/debug/incremental/alacritty-0apbfib5r6rer/s-hnarn3fo0v-1bemmqn-embc6e4s
