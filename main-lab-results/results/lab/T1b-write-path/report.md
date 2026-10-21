# T1b-write-path

A larger pipe, larger writes or one sending worker bring xs level with rsync on byte-bound copies from neo, at no cost from freya.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 2%. Interval level: 95.0%.
- Runs: 20261013T201554Z-T1b-write-path.
- Valid blocks: 40. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | pipe1m | 10 | 0.998 [0.995, 1.001] | 0.998 [0.995, 1.001] | 0.1777 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk256k | 10 | 0.995 [0.989, 1.002] | 0.997 [0.987, 1.000] | 0.0645 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk1m | 10 | 0.998 [0.993, 1.002] | 0.998 [0.993, 1.001] | 0.2637 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 10 | 1.001 [0.997, 1.004] | 1.000 [0.997, 1.005] | 0.6719 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 10 | 1.005 [0.990, 1.022] | 1.011 [0.981, 1.016] | 0.5137 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | pipe1m | 10 | 1.007 [0.991, 1.023] | 1.006 [0.989, 1.024] | 0.3457 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk256k | 10 | 1.000 [0.983, 1.016] | 1.000 [0.983, 1.018] | 0.9590 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk1m | 10 | 0.993 [0.978, 1.008] | 0.995 [0.978, 1.009] | 0.3047 | inconclusive |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 10 | 0.947 [0.934, 0.961] | 0.948 [0.936, 0.961] | 0.0020 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 10 | 0.951 [0.935, 0.967] | 0.952 [0.936, 0.969] | 0.0020 | faster |
| `mixed-threshold.fresh.freya-neo.sender.warm` | pipe1m | 10 | 0.998 [0.995, 1.001] | 0.999 [0.995, 1.001] | 0.2871 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk256k | 10 | 0.999 [0.995, 1.002] | 0.999 [0.995, 1.002] | 0.4355 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk1m | 10 | 1.002 [0.996, 1.009] | 1.002 [0.996, 1.009] | 0.4355 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | send1 | 10 | 1.002 [0.997, 1.007] | 1.001 [0.998, 1.007] | 0.3574 | equivalent |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 10 | 1.024 [1.014, 1.035] | 1.024 [1.013, 1.035] | 0.0020 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | pipe1m | 10 | 0.990 [0.980, 0.999] | 0.991 [0.979, 0.998] | 0.0176 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk256k | 10 | 0.994 [0.982, 1.006] | 0.993 [0.982, 1.006] | 0.3184 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk1m | 10 | 0.990 [0.982, 0.999] | 0.989 [0.981, 0.999] | 0.0449 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send1 | 10 | 0.944 [0.933, 0.956] | 0.943 [0.934, 0.955] | 0.0020 | faster |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 10 | 0.947 [0.935, 0.959] | 0.947 [0.935, 0.959] | 0.0020 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | pipe1m | 1.009 [0.985, 1.034] | 1.003 [1.000, 1.007] | 0.996 [0.987, 1.005] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk256k | 1.002 [0.972, 1.033] | 0.996 [0.987, 1.006] | 0.996 [0.985, 1.008] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk1m | 0.998 [0.973, 1.023] | 0.999 [0.994, 1.005] | 0.989 [0.981, 0.998] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.857 [0.841, 0.873] | 1.003 [0.999, 1.006] | 0.770 [0.762, 0.778] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.515 [0.502, 0.529] | 1.008 [0.997, 1.018] | 0.100 [0.097, 0.103] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | pipe1m | 1.025 [0.988, 1.063] | 1.007 [0.991, 1.023] | 1.002 [0.994, 1.011] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk256k | 1.023 [0.997, 1.050] | 1.000 [0.985, 1.017] | 1.002 [0.997, 1.008] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk1m | 1.010 [0.974, 1.048] | 0.994 [0.978, 1.010] | 1.003 [0.993, 1.012] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.673 [0.644, 0.704] | 0.947 [0.934, 0.962] | 0.944 [0.938, 0.950] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.441 [0.419, 0.464] | 0.951 [0.935, 0.968] | 0.125 [0.121, 0.129] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | pipe1m | 0.998 [0.972, 1.024] | 0.999 [0.992, 1.006] | 1.000 [0.995, 1.004] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk256k | 1.003 [0.984, 1.023] | 0.997 [0.988, 1.007] | 1.000 [0.995, 1.006] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk1m | 1.001 [0.984, 1.018] | 1.004 [0.997, 1.011] | 1.004 [0.999, 1.009] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | send1 | 0.817 [0.804, 0.831] | 0.998 [0.989, 1.007] | 0.793 [0.790, 0.796] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 0.418 [0.407, 0.429] | 1.026 [1.015, 1.037] | 0.124 [0.123, 0.126] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | pipe1m | 1.023 [1.011, 1.035] | 0.990 [0.980, 0.999] | 1.001 [0.997, 1.005] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk256k | 1.023 [0.998, 1.049] | 0.994 [0.982, 1.007] | 1.002 [0.999, 1.004] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk1m | 1.019 [1.001, 1.036] | 0.992 [0.983, 1.001] | 1.002 [0.998, 1.005] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send1 | 0.665 [0.642, 0.689] | 0.944 [0.933, 0.956] | 0.948 [0.946, 0.951] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.437 [0.416, 0.459] | 0.948 [0.937, 0.960] | 0.130 [0.127, 0.134] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | chunk1m | chunk256k | pipe1m | rsync | send1 | xs |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.322 | 12.293 | 12.326 | 12.419 | 12.360 | 12.351 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.828 | 12.917 | 13.011 | 12.288 | 12.242 | 12.922 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 13.101 | 13.051 | 13.050 | 13.387 | 13.101 | 13.071 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.781 | 13.834 | 13.772 | 13.180 | 13.141 | 13.916 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | pipe1m | 0.0045 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk256k | 0.0088 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | chunk1m | 0.0061 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | send1 | 0.0051 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0224 | 8 | 9 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | pipe1m | 0.0222 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk256k | 0.0229 | 8 | 9 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | chunk1m | 0.0216 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | send1 | 0.0206 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0242 | 8 | 10 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | pipe1m | 0.0042 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk256k | 0.0050 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | chunk1m | 0.0090 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | send1 | 0.0068 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 0.0145 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | pipe1m | 0.0131 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk256k | 0.0171 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | chunk1m | 0.0124 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | send1 | 0.0173 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.0173 | 8 | 8 |
