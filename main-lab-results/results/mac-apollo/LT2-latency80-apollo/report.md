# LT2-latency80-apollo

Over a 80 ms round trip, rsync is at least 5% faster than xs in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T182522Z-LT2-latency80-apollo.
- Valid blocks: 14. Voided block attempts: 9.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.676 |  |  | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 1 | 0.636 |  |  | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1 | 0.679 |  |  | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 1 | 0.636 |  |  | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.755 [0.691, 0.825] | 0.755 | 0.5000 | too few blocks |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 0.732 [0.613, 0.874] | 0.732 | 0.5000 | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.891 |  |  | too few blocks |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 1 | 0.713 |  |  | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.632 [0.369, 1.080] | 0.632 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 0.629 [0.373, 1.058] | 0.629 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 1 | 0.886 |  |  | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1 | 0.354 |  |  | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 2 | 0.153 [0.146, 0.161] | 0.153 | 0.5000 | too few blocks |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 2 | 0.109 [0.096, 0.123] | 0.109 | 0.5000 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 2 | 0.102 [0.072, 0.145] | 0.102 | 0.5000 | too few blocks |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 2 | 0.079 [0.047, 0.134] | 0.079 | 0.5000 | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1 | 0.148 |  |  | too few blocks |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1 | 0.105 |  |  | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 1 | 0.088 |  |  | too few blocks |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 1 | 0.081 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1.299 | 1.008 | 0.665 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.694 | 1.016 | 0.627 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.757 | 1.052 | 0.678 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.703 | 1.290 | 0.621 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.394 [0.626, 3.103] | 1.172 [0.919, 1.495] | 0.742 [0.560, 0.985] |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.887 [0.713, 1.104] | 1.689 [0.948, 3.009] | 0.728 [0.597, 0.887] |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.850 | 1.520 | 0.891 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.829 | 2.335 | 0.713 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.686 [0.462, 1.021] | 0.834 [0.147, 4.748] | 0.631 [0.360, 1.105] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.791 [0.461, 1.358] | 1.922 [0.444, 8.313] | 0.626 [0.373, 1.054] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.710 | 13.360 | 0.884 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.043 | 8.447 | 0.151 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 1.210 [0.789, 1.854] | 2.097 [1.237, 3.554] | 0.151 [0.138, 0.165] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.653 [0.625, 0.682] | 5.655 [3.765, 8.492] | 0.107 [0.105, 0.108] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.627 [0.201, 1.956] | 4.341 [1.353, 13.922] | 0.102 [0.072, 0.144] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.751 [0.693, 0.814] | 9.289 [3.560, 24.237] | 0.079 [0.047, 0.134] |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.164 | 1.800 | 0.146 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.666 | 4.582 | 0.102 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.563 | 3.381 | 0.087 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.669 | 5.842 | 0.071 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `local-laikav2.noop.apollo-mac.receiver.warm` | 2.871 | 1.940 | 1.825 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 2.884 | 1.959 | 1.833 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | 3.279 | 2.476 | 2.400 |
| `local-laikav2.update-1pct.mac-apollo.sender.warm` | 3.241 | 2.886 | 2.312 |
| `real-congress.fresh.apollo-mac.receiver.warm` | 80.589 | 50.892 | 50.655 |
| `real-congress.fresh.mac-apollo.sender.warm` | 56.060 | 49.653 | 19.844 |
| `real-congress.noop.apollo-mac.receiver.warm` | 26.340 | 4.036 | 2.859 |
| `real-congress.noop.mac-apollo.sender.warm` | 31.161 | 3.186 | 2.471 |
| `real-congress.update-1pct.apollo-mac.receiver.warm` | 30.043 | 4.445 | 3.141 |
| `real-congress.update-1pct.mac-apollo.sender.warm` | 35.140 | 3.076 | 2.838 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0099 | 8 | 8 |
| `local-laikav2.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0198 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0597 | 34 | 45 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0580 | 33 | 43 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0055 | 8 | 8 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.0135 | 8 | 8 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.0387 | 16 | 21 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.0581 | 33 | 43 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
- xs-cpp: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/0
- xs-rs: the destination does not match the corpus manifest: DIFFERS target/debug/incremental/mkit-1kamvep3e62m2/s-hng3ehopvi-1j46563-4fx46mu2g6x7f7kuko4hg7nkg/00
