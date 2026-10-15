# X4-cipher-rsync

AES-256 costs both tools little; neither rsync variant closes its gap to xs.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T030430Z-X4-cipher-rsync.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-aes256 | 8 | 0.969 [0.776, 1.211] | 1.008 [0.741, 1.197] | 0.7812 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | rsync-inplace | 8 | 0.902 [0.698, 1.165] | 0.970 [0.642, 1.081] | 0.5156 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | rsync-W | 8 | 0.883 [0.659, 1.183] | 0.947 [0.630, 1.103] | 0.4453 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | xs | 8 | 0.633 [0.427, 0.938] | 0.651 [0.399, 1.020] | 0.0625 | inconclusive |
| `large-one.fresh.mac-mars.sender.warm` | xs-aes256 | 8 | 0.626 [0.439, 0.893] | 0.639 [0.407, 0.952] | 0.0156 | faster |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-aes256 | 8 | 1.059 [0.984, 1.139] | 1.052 [0.978, 1.163] | 0.0938 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-inplace | 8 | 1.060 [0.963, 1.166] | 1.058 [0.950, 1.172] | 0.1953 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-W | 8 | 1.015 [0.948, 1.086] | 1.005 [0.953, 1.102] | 0.7266 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 8 | 0.610 [0.577, 0.646] | 0.610 [0.573, 0.649] | 0.0078 | faster |
| `large-one.fresh.mars-mac.receiver.warm` | xs-aes256 | 8 | 0.659 [0.593, 0.733] | 0.652 [0.596, 0.746] | 0.0078 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-aes256 | 1.016 [0.947, 1.089] | 1.004 [0.959, 1.052] | 0.969 [0.775, 1.210] |
| `large-one.fresh.mac-mars.sender.warm` | rsync-inplace | 0.964 [0.881, 1.054] | 1.064 [0.900, 1.257] | 0.902 [0.698, 1.165] |
| `large-one.fresh.mac-mars.sender.warm` | rsync-W | 0.981 [0.899, 1.071] | 1.004 [0.992, 1.015] | 0.876 [0.656, 1.170] |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.591 [0.546, 0.639] | 9.042 [8.629, 9.475] | 0.632 [0.427, 0.936] |
| `large-one.fresh.mac-mars.sender.warm` | xs-aes256 | 0.603 [0.552, 0.657] | 8.665 [8.236, 9.116] | 0.627 [0.439, 0.894] |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-aes256 | 1.012 [0.983, 1.041] | 0.994 [0.974, 1.015] | 1.059 [0.984, 1.139] |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-inplace | 1.013 [0.973, 1.055] | 0.996 [0.974, 1.017] | 1.060 [0.963, 1.166] |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-W | 0.997 [0.971, 1.023] | 1.004 [0.990, 1.017] | 1.014 [0.948, 1.086] |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.531 [0.520, 0.543] | 0.730 [0.656, 0.812] | 0.609 [0.576, 0.645] |
| `large-one.fresh.mars-mac.receiver.warm` | xs-aes256 | 0.539 [0.522, 0.557] | 0.693 [0.602, 0.797] | 0.658 [0.592, 0.732] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-W | rsync-aes256 | rsync-inplace | xs | xs-aes256 |
|---|---|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | 39.204 | 34.603 | 37.988 | 35.352 | 24.822 | 24.560 |
| `large-one.fresh.mars-mac.receiver.warm` | 33.135 | 33.616 | 35.084 | 35.118 | 20.225 | 21.847 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-aes256 | 0.2662 | 638 | 855 |
| `large-one.fresh.mac-mars.sender.warm` | rsync-inplace | 0.3066 | 846 | 1133 |
| `large-one.fresh.mac-mars.sender.warm` | rsync-W | 0.3500 | 1101 | 1475 |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.4706 | 1990 | 2666 |
| `large-one.fresh.mac-mars.sender.warm` | xs-aes256 | 0.4245 | 1619 | 2169 |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-aes256 | 0.0872 | 71 | 94 |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-inplace | 0.1142 | 119 | 159 |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-W | 0.0812 | 62 | 82 |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.0676 | 44 | 58 |
| `large-one.fresh.mars-mac.receiver.warm` | xs-aes256 | 0.1268 | 147 | 196 |
