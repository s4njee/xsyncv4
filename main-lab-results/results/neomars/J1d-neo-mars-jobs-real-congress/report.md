# J1d-neo-mars-jobs-real-congress

-j4 and -j8 differ from each other, and from the default, by more than 5% in time-to-durable on small-file and no-op copies between neo and mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T170936Z-J1d-neo-mars-jobs-real-congress.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j4 | 8 | 1.012 [0.911, 1.124] | 1.022 [0.900, 1.122] | 0.8281 | inconclusive |
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j8 | 8 | 1.015 [0.917, 1.123] | 1.025 [0.910, 1.138] | 0.7031 | inconclusive |
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 8 | 1.339 [1.237, 1.449] | 1.345 [1.230, 1.449] | 0.0078 | slower |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j4 | 8 | 1.003 [0.991, 1.015] | 1.003 [0.992, 1.017] | 0.5703 | equivalent |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j8 | 8 | 1.009 [1.000, 1.018] | 1.009 [0.998, 1.020] | 0.0859 | equivalent |
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 8 | 1.386 [1.372, 1.400] | 1.383 [1.373, 1.402] | 0.0078 | slower |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j4 | 8 | 0.867 [0.821, 0.916] | 0.856 [0.827, 0.922] | 0.0078 | faster |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j8 | 8 | 1.046 [0.851, 1.284] | 0.978 [0.899, 1.350] | 0.8281 | inconclusive |
| `real-congress.noop.mars-neo.receiver.warm` | rsync | 8 | 6.213 [5.916, 6.524] | 6.260 [5.846, 6.472] | 0.0078 | slower |
| `real-congress.noop.neo-mars.sender.warm` | xs-j4 | 8 | 0.970 [0.866, 1.085] | 1.000 [0.837, 1.050] | 0.7891 | inconclusive |
| `real-congress.noop.neo-mars.sender.warm` | xs-j8 | 8 | 0.781 [0.694, 0.878] | 0.800 [0.673, 0.872] | 0.0078 | faster |
| `real-congress.noop.neo-mars.sender.warm` | rsync | 8 | 2.265 [2.045, 2.509] | 2.359 [2.006, 2.437] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j4 | 0.749 [0.722, 0.778] | 0.900 [0.864, 0.938] | 1.012 [0.907, 1.128] |
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j8 | 0.799 [0.764, 0.836] | 0.851 [0.829, 0.872] | 1.016 [0.915, 1.129] |
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 0.880 [0.845, 0.917] | 0.607 [0.593, 0.621] | 1.346 [1.241, 1.461] |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j4 | 0.999 [0.985, 1.014] | 1.009 [0.980, 1.039] | 1.003 [0.989, 1.017] |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j8 | 1.063 [1.050, 1.076] | 1.068 [1.036, 1.100] | 1.009 [0.997, 1.022] |
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 1.126 [1.109, 1.143] | 0.216 [0.204, 0.228] | 1.391 [1.375, 1.407] |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j4 | 0.406 [0.394, 0.418] | 0.801 [0.778, 0.825] | 0.867 [0.821, 0.916] |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j8 | 0.555 [0.514, 0.598] | 0.894 [0.879, 0.909] | 1.046 [0.851, 1.284] |
| `real-congress.noop.mars-neo.receiver.warm` | rsync | 0.569 [0.551, 0.588] | 1.476 [1.462, 1.491] | 6.222 [5.925, 6.535] |
| `real-congress.noop.neo-mars.sender.warm` | xs-j4 | 1.029 [0.973, 1.088] | 1.010 [0.952, 1.072] | 1.020 [0.985, 1.055] |
| `real-congress.noop.neo-mars.sender.warm` | xs-j8 | 1.145 [1.103, 1.190] | 0.929 [0.870, 0.992] | 0.805 [0.758, 0.855] |
| `real-congress.noop.neo-mars.sender.warm` | rsync | 0.589 [0.554, 0.626] | 0.401 [0.359, 0.447] | 2.465 [2.355, 2.580] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-j4 | xs-j8 |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | 20.614 | 15.398 | 15.578 | 15.628 |
| `real-congress.fresh.neo-mars.sender.warm` | 41.728 | 30.107 | 30.202 | 30.373 |
| `real-congress.noop.mars-neo.receiver.warm` | 8.097 | 1.303 | 1.130 | 1.363 |
| `real-congress.noop.neo-mars.sender.warm` | 3.022 | 1.334 | 1.294 | 1.042 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j4 | 0.1258 | 145 | 193 |
| `real-congress.fresh.mars-neo.receiver.warm` | xs-j8 | 0.1211 | 134 | 179 |
| `real-congress.fresh.mars-neo.receiver.warm` | rsync | 0.0943 | 82 | 109 |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j4 | 0.0145 | 8 | 8 |
| `real-congress.fresh.neo-mars.sender.warm` | xs-j8 | 0.0111 | 8 | 8 |
| `real-congress.fresh.neo-mars.sender.warm` | rsync | 0.0123 | 8 | 8 |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j4 | 0.0653 | 41 | 54 |
| `real-congress.noop.mars-neo.receiver.warm` | xs-j8 | 0.2456 | 544 | 728 |
| `real-congress.noop.mars-neo.receiver.warm` | rsync | 0.0586 | 33 | 44 |
| `real-congress.noop.neo-mars.sender.warm` | xs-j4 | 0.1348 | 166 | 221 |
| `real-congress.noop.neo-mars.sender.warm` | xs-j8 | 0.1404 | 179 | 239 |
| `real-congress.noop.neo-mars.sender.warm` | rsync | 0.1223 | 137 | 182 |
