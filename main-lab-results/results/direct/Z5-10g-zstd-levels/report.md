# Z5-10g-zstd-levels

At 10 Gb/s, xs at zstd level 2 delivers compressible data faster than at levels 1 and 3.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z1`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T202205Z-Z5-10g-zstd-levels.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs-z2 | 6 | 1.456 [0.968, 2.190] | 1.481 [0.955, 2.810] | 0.0938 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 6 | 1.390 [0.975, 1.980] | 1.385 [0.881, 2.015] | 0.1250 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs | 6 | 1.225 [0.825, 1.820] | 1.236 [0.756, 1.817] | 0.2188 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z2 | 6 | 0.832 [0.752, 0.921] | 0.827 [0.725, 0.957] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 6 | 0.734 [0.600, 0.898] | 0.738 [0.529, 0.900] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 6 | 2.064 [1.527, 2.790] | 2.073 [1.338, 3.016] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs-z2 | 1.163 [1.049, 1.288] | 1.304 [1.236, 1.377] | 1.460 [0.968, 2.204] |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 1.327 [1.192, 1.477] | 1.318 [1.272, 1.366] | 1.396 [0.975, 1.999] |
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.513 [0.453, 0.582] | 0.496 [0.459, 0.537] | 1.225 [0.827, 1.815] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z2 | 0.998 [0.986, 1.010] | 1.346 [1.344, 1.348] | 0.830 [0.749, 0.920] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 1.125 [1.100, 1.151] | 1.392 [1.392, 1.393] | 0.732 [0.598, 0.896] |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.666 [0.630, 0.704] | 0.633 [0.596, 0.673] | 2.073 [1.532, 2.804] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-z1 | xs-z2 | xs-z3 |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | 19.107 | 15.593 | 22.705 | 21.669 |
| `large-text.fresh.mars-mac.receiver.warm` | 14.976 | 7.255 | 6.035 | 5.324 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs-z2 | 0.3890 | 1360 | 1822 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 0.3372 | 1023 | 1370 |
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.3770 | 1278 | 1712 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z2 | 0.0964 | 86 | 114 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 0.1921 | 334 | 446 |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.2872 | 743 | 994 |
