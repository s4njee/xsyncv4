# IN1-incremental-real-apollo

rsync is at least 5% faster than xs at some incremental sync of a real tree.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T001815Z-IN1-incremental-real-apollo.
- Valid blocks: 18. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.546 [0.335, 0.889] | 0.551 | 0.2500 | too few blocks |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.493 [0.282, 0.862] | 0.498 | 0.2500 | too few blocks |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.299 [0.188, 0.475] | 0.302 | 0.2500 | too few blocks |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.182 [0.119, 0.279] | 0.186 | 0.2500 | too few blocks |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 3 | 0.185 [0.128, 0.268] | 0.187 | 0.2500 | too few blocks |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.164 [0.115, 0.235] | 0.167 | 0.2500 | too few blocks |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.481 [0.438, 0.528] | 0.482 | 0.2500 | too few blocks |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.401 [0.216, 0.745] | 0.407 | 0.2500 | too few blocks |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.359 [0.204, 0.631] | 0.365 | 0.2500 | too few blocks |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.308 [0.102, 0.930] | 0.296 | 0.2500 | too few blocks |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 3 | 0.177 [0.147, 0.215] | 0.179 | 0.2500 | too few blocks |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.205 [0.080, 0.530] | 0.199 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.575 [0.269, 1.229] | 0.584 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 3 | 0.558 [0.199, 1.565] | 0.543 | 0.2500 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 3 | 0.348 [0.154, 0.784] | 0.334 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 3 | 0.314 [0.224, 0.442] | 0.318 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 3 | 0.206 [0.170, 0.249] | 0.205 | 0.2500 | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 3 | 0.183 [0.165, 0.203] | 0.184 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp | 2.175 [1.819, 2.602] | 1.992 [1.865, 2.128] | 0.538 [0.328, 0.882] |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 3.020 [2.432, 3.750] | 2.145 [1.972, 2.333] | 0.483 [0.273, 0.853] |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-rs | 1.246 [1.113, 1.395] | 4.973 [4.328, 5.713] | 0.285 [0.176, 0.463] |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp | 0.989 [0.899, 1.088] | 2.251 [2.011, 2.518] | 0.182 [0.119, 0.278] |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.445 [1.389, 1.504] | 2.478 [2.149, 2.857] | 0.183 [0.123, 0.272] |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-rs | 1.194 [1.069, 1.333] | 5.946 [5.213, 6.783] | 0.163 [0.114, 0.234] |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 1.145 [0.949, 1.380] | 4.410 [4.387, 4.434] | 0.480 [0.420, 0.547] |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.391 [0.676, 2.865] | 4.443 [4.350, 4.539] | 0.398 [0.208, 0.762] |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.860 [0.520, 1.422] | 4.685 [4.628, 4.743] | 0.355 [0.199, 0.635] |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.801 [0.645, 0.994] | 2.952 [2.492, 3.497] | 0.264 [0.159, 0.439] |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.096 [0.935, 1.285] | 3.147 [1.815, 5.455] | 0.171 [0.136, 0.216] |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.910 [0.708, 1.171] | 5.094 [4.649, 5.582] | 0.163 [0.120, 0.222] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.587 [0.968, 2.603] | 1.984 [1.753, 2.244] | 0.567 [0.264, 1.219] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.742 [0.901, 3.366] | 3.792 [0.960, 14.981] | 0.551 [0.191, 1.590] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.024 [0.593, 1.769] | 4.931 [4.152, 5.855] | 0.336 [0.147, 0.768] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.877 [0.815, 0.942] | 3.000 [2.877, 3.127] | 0.312 [0.221, 0.442] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 1.211 [1.082, 1.355] | 2.765 [2.508, 3.049] | 0.197 [0.156, 0.249] |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.941 [0.708, 1.251] | 5.698 [5.405, 6.008] | 0.180 [0.163, 0.200] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j8 | xs-rs |
|---|---|---|---|---|
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | 4.570 | 2.496 | 2.252 | 1.366 |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | 7.085 | 1.291 | 1.314 | 1.163 |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | 15.428 | 7.420 | 6.183 | 5.532 |
| `real-congress.update-10pct.mac-apollo.sender.warm` | 11.088 | 3.414 | 1.968 | 2.278 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | 5.897 | 3.389 | 3.293 | 2.052 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | 7.713 | 2.424 | 1.586 | 1.412 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp | 0.1964 | 349 | 466 |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.2253 | 458 | 613 |
| `real-congress.update-0p1pct.apollo-mac.receiver.warm` | xs-rs | 0.1864 | 314 | 420 |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp | 0.1713 | 266 | 355 |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 0.1481 | 199 | 266 |
| `real-congress.update-0p1pct.mac-apollo.sender.warm` | xs-rs | 0.1443 | 189 | 253 |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.0372 | 15 | 19 |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.2496 | 562 | 752 |
| `real-congress.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.2274 | 467 | 625 |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp | 0.4450 | 1780 | 2384 |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-cpp-j8 | 0.0763 | 55 | 73 |
| `real-congress.update-10pct.mac-apollo.sender.warm` | xs-rs | 0.3812 | 1307 | 1750 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.3060 | 843 | 1128 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp-j8 | 0.4149 | 1547 | 2073 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.3271 | 963 | 1289 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.1369 | 171 | 228 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp-j8 | 0.0765 | 55 | 73 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.0422 | 19 | 24 |
