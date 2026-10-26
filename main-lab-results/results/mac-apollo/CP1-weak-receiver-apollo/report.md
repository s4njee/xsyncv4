# CP1-weak-receiver-apollo

With the receiver held to 2 cores, rsync is at least 5% faster than xs in some cell, or fewer xs workers are faster than the default.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261025T111624Z-CP1-weak-receiver-apollo.
- Valid blocks: 9. Voided block attempts: 9.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.553 [0.487, 0.627] | 0.556 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 3 | 0.565 [0.529, 0.605] | 0.565 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.497 [0.338, 0.730] | 0.487 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j2 | 3 | 0.520 [0.511, 0.528] | 0.520 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 0.355 [0.110, 1.139] | 0.359 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 3 | 0.373 [0.197, 0.708] | 0.360 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.380 [0.158, 0.914] | 0.398 | 0.2500 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 3 | 0.394 [0.110, 1.419] | 0.378 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.215 [0.189, 0.245] | 0.214 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 3 | 0.300 [0.250, 0.361] | 0.298 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 3 | 0.203 [0.150, 0.274] | 0.206 | 0.2500 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j2 | 3 | 0.297 [0.258, 0.342] | 0.296 | 0.2500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1.125 [1.075, 1.177] | 0.993 [0.948, 1.041] | 0.546 [0.498, 0.599] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 0.895 [0.850, 0.942] | 1.007 [0.995, 1.020] | 0.562 [0.508, 0.622] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 1.165 [0.747, 1.819] | 1.011 [0.995, 1.026] | 0.491 [0.319, 0.756] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j2 | 0.722 [0.642, 0.811] | 0.998 [0.941, 1.058] | 0.513 [0.488, 0.539] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.764 [0.735, 0.795] | 7.693 [6.176, 9.584] | 0.215 [0.206, 0.224] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.626 [0.592, 0.662] | 5.050 [3.763, 6.776] | 0.299 [0.251, 0.356] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.161 [1.101, 1.224] | 6.396 [4.967, 8.235] | 0.224 [0.196, 0.256] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.525 [0.468, 0.588] | 6.120 [5.664, 6.614] | 0.284 [0.169, 0.479] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 1.084 [1.005, 1.169] | 2.921 [2.797, 3.050] | 0.215 [0.188, 0.246] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 0.908 [0.823, 1.002] | 2.696 [2.645, 2.748] | 0.300 [0.250, 0.360] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.443 [1.104, 1.885] | 7.915 [7.566, 8.281] | 0.203 [0.150, 0.274] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j2 | 0.777 [0.725, 0.833] | 7.922 [7.667, 8.185] | 0.297 [0.257, 0.343] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-j2 | xs-rs | xs-rs-j2 |
|---|---|---|---|---|---|
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.369 | 0.204 | 0.209 | 0.183 | 0.192 |
| `real-congress.fresh.mac-apollo.sender.warm` | 27.620 | 9.794 | 10.304 | 10.494 | 10.891 |
| `real-congress.noop.mac-apollo.sender.warm` | 5.683 | 1.223 | 1.707 | 1.153 | 1.688 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.0510 | 26 | 34 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 0.0272 | 9 | 11 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.1550 | 218 | 291 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs-j2 | 0.0067 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.4698 | 1983 | 2657 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp-j2 | 0.2577 | 599 | 801 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.3534 | 1123 | 1505 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-j2 | 0.5155 | 2387 | 3198 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.0522 | 27 | 35 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp-j2 | 0.0740 | 52 | 68 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.1211 | 134 | 179 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs-j2 | 0.0573 | 32 | 42 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp-j2: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nk
- xs-rs-j2: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
