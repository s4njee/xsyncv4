# E1c-cold

With cold caches xs -a differs from rsync -a by more than 3% in time-to-durable, per corpus, scenario and direction.

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220717Z-E1c-cold.
- Valid blocks: 280. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.cold` | xs | 10 | 0.972 [0.964, 0.980] | 0.972 [0.963, 0.980] | 0.0020 | 0.0547 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.cold` | xs | 10 | 1.004 [0.998, 1.010] | 1.004 [0.997, 1.009] | 0.2090 | 0.4180 | equivalent |
| `mixed-bimodal.noop.freya-neo.sender.cold` | xs | 10 | 0.538 [0.522, 0.555] | 0.539 [0.521, 0.556] | 0.0020 | 0.0547 | faster |
| `mixed-bimodal.noop.neo-freya.sender.cold` | xs | 10 | 0.539 [0.513, 0.566] | 0.537 [0.512, 0.571] | 0.0020 | 0.0547 | faster |
| `mixed-threshold.fresh.freya-neo.sender.cold` | xs | 10 | 0.974 [0.966, 0.982] | 0.975 [0.966, 0.981] | 0.0020 | 0.0547 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.cold` | xs | 10 | 0.998 [0.992, 1.003] | 0.997 [0.992, 1.004] | 0.3652 | 0.4180 | equivalent |
| `mixed-threshold.noop.freya-neo.sender.cold` | xs | 10 | 0.873 [0.852, 0.895] | 0.874 [0.855, 0.894] | 0.0020 | 0.0547 | faster |
| `mixed-threshold.noop.neo-freya.sender.cold` | xs | 10 | 0.867 [0.833, 0.901] | 0.862 [0.839, 0.910] | 0.0020 | 0.0547 | faster |
| `small-deep.fresh.freya-neo.sender.cold` | xs | 10 | 0.669 [0.655, 0.684] | 0.666 [0.658, 0.687] | 0.0020 | 0.0547 | faster |
| `small-deep.fresh.neo-freya.sender.cold` | xs | 10 | 0.440 [0.411, 0.472] | 0.432 [0.416, 0.478] | 0.0020 | 0.0547 | faster |
| `small-deep.noop.freya-neo.sender.cold` | xs | 10 | 0.211 [0.204, 0.217] | 0.211 [0.204, 0.216] | 0.0020 | 0.0547 | faster |
| `small-deep.noop.neo-freya.sender.cold` | xs | 10 | 0.466 [0.454, 0.478] | 0.462 [0.457, 0.482] | 0.0020 | 0.0547 | faster |
| `small-flat.fresh.freya-neo.sender.cold` | xs | 10 | 0.642 [0.627, 0.658] | 0.644 [0.627, 0.659] | 0.0020 | 0.0547 | faster |
| `small-flat.fresh.neo-freya.sender.cold` | xs | 10 | 0.363 [0.358, 0.368] | 0.363 [0.358, 0.368] | 0.0020 | 0.0547 | faster |
| `small-flat.noop.freya-neo.sender.cold` | xs | 10 | 0.303 [0.295, 0.311] | 0.302 [0.297, 0.311] | 0.0020 | 0.0547 | faster |
| `small-flat.noop.neo-freya.sender.cold` | xs | 10 | 0.305 [0.298, 0.312] | 0.305 [0.297, 0.312] | 0.0020 | 0.0547 | faster |
| `small-opaque.fresh.freya-neo.sender.cold` | xs | 10 | 0.476 [0.464, 0.488] | 0.474 [0.464, 0.488] | 0.0020 | 0.0547 | faster |
| `small-opaque.fresh.neo-freya.sender.cold` | xs | 10 | 0.380 [0.347, 0.416] | 0.366 [0.360, 0.440] | 0.0020 | 0.0547 | faster |
| `small-opaque.noop.freya-neo.sender.cold` | xs | 10 | 0.292 [0.284, 0.301] | 0.290 [0.284, 0.301] | 0.0020 | 0.0547 | faster |
| `small-opaque.noop.neo-freya.sender.cold` | xs | 10 | 0.305 [0.300, 0.311] | 0.306 [0.299, 0.311] | 0.0020 | 0.0547 | faster |
| `small-real.fresh.freya-neo.sender.cold` | xs | 10 | 0.618 [0.607, 0.630] | 0.618 [0.606, 0.630] | 0.0020 | 0.0547 | faster |
| `small-real.fresh.neo-freya.sender.cold` | xs | 10 | 0.577 [0.571, 0.583] | 0.578 [0.570, 0.582] | 0.0020 | 0.0547 | faster |
| `small-real.noop.freya-neo.sender.cold` | xs | 10 | 0.213 [0.206, 0.220] | 0.215 [0.205, 0.220] | 0.0020 | 0.0547 | faster |
| `small-real.noop.neo-freya.sender.cold` | xs | 10 | 0.279 [0.269, 0.291] | 0.279 [0.268, 0.292] | 0.0020 | 0.0547 | faster |
| `tiny-one.fresh.freya-neo.sender.cold` | xs | 10 | 0.967 [0.934, 1.001] | 0.967 [0.941, 1.000] | 0.0527 | 0.2637 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.cold` | xs | 10 | 0.959 [0.917, 1.002] | 0.950 [0.926, 1.022] | 0.0625 | 0.2637 | inconclusive |
| `tiny-one.noop.freya-neo.sender.cold` | xs | 10 | 0.981 [0.956, 1.006] | 0.982 [0.953, 1.008] | 0.1230 | 0.3691 | inconclusive |
| `tiny-one.noop.neo-freya.sender.cold` | xs | 10 | 0.937 [0.915, 0.960] | 0.937 [0.915, 0.959] | 0.0020 | 0.0547 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.cold` | xs | 1.688 [1.668, 1.708] | 9.838 [9.631, 10.048] | 0.971 [0.964, 0.979] |
| `mixed-bimodal.fresh.neo-freya.sender.cold` | xs | 1.964 [1.940, 1.988] | 7.447 [7.276, 7.622] | 1.003 [0.997, 1.009] |
| `mixed-bimodal.noop.freya-neo.sender.cold` | xs | 1.336 [1.286, 1.388] | 1.419 [1.399, 1.439] | 0.532 [0.516, 0.548] |
| `mixed-bimodal.noop.neo-freya.sender.cold` | xs | 1.537 [1.521, 1.553] | 1.353 [1.328, 1.379] | 0.537 [0.511, 0.564] |
| `mixed-threshold.fresh.freya-neo.sender.cold` | xs | 1.956 [1.928, 1.984] | 8.075 [7.939, 8.214] | 0.981 [0.972, 0.991] |
| `mixed-threshold.fresh.neo-freya.sender.cold` | xs | 1.830 [1.797, 1.863] | 7.152 [6.967, 7.342] | 0.997 [0.992, 1.002] |
| `mixed-threshold.noop.freya-neo.sender.cold` | xs | 1.538 [1.481, 1.596] | 1.327 [1.296, 1.360] | 0.869 [0.846, 0.892] |
| `mixed-threshold.noop.neo-freya.sender.cold` | xs | 1.499 [1.443, 1.557] | 1.326 [1.288, 1.365] | 0.866 [0.832, 0.901] |
| `small-deep.fresh.freya-neo.sender.cold` | xs | 0.694 [0.679, 0.710] | 0.627 [0.611, 0.645] | 0.664 [0.649, 0.678] |
| `small-deep.fresh.neo-freya.sender.cold` | xs | 2.048 [2.021, 2.075] | 4.916 [4.833, 5.000] | 0.436 [0.406, 0.468] |
| `small-deep.noop.freya-neo.sender.cold` | xs | 0.908 [0.882, 0.936] | 1.001 [0.990, 1.011] | 0.210 [0.204, 0.217] |
| `small-deep.noop.neo-freya.sender.cold` | xs | 3.096 [3.056, 3.137] | 5.524 [5.427, 5.623] | 0.466 [0.454, 0.478] |
| `small-flat.fresh.freya-neo.sender.cold` | xs | 1.381 [1.368, 1.394] | 10.106 [9.552, 10.693] | 0.629 [0.613, 0.644] |
| `small-flat.fresh.neo-freya.sender.cold` | xs | 1.340 [1.320, 1.359] | 1.950 [1.873, 2.031] | 0.357 [0.352, 0.361] |
| `small-flat.noop.freya-neo.sender.cold` | xs | 1.289 [1.267, 1.310] | 2.130 [2.068, 2.194] | 0.299 [0.292, 0.307] |
| `small-flat.noop.neo-freya.sender.cold` | xs | 1.278 [1.266, 1.290] | 1.664 [1.631, 1.699] | 0.304 [0.297, 0.311] |
| `small-opaque.fresh.freya-neo.sender.cold` | xs | 1.417 [1.399, 1.435] | 10.166 [10.006, 10.330] | 0.463 [0.452, 0.475] |
| `small-opaque.fresh.neo-freya.sender.cold` | xs | 1.339 [1.321, 1.357] | 1.909 [1.852, 1.967] | 0.376 [0.343, 0.412] |
| `small-opaque.noop.freya-neo.sender.cold` | xs | 1.286 [1.253, 1.320] | 2.098 [2.058, 2.137] | 0.289 [0.281, 0.298] |
| `small-opaque.noop.neo-freya.sender.cold` | xs | 1.270 [1.257, 1.282] | 1.660 [1.616, 1.705] | 0.305 [0.299, 0.311] |
| `small-real.fresh.freya-neo.sender.cold` | xs | 0.809 [0.792, 0.826] | 0.740 [0.728, 0.751] | 0.609 [0.596, 0.622] |
| `small-real.fresh.neo-freya.sender.cold` | xs | 1.890 [1.869, 1.911] | 9.921 [9.643, 10.206] | 0.575 [0.568, 0.582] |
| `small-real.noop.freya-neo.sender.cold` | xs | 0.915 [0.894, 0.937] | 0.609 [0.606, 0.612] | 0.212 [0.205, 0.220] |
| `small-real.noop.neo-freya.sender.cold` | xs | 3.306 [2.980, 3.666] | 4.692 [4.569, 4.819] | 0.279 [0.269, 0.290] |
| `tiny-one.fresh.freya-neo.sender.cold` | xs | 1.431 [1.357, 1.508] | 1.287 [1.207, 1.372] | 0.967 [0.932, 1.003] |
| `tiny-one.fresh.neo-freya.sender.cold` | xs | 1.292 [1.240, 1.346] | 1.314 [1.286, 1.343] | 0.959 [0.916, 1.005] |
| `tiny-one.noop.freya-neo.sender.cold` | xs | 1.466 [1.400, 1.534] | 1.341 [1.320, 1.362] | 0.977 [0.955, 0.999] |
| `tiny-one.noop.neo-freya.sender.cold` | xs | 1.378 [1.325, 1.434] | 1.311 [1.280, 1.343] | 0.938 [0.915, 0.961] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.cold` | 13.328 | 12.953 |
| `mixed-bimodal.fresh.neo-freya.sender.cold` | 12.308 | 12.352 |
| `mixed-bimodal.noop.freya-neo.sender.cold` | 0.577 | 0.310 |
| `mixed-bimodal.noop.neo-freya.sender.cold` | 0.451 | 0.243 |
| `mixed-threshold.fresh.freya-neo.sender.cold` | 14.279 | 13.904 |
| `mixed-threshold.fresh.neo-freya.sender.cold` | 13.253 | 13.222 |
| `mixed-threshold.noop.freya-neo.sender.cold` | 0.297 | 0.259 |
| `mixed-threshold.noop.neo-freya.sender.cold` | 0.213 | 0.185 |
| `small-deep.fresh.freya-neo.sender.cold` | 23.191 | 15.523 |
| `small-deep.fresh.neo-freya.sender.cold` | 23.472 | 10.331 |
| `small-deep.noop.freya-neo.sender.cold` | 25.506 | 5.371 |
| `small-deep.noop.neo-freya.sender.cold` | 11.037 | 5.141 |
| `small-flat.fresh.freya-neo.sender.cold` | 9.758 | 6.264 |
| `small-flat.fresh.neo-freya.sender.cold` | 10.300 | 3.736 |
| `small-flat.noop.freya-neo.sender.cold` | 1.705 | 0.516 |
| `small-flat.noop.neo-freya.sender.cold` | 1.585 | 0.483 |
| `small-opaque.fresh.freya-neo.sender.cold` | 13.397 | 6.372 |
| `small-opaque.fresh.neo-freya.sender.cold` | 10.236 | 3.888 |
| `small-opaque.noop.freya-neo.sender.cold` | 1.804 | 0.527 |
| `small-opaque.noop.neo-freya.sender.cold` | 1.556 | 0.475 |
| `small-real.fresh.freya-neo.sender.cold` | 21.726 | 13.433 |
| `small-real.fresh.neo-freya.sender.cold` | 19.365 | 11.168 |
| `small-real.noop.freya-neo.sender.cold` | 12.938 | 2.754 |
| `small-real.noop.neo-freya.sender.cold` | 6.293 | 1.759 |
| `tiny-one.fresh.freya-neo.sender.cold` | 0.263 | 0.254 |
| `tiny-one.fresh.neo-freya.sender.cold` | 0.189 | 0.181 |
| `tiny-one.noop.freya-neo.sender.cold` | 0.251 | 0.246 |
| `tiny-one.noop.neo-freya.sender.cold` | 0.185 | 0.173 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.cold` | xs | 0.0114 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.cold` | xs | 0.0084 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.cold` | xs | 0.0423 | 19 | 24 |
| `mixed-bimodal.noop.neo-freya.sender.cold` | xs | 0.0683 | 44 | 59 |
| `mixed-threshold.fresh.freya-neo.sender.cold` | xs | 0.0111 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.cold` | xs | 0.0081 | 8 | 8 |
| `mixed-threshold.noop.freya-neo.sender.cold` | xs | 0.0340 | 13 | 16 |
| `mixed-threshold.noop.neo-freya.sender.cold` | xs | 0.0552 | 30 | 39 |
| `small-deep.fresh.freya-neo.sender.cold` | xs | 0.0294 | 10 | 13 |
| `small-deep.fresh.neo-freya.sender.cold` | xs | 0.0963 | 86 | 114 |
| `small-deep.noop.freya-neo.sender.cold` | xs | 0.0424 | 19 | 24 |
| `small-deep.noop.neo-freya.sender.cold` | xs | 0.0353 | 14 | 17 |
| `small-flat.fresh.freya-neo.sender.cold` | xs | 0.0338 | 13 | 16 |
| `small-flat.fresh.neo-freya.sender.cold` | xs | 0.0186 | 8 | 8 |
| `small-flat.noop.freya-neo.sender.cold` | xs | 0.0354 | 14 | 18 |
| `small-flat.noop.neo-freya.sender.cold` | xs | 0.0338 | 13 | 16 |
| `small-opaque.fresh.freya-neo.sender.cold` | xs | 0.0358 | 14 | 18 |
| `small-opaque.fresh.neo-freya.sender.cold` | xs | 0.1257 | 144 | 192 |
| `small-opaque.noop.freya-neo.sender.cold` | xs | 0.0409 | 18 | 23 |
| `small-opaque.noop.neo-freya.sender.cold` | xs | 0.0269 | 9 | 11 |
| `small-real.fresh.freya-neo.sender.cold` | xs | 0.0261 | 9 | 11 |
| `small-real.fresh.neo-freya.sender.cold` | xs | 0.0148 | 8 | 8 |
| `small-real.noop.freya-neo.sender.cold` | xs | 0.0488 | 24 | 31 |
| `small-real.noop.neo-freya.sender.cold` | xs | 0.0547 | 29 | 38 |
| `tiny-one.fresh.freya-neo.sender.cold` | xs | 0.0483 | 23 | 31 |
| `tiny-one.fresh.neo-freya.sender.cold` | xs | 0.0618 | 37 | 48 |
| `tiny-one.noop.freya-neo.sender.cold` | xs | 0.0356 | 14 | 18 |
| `tiny-one.noop.neo-freya.sender.cold` | xs | 0.0342 | 13 | 17 |
