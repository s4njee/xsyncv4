# W0b-noise

On the Wi-Fi pair two identical arms are never called different, and sigma_d is within a factor of three of the wired pair's.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T112841Z-W0b-noise.
- Valid blocks: 160. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 10 | 0.991 [0.940, 1.044] | 0.985 [0.948, 1.044] | 0.6992 | inconclusive |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 10 | 1.008 [0.949, 1.072] | 0.997 [0.958, 1.086] | 0.8633 | inconclusive |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 10 | 0.983 [0.833, 1.161] | 0.997 [0.819, 1.162] | 0.7520 | inconclusive |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 10 | 0.907 [0.783, 1.050] | 0.912 [0.793, 1.014] | 0.1582 | inconclusive |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 10 | 0.986 [0.977, 0.996] | 0.987 [0.976, 0.997] | 0.0156 | equivalent |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 10 | 1.422 [1.395, 1.450] | 1.422 [1.394, 1.448] | 0.0020 | slower |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 10 | 0.862 [0.344, 2.161] | 1.066 [0.298, 1.982] | 0.8145 | inconclusive |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 10 | 1.695 [0.555, 5.182] | 1.809 [0.440, 6.308] | 0.3496 | inconclusive |
| `small-deep.fresh.mars-orion.sender.warm` | again | 10 | 1.123 [0.944, 1.336] | 1.073 [0.951, 1.375] | 0.1797 | inconclusive |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 10 | 0.641 [0.607, 0.677] | 0.639 [0.609, 0.677] | 0.0020 | faster |
| `small-deep.fresh.orion-mars.sender.warm` | again | 10 | 0.946 [0.792, 1.130] | 0.974 [0.780, 1.112] | 0.5527 | inconclusive |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 10 | 2.546 [1.823, 3.554] | 2.513 [1.738, 3.631] | 0.0020 | slower |
| `small-deep.noop.mars-orion.sender.warm` | again | 10 | 1.258 [0.845, 1.871] | 1.218 [0.841, 1.929] | 0.2285 | inconclusive |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 10 | 1.513 [1.249, 1.831] | 1.515 [1.242, 1.804] | 0.0020 | slower |
| `small-deep.noop.orion-mars.sender.warm` | again | 10 | 1.705 [0.881, 3.303] | 1.886 [0.895, 3.355] | 0.1035 | inconclusive |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 10 | 2.522 [1.594, 3.992] | 2.585 [1.593, 3.939] | 0.0078 | slower |
| `small-flat.fresh.mars-orion.sender.warm` | again | 10 | 0.987 [0.969, 1.005] | 0.987 [0.966, 1.005] | 0.1348 | inconclusive |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 10 | 1.190 [1.152, 1.230] | 1.196 [1.151, 1.225] | 0.0020 | slower |
| `small-flat.fresh.orion-mars.sender.warm` | again | 10 | 1.056 [0.860, 1.295] | 1.003 [0.858, 1.306] | 0.6074 | inconclusive |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 10 | 1.613 [1.143, 2.277] | 1.583 [1.117, 2.296] | 0.0156 | slower |
| `small-flat.noop.mars-orion.sender.warm` | again | 10 | 0.946 [0.843, 1.062] | 0.957 [0.847, 1.060] | 0.2949 | inconclusive |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 10 | 2.399 [2.149, 2.679] | 2.428 [2.101, 2.808] | 0.0020 | slower |
| `small-flat.noop.orion-mars.sender.warm` | again | 10 | 1.382 [0.513, 3.722] | 0.953 [0.568, 3.933] | 0.4922 | inconclusive |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 10 | 2.268 [1.079, 4.768] | 1.803 [1.203, 4.801] | 0.0117 | slower |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 10 | 1.016 [0.974, 1.058] | 1.012 [0.980, 1.061] | 0.5039 | inconclusive |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 10 | 1.054 [1.031, 1.079] | 1.054 [1.032, 1.077] | 0.0039 | slower |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 10 | 1.086 [0.500, 2.360] | 0.974 [0.571, 2.554] | 0.8887 | inconclusive |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 10 | 0.888 [0.559, 1.412] | 0.969 [0.586, 1.268] | 0.5879 | inconclusive |
| `tiny-one.noop.mars-orion.sender.warm` | again | 10 | 0.939 [0.842, 1.047] | 0.985 [0.806, 1.016] | 0.2598 | inconclusive |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 10 | 1.033 [0.981, 1.087] | 1.052 [0.976, 1.078] | 0.1895 | inconclusive |
| `tiny-one.noop.orion-mars.sender.warm` | again | 10 | 0.891 [0.544, 1.458] | 0.918 [0.543, 1.399] | 0.5938 | inconclusive |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 10 | 0.633 [0.211, 1.898] | 0.619 [0.217, 2.011] | 0.3691 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 1.007 [0.997, 1.017] | 0.995 [0.941, 1.052] | 0.994 [0.987, 1.000] |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 0.721 [0.708, 0.734] | 1.007 [0.945, 1.072] | 0.128 [0.127, 0.129] |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 0.988 [0.950, 1.027] | 0.983 [0.833, 1.161] | 1.000 [0.994, 1.006] |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 0.618 [0.587, 0.650] | 0.907 [0.784, 1.051] | 0.158 [0.156, 0.160] |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 0.978 [0.912, 1.049] | 0.987 [0.977, 0.997] | 0.999 [0.986, 1.012] |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 0.626 [0.595, 0.658] | 1.417 [1.391, 1.444] | 0.836 [0.823, 0.850] |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 0.983 [0.923, 1.046] | 0.706 [0.291, 1.711] | 0.997 [0.985, 1.008] |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 0.594 [0.549, 0.642] | 1.461 [0.451, 4.728] | 0.949 [0.938, 0.959] |
| `small-deep.fresh.mars-orion.sender.warm` | again | 1.028 [0.994, 1.063] | 1.123 [0.949, 1.330] | 0.984 [0.908, 1.066] |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 0.597 [0.585, 0.609] | 0.649 [0.615, 0.686] | 0.135 [0.126, 0.145] |
| `small-deep.fresh.orion-mars.sender.warm` | again | 0.970 [0.863, 1.091] | 0.947 [0.793, 1.130] | 0.991 [0.820, 1.197] |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 0.717 [0.612, 0.840] | 2.528 [1.815, 3.521] | 0.209 [0.174, 0.250] |
| `small-deep.noop.mars-orion.sender.warm` | again | 1.033 [0.932, 1.144] | 1.258 [0.846, 1.870] | 1.001 [0.983, 1.018] |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 0.292 [0.258, 0.329] | 1.512 [1.249, 1.831] | 0.144 [0.141, 0.146] |
| `small-deep.noop.orion-mars.sender.warm` | again | 0.986 [0.883, 1.100] | 1.730 [0.900, 3.326] | 1.021 [0.987, 1.057] |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 0.382 [0.347, 0.421] | 2.491 [1.568, 3.956] | 0.203 [0.196, 0.210] |
| `small-flat.fresh.mars-orion.sender.warm` | again | 0.992 [0.980, 1.006] | 0.999 [0.981, 1.017] | 0.999 [0.995, 1.004] |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 0.904 [0.877, 0.931] | 1.176 [1.129, 1.225] | 0.127 [0.126, 0.128] |
| `small-flat.fresh.orion-mars.sender.warm` | again | 0.929 [0.818, 1.055] | 1.056 [0.861, 1.295] | 1.133 [0.793, 1.618] |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 0.715 [0.636, 0.805] | 1.613 [1.145, 2.273] | 0.209 [0.147, 0.295] |
| `small-flat.noop.mars-orion.sender.warm` | again | 1.028 [0.945, 1.119] | 0.953 [0.856, 1.061] | 0.995 [0.984, 1.005] |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 1.052 [0.940, 1.178] | 2.388 [2.139, 2.666] | 0.591 [0.583, 0.599] |
| `small-flat.noop.orion-mars.sender.warm` | again | 1.001 [0.890, 1.126] | 1.665 [0.595, 4.660] | 0.987 [0.969, 1.005] |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 0.787 [0.685, 0.904] | 2.266 [1.075, 4.775] | 0.765 [0.752, 0.778] |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 0.996 [0.966, 1.027] | 1.015 [0.975, 1.058] | 0.998 [0.991, 1.005] |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 0.728 [0.706, 0.751] | 1.054 [1.030, 1.078] | 0.992 [0.984, 1.000] |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 1.001 [0.981, 1.022] | 0.876 [0.381, 2.012] | 1.005 [0.998, 1.012] |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 0.852 [0.825, 0.881] | 0.720 [0.450, 1.153] | 0.996 [0.984, 1.008] |
| `tiny-one.noop.mars-orion.sender.warm` | again | 1.000 [0.968, 1.033] | 0.939 [0.843, 1.046] | 1.000 [0.992, 1.009] |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 0.721 [0.705, 0.738] | 1.032 [0.981, 1.086] | 1.000 [0.992, 1.009] |
| `tiny-one.noop.orion-mars.sender.warm` | again | 0.983 [0.945, 1.022] | 0.931 [0.539, 1.608] | 1.000 [0.992, 1.009] |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 0.832 [0.798, 0.867] | 0.794 [0.255, 2.478] | 0.994 [0.986, 1.002] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | 22.215 | 22.606 | 22.421 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | 28.167 | 25.986 | 28.645 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | 0.432 | 0.622 | 0.438 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | 0.561 | 1.103 | 0.651 |
| `small-deep.fresh.mars-orion.sender.warm` | 41.506 | 23.685 | 36.964 |
| `small-deep.fresh.orion-mars.sender.warm` | 12.026 | 32.362 | 12.713 |
| `small-deep.noop.mars-orion.sender.warm` | 9.120 | 10.970 | 7.252 |
| `small-deep.noop.orion-mars.sender.warm` | 7.122 | 10.533 | 4.176 |
| `small-flat.fresh.mars-orion.sender.warm` | 15.565 | 18.773 | 15.772 |
| `small-flat.fresh.orion-mars.sender.warm` | 8.294 | 12.677 | 7.857 |
| `small-flat.noop.mars-orion.sender.warm` | 0.632 | 1.603 | 0.668 |
| `small-flat.noop.orion-mars.sender.warm` | 1.186 | 1.947 | 0.858 |
| `tiny-one.fresh.mars-orion.sender.warm` | 0.373 | 0.388 | 0.368 |
| `tiny-one.fresh.orion-mars.sender.warm` | 0.575 | 0.471 | 0.530 |
| `tiny-one.noop.mars-orion.sender.warm` | 0.364 | 0.401 | 0.388 |
| `tiny-one.noop.orion-mars.sender.warm` | 0.800 | 0.569 | 0.898 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 0.0732 | 51 | 67 |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 0.0852 | 68 | 90 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 0.2320 | 485 | 650 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 0.2050 | 380 | 508 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 0.0128 | 8 | 8 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 0.0268 | 9 | 11 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 1.2847 | 14811 | 19850 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 1.5619 | 21894 | 29343 |
| `small-deep.fresh.mars-orion.sender.warm` | again | 0.2424 | 530 | 709 |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 0.0761 | 54 | 72 |
| `small-deep.fresh.orion-mars.sender.warm` | again | 0.2480 | 555 | 742 |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 0.4665 | 1956 | 2620 |
| `small-deep.noop.mars-orion.sender.warm` | again | 0.5551 | 2767 | 3708 |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 0.2671 | 643 | 861 |
| `small-deep.noop.orion-mars.sender.warm` | again | 0.9240 | 7664 | 10271 |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 0.6417 | 3698 | 4955 |
| `small-flat.fresh.mars-orion.sender.warm` | again | 0.0252 | 8 | 10 |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 0.0458 | 21 | 28 |
| `small-flat.fresh.orion-mars.sender.warm` | again | 0.2860 | 736 | 986 |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 0.4814 | 2082 | 2790 |
| `small-flat.noop.mars-orion.sender.warm` | again | 0.1616 | 237 | 316 |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 0.1540 | 215 | 288 |
| `small-flat.noop.orion-mars.sender.warm` | again | 1.3850 | 17215 | 23072 |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 1.0388 | 9685 | 12980 |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 0.0578 | 32 | 43 |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 0.0317 | 12 | 15 |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 1.0849 | 10564 | 14158 |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 0.6472 | 3761 | 5040 |
| `tiny-one.noop.mars-orion.sender.warm` | again | 0.1526 | 211 | 283 |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 0.0717 | 49 | 64 |
| `tiny-one.noop.orion-mars.sender.warm` | again | 0.6887 | 4258 | 5707 |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 1.5346 | 21133 | 28323 |
