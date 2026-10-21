# Z4-10g-codecs

At 10 Gb/s a zstd fast level delivers compressible data faster than level 1, and LZ4 is faster than zstd for rsync.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z1`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T162335Z-Z4-10g-codecs.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast1 | 6 | 1.304 [1.029, 1.653] | 1.272 [1.065, 1.909] | 0.0312 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast5 | 6 | 1.117 [0.957, 1.304] | 1.097 [0.932, 1.429] | 0.1250 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast20 | 6 | 1.230 [0.959, 1.577] | 1.219 [0.911, 1.774] | 0.1250 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync-zstd | 6 | 3.211 [2.468, 4.178] | 3.312 [2.217, 4.256] | 0.0312 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync-lz4 | 6 | 3.467 [2.670, 4.502] | 3.410 [2.501, 4.446] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast1 | 6 | 1.360 [1.049, 1.763] | 1.284 [1.072, 2.188] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast5 | 6 | 1.239 [1.134, 1.355] | 1.256 [1.079, 1.355] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast20 | 6 | 1.337 [1.247, 1.433] | 1.323 [1.246, 1.512] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-zstd | 6 | 3.489 [3.071, 3.963] | 3.481 [3.017, 4.253] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-lz4 | 6 | 3.851 [3.225, 4.599] | 3.864 [3.126, 4.926] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast1 | 6 | 1.308 [1.029, 1.661] | 1.308 [0.926, 1.723] | 0.0625 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast5 | 6 | 1.224 [0.927, 1.617] | 1.113 [1.022, 2.077] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast20 | 6 | 1.235 [1.049, 1.453] | 1.207 [1.041, 1.628] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync-zstd | 6 | 4.356 [3.906, 4.859] | 4.280 [3.978, 5.159] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync-lz4 | 6 | 4.954 [4.579, 5.360] | 4.888 [4.646, 5.669] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast1 | 6 | 1.619 [1.215, 2.156] | 1.562 [1.204, 2.711] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast5 | 6 | 1.861 [1.525, 2.271] | 1.862 [1.485, 2.335] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast20 | 6 | 2.191 [1.701, 2.822] | 2.252 [1.466, 2.819] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-zstd | 6 | 4.547 [3.981, 5.194] | 4.576 [3.888, 5.384] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-lz4 | 6 | 5.214 [4.230, 6.426] | 5.209 [4.038, 6.781] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast1 | 1.003 [0.976, 1.032] | 0.651 [0.627, 0.676] | 1.303 [1.035, 1.640] |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast5 | 0.884 [0.863, 0.904] | 0.600 [0.586, 0.614] | 1.116 [0.948, 1.314] |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast20 | 0.797 [0.777, 0.818] | 0.555 [0.526, 0.585] | 1.236 [0.960, 1.591] |
| `large-half.fresh.mac-mars.sender.warm` | rsync-zstd | 1.914 [1.839, 1.992] | 0.053 [0.051, 0.055] | 3.228 [2.493, 4.180] |
| `large-half.fresh.mac-mars.sender.warm` | rsync-lz4 | 2.175 [2.093, 2.260] | 0.053 [0.052, 0.055] | 3.479 [2.684, 4.510] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast1 | 1.029 [0.989, 1.071] | 0.621 [0.586, 0.657] | 1.361 [1.048, 1.768] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast5 | 0.932 [0.913, 0.952] | 0.615 [0.571, 0.662] | 1.241 [1.134, 1.358] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast20 | 0.883 [0.872, 0.893] | 0.599 [0.570, 0.629] | 1.341 [1.252, 1.437] |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-zstd | 1.409 [1.370, 1.449] | 0.833 [0.819, 0.847] | 3.504 [3.088, 3.975] |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-lz4 | 1.413 [1.368, 1.460] | 0.837 [0.824, 0.850] | 3.877 [3.244, 4.634] |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast1 | 0.955 [0.886, 1.031] | 0.626 [0.605, 0.648] | 1.304 [1.028, 1.656] |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast5 | 0.801 [0.770, 0.834] | 0.567 [0.540, 0.595] | 1.225 [0.927, 1.618] |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast20 | 0.665 [0.626, 0.707] | 0.514 [0.491, 0.539] | 1.231 [1.043, 1.453] |
| `large-text.fresh.mac-mars.sender.warm` | rsync-zstd | 1.672 [1.620, 1.726] | 0.049 [0.048, 0.051] | 4.359 [3.908, 4.862] |
| `large-text.fresh.mac-mars.sender.warm` | rsync-lz4 | 2.008 [1.957, 2.061] | 0.050 [0.048, 0.051] | 4.955 [4.577, 5.364] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast1 | 1.044 [0.968, 1.127] | 0.625 [0.600, 0.651] | 1.625 [1.221, 2.163] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast5 | 0.875 [0.852, 0.899] | 0.625 [0.611, 0.639] | 1.869 [1.534, 2.277] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast20 | 0.779 [0.721, 0.843] | 0.611 [0.586, 0.637] | 2.204 [1.713, 2.837] |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-zstd | 1.338 [1.236, 1.448] | 0.846 [0.841, 0.851] | 4.592 [4.019, 5.247] |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-lz4 | 1.406 [1.282, 1.542] | 0.831 [0.823, 0.839] | 5.267 [4.280, 6.483] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-lz4 | rsync-zstd | xs-z1 | xs-zfast1 | xs-zfast20 | xs-zfast5 |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | 54.069 | 50.073 | 15.594 | 20.336 | 19.174 | 17.414 |
| `large-half.fresh.mars-mac.receiver.warm` | 36.216 | 32.810 | 9.405 | 12.788 | 12.574 | 11.657 |
| `large-text.fresh.mac-mars.sender.warm` | 63.163 | 55.538 | 12.749 | 16.669 | 15.740 | 15.607 |
| `large-text.fresh.mars-mac.receiver.warm` | 28.490 | 24.848 | 5.464 | 8.845 | 11.971 | 10.168 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast1 | 0.2258 | 460 | 616 |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast5 | 0.1474 | 198 | 264 |
| `large-half.fresh.mac-mars.sender.warm` | xs-zfast20 | 0.2372 | 507 | 679 |
| `large-half.fresh.mac-mars.sender.warm` | rsync-zstd | 0.2508 | 567 | 759 |
| `large-half.fresh.mac-mars.sender.warm` | rsync-lz4 | 0.2488 | 558 | 747 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast1 | 0.2475 | 552 | 739 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast5 | 0.0847 | 67 | 89 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-zfast20 | 0.0662 | 42 | 55 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-zstd | 0.1216 | 135 | 180 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-lz4 | 0.1691 | 259 | 347 |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast1 | 0.2280 | 469 | 628 |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast5 | 0.2650 | 632 | 847 |
| `large-text.fresh.mac-mars.sender.warm` | xs-zfast20 | 0.1553 | 219 | 293 |
| `large-text.fresh.mac-mars.sender.warm` | rsync-zstd | 0.1040 | 100 | 133 |
| `large-text.fresh.mac-mars.sender.warm` | rsync-lz4 | 0.0750 | 53 | 70 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast1 | 0.2732 | 672 | 900 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast5 | 0.1896 | 325 | 435 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-zfast20 | 0.2412 | 524 | 702 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-zstd | 0.1267 | 147 | 196 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-lz4 | 0.1992 | 359 | 480 |
