# NT1021-fresh

xs-rs at aa7aee150987 differs from xs-c++ at fe012667764a by more than 5% in time-to-durable.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T165635Z-NT1021-fresh.
- Valid blocks: 40. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 5 | 1.387 [0.789, 2.440] | 1.533 | 0.1875 | too few blocks |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-rs | 5 | 0.822 [0.653, 1.035] | 0.815 | 0.0625 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 5 | 2.274 [2.123, 2.435] | 2.273 | 0.0625 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-rs | 5 | 0.664 [0.626, 0.705] | 0.665 | 0.0625 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 5 | 1.348 [1.290, 1.409] | 1.357 | 0.0625 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-rs | 5 | 0.452 [0.425, 0.480] | 0.450 | 0.0625 | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 5 | 1.866 [1.333, 2.612] | 1.723 | 0.0625 | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-rs | 5 | 0.580 [0.473, 0.712] | 0.557 | 0.0625 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 5 | 1.108 [1.043, 1.177] | 1.103 | 0.0625 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | xs-rs | 5 | 0.409 [0.395, 0.424] | 0.413 | 0.0625 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 5 | 1.113 [1.003, 1.236] | 1.080 | 0.0625 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-rs | 5 | 0.460 [0.393, 0.539] | 0.446 | 0.0625 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 5 | 1.269 [1.201, 1.340] | 1.252 | 0.0625 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | xs-rs | 5 | 0.491 [0.463, 0.521] | 0.490 | 0.0625 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 5 | 1.511 [1.409, 1.621] | 1.515 | 0.0625 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-rs | 5 | 0.535 [0.505, 0.567] | 0.537 | 0.0625 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.334 [1.230, 1.447] | 0.052 [0.049, 0.054] | 1.403 [0.789, 2.495] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-rs | 0.993 [0.896, 1.100] | 1.065 [1.000, 1.134] | 0.811 [0.630, 1.044] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.509 [1.423, 1.600] | 0.612 [0.552, 0.678] | 2.302 [2.135, 2.482] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-rs | 1.104 [1.066, 1.144] | 1.110 [1.032, 1.194] | 0.657 [0.618, 0.699] |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 1.231 [1.199, 1.264] | 0.145 [0.142, 0.148] | 1.360 [1.309, 1.414] |
| `real-congress.fresh.mac-mars.sender.warm` | xs-rs | 0.987 [0.939, 1.037] | 0.867 [0.664, 1.132] | 0.441 [0.418, 0.465] |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 1.721 [1.332, 2.223] | 0.718 [0.652, 0.791] | 1.873 [1.341, 2.617] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-rs | 1.265 [1.098, 1.458] | 0.892 [0.763, 1.043] | 0.570 [0.466, 0.698] |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 1.110 [1.068, 1.153] | 0.221 [0.203, 0.241] | 1.110 [1.052, 1.172] |
| `small-deep.fresh.mac-mars.sender.warm` | xs-rs | 0.703 [0.696, 0.709] | 0.842 [0.765, 0.926] | 0.396 [0.380, 0.414] |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.909 [0.882, 0.938] | 0.733 [0.564, 0.952] | 1.111 [1.001, 1.234] |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-rs | 0.549 [0.522, 0.577] | 1.347 [1.221, 1.487] | 0.452 [0.381, 0.536] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 1.185 [1.099, 1.277] | 0.063 [0.059, 0.067] | 1.282 [1.201, 1.367] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-rs | 1.264 [1.239, 1.290] | 0.748 [0.688, 0.814] | 0.485 [0.460, 0.511] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.406 [1.347, 1.467] | 1.196 [1.125, 1.271] | 1.523 [1.419, 1.634] |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-rs | 1.518 [1.453, 1.587] | 1.058 [0.972, 1.152] | 0.530 [0.502, 0.560] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 7.306 | 5.266 | 4.330 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 9.391 | 4.130 | 2.744 |
| `real-congress.fresh.mac-mars.sender.warm` | 43.938 | 32.594 | 14.723 |
| `real-congress.fresh.mars-mac.receiver.warm` | 81.499 | 43.675 | 25.333 |
| `small-deep.fresh.mac-mars.sender.warm` | 26.643 | 24.037 | 9.840 |
| `small-deep.fresh.mars-mac.receiver.warm` | 48.050 | 43.172 | 19.878 |
| `small-flat.fresh.mac-mars.sender.warm` | 16.877 | 13.302 | 6.528 |
| `small-flat.fresh.mars-mac.receiver.warm` | 25.826 | 17.087 | 9.141 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.4545 | 1856 | 2487 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-rs | 0.1856 | 312 | 417 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.0552 | 30 | 39 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | xs-rs | 0.0479 | 23 | 30 |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 0.0356 | 14 | 18 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-rs | 0.0486 | 24 | 31 |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 0.2708 | 660 | 884 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-rs | 0.1647 | 246 | 329 |
| `small-deep.fresh.mac-mars.sender.warm` | rsync | 0.0487 | 24 | 31 |
| `small-deep.fresh.mac-mars.sender.warm` | xs-rs | 0.0285 | 10 | 12 |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.0841 | 66 | 88 |
| `small-deep.fresh.mars-mac.receiver.warm` | xs-rs | 0.1269 | 147 | 196 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.0443 | 20 | 26 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-rs | 0.0476 | 23 | 30 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.0564 | 31 | 41 |
| `small-flat.fresh.mars-mac.receiver.warm` | xs-rs | 0.0472 | 22 | 29 |
