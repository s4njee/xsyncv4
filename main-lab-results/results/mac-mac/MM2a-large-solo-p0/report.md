# MM2a-large-solo-p0

On one 4 GiB file, half compressible within the file, rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable, fresh or after a 4 KiB edit in its middle (update-1pct of one file is that one edit).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T144412Z-MM2a-large-solo-p0.
- Valid blocks: 46. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 11 | 0.549 [0.532, 0.567] | 0.550 [0.529, 0.569] | 0.0010 | faster |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 11 | 0.827 [0.789, 0.866] | 0.827 [0.786, 0.868] | 0.0010 | faster |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 12 | 0.552 [0.508, 0.599] | 0.567 [0.503, 0.597] | 0.0005 | faster |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 12 | 0.575 [0.529, 0.624] | 0.587 [0.533, 0.627] | 0.0005 | faster |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 12 | 2.340 [2.316, 2.365] | 2.343 [2.315, 2.364] | 0.0005 | slower |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 12 | 1.488 [1.455, 1.521] | 1.498 [1.482, 1.512] | 0.0005 | slower |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 11 | 2.199 [2.164, 2.236] | 2.196 [2.166, 2.235] | 0.0010 | slower |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 11 | 1.222 [1.188, 1.257] | 1.208 [1.187, 1.261] | 0.0010 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 0.526 [0.515, 0.537] | 15.299 [15.278, 15.319] | 0.545 [0.527, 0.563] |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 0.460 [0.430, 0.492] | 445.721 [443.988, 447.460] | 0.824 [0.786, 0.864] |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 0.546 [0.527, 0.566] | 1.745 [1.655, 1.841] | 0.549 [0.505, 0.596] |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 0.574 [0.547, 0.603] | 16.882 [16.593, 17.176] | 0.571 [0.525, 0.621] |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 0.943 [0.924, 0.963] | 1.261 [1.256, 1.265] | 2.354 [2.324, 2.384] |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 1.018 [1.007, 1.029] | 0.974 [0.962, 0.987] | 1.496 [1.462, 1.530] |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 1.024 [1.014, 1.034] | 1.562 [1.546, 1.579] | 2.217 [2.181, 2.254] |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 0.975 [0.967, 0.982] | 1.125 [1.108, 1.141] | 1.223 [1.188, 1.258] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | 9.942 | 5.461 | 8.220 |
| `large-solo.fresh.mars-mac.receiver.warm` | 11.322 | 6.247 | 6.510 |
| `large-solo.update-1pct.mac-mars.sender.warm` | 5.516 | 12.910 | 8.207 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | 4.881 | 10.735 | 5.964 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 0.0480 | 23 | 30 |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 0.0690 | 45 | 60 |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 0.1291 | 152 | 203 |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 0.1300 | 154 | 206 |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 0.0164 | 8 | 8 |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 0.0350 | 13 | 17 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 0.0245 | 8 | 10 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 0.0422 | 18 | 24 |
