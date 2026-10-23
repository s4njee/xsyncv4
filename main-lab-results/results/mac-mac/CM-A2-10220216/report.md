# CM-A2-10220216

After the receiver-lock change, small-file fresh copies are limited by per-file work on the receiving Mac. If so, -j8 and -j16 give little over -j4 while peer CPU rises, and the effect is stronger on pull (mars>mac), where small-deep takes about twice as long as push. --no-atomic at -j8 beats -j8 if temp-file rename costs matter. A large gap between durable_s and wall_s would point at writeback. T

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T071651Z-CM-A2-10220216.
- Valid blocks: 0. Voided block attempts: 1.

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

- stopped
