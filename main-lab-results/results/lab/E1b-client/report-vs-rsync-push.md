# E1b-client

A transfer started by the receiver takes the same time, within 3%, as the same transfer started by the sender.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `rsync-push`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T003200Z-E1b-client.
- Valid blocks: 80. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-push | 10 | 1.007 [0.998, 1.016] | 1.006 [0.998, 1.017] | 0.1250 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 10 | 1.011 [0.978, 1.045] | 0.999 [0.989, 1.065] | 0.8340 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 0.995 [0.992, 0.997] | 0.995 [0.992, 0.998] | 0.0039 | 0.0547 | equivalent |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-push | 10 | 1.053 [0.929, 1.194] | 1.109 [0.857, 1.136] | 0.4121 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 10 | 1.042 [0.938, 1.158] | 1.084 [0.885, 1.112] | 0.4336 | 1.0000 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 0.951 [0.839, 1.079] | 1.004 [0.765, 1.011] | 0.9453 | 1.0000 | inconclusive |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-push | 10 | 0.614 [0.589, 0.640] | 0.615 [0.585, 0.642] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.479 [0.457, 0.503] | 0.476 [0.453, 0.504] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 10 | 0.808 [0.776, 0.842] | 0.803 [0.780, 0.842] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-push | 10 | 0.677 [0.655, 0.701] | 0.677 [0.654, 0.701] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 10 | 0.935 [0.906, 0.964] | 0.936 [0.903, 0.969] | 0.0020 | 0.0469 | faster |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 10 | 1.149 [1.100, 1.201] | 1.146 [1.102, 1.197] | 0.0020 | 0.0469 | slower |
| `small-flat.fresh.freya-neo.arm.warm` | xs-push | 10 | 0.969 [0.918, 1.023] | 0.972 [0.917, 1.026] | 0.2305 | 1.0000 | inconclusive |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 10 | 0.954 [0.911, 0.998] | 0.957 [0.911, 0.997] | 0.0430 | 0.5586 | inconclusive |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 10 | 0.971 [0.915, 1.030] | 0.967 [0.914, 1.033] | 0.2949 | 1.0000 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | xs-push | 10 | 0.803 [0.647, 0.997] | 0.842 [0.667, 0.975] | 0.0527 | 0.6328 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 10 | 0.844 [0.669, 1.066] | 0.874 [0.688, 1.084] | 0.1406 | 1.0000 | inconclusive |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 10 | 1.124 [0.949, 1.330] | 1.056 [0.965, 1.359] | 0.1602 | 1.0000 | inconclusive |
| `small-flat.noop.freya-neo.arm.warm` | xs-push | 10 | 0.425 [0.384, 0.469] | 0.428 [0.379, 0.470] | 0.0020 | 0.0469 | faster |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 10 | 0.353 [0.332, 0.376] | 0.359 [0.330, 0.373] | 0.0020 | 0.0469 | faster |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 10 | 0.879 [0.775, 0.996] | 0.876 [0.779, 1.004] | 0.0527 | 0.6328 | inconclusive |
| `small-flat.noop.neo-freya.arm.warm` | xs-push | 10 | 0.424 [0.370, 0.485] | 0.422 [0.370, 0.485] | 0.0020 | 0.0469 | faster |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 10 | 0.506 [0.462, 0.554] | 0.509 [0.469, 0.551] | 0.0020 | 0.0469 | faster |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 10 | 1.088 [0.977, 1.212] | 1.097 [0.978, 1.191] | 0.1094 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-push | 2.072 [1.964, 2.185] | 1.004 [0.993, 1.015] | 10.018 [9.869, 10.169] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 3.431 [3.247, 3.627] | 1.009 [0.969, 1.051] | 10.031 [9.885, 10.180] |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 2.060 [1.989, 2.133] | 0.993 [0.982, 1.005] | 1.013 [0.997, 1.030] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-push | 2.428 [2.243, 2.629] | 1.056 [0.885, 1.261] | 8.201 [8.051, 8.353] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 1.799 [1.682, 1.924] | 1.058 [0.951, 1.177] | 8.210 [8.037, 8.388] |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.682 [0.652, 0.712] | 0.954 [0.842, 1.080] | 0.986 [0.960, 1.012] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-push | 1.713 [1.630, 1.799] | 0.617 [0.592, 0.643] | 1.444 [1.418, 1.470] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 1.704 [1.584, 1.833] | 0.484 [0.461, 0.509] | 1.427 [1.387, 1.468] |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 1.083 [1.031, 1.137] | 0.810 [0.778, 0.844] | 1.019 [0.990, 1.048] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-push | 1.851 [1.698, 2.018] | 0.680 [0.658, 0.703] | 1.386 [1.357, 1.415] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 1.626 [1.500, 1.763] | 0.939 [0.911, 0.968] | 1.360 [1.329, 1.391] |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.925 [0.835, 1.025] | 1.157 [1.111, 1.205] | 1.014 [0.986, 1.042] |
| `small-flat.fresh.freya-neo.arm.warm` | xs-push | 1.484 [1.422, 1.548] | 0.968 [0.923, 1.015] | 9.885 [9.567, 10.213] |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 1.722 [1.659, 1.787] | 0.955 [0.918, 0.993] | 9.982 [9.741, 10.230] |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 1.225 [1.174, 1.277] | 0.966 [0.915, 1.019] | 1.277 [1.201, 1.358] |
| `small-flat.fresh.neo-freya.arm.warm` | xs-push | 1.653 [1.536, 1.780] | 0.847 [0.682, 1.051] | 5.816 [4.461, 7.581] |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 1.409 [1.326, 1.497] | 0.811 [0.694, 0.948] | 5.852 [4.225, 8.104] |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.920 [0.880, 0.962] | 1.115 [0.939, 1.325] | 1.075 [1.036, 1.115] |
| `small-flat.noop.freya-neo.arm.warm` | xs-push | 1.232 [1.071, 1.416] | 0.427 [0.387, 0.472] | 2.091 [2.065, 2.118] |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 1.280 [1.156, 1.416] | 0.356 [0.334, 0.379] | 2.085 [2.067, 2.104] |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 1.003 [0.844, 1.191] | 0.879 [0.776, 0.996] | 0.968 [0.943, 0.994] |
| `small-flat.noop.neo-freya.arm.warm` | xs-push | 1.392 [1.154, 1.680] | 0.427 [0.375, 0.487] | 1.689 [1.667, 1.712] |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 1.292 [1.135, 1.471] | 0.508 [0.464, 0.556] | 1.682 [1.659, 1.705] |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 1.003 [0.863, 1.166] | 1.091 [0.983, 1.212] | 0.989 [0.968, 1.010] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-pull | rsync-push | xs-pull | xs-push |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | 12.223 | 12.288 | 12.420 | 12.374 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | 12.432 | 13.071 | 13.626 | 13.764 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | 0.320 | 0.396 | 0.190 | 0.243 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | 0.326 | 0.283 | 0.265 | 0.192 |
| `small-flat.fresh.freya-neo.arm.warm` | 6.785 | 6.987 | 6.663 | 6.771 |
| `small-flat.fresh.neo-freya.arm.warm` | 5.573 | 4.959 | 4.187 | 3.982 |
| `small-flat.noop.freya-neo.arm.warm` | 0.724 | 0.824 | 0.291 | 0.350 |
| `small-flat.noop.neo-freya.arm.warm` | 0.786 | 0.723 | 0.365 | 0.306 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-push | 0.0126 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | xs-pull | 0.0467 | 22 | 29 |
| `mixed-bimodal.fresh.freya-neo.arm.warm` | rsync-pull | 0.0036 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-push | 0.1758 | 280 | 374 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | xs-pull | 0.1471 | 197 | 263 |
| `mixed-bimodal.fresh.neo-freya.arm.warm` | rsync-pull | 0.1759 | 280 | 375 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-push | 0.0579 | 33 | 43 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | xs-pull | 0.0673 | 43 | 57 |
| `mixed-bimodal.noop.freya-neo.arm.warm` | rsync-pull | 0.0566 | 31 | 41 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-push | 0.0472 | 22 | 29 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | xs-pull | 0.0434 | 19 | 25 |
| `mixed-bimodal.noop.neo-freya.arm.warm` | rsync-pull | 0.0615 | 36 | 48 |
| `small-flat.fresh.freya-neo.arm.warm` | xs-push | 0.0758 | 54 | 72 |
| `small-flat.fresh.freya-neo.arm.warm` | xs-pull | 0.0637 | 39 | 51 |
| `small-flat.fresh.freya-neo.arm.warm` | rsync-pull | 0.0829 | 64 | 85 |
| `small-flat.fresh.neo-freya.arm.warm` | xs-push | 0.3024 | 823 | 1102 |
| `small-flat.fresh.neo-freya.arm.warm` | xs-pull | 0.3259 | 956 | 1280 |
| `small-flat.fresh.neo-freya.arm.warm` | rsync-pull | 0.2358 | 501 | 671 |
| `small-flat.noop.freya-neo.arm.warm` | xs-push | 0.1394 | 177 | 236 |
| `small-flat.noop.freya-neo.arm.warm` | xs-pull | 0.0876 | 71 | 95 |
| `small-flat.noop.freya-neo.arm.warm` | rsync-pull | 0.1753 | 278 | 372 |
| `small-flat.noop.neo-freya.arm.warm` | xs-push | 0.1883 | 321 | 429 |
| `small-flat.noop.neo-freya.arm.warm` | xs-pull | 0.1263 | 146 | 194 |
| `small-flat.noop.neo-freya.arm.warm` | rsync-pull | 0.1504 | 205 | 274 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
