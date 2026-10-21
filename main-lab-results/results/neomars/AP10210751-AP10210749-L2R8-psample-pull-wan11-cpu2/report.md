# AP10210751-AP10210749-L2R8-psample-pull-wan11-cpu2

With neo receiving under 11 ms and 2 CPUs, xs -a -j4's time-to-durable is at least 5% behind rsync -a, or its per-block times vary far more than rsync's.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T075209Z-AP10210751-AP10210749-L2R8-psample-pull-wan11-cpu2.
- Valid blocks: 0. Voided block attempts: 18.

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
