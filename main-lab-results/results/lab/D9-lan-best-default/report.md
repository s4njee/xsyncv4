# D9-lan-best-default

xs's best small-file setting is no slower than its default on mixed trees, either way.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T162644Z-D9-lan-best-default.
- Valid blocks: 27. Voided block attempts: 63.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-best | 1 | 0.993 |  |  | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 1 | 1.001 |  |  | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-best | 8 | 1.007 [0.995, 1.018] | 1.007 [0.996, 1.021] | 0.2109 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 8 | 0.961 [0.956, 0.967] | 0.962 [0.955, 0.967] | 0.0078 | faster |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs-best | 2 | 0.983 [0.689, 1.402] | 0.983 | 1.0000 | too few blocks |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 2 | 1.028 [1.012, 1.044] | 1.028 | 0.5000 | too few blocks |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-best | 8 | 1.000 [0.994, 1.006] | 0.999 [0.994, 1.008] | 0.9531 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 8 | 0.991 [0.986, 0.997] | 0.991 [0.986, 0.998] | 0.0156 | equivalent |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-best | 8 | 0.896 [0.850, 0.946] | 0.884 [0.853, 0.952] | 0.0156 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 8 | 2.144 [1.860, 2.471] | 2.133 [1.861, 2.496] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-best | 0.987 | 1.012 | 0.998 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.516 | 0.100 | 1.005 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-best | 1.026 [0.976, 1.078] | 1.001 [0.992, 1.011] | 1.007 [0.995, 1.019] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.477 [0.468, 0.487] | 0.140 [0.139, 0.141] | 0.962 [0.956, 0.967] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs-best | 1.009 [0.936, 1.088] | 1.003 [0.944, 1.066] | 1.003 [0.943, 1.067] |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 0.443 [0.387, 0.508] | 0.126 [0.123, 0.129] | 1.022 [0.928, 1.126] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-best | 0.987 [0.954, 1.020] | 1.002 [0.998, 1.006] | 1.000 [0.993, 1.007] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.528 [0.501, 0.557] | 0.142 [0.136, 0.150] | 0.992 [0.987, 0.997] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-best | 0.761 [0.730, 0.793] | 0.586 [0.341, 1.006] | 0.898 [0.851, 0.947] |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.696 [0.668, 0.726] | 0.193 [0.149, 0.250] | 2.180 [1.891, 2.513] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-best |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.813 | 12.803 | 12.714 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.241 | 12.734 | 12.820 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | 14.085 | 13.707 | 13.473 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.157 | 13.271 | 13.273 |
| `small-opaque.fresh.neo-freya.sender.warm` | 7.541 | 3.517 | 3.153 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-best | 0.0139 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0070 | 8 | 8 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | xs-best | 0.0395 | 17 | 21 |
| `mixed-threshold.fresh.freya-neo.sender.warm` | rsync | 0.0017 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | xs-best | 0.0073 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | rsync | 0.0062 | 8 | 8 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-best | 0.0644 | 40 | 52 |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.1697 | 261 | 349 |

## Voided attempts

- neo does not answer ping
