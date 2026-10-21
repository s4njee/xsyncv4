# G3-10g-small-push

Batching, scanning or framing settings let small and mixed trees use more of the 10GbE link.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T133652Z-G3-10g-small-push.
- Valid blocks: 15. Voided block attempts: 6.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | batch256 | 2 | 0.938 [0.624, 1.412] | 0.938 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | scan-all | 2 | 0.867 [0.229, 3.285] | 0.867 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | coalesce1m | 2 | 0.932 [0.495, 1.757] | 0.932 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-three | 2 | 0.876 [0.222, 3.466] | 0.876 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | z1-best | 2 | 0.917 [0.105, 8.026] | 0.917 | 1.0000 | too few blocks |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | batch256 | 2 | 0.975 [0.804, 1.183] | 0.975 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | scan-all | 2 | 1.006 [0.953, 1.061] | 1.006 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | coalesce1m | 2 | 0.971 [0.821, 1.148] | 0.971 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-three | 2 | 0.928 [0.615, 1.398] | 0.928 | 0.5000 | too few blocks |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | z1-best | 2 | 0.900 [0.887, 0.913] | 0.900 | 0.5000 | too few blocks |
| `real-congress.fresh.freya-mac.receiver.warm` | batch256 | 2 | 1.061 [0.589, 1.913] | 1.061 | 0.5000 | too few blocks |
| `real-congress.fresh.freya-mac.receiver.warm` | scan-all | 2 | 1.020 [0.455, 2.282] | 1.020 | 1.0000 | too few blocks |
| `real-congress.fresh.freya-mac.receiver.warm` | coalesce1m | 2 | 1.136 [0.315, 4.100] | 1.136 | 0.5000 | too few blocks |
| `real-congress.fresh.freya-mac.receiver.warm` | all-three | 2 | 1.141 [0.071, 18.307] | 1.141 | 1.0000 | too few blocks |
| `real-congress.fresh.freya-mac.receiver.warm` | z1-best | 2 | 0.966 [0.595, 1.568] | 0.966 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-freya.sender.warm` | batch256 | 2 | 1.058 [0.509, 2.201] | 1.058 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-freya.sender.warm` | scan-all | 2 | 1.030 [0.675, 1.573] | 1.030 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-freya.sender.warm` | coalesce1m | 2 | 1.035 [0.630, 1.701] | 1.035 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-freya.sender.warm` | all-three | 2 | 1.005 [0.954, 1.059] | 1.005 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-freya.sender.warm` | z1-best | 2 | 1.000 [0.461, 2.170] | 1.000 | 1.0000 | too few blocks |
| `small-deep.fresh.freya-mac.receiver.warm` | batch256 | 2 | 0.995 [0.589, 1.681] | 0.995 | 1.0000 | too few blocks |
| `small-deep.fresh.freya-mac.receiver.warm` | scan-all | 2 | 1.006 [0.462, 2.190] | 1.006 | 1.0000 | too few blocks |
| `small-deep.fresh.freya-mac.receiver.warm` | coalesce1m | 2 | 0.970 [0.527, 1.787] | 0.970 | 1.0000 | too few blocks |
| `small-deep.fresh.freya-mac.receiver.warm` | all-three | 2 | 0.964 [0.640, 1.451] | 0.964 | 0.5000 | too few blocks |
| `small-deep.fresh.freya-mac.receiver.warm` | z1-best | 2 | 0.975 [0.752, 1.264] | 0.975 | 0.5000 | too few blocks |
| `small-deep.fresh.mac-freya.sender.warm` | batch256 | 1 | 1.025 |  |  | too few blocks |
| `small-deep.fresh.mac-freya.sender.warm` | scan-all | 1 | 0.975 |  |  | too few blocks |
| `small-deep.fresh.mac-freya.sender.warm` | coalesce1m | 1 | 0.975 |  |  | too few blocks |
| `small-deep.fresh.mac-freya.sender.warm` | all-three | 1 | 0.971 |  |  | too few blocks |
| `small-deep.fresh.mac-freya.sender.warm` | z1-best | 1 | 0.995 |  |  | too few blocks |
| `small-flat.fresh.freya-mac.receiver.warm` | batch256 | 2 | 1.070 [0.107, 10.731] | 1.070 | 1.0000 | too few blocks |
| `small-flat.fresh.freya-mac.receiver.warm` | scan-all | 2 | 0.993 [0.134, 7.366] | 0.993 | 1.0000 | too few blocks |
| `small-flat.fresh.freya-mac.receiver.warm` | coalesce1m | 2 | 1.003 [0.600, 1.676] | 1.003 | 1.0000 | too few blocks |
| `small-flat.fresh.freya-mac.receiver.warm` | all-three | 2 | 0.974 [0.257, 3.694] | 0.974 | 1.0000 | too few blocks |
| `small-flat.fresh.freya-mac.receiver.warm` | z1-best | 2 | 1.004 [0.239, 4.217] | 1.004 | 1.0000 | too few blocks |
| `small-flat.fresh.mac-freya.sender.warm` | batch256 | 2 | 0.946 [0.908, 0.985] | 0.946 | 0.5000 | too few blocks |
| `small-flat.fresh.mac-freya.sender.warm` | scan-all | 2 | 1.001 [0.642, 1.560] | 1.001 | 1.0000 | too few blocks |
| `small-flat.fresh.mac-freya.sender.warm` | coalesce1m | 2 | 0.970 [0.919, 1.024] | 0.970 | 0.5000 | too few blocks |
| `small-flat.fresh.mac-freya.sender.warm` | all-three | 2 | 0.972 [0.781, 1.208] | 0.972 | 0.5000 | too few blocks |
| `small-flat.fresh.mac-freya.sender.warm` | z1-best | 2 | 0.951 [0.774, 1.169] | 0.951 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | batch256 | 0.994 [0.804, 1.229] | 0.977 [0.550, 1.736] | 0.936 [0.630, 1.389] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | scan-all | 0.952 [0.630, 1.438] | 1.003 [0.545, 1.845] | 0.860 [0.215, 3.433] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | coalesce1m | 0.960 [0.771, 1.196] | 0.913 [0.729, 1.145] | 0.926 [0.480, 1.787] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-three | 0.939 [0.658, 1.340] | 0.884 [0.274, 2.855] | 0.868 [0.223, 3.371] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | z1-best | 1.061 [0.671, 1.675] | 1.239 [0.947, 1.622] | 0.913 [0.103, 8.115] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | batch256 | 0.999 [0.925, 1.078] | 0.879 [0.277, 2.791] | 0.968 [0.783, 1.197] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | scan-all | 0.934 [0.387, 2.250] | 1.012 [0.299, 3.425] | 1.001 [0.866, 1.157] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | coalesce1m | 0.960 [0.309, 2.982] | 0.952 [0.517, 1.751] | 0.951 [0.659, 1.371] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-three | 0.938 [0.305, 2.885] | 0.947 [0.593, 1.512] | 0.922 [0.546, 1.557] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | z1-best | 1.109 [0.954, 1.289] | 1.171 [0.568, 2.413] | 0.895 [0.877, 0.913] |
| `real-congress.fresh.freya-mac.receiver.warm` | batch256 | 1.005 [0.687, 1.468] | 1.028 [0.662, 1.598] | 1.061 [0.592, 1.905] |
| `real-congress.fresh.freya-mac.receiver.warm` | scan-all | 1.008 [0.548, 1.854] | 0.916 [0.168, 4.999] | 1.020 [0.451, 2.303] |
| `real-congress.fresh.freya-mac.receiver.warm` | coalesce1m | 1.009 [0.714, 1.427] | 1.059 [0.277, 4.043] | 1.135 [0.318, 4.048] |
| `real-congress.fresh.freya-mac.receiver.warm` | all-three | 1.014 [0.554, 1.855] | 1.089 [0.710, 1.670] | 1.141 [0.072, 18.120] |
| `real-congress.fresh.freya-mac.receiver.warm` | z1-best | 1.007 [0.671, 1.511] | 0.546 [0.370, 0.806] | 0.966 [0.591, 1.578] |
| `real-congress.fresh.mac-freya.sender.warm` | batch256 | 1.001 [0.982, 1.020] | 0.777 [0.540, 1.118] | 1.063 [0.475, 2.376] |
| `real-congress.fresh.mac-freya.sender.warm` | scan-all | 0.993 [0.766, 1.287] | 0.889 [0.126, 6.255] | 1.035 [0.628, 1.707] |
| `real-congress.fresh.mac-freya.sender.warm` | coalesce1m | 0.979 [0.584, 1.639] | 0.816 [0.086, 7.696] | 1.035 [0.537, 1.997] |
| `real-congress.fresh.mac-freya.sender.warm` | all-three | 0.993 [0.818, 1.206] | 1.112 [0.985, 1.256] | 1.002 [0.944, 1.064] |
| `real-congress.fresh.mac-freya.sender.warm` | z1-best | 0.948 [0.650, 1.384] | 0.478 [0.426, 0.537] | 1.002 [0.466, 2.155] |
| `small-deep.fresh.freya-mac.receiver.warm` | batch256 | 0.999 [0.879, 1.134] | 1.018 [1.015, 1.021] | 0.995 [0.585, 1.692] |
| `small-deep.fresh.freya-mac.receiver.warm` | scan-all | 0.999 [0.883, 1.131] | 1.024 [0.799, 1.312] | 1.006 [0.460, 2.203] |
| `small-deep.fresh.freya-mac.receiver.warm` | coalesce1m | 0.992 [0.854, 1.152] | 1.020 [0.917, 1.135] | 0.970 [0.523, 1.798] |
| `small-deep.fresh.freya-mac.receiver.warm` | all-three | 0.994 [0.940, 1.051] | 1.016 [0.793, 1.302] | 0.964 [0.637, 1.458] |
| `small-deep.fresh.freya-mac.receiver.warm` | z1-best | 1.008 [0.961, 1.058] | 1.013 [0.897, 1.143] | 0.975 [0.754, 1.261] |
| `small-deep.fresh.mac-freya.sender.warm` | batch256 | 1.000 | 0.915 | 1.015 |
| `small-deep.fresh.mac-freya.sender.warm` | scan-all | 1.026 | 0.913 | 0.966 |
| `small-deep.fresh.mac-freya.sender.warm` | coalesce1m | 1.018 | 0.798 | 0.971 |
| `small-deep.fresh.mac-freya.sender.warm` | all-three | 0.997 | 0.895 | 0.954 |
| `small-deep.fresh.mac-freya.sender.warm` | z1-best | 0.978 | 1.038 | 0.985 |
| `small-flat.fresh.freya-mac.receiver.warm` | batch256 | 1.000 [0.417, 2.402] | 1.009 [0.416, 2.448] | 1.070 [0.105, 10.868] |
| `small-flat.fresh.freya-mac.receiver.warm` | scan-all | 0.990 [0.499, 1.963] | 0.995 [0.291, 3.402] | 0.992 [0.134, 7.371] |
| `small-flat.fresh.freya-mac.receiver.warm` | coalesce1m | 1.005 [0.720, 1.404] | 0.970 [0.144, 6.556] | 1.000 [0.605, 1.655] |
| `small-flat.fresh.freya-mac.receiver.warm` | all-three | 0.978 [0.465, 2.054] | 1.031 [0.809, 1.315] | 0.973 [0.256, 3.704] |
| `small-flat.fresh.freya-mac.receiver.warm` | z1-best | 0.967 [0.425, 2.201] | 1.459 [1.222, 1.742] | 1.004 [0.240, 4.189] |
| `small-flat.fresh.mac-freya.sender.warm` | batch256 | 1.060 [0.292, 3.854] | 0.585 [0.317, 1.081] | 0.943 [0.937, 0.949] |
| `small-flat.fresh.mac-freya.sender.warm` | scan-all | 0.979 [0.174, 5.509] | 0.902 [0.017, 47.595] | 0.998 [0.682, 1.459] |
| `small-flat.fresh.mac-freya.sender.warm` | coalesce1m | 0.998 [0.622, 1.599] | 0.651 [0.528, 0.803] | 0.961 [0.889, 1.040] |
| `small-flat.fresh.mac-freya.sender.warm` | all-three | 0.960 [0.515, 1.791] | 0.969 [0.053, 17.608] | 0.966 [0.815, 1.146] |
| `small-flat.fresh.mac-freya.sender.warm` | z1-best | 0.903 [0.279, 2.929] | 0.548 [0.225, 1.335] | 0.933 [0.882, 0.986] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | all-three | batch256 | coalesce1m | scan-all | xs-best | z1-best |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | 2.409 | 2.579 | 2.563 | 2.384 | 2.749 | 2.522 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | 1.559 | 1.640 | 1.632 | 1.691 | 1.681 | 1.513 |
| `real-congress.fresh.freya-mac.receiver.warm` | 37.124 | 34.526 | 36.945 | 33.168 | 32.533 | 31.425 |
| `real-congress.fresh.mac-freya.sender.warm` | 6.857 | 7.223 | 7.063 | 7.032 | 6.825 | 6.826 |
| `small-deep.fresh.freya-mac.receiver.warm` | 38.830 | 40.113 | 39.101 | 40.553 | 40.300 | 39.292 |
| `small-deep.fresh.mac-freya.sender.warm` | 6.210 | 6.556 | 6.237 | 6.234 | 6.396 | 6.364 |
| `small-flat.fresh.freya-mac.receiver.warm` | 9.913 | 10.890 | 10.203 | 10.104 | 10.174 | 10.212 |
| `small-flat.fresh.mac-freya.sender.warm` | 2.212 | 2.153 | 2.208 | 2.279 | 2.277 | 2.166 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | batch256 | 0.0455 | 21 | 27 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | scan-all | 0.1483 | 200 | 267 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | coalesce1m | 0.0705 | 47 | 62 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-three | 0.1531 | 213 | 284 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | z1-best | 0.2414 | 525 | 703 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | batch256 | 0.0215 | 8 | 8 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | scan-all | 0.0060 | 8 | 8 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | coalesce1m | 0.0186 | 8 | 8 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-three | 0.0457 | 21 | 28 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | z1-best | 0.0016 | 8 | 8 |
| `real-congress.fresh.freya-mac.receiver.warm` | batch256 | 0.0656 | 41 | 54 |
| `real-congress.fresh.freya-mac.receiver.warm` | scan-all | 0.0897 | 75 | 99 |
| `real-congress.fresh.freya-mac.receiver.warm` | coalesce1m | 0.1429 | 186 | 248 |
| `real-congress.fresh.freya-mac.receiver.warm` | all-three | 0.3089 | 859 | 1150 |
| `real-congress.fresh.freya-mac.receiver.warm` | z1-best | 0.0539 | 29 | 38 |
| `real-congress.fresh.mac-freya.sender.warm` | batch256 | 0.0815 | 62 | 82 |
| `real-congress.fresh.mac-freya.sender.warm` | scan-all | 0.0471 | 22 | 29 |
| `real-congress.fresh.mac-freya.sender.warm` | coalesce1m | 0.0553 | 30 | 39 |
| `real-congress.fresh.mac-freya.sender.warm` | all-three | 0.0058 | 8 | 8 |
| `real-congress.fresh.mac-freya.sender.warm` | z1-best | 0.0862 | 69 | 92 |
| `small-deep.fresh.freya-mac.receiver.warm` | batch256 | 0.0583 | 33 | 43 |
| `small-deep.fresh.freya-mac.receiver.warm` | scan-all | 0.0865 | 70 | 93 |
| `small-deep.fresh.freya-mac.receiver.warm` | coalesce1m | 0.0680 | 44 | 58 |
| `small-deep.fresh.freya-mac.receiver.warm` | all-three | 0.0456 | 21 | 27 |
| `small-deep.fresh.freya-mac.receiver.warm` | z1-best | 0.0289 | 10 | 13 |
| `small-flat.fresh.freya-mac.receiver.warm` | batch256 | 0.2566 | 593 | 794 |
| `small-flat.fresh.freya-mac.receiver.warm` | scan-all | 0.2230 | 449 | 601 |
| `small-flat.fresh.freya-mac.receiver.warm` | coalesce1m | 0.0572 | 32 | 42 |
| `small-flat.fresh.freya-mac.receiver.warm` | all-three | 0.1483 | 200 | 267 |
| `small-flat.fresh.freya-mac.receiver.warm` | z1-best | 0.1598 | 232 | 309 |
| `small-flat.fresh.mac-freya.sender.warm` | batch256 | 0.0046 | 8 | 8 |
| `small-flat.fresh.mac-freya.sender.warm` | scan-all | 0.0494 | 24 | 32 |
| `small-flat.fresh.mac-freya.sender.warm` | coalesce1m | 0.0060 | 8 | 8 |
| `small-flat.fresh.mac-freya.sender.warm` | all-three | 0.0243 | 8 | 10 |
| `small-flat.fresh.mac-freya.sender.warm` | z1-best | 0.0230 | 8 | 9 |

## Voided attempts

- mac reaches freya by en0, not en4
- xs-best: harness error: freya: `python3 /mnt/nvme/xsbench/lib/b135cedd700c/probe.py snapshot --interface enp27s0f0` exited 255: ssh: connect to host [host] p
