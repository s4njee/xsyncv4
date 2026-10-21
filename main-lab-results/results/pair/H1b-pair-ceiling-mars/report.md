# H1b-pair-ceiling-mars

mars creates small files locally much faster than xs delivers them from the Pi.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T121636Z-H1b-pair-ceiling-mars.
- Valid blocks: 24. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-mars.receiver.warm` | local-x1 | 8 | 0.509 [0.496, 0.523] | 0.507 [0.497, 0.524] | 0.0078 | faster |
| `real-congress.fresh.neo-mars.receiver.warm` | local-x4 | 8 | 0.264 [0.254, 0.275] | 0.262 [0.256, 0.277] | 0.0078 | faster |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x1 | 8 | 0.770 [0.709, 0.836] | 0.790 [0.695, 0.820] | 0.0078 | faster |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x4 | 8 | 0.480 [0.438, 0.527] | 0.493 [0.424, 0.516] | 0.0078 | faster |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x1 | 8 | 0.588 [0.577, 0.599] | 0.589 [0.575, 0.599] | 0.0078 | faster |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x4 | 8 | 0.220 [0.214, 0.226] | 0.220 [0.213, 0.227] | 0.0078 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-congress.fresh.neo-mars.receiver.warm` | local-x1 | 0.502 [0.485, 0.519] |
| `real-congress.fresh.neo-mars.receiver.warm` | local-x4 | 0.257 [0.247, 0.268] |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x1 | 0.756 [0.697, 0.819] |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x4 | 0.457 [0.418, 0.499] |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x1 | 0.575 [0.565, 0.586] |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x4 | 0.188 [0.181, 0.194] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | local-x1 | local-x4 | xs-z-best |
|---|---|---|---|
| `real-congress.fresh.neo-mars.receiver.warm` | 4.558 | 2.365 | 8.949 |
| `small-deep.fresh.neo-mars.receiver.warm` | 4.546 | 2.836 | 5.904 |
| `small-flat.fresh.neo-mars.receiver.warm` | 1.745 | 0.652 | 2.966 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-mars.receiver.warm` | local-x1 | 0.0310 | 11 | 14 |
| `real-congress.fresh.neo-mars.receiver.warm` | local-x4 | 0.0456 | 21 | 28 |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x1 | 0.0986 | 90 | 119 |
| `small-deep.fresh.neo-mars.receiver.warm` | local-x4 | 0.1108 | 113 | 150 |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x1 | 0.0226 | 8 | 9 |
| `small-flat.fresh.neo-mars.receiver.warm` | local-x4 | 0.0343 | 13 | 17 |
