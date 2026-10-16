# X5-10g-baseline

At 10 Gb/s xs copies large files faster than rsync and approaches what one ssh connection carries.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T032058Z-X5-10g-baseline.
- Valid blocks: 35. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | xs | 6 | 0.459 [0.289, 0.731] | 0.389 [0.365, 1.129] | 0.0625 | too few blocks |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 6 | 0.335 [0.323, 0.347] | 0.337 [0.314, 0.345] | 0.0312 | too few blocks |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 6 | 0.567 [0.328, 0.980] | 0.593 [0.368, 1.191] | 0.0938 | too few blocks |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 6 | 0.359 [0.344, 0.374] | 0.359 [0.343, 0.379] | 0.0312 | too few blocks |
| `large-one.fresh.mac-mars.sender.warm` | xs | 6 | 0.414 [0.306, 0.562] | 0.406 [0.314, 0.657] | 0.0312 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 5 | 0.332 [0.318, 0.346] | 0.332 | 0.0625 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | xs | 0.613 [0.569, 0.660] | 9.618 [8.111, 11.405] | 0.453 [0.289, 0.711] |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 0.559 [0.544, 0.574] | 0.688 [0.650, 0.727] | 0.333 [0.321, 0.345] |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 0.655 [0.582, 0.737] | 10.633 [9.961, 11.351] | 0.564 [0.326, 0.975] |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 0.730 [0.694, 0.767] | 0.714 [0.666, 0.766] | 0.357 [0.342, 0.372] |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.586 [0.554, 0.620] | 9.587 [8.269, 11.115] | 0.414 [0.309, 0.555] |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.510 [0.486, 0.535] | 0.673 [0.628, 0.720] | 0.329 [0.316, 0.343] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | 22.678 | 10.416 |
| `large-four.fresh.mars-mac.receiver.warm` | 24.252 | 8.115 |
| `large-mixed.fresh.mac-mars.sender.warm` | 22.435 | 12.715 |
| `large-mixed.fresh.mars-mac.receiver.warm` | 24.787 | 8.896 |
| `large-one.fresh.mac-mars.sender.warm` | 22.185 | 9.195 |
| `large-one.fresh.mars-mac.receiver.warm` | 22.192 | 7.359 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | xs | 0.4422 | 1757 | 2354 |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 0.0333 | 12 | 16 |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 0.5215 | 2443 | 3273 |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 0.0399 | 17 | 22 |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.2900 | 757 | 1014 |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.0333 | 12 | 16 |

## Voided attempts

- stopped
