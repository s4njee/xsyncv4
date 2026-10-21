# H6-pair-best-default

xs's best small-file setting is no slower than its default on mixed and large trees, either way.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T121639Z-H6-pair-best-default.
- Valid blocks: 48. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-best | 8 | 1.002 [0.998, 1.005] | 1.002 [0.998, 1.005] | 0.2578 | equivalent |
| `large-text.fresh.mars-neo.sender.warm` | rsync | 8 | 1.010 [1.005, 1.014] | 1.009 [1.005, 1.014] | 0.0078 | equivalent |
| `large-text.fresh.neo-mars.receiver.warm` | xs-best | 8 | 1.002 [0.995, 1.010] | 1.000 [0.998, 1.012] | 0.7031 | equivalent |
| `large-text.fresh.neo-mars.receiver.warm` | rsync | 8 | 0.997 [0.995, 0.998] | 0.997 [0.995, 0.998] | 0.0078 | equivalent |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-best | 8 | 1.002 [0.994, 1.010] | 1.002 [0.993, 1.011] | 0.4922 | equivalent |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync | 8 | 1.003 [1.000, 1.006] | 1.003 [0.999, 1.006] | 0.0781 | equivalent |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-best | 8 | 1.005 [0.997, 1.012] | 1.005 [0.996, 1.013] | 0.2031 | equivalent |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync | 8 | 0.974 [0.967, 0.981] | 0.974 [0.967, 0.983] | 0.0078 | inconclusive |
| `mixed-threshold.fresh.mars-neo.sender.warm` | xs-best | 8 | 0.998 [0.989, 1.007] | 0.998 [0.989, 1.010] | 0.6328 | equivalent |
| `mixed-threshold.fresh.mars-neo.sender.warm` | rsync | 8 | 0.991 [0.980, 1.002] | 0.994 [0.980, 1.000] | 0.0703 | equivalent |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | xs-best | 8 | 1.003 [0.999, 1.007] | 1.003 [0.998, 1.008] | 0.0859 | equivalent |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | rsync | 8 | 0.979 [0.973, 0.985] | 0.979 [0.973, 0.986] | 0.0078 | equivalent |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-best | 0.994 [0.980, 1.008] | 1.000 [0.998, 1.001] | 1.001 [0.999, 1.004] |
| `large-text.fresh.mars-neo.sender.warm` | rsync | 0.545 [0.537, 0.553] | 0.148 [0.146, 0.149] | 1.006 [1.002, 1.010] |
| `large-text.fresh.neo-mars.receiver.warm` | xs-best | 0.994 [0.969, 1.020] | 0.999 [0.998, 1.000] | 1.000 [0.998, 1.001] |
| `large-text.fresh.neo-mars.receiver.warm` | rsync | 0.567 [0.554, 0.580] | 0.163 [0.161, 0.165] | 0.997 [0.995, 0.998] |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-best | 0.976 [0.955, 0.997] | 0.993 [0.983, 1.003] | 1.001 [0.996, 1.005] |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync | 0.565 [0.551, 0.581] | 0.130 [0.126, 0.133] | 1.003 [0.999, 1.007] |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-best | 0.972 [0.961, 0.983] | 1.004 [0.996, 1.012] | 1.005 [0.997, 1.013] |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync | 0.454 [0.435, 0.475] | 0.156 [0.154, 0.159] | 0.974 [0.967, 0.981] |
| `mixed-threshold.fresh.mars-neo.sender.warm` | xs-best | 0.988 [0.968, 1.008] | 0.997 [0.993, 1.001] | 0.998 [0.988, 1.008] |
| `mixed-threshold.fresh.mars-neo.sender.warm` | rsync | 0.518 [0.509, 0.528] | 0.137 [0.135, 0.139] | 1.010 [1.000, 1.020] |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | xs-best | 1.007 [0.999, 1.014] | 1.001 [0.996, 1.005] | 1.003 [0.999, 1.007] |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | rsync | 0.446 [0.428, 0.465] | 0.163 [0.161, 0.164] | 0.979 [0.974, 0.985] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-best |
|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | 74.847 | 74.135 | 74.249 |
| `large-text.fresh.neo-mars.receiver.warm` | 73.844 | 74.083 | 74.258 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | 12.828 | 12.790 | 12.821 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | 12.221 | 12.546 | 12.604 |
| `mixed-threshold.fresh.mars-neo.sender.warm` | 13.709 | 13.830 | 13.804 |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | 13.118 | 13.395 | 13.440 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mars-neo.sender.warm` | xs-best | 0.0037 | 8 | 8 |
| `large-text.fresh.mars-neo.sender.warm` | rsync | 0.0051 | 8 | 8 |
| `large-text.fresh.neo-mars.receiver.warm` | xs-best | 0.0085 | 8 | 8 |
| `large-text.fresh.neo-mars.receiver.warm` | rsync | 0.0020 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | xs-best | 0.0095 | 8 | 8 |
| `mixed-bimodal.fresh.mars-neo.sender.warm` | rsync | 0.0040 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | xs-best | 0.0092 | 8 | 8 |
| `mixed-bimodal.fresh.neo-mars.receiver.warm` | rsync | 0.0085 | 8 | 8 |
| `mixed-threshold.fresh.mars-neo.sender.warm` | xs-best | 0.0110 | 8 | 8 |
| `mixed-threshold.fresh.mars-neo.sender.warm` | rsync | 0.0131 | 8 | 8 |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | xs-best | 0.0046 | 8 | 8 |
| `mixed-threshold.fresh.neo-mars.receiver.warm` | rsync | 0.0071 | 8 | 8 |

## Voided attempts

- xs: the transfer exited 12:  file changed during transfer after retry: "~/benchmarks/xsyncv4/lab/corpora/mixed-bimodal/d06/d04/f0000486.xml"
    read
