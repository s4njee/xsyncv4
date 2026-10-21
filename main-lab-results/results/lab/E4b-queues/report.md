# E4b-queues

Neither queue is a bottleneck at its default: a quarter or four times its size changes no copy by more than 3%.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T220731Z-E4b-queues.
- Valid blocks: 40. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq4m | 10 | 1.000 [0.997, 1.003] | 1.001 [0.996, 1.002] | 0.9883 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq64m | 10 | 0.999 [0.997, 1.001] | 1.000 [0.996, 1.001] | 0.3027 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq12m | 10 | 0.999 [0.997, 1.001] | 0.999 [0.997, 1.001] | 0.3281 | equivalent |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq192m | 10 | 0.998 [0.993, 1.003] | 1.000 [0.990, 1.001] | 0.4629 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq4m | 10 | 1.004 [0.997, 1.012] | 1.004 [0.997, 1.013] | 0.2363 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq64m | 10 | 0.998 [0.990, 1.005] | 0.997 [0.990, 1.006] | 0.5098 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq12m | 10 | 0.980 [0.972, 0.989] | 0.981 [0.971, 0.991] | 0.0020 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq192m | 10 | 1.010 [0.995, 1.024] | 1.008 [0.995, 1.024] | 0.1543 | equivalent |
| `small-real.fresh.freya-neo.sender.warm` | recvq4m | 10 | 1.053 [0.989, 1.121] | 1.052 [0.989, 1.119] | 0.0957 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | recvq64m | 10 | 0.953 [0.901, 1.008] | 0.952 [0.896, 1.015] | 0.0859 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | sendq12m | 10 | 0.958 [0.906, 1.012] | 0.965 [0.904, 1.028] | 0.1074 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | sendq192m | 10 | 0.985 [0.935, 1.038] | 0.982 [0.933, 1.038] | 0.5176 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recvq4m | 10 | 0.987 [0.959, 1.017] | 1.003 [0.952, 1.010] | 0.4844 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recvq64m | 10 | 1.036 [0.927, 1.158] | 1.000 [0.951, 1.222] | 0.7832 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | sendq12m | 10 | 1.084 [0.957, 1.229] | 1.058 [0.965, 1.270] | 0.1836 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | sendq192m | 10 | 1.040 [0.952, 1.136] | 1.008 [0.965, 1.149] | 0.3945 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq4m | 1.007 [0.987, 1.028] | 1.002 [1.000, 1.005] | 1.007 [1.001, 1.013] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq64m | 0.994 [0.976, 1.013] | 1.000 [0.997, 1.003] | 1.003 [0.996, 1.010] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq12m | 0.954 [0.938, 0.970] | 0.996 [0.986, 1.006] | 0.468 [0.463, 0.474] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq192m | 0.973 [0.951, 0.996] | 1.001 [0.995, 1.006] | 3.148 [3.136, 3.159] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq4m | 1.039 [0.997, 1.083] | 1.001 [0.990, 1.012] | 0.996 [0.987, 1.005] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq64m | 1.007 [0.978, 1.037] | 0.994 [0.984, 1.004] | 0.997 [0.990, 1.004] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq12m | 0.983 [0.939, 1.028] | 0.978 [0.969, 0.987] | 0.350 [0.344, 0.357] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq192m | 0.985 [0.940, 1.033] | 1.006 [0.996, 1.018] | 3.537 [3.512, 3.564] |
| `small-real.fresh.freya-neo.sender.warm` | recvq4m | 0.973 [0.928, 1.019] | 1.054 [0.992, 1.119] | 1.016 [1.000, 1.033] |
| `small-real.fresh.freya-neo.sender.warm` | recvq64m | 0.987 [0.951, 1.024] | 0.955 [0.905, 1.008] | 0.992 [0.973, 1.012] |
| `small-real.fresh.freya-neo.sender.warm` | sendq12m | 0.957 [0.913, 1.002] | 0.959 [0.911, 1.009] | 0.640 [0.635, 0.645] |
| `small-real.fresh.freya-neo.sender.warm` | sendq192m | 1.004 [0.964, 1.045] | 0.991 [0.944, 1.041] | 2.402 [2.335, 2.471] |
| `small-real.fresh.neo-freya.sender.warm` | recvq4m | 0.986 [0.952, 1.022] | 0.986 [0.957, 1.016] | 1.009 [0.968, 1.051] |
| `small-real.fresh.neo-freya.sender.warm` | recvq64m | 0.974 [0.949, 1.001] | 1.038 [0.933, 1.154] | 0.986 [0.940, 1.034] |
| `small-real.fresh.neo-freya.sender.warm` | sendq12m | 0.957 [0.923, 0.992] | 1.084 [0.958, 1.227] | 0.616 [0.590, 0.643] |
| `small-real.fresh.neo-freya.sender.warm` | sendq192m | 0.961 [0.934, 0.989] | 1.041 [0.952, 1.138] | 2.458 [2.356, 2.564] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | recvq4m | recvq64m | sendq12m | sendq192m | xs |
|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.283 | 12.270 | 12.270 | 12.255 | 12.283 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.499 | 12.415 | 12.201 | 12.564 | 12.444 |
| `small-real.fresh.freya-neo.sender.warm` | 14.035 | 12.697 | 12.766 | 13.132 | 13.328 |
| `small-real.fresh.neo-freya.sender.warm` | 10.995 | 11.533 | 12.074 | 11.580 | 11.136 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq4m | 0.0041 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | recvq64m | 0.0029 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq12m | 0.0030 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | sendq192m | 0.0072 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq4m | 0.0108 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recvq64m | 0.0109 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq12m | 0.0125 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | sendq192m | 0.0197 | 8 | 8 |
| `small-real.fresh.freya-neo.sender.warm` | recvq4m | 0.0878 | 72 | 95 |
| `small-real.fresh.freya-neo.sender.warm` | recvq64m | 0.0783 | 58 | 76 |
| `small-real.fresh.freya-neo.sender.warm` | sendq12m | 0.0776 | 57 | 75 |
| `small-real.fresh.freya-neo.sender.warm` | sendq192m | 0.0725 | 50 | 66 |
| `small-real.fresh.neo-freya.sender.warm` | recvq4m | 0.0414 | 18 | 23 |
| `small-real.fresh.neo-freya.sender.warm` | recvq64m | 0.1556 | 220 | 294 |
| `small-real.fresh.neo-freya.sender.warm` | sendq12m | 0.1751 | 278 | 371 |
| `small-real.fresh.neo-freya.sender.warm` | sendq192m | 0.1235 | 139 | 186 |
