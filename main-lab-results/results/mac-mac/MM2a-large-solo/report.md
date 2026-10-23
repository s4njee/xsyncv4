# MM2a-large-solo

On one 4 GiB file, half compressible within the file, rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable, fresh or after a 4 KiB edit in its middle (update-1pct of one file is that one edit).

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T114745Z-MM2a-large-solo.
- Valid blocks: 80. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 20 | 0.496 [0.462, 0.532] | 0.484 [0.464, 0.508] | 0.0000 | faster |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 20 | 0.720 [0.684, 0.757] | 0.714 [0.681, 0.749] | 0.0000 | faster |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 20 | 0.453 [0.432, 0.475] | 0.452 [0.428, 0.475] | 0.0000 | faster |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 20 | 0.476 [0.452, 0.502] | 0.471 [0.449, 0.506] | 0.0000 | faster |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 20 | 2.249 [2.163, 2.337] | 2.291 [2.259, 2.312] | 0.0000 | slower |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 20 | 1.332 [1.281, 1.385] | 1.353 [1.338, 1.367] | 0.0000 | slower |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 20 | 2.216 [2.167, 2.267] | 2.230 [2.176, 2.262] | 0.0000 | slower |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 20 | 1.215 [1.190, 1.241] | 1.223 [1.189, 1.240] | 0.0000 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 0.500 [0.491, 0.509] | 15.718 [14.824, 16.666] | 0.492 [0.458, 0.529] |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 0.380 [0.367, 0.394] | 442.268 [434.453, 450.225] | 0.715 [0.680, 0.752] |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 0.508 [0.497, 0.519] | 1.816 [1.775, 1.858] | 0.449 [0.428, 0.471] |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 0.475 [0.457, 0.493] | 16.671 [16.494, 16.851] | 0.472 [0.448, 0.498] |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 0.930 [0.921, 0.939] | 1.257 [1.254, 1.261] | 2.270 [2.184, 2.359] |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 0.982 [0.975, 0.989] | 1.007 [0.983, 1.031] | 1.333 [1.284, 1.385] |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 1.038 [1.027, 1.048] | 1.566 [1.555, 1.577] | 2.236 [2.184, 2.289] |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 0.987 [0.979, 0.995] | 1.117 [1.101, 1.132] | 1.218 [1.193, 1.244] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | 11.360 | 5.634 | 8.175 |
| `large-solo.fresh.mars-mac.receiver.warm` | 13.566 | 6.142 | 6.456 |
| `large-solo.update-1pct.mac-mars.sender.warm` | 5.594 | 12.580 | 7.452 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | 4.984 | 11.046 | 6.058 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-solo.fresh.mac-mars.sender.warm` | xs-cpp | 0.1494 | 203 | 271 |
| `large-solo.fresh.mac-mars.sender.warm` | xs-rs | 0.1075 | 106 | 141 |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-cpp | 0.1019 | 96 | 127 |
| `large-solo.fresh.mars-mac.receiver.warm` | xs-rs | 0.1123 | 116 | 154 |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-cpp | 0.0827 | 64 | 85 |
| `large-solo.update-1pct.mac-mars.sender.warm` | xs-rs | 0.0830 | 64 | 85 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-cpp | 0.0482 | 23 | 30 |
| `large-solo.update-1pct.mars-mac.receiver.warm` | xs-rs | 0.0452 | 21 | 27 |
