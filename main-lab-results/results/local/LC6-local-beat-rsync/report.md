# LC6-local-beat-rsync

With two or three workers, alone or with the source-guard fix, xs -aH copies psample to the T5 at least as fast as rsync -aH.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261018T224648Z-LC6-local-beat-rsync.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 4 | 1.077 [0.921, 1.260] | 1.067 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 4 | 1.085 [1.029, 1.145] | 1.085 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j3 | 4 | 1.049 [0.949, 1.158] | 1.049 | 0.3750 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j2 | 4 | 1.079 [0.996, 1.169] | 1.076 | 0.1250 | too few blocks |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j3 | 4 | 1.102 [0.937, 1.297] | 1.102 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 1.077 [0.919, 1.262] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 1.085 [1.028, 1.144] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j3 | 1.047 [0.948, 1.157] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j2 | 1.079 [0.997, 1.168] |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j3 | 1.102 [0.935, 1.298] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-guard-j2 | xs-guard-j3 | xs-j2 | xs-j3 |
|---|---|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | 210.6 | 226.9 | 227.3 | 232.2 | 228.6 | 220.8 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs | 0.0986 | 90 | 119 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j2 | 0.0334 | 13 | 16 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-j3 | 0.0626 | 38 | 50 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j2 | 0.0506 | 25 | 33 |
| `real-psample.fresh.neo-neo-ssd.receiver.cold` | xs-guard-j3 | 0.1022 | 96 | 128 |
