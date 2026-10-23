# RW6-hardlinks-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Hard links kept with -H, on laikav2 (1,234 linked files in its Rust target folder). xs-rs has no -H, so it sits out.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162412Z-RW6-hardlinks-apollo, 20261023T040632Z-RW6-hardlinks-apollo.
- Valid blocks: 12. Voided block attempts: 18.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.412 [0.391, 0.435] | 0.413 | 0.2500 | too few blocks |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 3 | 1.121 [0.213, 5.915] | 1.152 | 0.7500 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 3 | 0.729 [0.705, 0.753] | 0.730 | 0.2500 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 3 | 0.687 [0.295, 1.601] | 0.657 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.734 [0.657, 0.820] | 0.848 [0.677, 1.062] | 0.410 [0.388, 0.432] |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.698 [0.643, 0.758] | 21.044 [14.430, 30.690] | 0.483 [0.298, 0.782] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 2.055 [1.906, 2.214] | 1.156 [1.083, 1.234] | 0.703 [0.692, 0.715] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1.609 [1.479, 1.750] | 1.001 [0.940, 1.065] | 0.563 [0.533, 0.593] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp |
|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | 18.062 | 7.449 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | 21.588 | 24.204 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.379 | 0.277 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.400 | 0.275 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0212 | 8 | 8 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.6695 | 4025 | 5393 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0134 | 8 | 8 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.3404 | 1042 | 1396 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
