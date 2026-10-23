# MM2a-large-solo-apollo

On one 4 GiB file, half compressible within the file, rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable, fresh or after a 4 KiB edit in its middle (update-1pct of one file is that one edit).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162408Z-MM2a-large-solo-apollo.
- Valid blocks: 75. Voided block attempts: 15.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-cpp | 20 | 0.323 [0.317, 0.329] | 0.323 [0.316, 0.329] | 0.0000 | faster |
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-rs | 20 | 0.382 [0.373, 0.392] | 0.382 [0.372, 0.393] | 0.0000 | faster |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-cpp | 18 | 0.434 [0.362, 0.520] | 0.410 [0.385, 0.514] | 0.0000 | faster |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-rs | 18 | 0.489 [0.394, 0.607] | 0.429 [0.409, 0.565] | 0.0001 | faster |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 20 | 2.316 [2.273, 2.359] | 2.317 [2.274, 2.359] | 0.0000 | slower |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 20 | 1.247 [1.211, 1.285] | 1.248 [1.209, 1.283] | 0.0000 | slower |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 17 | 1.211 [1.053, 1.393] | 1.260 [1.076, 1.302] | 0.0111 | slower |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 17 | 1.081 [0.869, 1.344] | 1.220 [0.876, 1.267] | 0.4612 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.612 [0.600, 0.625] | 0.660 [0.638, 0.683] | 0.317 [0.312, 0.323] |
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-rs | 0.365 [0.351, 0.379] | 15.837 [15.685, 15.990] | 0.378 [0.368, 0.387] |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-cpp | 0.551 [0.542, 0.561] | 7.832 [7.618, 8.052] | 0.360 [0.348, 0.372] |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-rs | 0.323 [0.314, 0.333] | 229.797 [223.256, 236.531] | 0.370 [0.359, 0.382] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.260 [1.247, 1.273] | 0.993 [0.983, 1.003] | 2.334 [2.290, 2.378] |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.136 [1.130, 1.143] | 0.997 [0.988, 1.006] | 1.245 [1.209, 1.281] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1.124 [1.116, 1.133] | 0.996 [0.987, 1.005] | 1.210 [1.052, 1.392] |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 1.081 [1.072, 1.091] | 0.997 [0.988, 1.007] | 1.080 [0.869, 1.344] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-solo.fresh.apollo-mac.receiver.warm` | 14.131 | 4.560 | 5.401 |
| `large-solo.fresh.mac-apollo.sender.warm` | 14.894 | 6.463 | 7.287 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | 4.844 | 11.217 | 6.043 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | 7.365 | 8.920 | 7.960 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0388 | 16 | 21 |
| `large-solo.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0530 | 28 | 36 |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3623 | 1180 | 1581 |
| `large-solo.fresh.mac-apollo.sender.warm` | xs-rs | 0.4331 | 1686 | 2259 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0396 | 17 | 21 |
| `large-solo.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0626 | 38 | 50 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.2716 | 664 | 890 |
| `large-solo.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.4239 | 1615 | 2164 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
