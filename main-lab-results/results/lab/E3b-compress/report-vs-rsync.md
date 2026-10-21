# E3b-compress

With neo sending over gigabit, -z makes xs faster on compressible corpora and no slower on incompressible ones.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T133009Z-E3b-compress.
- Valid blocks: 60. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 10 | 0.939 [0.838, 1.052] | 0.986 [0.771, 0.992] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 10 | 0.725 [0.647, 0.813] | 0.761 [0.596, 0.767] | 0.0020 | faster |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 0.745 [0.704, 0.788] | 0.763 [0.678, 0.767] | 0.0020 | faster |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 10 | 0.763 [0.739, 0.787] | 0.770 [0.731, 0.782] | 0.0020 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 10 | 1.037 [1.030, 1.045] | 1.039 [1.029, 1.044] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 10 | 0.902 [0.763, 1.067] | 0.813 [0.803, 1.088] | 0.2188 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 0.813 [0.806, 0.819] | 0.813 [0.806, 0.819] | 0.0020 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 10 | 1.368 [1.324, 1.413] | 1.368 [1.326, 1.415] | 0.0020 | slower |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 10 | 0.929 [0.881, 0.980] | 0.931 [0.873, 0.986] | 0.0117 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 10 | 0.944 [0.900, 0.990] | 0.946 [0.900, 0.995] | 0.0234 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 0.960 [0.909, 1.014] | 0.961 [0.904, 1.019] | 0.1270 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 10 | 1.014 [0.942, 1.091] | 1.014 [0.940, 1.095] | 0.6777 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 10 | 0.703 [0.564, 0.875] | 0.695 [0.578, 0.912] | 0.0020 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 10 | 0.740 [0.593, 0.925] | 0.744 [0.600, 0.967] | 0.0117 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 0.739 [0.591, 0.924] | 0.744 [0.587, 0.958] | 0.0137 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 10 | 2.025 [1.751, 2.342] | 2.038 [1.725, 2.336] | 0.0020 | slower |
| `small-real.fresh.freya-neo.sender.warm` | xs | 10 | 0.742 [0.717, 0.769] | 0.742 [0.716, 0.769] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 10 | 0.607 [0.574, 0.642] | 0.604 [0.573, 0.638] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 0.599 [0.576, 0.624] | 0.598 [0.573, 0.626] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 10 | 0.861 [0.841, 0.882] | 0.860 [0.839, 0.885] | 0.0020 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs | 10 | 1.008 [0.896, 1.133] | 0.989 [0.944, 1.149] | 0.9551 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 10 | 0.501 [0.461, 0.545] | 0.494 [0.464, 0.548] | 0.0020 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 0.493 [0.457, 0.531] | 0.498 [0.460, 0.528] | 0.0020 | faster |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 10 | 1.021 [0.935, 1.116] | 1.036 [0.940, 1.101] | 0.5957 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.946 [1.900, 1.992] | 0.942 [0.845, 1.051] | 10.117 [10.002, 10.234] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 2.196 [2.154, 2.239] | 0.729 [0.655, 0.812] | 14.937 [14.502, 15.386] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 2.179 [2.130, 2.229] | 0.754 [0.714, 0.796] | 14.708 [14.380, 15.044] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 1.802 [1.771, 1.832] | 0.774 [0.749, 0.801] | 1.224 [1.195, 1.254] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.125 [2.062, 2.189] | 1.039 [1.030, 1.049] | 7.958 [7.741, 8.180] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 3.568 [2.518, 5.056] | 0.902 [0.763, 1.066] | 11.503 [10.705, 12.360] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 2.810 [2.696, 2.928] | 0.814 [0.806, 0.823] | 12.149 [11.786, 12.524] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 2.542 [2.448, 2.640] | 1.367 [1.323, 1.412] | 0.937 [0.914, 0.960] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 1.408 [1.342, 1.478] | 0.936 [0.892, 0.982] | 10.087 [9.828, 10.353] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 1.710 [1.618, 1.807] | 0.955 [0.917, 0.995] | 11.304 [10.769, 11.866] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 1.719 [1.610, 1.836] | 0.966 [0.919, 1.014] | 10.849 [9.788, 12.027] |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 1.076 [1.012, 1.143] | 1.016 [0.948, 1.089] | 1.003 [0.985, 1.022] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 1.538 [1.496, 1.581] | 0.709 [0.571, 0.881] | 6.111 [4.837, 7.721] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 1.838 [1.780, 1.897] | 0.750 [0.602, 0.933] | 6.952 [4.669, 10.350] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 1.862 [1.796, 1.931] | 0.747 [0.604, 0.923] | 6.383 [4.264, 9.553] |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 1.833 [1.739, 1.933] | 2.010 [1.748, 2.312] | 0.997 [0.961, 1.035] |
| `small-real.fresh.freya-neo.sender.warm` | xs | 1.056 [1.034, 1.078] | 0.748 [0.724, 0.773] | 0.765 [0.754, 0.776] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.953 [0.906, 1.002] | 0.614 [0.581, 0.648] | 0.878 [0.543, 1.419] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 0.940 [0.915, 0.965] | 0.606 [0.582, 0.631] | 0.923 [0.587, 1.452] |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 0.837 [0.821, 0.853] | 0.860 [0.842, 0.878] | 1.012 [1.010, 1.014] |
| `small-real.fresh.neo-freya.sender.warm` | xs | 1.964 [1.919, 2.010] | 1.021 [0.905, 1.151] | 10.269 [10.009, 10.535] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 1.643 [1.607, 1.678] | 0.532 [0.492, 0.575] | 5.045 [4.434, 5.741] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 1.614 [1.574, 1.656] | 0.526 [0.491, 0.563] | 4.815 [4.356, 5.323] |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 0.949 [0.924, 0.975] | 1.029 [0.942, 1.123] | 1.229 [1.201, 1.258] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z | xs-z1 |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.989 | 9.908 | 12.194 | 9.418 | 9.677 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.263 | 16.776 | 12.722 | 11.067 | 9.964 |
| `small-opaque.fresh.freya-neo.sender.warm` | 7.006 | 7.102 | 6.509 | 6.612 | 6.724 |
| `small-opaque.fresh.neo-freya.sender.warm` | 4.915 | 9.951 | 3.453 | 3.639 | 3.632 |
| `small-real.fresh.freya-neo.sender.warm` | 23.449 | 20.192 | 17.407 | 14.231 | 14.053 |
| `small-real.fresh.neo-freya.sender.warm` | 11.911 | 12.167 | 12.005 | 5.973 | 5.867 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.1590 | 229 | 307 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 0.1592 | 230 | 307 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 0.0783 | 58 | 76 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 0.0444 | 20 | 26 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0101 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 0.2341 | 494 | 662 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 0.0104 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 0.0452 | 21 | 27 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs | 0.0743 | 52 | 69 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 0.0670 | 43 | 56 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 0.0767 | 55 | 73 |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 0.1032 | 98 | 130 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs | 0.3075 | 851 | 1139 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 0.3104 | 867 | 1161 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 0.3115 | 873 | 1170 |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 0.2032 | 373 | 499 |
| `small-real.fresh.freya-neo.sender.warm` | xs | 0.0494 | 24 | 32 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.0780 | 57 | 76 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 0.0564 | 31 | 41 |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 0.0329 | 12 | 16 |
| `small-real.fresh.neo-freya.sender.warm` | xs | 0.1640 | 244 | 326 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 0.1174 | 126 | 168 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 0.1040 | 100 | 133 |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 0.1236 | 140 | 186 |
