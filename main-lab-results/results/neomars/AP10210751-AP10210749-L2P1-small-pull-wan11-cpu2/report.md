# AP10210751-AP10210749-L2P1-small-pull-wan11-cpu2

In at least one of these six cells, rsync -a's time-to-durable comes within 5% of xs -a -j4's or beats it, since its plain-link lead there was 1.1x to 3x.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-j4`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T075211Z-AP10210751-AP10210749-L2P1-small-pull-wan11-cpu2.
- Valid blocks: 36. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 6 | 1.020 [1.003, 1.037] | 1.017 [1.004, 1.048] | 0.0312 | too few blocks |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 6 | 1.798 [1.763, 1.835] | 1.797 [1.744, 1.826] | 0.0312 | too few blocks |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 6 | 1.060 [0.966, 1.163] | 1.041 [0.980, 1.250] | 0.1562 | too few blocks |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 6 | 6.522 [6.085, 6.990] | 6.544 [5.911, 7.055] | 0.0312 | too few blocks |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 6 | 1.125 [0.833, 1.519] | 1.017 [0.934, 2.006] | 0.4375 | too few blocks |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 6 | 4.316 [4.154, 4.486] | 4.276 [4.190, 4.631] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.874 [0.859, 0.889] | 0.048 [0.045, 0.052] | 1.007 [1.003, 1.012] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 1.163 [1.141, 1.184] | 1.000 [1.000, 1.001] | 1.826 [1.800, 1.852] |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 1.485 [1.379, 1.598] | 1.017 [0.970, 1.066] | 1.074 [0.974, 1.184] |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 1.559 [1.492, 1.629] | 0.914 [0.901, 0.927] | 6.541 [6.098, 7.017] |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.867 [0.831, 0.905] | 0.074 [0.065, 0.083] | 1.142 [0.842, 1.550] |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 1.347 [1.203, 1.510] | 0.530 [0.523, 0.537] | 4.383 [4.231, 4.541] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-j4 |
|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | 13.202 | 12.944 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | 0.697 | 0.387 |
| `small-deep.fresh.mars-neo.receiver.warm` | 18.248 | 17.215 |
| `small-deep.noop.mars-neo.receiver.warm` | 17.346 | 2.660 |
| `small-flat.fresh.mars-neo.receiver.warm` | 6.765 | 6.015 |
| `small-flat.noop.mars-neo.receiver.warm` | 2.062 | 0.478 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.0160 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 0.0191 | 8 | 8 |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 0.0885 | 73 | 97 |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 0.0661 | 42 | 55 |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.2865 | 739 | 989 |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 0.0366 | 15 | 19 |
