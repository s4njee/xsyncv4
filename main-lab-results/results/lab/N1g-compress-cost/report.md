# N1g-compress-cost

On a tree that will not compress, xs -z costs time against xs -a, and level 1 less than adaptive.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T165108Z-N1g-compress-cost, 20261017T185524Z-N1g-compress-cost.
- Valid blocks: 8. Voided block attempts: 24.
- **The runs were made from different versions of the spec.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z | 8 | 0.999 [0.997, 1.001] | 1.000 [0.997, 1.001] | 0.4766 | equivalent |
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z1 | 8 | 0.999 [0.998, 1.001] | 1.000 [0.998, 1.001] | 0.4688 | equivalent |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z | 0.981 [0.929, 1.036] | 1.007 [1.004, 1.010] | 1.000 [0.998, 1.001] |
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z1 | 1.002 [0.959, 1.048] | 1.006 [1.003, 1.008] | 0.999 [0.998, 1.001] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-z | xs-z1 |
|---|---|---|---|
| `large-mixed.fresh.neo-freya.sender.warm` | 77.297 | 77.251 | 77.257 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z | 0.0023 | 8 | 8 |
| `large-mixed.fresh.neo-freya.sender.warm` | xs-z1 | 0.0019 | 8 | 8 |

## Voided attempts

- neo does not answer ping
