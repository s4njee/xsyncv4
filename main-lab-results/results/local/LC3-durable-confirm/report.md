# LC3-durable-confirm

xs-eager is more than 5% faster than xs on real-psample (from LC3-psample-local-durable, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261019T125037Z-LC3-durable-confirm.
- Valid blocks: 12. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 12 | 0.597 [0.552, 0.646] | 0.604 [0.549, 0.648] | 0.0005 | 0.0005 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.598 [0.552, 0.647] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-eager |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 233.5 | 139.5 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-eager | 0.1240 | 140 | 187 |
