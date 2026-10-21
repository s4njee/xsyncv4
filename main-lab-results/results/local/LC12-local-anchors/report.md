# LC12-local-anchors

With a larger parent-descriptor budget, xs -aH copies and re-syncs psample to the T5 faster than its parent, and at least as fast as rsync -aH.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261019T132845Z-LC12-local-anchors.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 6 | 1.109 [1.062, 1.158] | 1.110 [1.044, 1.183] | 0.0312 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-anchors | 6 | 1.165 [1.036, 1.311] | 1.165 [1.043, 1.360] | 0.0312 | 0.1250 | too few blocks |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 6 | 0.507 [0.497, 0.518] | 0.506 [0.493, 0.519] | 0.0312 | 0.1250 | too few blocks |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs-anchors | 6 | 0.511 [0.502, 0.520] | 0.511 [0.499, 0.522] | 0.0312 | 0.1250 | too few blocks |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 1.108 [1.062, 1.157] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-anchors | 1.166 [1.037, 1.312] |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 0.507 [0.497, 0.518] |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs-anchors | 0.511 [0.502, 0.520] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-anchors |
|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 209.3 | 232.1 | 243.9 |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | 124.5 | 63.146 | 63.604 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 0.0412 | 18 | 23 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-anchors | 0.1122 | 115 | 154 |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs | 0.0199 | 8 | 8 |
| `real-psample.noop.neo-neo-ssd.receiver.cold` | xs-anchors | 0.0171 | 8 | 8 |
