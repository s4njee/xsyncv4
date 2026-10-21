# X1c-large-one-to-mac

On a ~3 Gb/s direct link, xs -a copies large files at least as fast as rsync -a, and ChaCha20 slows both against AES-GCM.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T012148Z-X1c-large-one-to-mac.
- Valid blocks: 8. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 8 | 1.609 [1.414, 1.831] | 1.651 [1.392, 1.813] | 0.0078 | slower |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 8 | 0.558 [0.510, 0.610] | 0.563 [0.504, 0.612] | 0.0078 | faster |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 8 | 0.870 [0.786, 0.963] | 0.878 [0.776, 0.960] | 0.0156 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 1.672 [1.612, 1.733] | 1.002 [0.985, 1.018] | 1.610 [1.415, 1.832] |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.539 [0.528, 0.550] | 0.714 [0.641, 0.797] | 0.556 [0.509, 0.608] |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 1.118 [1.078, 1.161] | 0.711 [0.699, 0.724] | 0.870 [0.786, 0.963] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-chacha | xs | xs-chacha |
|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | 37.786 | 60.787 | 21.072 | 32.887 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 0.1545 | 217 | 290 |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.1068 | 105 | 140 |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 0.1213 | 135 | 180 |
