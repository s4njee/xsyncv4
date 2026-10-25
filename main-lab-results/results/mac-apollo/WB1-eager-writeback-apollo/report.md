# WB1-eager-writeback-apollo

With eager writeback on apollo, xs reaches durable at least 5% sooner than with default writeback.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T154821Z-WB1-eager-writeback-apollo.
- Valid blocks: 6. Voided block attempts: 9.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 3 | 0.491 [0.135, 1.789] | 0.489 | 0.2500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3 | 0.952 [0.798, 1.136] | 0.951 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync-eager | 3 | 1.060 [0.554, 2.028] | 1.053 | 0.7500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 3 | 0.559 [0.423, 0.738] | 0.567 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 3 | 2.496 [1.503, 4.145] | 2.515 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync-eager | 3 | 2.214 [1.123, 4.365] | 2.270 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 1.003 [0.930, 1.083] | 0.974 [0.794, 1.194] | 0.969 [0.676, 1.388] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1.758 [1.657, 1.865] | 0.117 [0.097, 0.142] | 2.510 [1.743, 3.614] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync-eager | 1.785 [1.568, 2.033] | 0.114 [0.090, 0.143] | 2.595 [2.315, 2.909] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 0.951 [0.853, 1.060] | 0.935 [0.243, 3.603] | 0.871 [0.579, 1.312] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.392 [1.200, 1.615] | 0.180 [0.144, 0.226] | 4.255 [3.346, 5.410] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync-eager | 1.346 [1.112, 1.630] | 0.179 [0.137, 0.235] | 3.799 [3.099, 4.657] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-eager | xs-cpp | xs-cpp-eager |
|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 13.440 | 14.963 | 14.113 | 6.928 |
| `real-congress.fresh.mac-apollo.sender.warm` | 40.392 | 35.820 | 16.182 | 9.045 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 0.5205 | 2433 | 3261 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.0709 | 48 | 63 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync-eager | 0.2612 | 615 | 823 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-eager | 0.1119 | 115 | 153 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.2041 | 376 | 504 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync-eager | 0.2733 | 673 | 901 |

## Voided attempts

- rsync-eager: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7
- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp-eager: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg
- xs-cpp: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/0
