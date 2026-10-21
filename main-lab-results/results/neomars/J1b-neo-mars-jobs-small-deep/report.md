# J1b-neo-mars-jobs-small-deep

-j4 and -j8 differ from each other, and from the default, by more than 5% in time-to-durable on small-file and no-op copies between neo and mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T170932Z-J1b-neo-mars-jobs-small-deep.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j4 | 8 | 1.009 [0.907, 1.123] | 0.998 [0.890, 1.128] | 0.9297 | inconclusive |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j8 | 8 | 1.027 [0.975, 1.082] | 1.024 [0.974, 1.093] | 0.2812 | inconclusive |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 8 | 1.123 [1.041, 1.211] | 1.135 [1.025, 1.201] | 0.0156 | inconclusive |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j4 | 8 | 0.998 [0.989, 1.008] | 0.998 [0.988, 1.010] | 0.6953 | equivalent |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j8 | 8 | 0.999 [0.991, 1.008] | 1.000 [0.990, 1.011] | 0.7969 | equivalent |
| `small-deep.fresh.neo-mars.sender.warm` | rsync | 8 | 1.093 [1.063, 1.125] | 1.093 [1.057, 1.131] | 0.0078 | slower |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j4 | 8 | 0.708 [0.644, 0.779] | 0.703 [0.642, 0.793] | 0.0078 | faster |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j8 | 8 | 0.704 [0.671, 0.739] | 0.696 [0.677, 0.751] | 0.0078 | faster |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 8 | 5.240 [5.057, 5.430] | 5.234 [5.020, 5.468] | 0.0078 | slower |
| `small-deep.noop.neo-mars.sender.warm` | xs-j4 | 8 | 0.994 [0.946, 1.044] | 0.994 [0.934, 1.048] | 0.7812 | inconclusive |
| `small-deep.noop.neo-mars.sender.warm` | xs-j8 | 8 | 0.749 [0.707, 0.794] | 0.751 [0.705, 0.795] | 0.0078 | faster |
| `small-deep.noop.neo-mars.sender.warm` | rsync | 8 | 1.180 [1.113, 1.250] | 1.192 [1.091, 1.248] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j4 | 0.526 [0.473, 0.586] | 0.980 [0.839, 1.146] | 1.007 [0.902, 1.124] |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j8 | 0.596 [0.555, 0.640] | 0.652 [0.565, 0.753] | 1.027 [0.973, 1.085] |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 0.760 [0.689, 0.839] | 1.038 [0.890, 1.212] | 1.131 [1.046, 1.223] |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j4 | 0.990 [0.978, 1.003] | 1.002 [0.977, 1.028] | 1.000 [0.991, 1.009] |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j8 | 1.088 [1.063, 1.115] | 1.017 [0.966, 1.070] | 1.000 [0.991, 1.009] |
| `small-deep.fresh.neo-mars.sender.warm` | rsync | 1.028 [0.993, 1.064] | 0.196 [0.181, 0.212] | 1.095 [1.063, 1.127] |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j4 | 0.309 [0.295, 0.324] | 0.937 [0.896, 0.979] | 0.708 [0.643, 0.778] |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j8 | 0.424 [0.414, 0.433] | 1.026 [1.004, 1.049] | 0.704 [0.671, 0.739] |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 0.454 [0.442, 0.467] | 0.918 [0.906, 0.931] | 5.243 [5.060, 5.433] |
| `small-deep.noop.neo-mars.sender.warm` | xs-j4 | 1.010 [0.975, 1.047] | 0.994 [0.959, 1.030] | 0.994 [0.945, 1.046] |
| `small-deep.noop.neo-mars.sender.warm` | xs-j8 | 1.152 [1.102, 1.204] | 0.914 [0.886, 0.944] | 0.742 [0.699, 0.787] |
| `small-deep.noop.neo-mars.sender.warm` | rsync | 0.341 [0.322, 0.360] | 0.220 [0.205, 0.235] | 1.186 [1.118, 1.257] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-j4 | xs-j8 |
|---|---|---|---|---|
| `small-deep.fresh.mars-neo.receiver.warm` | 16.095 | 14.335 | 14.464 | 14.726 |
| `small-deep.fresh.neo-mars.sender.warm` | 23.829 | 21.794 | 21.760 | 21.774 |
| `small-deep.noop.mars-neo.receiver.warm` | 15.656 | 2.988 | 2.115 | 2.104 |
| `small-deep.noop.neo-mars.sender.warm` | 3.105 | 2.632 | 2.616 | 1.972 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j4 | 0.1275 | 148 | 198 |
| `small-deep.fresh.mars-neo.receiver.warm` | xs-j8 | 0.0621 | 37 | 49 |
| `small-deep.fresh.mars-neo.receiver.warm` | rsync | 0.0906 | 76 | 101 |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j4 | 0.0109 | 8 | 8 |
| `small-deep.fresh.neo-mars.sender.warm` | xs-j8 | 0.0102 | 8 | 8 |
| `small-deep.fresh.neo-mars.sender.warm` | rsync | 0.0338 | 13 | 16 |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j4 | 0.1137 | 118 | 158 |
| `small-deep.noop.mars-neo.receiver.warm` | xs-j8 | 0.0575 | 32 | 42 |
| `small-deep.noop.mars-neo.receiver.warm` | rsync | 0.0425 | 19 | 24 |
| `small-deep.noop.neo-mars.sender.warm` | xs-j4 | 0.0594 | 34 | 45 |
| `small-deep.noop.neo-mars.sender.warm` | xs-j8 | 0.0687 | 45 | 59 |
| `small-deep.noop.neo-mars.sender.warm` | rsync | 0.0691 | 45 | 60 |
