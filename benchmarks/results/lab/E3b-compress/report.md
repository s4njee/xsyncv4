# E3b-compress

With neo sending over gigabit, -z makes xs faster on compressible corpora and no slower on incompressible ones.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T133009Z-E3b-compress.
- Valid blocks: 60. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 10 | 0.772 [0.771, 0.774] | 0.772 [0.770, 0.774] | 0.0020 | faster |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 0.794 [0.749, 0.841] | 0.775 [0.770, 0.877] | 0.0020 | faster |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 10 | 1.065 [0.951, 1.194] | 1.015 [1.009, 1.297] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 10 | 0.813 [0.746, 0.885] | 0.786 [0.774, 0.934] | 0.0039 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 10 | 0.870 [0.735, 1.029] | 0.786 [0.772, 1.046] | 0.1055 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 0.783 [0.779, 0.788] | 0.784 [0.779, 0.788] | 0.0020 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 10 | 0.964 [0.957, 0.971] | 0.963 [0.958, 0.972] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 10 | 1.319 [1.273, 1.366] | 1.318 [1.272, 1.368] | 0.0020 | slower |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 10 | 1.016 [0.999, 1.033] | 1.022 [1.000, 1.032] | 0.0605 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 1.033 [1.016, 1.050] | 1.034 [1.015, 1.050] | 0.0059 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 10 | 1.076 [1.021, 1.135] | 1.074 [1.014, 1.145] | 0.0117 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 10 | 1.091 [1.055, 1.128] | 1.086 [1.053, 1.129] | 0.0020 | slower |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 10 | 1.054 [1.034, 1.074] | 1.054 [1.033, 1.078] | 0.0020 | slower |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 1.052 [1.022, 1.082] | 1.055 [1.018, 1.086] | 0.0020 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 10 | 1.423 [1.142, 1.773] | 1.439 [1.097, 1.730] | 0.0020 | slower |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 10 | 2.882 [2.615, 3.175] | 2.873 [2.621, 3.186] | 0.0020 | slower |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 10 | 0.818 [0.780, 0.857] | 0.820 [0.774, 0.858] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 10 | 0.807 [0.783, 0.832] | 0.806 [0.785, 0.832] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 10 | 1.347 [1.300, 1.396] | 1.348 [1.300, 1.397] | 0.0020 | slower |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 10 | 1.160 [1.133, 1.187] | 1.160 [1.130, 1.191] | 0.0020 | slower |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 10 | 0.497 [0.435, 0.570] | 0.507 [0.433, 0.574] | 0.0020 | faster |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 10 | 0.489 [0.445, 0.537] | 0.497 [0.447, 0.534] | 0.0020 | faster |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 10 | 0.992 [0.882, 1.116] | 1.011 [0.870, 1.059] | 0.9551 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 10 | 1.013 [0.890, 1.154] | 1.044 [0.881, 1.142] | 0.8281 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 1.129 [1.103, 1.154] | 0.774 [0.767, 0.780] | 1.476 [1.429, 1.525] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 1.120 [1.100, 1.140] | 0.800 [0.757, 0.846] | 1.454 [1.418, 1.491] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.514 [0.502, 0.526] | 1.061 [0.951, 1.183] | 0.099 [0.098, 0.100] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 0.926 [0.907, 0.946] | 0.822 [0.758, 0.890] | 0.121 [0.118, 0.124] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 1.679 [1.176, 2.399] | 0.868 [0.737, 1.023] | 1.446 [1.350, 1.548] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 1.322 [1.266, 1.382] | 0.784 [0.778, 0.789] | 1.527 [1.486, 1.569] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.471 [0.457, 0.485] | 0.962 [0.953, 0.971] | 0.126 [0.122, 0.129] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 1.196 [1.165, 1.229] | 1.315 [1.268, 1.364] | 0.118 [0.115, 0.121] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 1.214 [1.193, 1.236] | 1.020 [1.006, 1.035] | 1.121 [1.068, 1.175] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 1.221 [1.185, 1.258] | 1.031 [1.015, 1.047] | 1.076 [0.980, 1.180] |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 0.710 [0.677, 0.745] | 1.068 [1.018, 1.121] | 0.099 [0.097, 0.102] |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 0.764 [0.741, 0.788] | 1.086 [1.047, 1.126] | 0.099 [0.097, 0.102] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 1.195 [1.151, 1.241] | 1.057 [1.033, 1.082] | 1.138 [0.893, 1.449] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 1.211 [1.161, 1.264] | 1.053 [1.026, 1.081] | 1.044 [0.741, 1.473] |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.650 [0.633, 0.669] | 1.411 [1.136, 1.752] | 0.164 [0.130, 0.207] |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 1.192 [1.138, 1.250] | 2.836 [2.580, 3.117] | 0.163 [0.130, 0.206] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.903 [0.847, 0.961] | 0.820 [0.784, 0.858] | 1.147 [0.706, 1.864] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 0.890 [0.867, 0.914] | 0.809 [0.786, 0.834] | 1.206 [0.770, 1.890] |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.947 [0.927, 0.967] | 1.337 [1.293, 1.382] | 1.307 [1.288, 1.326] |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 0.792 [0.769, 0.817] | 1.149 [1.121, 1.178] | 1.323 [1.303, 1.342] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 0.836 [0.809, 0.864] | 0.521 [0.454, 0.599] | 0.491 [0.433, 0.557] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 0.822 [0.801, 0.844] | 0.515 [0.460, 0.576] | 0.469 [0.424, 0.518] |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.509 [0.498, 0.521] | 0.980 [0.869, 1.105] | 0.097 [0.095, 0.100] |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 0.483 [0.471, 0.496] | 1.008 [0.883, 1.151] | 0.120 [0.117, 0.122] |

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
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 0.0034 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z1 | 0.0811 | 61 | 82 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.1590 | 229 | 307 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 0.1192 | 130 | 173 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 0.2350 | 498 | 667 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z1 | 0.0084 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0101 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 0.0494 | 24 | 32 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 0.0228 | 8 | 9 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z1 | 0.0229 | 8 | 9 |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 0.0743 | 52 | 69 |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync-z | 0.0466 | 22 | 29 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 0.0270 | 9 | 11 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z1 | 0.0399 | 17 | 22 |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.3075 | 851 | 1139 |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync-z | 0.1355 | 167 | 223 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.0664 | 42 | 55 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z1 | 0.0419 | 18 | 24 |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.0494 | 24 | 32 |
| `small-real.fresh.freya-neo.sender.warm` | rsync-z | 0.0323 | 12 | 15 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 0.1890 | 323 | 432 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z1 | 0.1310 | 156 | 209 |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.1640 | 244 | 326 |
| `small-real.fresh.neo-freya.sender.warm` | rsync-z | 0.1814 | 298 | 398 |
