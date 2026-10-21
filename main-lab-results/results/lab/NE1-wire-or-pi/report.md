# NE1-wire-or-pi

xs fills the gigabit wire on large trees in both directions, and falls short only where the Pi's four-core sender is CPU-bound.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T153637Z-NE1-wire-or-pi.
- Valid blocks: 14. Voided block attempts: 30.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | rsync | 1 | 1.016 |  |  | too few blocks |
| `large-text.fresh.neo-freya.sender.warm` | rsync | 6 | 1.000 [0.999, 1.001] | 1.000 [0.999, 1.001] | 0.7812 | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 1 | 1.006 |  |  | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 6 | 0.957 [0.940, 0.974] | 0.955 [0.940, 0.981] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | rsync | 0.503 | 0.114 | 1.014 |
| `large-text.fresh.neo-freya.sender.warm` | rsync | 0.616 [0.594, 0.640] | 0.145 [0.143, 0.146] | 1.000 [0.999, 1.000] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.514 | 0.103 | 1.006 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.450 [0.430, 0.471] | 0.137 [0.135, 0.140] | 0.957 [0.940, 0.974] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `large-text.fresh.freya-neo.sender.warm` | 76.225 | 75.048 |
| `large-text.fresh.neo-freya.sender.warm` | 73.907 | 73.913 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.861 | 12.789 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.261 | 12.818 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.neo-freya.sender.warm` | rsync | 0.0006 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0169 | 8 | 8 |

## Voided attempts

- neo does not answer ping
