# E1r-laikav2-linked

Once xs -aH sends linked data once, it is within a few percent of rsync -aH on the real 42 GiB tree.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261013T143717Z-E1r-laikav2-linked.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 4 | 0.970 [0.953, 0.988] | 0.970 | 0.1250 | too few blocks |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 4 | 1.006 [1.003, 1.009] | 1.006 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 2.317 [2.235, 2.403] | 1.065 [1.046, 1.085] | 0.970 [0.953, 0.987] |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 1.844 [1.794, 1.894] | 8.136 [7.583, 8.730] | 1.006 [1.003, 1.009] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | 327.4 | 317.7 |
| `real-laikav2.fresh.neo-freya.sender.warm` | 315.7 | 317.5 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-laikav2.fresh.freya-neo.sender.warm` | xs | 0.0114 | 8 | 8 |
| `real-laikav2.fresh.neo-freya.sender.warm` | xs | 0.0018 | 8 | 8 |
