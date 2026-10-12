# E0a-noise

Two labels on one binary are equivalent within 3% in every cell.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T001524Z-E0a-noise.
- Valid blocks: 144. Voided block attempts: 3.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 12 | 0.991 [0.985, 0.997] | 0.993 [0.988, 0.996] | 0.0005 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 12 | 0.996 [0.991, 1.000] | 0.996 [0.991, 1.000] | 0.0522 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 12 | 0.996 [0.987, 1.005] | 0.999 [0.991, 1.003] | 0.4551 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 12 | 1.067 [1.048, 1.086] | 1.064 [1.047, 1.087] | 0.0005 | slower |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 12 | 1.122 [1.013, 1.244] | 1.077 [1.052, 1.109] | 0.0005 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 12 | 1.022 [0.977, 1.069] | 1.001 [0.998, 1.011] | 0.2744 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 12 | 0.613 [0.591, 0.636] | 0.610 [0.589, 0.637] | 0.0005 | faster |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 12 | 0.606 [0.595, 0.616] | 0.605 [0.597, 0.615] | 0.0005 | faster |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 12 | 0.991 [0.959, 1.025] | 0.996 [0.957, 1.029] | 0.5679 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 12 | 0.663 [0.646, 0.681] | 0.665 [0.647, 0.681] | 0.0005 | faster |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 12 | 0.689 [0.671, 0.708] | 0.690 [0.676, 0.705] | 0.0005 | faster |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 12 | 0.995 [0.976, 1.014] | 0.992 [0.973, 1.012] | 0.5386 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 12 | 0.965 [0.939, 0.992] | 0.969 [0.941, 0.993] | 0.0107 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 12 | 0.978 [0.950, 1.007] | 0.980 [0.947, 1.011] | 0.1255 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 12 | 1.052 [0.983, 1.125] | 1.030 [0.987, 1.158] | 0.1274 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 12 | 0.811 [0.655, 1.004] | 0.797 [0.639, 0.987] | 0.0581 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 12 | 0.795 [0.670, 0.944] | 0.799 [0.650, 0.961] | 0.0161 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 12 | 1.062 [0.898, 1.255] | 1.071 [0.876, 1.302] | 0.4409 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | xs | 12 | 0.422 [0.396, 0.449] | 0.424 [0.403, 0.438] | 0.0005 | faster |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 12 | 0.421 [0.403, 0.440] | 0.426 [0.401, 0.439] | 0.0005 | faster |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 12 | 1.023 [0.957, 1.094] | 1.014 [0.974, 1.071] | 0.5205 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | xs | 12 | 0.414 [0.400, 0.428] | 0.413 [0.399, 0.429] | 0.0005 | faster |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 12 | 0.430 [0.411, 0.450] | 0.428 [0.409, 0.452] | 0.0005 | faster |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 12 | 1.064 [0.990, 1.144] | 1.045 [0.991, 1.148] | 0.0894 | inconclusive |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 12 | 0.933 [0.910, 0.956] | 0.931 [0.907, 0.959] | 0.0005 | faster |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 12 | 0.923 [0.891, 0.956] | 0.924 [0.888, 0.960] | 0.0005 | faster |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 12 | 1.010 [0.990, 1.031] | 1.010 [0.988, 1.033] | 0.2886 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 12 | 0.903 [0.883, 0.923] | 0.901 [0.883, 0.924] | 0.0005 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 12 | 0.906 [0.887, 0.926] | 0.905 [0.885, 0.928] | 0.0005 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 12 | 0.995 [0.980, 1.011] | 0.994 [0.978, 1.011] | 0.5117 | equivalent |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 12 | 0.914 [0.893, 0.936] | 0.911 [0.892, 0.937] | 0.0005 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 12 | 0.913 [0.888, 0.938] | 0.917 [0.887, 0.939] | 0.0005 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 12 | 0.995 [0.976, 1.014] | 0.994 [0.974, 1.016] | 0.5381 | equivalent |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 12 | 0.895 [0.874, 0.916] | 0.896 [0.872, 0.919] | 0.0005 | faster |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 12 | 0.910 [0.891, 0.929] | 0.911 [0.891, 0.933] | 0.0005 | faster |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 12 | 1.005 [0.986, 1.024] | 1.005 [0.983, 1.024] | 0.5874 | equivalent |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 1.934 [1.894, 1.975] | 0.993 [0.987, 0.999] | 10.143 [10.025, 10.263] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 1.978 [1.947, 2.010] | 0.994 [0.985, 1.002] | 10.197 [10.054, 10.343] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 0.982 [0.967, 0.998] | 0.996 [0.987, 1.005] | 1.000 [0.987, 1.012] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.285 [2.243, 2.328] | 1.058 [1.039, 1.078] | 7.940 [7.759, 8.125] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 2.293 [2.177, 2.414] | 1.130 [0.988, 1.291] | 7.944 [7.750, 8.144] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 1.008 [0.976, 1.042] | 1.017 [0.971, 1.066] | 0.991 [0.964, 1.019] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 1.728 [1.678, 1.779] | 0.616 [0.594, 0.639] | 1.449 [1.411, 1.489] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 1.742 [1.689, 1.797] | 0.609 [0.598, 0.620] | 1.469 [1.437, 1.503] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 1.011 [0.979, 1.044] | 0.991 [0.958, 1.025] | 1.028 [1.007, 1.050] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 1.797 [1.734, 1.862] | 0.670 [0.650, 0.689] | 1.394 [1.377, 1.411] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 1.844 [1.749, 1.944] | 0.692 [0.674, 0.711] | 1.381 [1.362, 1.401] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 0.983 [0.939, 1.029] | 0.995 [0.976, 1.014] | 1.007 [0.986, 1.029] |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 1.484 [1.451, 1.517] | 0.973 [0.950, 0.998] | 10.136 [9.911, 10.367] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 1.505 [1.470, 1.541] | 0.989 [0.965, 1.013] | 9.936 [9.571, 10.315] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 1.007 [0.980, 1.035] | 1.055 [0.988, 1.126] | 0.985 [0.950, 1.022] |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 1.488 [1.424, 1.556] | 0.826 [0.672, 1.015] | 7.521 [6.229, 9.080] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 1.507 [1.465, 1.549] | 0.817 [0.681, 0.979] | 7.555 [6.512, 8.765] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 1.003 [0.958, 1.051] | 1.054 [0.881, 1.260] | 1.006 [0.988, 1.025] |
| `small-flat.noop.freya-neo.sender.warm` | xs | 1.238 [1.106, 1.387] | 0.424 [0.399, 0.451] | 2.187 [2.150, 2.225] |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 1.229 [1.159, 1.304] | 0.424 [0.406, 0.442] | 2.184 [2.144, 2.225] |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 1.038 [0.944, 1.142] | 1.023 [0.957, 1.093] | 1.018 [0.999, 1.037] |
| `small-flat.noop.neo-freya.sender.warm` | xs | 1.353 [1.292, 1.416] | 0.416 [0.402, 0.430] | 1.713 [1.687, 1.739] |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 1.385 [1.302, 1.474] | 0.437 [0.416, 0.459] | 1.711 [1.675, 1.748] |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 1.079 [0.973, 1.196] | 1.068 [0.989, 1.153] | 0.990 [0.966, 1.014] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 1.620 [1.517, 1.729] | 0.935 [0.911, 0.959] | 1.343 [1.313, 1.374] |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 1.577 [1.497, 1.660] | 0.925 [0.893, 0.958] | 1.358 [1.326, 1.390] |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 1.002 [0.952, 1.055] | 1.012 [0.992, 1.033] | 1.006 [0.983, 1.030] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 1.361 [1.309, 1.416] | 0.900 [0.878, 0.923] | 1.367 [1.335, 1.399] |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 1.343 [1.294, 1.394] | 0.914 [0.886, 0.944] | 1.381 [1.355, 1.407] |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 0.990 [0.955, 1.026] | 0.995 [0.969, 1.023] | 1.005 [0.982, 1.030] |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 1.498 [1.448, 1.550] | 0.915 [0.894, 0.937] | 1.329 [1.301, 1.358] |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 1.576 [1.488, 1.669] | 0.914 [0.889, 0.940] | 1.332 [1.308, 1.358] |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 1.014 [0.984, 1.045] | 0.995 [0.975, 1.014] | 0.977 [0.952, 1.004] |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 1.381 [1.337, 1.427] | 0.878 [0.842, 0.915] | 1.340 [1.321, 1.360] |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 1.337 [1.288, 1.388] | 0.892 [0.850, 0.936] | 1.346 [1.325, 1.368] |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 1.000 [0.947, 1.055] | 0.985 [0.939, 1.033] | 0.990 [0.964, 1.017] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-same | xs | xs-same |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.362 | 12.314 | 12.251 | 12.307 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.270 | 12.539 | 13.088 | 13.773 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.379 | 0.376 | 0.232 | 0.230 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.278 | 0.277 | 0.185 | 0.192 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.675 | 7.020 | 6.443 | 6.530 |
| `small-flat.fresh.neo-freya.sender.warm` | 4.540 | 4.819 | 3.682 | 3.611 |
| `small-flat.noop.freya-neo.sender.warm` | 0.733 | 0.750 | 0.309 | 0.309 |
| `small-flat.noop.neo-freya.sender.warm` | 0.654 | 0.696 | 0.271 | 0.281 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.221 | 0.224 | 0.207 | 0.204 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.178 | 0.177 | 0.161 | 0.161 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.222 | 0.221 | 0.203 | 0.203 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.177 | 0.177 | 0.158 | 0.161 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs | 0.0102 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-same | 0.0072 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-same | 0.0140 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0279 | 9 | 12 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-same | 0.1620 | 238 | 318 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-same | 0.0703 | 47 | 62 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs | 0.0578 | 32 | 43 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | xs-same | 0.0266 | 9 | 11 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync-same | 0.0526 | 27 | 36 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs | 0.0422 | 18 | 24 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | xs-same | 0.0425 | 19 | 24 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync-same | 0.0299 | 11 | 13 |
| `small-flat.fresh.freya-neo.sender.warm` | xs | 0.0434 | 19 | 25 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-same | 0.0455 | 21 | 27 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-same | 0.1062 | 104 | 138 |
| `small-flat.fresh.neo-freya.sender.warm` | xs | 0.3365 | 1018 | 1364 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-same | 0.2700 | 657 | 879 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-same | 0.2639 | 627 | 840 |
| `small-flat.noop.freya-neo.sender.warm` | xs | 0.0977 | 88 | 117 |
| `small-flat.noop.freya-neo.sender.warm` | xs-same | 0.0683 | 44 | 59 |
| `small-flat.noop.freya-neo.sender.warm` | rsync-same | 0.1053 | 102 | 136 |
| `small-flat.noop.neo-freya.sender.warm` | xs | 0.0528 | 28 | 36 |
| `small-flat.noop.neo-freya.sender.warm` | xs-same | 0.0701 | 47 | 62 |
| `small-flat.noop.neo-freya.sender.warm` | rsync-same | 0.1133 | 118 | 157 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs | 0.0394 | 16 | 21 |
| `tiny-one.fresh.freya-neo.sender.warm` | xs-same | 0.0559 | 31 | 40 |
| `tiny-one.fresh.freya-neo.sender.warm` | rsync-same | 0.0316 | 11 | 14 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs | 0.0347 | 13 | 17 |
| `tiny-one.fresh.neo-freya.sender.warm` | xs-same | 0.0339 | 13 | 16 |
| `tiny-one.fresh.neo-freya.sender.warm` | rsync-same | 0.0240 | 8 | 9 |
| `tiny-one.noop.freya-neo.sender.warm` | xs | 0.0370 | 15 | 19 |
| `tiny-one.noop.freya-neo.sender.warm` | xs-same | 0.0433 | 19 | 25 |
| `tiny-one.noop.freya-neo.sender.warm` | rsync-same | 0.0303 | 11 | 14 |
| `tiny-one.noop.neo-freya.sender.warm` | xs | 0.0374 | 15 | 19 |
| `tiny-one.noop.neo-freya.sender.warm` | xs-same | 0.0334 | 13 | 16 |
| `tiny-one.noop.neo-freya.sender.warm` | rsync-same | 0.0304 | 11 | 14 |

## Voided attempts

- freya reaches neo by br-039e63f2ae7f, not enp10s0
