# L1-recv-tune

Fewer receiving workers on freya, and --no-atomic on either end, make small fresh copies faster.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T152107Z-L1-recv-tune.
- Valid blocks: 100. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 10 | 0.997 [0.988, 1.007] | 1.000 [0.986, 1.005] | 0.6367 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.003 [0.997, 1.009] | 1.003 [0.998, 1.010] | 0.2324 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.005 [0.996, 1.014] | 1.001 [0.999, 1.018] | 0.2734 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 10 | 1.000 [0.994, 1.005] | 0.999 [0.994, 1.005] | 0.9121 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4-noatomic | 10 | 1.002 [0.993, 1.012] | 1.000 [0.993, 1.015] | 0.6934 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 10 | 1.000 [0.992, 1.008] | 1.000 [0.992, 1.008] | 0.9551 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 10 | 0.998 [0.990, 1.006] | 0.999 [0.989, 1.006] | 0.5957 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 10 | 1.003 [0.994, 1.013] | 1.002 [0.995, 1.012] | 0.4688 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 10 | 0.998 [0.990, 1.005] | 0.999 [0.990, 1.005] | 0.4688 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4-noatomic | 10 | 0.999 [0.990, 1.009] | 1.000 [0.989, 1.009] | 0.8457 | equivalent |
| `small-deep.fresh.freya-neo.sender.warm` | recv2 | 10 | 1.076 [1.035, 1.118] | 1.069 [1.033, 1.116] | 0.0020 | slower |
| `small-deep.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.030 [0.977, 1.087] | 1.026 [0.978, 1.091] | 0.2598 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.051 [0.994, 1.112] | 1.056 [0.993, 1.114] | 0.0801 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 10 | 1.013 [0.955, 1.075] | 1.018 [0.955, 1.068] | 0.6270 | inconclusive |
| `small-deep.fresh.freya-neo.sender.warm` | recv4-noatomic | 10 | 0.994 [0.954, 1.035] | 0.992 [0.953, 1.038] | 0.7422 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv2 | 10 | 1.065 [0.932, 1.216] | 1.034 [0.943, 1.246] | 0.3574 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 10 | 1.123 [0.876, 1.442] | 1.036 [0.940, 1.636] | 0.3887 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.992 [0.902, 1.091] | 0.993 [0.901, 1.098] | 0.8594 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 10 | 0.991 [0.664, 1.479] | 0.967 [0.688, 1.583] | 0.9473 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv4-noatomic | 10 | 1.032 [0.788, 1.353] | 0.928 [0.864, 1.557] | 0.9785 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 10 | 0.966 [0.961, 0.971] | 0.966 [0.961, 0.971] | 0.0020 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 10 | 1.004 [0.994, 1.014] | 1.006 [0.993, 1.013] | 0.4297 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.021 [1.006, 1.036] | 1.020 [1.009, 1.037] | 0.0098 | inconclusive |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 10 | 0.708 [0.698, 0.717] | 0.708 [0.698, 0.718] | 0.0020 | faster |
| `small-flat.fresh.freya-neo.sender.warm` | recv4-noatomic | 10 | 0.713 [0.703, 0.723] | 0.713 [0.704, 0.724] | 0.0020 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 10 | 0.969 [0.954, 0.984] | 0.969 [0.954, 0.984] | 0.0059 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 10 | 0.953 [0.935, 0.972] | 0.954 [0.933, 0.976] | 0.0020 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.978 [0.963, 0.994] | 0.980 [0.963, 0.994] | 0.0098 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 10 | 0.889 [0.865, 0.913] | 0.888 [0.864, 0.911] | 0.0020 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | recv4-noatomic | 10 | 0.878 [0.863, 0.893] | 0.877 [0.864, 0.894] | 0.0020 | faster |
| `small-opaque.fresh.freya-neo.sender.warm` | recv2 | 10 | 0.969 [0.955, 0.983] | 0.969 [0.954, 0.985] | 0.0020 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4 | 10 | 0.999 [0.990, 1.008] | 0.999 [0.991, 1.008] | 0.8242 | equivalent |
| `small-opaque.fresh.freya-neo.sender.warm` | recv8 | 10 | 1.019 [1.008, 1.031] | 1.018 [1.008, 1.031] | 0.0039 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 10 | 0.702 [0.690, 0.714] | 0.702 [0.690, 0.714] | 0.0020 | faster |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4-noatomic | 10 | 0.698 [0.686, 0.710] | 0.697 [0.684, 0.712] | 0.0020 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | recv2 | 10 | 0.976 [0.966, 0.986] | 0.974 [0.966, 0.988] | 0.0039 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 10 | 0.968 [0.952, 0.983] | 0.968 [0.951, 0.983] | 0.0020 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 10 | 0.996 [0.968, 1.025] | 0.993 [0.969, 1.022] | 0.7578 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | no-atomic | 10 | 0.875 [0.866, 0.884] | 0.873 [0.866, 0.883] | 0.0020 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4-noatomic | 10 | 0.875 [0.867, 0.883] | 0.875 [0.867, 0.883] | 0.0020 | faster |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 10 | 1.020 [0.969, 1.073] | 1.029 [0.964, 1.063] | 0.4121 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 10 | 0.970 [0.898, 1.048] | 0.973 [0.883, 1.053] | 0.3906 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 10 | 0.991 [0.927, 1.059] | 0.996 [0.929, 1.054] | 0.7598 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 10 | 0.972 [0.905, 1.044] | 0.973 [0.900, 1.042] | 0.3867 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recv4-noatomic | 10 | 0.926 [0.875, 0.981] | 0.929 [0.872, 0.980] | 0.0156 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 10 | 1.108 [0.929, 1.320] | 1.001 [0.976, 1.324] | 0.4727 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 10 | 1.033 [0.912, 1.171] | 0.981 [0.968, 1.278] | 0.9961 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 10 | 1.057 [0.937, 1.192] | 0.989 [0.980, 1.275] | 0.5000 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 10 | 1.024 [0.997, 1.052] | 1.016 [1.001, 1.059] | 0.0312 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv4-noatomic | 10 | 1.030 [0.904, 1.174] | 0.974 [0.965, 1.287] | 0.9980 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 0.995 [0.977, 1.012] | 0.995 [0.984, 1.007] | 0.996 [0.985, 1.006] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 1.006 [0.992, 1.021] | 1.001 [0.995, 1.008] | 1.000 [0.991, 1.009] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 0.991 [0.980, 1.003] | 1.000 [0.987, 1.012] | 0.995 [0.989, 1.002] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 0.975 [0.966, 0.985] | 0.994 [0.984, 1.005] | 0.995 [0.988, 1.001] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.976 [0.955, 0.996] | 1.000 [0.989, 1.011] | 1.002 [0.993, 1.011] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 0.997 [0.965, 1.031] | 0.999 [0.989, 1.009] | 1.000 [0.993, 1.006] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 0.987 [0.956, 1.019] | 0.997 [0.987, 1.007] | 1.001 [0.998, 1.005] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.992 [0.952, 1.034] | 1.002 [0.990, 1.013] | 0.999 [0.995, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 0.975 [0.946, 1.005] | 0.996 [0.988, 1.003] | 1.000 [0.994, 1.006] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.988 [0.954, 1.023] | 0.998 [0.988, 1.009] | 1.000 [0.994, 1.006] |
| `small-deep.fresh.freya-neo.sender.warm` | recv2 | 0.947 [0.888, 1.010] | 1.072 [1.034, 1.111] | 0.988 [0.914, 1.068] |
| `small-deep.fresh.freya-neo.sender.warm` | recv4 | 1.019 [0.931, 1.116] | 1.026 [0.972, 1.082] | 0.940 [0.872, 1.013] |
| `small-deep.fresh.freya-neo.sender.warm` | recv8 | 1.037 [0.961, 1.118] | 1.046 [0.989, 1.106] | 1.016 [0.953, 1.084] |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 0.995 [0.935, 1.058] | 1.007 [0.950, 1.067] | 0.972 [0.911, 1.038] |
| `small-deep.fresh.freya-neo.sender.warm` | recv4-noatomic | 1.014 [0.941, 1.092] | 0.990 [0.952, 1.030] | 0.971 [0.912, 1.033] |
| `small-deep.fresh.neo-freya.sender.warm` | recv2 | 0.649 [0.627, 0.671] | 1.065 [0.932, 1.216] | 1.081 [0.914, 1.278] |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 0.669 [0.645, 0.695] | 1.116 [0.874, 1.426] | 1.107 [0.933, 1.313] |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 0.800 [0.765, 0.837] | 0.998 [0.912, 1.092] | 0.966 [0.797, 1.171] |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 0.940 [0.891, 0.992] | 0.981 [0.666, 1.445] | 1.136 [0.869, 1.487] |
| `small-deep.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.636 [0.611, 0.662] | 1.038 [0.795, 1.355] | 1.111 [0.945, 1.305] |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 0.970 [0.953, 0.988] | 0.972 [0.965, 0.980] | 0.991 [0.972, 1.010] |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 0.999 [0.986, 1.011] | 1.006 [0.995, 1.017] | 0.988 [0.961, 1.017] |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 1.012 [0.987, 1.038] | 1.023 [1.008, 1.039] | 1.004 [0.972, 1.037] |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 0.816 [0.800, 0.833] | 0.727 [0.718, 0.737] | 1.013 [0.979, 1.047] |
| `small-flat.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.819 [0.806, 0.832] | 0.723 [0.714, 0.733] | 1.023 [0.994, 1.051] |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 0.992 [0.958, 1.026] | 0.976 [0.952, 1.001] | 0.969 [0.788, 1.191] |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.948 [0.913, 0.984] | 0.983 [0.948, 1.020] | 1.096 [0.930, 1.292] |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 0.964 [0.942, 0.987] | 0.979 [0.961, 0.997] | 1.149 [0.937, 1.409] |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 0.774 [0.730, 0.820] | 0.891 [0.862, 0.921] | 0.892 [0.663, 1.199] |
| `small-flat.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.762 [0.731, 0.793] | 0.874 [0.860, 0.888] | 1.170 [0.927, 1.476] |
| `small-opaque.fresh.freya-neo.sender.warm` | recv2 | 0.968 [0.953, 0.983] | 0.966 [0.952, 0.981] | 0.980 [0.947, 1.015] |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4 | 1.006 [0.984, 1.028] | 0.999 [0.990, 1.009] | 1.004 [0.981, 1.029] |
| `small-opaque.fresh.freya-neo.sender.warm` | recv8 | 1.019 [1.002, 1.037] | 1.019 [1.004, 1.034] | 0.987 [0.944, 1.031] |
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 0.800 [0.782, 0.819] | 0.715 [0.702, 0.729] | 1.011 [0.994, 1.029] |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.802 [0.789, 0.815] | 0.714 [0.703, 0.724] | 1.015 [0.991, 1.039] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv2 | 0.985 [0.955, 1.016] | 0.973 [0.966, 0.980] | 0.991 [0.921, 1.066] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 0.986 [0.950, 1.023] | 0.981 [0.948, 1.014] | 0.968 [0.886, 1.058] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 1.008 [0.976, 1.041] | 0.989 [0.965, 1.014] | 0.994 [0.950, 1.041] |
| `small-opaque.fresh.neo-freya.sender.warm` | no-atomic | 0.776 [0.750, 0.804] | 0.877 [0.853, 0.901] | 0.913 [0.795, 1.048] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.775 [0.741, 0.811] | 0.868 [0.863, 0.872] | 0.949 [0.808, 1.115] |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 0.928 [0.902, 0.956] | 1.011 [0.965, 1.059] | 1.006 [0.997, 1.016] |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 0.984 [0.946, 1.023] | 0.972 [0.901, 1.048] | 1.006 [0.987, 1.025] |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 0.998 [0.966, 1.032] | 0.990 [0.929, 1.055] | 1.012 [0.999, 1.026] |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 0.939 [0.901, 0.980] | 0.972 [0.905, 1.045] | 1.009 [0.993, 1.025] |
| `small-real.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.925 [0.896, 0.956] | 0.928 [0.876, 0.982] | 1.004 [0.989, 1.018] |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 0.742 [0.722, 0.763] | 1.112 [0.933, 1.325] | 1.002 [0.965, 1.041] |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.762 [0.745, 0.780] | 1.032 [0.911, 1.169] | 0.991 [0.962, 1.020] |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.893 [0.869, 0.919] | 1.065 [0.947, 1.199] | 1.016 [0.993, 1.039] |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 0.957 [0.930, 0.985] | 1.026 [0.998, 1.055] | 1.003 [0.966, 1.041] |
| `small-real.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.748 [0.732, 0.765] | 1.035 [0.910, 1.178] | 0.971 [0.937, 1.005] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | no-atomic | recv2 | recv4 | recv4-noatomic | recv8 | xs |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.525 | 12.493 | 12.569 | 12.560 | 12.591 | 12.529 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.403 | 12.431 | 12.409 | 12.422 | 12.476 | 12.433 |
| `small-deep.fresh.freya-neo.sender.warm` | 15.433 | 16.379 | 15.688 | 15.133 | 16.005 | 15.227 |
| `small-deep.fresh.neo-freya.sender.warm` | 6.539 | 7.024 | 7.413 | 6.812 | 6.545 | 6.598 |
| `small-flat.fresh.freya-neo.sender.warm` | 3.844 | 5.247 | 5.454 | 3.872 | 5.548 | 5.433 |
| `small-flat.fresh.neo-freya.sender.warm` | 2.997 | 3.268 | 3.214 | 2.960 | 3.299 | 3.372 |
| `small-opaque.fresh.freya-neo.sender.warm` | 3.865 | 5.332 | 5.500 | 3.844 | 5.612 | 5.505 |
| `small-opaque.fresh.neo-freya.sender.warm` | 2.958 | 3.300 | 3.272 | 2.958 | 3.368 | 3.381 |
| `small-real.fresh.freya-neo.sender.warm` | 12.985 | 13.625 | 12.966 | 12.377 | 13.239 | 13.361 |
| `small-real.fresh.neo-freya.sender.warm` | 11.239 | 12.152 | 11.337 | 11.306 | 11.594 | 10.972 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv2 | 0.0132 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4 | 0.0080 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv8 | 0.0126 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | no-atomic | 0.0077 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.0139 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv2 | 0.0108 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 0.0111 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.0133 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | no-atomic | 0.0101 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.0132 | 8 | 8 |
| `small-deep.fresh.freya-neo.sender.warm` | recv2 | 0.0537 | 28 | 37 |
| `small-deep.fresh.freya-neo.sender.warm` | recv4 | 0.0749 | 53 | 70 |
| `small-deep.fresh.freya-neo.sender.warm` | recv8 | 0.0785 | 58 | 77 |
| `small-deep.fresh.freya-neo.sender.warm` | no-atomic | 0.0829 | 64 | 85 |
| `small-deep.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.0572 | 32 | 42 |
| `small-deep.fresh.neo-freya.sender.warm` | recv2 | 0.1855 | 311 | 416 |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 0.3485 | 1092 | 1463 |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 0.1329 | 161 | 215 |
| `small-deep.fresh.neo-freya.sender.warm` | no-atomic | 0.5592 | 2809 | 3764 |
| `small-deep.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.3784 | 1287 | 1725 |
| `small-flat.fresh.freya-neo.sender.warm` | recv2 | 0.0073 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | recv4 | 0.0145 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | recv8 | 0.0203 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | no-atomic | 0.0184 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.0192 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | recv2 | 0.0217 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.0276 | 9 | 12 |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 0.0227 | 8 | 9 |
| `small-flat.fresh.neo-freya.sender.warm` | no-atomic | 0.0375 | 15 | 19 |
| `small-flat.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.0239 | 8 | 9 |
| `small-opaque.fresh.freya-neo.sender.warm` | recv2 | 0.0204 | 8 | 8 |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4 | 0.0127 | 8 | 8 |
| `small-opaque.fresh.freya-neo.sender.warm` | recv8 | 0.0158 | 8 | 8 |
| `small-opaque.fresh.freya-neo.sender.warm` | no-atomic | 0.0235 | 8 | 9 |
| `small-opaque.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.0240 | 8 | 9 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv2 | 0.0149 | 8 | 8 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 0.0220 | 8 | 8 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 0.0403 | 17 | 22 |
| `small-opaque.fresh.neo-freya.sender.warm` | no-atomic | 0.0141 | 8 | 8 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.0125 | 8 | 8 |
| `small-real.fresh.freya-neo.sender.warm` | recv2 | 0.0713 | 48 | 64 |
| `small-real.fresh.freya-neo.sender.warm` | recv4 | 0.1078 | 107 | 142 |
| `small-real.fresh.freya-neo.sender.warm` | recv8 | 0.0928 | 80 | 106 |
| `small-real.fresh.freya-neo.sender.warm` | no-atomic | 0.1004 | 93 | 124 |
| `small-real.fresh.freya-neo.sender.warm` | recv4-noatomic | 0.0795 | 59 | 78 |
| `small-real.fresh.neo-freya.sender.warm` | recv2 | 0.2454 | 543 | 727 |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.1745 | 276 | 369 |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.1686 | 258 | 344 |
| `small-real.fresh.neo-freya.sender.warm` | no-atomic | 0.0372 | 15 | 19 |
| `small-real.fresh.neo-freya.sender.warm` | recv4-noatomic | 0.1823 | 301 | 402 |
