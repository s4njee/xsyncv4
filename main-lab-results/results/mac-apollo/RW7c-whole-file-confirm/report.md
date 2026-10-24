# RW7c-whole-file-confirm

xs-rs-W is more than 5% faster than rsync on large-text (from RW7-delta-breakdown-apollo, confirmed with fresh blocks).

- Kind: confirmatory. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T185557Z-RW7c-whole-file-confirm.
- Valid blocks: 48. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 8 | 0.880 [0.865, 0.896] | 0.885 [0.864, 0.895] | 0.0078 | 0.0469 | faster |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 8 | 0.826 [0.354, 1.927] | 0.738 [0.352, 2.016] | 0.6016 | 1.0000 | inconclusive |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 8 | 0.990 [0.838, 1.170] | 0.940 [0.883, 1.230] | 0.9453 | 1.0000 | inconclusive |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 8 | 0.938 [0.452, 1.946] | 0.874 [0.403, 1.994] | 0.8516 | 1.0000 | inconclusive |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 8 | 0.975 [0.878, 1.082] | 0.955 [0.891, 1.111] | 0.6016 | 1.0000 | inconclusive |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 8 | 1.212 [0.394, 3.725] | 1.124 [0.318, 4.057] | 0.6719 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.645 [0.608, 0.685] | 5.717 [5.629, 5.807] | 0.863 [0.834, 0.893] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.688 [0.662, 0.716] | 8.684 [7.615, 9.905] | 0.825 [0.355, 1.918] |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.732 [0.671, 0.800] | 5.714 [5.645, 5.785] | 0.985 [0.835, 1.161] |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.707 [0.679, 0.737] | 8.826 [7.590, 10.263] | 0.938 [0.451, 1.949] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.715 [0.654, 0.782] | 5.735 [5.618, 5.855] | 0.971 [0.873, 1.080] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 0.740 [0.701, 0.781] | 8.489 [7.463, 9.657] | 1.205 [0.389, 3.730] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs-W |
|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.460 | 1.285 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 2.895 | 2.390 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | 1.382 | 1.369 |
| `large-text.update-10pct.mac-apollo.sender.warm` | 3.658 | 3.431 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.355 | 1.321 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 3.363 | 4.075 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.0207 | 8 | 8 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs-W | 1.0140 | 9228 | 12367 |
| `large-text.update-10pct.apollo-mac.receiver.warm` | xs-rs-W | 0.1998 | 361 | 483 |
| `large-text.update-10pct.mac-apollo.sender.warm` | xs-rs-W | 0.8734 | 6847 | 9176 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs-W | 0.1245 | 142 | 189 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs-W | 1.3433 | 16194 | 21703 |
