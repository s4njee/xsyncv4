# W0a-noise

On the Wi-Fi pair two identical arms are never called different, and sigma_d is within a factor of three of the wired pair's.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T025159Z-W0a-noise.
- Valid blocks: 192. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 12 | 0.981 [0.930, 1.036] | 0.981 [0.926, 1.041] | 0.4507 | inconclusive |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 12 | 0.982 [0.950, 1.015] | 0.983 [0.948, 1.017] | 0.2495 | inconclusive |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 12 | 0.989 [0.926, 1.056] | 0.980 [0.933, 1.048] | 0.7290 | inconclusive |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 12 | 0.995 [0.934, 1.060] | 0.993 [0.923, 1.064] | 0.8604 | inconclusive |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 12 | 0.990 [0.951, 1.031] | 1.002 [0.976, 1.021] | 0.7954 | inconclusive |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 12 | 1.416 [1.378, 1.456] | 1.426 [1.389, 1.455] | 0.0005 | slower |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 12 | 0.413 [0.196, 0.869] | 0.369 [0.221, 0.946] | 0.0176 | faster |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 12 | 0.777 [0.238, 2.540] | 0.860 [0.233, 3.175] | 0.6396 | inconclusive |
| `small-deep.fresh.mars-orion.sender.warm` | again | 12 | 0.927 [0.826, 1.041] | 0.956 [0.806, 1.041] | 0.2002 | inconclusive |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 12 | 0.614 [0.560, 0.672] | 0.640 [0.550, 0.667] | 0.0005 | faster |
| `small-deep.fresh.orion-mars.sender.warm` | again | 12 | 0.870 [0.662, 1.144] | 0.872 [0.639, 1.174] | 0.2847 | inconclusive |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 12 | 1.373 [1.032, 1.825] | 1.340 [0.989, 1.878] | 0.0352 | inconclusive |
| `small-deep.noop.mars-orion.sender.warm` | again | 12 | 1.181 [0.851, 1.641] | 1.218 [0.776, 1.699] | 0.2837 | inconclusive |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 12 | 1.459 [1.136, 1.874] | 1.467 [1.102, 1.903] | 0.0073 | slower |
| `small-deep.noop.orion-mars.sender.warm` | again | 12 | 0.871 [0.627, 1.210] | 0.932 [0.647, 1.190] | 0.4385 | inconclusive |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 12 | 2.042 [1.477, 2.824] | 2.079 [1.632, 2.633] | 0.0020 | slower |
| `small-flat.fresh.mars-orion.sender.warm` | again | 12 | 1.004 [0.993, 1.014] | 1.004 [0.992, 1.016] | 0.4575 | equivalent |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 12 | 1.218 [1.188, 1.250] | 1.218 [1.191, 1.253] | 0.0005 | slower |
| `small-flat.fresh.orion-mars.sender.warm` | again | 12 | 1.051 [0.828, 1.335] | 0.945 [0.860, 1.419] | 0.6523 | inconclusive |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 12 | 1.503 [1.098, 2.059] | 1.520 [0.978, 2.264] | 0.0278 | inconclusive |
| `small-flat.noop.mars-orion.sender.warm` | again | 12 | 1.050 [0.951, 1.159] | 1.077 [0.940, 1.168] | 0.2939 | inconclusive |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 12 | 2.342 [2.124, 2.583] | 2.296 [2.115, 2.611] | 0.0005 | slower |
| `small-flat.noop.orion-mars.sender.warm` | again | 12 | 0.887 [0.414, 1.901] | 1.000 [0.386, 1.531] | 0.7490 | inconclusive |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 12 | 1.741 [0.807, 3.758] | 2.278 [0.644, 3.549] | 0.1396 | inconclusive |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 12 | 0.992 [0.979, 1.005] | 0.992 [0.978, 1.007] | 0.2021 | equivalent |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 12 | 1.058 [1.036, 1.081] | 1.055 [1.035, 1.079] | 0.0005 | slower |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 12 | 1.045 [0.630, 1.734] | 1.035 [0.607, 1.842] | 0.7783 | inconclusive |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 12 | 1.200 [0.574, 2.508] | 0.932 [0.627, 2.374] | 0.6816 | inconclusive |
| `tiny-one.noop.mars-orion.sender.warm` | again | 12 | 0.980 [0.936, 1.025] | 0.992 [0.943, 1.020] | 0.4180 | inconclusive |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 12 | 1.044 [0.971, 1.122] | 1.051 [0.979, 1.130] | 0.2168 | inconclusive |
| `tiny-one.noop.orion-mars.sender.warm` | again | 12 | 1.114 [0.605, 2.052] | 0.987 [0.691, 1.389] | 0.8306 | inconclusive |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 12 | 0.945 [0.756, 1.182] | 0.977 [0.764, 1.179] | 0.6353 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 1.003 [0.983, 1.023] | 0.985 [0.929, 1.045] | 1.001 [0.995, 1.008] |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 0.733 [0.718, 0.748] | 0.980 [0.942, 1.019] | 0.129 [0.128, 0.131] |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 0.978 [0.950, 1.007] | 0.989 [0.927, 1.056] | 1.000 [0.993, 1.008] |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 0.619 [0.600, 0.639] | 0.995 [0.934, 1.060] | 0.158 [0.156, 0.159] |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 0.992 [0.953, 1.033] | 0.990 [0.951, 1.030] | 0.999 [0.983, 1.015] |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 0.625 [0.597, 0.655] | 1.412 [1.373, 1.451] | 0.833 [0.820, 0.846] |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 0.997 [0.947, 1.050] | 0.406 [0.188, 0.877] | 0.997 [0.981, 1.014] |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 0.609 [0.560, 0.662] | 0.852 [0.276, 2.634] | 0.958 [0.947, 0.968] |
| `small-deep.fresh.mars-orion.sender.warm` | again | 0.987 [0.968, 1.006] | 0.926 [0.828, 1.036] | 1.023 [0.947, 1.105] |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 0.597 [0.586, 0.609] | 0.620 [0.566, 0.679] | 0.140 [0.134, 0.147] |
| `small-deep.fresh.orion-mars.sender.warm` | again | 0.964 [0.842, 1.105] | 0.872 [0.665, 1.143] | 0.981 [0.866, 1.110] |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 0.623 [0.546, 0.710] | 1.366 [1.030, 1.813] | 0.224 [0.190, 0.265] |
| `small-deep.noop.mars-orion.sender.warm` | again | 0.995 [0.895, 1.105] | 1.181 [0.851, 1.640] | 1.002 [0.988, 1.015] |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 0.287 [0.247, 0.332] | 1.459 [1.136, 1.874] | 0.144 [0.142, 0.145] |
| `small-deep.noop.orion-mars.sender.warm` | again | 1.010 [0.953, 1.070] | 0.898 [0.646, 1.248] | 1.036 [1.007, 1.065] |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 0.411 [0.367, 0.459] | 2.000 [1.470, 2.719] | 0.206 [0.200, 0.211] |
| `small-flat.fresh.mars-orion.sender.warm` | again | 0.999 [0.992, 1.006] | 1.016 [0.997, 1.035] | 1.003 [0.997, 1.010] |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 0.919 [0.903, 0.935] | 1.220 [1.193, 1.249] | 0.128 [0.128, 0.129] |
| `small-flat.fresh.orion-mars.sender.warm` | again | 0.959 [0.892, 1.030] | 1.051 [0.829, 1.333] | 1.153 [0.858, 1.550] |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 0.735 [0.647, 0.835] | 1.503 [1.099, 2.055] | 0.194 [0.147, 0.258] |
| `small-flat.noop.mars-orion.sender.warm` | again | 0.990 [0.919, 1.065] | 1.050 [0.951, 1.158] | 1.003 [0.991, 1.016] |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 1.041 [0.940, 1.153] | 2.332 [2.116, 2.571] | 0.592 [0.587, 0.597] |
| `small-flat.noop.orion-mars.sender.warm` | again | 0.929 [0.867, 0.994] | 0.904 [0.418, 1.957] | 1.002 [0.990, 1.015] |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 0.815 [0.710, 0.936] | 1.541 [0.730, 3.252] | 0.774 [0.769, 0.779] |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 0.997 [0.971, 1.024] | 0.992 [0.980, 1.005] | 1.000 [0.994, 1.006] |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 0.752 [0.720, 0.786] | 1.057 [1.036, 1.079] | 0.997 [0.990, 1.005] |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 1.011 [0.988, 1.033] | 0.996 [0.595, 1.666] | 0.999 [0.993, 1.004] |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 0.857 [0.842, 0.872] | 1.079 [0.484, 2.405] | 0.978 [0.970, 0.987] |
| `tiny-one.noop.mars-orion.sender.warm` | again | 1.015 [0.988, 1.043] | 0.980 [0.937, 1.025] | 0.999 [0.992, 1.006] |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 0.739 [0.716, 0.764] | 1.044 [0.972, 1.120] | 1.000 [0.996, 1.004] |
| `tiny-one.noop.orion-mars.sender.warm` | again | 0.998 [0.984, 1.013] | 1.013 [0.533, 1.924] | 1.002 [0.994, 1.009] |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 0.843 [0.825, 0.861] | 0.894 [0.626, 1.275] | 0.991 [0.978, 1.003] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | 21.232 | 21.244 | 21.635 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | 23.988 | 24.123 | 24.247 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | 0.435 | 0.623 | 0.440 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | 0.585 | 1.102 | 1.418 |
| `small-deep.fresh.mars-orion.sender.warm` | 35.986 | 23.820 | 38.817 |
| `small-deep.fresh.orion-mars.sender.warm` | 12.169 | 19.201 | 13.989 |
| `small-deep.noop.mars-orion.sender.warm` | 8.937 | 11.038 | 7.565 |
| `small-deep.noop.orion-mars.sender.warm` | 4.040 | 9.473 | 4.639 |
| `small-flat.fresh.mars-orion.sender.warm` | 15.537 | 18.863 | 15.481 |
| `small-flat.fresh.orion-mars.sender.warm` | 7.098 | 10.149 | 6.752 |
| `small-flat.noop.mars-orion.sender.warm` | 0.712 | 1.588 | 0.678 |
| `small-flat.noop.orion-mars.sender.warm` | 0.872 | 1.712 | 0.983 |
| `tiny-one.fresh.mars-orion.sender.warm` | 0.366 | 0.390 | 0.369 |
| `tiny-one.fresh.orion-mars.sender.warm` | 0.479 | 0.550 | 0.458 |
| `tiny-one.noop.mars-orion.sender.warm` | 0.368 | 0.392 | 0.376 |
| `tiny-one.noop.orion-mars.sender.warm` | 0.725 | 0.615 | 0.650 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-orion.sender.warm` | again | 0.0847 | 67 | 89 |
| `mixed-bimodal.fresh.mars-orion.sender.warm` | rsync | 0.0516 | 26 | 35 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | again | 0.1034 | 98 | 131 |
| `mixed-bimodal.fresh.orion-mars.sender.warm` | rsync | 0.1002 | 93 | 123 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | again | 0.0636 | 39 | 51 |
| `mixed-bimodal.noop.mars-orion.sender.warm` | rsync | 0.0436 | 20 | 25 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | again | 1.1724 | 12337 | 16534 |
| `mixed-bimodal.noop.orion-mars.sender.warm` | rsync | 1.8646 | 31198 | 41813 |
| `small-deep.fresh.mars-orion.sender.warm` | again | 0.1823 | 301 | 402 |
| `small-deep.fresh.mars-orion.sender.warm` | rsync | 0.1426 | 185 | 247 |
| `small-deep.fresh.orion-mars.sender.warm` | again | 0.4306 | 1666 | 2232 |
| `small-deep.fresh.orion-mars.sender.warm` | rsync | 0.4487 | 1809 | 2423 |
| `small-deep.noop.mars-orion.sender.warm` | again | 0.5169 | 2400 | 3216 |
| `small-deep.noop.mars-orion.sender.warm` | rsync | 0.3942 | 1397 | 1871 |
| `small-deep.noop.orion-mars.sender.warm` | again | 0.5172 | 2403 | 3220 |
| `small-deep.noop.orion-mars.sender.warm` | rsync | 0.5104 | 2340 | 3135 |
| `small-flat.fresh.mars-orion.sender.warm` | again | 0.0167 | 8 | 8 |
| `small-flat.fresh.mars-orion.sender.warm` | rsync | 0.0400 | 17 | 22 |
| `small-flat.fresh.orion-mars.sender.warm` | again | 0.3764 | 1274 | 1706 |
| `small-flat.fresh.orion-mars.sender.warm` | rsync | 0.4950 | 2201 | 2950 |
| `small-flat.noop.mars-orion.sender.warm` | again | 0.1558 | 220 | 294 |
| `small-flat.noop.mars-orion.sender.warm` | rsync | 0.1539 | 215 | 287 |
| `small-flat.noop.orion-mars.sender.warm` | again | 1.1995 | 12912 | 17305 |
| `small-flat.noop.orion-mars.sender.warm` | rsync | 1.2111 | 13163 | 17641 |
| `tiny-one.fresh.mars-orion.sender.warm` | again | 0.0208 | 8 | 8 |
| `tiny-one.fresh.mars-orion.sender.warm` | rsync | 0.0334 | 13 | 16 |
| `tiny-one.fresh.orion-mars.sender.warm` | again | 0.7963 | 5692 | 7628 |
| `tiny-one.fresh.orion-mars.sender.warm` | rsync | 1.1607 | 12090 | 16203 |
| `tiny-one.noop.mars-orion.sender.warm` | again | 0.0715 | 48 | 64 |
| `tiny-one.noop.mars-orion.sender.warm` | rsync | 0.1134 | 118 | 157 |
| `tiny-one.noop.orion-mars.sender.warm` | again | 0.9609 | 8287 | 11106 |
| `tiny-one.noop.orion-mars.sender.warm` | rsync | 0.3521 | 1115 | 1494 |
