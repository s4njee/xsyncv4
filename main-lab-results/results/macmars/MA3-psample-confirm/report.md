# MA3-psample-confirm

xs is more than 5% faster than rsync on real-psample (from MA3-psample-bidir, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T045434Z-MA3-psample-confirm.
- Valid blocks: 24. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 12 | 0.257 [0.232, 0.284] | 0.248 [0.238, 0.263] | 0.0005 | 0.0010 | faster |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 12 | 0.658 [0.578, 0.749] | 0.695 [0.654, 0.713] | 0.0005 | 0.0010 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 1.090 [1.046, 1.135] | 0.271 [0.240, 0.305] | 3.571 [3.133, 4.071] |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 1.032 [0.940, 1.133] | 0.658 [0.578, 0.749] | 2.563 [2.491, 2.636] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | 228.0 | 58.595 |
| `real-psample.fresh.mars-mac.receiver.warm` | 405.1 | 266.6 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.fresh.mac-mars.sender.warm` | xs | 0.1597 | 231 | 309 |
| `real-psample.fresh.mars-mac.receiver.warm` | xs | 0.2034 | 374 | 500 |
