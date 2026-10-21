# G0b-10g-large-mac

xs carries the large trees to freya at close to 10 Gb/s.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T020250Z-G0b-10g-large-mac.
- Valid blocks: 0. Voided block attempts: 72.

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

- mac reaches freya by en4, not en13
