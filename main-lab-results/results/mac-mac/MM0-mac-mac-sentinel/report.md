# MM0-mac-mac-sentinel

Hour by hour, the A/A ratio stays within 5% of 1 and the xs to rsync ratio stays where MM1 put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T133437Z-MM0-mac-mac-sentinel-s0001, 20261021T140437Z-MM0-mac-mac-sentinel-s0001.
- Valid blocks: 32. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 4 | 1.248 [0.564, 2.761] | 1.248 | 0.3750 | too few blocks |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 4 | 2.039 [1.299, 3.200] | 2.168 | 0.1250 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 4 | 1.040 [0.968, 1.118] | 1.040 | 0.2500 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 4 | 2.527 [2.200, 2.902] | 2.527 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 4 | 0.938 [0.686, 1.283] | 0.938 | 0.6250 | too few blocks |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 4 | 1.433 [1.116, 1.841] | 1.433 | 0.1250 | too few blocks |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 4 | 1.006 [0.952, 1.062] | 1.012 | 0.8750 | too few blocks |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 4 | 1.250 [1.113, 1.405] | 1.250 | 0.1250 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | again | 4 | 0.982 [0.905, 1.066] | 0.995 | 0.7500 | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 4 | 1.344 [1.170, 1.544] | 1.344 | 0.1250 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 4 | 1.006 [0.788, 1.285] | 1.019 | 1.0000 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 4 | 1.455 [1.126, 1.880] | 1.548 | 0.1250 | too few blocks |
| `small-flat.noop.mac-mars.sender.warm` | again | 4 | 1.153 [0.707, 1.879] | 1.109 | 0.6250 | too few blocks |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 4 | 2.204 [1.505, 3.226] | 2.204 | 0.1250 | too few blocks |
| `small-flat.noop.mars-mac.receiver.warm` | again | 4 | 1.006 [0.670, 1.511] | 0.961 | 1.0000 | too few blocks |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 4 | 1.881 [1.438, 2.460] | 1.881 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 0.980 [0.939, 1.023] | 1.242 [0.573, 2.694] | 0.998 [0.868, 1.148] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.314 [1.219, 1.416] | 2.009 [1.297, 3.111] | 0.049 [0.043, 0.057] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 1.019 [0.964, 1.077] | 1.041 [0.968, 1.119] | 1.001 [0.949, 1.057] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.332 [1.200, 1.479] | 2.494 [2.185, 2.845] | 0.652 [0.610, 0.698] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.975 [0.906, 1.051] | 1.005 [0.832, 1.214] | 0.962 [0.909, 1.019] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.579 [0.445, 0.754] | 1.319 [1.039, 1.674] | 0.604 [0.567, 0.644] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 1.159 [0.859, 1.563] | 1.018 [0.961, 1.079] | 0.985 [0.914, 1.061] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.314 [0.262, 0.376] | 1.222 [1.124, 1.329] | 0.389 [0.372, 0.406] |
| `small-flat.fresh.mac-mars.sender.warm` | again | 1.012 [0.984, 1.042] | 0.979 [0.897, 1.069] | 1.021 [0.902, 1.157] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 1.012 [0.967, 1.059] | 1.337 [1.169, 1.529] | 0.057 [0.051, 0.064] |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 1.015 [0.906, 1.138] | 1.007 [0.790, 1.284] | 1.082 [0.956, 1.224] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.106 [0.868, 1.410] | 1.443 [1.129, 1.844] | 1.056 [0.933, 1.195] |
| `small-flat.noop.mac-mars.sender.warm` | again | 1.310 [0.700, 2.451] | 1.111 [0.717, 1.722] | 0.947 [0.710, 1.263] |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.487 [0.360, 0.659] | 2.005 [1.447, 2.779] | 0.421 [0.347, 0.510] |
| `small-flat.noop.mars-mac.receiver.warm` | again | 1.062 [1.007, 1.121] | 0.975 [0.667, 1.426] | 0.999 [0.970, 1.029] |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.367 [0.302, 0.447] | 1.754 [1.403, 2.194] | 0.260 [0.253, 0.269] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 4.897 | 8.001 | 3.925 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 4.665 | 11.333 | 4.485 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.260 | 0.398 | 0.278 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | 0.310 | 0.385 | 0.308 |
| `small-flat.fresh.mac-mars.sender.warm` | 13.187 | 18.051 | 13.427 |
| `small-flat.fresh.mars-mac.receiver.warm` | 18.319 | 26.484 | 18.205 |
| `small-flat.noop.mac-mars.sender.warm` | 0.648 | 1.239 | 0.562 |
| `small-flat.noop.mars-mac.receiver.warm` | 0.730 | 1.366 | 0.726 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 0.4992 | 2239 | 3000 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.2833 | 723 | 968 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 0.0453 | 21 | 27 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.0870 | 70 | 93 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.1968 | 350 | 468 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.1573 | 225 | 300 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 0.0343 | 13 | 17 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.0733 | 51 | 67 |
| `small-flat.fresh.mac-mars.sender.warm` | again | 0.0515 | 26 | 34 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.0870 | 70 | 94 |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 0.1538 | 215 | 287 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.1612 | 236 | 315 |
| `small-flat.noop.mac-mars.sender.warm` | again | 0.3070 | 848 | 1136 |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.2395 | 517 | 693 |
| `small-flat.noop.mars-mac.receiver.warm` | again | 0.2554 | 588 | 787 |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.1687 | 258 | 345 |
