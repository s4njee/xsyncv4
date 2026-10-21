# T1f-send-streams

Capping the sender at one or two large-file streams makes byte-bound copies from neo as fast as one sending worker does, without slowing small files or no-ops.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T114615Z-T1f-send-streams.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams1 | 10 | 1.005 [0.998, 1.013] | 1.005 [0.998, 1.013] | 0.1328 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams2 | 10 | 1.004 [0.998, 1.010] | 1.003 [0.998, 1.010] | 0.1562 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 10 | 1.001 [0.996, 1.007] | 1.002 [0.996, 1.007] | 0.5898 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 10 | 1.006 [0.999, 1.013] | 1.007 [0.999, 1.012] | 0.0859 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams1 | 10 | 0.987 [0.977, 0.998] | 0.987 [0.977, 0.999] | 0.0312 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams2 | 10 | 1.002 [0.989, 1.015] | 1.004 [0.988, 1.018] | 0.7207 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 10 | 0.965 [0.952, 0.978] | 0.965 [0.952, 0.976] | 0.0020 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 10 | 0.965 [0.952, 0.977] | 0.965 [0.952, 0.977] | 0.0020 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams1 | 10 | 0.989 [0.917, 1.066] | 0.979 [0.917, 1.063] | 0.7402 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams2 | 10 | 1.000 [0.950, 1.052] | 1.006 [0.949, 1.055] | 0.9844 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 10 | 1.008 [0.956, 1.062] | 1.014 [0.950, 1.065] | 0.7520 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 10 | 1.605 [1.539, 1.675] | 1.616 [1.532, 1.675] | 0.0020 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams1 | 10 | 1.008 [0.974, 1.043] | 1.007 [0.975, 1.053] | 0.6172 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams2 | 10 | 1.036 [1.006, 1.067] | 1.041 [1.003, 1.057] | 0.0273 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 10 | 1.191 [1.142, 1.242] | 1.189 [1.150, 1.242] | 0.0020 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 10 | 1.564 [1.499, 1.631] | 1.551 [1.504, 1.637] | 0.0020 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | streams1 | 10 | 1.002 [0.991, 1.014] | 0.999 [0.992, 1.016] | 0.6621 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | streams2 | 10 | 1.003 [0.993, 1.013] | 1.002 [0.993, 1.012] | 0.5605 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 10 | 1.000 [0.981, 1.019] | 0.996 [0.981, 1.018] | 0.9824 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 10 | 1.036 [1.003, 1.069] | 1.030 [1.005, 1.072] | 0.0176 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | streams1 | 10 | 0.996 [0.979, 1.014] | 0.998 [0.980, 1.016] | 0.6250 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | streams2 | 10 | 0.993 [0.970, 1.015] | 0.992 [0.972, 1.015] | 0.4727 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 10 | 1.578 [1.237, 2.013] | 1.583 [1.214, 2.043] | 0.0039 | slower |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 10 | 1.471 [1.150, 1.883] | 1.450 [1.108, 1.888] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | streams1 | 10 | 1.054 [0.989, 1.123] | 1.039 [0.995, 1.138] | 0.0645 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | streams2 | 10 | 0.995 [0.944, 1.049] | 0.997 [0.946, 1.060] | 0.8438 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 10 | 1.134 [1.063, 1.211] | 1.124 [1.058, 1.214] | 0.0020 | slower |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 10 | 2.435 [2.204, 2.691] | 2.369 [2.242, 2.785] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | streams1 | 10 | 0.959 [0.876, 1.050] | 0.962 [0.885, 1.049] | 0.3262 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | streams2 | 10 | 1.024 [0.896, 1.171] | 1.020 [0.881, 1.177] | 0.6973 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 10 | 1.606 [1.373, 1.879] | 1.576 [1.395, 1.914] | 0.0020 | slower |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 10 | 2.395 [2.166, 2.648] | 2.391 [2.153, 2.680] | 0.0020 | slower |
| `small-real.fresh.freya-neo.sender.warm` | streams1 | 10 | 1.004 [0.916, 1.100] | 1.036 [0.904, 1.085] | 0.9160 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | streams2 | 10 | 0.992 [0.936, 1.052] | 1.000 [0.928, 1.048] | 0.7695 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 10 | 1.057 [0.973, 1.148] | 1.051 [0.974, 1.156] | 0.1621 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 10 | 1.366 [1.276, 1.461] | 1.381 [1.280, 1.463] | 0.0020 | slower |
| `small-real.fresh.neo-freya.sender.warm` | streams1 | 10 | 0.982 [0.851, 1.134] | 0.993 [0.805, 1.176] | 0.5781 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | streams2 | 10 | 1.090 [0.900, 1.320] | 1.053 [0.986, 1.262] | 0.3770 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 10 | 1.188 [1.035, 1.363] | 1.216 [1.015, 1.342] | 0.0273 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 10 | 1.100 [0.977, 1.240] | 1.099 [0.963, 1.234] | 0.1035 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | streams1 | 10 | 1.010 [0.923, 1.105] | 1.023 [0.921, 1.112] | 0.7969 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | streams2 | 10 | 0.945 [0.857, 1.041] | 0.967 [0.854, 1.048] | 0.2246 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | send1 | 10 | 1.020 [0.918, 1.132] | 1.039 [0.910, 1.121] | 0.6855 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | rsync | 10 | 6.128 [5.643, 6.655] | 6.198 [5.551, 6.606] | 0.0020 | slower |
| `small-real.noop.neo-freya.sender.warm` | streams1 | 10 | 0.868 [0.707, 1.065] | 0.846 [0.705, 1.082] | 0.1445 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | streams2 | 10 | 1.000 [0.927, 1.080] | 1.002 [0.925, 1.082] | 0.9785 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | send1 | 10 | 0.877 [0.785, 0.980] | 0.877 [0.788, 0.976] | 0.0254 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | rsync | 10 | 1.104 [0.997, 1.221] | 1.098 [1.001, 1.223] | 0.0469 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams1 | 0.914 [0.895, 0.934] | 0.998 [0.986, 1.009] | 1.022 [1.009, 1.035] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams2 | 0.942 [0.918, 0.966] | 1.002 [0.989, 1.014] | 1.023 [1.017, 1.029] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.855 [0.832, 0.878] | 0.996 [0.986, 1.007] | 0.776 [0.770, 0.782] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.502 [0.495, 0.510] | 1.003 [0.994, 1.013] | 0.101 [0.099, 0.104] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams1 | 0.897 [0.870, 0.925] | 0.988 [0.978, 0.998] | 1.004 [0.999, 1.008] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams2 | 0.998 [0.969, 1.028] | 1.002 [0.990, 1.015] | 1.001 [0.996, 1.007] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.700 [0.674, 0.726] | 0.965 [0.952, 0.978] | 0.940 [0.935, 0.944] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.460 [0.443, 0.478] | 0.965 [0.952, 0.977] | 0.121 [0.119, 0.123] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams1 | 0.984 [0.947, 1.023] | 0.989 [0.919, 1.064] | 0.989 [0.965, 1.014] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams2 | 0.981 [0.948, 1.015] | 1.000 [0.954, 1.048] | 0.985 [0.958, 1.014] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 0.492 [0.470, 0.515] | 1.006 [0.956, 1.060] | 0.697 [0.682, 0.713] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.571 [0.552, 0.591] | 1.581 [1.515, 1.649] | 0.697 [0.679, 0.715] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams1 | 1.055 [0.950, 1.171] | 1.007 [0.973, 1.043] | 0.997 [0.983, 1.012] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams2 | 1.085 [0.992, 1.186] | 1.036 [1.005, 1.067] | 1.005 [0.993, 1.018] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 0.773 [0.708, 0.844] | 1.188 [1.139, 1.239] | 1.000 [0.987, 1.013] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.600 [0.538, 0.669] | 1.559 [1.495, 1.625] | 0.704 [0.676, 0.733] |
| `small-flat.fresh.freya-neo.sender.warm` | streams1 | 1.002 [0.990, 1.014] | 1.000 [0.985, 1.016] | 1.010 [0.990, 1.031] |
| `small-flat.fresh.freya-neo.sender.warm` | streams2 | 1.010 [0.996, 1.024] | 1.000 [0.990, 1.011] | 0.999 [0.980, 1.018] |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 0.839 [0.825, 0.852] | 0.993 [0.972, 1.014] | 0.784 [0.772, 0.795] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.677 [0.651, 0.704] | 1.030 [0.998, 1.063] | 0.099 [0.096, 0.101] |
| `small-flat.fresh.neo-freya.sender.warm` | streams1 | 0.986 [0.957, 1.017] | 0.994 [0.976, 1.012] | 1.065 [0.931, 1.219] |
| `small-flat.fresh.neo-freya.sender.warm` | streams2 | 1.002 [0.966, 1.039] | 0.992 [0.972, 1.012] | 1.058 [0.898, 1.247] |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 0.754 [0.721, 0.789] | 1.566 [1.235, 1.985] | 0.343 [0.264, 0.446] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.659 [0.635, 0.683] | 1.457 [1.144, 1.856] | 0.156 [0.132, 0.186] |
| `small-flat.noop.freya-neo.sender.warm` | streams1 | 1.076 [0.973, 1.191] | 1.053 [0.991, 1.118] | 0.994 [0.980, 1.008] |
| `small-flat.noop.freya-neo.sender.warm` | streams2 | 1.018 [0.936, 1.106] | 0.994 [0.944, 1.047] | 1.003 [0.990, 1.015] |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 0.932 [0.786, 1.106] | 1.129 [1.059, 1.204] | 0.457 [0.442, 0.473] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.837 [0.722, 0.971] | 2.395 [2.169, 2.645] | 0.466 [0.453, 0.479] |
| `small-flat.noop.neo-freya.sender.warm` | streams1 | 0.992 [0.884, 1.113] | 0.958 [0.876, 1.048] | 1.003 [0.990, 1.016] |
| `small-flat.noop.neo-freya.sender.warm` | streams2 | 1.058 [0.870, 1.286] | 1.023 [0.895, 1.168] | 1.018 [1.008, 1.029] |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 0.811 [0.708, 0.928] | 1.600 [1.368, 1.872] | 0.984 [0.968, 1.000] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.753 [0.671, 0.844] | 2.381 [2.153, 2.634] | 0.586 [0.574, 0.598] |
| `small-real.fresh.freya-neo.sender.warm` | streams1 | 0.995 [0.951, 1.040] | 1.005 [0.922, 1.094] | 1.001 [0.973, 1.030] |
| `small-real.fresh.freya-neo.sender.warm` | streams2 | 1.005 [0.979, 1.031] | 0.990 [0.932, 1.052] | 0.999 [0.972, 1.027] |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 0.766 [0.734, 0.798] | 1.060 [0.977, 1.150] | 0.818 [0.800, 0.836] |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.939 [0.902, 0.977] | 1.353 [1.269, 1.443] | 1.298 [1.271, 1.326] |
| `small-real.fresh.neo-freya.sender.warm` | streams1 | 0.996 [0.968, 1.024] | 0.983 [0.850, 1.137] | 1.017 [0.976, 1.061] |
| `small-real.fresh.neo-freya.sender.warm` | streams2 | 0.979 [0.948, 1.012] | 1.091 [0.901, 1.321] | 1.004 [0.947, 1.065] |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 0.849 [0.822, 0.876] | 1.189 [1.034, 1.367] | 0.486 [0.422, 0.561] |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.506 [0.495, 0.516] | 1.097 [0.971, 1.238] | 0.099 [0.096, 0.102] |
| `small-real.noop.freya-neo.sender.warm` | streams1 | 0.998 [0.975, 1.021] | 1.010 [0.923, 1.105] | 1.009 [0.976, 1.043] |
| `small-real.noop.freya-neo.sender.warm` | streams2 | 0.981 [0.944, 1.019] | 0.945 [0.858, 1.041] | 0.991 [0.954, 1.029] |
| `small-real.noop.freya-neo.sender.warm` | send1 | 0.418 [0.389, 0.449] | 1.019 [0.919, 1.131] | 0.921 [0.889, 0.954] |
| `small-real.noop.freya-neo.sender.warm` | rsync | 0.807 [0.776, 0.839] | 6.100 [5.620, 6.621] | 1.581 [1.536, 1.628] |
| `small-real.noop.neo-freya.sender.warm` | streams1 | 1.015 [1.005, 1.024] | 0.868 [0.707, 1.064] | 1.002 [0.939, 1.069] |
| `small-real.noop.neo-freya.sender.warm` | streams2 | 0.984 [0.937, 1.033] | 1.000 [0.927, 1.080] | 1.023 [0.943, 1.110] |
| `small-real.noop.neo-freya.sender.warm` | send1 | 0.466 [0.404, 0.538] | 0.882 [0.790, 0.986] | 1.003 [0.955, 1.055] |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.114 [0.111, 0.118] | 1.103 [0.997, 1.221] | 0.216 [0.207, 0.226] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | send1 | streams1 | streams2 | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.291 | 12.236 | 12.286 | 12.269 | 12.220 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.239 | 12.240 | 12.529 | 12.713 | 12.687 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.378 | 0.238 | 0.233 | 0.236 | 0.236 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.290 | 0.221 | 0.187 | 0.192 | 0.186 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.827 | 6.591 | 6.609 | 6.610 | 6.593 |
| `small-flat.fresh.neo-freya.sender.warm` | 5.056 | 5.423 | 3.423 | 3.411 | 3.437 |
| `small-flat.noop.freya-neo.sender.warm` | 0.762 | 0.355 | 0.330 | 0.311 | 0.313 |
| `small-flat.noop.neo-freya.sender.warm` | 0.702 | 0.471 | 0.281 | 0.300 | 0.293 |
| `small-real.fresh.freya-neo.sender.warm` | 23.836 | 18.454 | 17.521 | 17.316 | 17.454 |
| `small-real.fresh.neo-freya.sender.warm` | 12.925 | 13.949 | 11.537 | 12.806 | 11.746 |
| `small-real.noop.freya-neo.sender.warm` | 9.570 | 1.592 | 1.577 | 1.475 | 1.562 |
| `small-real.noop.neo-freya.sender.warm` | 2.040 | 1.621 | 1.604 | 1.849 | 1.848 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams1 | 0.0104 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | streams2 | 0.0084 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.0073 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0095 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams1 | 0.0149 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | streams2 | 0.0178 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.0189 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0178 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams1 | 0.1049 | 101 | 135 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | streams2 | 0.0709 | 48 | 63 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | send1 | 0.0736 | 51 | 68 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.0590 | 34 | 44 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams1 | 0.0480 | 23 | 30 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | streams2 | 0.0412 | 18 | 23 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | send1 | 0.0585 | 33 | 44 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.0589 | 34 | 44 |
| `small-flat.fresh.freya-neo.sender.warm` | streams1 | 0.0154 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | streams2 | 0.0140 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | send1 | 0.0267 | 9 | 11 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0447 | 20 | 27 |
| `small-flat.fresh.neo-freya.sender.warm` | streams1 | 0.0243 | 8 | 10 |
| `small-flat.fresh.neo-freya.sender.warm` | streams2 | 0.0316 | 11 | 15 |
| `small-flat.fresh.neo-freya.sender.warm` | send1 | 0.3401 | 1041 | 1394 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.3448 | 1069 | 1432 |
| `small-flat.noop.freya-neo.sender.warm` | streams1 | 0.0890 | 74 | 98 |
| `small-flat.noop.freya-neo.sender.warm` | streams2 | 0.0737 | 51 | 68 |
| `small-flat.noop.freya-neo.sender.warm` | send1 | 0.0912 | 77 | 102 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.1397 | 178 | 237 |
| `small-flat.noop.neo-freya.sender.warm` | streams1 | 0.1265 | 146 | 195 |
| `small-flat.noop.neo-freya.sender.warm` | streams2 | 0.1874 | 318 | 425 |
| `small-flat.noop.neo-freya.sender.warm` | send1 | 0.2197 | 435 | 583 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1405 | 180 | 240 |
| `small-real.fresh.freya-neo.sender.warm` | streams1 | 0.1274 | 148 | 198 |
| `small-real.fresh.freya-neo.sender.warm` | streams2 | 0.0815 | 62 | 82 |
| `small-real.fresh.freya-neo.sender.warm` | send1 | 0.1155 | 122 | 163 |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.0944 | 82 | 110 |
| `small-real.fresh.neo-freya.sender.warm` | streams1 | 0.2008 | 364 | 487 |
| `small-real.fresh.neo-freya.sender.warm` | streams2 | 0.2674 | 644 | 863 |
| `small-real.fresh.neo-freya.sender.warm` | send1 | 0.1927 | 336 | 449 |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.1666 | 252 | 336 |
| `small-real.noop.freya-neo.sender.warm` | streams1 | 0.1263 | 146 | 194 |
| `small-real.noop.freya-neo.sender.warm` | streams2 | 0.1363 | 169 | 226 |
| `small-real.noop.freya-neo.sender.warm` | send1 | 0.1465 | 195 | 261 |
| `small-real.noop.freya-neo.sender.warm` | rsync | 0.1153 | 122 | 162 |
| `small-real.noop.neo-freya.sender.warm` | streams1 | 0.2861 | 737 | 987 |
| `small-real.noop.neo-freya.sender.warm` | streams2 | 0.1070 | 105 | 140 |
| `small-real.noop.neo-freya.sender.warm` | send1 | 0.1547 | 217 | 290 |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.1419 | 183 | 245 |
