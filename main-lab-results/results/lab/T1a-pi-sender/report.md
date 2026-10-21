# T1a-pi-sender

Fewer xs worker threads, or a cheaper SSH cipher, close the gap to rsync when neo sends a mixed tree.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 2%. Interval level: 95.0%.
- Runs: 20261012T124301Z-T1a-pi-sender.
- Valid blocks: 24. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 12 | 0.977 [0.974, 0.980] | 0.977 [0.974, 0.981] | 0.0005 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 12 | 0.980 [0.975, 0.984] | 0.980 [0.974, 0.985] | 0.0005 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 12 | 0.992 [0.988, 0.996] | 0.991 [0.988, 0.996] | 0.0024 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 12 | 0.977 [0.974, 0.981] | 0.977 [0.974, 0.981] | 0.0005 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 12 | 1.020 [0.917, 1.135] | 0.974 [0.969, 0.979] | 1.0000 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 12 | 0.983 [0.978, 0.988] | 0.983 [0.977, 0.989] | 0.0005 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 12 | 0.984 [0.978, 0.989] | 0.983 [0.978, 0.989] | 0.0005 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 12 | 0.989 [0.983, 0.996] | 0.989 [0.982, 0.996] | 0.0044 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 12 | 0.986 [0.981, 0.991] | 0.985 [0.981, 0.991] | 0.0005 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 12 | 0.981 [0.976, 0.986] | 0.981 [0.976, 0.986] | 0.0005 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 0.721 [0.710, 0.732] | 0.998 [0.951, 1.048] | 0.941 [0.937, 0.946] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 0.888 [0.877, 0.898] | 0.980 [0.975, 0.985] | 0.957 [0.953, 0.961] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 0.854 [0.845, 0.864] | 0.992 [0.988, 0.996] | 0.998 [0.993, 1.002] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.482 [0.475, 0.488] | 0.977 [0.974, 0.981] | 0.124 [0.121, 0.126] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 0.325 [0.317, 0.333] | 1.032 [0.905, 1.177] | 0.120 [0.118, 0.121] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 0.772 [0.757, 0.787] | 0.983 [0.978, 0.989] | 0.944 [0.942, 0.946] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 0.893 [0.873, 0.912] | 0.983 [0.978, 0.989] | 0.961 [0.959, 0.963] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 0.817 [0.789, 0.847] | 0.989 [0.983, 0.996] | 0.999 [0.996, 1.001] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.503 [0.493, 0.514] | 0.986 [0.981, 0.991] | 0.129 [0.127, 0.131] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 0.318 [0.311, 0.326] | 0.981 [0.976, 0.986] | 0.124 [0.121, 0.127] |

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
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j1 | 0.0053 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-j2 | 0.0080 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-aes | 0.0064 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0055 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-aes | 0.1680 | 256 | 342 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j1 | 0.0083 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-j2 | 0.0083 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-aes | 0.0101 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.0077 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync-aes | 0.0079 | 8 | 8 |
