# AP10210142-L2R5-local-congress-cpu2

With 2 CPUs, xs -a -j4's lead over rsync -a on a fresh local real-congress copy falls well below J2's 1.84x, showing that xs's small-file advantage depends on spare cores.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T014235Z-AP10210142-L2R5-local-congress-cpu2.
- Valid blocks: 12. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 12 | 1.963 [1.893, 2.036] | 1.959 [1.890, 2.054] | 0.0005 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 2.017 [1.938, 2.099] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | 33.684 | 17.158 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.0574 | 32 | 42 |
