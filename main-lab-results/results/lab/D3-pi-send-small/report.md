# D3-pi-send-small

Turning compression off, leaving ssh a core, or batching reads makes the Pi send small trees faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z-best`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T002741Z-D3-pi-send-small.
- Valid blocks: 8. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-freya.sender.warm` | xs-best | 2 | 1.237 [0.823, 1.858] | 1.237 | 0.5000 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | send3 | 2 | 1.204 [0.692, 2.094] | 1.204 | 0.5000 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | batch256 | 2 | 1.000 [0.659, 1.517] | 1.000 | 1.0000 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | coalesce1m | 2 | 1.013 [0.790, 1.300] | 1.013 | 1.0000 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | xs-best | 3 | 0.980 [0.932, 1.032] | 0.983 | 0.2500 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | send3 | 3 | 1.053 [1.007, 1.101] | 1.053 | 0.2500 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 3 | 1.009 [0.938, 1.086] | 1.009 | 0.7500 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | coalesce1m | 3 | 1.009 [0.942, 1.080] | 1.006 | 1.0000 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | xs-best | 3 | 1.004 [0.897, 1.123] | 1.009 | 1.0000 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 3 | 1.203 [1.115, 1.299] | 1.199 | 0.2500 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 3 | 0.976 [0.910, 1.047] | 0.979 | 0.2500 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | coalesce1m | 3 | 0.995 [0.944, 1.049] | 0.993 | 0.7500 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.neo-freya.sender.warm` | xs-best | 1.212 [1.038, 1.416] | 2.260 [2.227, 2.294] | 1.241 [0.829, 1.858] |
| `real-congress.fresh.neo-freya.sender.warm` | send3 | 0.973 [0.685, 1.381] | 0.997 [0.766, 1.297] | 1.207 [0.688, 2.118] |
| `real-congress.fresh.neo-freya.sender.warm` | batch256 | 1.002 [0.748, 1.343] | 1.063 [0.908, 1.245] | 1.004 [0.682, 1.477] |
| `real-congress.fresh.neo-freya.sender.warm` | coalesce1m | 1.016 [0.986, 1.047] | 1.033 [0.804, 1.327] | 1.016 [0.805, 1.284] |
| `small-deep.fresh.neo-freya.sender.warm` | xs-best | 0.974 [0.923, 1.027] | 0.989 [0.728, 1.344] | 0.976 [0.922, 1.032] |
| `small-deep.fresh.neo-freya.sender.warm` | send3 | 0.992 [0.980, 1.005] | 1.011 [0.989, 1.034] | 1.057 [1.009, 1.107] |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 1.027 [0.985, 1.071] | 0.986 [0.826, 1.176] | 1.015 [0.938, 1.099] |
| `small-deep.fresh.neo-freya.sender.warm` | coalesce1m | 1.016 [0.914, 1.129] | 1.005 [0.861, 1.172] | 1.014 [0.933, 1.103] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-best | 0.926 [0.915, 0.937] | 2.761 [2.020, 3.776] | 1.013 [0.969, 1.058] |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 0.919 [0.887, 0.952] | 0.731 [0.664, 0.804] | 1.207 [1.149, 1.269] |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 0.982 [0.946, 1.019] | 1.006 [0.783, 1.292] | 0.987 [0.970, 1.006] |
| `small-flat.fresh.neo-freya.sender.warm` | coalesce1m | 0.991 [0.921, 1.067] | 0.991 [0.933, 1.052] | 0.998 [0.929, 1.072] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | batch256 | coalesce1m | send3 | xs-best | xs-z-best |
|---|---|---|---|---|---|
| `real-congress.fresh.neo-freya.sender.warm` | 9.127 | 9.249 | 10.986 | 11.289 | 9.127 |
| `small-deep.fresh.neo-freya.sender.warm` | 6.864 | 6.864 | 7.163 | 6.669 | 6.802 |
| `small-flat.fresh.neo-freya.sender.warm` | 2.916 | 2.972 | 3.596 | 2.999 | 2.988 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-freya.sender.warm` | xs-best | 0.0453 | 21 | 27 |
| `real-congress.fresh.neo-freya.sender.warm` | send3 | 0.0616 | 37 | 48 |
| `real-congress.fresh.neo-freya.sender.warm` | batch256 | 0.0464 | 22 | 28 |
| `real-congress.fresh.neo-freya.sender.warm` | coalesce1m | 0.0277 | 9 | 12 |
| `small-deep.fresh.neo-freya.sender.warm` | xs-best | 0.0204 | 8 | 8 |
| `small-deep.fresh.neo-freya.sender.warm` | send3 | 0.0178 | 8 | 8 |
| `small-deep.fresh.neo-freya.sender.warm` | batch256 | 0.0295 | 10 | 13 |
| `small-deep.fresh.neo-freya.sender.warm` | coalesce1m | 0.0275 | 9 | 12 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-best | 0.0451 | 21 | 27 |
| `small-flat.fresh.neo-freya.sender.warm` | send3 | 0.0308 | 11 | 14 |
| `small-flat.fresh.neo-freya.sender.warm` | batch256 | 0.0282 | 10 | 12 |
| `small-flat.fresh.neo-freya.sender.warm` | coalesce1m | 0.0212 | 8 | 8 |

## Voided attempts

- stopped
