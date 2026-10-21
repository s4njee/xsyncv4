# J2-neo-local-jobs

On a four-core Pi copying locally, -j8 differs from -j4 by more than 5% in time-to-durable on small-file and no-op copies.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T170712Z-J2-neo-local-jobs.
- Valid blocks: 64. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 0.992 [0.975, 1.010] | 0.993 [0.970, 1.013] | 0.3203 | equivalent |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.987 [0.970, 1.005] | 0.986 [0.966, 1.006] | 0.1328 | equivalent |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | rsync | 8 | 1.246 [1.163, 1.335] | 1.264 [1.159, 1.334] | 0.0078 | slower |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 0.906 [0.707, 1.160] | 0.958 [0.669, 1.090] | 0.4688 | inconclusive |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.999 [0.728, 1.371] | 1.058 [0.685, 1.310] | 1.0000 | inconclusive |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | rsync | 8 | 4.428 [3.448, 5.687] | 4.913 [3.331, 5.281] | 0.0078 | slower |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 1.048 [0.950, 1.156] | 1.054 [0.949, 1.180] | 0.2812 | inconclusive |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.977 [0.886, 1.077] | 0.974 [0.872, 1.093] | 0.5938 | inconclusive |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 8 | 1.840 [1.701, 1.990] | 1.822 [1.699, 2.015] | 0.0078 | slower |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 0.963 [0.865, 1.071] | 0.958 [0.852, 1.082] | 0.4688 | inconclusive |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.975 [0.858, 1.107] | 0.949 [0.877, 1.143] | 0.6719 | inconclusive |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | rsync | 8 | 4.654 [4.270, 5.073] | 4.626 [4.239, 5.066] | 0.0078 | slower |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 0.838 [0.586, 1.197] | 0.834 [0.575, 1.298] | 0.2891 | inconclusive |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.865 [0.470, 1.590] | 0.804 [0.480, 1.731] | 0.5781 | inconclusive |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | rsync | 8 | 0.828 [0.539, 1.272] | 0.848 [0.501, 1.342] | 0.3203 | inconclusive |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 1.054 [0.838, 1.326] | 1.001 [0.870, 1.377] | 0.7031 | inconclusive |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.843 [0.772, 0.920] | 0.829 [0.770, 0.944] | 0.0156 | faster |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | rsync | 8 | 4.329 [3.804, 4.927] | 4.318 [3.814, 5.023] | 0.0078 | slower |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 0.999 [0.973, 1.026] | 0.997 [0.973, 1.029] | 0.9453 | equivalent |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 0.977 [0.956, 0.999] | 0.979 [0.954, 1.000] | 0.0391 | equivalent |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | rsync | 8 | 1.347 [1.258, 1.443] | 1.333 [1.255, 1.462] | 0.0078 | slower |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 8 | 1.162 [0.847, 1.596] | 1.249 [0.755, 1.542] | 0.2969 | inconclusive |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 8 | 1.065 [0.861, 1.318] | 1.042 [0.895, 1.404] | 0.6016 | inconclusive |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | rsync | 8 | 4.760 [3.786, 5.984] | 4.919 [3.563, 5.850] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `wall_s` |
|---|---|---|
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 1.004 [0.951, 1.060] |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.953 [0.892, 1.019] |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | rsync | 1.539 [1.394, 1.699] |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.924 [0.684, 1.249] |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.996 [0.688, 1.440] |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | rsync | 5.516 [4.104, 7.413] |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 1.048 [0.944, 1.164] |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.969 [0.871, 1.079] |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 1.874 [1.724, 2.037] |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.962 [0.864, 1.071] |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.975 [0.858, 1.107] |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | rsync | 4.672 [4.287, 5.092] |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.847 [0.582, 1.234] |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.872 [0.465, 1.636] |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.844 [0.538, 1.324] |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 1.054 [0.838, 1.327] |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.842 [0.772, 0.919] |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | rsync | 4.337 [3.811, 4.936] |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.996 [0.967, 1.026] |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.976 [0.956, 0.996] |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | rsync | 1.371 [1.282, 1.466] |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 1.173 [0.835, 1.646] |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 1.063 [0.851, 1.328] |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | rsync | 5.032 [3.960, 6.394] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-j4 | xs-j8 |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | 5.702 | 4.577 | 4.542 | 4.519 |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | 0.187 | 0.042 | 0.038 | 0.042 |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | 35.930 | 19.527 | 20.460 | 19.074 |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | 7.502 | 1.612 | 1.552 | 1.571 |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | 29.990 | 36.227 | 30.351 | 31.332 |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | 13.915 | 3.214 | 3.390 | 2.709 |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | 8.729 | 6.479 | 6.474 | 6.332 |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | 0.620 | 0.130 | 0.151 | 0.139 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.0209 | 8 | 8 |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.0214 | 8 | 8 |
| `mixed-bimodal.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.0826 | 64 | 85 |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.2965 | 791 | 1060 |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.3786 | 1289 | 1727 |
| `mixed-bimodal.noop.neo-neo-ssd.receiver.warm` | rsync | 0.2992 | 806 | 1079 |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.1176 | 127 | 169 |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.1171 | 126 | 167 |
| `real-congress.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.0939 | 82 | 108 |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.1273 | 148 | 197 |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.1520 | 210 | 280 |
| `real-congress.noop.neo-neo-ssd.receiver.warm` | rsync | 0.1030 | 98 | 130 |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.4266 | 1635 | 2191 |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.7286 | 4766 | 6386 |
| `small-deep.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.5140 | 2373 | 3180 |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.2742 | 677 | 907 |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.1045 | 100 | 134 |
| `small-deep.noop.neo-neo-ssd.receiver.warm` | rsync | 0.1547 | 217 | 290 |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j4 | 0.0315 | 11 | 14 |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | xs-j8 | 0.0258 | 8 | 10 |
| `small-flat.fresh.neo-neo-ssd.receiver.warm` | rsync | 0.0823 | 63 | 84 |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j4 | 0.3790 | 1291 | 1730 |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | xs-j8 | 0.2549 | 585 | 784 |
| `small-flat.noop.neo-neo-ssd.receiver.warm` | rsync | 0.2738 | 675 | 904 |

## Voided attempts

- xs: did not settle: neo is 21% busy; neo-ssd is 21% busy
