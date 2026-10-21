# S3-mac-mars-sentinel

Hour by hour, the A/A ratio stays within 5% of 1 and the xs to rsync ratio stays where E6b's rsync arm put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T144634Z-S3-mac-mars-sentinel-s0001, 20261018T144634Z-S3-mac-mars-sentinel-s0002, 20261018T144635Z-S3-mac-mars-sentinel-s0003, 20261018T144636Z-S3-mac-mars-sentinel-s0004.
- Valid blocks: 64. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 8 | 1.018 [0.982, 1.056] | 1.020 [0.982, 1.058] | 0.2812 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 8 | 3.085 [2.620, 3.634] | 3.028 [2.639, 3.694] | 0.0078 | slower |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 8 | 1.047 [0.929, 1.179] | 1.056 [0.912, 1.203] | 0.3984 | inconclusive |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 8 | 2.292 [2.129, 2.467] | 2.290 [2.114, 2.494] | 0.0078 | slower |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 8 | 1.056 [0.938, 1.190] | 1.023 [0.937, 1.164] | 0.2891 | inconclusive |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 8 | 1.336 [1.249, 1.430] | 1.331 [1.241, 1.446] | 0.0078 | slower |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 8 | 0.970 [0.895, 1.050] | 0.961 [0.895, 1.063] | 0.3828 | inconclusive |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 8 | 1.140 [1.031, 1.261] | 1.141 [1.022, 1.296] | 0.0234 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | again | 8 | 0.990 [0.942, 1.040] | 0.992 [0.929, 1.030] | 0.7266 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 8 | 2.374 [1.389, 4.057] | 2.367 [1.287, 4.414] | 0.0078 | slower |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 8 | 1.020 [0.948, 1.097] | 1.024 [0.939, 1.100] | 0.5312 | inconclusive |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 8 | 1.590 [1.487, 1.701] | 1.599 [1.477, 1.692] | 0.0078 | slower |
| `small-flat.noop.mac-mars.sender.warm` | again | 8 | 1.086 [1.005, 1.175] | 1.085 [0.984, 1.155] | 0.0547 | inconclusive |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 8 | 2.120 [1.925, 2.336] | 2.079 [1.946, 2.341] | 0.0078 | slower |
| `small-flat.noop.mars-mac.receiver.warm` | again | 8 | 0.937 [0.858, 1.024] | 0.922 [0.852, 1.055] | 0.1172 | inconclusive |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 8 | 1.796 [1.558, 2.071] | 1.796 [1.526, 2.107] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 1.018 [0.956, 1.085] | 1.007 [0.970, 1.045] | 1.041 [0.982, 1.103] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.308 [1.217, 1.407] | 2.762 [2.394, 3.187] | 0.078 [0.075, 0.081] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 1.039 [0.991, 1.090] | 1.044 [0.929, 1.172] | 0.971 [0.856, 1.103] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.277 [1.231, 1.325] | 2.250 [2.094, 2.418] | 1.526 [1.387, 1.679] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.991 [0.941, 1.043] | 1.056 [0.938, 1.187] | 1.004 [0.993, 1.016] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.267 [0.256, 0.278] | 1.332 [1.247, 1.422] | 0.891 [0.870, 0.912] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 1.005 [0.970, 1.040] | 0.973 [0.914, 1.036] | 1.000 [0.966, 1.036] |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.398 [0.360, 0.441] | 1.119 [1.026, 1.220] | 0.817 [0.799, 0.835] |
| `small-flat.fresh.mac-mars.sender.warm` | again | 0.973 [0.800, 1.182] | 0.990 [0.948, 1.033] | 1.029 [0.908, 1.166] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.695 [0.538, 0.896] | 2.212 [1.340, 3.651] | 0.108 [0.091, 0.129] |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 1.011 [0.964, 1.060] | 1.023 [0.951, 1.100] | 0.932 [0.836, 1.038] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.367 [1.321, 1.414] | 1.581 [1.477, 1.692] | 1.461 [1.266, 1.687] |
| `small-flat.noop.mac-mars.sender.warm` | again | 0.922 [0.739, 1.150] | 1.084 [1.004, 1.171] | 0.976 [0.945, 1.007] |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.227 [0.165, 0.311] | 2.104 [1.912, 2.316] | 0.666 [0.643, 0.690] |
| `small-flat.noop.mars-mac.receiver.warm` | again | 0.932 [0.852, 1.019] | 0.944 [0.873, 1.021] | 0.683 [0.368, 1.269] |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.496 [0.417, 0.590] | 1.698 [1.493, 1.931] | 0.213 [0.136, 0.333] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 1.680 | 5.090 | 1.650 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 3.922 | 8.586 | 3.746 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.267 | 0.338 | 0.253 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | 0.315 | 0.371 | 0.325 |
| `small-flat.fresh.mac-mars.sender.warm` | 3.697 | 8.865 | 3.734 |
| `small-flat.fresh.mars-mac.receiver.warm` | 16.871 | 26.305 | 16.539 |
| `small-flat.noop.mac-mars.sender.warm` | 0.377 | 0.735 | 0.347 |
| `small-flat.noop.mars-mac.receiver.warm` | 0.548 | 1.050 | 0.584 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | again | 0.0433 | 19 | 25 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.1957 | 346 | 463 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | again | 0.1426 | 185 | 247 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.0883 | 72 | 96 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | again | 0.1423 | 184 | 246 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | rsync | 0.0810 | 61 | 81 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | again | 0.0954 | 84 | 112 |
| `mixed-bimodal.noop.mars-mac.receiver.warm` | rsync | 0.1204 | 133 | 177 |
| `small-flat.fresh.mac-mars.sender.warm` | again | 0.0590 | 34 | 44 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.6411 | 3690 | 4945 |
| `small-flat.fresh.mars-mac.receiver.warm` | again | 0.0871 | 71 | 94 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.0805 | 61 | 80 |
| `small-flat.noop.mac-mars.sender.warm` | again | 0.0935 | 81 | 108 |
| `small-flat.noop.mac-mars.sender.warm` | rsync | 0.1158 | 123 | 164 |
| `small-flat.noop.mars-mac.receiver.warm` | again | 0.1060 | 103 | 138 |
| `small-flat.noop.mars-mac.receiver.warm` | rsync | 0.1702 | 262 | 351 |

## Voided attempts

- round trip is 3.831 ms, above 2.0
