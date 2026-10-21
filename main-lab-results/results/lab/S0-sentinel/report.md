# S0-sentinel

Hour by hour, the A/A ratio stays within 3% of 1 and the xs to rsync ratio stays where the baseline put it.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020701Z-S0-sentinel-s0001, 20261014T020707Z-S0-sentinel-s0002, 20261014T020709Z-S0-sentinel-s0003.
- Valid blocks: 72. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 9 | 0.998 [0.992, 1.003] | 0.998 [0.992, 1.003] | 0.3828 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 9 | 1.006 [1.001, 1.011] | 1.006 [1.000, 1.011] | 0.0391 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 9 | 1.000 [0.983, 1.017] | 1.003 [0.979, 1.017] | 0.9922 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 9 | 0.964 [0.949, 0.980] | 0.965 [0.943, 0.980] | 0.0039 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 9 | 1.017 [0.964, 1.073] | 1.019 [0.965, 1.075] | 0.5039 | inconclusive |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 9 | 1.610 [1.521, 1.705] | 1.603 [1.528, 1.716] | 0.0039 | slower |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 9 | 1.019 [0.988, 1.051] | 1.024 [0.986, 1.051] | 0.2070 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 9 | 1.526 [1.494, 1.558] | 1.522 [1.499, 1.561] | 0.0039 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | again | 9 | 1.002 [0.994, 1.011] | 1.001 [0.993, 1.012] | 0.5898 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 9 | 1.043 [0.995, 1.094] | 1.035 [0.994, 1.106] | 0.0586 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | again | 9 | 0.992 [0.966, 1.019] | 0.994 [0.962, 1.026] | 0.5000 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 9 | 1.241 [1.026, 1.503] | 1.231 [1.052, 1.528] | 0.0039 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | again | 9 | 0.991 [0.936, 1.050] | 0.995 [0.918, 1.056] | 0.7148 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 9 | 2.327 [2.207, 2.452] | 2.322 [2.192, 2.460] | 0.0039 | slower |
| `small-flat.noop.neo-freya.sender.warm` | again | 9 | 0.968 [0.877, 1.067] | 0.999 [0.858, 1.058] | 0.5469 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 9 | 2.370 [2.045, 2.747] | 2.361 [2.020, 2.846] | 0.0039 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 0.989 [0.978, 1.000] | 0.993 [0.980, 1.006] | 0.996 [0.988, 1.005] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.502 [0.492, 0.513] | 1.004 [0.993, 1.016] | 0.099 [0.096, 0.101] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 0.992 [0.933, 1.055] | 0.999 [0.982, 1.016] | 1.004 [0.994, 1.015] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.468 [0.447, 0.489] | 0.964 [0.948, 0.979] | 0.122 [0.119, 0.125] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 0.998 [0.954, 1.044] | 1.017 [0.968, 1.068] | 1.005 [0.986, 1.024] |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.551 [0.527, 0.576] | 1.589 [1.508, 1.674] | 0.685 [0.656, 0.715] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 1.011 [0.935, 1.093] | 1.019 [0.988, 1.051] | 0.997 [0.990, 1.004] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.568 [0.530, 0.609] | 1.521 [1.490, 1.553] | 0.717 [0.697, 0.738] |
| `small-flat.fresh.freya-neo.sender.warm` | again | 1.009 [1.001, 1.018] | 1.009 [0.997, 1.020] | 0.999 [0.982, 1.016] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.682 [0.656, 0.710] | 1.040 [0.995, 1.087] | 0.100 [0.099, 0.102] |
| `small-flat.fresh.neo-freya.sender.warm` | again | 0.996 [0.957, 1.038] | 0.998 [0.971, 1.025] | 1.061 [0.897, 1.254] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.667 [0.650, 0.685] | 1.228 [1.018, 1.481] | 0.134 [0.110, 0.164] |
| `small-flat.noop.freya-neo.sender.warm` | again | 0.996 [0.939, 1.056] | 0.991 [0.934, 1.050] | 0.995 [0.981, 1.010] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.789 [0.744, 0.836] | 2.288 [2.169, 2.413] | 0.469 [0.458, 0.480] |
| `small-flat.noop.neo-freya.sender.warm` | again | 0.959 [0.844, 1.089] | 0.982 [0.914, 1.055] | 0.991 [0.976, 1.006] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.745 [0.611, 0.908] | 2.362 [2.038, 2.737] | 0.577 [0.562, 0.592] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | again | rsync | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.173 | 12.270 | 12.200 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.692 | 12.237 | 12.693 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | 0.236 | 0.374 | 0.232 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.188 | 0.281 | 0.184 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.459 | 6.722 | 6.443 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.379 | 4.229 | 3.406 |
| `small-flat.noop.freya-neo.sender.warm` | 0.307 | 0.721 | 0.310 |
| `small-flat.noop.neo-freya.sender.warm` | 0.269 | 0.659 | 0.278 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | again | 0.0070 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0066 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | again | 0.0227 | 8 | 9 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0208 | 8 | 8 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | again | 0.0699 | 46 | 61 |
| `mixed-bimodal.noop.freya-neo.sender.warm` | rsync | 0.0743 | 52 | 69 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | again | 0.0403 | 17 | 22 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | rsync | 0.0272 | 9 | 11 |
| `small-flat.fresh.freya-neo.sender.warm` | again | 0.0112 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0617 | 37 | 48 |
| `small-flat.fresh.neo-freya.sender.warm` | again | 0.0348 | 13 | 17 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.2483 | 556 | 744 |
| `small-flat.noop.freya-neo.sender.warm` | again | 0.0751 | 53 | 70 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.0684 | 45 | 59 |
| `small-flat.noop.neo-freya.sender.warm` | again | 0.1275 | 148 | 198 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1919 | 333 | 445 |
