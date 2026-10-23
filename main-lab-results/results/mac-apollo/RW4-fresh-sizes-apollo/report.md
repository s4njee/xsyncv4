# RW4-fresh-sizes-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Fresh copies of 1 MiB and 16 MiB files and of mixed-threshold, around xs's whole-file and split thresholds; -j1 arms as in RW3.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162411Z-RW4-fresh-sizes-apollo, 20261023T040631Z-RW4-fresh-sizes-apollo.
- Valid blocks: 18. Voided block attempts: 27.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.453 [0.424, 0.485] | 0.454 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.460 [0.419, 0.506] | 0.462 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.439 [0.406, 0.475] | 0.440 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.437 [0.402, 0.474] | 0.437 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 2.271 [1.416, 3.643] | 2.323 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 0.461 [0.416, 0.510] | 0.459 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.465 [0.445, 0.486] | 0.465 | 0.2500 | too few blocks |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.481 [0.409, 0.564] | 0.481 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.583 [0.529, 0.643] | 0.586 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.584 [0.488, 0.700] | 0.587 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.562 [0.450, 0.701] | 0.568 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.612 [0.481, 0.779] | 0.618 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.451 [0.249, 0.818] | 0.465 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 1.466 [0.152, 14.183] | 1.639 | 0.5000 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.439 [0.220, 0.878] | 0.456 | 0.2500 | too few blocks |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 1.928 [0.106, 35.199] | 2.186 | 0.5000 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.617 [0.235, 1.618] | 0.591 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.521 [0.445, 0.611] | 0.520 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 3 | 0.497 [0.468, 0.527] | 0.498 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.524 [0.429, 0.641] | 0.524 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.307 [0.149, 0.632] | 0.298 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 3 | 0.296 [0.024, 3.640] | 0.266 | 0.2500 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.542 [0.058, 5.021] | 0.601 | 0.5000 | too few blocks |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 3 | 0.212 [0.072, 0.619] | 0.220 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.736 [0.636, 0.851] | 0.613 [0.371, 1.013] | 0.442 [0.411, 0.476] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.687 [0.546, 0.863] | 0.539 [0.329, 0.883] | 0.447 [0.400, 0.500] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.399 [0.353, 0.451] | 0.881 [0.812, 0.955] | 0.426 [0.391, 0.465] |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.320 [0.259, 0.395] | 0.743 [0.713, 0.774] | 0.425 [0.388, 0.466] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 0.646 [0.559, 0.746] | 10.905 [9.246, 12.862] | 0.426 [0.398, 0.457] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.631 [0.599, 0.664] | 13.340 [12.738, 13.969] | 0.424 [0.396, 0.454] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 0.342 [0.327, 0.357] | 16.854 [16.381, 17.342] | 0.413 [0.399, 0.429] |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.291 [0.264, 0.319] | 15.595 [10.387, 23.413] | 0.419 [0.398, 0.442] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.740 [0.719, 0.762] | 0.480 [0.377, 0.610] | 0.546 [0.493, 0.604] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.615 [0.552, 0.687] | 0.541 [0.299, 0.978] | 0.545 [0.444, 0.670] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 0.397 [0.357, 0.441] | 0.738 [0.649, 0.839] | 0.525 [0.416, 0.663] |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.336 [0.295, 0.382] | 0.689 [0.532, 0.892] | 0.559 [0.421, 0.741] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 0.729 [0.669, 0.794] | 8.058 [6.887, 9.429] | 0.500 [0.453, 0.552] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.661 [0.640, 0.682] | 9.872 [7.953, 12.255] | 0.499 [0.436, 0.570] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 0.435 [0.427, 0.443] | 11.804 [10.347, 13.466] | 0.474 [0.434, 0.517] |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.344 [0.331, 0.357] | 10.879 [7.725, 15.322] | 0.517 [0.456, 0.587] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.630 [0.589, 0.675] | 0.531 [0.448, 0.630] | 0.473 [0.403, 0.556] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.589 [0.566, 0.612] | 0.576 [0.389, 0.852] | 0.479 [0.397, 0.579] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 0.322 [0.273, 0.380] | 0.502 [0.496, 0.508] | 0.460 [0.443, 0.478] |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.268 [0.246, 0.293] | 0.434 [0.412, 0.458] | 0.487 [0.397, 0.599] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 0.712 [0.664, 0.763] | 7.490 [6.486, 8.649] | 0.472 [0.375, 0.595] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.661 [0.626, 0.699] | 9.526 [6.692, 13.560] | 0.472 [0.393, 0.568] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 0.501 [0.365, 0.687] | 9.799 [8.204, 11.704] | 0.426 [0.318, 0.572] |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.325 [0.275, 0.384] | 10.529 [8.068, 13.742] | 0.488 [0.428, 0.556] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-rs | xs-rs-j1 |
|---|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | 3.566 | 1.617 | 1.642 | 1.566 | 1.557 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | 3.739 | 8.492 | 1.723 | 1.739 | 1.797 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | 0.863 | 0.503 | 0.504 | 0.485 | 0.529 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | 1.073 | 0.484 | 1.574 | 0.472 | 2.070 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | 1.001 | 0.618 | 0.522 | 0.497 | 0.525 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | 2.760 | 0.848 | 0.816 | 1.494 | 0.584 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0268 | 9 | 11 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0378 | 15 | 20 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0317 | 12 | 15 |
| `mixed-threshold.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0328 | 12 | 15 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp | 0.1902 | 327 | 437 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.0409 | 17 | 23 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs | 0.0175 | 8 | 8 |
| `mixed-threshold.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.0647 | 40 | 53 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0390 | 16 | 21 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0727 | 50 | 66 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0892 | 74 | 98 |
| `scale-size-1048576.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0969 | 87 | 115 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp | 0.2395 | 517 | 692 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 0.9135 | 7491 | 10038 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs | 0.2788 | 700 | 937 |
| `scale-size-1048576.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 1.1692 | 12268 | 16441 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.3880 | 1354 | 1813 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0640 | 39 | 52 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0239 | 8 | 9 |
| `scale-size-16777216.fresh.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0808 | 61 | 81 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp | 0.2903 | 759 | 1016 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-cpp-j1 | 1.0106 | 9166 | 12284 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs | 0.8965 | 7215 | 9669 |
| `scale-size-16777216.fresh.mac-apollo.sender.warm` | xs-rs-j1 | 0.4324 | 1680 | 2251 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
