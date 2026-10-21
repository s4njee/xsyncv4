# C1-congress

On a real tree of small JSON and XML files, xs is faster than rsync, and -z helps neither on a gigabit link.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T162233Z-C1-congress.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | rsync-z | 8 | 0.927 [0.901, 0.953] | 0.927 [0.901, 0.960] | 0.0078 | faster |
| `real-congress.fresh.freya-neo.sender.warm` | xs | 8 | 0.844 [0.806, 0.884] | 0.846 [0.800, 0.890] | 0.0078 | faster |
| `real-congress.fresh.freya-neo.sender.warm` | xs-z | 8 | 0.771 [0.727, 0.817] | 0.771 [0.724, 0.830] | 0.0078 | faster |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 8 | 1.116 [1.081, 1.151] | 1.116 [1.081, 1.154] | 0.0078 | slower |
| `real-congress.fresh.neo-freya.sender.warm` | xs | 8 | 0.472 [0.450, 0.495] | 0.469 [0.448, 0.495] | 0.0078 | faster |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z | 8 | 0.336 [0.318, 0.355] | 0.338 [0.316, 0.353] | 0.0078 | faster |
| `real-congress.noop.freya-neo.sender.warm` | rsync-z | 8 | 0.977 [0.936, 1.020] | 0.984 [0.931, 1.018] | 0.2969 | inconclusive |
| `real-congress.noop.freya-neo.sender.warm` | xs | 8 | 0.191 [0.172, 0.212] | 0.185 [0.177, 0.217] | 0.0078 | faster |
| `real-congress.noop.freya-neo.sender.warm` | xs-z | 8 | 0.196 [0.183, 0.210] | 0.195 [0.182, 0.213] | 0.0078 | faster |
| `real-congress.noop.neo-freya.sender.warm` | rsync-z | 8 | 0.970 [0.928, 1.013] | 0.971 [0.919, 1.015] | 0.1562 | inconclusive |
| `real-congress.noop.neo-freya.sender.warm` | xs | 8 | 0.433 [0.369, 0.509] | 0.426 [0.365, 0.523] | 0.0078 | faster |
| `real-congress.noop.neo-freya.sender.warm` | xs-z | 8 | 0.447 [0.400, 0.499] | 0.433 [0.414, 0.516] | 0.0078 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | rsync-z | 0.886 [0.866, 0.907] | 1.004 [1.003, 1.006] | 0.925 [0.902, 0.948] |
| `real-congress.fresh.freya-neo.sender.warm` | xs | 1.457 [1.420, 1.495] | 0.745 [0.720, 0.772] | 0.838 [0.796, 0.882] |
| `real-congress.fresh.freya-neo.sender.warm` | xs-z | 1.366 [1.332, 1.401] | 0.738 [0.496, 1.099] | 0.765 [0.720, 0.813] |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 0.993 [0.985, 1.001] | 1.167 [1.139, 1.195] | 1.116 [1.081, 1.151] |
| `real-congress.fresh.neo-freya.sender.warm` | xs | 1.805 [1.757, 1.855] | 7.930 [7.584, 8.290] | 0.469 [0.446, 0.492] |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z | 1.455 [1.430, 1.480] | 3.644 [3.437, 3.863] | 0.332 [0.314, 0.351] |
| `real-congress.noop.freya-neo.sender.warm` | rsync-z | 0.976 [0.937, 1.017] | 0.998 [0.994, 1.001] | 0.977 [0.936, 1.020] |
| `real-congress.noop.freya-neo.sender.warm` | xs | 1.822 [1.720, 1.931] | 0.514 [0.496, 0.534] | 0.190 [0.171, 0.211] |
| `real-congress.noop.freya-neo.sender.warm` | xs-z | 1.780 [1.673, 1.894] | 0.533 [0.519, 0.547] | 0.195 [0.182, 0.209] |
| `real-congress.noop.neo-freya.sender.warm` | rsync-z | 0.957 [0.924, 0.991] | 1.004 [0.975, 1.034] | 0.970 [0.928, 1.013] |
| `real-congress.noop.neo-freya.sender.warm` | xs | 4.996 [4.810, 5.188] | 3.000 [2.944, 3.058] | 0.433 [0.368, 0.509] |
| `real-congress.noop.neo-freya.sender.warm` | xs-z | 5.184 [4.963, 5.415] | 3.172 [3.082, 3.264] | 0.447 [0.400, 0.499] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | 19.455 | 18.034 | 16.413 | 14.997 |
| `real-congress.fresh.neo-freya.sender.warm` | 24.409 | 27.229 | 11.519 | 8.210 |
| `real-congress.noop.freya-neo.sender.warm` | 6.417 | 6.270 | 1.225 | 1.260 |
| `real-congress.noop.neo-freya.sender.warm` | 2.517 | 2.440 | 1.090 | 1.125 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | rsync-z | 0.0336 | 13 | 16 |
| `real-congress.fresh.freya-neo.sender.warm` | xs | 0.0553 | 30 | 39 |
| `real-congress.fresh.freya-neo.sender.warm` | xs-z | 0.0700 | 46 | 61 |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 0.0372 | 15 | 19 |
| `real-congress.fresh.neo-freya.sender.warm` | xs | 0.0569 | 32 | 41 |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z | 0.0657 | 41 | 54 |
| `real-congress.noop.freya-neo.sender.warm` | rsync-z | 0.0514 | 26 | 34 |
| `real-congress.noop.freya-neo.sender.warm` | xs | 0.1250 | 143 | 190 |
| `real-congress.noop.freya-neo.sender.warm` | xs-z | 0.0815 | 62 | 82 |
| `real-congress.noop.neo-freya.sender.warm` | rsync-z | 0.0523 | 27 | 35 |
| `real-congress.noop.neo-freya.sender.warm` | xs | 0.1932 | 337 | 451 |
| `real-congress.noop.neo-freya.sender.warm` | xs-z | 0.1326 | 160 | 214 |
