# RW3-noop-many-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. No-ops of many files, where NT1021 saw rsync pull real-psample in 75.7 s against xs-cpp 151.6 s; -j1 arms for a per-core comparison.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162410Z-RW3-noop-many-apollo, 20261023T040631Z-RW3-noop-many-apollo.
- Valid blocks: 9. Voided block attempts: 18.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.756 [0.425, 1.345] | 0.770 | 0.2500 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 1.015 [0.785, 1.313] | 1.017 | 0.7500 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.542 [0.335, 0.878] | 0.550 | 0.2500 | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.914 [0.648, 1.288] | 0.918 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.321 [0.312, 0.329] | 0.321 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 2 | 0.576 [0.344, 0.966] | 0.576 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 2 | 0.255 [0.253, 0.257] | 0.255 | 0.5000 | too few blocks |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 2 | 0.471 [0.393, 0.564] | 0.471 | 0.5000 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.218 [0.176, 0.271] | 0.221 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 3 | 0.511 [0.425, 0.616] | 0.516 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 3 | 0.230 [0.146, 0.364] | 0.233 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 3 | 0.517 [0.461, 0.579] | 0.517 | 0.2500 | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.138 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 1 | 0.649 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 1 | 0.146 |  |  | too few blocks |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 1 | 0.684 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 2.823 [1.338, 5.954] | 4.241 [3.373, 5.332] | 0.756 [0.424, 1.348] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 1.225 [1.099, 1.367] | 4.448 [4.035, 4.904] | 1.015 [0.785, 1.312] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 1.745 [1.548, 1.967] | 9.949 [9.021, 10.973] | 0.542 [0.334, 0.877] |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 1.140 [1.040, 1.249] | 10.417 [8.340, 13.010] | 0.914 [0.648, 1.289] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 1.054 [0.722, 1.539] | 4.297 [4.212, 4.385] | 0.315 [0.294, 0.339] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.635 [0.512, 0.789] | 4.303 [4.126, 4.486] | 0.576 [0.343, 0.969] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 0.851 [0.766, 0.946] | 11.748 [11.375, 12.133] | 0.255 [0.250, 0.260] |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.530 [0.483, 0.581] | 11.838 [11.430, 12.260] | 0.471 [0.392, 0.566] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 0.801 [0.624, 1.028] | 1.050 [0.985, 1.120] | 0.213 [0.171, 0.266] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.520 [0.465, 0.580] | 1.014 [0.956, 1.077] | 0.507 [0.420, 0.613] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 0.826 [0.619, 1.104] | 28.137 [23.559, 33.604] | 0.225 [0.139, 0.364] |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.545 [0.505, 0.588] | 25.207 [24.022, 26.450] | 0.514 [0.457, 0.578] |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp | 0.460 | 0.999 | 0.141 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.674 | 1.009 | 0.664 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs | 0.493 | 21.312 | 0.150 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.671 | 21.343 | 0.703 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j1 | xs-rs | xs-rs-j1 |
|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | 35.697 | 26.995 | 36.241 | 19.362 | 32.622 |
| `real-psample.noop.mac-apollo.sender.warm` | 75.561 | 24.229 | 43.549 | 19.265 | 35.554 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | 15.929 | 3.480 | 8.144 | 3.667 | 8.233 |
| `scale-count-1000000.noop.mac-apollo.sender.warm` | 76.196 | 10.494 | 49.429 | 11.097 | 52.103 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp | 0.2317 | 484 | 648 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.1034 | 98 | 131 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs | 0.1937 | 339 | 454 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.1381 | 174 | 232 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp | 0.0030 | 8 | 8 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-cpp-j1 | 0.0574 | 32 | 42 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs | 0.0008 | 8 | 8 |
| `real-psample.noop.mac-apollo.sender.warm` | xs-rs-j1 | 0.0201 | 8 | 8 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0871 | 71 | 94 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-cpp-j1 | 0.0748 | 53 | 70 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs | 0.1845 | 308 | 412 |
| `scale-count-1000000.noop.apollo-mac.receiver.warm` | xs-rs-j1 | 0.0460 | 21 | 28 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
