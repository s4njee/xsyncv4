# MA6-mac-mars-shapes-confirm

xs is more than 5% faster than rsync on large-text, real-congress (from MA6-mac-mars-shapes, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T135930Z-MA6-mac-mars-shapes-confirm.
- Valid blocks: 48. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 12 | 0.393 [0.358, 0.431] | 0.406 [0.379, 0.421] | 0.0005 | 0.0020 | faster |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 12 | 0.314 [0.258, 0.382] | 0.341 [0.256, 0.370] | 0.0005 | 0.0020 | faster |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 12 | 0.244 [0.231, 0.258] | 0.243 [0.229, 0.261] | 0.0005 | 0.0020 | faster |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 12 | 0.599 [0.505, 0.711] | 0.578 [0.526, 0.600] | 0.0010 | 0.0020 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.603 [0.584, 0.622] | 0.550 [0.424, 0.714] | 9.432 [8.789, 10.123] |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.642 [0.596, 0.691] | 0.315 [0.260, 0.383] | 0.675 [0.643, 0.708] |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 1.115 [0.948, 1.313] | 0.309 [0.267, 0.358] | 10.033 [8.963, 11.231] |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 0.725 [0.636, 0.826] | 0.600 [0.506, 0.711] | 0.735 [0.673, 0.804] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | 20.053 | 7.878 |
| `large-text.fresh.mars-mac.receiver.warm` | 28.238 | 8.865 |
| `real-congress.fresh.mac-mars.sender.warm` | 30.887 | 7.535 |
| `real-congress.fresh.mars-mac.receiver.warm` | 82.652 | 49.490 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.mac-mars.sender.warm` | xs | 0.1446 | 190 | 254 |
| `large-text.fresh.mars-mac.receiver.warm` | xs | 0.3072 | 850 | 1138 |
| `real-congress.fresh.mac-mars.sender.warm` | xs | 0.0868 | 70 | 93 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs | 0.2694 | 654 | 875 |
