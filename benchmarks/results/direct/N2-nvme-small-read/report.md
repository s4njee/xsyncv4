# N2-nvme-small-read

xs -a reads small and mixed trees off a cold NVMe drive faster than rsync -a.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T034426Z-N2-nvme-small-read, 20261015T100232Z-N2-nvme-small-read.
- Valid blocks: 99. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 9 | 0.435 [0.308, 0.614] | 0.468 [0.273, 0.578] | 0.0039 | faster |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 8 | 0.501 [0.348, 0.722] | 0.572 [0.331, 0.671] | 0.0078 | faster |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 8 | 0.605 [0.401, 0.910] | 0.668 [0.365, 0.846] | 0.0156 | faster |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 8 | 1.198 [0.864, 1.662] | 1.089 [0.894, 1.586] | 0.3203 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 8 | 1.194 [0.877, 1.627] | 1.379 [0.876, 1.512] | 0.2109 | inconclusive |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 8 | 1.183 [1.024, 1.366] | 1.153 [1.041, 1.392] | 0.0234 | inconclusive |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 8 | 0.820 [0.678, 0.991] | 0.858 [0.645, 0.958] | 0.0156 | inconclusive |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 9 | 0.260 [0.180, 0.375] | 0.240 [0.192, 0.445] | 0.0039 | faster |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 9 | 1.080 [0.817, 1.428] | 0.956 [0.888, 1.525] | 0.6641 | inconclusive |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 8 | 0.251 [0.210, 0.299] | 0.249 [0.209, 0.298] | 0.0078 | faster |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 8 | 0.832 [0.434, 1.594] | 1.034 [0.358, 1.240] | 0.9375 | inconclusive |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 8 | 1.167 [0.577, 2.361] | 1.079 [0.589, 2.772] | 0.5391 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 0.739 [0.708, 0.772] | 0.746 [0.683, 0.814] | 0.423 [0.306, 0.583] |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 1.386 [1.215, 1.582] | 1.155 [1.127, 1.184] | 0.453 [0.296, 0.694] |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 0.598 [0.546, 0.655] | 0.680 [0.622, 0.743] | 0.601 [0.398, 0.909] |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 1.424 [1.335, 1.520] | 0.997 [0.985, 1.010] | 1.209 [0.794, 1.841] |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 2.372 [2.041, 2.757] | 2.640 [1.494, 4.664] | 1.224 [0.887, 1.689] |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 7.890 [7.479, 8.323] | 4.737 [4.457, 5.035] | 1.186 [1.026, 1.371] |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 0.910 [0.843, 0.982] | 0.658 [0.565, 0.766] | 0.811 [0.672, 0.978] |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 0.953 [0.888, 1.023] | 1.667 [1.639, 1.696] | 0.239 [0.163, 0.351] |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 0.923 [0.880, 0.968] | 0.519 [0.337, 0.799] | 1.065 [0.799, 1.419] |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.975 [0.873, 1.089] | 1.612 [1.457, 1.783] | 0.231 [0.193, 0.277] |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 1.148 [1.093, 1.205] | 1.002 [0.986, 1.018] | 0.857 [0.432, 1.700] |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 1.169 [1.091, 1.254] | 1.006 [0.992, 1.020] | 1.216 [0.559, 2.644] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | 14.635 | 6.366 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | 0.835 | 0.419 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | 7.937 | 4.798 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | 0.342 | 0.410 |
| `small-deep.fresh.mars-mac.receiver.cold` | 59.460 | 71.011 |
| `small-deep.noop.mars-mac.receiver.cold` | 9.168 | 10.843 |
| `small-flat.fresh.mars-mac.receiver.cold` | 25.028 | 20.513 |
| `small-flat.noop.mars-mac.receiver.cold` | 3.043 | 0.791 |
| `small-opaque.fresh.mars-mac.receiver.cold` | 38.373 | 41.448 |
| `small-opaque.noop.mars-mac.receiver.cold` | 2.766 | 0.693 |
| `tiny-one.fresh.mars-mac.receiver.cold` | 0.361 | 0.300 |
| `tiny-one.noop.mars-mac.receiver.cold` | 0.318 | 0.371 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 0.4492 | 1813 | 2429 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 0.4358 | 1707 | 2286 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 0.4897 | 2154 | 2886 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 0.3911 | 1375 | 1842 |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 0.3696 | 1228 | 1645 |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 0.1727 | 270 | 361 |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 0.2276 | 467 | 625 |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 0.4774 | 2047 | 2743 |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 0.3628 | 1184 | 1585 |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.2118 | 405 | 542 |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 0.7781 | 5435 | 7283 |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 0.8424 | 6370 | 8537 |

## Voided attempts

- stopped
