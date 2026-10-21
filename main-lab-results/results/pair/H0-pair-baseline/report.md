# H0-pair-baseline

xs with its best small-file setting is faster than rsync -az both ways on every tree.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T021151Z-H0-pair-baseline.
- Valid blocks: 80. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-z-best | 8 | 0.977 [0.905, 1.054] | 0.992 [0.903, 1.050] | 0.5078 | inconclusive |
| `large-text.fresh.mars-neo.sender.warm` | rsync-z | 8 | 0.945 [0.871, 1.025] | 0.958 [0.860, 1.019] | 0.1094 | inconclusive |
| `large-text.fresh.neo-mars.receiver.warm` | xs-z-best | 8 | 1.033 [1.002, 1.065] | 1.029 [1.000, 1.063] | 0.0391 | inconclusive |
| `large-text.fresh.neo-mars.receiver.warm` | rsync-z | 8 | 3.568 [3.434, 3.708] | 3.560 [3.435, 3.711] | 0.0078 | slower |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-z-best | 8 | 0.999 [0.993, 1.005] | 1.000 [0.991, 1.006] | 0.8125 | equivalent |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync-z | 8 | 0.932 [0.926, 0.937] | 0.932 [0.925, 0.937] | 0.0078 | faster |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-z-best | 8 | 0.989 [0.939, 1.040] | 1.006 [0.924, 1.021] | 0.9297 | inconclusive |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync-z | 8 | 1.534 [1.453, 1.619] | 1.541 [1.444, 1.613] | 0.0078 | slower |
| `real-congress.fresh.mars-neo.sender.warm` | xs-z-best | 8 | 0.863 [0.797, 0.935] | 0.876 [0.785, 0.924] | 0.0078 | faster |
| `real-congress.fresh.mars-neo.sender.warm` | rsync-z | 8 | 1.326 [1.240, 1.418] | 1.348 [1.235, 1.414] | 0.0078 | slower |
| `real-congress.fresh.neo-mars.receiver.warm` | xs-z-best | 8 | 1.002 [0.942, 1.066] | 1.014 [0.923, 1.050] | 0.9453 | inconclusive |
| `real-congress.fresh.neo-mars.receiver.warm` | rsync-z | 8 | 3.334 [3.154, 3.524] | 3.332 [3.119, 3.560] | 0.0078 | slower |
| `small-deep.fresh.mars-neo.sender.warm` | xs-z-best | 8 | 0.959 [0.923, 0.996] | 0.948 [0.931, 1.002] | 0.0391 | inconclusive |
| `small-deep.fresh.mars-neo.sender.warm` | rsync-z | 8 | 1.147 [1.115, 1.179] | 1.149 [1.107, 1.178] | 0.0078 | slower |
| `small-deep.fresh.neo-mars.receiver.warm` | xs-z-best | 8 | 1.043 [0.966, 1.126] | 1.043 [0.961, 1.139] | 0.2266 | inconclusive |
| `small-deep.fresh.neo-mars.receiver.warm` | rsync-z | 8 | 2.200 [2.033, 2.382] | 2.203 [2.011, 2.397] | 0.0078 | slower |
| `small-flat.fresh.mars-neo.sender.warm` | xs-z-best | 8 | 0.692 [0.679, 0.706] | 0.694 [0.677, 0.708] | 0.0078 | faster |
| `small-flat.fresh.mars-neo.sender.warm` | rsync-z | 8 | 1.131 [1.087, 1.178] | 1.126 [1.086, 1.179] | 0.0078 | slower |
| `small-flat.fresh.neo-mars.receiver.warm` | xs-z-best | 8 | 0.662 [0.552, 0.795] | 0.646 [0.546, 0.840] | 0.0078 | faster |
| `small-flat.fresh.neo-mars.receiver.warm` | rsync-z | 8 | 2.362 [1.813, 3.077] | 2.435 [1.726, 3.052] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-z-best | 0.992 [0.965, 1.020] | 1.005 [0.993, 1.016] | 0.982 [0.912, 1.058] |
| `large-text.fresh.mars-neo.sender.warm` | rsync-z | 1.153 [1.095, 1.214] | 0.058 [0.058, 0.059] | 0.939 [0.863, 1.022] |
| `large-text.fresh.neo-mars.receiver.warm` | xs-z-best | 1.027 [0.988, 1.067] | 0.888 [0.652, 1.210] | 1.033 [1.002, 1.065] |
| `large-text.fresh.neo-mars.receiver.warm` | rsync-z | 1.194 [1.150, 1.239] | 0.351 [0.260, 0.473] | 3.570 [3.435, 3.710] |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-z-best | 0.977 [0.963, 0.992] | 0.996 [0.958, 1.037] | 0.997 [0.993, 1.002] |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync-z | 0.867 [0.848, 0.886] | 0.085 [0.083, 0.087] | 0.929 [0.925, 0.932] |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-z-best | 0.943 [0.819, 1.086] | 0.990 [0.952, 1.028] | 0.988 [0.939, 1.039] |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync-z | 0.936 [0.821, 1.067] | 0.103 [0.102, 0.105] | 1.535 [1.454, 1.620] |
| `real-congress.fresh.mars-neo.sender.warm` | xs-z-best | 0.923 [0.891, 0.957] | 1.595 [1.113, 2.287] | 0.861 [0.793, 0.936] |
| `real-congress.fresh.mars-neo.sender.warm` | rsync-z | 0.690 [0.664, 0.716] | 2.243 [2.179, 2.308] | 1.335 [1.247, 1.429] |
| `real-congress.fresh.neo-mars.receiver.warm` | xs-z-best | 0.817 [0.788, 0.846] | 0.987 [0.924, 1.054] | 0.999 [0.939, 1.063] |
| `real-congress.fresh.neo-mars.receiver.warm` | rsync-z | 0.754 [0.741, 0.767] | 0.404 [0.382, 0.427] | 3.376 [3.186, 3.578] |
| `small-deep.fresh.mars-neo.sender.warm` | xs-z-best | 0.968 [0.944, 0.993] | 1.004 [0.983, 1.025] | 0.955 [0.914, 0.997] |
| `small-deep.fresh.mars-neo.sender.warm` | rsync-z | 0.896 [0.879, 0.912] | 1.766 [1.747, 1.785] | 1.155 [1.124, 1.187] |
| `small-deep.fresh.neo-mars.receiver.warm` | xs-z-best | 0.729 [0.697, 0.762] | 0.932 [0.824, 1.054] | 1.056 [0.971, 1.149] |
| `small-deep.fresh.neo-mars.receiver.warm` | rsync-z | 0.685 [0.653, 0.720] | 0.224 [0.201, 0.250] | 2.253 [2.084, 2.436] |
| `small-flat.fresh.mars-neo.sender.warm` | xs-z-best | 0.812 [0.803, 0.821] | 1.042 [0.966, 1.123] | 0.672 [0.663, 0.682] |
| `small-flat.fresh.mars-neo.sender.warm` | rsync-z | 0.818 [0.793, 0.843] | 0.087 [0.078, 0.097] | 1.144 [1.100, 1.191] |
| `small-flat.fresh.neo-mars.receiver.warm` | xs-z-best | 0.680 [0.591, 0.782] | 0.325 [0.259, 0.409] | 0.654 [0.541, 0.791] |
| `small-flat.fresh.neo-mars.receiver.warm` | rsync-z | 1.002 [0.860, 1.168] | 0.213 [0.153, 0.296] | 2.389 [1.828, 3.121] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-z | xs-z | xs-z-best |
|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | 28.051 | 29.691 | 29.007 |
| `large-text.fresh.neo-mars.receiver.warm` | 105.8 | 29.641 | 30.621 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | 9.259 | 9.939 | 9.932 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | 14.830 | 9.670 | 9.561 |
| `real-congress.fresh.mars-neo.sender.warm` | 16.560 | 12.492 | 10.785 |
| `real-congress.fresh.neo-mars.receiver.warm` | 28.307 | 8.490 | 8.510 |
| `small-deep.fresh.mars-neo.sender.warm` | 15.825 | 13.803 | 13.238 |
| `small-deep.fresh.neo-mars.receiver.warm` | 11.352 | 5.159 | 5.380 |
| `small-flat.fresh.mars-neo.sender.warm` | 5.926 | 5.238 | 3.627 |
| `small-flat.fresh.neo-mars.receiver.warm` | 8.738 | 3.700 | 2.450 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-z-best | 0.0910 | 77 | 102 |
| `large-text.fresh.mars-neo.sender.warm` | rsync-z | 0.0970 | 87 | 116 |
| `large-text.fresh.neo-mars.receiver.warm` | xs-z-best | 0.0362 | 14 | 18 |
| `large-text.fresh.neo-mars.receiver.warm` | rsync-z | 0.0459 | 21 | 28 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-z-best | 0.0073 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync-z | 0.0074 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-z-best | 0.0611 | 36 | 47 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync-z | 0.0645 | 40 | 52 |
| `real-congress.fresh.mars-neo.sender.warm` | xs-z-best | 0.0957 | 85 | 113 |
| `real-congress.fresh.mars-neo.sender.warm` | rsync-z | 0.0803 | 60 | 80 |
| `real-congress.fresh.neo-mars.receiver.warm` | xs-z-best | 0.0736 | 51 | 68 |
| `real-congress.fresh.neo-mars.receiver.warm` | rsync-z | 0.0663 | 42 | 55 |
| `small-deep.fresh.mars-neo.sender.warm` | xs-z-best | 0.0457 | 21 | 28 |
| `small-deep.fresh.mars-neo.sender.warm` | rsync-z | 0.0331 | 12 | 16 |
| `small-deep.fresh.neo-mars.receiver.warm` | xs-z-best | 0.0918 | 78 | 104 |
| `small-deep.fresh.neo-mars.receiver.warm` | rsync-z | 0.0948 | 83 | 110 |
| `small-flat.fresh.mars-neo.sender.warm` | xs-z-best | 0.0228 | 8 | 9 |
| `small-flat.fresh.mars-neo.sender.warm` | rsync-z | 0.0481 | 23 | 30 |
| `small-flat.fresh.neo-mars.receiver.warm` | xs-z-best | 0.2181 | 429 | 575 |
| `small-flat.fresh.neo-mars.receiver.warm` | rsync-z | 0.3163 | 900 | 1205 |
