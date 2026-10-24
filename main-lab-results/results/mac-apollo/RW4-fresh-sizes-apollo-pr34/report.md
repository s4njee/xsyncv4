# RW4-fresh-sizes-apollo-pr34

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Fresh copies of 1 MiB and 16 MiB files and of mixed-threshold, around xs's whole-file and split thresholds; -j1 arms as in RW3.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T092442Z-RW4-fresh-sizes-apollo-pr34.
- Valid blocks: 18. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.354 [0.222, 0.565] | 0.361 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.361 [0.209, 0.622] | 0.368 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.404 [0.218, 0.748] | 0.409 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.395 [0.166, 0.941] | 0.390 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.272 [0.042, 1.752] | 0.249 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 0.232 [0.056, 0.964] | 0.219 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.224 [0.057, 0.879] | 0.208 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.145 [0.127, 0.165] | 0.145 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.523 [0.358, 0.764] | 0.530 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.551 [0.388, 0.783] | 0.559 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.521 [0.432, 0.629] | 0.521 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.553 [0.463, 0.662] | 0.551 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.463 [0.377, 0.568] | 0.469 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 0.714 [0.070, 7.295] | 0.629 | 0.5000 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.980 [0.131, 7.312] | 1.045 | 1.0000 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.691 [0.086, 5.542] | 0.618 | 0.5000 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.451 [0.399, 0.510] | 0.451 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.466 [0.415, 0.523] | 0.468 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.461 [0.431, 0.492] | 0.461 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.431 [0.332, 0.560] | 0.426 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.576 [0.200, 1.654] | 0.563 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 0.593 [0.030, 11.711] | 0.549 | 0.5000 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.772 [0.142, 4.200] | 0.817 | 0.7500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.563 [0.178, 1.783] | 0.545 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.643 [0.496, 0.834] | 0.670 [0.604, 0.743] | 0.343 [0.212, 0.555] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.592 [0.466, 0.751] | 0.718 [0.678, 0.760] | 0.350 [0.199, 0.614] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.444 [0.326, 0.604] | 1.018 [0.936, 1.107] | 0.392 [0.207, 0.744] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.291 [0.196, 0.433] | 0.775 [0.730, 0.822] | 0.384 [0.158, 0.935] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 0.603 [0.580, 0.627] | 9.958 [9.332, 10.626] | 0.372 [0.305, 0.454] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.563 [0.526, 0.602] | 8.847 [7.147, 10.950] | 0.373 [0.337, 0.414] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 0.331 [0.283, 0.388] | 16.825 [15.509, 18.253] | 0.376 [0.319, 0.443] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.239 [0.213, 0.269] | 12.339 [10.360, 14.697] | 0.347 [0.314, 0.385] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.688 [0.529, 0.894] | 0.606 [0.353, 1.042] | 0.485 [0.333, 0.704] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.636 [0.520, 0.779] | 0.705 [0.636, 0.781] | 0.515 [0.352, 0.754] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 0.434 [0.408, 0.462] | 0.694 [0.670, 0.719] | 0.476 [0.400, 0.567] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.326 [0.282, 0.376] | 0.614 [0.424, 0.891] | 0.507 [0.427, 0.603] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 0.615 [0.501, 0.753] | 8.168 [7.645, 8.727] | 0.449 [0.385, 0.525] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.567 [0.465, 0.691] | 7.375 [5.816, 9.353] | 0.442 [0.336, 0.582] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 0.758 [0.217, 2.652] | 16.447 [8.403, 32.192] | 0.401 [0.310, 0.519] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.282 [0.219, 0.363] | 9.257 [7.579, 11.306] | 0.435 [0.374, 0.505] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.583 [0.497, 0.684] | 0.635 [0.466, 0.866] | 0.413 [0.350, 0.487] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.563 [0.509, 0.622] | 0.677 [0.529, 0.866] | 0.433 [0.375, 0.499] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 0.352 [0.308, 0.402] | 0.536 [0.530, 0.541] | 0.422 [0.372, 0.478] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.222 [0.201, 0.244] | 0.432 [0.427, 0.438] | 0.395 [0.299, 0.522] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 0.585 [0.530, 0.645] | 7.531 [6.600, 8.594] | 0.443 [0.333, 0.590] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.579 [0.541, 0.620] | 7.662 [6.171, 9.514] | 0.449 [0.394, 0.511] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 0.625 [0.307, 1.270] | 8.293 [5.246, 13.108] | 0.383 [0.240, 0.613] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.256 [0.234, 0.280] | 6.786 [4.977, 9.253] | 0.431 [0.329, 0.564] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-rs | xs-rs-j1 |
|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | 4.832 | 1.711 | 1.743 | 1.952 | 1.908 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | 11.036 | 3.006 | 2.557 | 2.469 | 1.597 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | 1.007 | 0.527 | 0.555 | 0.525 | 0.557 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | 1.010 | 0.468 | 0.721 | 0.990 | 0.698 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | 1.189 | 0.536 | 0.554 | 0.548 | 0.513 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | 1.342 | 0.772 | 0.795 | 1.036 | 0.755 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.1880 | 320 | 427 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.2194 | 434 | 581 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.2480 | 554 | 742 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.3496 | 1099 | 1473 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 0.7492 | 5040 | 6754 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.5739 | 2958 | 3963 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 0.5507 | 2724 | 3650 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.0527 | 27 | 36 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.1525 | 211 | 282 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.1415 | 182 | 243 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0755 | 54 | 71 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0720 | 49 | 65 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 0.0824 | 63 | 84 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.9354 | 7854 | 10525 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 0.8089 | 5873 | 7871 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.8380 | 6304 | 8448 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0496 | 25 | 32 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0468 | 22 | 29 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0263 | 9 | 11 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.1053 | 102 | 136 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 0.4250 | 1623 | 2175 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 1.2009 | 12944 | 17347 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 0.6817 | 4172 | 5591 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.4641 | 1935 | 2593 |
