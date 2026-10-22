# S3-mac-mars-sentinel

Hour by hour, the A/A ratio stays within 5% of 1 and the xs to rsync ratio stays where E6b's rsync arm put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T144634Z-S3-mac-mars-sentinel-s0001, 20261018T144634Z-S3-mac-mars-sentinel-s0002, 20261018T144635Z-S3-mac-mars-sentinel-s0003, 20261018T144636Z-S3-mac-mars-sentinel-s0004, 20261018T144637Z-S3-mac-mars-sentinel-s0005, 20261018T144637Z-S3-mac-mars-sentinel-s0006.
- Valid blocks: 72. Voided block attempts: 25.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 10 | 1.014 [0.985, 1.044] | 1.016 [0.985, 1.041] | 0.3086 | equivalent |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 10 | 3.198 [2.778, 3.681] | 3.193 [2.766, 3.689] | 0.0020 | slower |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 8 | 1.047 [0.929, 1.179] | 1.056 [0.912, 1.203] | 0.3984 | inconclusive |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 8 | 2.292 [2.129, 2.467] | 2.290 [2.114, 2.494] | 0.0078 | slower |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 10 | 0.908 [0.677, 1.217] | 1.004 [0.633, 1.151] | 0.6797 | inconclusive |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 10 | 1.266 [0.946, 1.694] | 1.329 [0.828, 1.682] | 0.1074 | inconclusive |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 8 | 0.970 [0.895, 1.050] | 0.961 [0.895, 1.063] | 0.3828 | inconclusive |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 8 | 1.140 [1.031, 1.261] | 1.141 [1.022, 1.296] | 0.0234 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | again | 10 | 0.980 [0.942, 1.020] | 0.990 [0.938, 1.015] | 0.3145 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 10 | 2.642 [1.709, 4.083] | 2.402 [1.350, 4.264] | 0.0020 | slower |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 8 | 1.020 [0.948, 1.097] | 1.024 [0.939, 1.100] | 0.5312 | inconclusive |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 8 | 1.590 [1.487, 1.701] | 1.599 [1.477, 1.692] | 0.0078 | slower |
| `small-flat.noop.mac-mars.sender.warm` | again | 10 | 1.078 [1.015, 1.145] | 1.077 [1.022, 1.142] | 0.0254 | inconclusive |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 10 | 2.129 [1.978, 2.291] | 2.091 [1.974, 2.292] | 0.0020 | slower |
| `small-flat.noop.mars-mac.receiver.warm` | again | 8 | 0.937 [0.858, 1.024] | 0.922 [0.852, 1.055] | 0.1172 | inconclusive |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 8 | 1.796 [1.558, 2.071] | 1.796 [1.526, 2.107] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 1.019 [0.970, 1.070] | 1.018 [0.985, 1.052] | 1.024 [0.972, 1.080] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.278 [1.195, 1.366] | 2.924 [2.537, 3.369] | 0.078 [0.076, 0.081] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 1.039 [0.991, 1.090] | 1.044 [0.929, 1.172] | 0.971 [0.856, 1.103] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.277 [1.231, 1.325] | 2.250 [2.094, 2.418] | 1.526 [1.387, 1.679] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.985 [0.930, 1.043] | 0.909 [0.682, 1.213] | 1.003 [0.983, 1.024] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.275 [0.260, 0.292] | 1.262 [0.949, 1.678] | 0.901 [0.878, 0.926] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 1.005 [0.970, 1.040] | 0.973 [0.914, 1.036] | 1.000 [0.966, 1.036] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.398 [0.360, 0.441] | 1.119 [1.026, 1.220] | 0.817 [0.799, 0.835] |
| `small-flat.fresh.mac-mars.sender.warm` | again | 0.985 [0.849, 1.144] | 0.982 [0.949, 1.016] | 1.067 [0.934, 1.219] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.734 [0.595, 0.906] | 2.450 [1.628, 3.687] | 0.115 [0.096, 0.138] |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 1.011 [0.964, 1.060] | 1.023 [0.951, 1.100] | 0.932 [0.836, 1.038] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.367 [1.321, 1.414] | 1.581 [1.477, 1.692] | 1.461 [1.266, 1.687] |
| `small-flat.noop.mac-mars.sender.warm` | again | 0.984 [0.793, 1.222] | 1.080 [1.018, 1.145] | 0.990 [0.955, 1.026] |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.254 [0.188, 0.343] | 2.110 [1.963, 2.269] | 0.682 [0.652, 0.713] |
| `small-flat.noop.mars-mac.receiver.warm` | again | 0.932 [0.852, 1.019] | 0.944 [0.873, 1.021] | 0.683 [0.368, 1.269] |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.496 [0.417, 0.590] | 1.698 [1.493, 1.931] | 0.213 [0.136, 0.333] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 1.732 | 5.463 | 1.708 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 3.922 | 8.586 | 3.746 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.265 | 0.370 | 0.292 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | 0.315 | 0.371 | 0.325 |
| `small-flat.fresh.mac-mars.sender.warm` | 3.738 | 10.075 | 3.814 |
| `small-flat.fresh.mars-mac.receiver.warm` | 16.871 | 26.305 | 16.539 |
| `small-flat.noop.mac-mars.sender.warm` | 0.372 | 0.735 | 0.345 |
| `small-flat.noop.mars-mac.receiver.warm` | 0.548 | 1.050 | 0.584 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 0.0405 | 17 | 22 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.1968 | 350 | 468 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 0.1426 | 185 | 247 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.0883 | 72 | 96 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.4096 | 1508 | 2020 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.4070 | 1489 | 1995 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 0.0954 | 84 | 112 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.1204 | 133 | 177 |
| `small-flat.fresh.mac-mars.sender.warm` | again | 0.0561 | 31 | 40 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.6087 | 3327 | 4458 |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 0.0871 | 71 | 94 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.0805 | 61 | 80 |
| `small-flat.noop.mac-mars.sender.warm` | again | 0.0847 | 67 | 89 |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.1026 | 97 | 129 |
| `small-flat.noop.mars-mac.receiver.warm` | again | 0.1060 | 103 | 138 |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.1702 | 262 | 351 |

## Voided attempts

- mars reaches mac by enp24s0f0, not enp25s0f0
- round trip is 3.831 ms, above 2.0
