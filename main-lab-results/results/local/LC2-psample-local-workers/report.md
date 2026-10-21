# LC2-psample-local-workers

On a four-core Pi writing to one USB SSD, a worker count other than the default four copies psample faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T215450Z-LC2-psample-local-workers.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j1 | 4 | 1.218 [1.111, 1.336] | 1.225 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 4 | 0.974 [0.884, 1.074] | 0.997 | 0.7500 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j8 | 4 | 1.055 [0.879, 1.266] | 1.055 | 0.5000 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j16 | 4 | 1.159 [0.884, 1.521] | 1.172 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j1 | 1.219 [1.110, 1.338] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 0.975 [0.884, 1.074] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j8 | 1.055 [0.880, 1.265] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j16 | 1.160 [0.886, 1.519] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-j1 | xs-j16 | xs-j2 | xs-j8 |
|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 229.3 | 279.4 | 265.9 | 223.4 | 241.9 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j1 | 0.0578 | 32 | 43 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 0.0610 | 36 | 47 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j8 | 0.1144 | 120 | 160 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j16 | 0.1704 | 263 | 352 |
