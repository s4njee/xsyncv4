# N3-nvme-small-tune

Fewer receiving workers or --no-atomic make small and mixed copies onto NVMe faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T034425Z-N3-nvme-small-tune.
- Valid blocks: 24. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv1 | 8 | 0.959 [0.831, 1.105] | 0.989 [0.839, 1.124] | 0.4922 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv2 | 8 | 0.997 [0.855, 1.162] | 0.991 [0.844, 1.196] | 0.8750 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4 | 8 | 0.926 [0.823, 1.042] | 0.981 [0.844, 1.013] | 0.2422 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | no-atomic | 8 | 0.945 [0.824, 1.084] | 0.987 [0.843, 1.088] | 0.3594 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4-noatomic | 8 | 0.949 [0.822, 1.097] | 0.981 [0.840, 1.112] | 0.2891 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | recv1 | 8 | 1.391 [0.907, 2.133] | 1.349 [0.873, 2.180] | 0.1172 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | recv2 | 8 | 0.894 [0.690, 1.159] | 0.901 [0.659, 1.149] | 0.3359 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | recv4 | 8 | 1.069 [0.807, 1.416] | 1.071 [0.790, 1.532] | 0.6562 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | no-atomic | 8 | 0.961 [0.721, 1.281] | 0.953 [0.727, 1.332] | 0.7656 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | recv4-noatomic | 8 | 0.905 [0.686, 1.195] | 0.918 [0.692, 1.275] | 0.3984 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | recv1 | 8 | 0.966 [0.825, 1.131] | 0.914 [0.878, 1.185] | 0.6953 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | recv2 | 8 | 0.933 [0.893, 0.975] | 0.924 [0.899, 0.989] | 0.0156 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | recv4 | 8 | 1.073 [0.863, 1.332] | 0.995 [0.928, 1.400] | 0.7656 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | no-atomic | 8 | 0.825 [0.646, 1.055] | 0.803 [0.632, 1.127] | 0.0938 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | recv4-noatomic | 8 | 0.689 [0.517, 0.918] | 0.608 [0.561, 0.940] | 0.0234 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv1 | 0.956 [0.904, 1.012] | 0.988 [0.949, 1.028] | 0.959 [0.830, 1.108] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv2 | 0.986 [0.940, 1.035] | 1.007 [0.948, 1.070] | 0.997 [0.856, 1.162] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4 | 1.001 [0.974, 1.029] | 0.989 [0.938, 1.042] | 0.927 [0.824, 1.043] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | no-atomic | 0.961 [0.908, 1.016] | 0.982 [0.957, 1.007] | 0.922 [0.822, 1.034] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.982 [0.962, 1.002] | 1.004 [0.932, 1.081] | 0.949 [0.820, 1.098] |
| `small-deep.fresh.mac-mars.sender.warm` | recv1 | 0.842 [0.823, 0.862] | 1.456 [0.971, 2.184] | 1.394 [0.907, 2.141] |
| `small-deep.fresh.mac-mars.sender.warm` | recv2 | 0.832 [0.801, 0.864] | 0.801 [0.492, 1.305] | 0.894 [0.689, 1.159] |
| `small-deep.fresh.mac-mars.sender.warm` | recv4 | 0.872 [0.842, 0.903] | 0.959 [0.649, 1.418] | 1.070 [0.807, 1.419] |
| `small-deep.fresh.mac-mars.sender.warm` | no-atomic | 1.011 [0.979, 1.044] | 1.039 [0.622, 1.733] | 0.961 [0.719, 1.285] |
| `small-deep.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.825 [0.798, 0.853] | 0.797 [0.506, 1.258] | 0.904 [0.684, 1.194] |
| `small-flat.fresh.mac-mars.sender.warm` | recv1 | 0.947 [0.905, 0.992] | 1.017 [0.850, 1.218] | 0.972 [0.831, 1.136] |
| `small-flat.fresh.mac-mars.sender.warm` | recv2 | 0.961 [0.920, 1.004] | 1.004 [0.843, 1.196] | 0.937 [0.896, 0.979] |
| `small-flat.fresh.mac-mars.sender.warm` | recv4 | 0.993 [0.920, 1.071] | 0.889 [0.760, 1.040] | 1.077 [0.869, 1.335] |
| `small-flat.fresh.mac-mars.sender.warm` | no-atomic | 0.841 [0.798, 0.887] | 0.730 [0.592, 0.899] | 0.828 [0.646, 1.060] |
| `small-flat.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.816 [0.778, 0.855] | 0.765 [0.586, 0.999] | 0.690 [0.518, 0.918] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | no-atomic | recv1 | recv2 | recv4 | recv4-noatomic | xs |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 3.701 | 3.753 | 3.904 | 3.626 | 3.717 | 3.916 |
| `small-deep.fresh.mac-mars.sender.warm` | 7.249 | 10.492 | 6.741 | 8.061 | 6.824 | 7.541 |
| `small-flat.fresh.mac-mars.sender.warm` | 3.014 | 3.526 | 3.408 | 3.916 | 2.517 | 3.651 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv1 | 0.1705 | 263 | 352 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv2 | 0.1835 | 305 | 407 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4 | 0.1412 | 181 | 242 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | no-atomic | 0.1634 | 242 | 324 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.1726 | 270 | 361 |
| `small-deep.fresh.mac-mars.sender.warm` | recv1 | 0.5113 | 2349 | 3147 |
| `small-deep.fresh.mac-mars.sender.warm` | recv2 | 0.3103 | 866 | 1160 |
| `small-deep.fresh.mac-mars.sender.warm` | recv4 | 0.3367 | 1020 | 1366 |
| `small-deep.fresh.mac-mars.sender.warm` | no-atomic | 0.3434 | 1061 | 1421 |
| `small-deep.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.3322 | 993 | 1330 |
| `small-flat.fresh.mac-mars.sender.warm` | recv1 | 0.1885 | 321 | 430 |
| `small-flat.fresh.mac-mars.sender.warm` | recv2 | 0.0529 | 28 | 36 |
| `small-flat.fresh.mac-mars.sender.warm` | recv4 | 0.2595 | 607 | 812 |
| `small-flat.fresh.mac-mars.sender.warm` | no-atomic | 0.2933 | 774 | 1037 |
| `small-flat.fresh.mac-mars.sender.warm` | recv4-noatomic | 0.3429 | 1058 | 1417 |

## Voided attempts

- recv4-noatomic: the transfer exited 255: st 10.25.0.2 port 22: Operation timed out
xs: connection unexpectedly closed (remote shell exited with code 255)
xs: er
