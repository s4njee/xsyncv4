# X1d-large-many-to-mars

On a ~3 Gb/s direct link, xs -a copies large files at least as fast as rsync -a, and ChaCha20 slows both against AES-GCM.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261015T131339Z-X1d-large-many-to-mars.
- Valid blocks: 16. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | rsync-chacha | 8 | 1.489 [0.989, 2.243] | 1.669 [0.897, 2.091] | 0.0703 | inconclusive |
| `large-four.fresh.mac-mars.sender.warm` | xs | 8 | 0.460 [0.298, 0.710] | 0.506 [0.263, 0.692] | 0.0078 | faster |
| `large-four.fresh.mac-mars.sender.warm` | xs-chacha | 8 | 1.061 [0.732, 1.536] | 1.194 [0.661, 1.384] | 0.7891 | inconclusive |
| `large-mixed.fresh.mac-mars.sender.warm` | rsync-chacha | 8 | 1.433 [1.148, 1.788] | 1.424 [1.147, 1.881] | 0.0078 | slower |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 8 | 0.459 [0.341, 0.617] | 0.461 [0.339, 0.659] | 0.0078 | faster |
| `large-mixed.fresh.mac-mars.sender.warm` | xs-chacha | 8 | 0.961 [0.668, 1.383] | 0.990 [0.642, 1.463] | 0.7891 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | rsync-chacha | 1.618 [1.334, 1.963] | 0.991 [0.973, 1.010] | 1.488 [0.988, 2.241] |
| `large-four.fresh.mac-mars.sender.warm` | xs | 0.509 [0.434, 0.598] | 9.615 [9.310, 9.931] | 0.458 [0.297, 0.707] |
| `large-four.fresh.mac-mars.sender.warm` | xs-chacha | 1.169 [0.989, 1.381] | 9.639 [9.045, 10.273] | 1.060 [0.731, 1.537] |
| `large-mixed.fresh.mac-mars.sender.warm` | rsync-chacha | 1.603 [1.470, 1.748] | 0.995 [0.985, 1.004] | 1.432 [1.147, 1.788] |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 0.512 [0.477, 0.549] | 10.346 [9.961, 10.746] | 0.458 [0.341, 0.617] |
| `large-mixed.fresh.mac-mars.sender.warm` | xs-chacha | 1.185 [1.085, 1.294] | 10.424 [9.898, 10.977] | 0.961 [0.667, 1.384] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-chacha | xs | xs-chacha |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | 85.150 | 126.8 | 39.164 | 90.312 |
| `large-mixed.fresh.mac-mars.sender.warm` | 100.7 | 144.3 | 46.191 | 96.823 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-four.fresh.mac-mars.sender.warm` | rsync-chacha | 0.4899 | 2156 | 2889 |
| `large-four.fresh.mac-mars.sender.warm` | xs | 0.5201 | 2430 | 3256 |
| `large-four.fresh.mac-mars.sender.warm` | xs-chacha | 0.4433 | 1766 | 2366 |
| `large-mixed.fresh.mac-mars.sender.warm` | rsync-chacha | 0.2652 | 634 | 848 |
| `large-mixed.fresh.mac-mars.sender.warm` | xs | 0.3539 | 1126 | 1508 |
| `large-mixed.fresh.mac-mars.sender.warm` | xs-chacha | 0.4351 | 1701 | 2279 |
