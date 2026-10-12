# T1a-pi-sender

Fewer xs worker threads, or a cheaper SSH cipher, close the gap to rsync when neo sends a mixed tree.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 2%. Interval level: 95.0%.
- Runs: 20261012T124301Z-T1a-pi-sender.
- Valid blocks: 24. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 12 | 1.023 [1.020, 1.027] | 1.023 [1.019, 1.027] | 0.0005 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 12 | 0.999 [0.997, 1.002] | 0.999 [0.998, 1.001] | 0.6094 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 12 | 1.002 [1.000, 1.005] | 1.002 [0.999, 1.005] | 0.0913 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 12 | 1.015 [1.010, 1.019] | 1.014 [1.011, 1.019] | 0.0005 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 12 | 1.044 [0.938, 1.162] | 0.995 [0.993, 0.996] | 1.0000 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 12 | 1.014 [1.009, 1.019] | 1.015 [1.009, 1.020] | 0.0005 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 12 | 0.997 [0.996, 0.998] | 0.997 [0.996, 0.998] | 0.0005 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 12 | 0.998 [0.996, 1.000] | 0.998 [0.996, 0.999] | 0.0264 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 12 | 1.004 [0.999, 1.008] | 1.003 [0.999, 1.009] | 0.1235 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 12 | 0.995 [0.994, 0.997] | 0.995 [0.993, 0.997] | 0.0010 | equivalent |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 2.076 [2.048, 2.103] | 1.023 [1.020, 1.027] | 8.068 [7.906, 8.234] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 1.497 [1.469, 1.525] | 1.022 [0.973, 1.073] | 7.594 [7.452, 7.739] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 1.842 [1.816, 1.869] | 1.003 [1.000, 1.005] | 7.722 [7.558, 7.890] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 1.773 [1.751, 1.796] | 1.015 [1.011, 1.020] | 8.050 [7.893, 8.211] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 0.675 [0.659, 0.692] | 1.056 [0.926, 1.205] | 0.967 [0.945, 0.990] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 1.987 [1.945, 2.029] | 1.014 [1.009, 1.020] | 7.757 [7.626, 7.889] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 1.533 [1.508, 1.558] | 0.997 [0.996, 0.998] | 7.325 [7.205, 7.447] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 1.773 [1.744, 1.803] | 0.997 [0.995, 1.000] | 7.457 [7.334, 7.581] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 1.624 [1.583, 1.665] | 1.004 [0.999, 1.008] | 7.745 [7.619, 7.873] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 0.632 [0.623, 0.642] | 0.995 [0.993, 0.997] | 0.959 [0.930, 0.990] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-aes | xs | xs-aes | xs-j1 | xs-j2 |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.245 | 12.784 | 12.528 | 12.424 | 12.238 | 12.271 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.161 | 13.099 | 13.350 | 13.208 | 13.124 | 13.131 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs | 0.0055 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 0.0032 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 0.0040 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 0.0064 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 0.1688 | 258 | 345 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs | 0.0077 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 0.0018 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 0.0031 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 0.0074 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 0.0028 | 8 | 8 |
