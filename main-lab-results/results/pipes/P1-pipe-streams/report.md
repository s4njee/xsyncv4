# P1-pipe-streams

Plain tar streams, compressed or cut into several at once, copy small trees onto NVMe faster than xs.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T210940Z-P1-pipe-streams.
- Valid blocks: 4. Voided block attempts: 2.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | xs | 2 | 0.978 [0.193, 4.964] | 0.978 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | tar | 2 | 8.434 [0.182, 390.373] | 8.434 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | tar-zstd | 2 | 5.613 [2.150, 14.653] | 5.613 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x4 | 2 | 3.887 [0.240, 63.030] | 3.887 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x8 | 2 | 1.989 [0.193, 20.559] | 1.989 | 0.5000 | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 1 | 1.508 |  |  | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | tar | 1 | 2.879 |  |  | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | tar-zstd | 1 | 2.752 |  |  | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | tar-x4 | 1 | 1.466 |  |  | too few blocks |
| `small-deep.fresh.mac-mars.sender.warm` | tar-x8 | 1 | 1.385 |  |  | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 1 | 1.093 |  |  | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | tar | 1 | 6.681 |  |  | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | tar-zstd | 1 | 5.686 |  |  | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | tar-x4 | 1 | 1.793 |  |  | too few blocks |
| `small-flat.fresh.mac-mars.sender.warm` | tar-x8 | 1 | 1.236 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | xs | 1.163 [0.997, 1.357] | 1.132 [0.267, 4.792] | 0.982 [0.177, 5.436] |
| `real-congress.fresh.mac-mars.sender.warm` | tar | 1.036 [0.187, 5.729] | 0.497 [0.159, 1.556] | 8.495 [0.192, 376.184] |
| `real-congress.fresh.mac-mars.sender.warm` | tar-zstd | 0.887 [0.487, 1.616] | 0.511 [0.170, 1.537] | 5.653 [2.070, 15.439] |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x4 | 1.122 [0.252, 4.989] | 0.331 [0.100, 1.099] | 3.915 [0.253, 60.682] |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x8 | 1.086 [0.756, 1.560] | 0.312 [0.134, 0.729] | 1.999 [0.187, 21.416] |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 1.253 | 0.774 | 1.516 |
| `small-deep.fresh.mac-mars.sender.warm` | tar | 0.715 | 0.477 | 2.893 |
| `small-deep.fresh.mac-mars.sender.warm` | tar-zstd | 0.733 | 0.474 | 2.761 |
| `small-deep.fresh.mac-mars.sender.warm` | tar-x4 | 0.748 | 0.453 | 1.469 |
| `small-deep.fresh.mac-mars.sender.warm` | tar-x8 | 0.814 | 0.450 | 1.386 |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 1.233 | 1.007 | 1.107 |
| `small-flat.fresh.mac-mars.sender.warm` | tar | 0.961 | 0.904 | 6.792 |
| `small-flat.fresh.mac-mars.sender.warm` | tar-zstd | 0.897 | 0.900 | 5.777 |
| `small-flat.fresh.mac-mars.sender.warm` | tar-x4 | 0.976 | 0.702 | 1.816 |
| `small-flat.fresh.mac-mars.sender.warm` | tar-x8 | 1.130 | 0.646 | 1.244 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | tar | tar-x4 | tar-x8 | tar-zstd | xs | xs-best |
|---|---|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | 98.481 | 45.389 | 23.231 | 65.545 | 11.419 | 11.677 |
| `small-deep.fresh.mac-mars.sender.warm` | 29.737 | 15.145 | 14.302 | 28.431 | 15.578 | 10.330 |
| `small-flat.fresh.mac-mars.sender.warm` | 22.358 | 6.001 | 4.137 | 19.027 | 3.659 | 3.346 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.mac-mars.sender.warm` | xs | 0.1808 | 296 | 396 |
| `real-congress.fresh.mac-mars.sender.warm` | tar | 0.4268 | 1637 | 2193 |
| `real-congress.fresh.mac-mars.sender.warm` | tar-zstd | 0.1068 | 105 | 140 |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x4 | 0.3101 | 865 | 1159 |
| `real-congress.fresh.mac-mars.sender.warm` | tar-x8 | 0.2599 | 609 | 815 |

## Voided attempts

- stopped
- tar: did not settle: mars has 54 MiB dirty
