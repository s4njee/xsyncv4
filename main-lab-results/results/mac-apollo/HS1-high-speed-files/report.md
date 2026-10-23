# HS1-high-speed-files

On 4 GiB of incompressible data, rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable in some of the four file counts, and the gap changes with the number of files.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T060258Z-HS1-high-speed-files.
- Valid blocks: 80. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.412 [0.407, 0.417] | 0.412 [0.407, 0.418] | 0.0020 | faster |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 10 | 0.397 [0.392, 0.403] | 0.397 [0.391, 0.403] | 0.0020 | faster |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 10 | 0.794 [0.626, 1.006] | 0.794 [0.624, 1.014] | 0.0625 | inconclusive |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 10 | 0.593 [0.469, 0.751] | 0.658 [0.501, 0.743] | 0.0020 | faster |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.392 [0.387, 0.397] | 0.392 [0.386, 0.397] | 0.0020 | faster |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 10 | 0.468 [0.409, 0.536] | 0.444 [0.433, 0.586] | 0.0020 | faster |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 10 | 0.661 [0.457, 0.956] | 0.678 [0.457, 0.984] | 0.0293 | inconclusive |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 10 | 0.535 [0.353, 0.810] | 0.509 [0.360, 0.853] | 0.0098 | faster |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.404 [0.397, 0.411] | 0.403 [0.397, 0.411] | 0.0020 | faster |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 10 | 0.389 [0.383, 0.395] | 0.390 [0.385, 0.395] | 0.0020 | faster |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 10 | 0.852 [0.688, 1.055] | 0.841 [0.699, 1.050] | 0.1250 | inconclusive |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 10 | 0.831 [0.627, 1.101] | 0.821 [0.629, 1.102] | 0.1816 | inconclusive |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.412 [0.390, 0.436] | 0.407 [0.395, 0.446] | 0.0020 | faster |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 10 | 0.388 [0.380, 0.396] | 0.390 [0.379, 0.397] | 0.0020 | faster |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 10 | 0.683 [0.509, 0.916] | 0.726 [0.494, 0.889] | 0.0098 | faster |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 10 | 0.837 [0.701, 0.999] | 0.851 [0.699, 0.996] | 0.0469 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.662 [0.650, 0.674] | 0.603 [0.539, 0.675] | 0.408 [0.403, 0.413] |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.314 [0.301, 0.328] | 0.658 [0.628, 0.690] | 0.393 [0.387, 0.399] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.665 [0.654, 0.676] | 9.517 [9.098, 9.956] | 0.436 [0.421, 0.450] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.296 [0.284, 0.309] | 10.275 [9.929, 10.633] | 0.431 [0.417, 0.446] |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.631 [0.608, 0.654] | 0.619 [0.576, 0.665] | 0.388 [0.383, 0.393] |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.447 [0.426, 0.469] | 16.388 [16.253, 16.525] | 0.464 [0.405, 0.532] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.620 [0.608, 0.632] | 7.930 [7.868, 7.993] | 0.442 [0.425, 0.459] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.377 [0.365, 0.389] | 227.231 [225.281, 229.198] | 0.441 [0.425, 0.458] |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.645 [0.630, 0.660] | 0.616 [0.567, 0.670] | 0.400 [0.393, 0.407] |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.315 [0.306, 0.325] | 0.597 [0.573, 0.622] | 0.385 [0.379, 0.391] |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.665 [0.657, 0.673] | 8.779 [7.186, 10.726] | 0.432 [0.423, 0.441] |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 0.296 [0.290, 0.301] | 9.224 [7.686, 11.068] | 0.428 [0.419, 0.437] |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.650 [0.642, 0.659] | 0.627 [0.559, 0.703] | 0.408 [0.386, 0.431] |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.314 [0.303, 0.326] | 0.598 [0.579, 0.618] | 0.383 [0.375, 0.392] |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.656 [0.646, 0.667] | 9.394 [8.997, 9.808] | 0.421 [0.412, 0.430] |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 0.295 [0.287, 0.304] | 10.069 [9.544, 10.623] | 0.417 [0.409, 0.424] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | 9.947 | 4.097 | 3.952 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 14.314 | 11.362 | 8.495 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | 10.154 | 3.978 | 4.754 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | 13.018 | 8.602 | 6.960 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | 10.137 | 4.091 | 3.946 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | 12.581 | 10.715 | 10.453 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | 10.142 | 4.183 | 3.932 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | 15.284 | 10.433 | 12.791 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0163 | 8 | 8 |
| `hs-16x256m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0189 | 8 | 8 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3309 | 985 | 1319 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.3291 | 975 | 1305 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0180 | 8 | 8 |
| `hs-1x4g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.1879 | 319 | 427 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.5168 | 2399 | 3215 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.5804 | 3025 | 4053 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0241 | 8 | 9 |
| `hs-4x1g.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0210 | 8 | 8 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-cpp | 0.2987 | 803 | 1076 |
| `hs-4x1g.fresh.mac-apollo.sender.warm` | xs-rs | 0.3936 | 1393 | 1866 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0768 | 55 | 74 |
| `hs-64x64m.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0297 | 10 | 13 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-cpp | 0.4106 | 1516 | 2030 |
| `hs-64x64m.fresh.mac-apollo.sender.warm` | xs-rs | 0.2477 | 553 | 740 |
