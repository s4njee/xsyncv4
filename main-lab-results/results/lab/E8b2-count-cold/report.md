# E8b2-count-cold

Descriptive: the xs to rsync ratio as a smooth function of the swept variable, each point with its interval.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220943Z-E8b2-count-cold.
- Valid blocks: 112. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.cold` | xs | 4 | 0.884 [0.708, 1.103] | 0.928 | 0.1250 | too few blocks |
| `scale-count-1000.fresh.neo-freya.sender.cold` | xs | 4 | 1.124 [0.971, 1.301] | 1.077 | 0.1250 | too few blocks |
| `scale-count-1000.noop.freya-neo.sender.cold` | xs | 4 | 0.913 [0.850, 0.981] | 0.921 | 0.1250 | too few blocks |
| `scale-count-1000.noop.neo-freya.sender.cold` | xs | 4 | 0.924 [0.888, 0.962] | 0.926 | 0.1250 | too few blocks |
| `scale-count-10000.fresh.freya-neo.sender.cold` | xs | 4 | 0.561 [0.503, 0.627] | 0.546 | 0.1250 | too few blocks |
| `scale-count-10000.fresh.neo-freya.sender.cold` | xs | 4 | 0.507 [0.440, 0.584] | 0.507 | 0.1250 | too few blocks |
| `scale-count-10000.noop.freya-neo.sender.cold` | xs | 4 | 0.684 [0.624, 0.750] | 0.684 | 0.1250 | too few blocks |
| `scale-count-10000.noop.neo-freya.sender.cold` | xs | 4 | 0.665 [0.645, 0.686] | 0.663 | 0.1250 | too few blocks |
| `scale-count-100000.fresh.freya-neo.sender.cold` | xs | 4 | 0.745 [0.711, 0.780] | 0.747 | 0.1250 | too few blocks |
| `scale-count-100000.fresh.neo-freya.sender.cold` | xs | 4 | 0.369 [0.344, 0.395] | 0.369 | 0.1250 | too few blocks |
| `scale-count-100000.noop.freya-neo.sender.cold` | xs | 4 | 0.273 [0.242, 0.308] | 0.265 | 0.1250 | too few blocks |
| `scale-count-100000.noop.neo-freya.sender.cold` | xs | 4 | 0.287 [0.259, 0.318] | 0.287 | 0.1250 | too few blocks |
| `scale-count-1000000.fresh.freya-neo.sender.cold` | xs | 4 | 0.762 [0.752, 0.772] | 0.762 | 0.1250 | too few blocks |
| `scale-count-1000000.fresh.neo-freya.sender.cold` | xs | 4 | 0.345 [0.331, 0.359] | 0.341 | 0.1250 | too few blocks |
| `scale-count-1000000.noop.freya-neo.sender.cold` | xs | 4 | 0.167 [0.164, 0.171] | 0.167 | 0.1250 | too few blocks |
| `scale-count-1000000.noop.neo-freya.sender.cold` | xs | 4 | 0.202 [0.196, 0.208] | 0.201 | 0.1250 | too few blocks |
| `scale-count-3000.fresh.freya-neo.sender.cold` | xs | 4 | 0.913 [0.867, 0.961] | 0.904 | 0.1250 | too few blocks |
| `scale-count-3000.fresh.neo-freya.sender.cold` | xs | 4 | 0.708 [0.651, 0.770] | 0.713 | 0.1250 | too few blocks |
| `scale-count-3000.noop.freya-neo.sender.cold` | xs | 4 | 0.908 [0.863, 0.956] | 0.905 | 0.1250 | too few blocks |
| `scale-count-3000.noop.neo-freya.sender.cold` | xs | 4 | 0.834 [0.784, 0.887] | 0.828 | 0.1250 | too few blocks |
| `scale-count-30000.fresh.freya-neo.sender.cold` | xs | 4 | 0.783 [0.727, 0.844] | 0.794 | 0.1250 | too few blocks |
| `scale-count-30000.fresh.neo-freya.sender.cold` | xs | 4 | 0.409 [0.402, 0.416] | 0.409 | 0.1250 | too few blocks |
| `scale-count-30000.noop.freya-neo.sender.cold` | xs | 4 | 0.480 [0.425, 0.542] | 0.470 | 0.1250 | too few blocks |
| `scale-count-30000.noop.neo-freya.sender.cold` | xs | 4 | 0.487 [0.428, 0.555] | 0.487 | 0.1250 | too few blocks |
| `scale-count-300000.fresh.freya-neo.sender.cold` | xs | 4 | 0.729 [0.697, 0.764] | 0.729 | 0.1250 | too few blocks |
| `scale-count-300000.fresh.neo-freya.sender.cold` | xs | 4 | 0.346 [0.340, 0.352] | 0.347 | 0.1250 | too few blocks |
| `scale-count-300000.noop.freya-neo.sender.cold` | xs | 4 | 0.201 [0.190, 0.213] | 0.201 | 0.1250 | too few blocks |
| `scale-count-300000.noop.neo-freya.sender.cold` | xs | 4 | 0.228 [0.198, 0.262] | 0.228 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.cold` | xs | 1.374 [1.269, 1.489] | 1.557 [1.495, 1.622] | 0.871 [0.689, 1.099] |
| `scale-count-1000.fresh.neo-freya.sender.cold` | xs | 1.285 [1.218, 1.357] | 1.480 [1.408, 1.556] | 1.068 [1.040, 1.097] |
| `scale-count-1000.noop.freya-neo.sender.cold` | xs | 1.278 [1.241, 1.317] | 1.337 [1.292, 1.384] | 0.912 [0.848, 0.981] |
| `scale-count-1000.noop.neo-freya.sender.cold` | xs | 1.214 [1.188, 1.242] | 1.324 [1.246, 1.407] | 0.923 [0.886, 0.961] |
| `scale-count-10000.fresh.freya-neo.sender.cold` | xs | 1.336 [1.320, 1.353] | 2.845 [2.250, 3.596] | 0.515 [0.450, 0.589] |
| `scale-count-10000.fresh.neo-freya.sender.cold` | xs | 1.248 [1.194, 1.303] | 2.044 [1.875, 2.229] | 0.495 [0.452, 0.542] |
| `scale-count-10000.noop.freya-neo.sender.cold` | xs | 1.212 [1.175, 1.250] | 1.469 [1.267, 1.702] | 0.680 [0.625, 0.740] |
| `scale-count-10000.noop.neo-freya.sender.cold` | xs | 1.191 [1.176, 1.206] | 1.522 [1.415, 1.638] | 0.663 [0.643, 0.684] |
| `scale-count-100000.fresh.freya-neo.sender.cold` | xs | 1.366 [1.329, 1.405] | 10.079 [8.978, 11.315] | 0.739 [0.703, 0.776] |
| `scale-count-100000.fresh.neo-freya.sender.cold` | xs | 1.241 [1.184, 1.301] | 3.900 [3.542, 4.293] | 0.359 [0.346, 0.372] |
| `scale-count-100000.noop.freya-neo.sender.cold` | xs | 1.228 [1.208, 1.248] | 2.149 [2.060, 2.243] | 0.271 [0.240, 0.307] |
| `scale-count-100000.noop.neo-freya.sender.cold` | xs | 1.164 [1.142, 1.186] | 1.661 [1.572, 1.754] | 0.286 [0.258, 0.317] |
| `scale-count-1000000.fresh.freya-neo.sender.cold` | xs | 1.339 [1.319, 1.359] | 10.683 [10.331, 11.048] | 0.762 [0.752, 0.771] |
| `scale-count-1000000.fresh.neo-freya.sender.cold` | xs | 1.310 [1.250, 1.374] | 3.859 [2.802, 5.314] | 0.344 [0.331, 0.359] |
| `scale-count-1000000.noop.freya-neo.sender.cold` | xs | 1.223 [1.214, 1.232] | 2.289 [2.199, 2.382] | 0.167 [0.163, 0.171] |
| `scale-count-1000000.noop.neo-freya.sender.cold` | xs | 1.177 [1.163, 1.191] | 1.764 [1.655, 1.880] | 0.202 [0.196, 0.208] |
| `scale-count-3000.fresh.freya-neo.sender.cold` | xs | 1.383 [1.224, 1.562] | 2.009 [1.959, 2.060] | 0.909 [0.852, 0.969] |
| `scale-count-3000.fresh.neo-freya.sender.cold` | xs | 1.312 [1.267, 1.359] | 1.593 [1.508, 1.683] | 0.709 [0.683, 0.736] |
| `scale-count-3000.noop.freya-neo.sender.cold` | xs | 1.233 [1.190, 1.277] | 1.356 [1.303, 1.411] | 0.906 [0.857, 0.957] |
| `scale-count-3000.noop.neo-freya.sender.cold` | xs | 1.208 [1.174, 1.243] | 1.366 [1.279, 1.458] | 0.831 [0.783, 0.883] |
| `scale-count-30000.fresh.freya-neo.sender.cold` | xs | 1.382 [1.288, 1.484] | 6.508 [4.555, 9.300] | 0.757 [0.690, 0.830] |
| `scale-count-30000.fresh.neo-freya.sender.cold` | xs | 1.248 [1.217, 1.280] | 3.001 [2.753, 3.271] | 0.402 [0.395, 0.409] |
| `scale-count-30000.noop.freya-neo.sender.cold` | xs | 1.270 [1.202, 1.341] | 1.602 [1.526, 1.682] | 0.477 [0.425, 0.536] |
| `scale-count-30000.noop.neo-freya.sender.cold` | xs | 1.184 [1.130, 1.241] | 1.562 [1.527, 1.597] | 0.485 [0.426, 0.552] |
| `scale-count-300000.fresh.freya-neo.sender.cold` | xs | 1.346 [1.322, 1.370] | 10.298 [10.171, 10.427] | 0.726 [0.691, 0.763] |
| `scale-count-300000.fresh.neo-freya.sender.cold` | xs | 1.257 [1.245, 1.270] | 4.867 [3.992, 5.935] | 0.344 [0.338, 0.350] |
| `scale-count-300000.noop.freya-neo.sender.cold` | xs | 1.213 [1.200, 1.226] | 2.195 [2.105, 2.288] | 0.200 [0.189, 0.212] |
| `scale-count-300000.noop.neo-freya.sender.cold` | xs | 1.172 [1.164, 1.180] | 1.706 [1.601, 1.818] | 0.221 [0.192, 0.255] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.cold` | 0.342 | 0.303 |
| `scale-count-1000.fresh.neo-freya.sender.cold` | 0.234 | 0.263 |
| `scale-count-1000.noop.freya-neo.sender.cold` | 0.255 | 0.232 |
| `scale-count-1000.noop.neo-freya.sender.cold` | 0.199 | 0.184 |
| `scale-count-10000.fresh.freya-neo.sender.cold` | 1.659 | 0.931 |
| `scale-count-10000.fresh.neo-freya.sender.cold` | 1.252 | 0.634 |
| `scale-count-10000.noop.freya-neo.sender.cold` | 0.363 | 0.248 |
| `scale-count-10000.noop.neo-freya.sender.cold` | 0.303 | 0.201 |
| `scale-count-100000.fresh.freya-neo.sender.cold` | 7.365 | 5.486 |
| `scale-count-100000.fresh.neo-freya.sender.cold` | 9.599 | 3.539 |
| `scale-count-100000.noop.freya-neo.sender.cold` | 1.613 | 0.440 |
| `scale-count-100000.noop.neo-freya.sender.cold` | 1.464 | 0.420 |
| `scale-count-1000000.fresh.freya-neo.sender.cold` | 69.755 | 53.182 |
| `scale-count-1000000.fresh.neo-freya.sender.cold` | 96.359 | 33.233 |
| `scale-count-1000000.noop.freya-neo.sender.cold` | 14.287 | 2.390 |
| `scale-count-1000000.noop.neo-freya.sender.cold` | 13.950 | 2.817 |
| `scale-count-3000.fresh.freya-neo.sender.cold` | 0.486 | 0.444 |
| `scale-count-3000.fresh.neo-freya.sender.cold` | 0.475 | 0.336 |
| `scale-count-3000.noop.freya-neo.sender.cold` | 0.269 | 0.244 |
| `scale-count-3000.noop.neo-freya.sender.cold` | 0.219 | 0.183 |
| `scale-count-30000.fresh.freya-neo.sender.cold` | 2.517 | 1.971 |
| `scale-count-30000.fresh.neo-freya.sender.cold` | 3.051 | 1.249 |
| `scale-count-30000.noop.freya-neo.sender.cold` | 0.637 | 0.306 |
| `scale-count-30000.noop.neo-freya.sender.cold` | 0.538 | 0.262 |
| `scale-count-300000.fresh.freya-neo.sender.cold` | 21.699 | 15.828 |
| `scale-count-300000.fresh.neo-freya.sender.cold` | 28.626 | 9.903 |
| `scale-count-300000.noop.freya-neo.sender.cold` | 4.364 | 0.878 |
| `scale-count-300000.noop.neo-freya.sender.cold` | 4.069 | 0.927 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `scale-count-1000.fresh.freya-neo.sender.cold` | xs | 0.1392 | 176 | 235 |
| `scale-count-1000.fresh.neo-freya.sender.cold` | xs | 0.0920 | 78 | 104 |
| `scale-count-1000.noop.freya-neo.sender.cold` | xs | 0.0451 | 21 | 27 |
| `scale-count-1000.noop.neo-freya.sender.cold` | xs | 0.0250 | 8 | 10 |
| `scale-count-10000.fresh.freya-neo.sender.cold` | xs | 0.0694 | 46 | 60 |
| `scale-count-10000.fresh.neo-freya.sender.cold` | xs | 0.0888 | 73 | 97 |
| `scale-count-10000.noop.freya-neo.sender.cold` | xs | 0.0578 | 32 | 43 |
| `scale-count-10000.noop.neo-freya.sender.cold` | xs | 0.0195 | 8 | 8 |
| `scale-count-100000.fresh.freya-neo.sender.cold` | xs | 0.0293 | 10 | 13 |
| `scale-count-100000.fresh.neo-freya.sender.cold` | xs | 0.0435 | 19 | 25 |
| `scale-count-100000.noop.freya-neo.sender.cold` | xs | 0.0749 | 53 | 70 |
| `scale-count-100000.noop.neo-freya.sender.cold` | xs | 0.0640 | 39 | 52 |
| `scale-count-1000000.fresh.freya-neo.sender.cold` | xs | 0.0082 | 8 | 8 |
| `scale-count-1000000.fresh.neo-freya.sender.cold` | xs | 0.0257 | 8 | 10 |
| `scale-count-1000000.noop.freya-neo.sender.cold` | xs | 0.0143 | 8 | 8 |
| `scale-count-1000000.noop.neo-freya.sender.cold` | xs | 0.0180 | 8 | 8 |
| `scale-count-3000.fresh.freya-neo.sender.cold` | xs | 0.0324 | 12 | 15 |
| `scale-count-3000.fresh.neo-freya.sender.cold` | xs | 0.0528 | 28 | 36 |
| `scale-count-3000.noop.freya-neo.sender.cold` | xs | 0.0321 | 12 | 15 |
| `scale-count-3000.noop.neo-freya.sender.cold` | xs | 0.0389 | 16 | 21 |
| `scale-count-30000.fresh.freya-neo.sender.cold` | xs | 0.0469 | 22 | 29 |
| `scale-count-30000.fresh.neo-freya.sender.cold` | xs | 0.0109 | 8 | 8 |
| `scale-count-30000.noop.freya-neo.sender.cold` | xs | 0.0760 | 54 | 72 |
| `scale-count-30000.noop.neo-freya.sender.cold` | xs | 0.0820 | 63 | 83 |
| `scale-count-300000.fresh.freya-neo.sender.cold` | xs | 0.0288 | 10 | 12 |
| `scale-count-300000.fresh.neo-freya.sender.cold` | xs | 0.0107 | 8 | 8 |
| `scale-count-300000.noop.freya-neo.sender.cold` | xs | 0.0364 | 14 | 18 |
| `scale-count-300000.noop.neo-freya.sender.cold` | xs | 0.0870 | 70 | 93 |
