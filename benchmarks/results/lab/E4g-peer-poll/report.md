# E4g-peer-poll

Polling for the peer's exit every 5 or 1 ms instead of 25 shortens a no-op by more than 3% on a one-file tree, and measurably on 100,000 files.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T205439Z-E4g-peer-poll.
- Valid blocks: 160. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.noop.freya-neo.sender.warm` | poll5 | 40 | 0.975 [0.958, 0.991] | 0.978 [0.962, 0.991] | 0.0020 | inconclusive |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 40 | 0.948 [0.933, 0.964] | 0.948 [0.933, 0.965] | 0.0000 | faster |
| `small-flat.noop.neo-freya.sender.warm` | poll5 | 40 | 0.962 [0.947, 0.976] | 0.955 [0.948, 0.963] | 0.0000 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 40 | 0.941 [0.929, 0.952] | 0.942 [0.930, 0.952] | 0.0000 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | poll5 | 40 | 0.969 [0.953, 0.985] | 0.971 [0.955, 0.987] | 0.0004 | inconclusive |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 40 | 0.962 [0.948, 0.977] | 0.960 [0.947, 0.973] | 0.0000 | inconclusive |
| `tiny-one.noop.neo-freya.sender.warm` | poll5 | 40 | 0.903 [0.890, 0.916] | 0.900 [0.891, 0.912] | 0.0000 | faster |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 40 | 0.875 [0.863, 0.887] | 0.875 [0.863, 0.888] | 0.0000 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-flat.noop.freya-neo.sender.warm` | poll5 | 0.982 [0.960, 1.005] | 0.975 [0.959, 0.991] | 1.000 [0.993, 1.006] |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 0.968 [0.948, 0.989] | 0.949 [0.933, 0.965] | 0.999 [0.992, 1.007] |
| `small-flat.noop.neo-freya.sender.warm` | poll5 | 1.015 [0.997, 1.034] | 0.959 [0.939, 0.980] | 1.000 [0.994, 1.007] |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 1.006 [0.992, 1.022] | 0.935 [0.918, 0.953] | 1.001 [0.993, 1.009] |
| `tiny-one.noop.freya-neo.sender.warm` | poll5 | 1.006 [0.982, 1.030] | 0.970 [0.954, 0.986] | 1.005 [0.993, 1.018] |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 1.003 [0.980, 1.027] | 0.963 [0.949, 0.977] | 1.000 [0.986, 1.014] |
| `tiny-one.noop.neo-freya.sender.warm` | poll5 | 1.003 [0.988, 1.019] | 0.904 [0.892, 0.917] | 0.997 [0.990, 1.004] |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 1.004 [0.991, 1.018] | 0.878 [0.866, 0.890] | 1.000 [0.995, 1.005] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | poll1 | poll5 | xs |
|---|---|---|---|
| `small-flat.noop.freya-neo.sender.warm` | 0.283 | 0.291 | 0.298 |
| `small-flat.noop.neo-freya.sender.warm` | 0.234 | 0.239 | 0.249 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.193 | 0.195 | 0.201 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.140 | 0.144 | 0.160 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.noop.freya-neo.sender.warm` | poll5 | 0.0521 | 27 | 35 |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 0.0525 | 27 | 36 |
| `small-flat.noop.neo-freya.sender.warm` | poll5 | 0.0469 | 22 | 29 |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 0.0387 | 16 | 20 |
| `tiny-one.noop.freya-neo.sender.warm` | poll5 | 0.0522 | 27 | 35 |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 0.0463 | 22 | 28 |
| `tiny-one.noop.neo-freya.sender.warm` | poll5 | 0.0449 | 21 | 27 |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 0.0429 | 19 | 25 |
