# J1c-neo-mars-jobs-mixed-bimodal

-j4 and -j8 differ from each other, and from the default, by more than 5% in time-to-durable on small-file and no-op copies between neo and mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261020T170934Z-J1c-neo-mars-jobs-mixed-bimodal.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j4 | 8 | 1.003 [0.990, 1.016] | 1.001 [0.990, 1.016] | 0.6953 | equivalent |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j8 | 8 | 1.006 [0.989, 1.023] | 1.005 [0.987, 1.025] | 0.4141 | equivalent |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 8 | 1.010 [0.996, 1.024] | 1.009 [0.995, 1.025] | 0.1328 | equivalent |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j4 | 8 | 0.999 [0.992, 1.005] | 0.999 [0.990, 1.006] | 0.6172 | equivalent |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j8 | 8 | 1.008 [0.998, 1.019] | 1.008 [0.998, 1.020] | 0.1172 | equivalent |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 8 | 0.980 [0.970, 0.989] | 0.980 [0.971, 0.990] | 0.0078 | equivalent |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j4 | 8 | 0.987 [0.982, 0.993] | 0.987 [0.982, 0.993] | 0.0078 | equivalent |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j8 | 8 | 0.999 [0.986, 1.012] | 0.999 [0.985, 1.013] | 0.8672 | equivalent |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 8 | 1.700 [1.675, 1.724] | 1.700 [1.672, 1.726] | 0.0078 | slower |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j4 | 8 | 1.006 [0.953, 1.062] | 1.004 [0.942, 1.061] | 0.8359 | inconclusive |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j8 | 8 | 0.986 [0.938, 1.036] | 0.999 [0.929, 1.029] | 0.6797 | inconclusive |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 8 | 1.222 [1.168, 1.278] | 1.235 [1.155, 1.272] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j4 | 0.879 [0.859, 0.900] | 1.234 [1.181, 1.290] | 1.000 [0.997, 1.002] |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j8 | 0.900 [0.884, 0.916] | 1.008 [0.982, 1.035] | 0.999 [0.997, 1.001] |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.723 [0.709, 0.737] | 0.047 [0.044, 0.051] | 1.003 [0.999, 1.006] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j4 | 1.012 [0.994, 1.031] | 1.000 [0.995, 1.005] | 0.999 [0.992, 1.005] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j8 | 1.029 [0.996, 1.063] | 1.084 [1.075, 1.092] | 1.008 [0.998, 1.019] |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 0.699 [0.681, 0.718] | 0.132 [0.126, 0.139] | 0.979 [0.970, 0.988] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j4 | 0.489 [0.467, 0.512] | 0.469 [0.463, 0.474] | 0.988 [0.981, 0.995] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j8 | 0.620 [0.588, 0.653] | 0.608 [0.596, 0.621] | 0.999 [0.986, 1.012] |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 0.549 [0.519, 0.581] | 0.469 [0.463, 0.474] | 1.708 [1.684, 1.733] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j4 | 0.964 [0.905, 1.027] | 1.000 [0.999, 1.000] | 0.986 [0.935, 1.040] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j8 | 1.130 [1.046, 1.222] | 1.126 [1.114, 1.137] | 0.989 [0.928, 1.054] |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 0.836 [0.779, 0.898] | 0.999 [0.999, 1.000] | 1.320 [1.253, 1.391] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-j4 | xs-j8 |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | 12.725 | 12.601 | 12.633 | 12.675 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | 12.360 | 12.617 | 12.600 | 12.721 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | 0.318 | 0.187 | 0.185 | 0.187 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | 0.312 | 0.256 | 0.257 | 0.252 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j4 | 0.0156 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | xs-j8 | 0.0199 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.receiver.warm` | rsync | 0.0162 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j4 | 0.0079 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | xs-j8 | 0.0125 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.sender.warm` | rsync | 0.0113 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j4 | 0.0070 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | xs-j8 | 0.0154 | 8 | 8 |
| `mixed-bimodal.noop.mars-neo.receiver.warm` | rsync | 0.0173 | 8 | 8 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j4 | 0.0652 | 41 | 54 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | xs-j8 | 0.0596 | 34 | 45 |
| `mixed-bimodal.noop.neo-mars.sender.warm` | rsync | 0.0542 | 29 | 38 |
