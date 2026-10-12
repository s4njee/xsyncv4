# E1-baseline

xs -a differs from rsync -a by more than 3% in time-to-durable, per corpus, scenario and direction.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T003159Z-E1-baseline.
- Valid blocks: 336. Voided block attempts: 5.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 12 | 0.964 [0.916, 1.014] | 0.986 [0.944, 0.998] | 0.0107 | 0.0537 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 12 | 1.048 [1.026, 1.071] | 1.041 [1.029, 1.068] | 0.0005 | 0.0137 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 12 | 0.613 [0.588, 0.639] | 0.616 [0.595, 0.639] | 0.0005 | 0.0137 | faster |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 12 | 0.666 [0.645, 0.687] | 0.666 [0.644, 0.686] | 0.0005 | 0.0137 | faster |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 12 | 0.983 [0.960, 1.006] | 0.988 [0.958, 1.003] | 0.1250 | 0.5000 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 12 | 0.955 [0.818, 1.116] | 1.044 [0.787, 1.100] | 0.5513 | 1.0000 | inconclusive |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 12 | 0.898 [0.843, 0.957] | 0.886 [0.845, 0.943] | 0.0054 | 0.0376 | faster |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 12 | 0.887 [0.852, 0.923] | 0.875 [0.853, 0.932] | 0.0010 | 0.0137 | faster |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 12 | 0.801 [0.760, 0.844] | 0.803 [0.759, 0.855] | 0.0005 | 0.0137 | faster |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 12 | 1.060 [0.759, 1.479] | 1.067 [0.787, 1.501] | 0.7065 | 1.0000 | inconclusive |
| `small-deep.noop.freya-neo.sender.warm` | xs | 12 | 0.154 [0.136, 0.175] | 0.154 [0.132, 0.181] | 0.0005 | 0.0137 | faster |
| `small-deep.noop.neo-freya.sender.warm` | xs | 12 | 0.537 [0.488, 0.590] | 0.544 [0.484, 0.590] | 0.0005 | 0.0137 | faster |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 12 | 0.901 [0.847, 0.959] | 0.903 [0.849, 0.961] | 0.0024 | 0.0195 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 12 | 0.521 [0.434, 0.626] | 0.494 [0.430, 0.668] | 0.0010 | 0.0137 | faster |
| `small-flat.noop.freya-neo.sender.warm` | xs | 12 | 0.420 [0.406, 0.435] | 0.420 [0.404, 0.437] | 0.0005 | 0.0137 | faster |
| `small-flat.noop.neo-freya.sender.warm` | xs | 12 | 0.394 [0.364, 0.425] | 0.395 [0.359, 0.435] | 0.0005 | 0.0137 | faster |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 12 | 0.904 [0.823, 0.991] | 0.938 [0.805, 0.987] | 0.0068 | 0.0410 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 12 | 0.477 [0.402, 0.566] | 0.450 [0.420, 0.500] | 0.0010 | 0.0137 | faster |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 12 | 0.437 [0.417, 0.458] | 0.438 [0.417, 0.458] | 0.0005 | 0.0137 | faster |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 12 | 0.395 [0.364, 0.428] | 0.393 [0.366, 0.425] | 0.0005 | 0.0137 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs | 12 | 0.760 [0.737, 0.785] | 0.759 [0.733, 0.787] | 0.0005 | 0.0137 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 12 | 0.989 [0.745, 1.313] | 0.939 [0.699, 1.374] | 0.9307 | 1.0000 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | xs | 12 | 0.154 [0.141, 0.168] | 0.151 [0.140, 0.168] | 0.0005 | 0.0137 | faster |
| `small-real.noop.neo-freya.sender.warm` | xs | 12 | 0.692 [0.617, 0.777] | 0.698 [0.618, 0.778] | 0.0005 | 0.0137 | faster |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 12 | 0.920 [0.900, 0.941] | 0.916 [0.900, 0.943] | 0.0005 | 0.0137 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 12 | 0.907 [0.865, 0.952] | 0.916 [0.870, 0.951] | 0.0005 | 0.0137 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 12 | 0.919 [0.887, 0.952] | 0.920 [0.882, 0.961] | 0.0005 | 0.0137 | faster |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 12 | 0.902 [0.844, 0.964] | 0.916 [0.854, 0.957] | 0.0015 | 0.0137 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.953 [1.921, 1.986] | 9.991 [9.858, 10.126] | 0.963 [0.917, 1.011] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.137 [2.058, 2.220] | 8.050 [7.820, 8.286] | 1.044 [1.021, 1.068] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 1.665 [1.553, 1.785] | 1.423 [1.386, 1.461] | 0.610 [0.585, 0.636] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 1.774 [1.664, 1.891] | 1.377 [1.353, 1.402] | 0.663 [0.642, 0.684] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 2.401 [2.345, 2.458] | 8.259 [8.089, 8.434] | 0.981 [0.955, 1.007] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 2.166 [2.134, 2.199] | 7.870 [7.699, 8.044] | 0.984 [0.861, 1.125] |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 2.014 [1.913, 2.121] | 1.315 [1.297, 1.334] | 0.896 [0.840, 0.956] |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 1.780 [1.714, 1.848] | 1.374 [1.345, 1.404] | 0.879 [0.846, 0.913] |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.874 [0.836, 0.914] | 0.565 [0.548, 0.582] | 0.794 [0.750, 0.841] |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 2.301 [2.190, 2.417] | 8.002 [6.846, 9.354] | 1.142 [0.880, 1.481] |
| `small-deep.noop.freya-neo.sender.warm` | xs | 1.042 [0.993, 1.093] | 1.052 [1.036, 1.069] | 0.154 [0.135, 0.175] |
| `small-deep.noop.neo-freya.sender.warm` | xs | 5.380 [5.122, 5.651] | 5.546 [5.331, 5.770] | 0.537 [0.488, 0.591] |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 1.434 [1.384, 1.484] | 10.073 [9.881, 10.269] | 0.893 [0.839, 0.951] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.511 [1.464, 1.559] | 4.731 [3.906, 5.730] | 0.527 [0.441, 0.630] |
| `small-flat.noop.freya-neo.sender.warm` | xs | 1.247 [1.199, 1.298] | 2.144 [2.100, 2.189] | 0.417 [0.403, 0.432] |
| `small-flat.noop.neo-freya.sender.warm` | xs | 1.266 [1.138, 1.409] | 1.723 [1.680, 1.768] | 0.391 [0.362, 0.422] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 1.442 [1.400, 1.485] | 10.091 [9.812, 10.377] | 0.901 [0.820, 0.990] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.477 [1.451, 1.503] | 4.140 [3.423, 5.009] | 0.450 [0.391, 0.519] |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 1.288 [1.189, 1.396] | 2.158 [2.116, 2.201] | 0.434 [0.414, 0.455] |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 1.277 [1.134, 1.439] | 1.710 [1.691, 1.730] | 0.393 [0.363, 0.426] |
| `small-real.fresh.freya-neo.sender.warm` | xs | 1.031 [1.000, 1.062] | 0.765 [0.754, 0.775] | 0.753 [0.729, 0.778] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.949 [1.874, 2.027] | 10.213 [9.912, 10.524] | 0.995 [0.762, 1.299] |
| `small-real.noop.freya-neo.sender.warm` | xs | 1.152 [1.070, 1.240] | 0.621 [0.607, 0.635] | 0.154 [0.141, 0.167] |
| `small-real.noop.neo-freya.sender.warm` | xs | 7.641 [6.944, 8.408] | 4.657 [4.210, 5.150] | 0.692 [0.616, 0.777] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 1.544 [1.468, 1.623] | 1.362 [1.324, 1.401] | 0.919 [0.899, 0.940] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.373 [1.308, 1.441] | 1.353 [1.323, 1.382] | 0.921 [0.903, 0.941] |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 1.550 [1.420, 1.691] | 1.345 [1.313, 1.377] | 0.917 [0.884, 0.950] |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 1.359 [1.302, 1.417] | 1.328 [1.300, 1.358] | 0.922 [0.889, 0.957] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 13.584 | 13.091 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.391 | 12.992 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.383 | 0.235 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.290 | 0.193 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 14.376 | 14.129 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 16.107 | 15.384 |
| `mixed-threshold.noop.freya-neo.sender.warm` | 0.244 | 0.219 |
| `mixed-threshold.noop.neo-freya.sender.warm` | 0.191 | 0.169 |
| `small-deep.fresh.freya-neo.sender.warm` | 25.941 | 20.773 |
| `small-deep.fresh.neo-freya.sender.warm` | 10.516 | 11.142 |
| `small-deep.noop.freya-neo.sender.warm` | 20.002 | 3.083 |
| `small-deep.noop.neo-freya.sender.warm` | 3.033 | 1.628 |
| `small-flat.fresh.freya-neo.sender.warm` | 7.620 | 6.869 |
| `small-flat.fresh.neo-freya.sender.warm` | 7.803 | 4.066 |
| `small-flat.noop.freya-neo.sender.warm` | 0.747 | 0.314 |
| `small-flat.noop.neo-freya.sender.warm` | 0.769 | 0.303 |
| `small-opaque.fresh.freya-neo.sender.warm` | 7.579 | 6.848 |
| `small-opaque.fresh.neo-freya.sender.warm` | 8.133 | 3.879 |
| `small-opaque.noop.freya-neo.sender.warm` | 0.746 | 0.326 |
| `small-opaque.noop.neo-freya.sender.warm` | 0.807 | 0.319 |
| `small-real.fresh.freya-neo.sender.warm` | 24.426 | 18.572 |
| `small-real.fresh.neo-freya.sender.warm` | 14.360 | 14.202 |
| `small-real.noop.freya-neo.sender.warm` | 10.101 | 1.553 |
| `small-real.noop.neo-freya.sender.warm` | 2.331 | 1.614 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.232 | 0.213 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.185 | 0.168 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.231 | 0.212 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.185 | 0.167 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.0797 | 59 | 79 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0334 | 13 | 16 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 0.0665 | 42 | 56 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 0.0497 | 25 | 32 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs | 0.0363 | 14 | 18 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.2444 | 538 | 721 |
| `mixed-threshold.noop.freya-neo.sender.warm` | xs | 0.0996 | 92 | 122 |
| `mixed-threshold.noop.neo-freya.sender.warm` | xs | 0.0635 | 39 | 51 |
| `small-deep.fresh.freya-neo.sender.warm` | xs | 0.0827 | 64 | 85 |
| `small-deep.fresh.neo-freya.sender.warm` | xs | 0.5248 | 2474 | 3315 |
| `small-deep.noop.freya-neo.sender.warm` | xs | 0.2017 | 368 | 492 |
| `small-deep.noop.neo-freya.sender.warm` | xs | 0.1499 | 204 | 273 |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 0.0978 | 88 | 118 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.2891 | 753 | 1008 |
| `small-flat.noop.freya-neo.sender.warm` | xs | 0.0547 | 29 | 38 |
| `small-flat.noop.neo-freya.sender.warm` | xs | 0.1225 | 137 | 183 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 0.1462 | 194 | 259 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.2697 | 655 | 877 |
| `small-opaque.noop.freya-neo.sender.warm` | xs | 0.0738 | 51 | 68 |
| `small-opaque.noop.neo-freya.sender.warm` | xs | 0.1263 | 146 | 194 |
| `small-real.fresh.freya-neo.sender.warm` | xs | 0.0498 | 25 | 32 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.4459 | 1786 | 2393 |
| `small-real.noop.freya-neo.sender.warm` | xs | 0.1366 | 170 | 227 |
| `small-real.noop.neo-freya.sender.warm` | xs | 0.1820 | 300 | 401 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 0.0345 | 13 | 17 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.0754 | 54 | 71 |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 0.0558 | 30 | 40 |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 0.1041 | 100 | 133 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
