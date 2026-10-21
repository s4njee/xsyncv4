# N2b-10g-small-read

At 10 Gb/s xs reads small and mixed trees off a cold NVMe drive faster than rsync.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T113054Z-N2b-10g-small-read.
- Valid blocks: 96. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 8 | 0.549 [0.204, 1.478] | 0.472 [0.218, 1.820] | 0.1953 | inconclusive |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 8 | 0.618 [0.533, 0.715] | 0.635 [0.522, 0.701] | 0.0078 | faster |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 8 | 0.283 [0.146, 0.548] | 0.360 [0.129, 0.453] | 0.0078 | faster |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 8 | 1.043 [0.955, 1.139] | 1.040 [0.951, 1.161] | 0.2891 | inconclusive |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 8 | 1.669 [0.519, 5.366] | 1.667 [0.479, 6.380] | 0.3984 | inconclusive |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 8 | 0.764 [0.230, 2.543] | 1.145 [0.161, 1.579] | 0.9766 | inconclusive |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 8 | 1.376 [0.529, 3.579] | 0.909 [0.701, 3.882] | 0.5625 | inconclusive |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 8 | 0.391 [0.276, 0.552] | 0.354 [0.295, 0.561] | 0.0078 | faster |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 8 | 0.971 [0.650, 1.451] | 0.867 [0.749, 1.648] | 0.9141 | inconclusive |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 8 | 0.329 [0.198, 0.545] | 0.257 [0.223, 0.504] | 0.0078 | faster |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 8 | 1.036 [0.941, 1.139] | 1.035 [0.929, 1.159] | 0.4375 | inconclusive |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 8 | 1.127 [0.971, 1.307] | 1.078 [1.009, 1.371] | 0.0078 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 0.745 [0.654, 0.849] | 0.781 [0.728, 0.839] | 0.545 [0.201, 1.478] |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 1.264 [1.165, 1.371] | 1.165 [1.124, 1.208] | 0.567 [0.478, 0.673] |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 0.609 [0.554, 0.668] | 0.711 [0.682, 0.741] | 0.277 [0.141, 0.542] |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 1.483 [1.378, 1.595] | 1.006 [0.991, 1.021] | 1.042 [0.946, 1.148] |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 2.443 [2.226, 2.680] | 1.405 [0.917, 2.154] | 1.688 [0.524, 5.437] |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 6.703 [5.330, 8.429] | 4.540 [3.918, 5.260] | 0.765 [0.229, 2.554] |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 0.904 [0.782, 1.046] | 0.667 [0.583, 0.763] | 1.373 [0.525, 3.590] |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 1.022 [0.793, 1.318] | 1.531 [1.319, 1.777] | 0.367 [0.256, 0.527] |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 1.022 [0.792, 1.318] | 0.694 [0.636, 0.759] | 0.965 [0.644, 1.445] |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.924 [0.809, 1.055] | 1.509 [1.273, 1.790] | 0.318 [0.189, 0.537] |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 1.094 [0.967, 1.238] | 1.020 [0.997, 1.043] | 1.051 [0.949, 1.165] |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 1.135 [1.032, 1.249] | 1.004 [0.987, 1.021] | 1.160 [0.994, 1.352] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | 17.736 | 9.736 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | 0.716 | 0.442 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | 7.208 | 2.037 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | 0.336 | 0.351 |
| `small-deep.fresh.mars-mac.receiver.cold` | 55.386 | 92.414 |
| `small-deep.noop.mars-mac.receiver.cold` | 14.326 | 10.946 |
| `small-flat.fresh.mars-mac.receiver.cold` | 33.578 | 46.198 |
| `small-flat.noop.mars-mac.receiver.cold` | 2.905 | 1.135 |
| `small-opaque.fresh.mars-mac.receiver.cold` | 23.525 | 22.846 |
| `small-opaque.noop.mars-mac.receiver.cold` | 4.582 | 1.507 |
| `tiny-one.fresh.mars-mac.receiver.cold` | 0.310 | 0.321 |
| `tiny-one.noop.mars-mac.receiver.cold` | 0.271 | 0.305 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.cold` | xs | 1.1845 | 12591 | 16875 |
| `mixed-bimodal.noop.mars-mac.receiver.cold` | xs | 0.1756 | 279 | 373 |
| `mixed-threshold.fresh.mars-mac.receiver.cold` | xs | 0.7926 | 5640 | 7558 |
| `mixed-threshold.noop.mars-mac.receiver.cold` | xs | 0.1056 | 102 | 137 |
| `small-deep.fresh.mars-mac.receiver.cold` | xs | 1.3973 | 17522 | 23483 |
| `small-deep.noop.mars-mac.receiver.cold` | xs | 1.4385 | 18570 | 24887 |
| `small-flat.fresh.mars-mac.receiver.cold` | xs | 1.1437 | 11739 | 15733 |
| `small-flat.noop.mars-mac.receiver.cold` | xs | 0.4141 | 1541 | 2065 |
| `small-opaque.fresh.mars-mac.receiver.cold` | xs | 0.4805 | 2074 | 2779 |
| `small-opaque.noop.mars-mac.receiver.cold` | xs | 0.6050 | 3287 | 4404 |
| `tiny-one.fresh.mars-mac.receiver.cold` | xs | 0.1142 | 120 | 159 |
| `tiny-one.noop.mars-mac.receiver.cold` | xs | 0.1781 | 287 | 384 |
