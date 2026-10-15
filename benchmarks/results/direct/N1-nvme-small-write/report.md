# N1-nvme-small-write

xs -a writes small and mixed trees onto NVMe faster than rsync -a, durably, and passes 1 Gb/s.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T034423Z-N1-nvme-small-write.
- Valid blocks: 96. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 8 | 0.510 [0.356, 0.729] | 0.530 [0.318, 0.695] | 0.0078 | faster |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 8 | 0.712 [0.652, 0.777] | 0.713 [0.641, 0.786] | 0.0078 | faster |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 8 | 0.479 [0.304, 0.756] | 0.540 [0.287, 0.728] | 0.0078 | faster |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 8 | 0.898 [0.757, 1.065] | 0.942 [0.737, 1.028] | 0.1406 | inconclusive |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 8 | 0.509 [0.360, 0.720] | 0.513 [0.360, 0.773] | 0.0156 | faster |
| `small-deep.noop.mac-mars.sender.warm` | xs | 8 | 0.483 [0.403, 0.579] | 0.471 [0.411, 0.608] | 0.0078 | faster |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 8 | 0.576 [0.388, 0.855] | 0.597 [0.366, 0.842] | 0.0078 | faster |
| `small-flat.noop.mac-mars.sender.warm` | xs | 8 | 0.330 [0.247, 0.441] | 0.323 [0.235, 0.460] | 0.0078 | faster |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 8 | 0.501 [0.289, 0.870] | 0.492 [0.254, 0.902] | 0.0078 | faster |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 8 | 0.264 [0.189, 0.370] | 0.290 [0.179, 0.351] | 0.0078 | faster |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 8 | 0.937 [0.866, 1.013] | 0.921 [0.873, 1.008] | 0.1250 | inconclusive |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 8 | 1.197 [0.788, 1.818] | 1.041 [0.886, 1.995] | 0.4219 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 0.713 [0.643, 0.790] | 12.006 [11.681, 12.340] | 0.500 [0.354, 0.706] |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 1.369 [1.243, 1.507] | 1.043 [1.032, 1.054] | 0.696 [0.624, 0.776] |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 0.585 [0.512, 0.667] | 9.206 [8.004, 10.588] | 0.478 [0.303, 0.754] |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 1.612 [1.519, 1.711] | 1.016 [1.005, 1.027] | 1.116 [0.769, 1.619] |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 1.707 [1.420, 2.052] | 5.429 [3.826, 7.703] | 0.507 [0.359, 0.718] |
| `small-deep.noop.mac-mars.sender.warm` | xs | 3.098 [2.814, 3.410] | 4.207 [4.180, 4.234] | 0.484 [0.403, 0.580] |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 1.319 [1.178, 1.477] | 8.676 [6.663, 11.296] | 0.572 [0.386, 0.847] |
| `small-flat.noop.mac-mars.sender.warm` | xs | 1.038 [0.968, 1.113] | 1.348 [1.319, 1.377] | 0.287 [0.234, 0.354] |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 1.338 [1.135, 1.577] | 9.631 [7.559, 12.272] | 0.497 [0.285, 0.865] |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 0.936 [0.790, 1.108] | 1.333 [1.312, 1.354] | 0.263 [0.189, 0.367] |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 1.214 [1.090, 1.352] | 1.010 [0.995, 1.025] | 0.957 [0.891, 1.029] |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 1.207 [1.119, 1.302] | 1.018 [1.005, 1.031] | 1.174 [0.769, 1.792] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 8.567 | 4.367 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | 0.311 | 0.221 |
| `mixed-threshold.fresh.mac-mars.sender.warm` | 8.698 | 4.169 |
| `mixed-threshold.noop.mac-mars.sender.warm` | 0.258 | 0.232 |
| `small-deep.fresh.mac-mars.sender.warm` | 18.511 | 9.420 |
| `small-deep.noop.mac-mars.sender.warm` | 6.959 | 3.362 |
| `small-flat.fresh.mac-mars.sender.warm` | 6.246 | 3.597 |
| `small-flat.noop.mac-mars.sender.warm` | 0.877 | 0.290 |
| `small-opaque.fresh.mac-mars.sender.warm` | 7.342 | 3.680 |
| `small-opaque.noop.mac-mars.sender.warm` | 1.046 | 0.276 |
| `tiny-one.fresh.mac-mars.sender.warm` | 0.217 | 0.204 |
| `tiny-one.noop.mac-mars.sender.warm` | 0.216 | 0.259 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs | 0.4278 | 1645 | 2204 |
| `mixed-bimodal.noop.mac-mars.sender.warm` | xs | 0.1045 | 100 | 134 |
| `mixed-threshold.fresh.mac-mars.sender.warm` | xs | 0.5445 | 2663 | 3568 |
| `mixed-threshold.noop.mac-mars.sender.warm` | xs | 0.2040 | 376 | 503 |
| `small-deep.fresh.mac-mars.sender.warm` | xs | 0.4154 | 1551 | 2078 |
| `small-deep.noop.mac-mars.sender.warm` | xs | 0.2157 | 420 | 562 |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 0.4733 | 2012 | 2696 |
| `small-flat.noop.mac-mars.sender.warm` | xs | 0.3455 | 1074 | 1438 |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 0.6592 | 3901 | 5228 |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 0.4030 | 1459 | 1955 |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 0.0933 | 81 | 107 |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 0.4998 | 2244 | 3006 |
