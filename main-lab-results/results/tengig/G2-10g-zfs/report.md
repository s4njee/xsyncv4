# G2-10g-zfs

xs lands large files on the raidz2 pool at close to 10 Gb/s.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T133650Z-G2-10g-zfs.
- Valid blocks: 24. Voided block attempts: 48.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.mac-freya-zfs.sender.warm` | xs-best | 8 | 1.011 [0.946, 1.079] | 1.010 [0.941, 1.083] | 0.7109 | inconclusive |
| `large-text.fresh.mac-freya-zfs.sender.warm` | rsync | 8 | 1.950 [1.876, 2.027] | 1.937 [1.884, 2.044] | 0.0078 | slower |
| `large-text.fresh.mac-freya-zfs.sender.warm` | write1m | 8 | 0.978 [0.955, 1.001] | 0.978 [0.955, 1.008] | 0.0703 | inconclusive |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | xs-best | 8 | 0.946 [0.719, 1.246] | 0.980 [0.707, 1.242] | 0.6719 | inconclusive |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | rsync | 8 | 1.860 [1.313, 2.635] | 1.809 [1.278, 2.922] | 0.0078 | slower |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | write1m | 8 | 0.991 [0.774, 1.268] | 0.995 [0.740, 1.282] | 0.9609 | inconclusive |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | xs-best | 8 | 0.738 [0.664, 0.820] | 0.736 [0.665, 0.840] | 0.0078 | faster |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | rsync | 8 | 1.843 [1.284, 2.646] | 1.832 [1.279, 2.906] | 0.0078 | slower |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | write1m | 8 | 1.009 [0.933, 1.092] | 1.008 [0.923, 1.115] | 0.7891 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.992 [0.964, 1.020] | 1.036 [0.935, 1.147] | 1.007 [0.961, 1.055] |
| `large-text.fresh.mac-freya-zfs.sender.warm` | rsync | 1.535 [1.462, 1.613] | 0.085 [0.076, 0.095] | 2.117 [2.010, 2.231] |
| `large-text.fresh.mac-freya-zfs.sender.warm` | write1m | 0.990 [0.971, 1.009] | 1.018 [0.914, 1.135] | 0.993 [0.971, 1.016] |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.893 [0.844, 0.944] | 0.968 [0.939, 0.999] | 1.050 [0.951, 1.160] |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | rsync | 1.252 [1.048, 1.497] | 0.059 [0.056, 0.062] | 3.010 [2.207, 4.106] |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | write1m | 0.998 [0.963, 1.035] | 0.966 [0.905, 1.032] | 1.034 [0.913, 1.172] |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.932 [0.773, 1.123] | 0.495 [0.363, 0.675] | 0.625 [0.532, 0.734] |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | rsync | 0.789 [0.624, 0.998] | 0.076 [0.073, 0.079] | 1.993 [1.295, 3.066] |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | write1m | 1.093 [0.922, 1.295] | 0.972 [0.868, 1.089] | 0.995 [0.936, 1.058] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | write1m | xs | xs-best |
|---|---|---|---|---|
| `large-text.fresh.mac-freya-zfs.sender.warm` | 19.544 | 9.803 | 10.024 | 10.130 |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | 6.545 | 3.486 | 3.518 | 3.330 |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | 9.822 | 5.379 | 5.328 | 3.932 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.0789 | 58 | 77 |
| `large-text.fresh.mac-freya-zfs.sender.warm` | rsync | 0.0464 | 22 | 28 |
| `large-text.fresh.mac-freya-zfs.sender.warm` | write1m | 0.0281 | 10 | 12 |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.3289 | 973 | 1303 |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | rsync | 0.4164 | 1558 | 2088 |
| `mixed-bimodal.fresh.mac-freya-zfs.sender.warm` | write1m | 0.2953 | 785 | 1051 |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | xs-best | 0.1269 | 147 | 196 |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | rsync | 0.4325 | 1681 | 2252 |
| `small-flat.fresh.mac-freya-zfs.sender.warm` | write1m | 0.0943 | 82 | 109 |

## Voided attempts

- rsync: the destination does not match the corpus manifest: 
- write1m: the destination does not match the corpus manifest: 
- xs-best: the destination does not match the corpus manifest: 
- xs: the destination does not match the corpus manifest: 
