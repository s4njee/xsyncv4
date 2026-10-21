# H1a-pair-ceiling-neo

The Pi creates small files locally much faster than xs delivers them from mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T121633Z-H1a-pair-ceiling-neo.
- Valid blocks: 24. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | local-x1 | 8 | 3.227 [3.127, 3.331] | 3.229 [3.113, 3.354] | 0.0078 | slower |
| `real-congress.fresh.mars-neo.sender.warm` | local-x4 | 8 | 1.595 [1.535, 1.656] | 1.582 [1.546, 1.679] | 0.0078 | slower |
| `small-deep.fresh.mars-neo.sender.warm` | local-x1 | 8 | 1.039 [0.997, 1.082] | 1.039 [0.988, 1.080] | 0.0625 | inconclusive |
| `small-deep.fresh.mars-neo.sender.warm` | local-x4 | 8 | 0.983 [0.944, 1.024] | 0.993 [0.942, 1.022] | 0.3750 | inconclusive |
| `small-flat.fresh.mars-neo.sender.warm` | local-x1 | 8 | 2.620 [2.455, 2.796] | 2.580 [2.472, 2.786] | 0.0078 | slower |
| `small-flat.fresh.mars-neo.sender.warm` | local-x4 | 8 | 1.292 [1.124, 1.485] | 1.245 [1.167, 1.542] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | local-x1 | 3.292 [3.189, 3.398] |
| `real-congress.fresh.mars-neo.sender.warm` | local-x4 | 1.607 [1.534, 1.683] |
| `small-deep.fresh.mars-neo.sender.warm` | local-x1 | 1.048 [1.002, 1.097] |
| `small-deep.fresh.mars-neo.sender.warm` | local-x4 | 0.990 [0.951, 1.032] |
| `small-flat.fresh.mars-neo.sender.warm` | local-x1 | 2.784 [2.614, 2.965] |
| `small-flat.fresh.mars-neo.sender.warm` | local-x4 | 1.311 [1.140, 1.507] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | local-x1 | local-x4 | xs-z-best |
|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | 35.022 | 17.305 | 10.852 |
| `small-deep.fresh.mars-neo.sender.warm` | 14.180 | 13.416 | 13.647 |
| `small-flat.fresh.mars-neo.sender.warm` | 9.511 | 4.691 | 3.630 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.sender.warm` | local-x1 | 0.0378 | 15 | 20 |
| `real-congress.fresh.mars-neo.sender.warm` | local-x4 | 0.0455 | 21 | 27 |
| `small-deep.fresh.mars-neo.sender.warm` | local-x1 | 0.0490 | 24 | 31 |
| `small-deep.fresh.mars-neo.sender.warm` | local-x4 | 0.0486 | 24 | 31 |
| `small-flat.fresh.mars-neo.sender.warm` | local-x1 | 0.0779 | 57 | 76 |
| `small-flat.fresh.mars-neo.sender.warm` | local-x4 | 0.1665 | 251 | 336 |
