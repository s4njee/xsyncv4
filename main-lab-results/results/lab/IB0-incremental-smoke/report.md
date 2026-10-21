# IB0-incremental-smoke

The fastest incremental backup policy depends on the changed-file fraction, corpus, and direction.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T230619Z-IB0-incremental-smoke.
- Valid blocks: 2. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `tiny-one.update-1pct.freya-neo.sender.warm` | rsync-z | 1 | 1.101 |  |  | too few blocks |
| `tiny-one.update-1pct.freya-neo.sender.warm` | xs-z-whole | 1 | 1.048 |  |  | too few blocks |
| `tiny-one.update-1pct.neo-freya.sender.warm` | rsync-z | 1 | 1.144 |  |  | too few blocks |
| `tiny-one.update-1pct.neo-freya.sender.warm` | xs-z-whole | 1 | 0.987 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `tiny-one.update-1pct.freya-neo.sender.warm` | rsync-z | 0.649 | 0.678 | 1.099 |
| `tiny-one.update-1pct.freya-neo.sender.warm` | xs-z-whole | 0.975 | 0.975 | 1.048 |
| `tiny-one.update-1pct.neo-freya.sender.warm` | rsync-z | 0.706 | 0.643 | 1.173 |
| `tiny-one.update-1pct.neo-freya.sender.warm` | xs-z-whole | 0.947 | 1.000 | 0.983 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-z | xs-z | xs-z-whole |
|---|---|---|---|
| `tiny-one.update-1pct.freya-neo.sender.warm` | 0.209 | 0.189 | 0.198 |
| `tiny-one.update-1pct.neo-freya.sender.warm` | 0.200 | 0.175 | 0.172 |
