# MA3-psample-bidir

On the Mac/mars 10GbE link, xs copies the psample tree faster than rsync -a fresh, in both directions, and xs -z helps only where the data compresses.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261017T165019Z-MA3-psample-bidir, 20261017T185527Z-MA3-psample-bidir.
- Valid blocks: 11. Voided block attempts: 6.
- **The runs were made from different versions of the spec.**
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | rsync-z | 6 | 1.094 [1.078, 1.110] | 1.092 [1.077, 1.122] | 0.0312 | too few blocks |
| `real-psample.fresh.mac-mars.sender.warm` | xs | 6 | 0.335 [0.257, 0.437] | 0.336 [0.239, 0.450] | 0.0312 | too few blocks |
| `real-psample.fresh.mac-mars.sender.warm` | xs-z | 6 | 0.298 [0.221, 0.402] | 0.289 [0.226, 0.483] | 0.0312 | too few blocks |
| `real-psample.fresh.mars-mac.receiver.warm` | rsync-z | 5 | 1.036 [1.010, 1.063] | 1.031 | 0.0625 | too few blocks |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 5 | 0.714 [0.682, 0.748] | 0.713 | 0.0625 | too few blocks |
| `real-psample.fresh.mars-mac.receiver.warm` | xs-z | 5 | 0.769 [0.582, 1.016] | 0.709 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | rsync-z | 1.054 [1.040, 1.068] | 1.094 [1.079, 1.110] | 0.968 [0.815, 1.150] |
| `real-psample.fresh.mac-mars.sender.warm` | xs | 1.103 [1.065, 1.142] | 0.336 [0.257, 0.437] | 4.375 [3.611, 5.300] |
| `real-psample.fresh.mac-mars.sender.warm` | xs-z | 1.107 [1.059, 1.158] | 0.299 [0.221, 0.404] | 8.552 [4.871, 15.014] |
| `real-psample.fresh.mars-mac.receiver.warm` | rsync-z | 0.920 [0.914, 0.927] | 1.036 [1.009, 1.063] | 1.002 [0.929, 1.081] |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 1.109 [1.059, 1.161] | 0.714 [0.681, 0.748] | 2.426 [2.373, 2.480] |
| `real-psample.fresh.mars-mac.receiver.warm` | xs-z | 1.142 [1.087, 1.199] | 0.769 [0.582, 1.016] | 2.385 [2.304, 2.468] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | 224.0 | 245.1 | 75.053 | 66.729 |
| `real-psample.fresh.mars-mac.receiver.warm` | 370.1 | 383.4 | 264.3 | 284.7 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | rsync-z | 0.0137 | 8 | 8 |
| `real-psample.fresh.mac-mars.sender.warm` | xs | 0.2537 | 580 | 776 |
| `real-psample.fresh.mac-mars.sender.warm` | xs-z | 0.2859 | 736 | 985 |
| `real-psample.fresh.mars-mac.receiver.warm` | rsync-z | 0.0207 | 8 | 8 |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 0.0373 | 15 | 19 |
| `real-psample.fresh.mars-mac.receiver.warm` | xs-z | 0.2241 | 453 | 606 |

## Voided attempts

- rsync: harness error: Command '['ssh', '-oBatchMode=yes', '-oConnectTimeout=10', '[email]', "sh -c 'find ~/benchmarks/xsyncv4/lab/corpora/r
- rsync: the destination does not match the corpus manifest: DIFFERS github/acritty/target/debug/incremental/alacritty-0apbfib5r6rer/s-hnarn3fo0v-1bemmqn-embc6e4s
- rsync: the transfer exited 20: 
- xs-z: the destination does not match the corpus manifest: DIFFERS github/acritty/target/debug/incremental/alacritty-0apbfib5r6rer/s-hnarn3fo0v-1bemmqn-embc6e4sc
