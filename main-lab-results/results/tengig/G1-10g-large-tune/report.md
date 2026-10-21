# G1-10g-large-tune

A larger stream count, block size, queue or worker count brings large files closer to 10 Gb/s.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T124214Z-G1-10g-large-tune.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | streams8 | 8 | 0.999 [0.984, 1.015] | 0.998 [0.983, 1.020] | 0.8672 | equivalent |
| `large-text.fresh.freya-mac.receiver.warm` | block4m | 8 | 1.012 [0.998, 1.027] | 1.018 [0.998, 1.025] | 0.1016 | equivalent |
| `large-text.fresh.freya-mac.receiver.warm` | queues | 8 | 1.017 [1.007, 1.027] | 1.018 [1.006, 1.028] | 0.0156 | equivalent |
| `large-text.fresh.freya-mac.receiver.warm` | jobs16 | 8 | 1.011 [0.989, 1.034] | 1.010 [0.986, 1.036] | 0.2812 | inconclusive |
| `large-text.fresh.freya-mac.receiver.warm` | all-four | 8 | 1.035 [1.013, 1.058] | 1.034 [1.011, 1.060] | 0.0156 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | streams8 | 8 | 1.040 [0.958, 1.128] | 1.009 [0.988, 1.153] | 0.3438 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | block4m | 8 | 1.016 [1.003, 1.030] | 1.014 [1.003, 1.033] | 0.0156 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | queues | 8 | 1.028 [0.997, 1.059] | 1.025 [0.999, 1.063] | 0.0547 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | jobs16 | 8 | 1.000 [0.975, 1.025] | 0.998 [0.972, 1.030] | 0.9766 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | all-four | 8 | 1.023 [1.008, 1.039] | 1.025 [1.006, 1.040] | 0.0234 | inconclusive |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | streams8 | 8 | 1.048 [1.009, 1.089] | 1.040 [1.011, 1.087] | 0.0156 | inconclusive |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | block4m | 8 | 1.021 [0.999, 1.043] | 1.017 [1.000, 1.047] | 0.0391 | inconclusive |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | queues | 8 | 1.034 [0.992, 1.079] | 1.028 [0.988, 1.089] | 0.1016 | inconclusive |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | jobs16 | 8 | 1.040 [1.017, 1.064] | 1.044 [1.010, 1.068] | 0.0156 | inconclusive |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-four | 8 | 1.056 [1.025, 1.089] | 1.055 [1.023, 1.094] | 0.0078 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | streams8 | 8 | 1.105 [0.958, 1.275] | 1.058 [0.999, 1.323] | 0.0625 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | block4m | 8 | 1.102 [0.890, 1.366] | 1.004 [0.926, 1.369] | 0.4688 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | queues | 8 | 1.070 [1.010, 1.134] | 1.055 [1.014, 1.139] | 0.0156 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | jobs16 | 8 | 1.204 [0.988, 1.466] | 1.106 [1.023, 1.440] | 0.0156 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-four | 8 | 1.186 [1.046, 1.345] | 1.117 [1.075, 1.310] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | streams8 | 0.997 [0.976, 1.020] | 1.049 [0.981, 1.122] | 0.998 [0.983, 1.014] |
| `large-text.fresh.freya-mac.receiver.warm` | block4m | 1.036 [1.025, 1.047] | 1.147 [1.051, 1.251] | 1.011 [0.995, 1.028] |
| `large-text.fresh.freya-mac.receiver.warm` | queues | 0.971 [0.957, 0.986] | 3.609 [3.333, 3.909] | 1.016 [1.007, 1.026] |
| `large-text.fresh.freya-mac.receiver.warm` | jobs16 | 1.005 [0.986, 1.024] | 1.039 [0.903, 1.195] | 1.011 [0.989, 1.033] |
| `large-text.fresh.freya-mac.receiver.warm` | all-four | 1.059 [1.038, 1.080] | 3.925 [3.625, 4.250] | 1.035 [1.013, 1.058] |
| `large-text.fresh.mac-freya.sender.warm` | streams8 | 0.996 [0.964, 1.029] | 1.004 [0.943, 1.069] | 1.037 [0.961, 1.118] |
| `large-text.fresh.mac-freya.sender.warm` | block4m | 0.947 [0.911, 0.986] | 0.989 [0.917, 1.066] | 1.016 [1.002, 1.030] |
| `large-text.fresh.mac-freya.sender.warm` | queues | 1.003 [0.976, 1.031] | 3.570 [3.305, 3.856] | 1.028 [0.998, 1.059] |
| `large-text.fresh.mac-freya.sender.warm` | jobs16 | 0.996 [0.961, 1.031] | 1.040 [0.990, 1.093] | 1.000 [0.976, 1.025] |
| `large-text.fresh.mac-freya.sender.warm` | all-four | 0.967 [0.933, 1.002] | 3.439 [3.190, 3.709] | 1.024 [1.008, 1.039] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | streams8 | 1.001 [0.972, 1.031] | 1.055 [0.982, 1.133] | 1.048 [1.008, 1.089] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | block4m | 0.985 [0.958, 1.014] | 1.666 [1.582, 1.755] | 1.016 [0.995, 1.038] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | queues | 1.003 [0.974, 1.034] | 3.884 [3.732, 4.042] | 1.032 [0.988, 1.077] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | jobs16 | 1.031 [1.017, 1.045] | 1.083 [1.004, 1.168] | 1.038 [1.011, 1.066] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-four | 1.095 [1.071, 1.119] | 4.715 [4.511, 4.929] | 1.054 [1.019, 1.090] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | streams8 | 1.011 [0.968, 1.056] | 1.001 [0.952, 1.053] | 1.078 [0.975, 1.192] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | block4m | 0.906 [0.860, 0.953] | 1.110 [1.061, 1.160] | 1.098 [0.893, 1.350] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | queues | 1.042 [0.970, 1.120] | 3.067 [2.947, 3.192] | 1.050 [1.018, 1.082] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | jobs16 | 1.119 [1.045, 1.197] | 1.117 [1.063, 1.174] | 1.200 [1.000, 1.441] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-four | 1.059 [1.014, 1.106] | 3.298 [3.171, 3.429] | 1.151 [1.048, 1.264] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | all-four | block4m | jobs16 | queues | streams8 | xs |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | 8.115 | 7.935 | 7.926 | 7.973 | 7.831 | 7.838 |
| `large-text.fresh.mac-freya.sender.warm` | 7.666 | 7.614 | 7.489 | 7.699 | 7.787 | 7.491 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | 3.930 | 3.797 | 3.869 | 3.848 | 3.899 | 3.720 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | 1.869 | 1.737 | 1.896 | 1.686 | 1.741 | 1.576 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | streams8 | 0.0189 | 8 | 8 |
| `large-text.fresh.freya-mac.receiver.warm` | block4m | 0.0177 | 8 | 8 |
| `large-text.fresh.freya-mac.receiver.warm` | queues | 0.0120 | 8 | 8 |
| `large-text.fresh.freya-mac.receiver.warm` | jobs16 | 0.0266 | 9 | 11 |
| `large-text.fresh.freya-mac.receiver.warm` | all-four | 0.0264 | 9 | 11 |
| `large-text.fresh.mac-freya.sender.warm` | streams8 | 0.0981 | 89 | 118 |
| `large-text.fresh.mac-freya.sender.warm` | block4m | 0.0164 | 8 | 8 |
| `large-text.fresh.mac-freya.sender.warm` | queues | 0.0359 | 14 | 18 |
| `large-text.fresh.mac-freya.sender.warm` | jobs16 | 0.0295 | 10 | 13 |
| `large-text.fresh.mac-freya.sender.warm` | all-four | 0.0179 | 8 | 8 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | streams8 | 0.0457 | 21 | 28 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | block4m | 0.0254 | 8 | 10 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | queues | 0.0503 | 25 | 33 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | jobs16 | 0.0272 | 9 | 11 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | all-four | 0.0364 | 14 | 18 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | streams8 | 0.1714 | 266 | 356 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | block4m | 0.2567 | 594 | 795 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | queues | 0.0692 | 45 | 60 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | jobs16 | 0.2358 | 501 | 671 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | all-four | 0.1503 | 205 | 274 |
