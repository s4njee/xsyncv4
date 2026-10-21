# X2-large-tune

One of these settings brings xs closer to the link rate on a single large file.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T030429Z-X2-large-tune.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | j4 | 8 | 1.136 [0.925, 1.395] | 1.177 [0.870, 1.401] | 0.1484 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 8 | 1.067 [0.931, 1.222] | 1.034 [0.939, 1.239] | 0.3203 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 8 | 0.954 [0.818, 1.113] | 0.966 [0.794, 1.121] | 0.4922 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 8 | 0.875 [0.702, 1.091] | 0.986 [0.697, 1.015] | 0.2969 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | queues | 8 | 1.117 [0.985, 1.266] | 1.068 [1.014, 1.290] | 0.0156 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 8 | 1.016 [0.953, 1.082] | 0.994 [0.979, 1.103] | 0.9922 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 8 | 1.086 [0.915, 1.289] | 1.008 [0.978, 1.330] | 0.3828 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 8 | 1.044 [0.940, 1.160] | 1.002 [0.972, 1.183] | 0.4609 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 8 | 1.055 [0.911, 1.222] | 0.997 [0.974, 1.273] | 0.8203 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 8 | 1.037 [0.966, 1.113] | 1.009 [0.992, 1.134] | 0.2266 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | j4 | 1.024 [0.958, 1.093] | 0.870 [0.845, 0.895] | 1.141 [0.926, 1.406] |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 0.982 [0.912, 1.058] | 1.101 [1.070, 1.134] | 1.070 [0.928, 1.234] |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 0.981 [0.942, 1.020] | 0.742 [0.721, 0.763] | 0.959 [0.827, 1.111] |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 1.065 [0.984, 1.152] | 1.020 [0.947, 1.098] | 0.879 [0.706, 1.095] |
| `large-one.fresh.mac-mars.sender.warm` | queues | 1.037 [1.011, 1.063] | 3.123 [2.974, 3.281] | 1.122 [0.985, 1.278] |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 0.989 [0.959, 1.021] | 0.921 [0.820, 1.035] | 1.016 [0.953, 1.082] |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 1.090 [1.041, 1.141] | 1.067 [0.950, 1.199] | 1.087 [0.915, 1.291] |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 0.943 [0.904, 0.984] | 1.006 [0.793, 1.276] | 1.045 [0.940, 1.161] |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 0.994 [0.961, 1.028] | 0.888 [0.737, 1.070] | 1.056 [0.911, 1.223] |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 1.011 [0.979, 1.043] | 2.428 [2.234, 2.638] | 1.037 [0.965, 1.114] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | block4m | chunk1m | j4 | j8 | queues | xs |
|---|---|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | 23.917 | 21.947 | 28.481 | 26.756 | 28.008 | 25.078 |
| `large-one.fresh.mars-mac.receiver.warm` | 21.191 | 21.409 | 20.605 | 22.038 | 21.037 | 20.290 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | j4 | 0.2456 | 544 | 728 |
| `large-one.fresh.mac-mars.sender.warm` | j8 | 0.1626 | 240 | 320 |
| `large-one.fresh.mac-mars.sender.warm` | block4m | 0.1843 | 307 | 411 |
| `large-one.fresh.mac-mars.sender.warm` | chunk1m | 0.2635 | 625 | 837 |
| `large-one.fresh.mac-mars.sender.warm` | queues | 0.1498 | 204 | 272 |
| `large-one.fresh.mars-mac.receiver.warm` | j4 | 0.0757 | 54 | 71 |
| `large-one.fresh.mars-mac.receiver.warm` | j8 | 0.2047 | 378 | 506 |
| `large-one.fresh.mars-mac.receiver.warm` | block4m | 0.1259 | 145 | 193 |
| `large-one.fresh.mars-mac.receiver.warm` | chunk1m | 0.1753 | 278 | 372 |
| `large-one.fresh.mars-mac.receiver.warm` | queues | 0.0851 | 67 | 90 |
