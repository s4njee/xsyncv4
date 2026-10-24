# RW6b-hardlinks-apollo

rsync is at least 5% faster to durable than xs-c++ or xs-rs in some cell. Hard links kept with -H, on laikav2 (1,234 linked files in its Rust target folder). xs-rs has no -H, so it sits out.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T023910Z-RW6b-hardlinks-apollo.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 6 | 0.385 [0.359, 0.413] | 0.387 [0.344, 0.422] | 0.0312 | too few blocks |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 6 | 0.649 [0.450, 0.937] | 0.612 [0.431, 1.249] | 0.0625 | too few blocks |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 6 | 0.929 [0.542, 1.592] | 0.954 [0.440, 1.623] | 0.7188 | too few blocks |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 6 | 0.502 [0.400, 0.631] | 0.508 [0.343, 0.648] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.699 [0.667, 0.733] | 0.764 [0.733, 0.797] | 0.382 [0.356, 0.409] |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.612 [0.563, 0.665] | 10.524 [3.682, 30.084] | 0.360 [0.334, 0.388] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 2.060 [1.859, 2.284] | 1.150 [1.138, 1.163] | 0.891 [0.487, 1.629] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1.460 [1.339, 1.592] | 1.008 [0.984, 1.033] | 0.499 [0.396, 0.628] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp |
|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | 21.696 | 8.357 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | 26.408 | 17.145 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.474 | 0.441 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.456 | 0.229 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0668 | 43 | 56 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3496 | 1099 | 1473 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 0.5137 | 2370 | 3176 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.2179 | 429 | 574 |
