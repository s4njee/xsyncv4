# S4-neo-mars-sentinel

Hour by hour, the A/A ratio stays within 5% of 1 and the xs to rsync ratio stays where E1n's put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T055459Z-S4-neo-mars-sentinel-s0001, 20261020T055501Z-S4-neo-mars-sentinel-s0002, 20261020T055503Z-S4-neo-mars-sentinel-s0003, 20261020T055505Z-S4-neo-mars-sentinel-s0004, 20261020T055506Z-S4-neo-mars-sentinel-s0005.
- Valid blocks: 80. Voided block attempts: 6.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | again | 10 | 1.000 [0.996, 1.004] | 1.000 [0.996, 1.003] | 0.9043 | equivalent |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 10 | 1.002 [0.999, 1.004] | 1.001 [1.000, 1.005] | 0.1426 | equivalent |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | again | 10 | 1.001 [0.993, 1.008] | 1.002 [0.992, 1.008] | 0.8770 | equivalent |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 10 | 0.996 [0.988, 1.005] | 0.997 [0.988, 1.005] | 0.3477 | equivalent |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | again | 10 | 1.000 [0.984, 1.017] | 1.003 [0.982, 1.015] | 0.9902 | equivalent |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 10 | 1.690 [1.655, 1.726] | 1.700 [1.658, 1.725] | 0.0020 | slower |
| `mixed-bimodal.noop.neo-mars.sender.warm` | again | 10 | 0.992 [0.944, 1.043] | 0.979 [0.956, 1.065] | 0.7578 | inconclusive |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 10 | 1.434 [1.346, 1.527] | 1.434 [1.324, 1.547] | 0.0020 | slower |
| `small-flat.fresh.mars-neo.receiver.warm` | again | 10 | 0.999 [0.977, 1.021] | 1.000 [0.976, 1.022] | 0.9082 | equivalent |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 10 | 0.960 [0.935, 0.985] | 0.956 [0.934, 0.995] | 0.0020 | inconclusive |
| `small-flat.fresh.neo-mars.sender.warm` | again | 10 | 1.002 [0.988, 1.016] | 1.001 [0.990, 1.017] | 0.7676 | equivalent |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 10 | 1.322 [1.271, 1.376] | 1.324 [1.266, 1.386] | 0.0020 | slower |
| `small-flat.noop.mars-neo.receiver.warm` | again | 10 | 1.063 [0.900, 1.256] | 0.987 [0.957, 1.386] | 0.7090 | inconclusive |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 10 | 3.054 [2.911, 3.203] | 3.071 [2.894, 3.204] | 0.0020 | slower |
| `small-flat.noop.neo-mars.sender.warm` | again | 10 | 1.023 [0.936, 1.118] | 1.027 [0.943, 1.114] | 0.5703 | inconclusive |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 10 | 3.236 [2.726, 3.842] | 3.300 [2.652, 3.818] | 0.0020 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | again | 0.991 [0.960, 1.024] | 1.000 [0.992, 1.008] | 0.978 [0.946, 1.011] |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.714 [0.687, 0.742] | 1.003 [0.990, 1.017] | 0.044 [0.040, 0.048] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | again | 0.982 [0.937, 1.030] | 1.001 [0.993, 1.009] | 0.999 [0.994, 1.003] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 0.698 [0.661, 0.737] | 0.996 [0.988, 1.005] | 0.133 [0.127, 0.139] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | again | 0.991 [0.964, 1.019] | 0.999 [0.983, 1.016] | 1.002 [0.992, 1.013] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 0.532 [0.505, 0.560] | 1.679 [1.644, 1.714] | 0.466 [0.457, 0.476] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | again | 0.973 [0.928, 1.019] | 0.988 [0.944, 1.033] | 1.001 [0.999, 1.002] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 0.840 [0.776, 0.909] | 1.299 [1.234, 1.368] | 1.001 [0.999, 1.003] |
| `small-flat.fresh.mars-neo.receiver.warm` | again | 0.987 [0.959, 1.016] | 0.998 [0.979, 1.018] | 0.985 [0.944, 1.028] |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.408 [0.355, 0.469] | 0.962 [0.936, 0.989] | 0.066 [0.061, 0.071] |
| `small-flat.fresh.neo-mars.sender.warm` | again | 1.002 [0.988, 1.017] | 1.001 [0.988, 1.014] | 1.000 [0.975, 1.025] |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 1.045 [1.002, 1.089] | 1.314 [1.262, 1.367] | 0.101 [0.098, 0.104] |
| `small-flat.noop.mars-neo.receiver.warm` | again | 1.049 [0.969, 1.135] | 1.062 [0.900, 1.254] | 0.999 [0.981, 1.018] |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 0.653 [0.628, 0.679] | 3.030 [2.891, 3.175] | 0.314 [0.306, 0.321] |
| `small-flat.noop.neo-mars.sender.warm` | again | 1.054 [0.932, 1.193] | 1.002 [0.933, 1.075] | 1.018 [0.907, 1.143] |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 0.972 [0.779, 1.213] | 2.786 [2.373, 3.271] | 0.889 [0.805, 0.982] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | 12.128 | 12.154 | 12.131 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | 12.376 | 12.323 | 12.369 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | 0.184 | 0.312 | 0.184 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | 0.185 | 0.267 | 0.186 |
| `small-flat.fresh.mars-neo.receiver.warm` | 5.454 | 5.240 | 5.460 |
| `small-flat.fresh.neo-mars.sender.warm` | 12.341 | 16.286 | 12.315 |
| `small-flat.noop.mars-neo.receiver.warm` | 0.261 | 0.751 | 0.246 |
| `small-flat.noop.neo-mars.sender.warm` | 0.296 | 0.937 | 0.290 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | again | 0.0053 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.0036 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | again | 0.0110 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 0.0121 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | again | 0.0233 | 8 | 9 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 0.0291 | 10 | 13 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | again | 0.0701 | 47 | 62 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 0.0882 | 72 | 96 |
| `small-flat.fresh.mars-neo.receiver.warm` | again | 0.0308 | 11 | 14 |
| `small-flat.fresh.mars-neo.receiver.warm` | rsync | 0.0364 | 14 | 18 |
| `small-flat.fresh.neo-mars.sender.warm` | again | 0.0192 | 8 | 8 |
| `small-flat.fresh.neo-mars.sender.warm` | rsync | 0.0551 | 30 | 39 |
| `small-flat.noop.mars-neo.receiver.warm` | again | 0.2330 | 489 | 655 |
| `small-flat.noop.mars-neo.receiver.warm` | rsync | 0.0669 | 43 | 56 |
| `small-flat.noop.neo-mars.sender.warm` | again | 0.1241 | 141 | 188 |
| `small-flat.noop.neo-mars.sender.warm` | rsync | 0.2399 | 519 | 694 |

## Voided attempts

- again: did not settle: neo is 32% busy
- again: did not settle: neo is 60% busy
- round trip is 2.375 ms, above 2.0
- rsync: did not settle: neo is 44% busy
- xs: did not settle: neo is 22% busy
- xs: did not settle: neo is 38% busy
