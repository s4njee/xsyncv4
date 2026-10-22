# OS1b-neo-mars-psample-noop

Onto macOS, e51c1df1329a's no-op is more than 10% faster than its parent's; onto Linux the two differ by less than 10%.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-parent`.
- Smallest effect of interest: 10%. Interval level: 95.0%.
- Runs: 20261020T055558Z-OS1b-neo-mars-psample-noop, 20261020T143456Z-OS1b-neo-mars-psample-noop, 20261020T170939Z-OS1b-neo-mars-psample-noop.
- Valid blocks: 11. Voided block attempts: 2.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.mars-neo.receiver.warm` | xs | 5 | 0.942 [0.895, 0.992] | 0.946 | 0.1250 | too few blocks |
| `real-psample.noop.mars-neo.receiver.warm` | rsync | 5 | 5.408 [5.042, 5.801] | 5.383 | 0.0625 | too few blocks |
| `real-psample.noop.neo-mars.sender.warm` | xs | 6 | 0.562 [0.489, 0.646] | 0.560 [0.478, 0.669] | 0.0312 | too few blocks |
| `real-psample.noop.neo-mars.sender.warm` | rsync | 6 | 1.364 [1.137, 1.636] | 1.382 [1.068, 1.645] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-psample.noop.mars-neo.receiver.warm` | xs | 0.941 [0.922, 0.961] | 1.006 [0.989, 1.024] | 0.942 [0.895, 0.992] |
| `real-psample.noop.mars-neo.receiver.warm` | rsync | 0.463 [0.440, 0.488] | 0.648 [0.642, 0.655] | 5.408 [5.042, 5.801] |
| `real-psample.noop.neo-mars.sender.warm` | xs | 0.578 [0.531, 0.630] | 0.893 [0.812, 0.983] | 0.561 [0.488, 0.645] |
| `real-psample.noop.neo-mars.sender.warm` | rsync | 0.259 [0.225, 0.299] | 0.212 [0.202, 0.222] | 1.366 [1.138, 1.639] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-parent |
|---|---|---|---|
| `real-psample.noop.mars-neo.receiver.warm` | 106.4 | 18.537 | 19.681 |
| `real-psample.noop.neo-mars.sender.warm` | 34.323 | 14.133 | 25.157 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.mars-neo.receiver.warm` | xs | 0.0414 | 18 | 23 |
| `real-psample.noop.mars-neo.receiver.warm` | rsync | 0.0565 | 31 | 41 |
| `real-psample.noop.neo-mars.sender.warm` | xs | 0.1329 | 161 | 215 |
| `real-psample.noop.neo-mars.sender.warm` | rsync | 0.1733 | 272 | 364 |

## Voided attempts

- rsync: harness error: neo: `rsync -aH -e 'ssh -oBatchMode=yes -oCompression=no -oControlMaster=no -oConnectTimeout=10 -oHostKeyAlias=[address]' [user]@192.16
- xs: harness error: mars: `python3 /Volumes/xsbench/lab/lib/736894f6f725/probe.py snapshot --interface en0` exited 255: ssh: connect to host [address] port 22
