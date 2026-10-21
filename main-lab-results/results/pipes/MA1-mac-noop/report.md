# MA1-mac-noop

xs is slower than rsync on a warm no-op push from the Mac to mars.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T160919Z-MA1-mac-noop.
- Valid blocks: 1. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | xs | 1 | 0.144 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | xs | 0.953 | 0.795 | 0.144 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | 9.983 | 1.441 |

## Voided attempts

- rsync: harness error: mac: `rsync -aH -e 'ssh -oBatchMode=yes -oCompression=no -oControlMaster=no -oConnectTimeout=10 -oHostKeyAlias=[host]' [user]@10.25.0.
