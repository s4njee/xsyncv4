# XC1-ssh-ceiling-apollo

A bare pipe on 8 streams is at least 5% faster than xs on large files over the cable.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T160501Z-XC1-ssh-ceiling-apollo.
- Valid blocks: 6. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 0.732 [0.165, 3.242] | 0.768 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 3 | 1.518 [0.322, 7.159] | 1.412 | 0.5000 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x1 | 3 | 1.049 [0.172, 6.393] | 1.046 | 0.7500 | too few blocks |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x8 | 3 | 0.878 [0.092, 8.345] | 0.920 | 1.0000 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 3 | 1.487 [0.357, 6.184] | 1.375 | 0.2500 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 3 | 2.195 [0.764, 6.303] | 2.167 | 0.2500 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x1 | 3 | 1.313 [0.543, 3.173] | 1.314 | 0.5000 | too few blocks |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x8 | 3 | 0.839 [0.066, 10.630] | 0.853 | 0.7500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.411 [0.396, 0.427] | 1.033 [0.937, 1.139] | 0.873 [0.679, 1.122] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 1.903 [1.708, 2.120] | 0.109 [0.100, 0.118] | 2.591 [1.554, 4.320] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x1 | 0.891 [0.756, 1.050] | 0.391 [0.033, 4.632] | 1.081 [0.617, 1.896] |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x8 | 1.165 [0.976, 1.390] | 0.793 [0.676, 0.931] | 0.661 [0.348, 1.258] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.382 [0.346, 0.423] | 1.052 [0.997, 1.109] | 1.011 [0.712, 1.435] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 1.984 [1.938, 2.031] | 0.127 [0.126, 0.128] | 2.959 [2.371, 3.694] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x1 | 0.845 [0.823, 0.867] | 0.262 [0.018, 3.792] | 0.845 [0.783, 0.912] |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x8 | 0.835 [0.803, 0.869] | 0.233 [0.026, 2.082] | 0.820 [0.699, 0.963] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | pipe-x1 | pipe-x8 | rsync | xs-cpp | xs-rs |
|---|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | 14.831 | 12.411 | 21.470 | 14.140 | 10.345 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | 13.383 | 8.556 | 22.381 | 10.196 | 15.158 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `hs-16x256m.fresh.mac-apollo.sender.warm` | xs-rs | 0.5993 | 3225 | 4322 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | rsync | 0.6243 | 3499 | 4689 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x1 | 0.7276 | 4753 | 6370 |
| `hs-16x256m.fresh.mac-apollo.sender.warm` | pipe-x8 | 0.9066 | 7378 | 9887 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | xs-rs | 0.5738 | 2957 | 3962 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | rsync | 0.4246 | 1620 | 2171 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x1 | 0.3554 | 1136 | 1521 |
| `hs-1x4g.fresh.mac-apollo.sender.warm` | pipe-x8 | 1.0221 | 9377 | 12567 |
