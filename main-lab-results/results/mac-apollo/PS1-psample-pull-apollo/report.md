# PS1-psample-pull-apollo

Pulling psample onto the Mac, some xs setting is at least 5% faster than xs's default, and xs is at least as fast as rsync.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-cpp`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T103613Z-PS1-psample-pull-apollo.
- Valid blocks: 1. Voided block attempts: 6.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1 | 0.589 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 1 | 0.880 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-O | 1 | 0.632 |  |  | too few blocks |
| `real-psample.noop.apollo-mac.receiver.warm` | rsync | 1 | 1.056 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-j8 | 1.007 | 1.116 | 0.588 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-noatomic | 0.641 | 1.113 | 0.878 |
| `real-psample.noop.apollo-mac.receiver.warm` | xs-cpp-O | 0.635 | 1.107 | 0.631 |
| `real-psample.noop.apollo-mac.receiver.warm` | rsync | 0.281 | 0.220 | 1.056 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-cpp-O | xs-cpp-j8 | xs-cpp-noatomic |
|---|---|---|---|---|---|
| `real-psample.noop.apollo-mac.receiver.warm` | 33.755 | 31.961 | 20.191 | 18.836 | 28.118 |

## Voided attempts

- xs-cpp-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover
DIFFERS .xsyncv4-carryover/corpora
DIFFERS .xsyncv4-carryover/mac-root

- xs-cpp-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs/20261016T113325Z-R4-direct-send-replicate
DIFFERS audio/p
- xs-cpp-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/2e
DIFFERS blackbird/.git/objects/41
DIFFERS blackbird/.git/objects
- xs-cpp-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/50
DIFFERS blackbird/.git/objects/86
DIFFERS blackbird/.git/objects
