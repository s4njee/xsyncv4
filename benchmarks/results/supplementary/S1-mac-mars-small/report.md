# S1-mac-mars-small

On small files between a Mac (APFS) and a Linux desktop (ext4), xs -a is faster than rsync -a, fresh and no-op, in both directions.

- Kind: screening. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261012T210425Z-S1-mac-mars-small.
- Valid blocks: 192. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-deep.fresh.mac-mars.sender.warm` | xs | 12 | 0.369 [0.301, 0.452] | 0.358 [0.304, 0.471] | 0.0005 | faster |
| `small-deep.fresh.mars-mac.receiver.warm` | xs | 12 | 1.748 [1.534, 1.992] | 1.778 [1.542, 2.050] | 0.0005 | slower |
| `small-deep.noop.mac-mars.sender.warm` | xs | 12 | 0.533 [0.429, 0.662] | 0.528 [0.421, 0.664] | 0.0010 | faster |
| `small-deep.noop.mars-mac.receiver.warm` | xs | 12 | 3.655 [2.866, 4.661] | 4.114 [2.831, 4.696] | 0.0005 | slower |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 12 | 0.293 [0.220, 0.392] | 0.280 [0.216, 0.414] | 0.0005 | faster |
| `small-flat.fresh.mars-mac.receiver.warm` | xs | 12 | 0.805 [0.726, 0.892] | 0.803 [0.723, 0.900] | 0.0005 | faster |
| `small-flat.noop.mac-mars.sender.warm` | xs | 12 | 0.353 [0.297, 0.419] | 0.357 [0.299, 0.402] | 0.0005 | faster |
| `small-flat.noop.mars-mac.receiver.warm` | xs | 12 | 0.384 [0.298, 0.494] | 0.361 [0.300, 0.521] | 0.0005 | faster |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 12 | 0.299 [0.211, 0.423] | 0.249 [0.216, 0.448] | 0.0005 | faster |
| `small-opaque.fresh.mars-mac.receiver.warm` | xs | 12 | 0.775 [0.669, 0.899] | 0.781 [0.671, 0.905] | 0.0029 | faster |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 12 | 0.299 [0.258, 0.347] | 0.301 [0.257, 0.353] | 0.0005 | faster |
| `small-opaque.noop.mars-mac.receiver.warm` | xs | 12 | 0.401 [0.339, 0.474] | 0.387 [0.341, 0.483] | 0.0005 | faster |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 12 | 1.012 [0.626, 1.635] | 0.968 [0.544, 1.712] | 0.9854 | inconclusive |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs | 12 | 0.969 [0.654, 1.435] | 1.060 [0.595, 1.214] | 0.9878 | inconclusive |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 12 | 0.667 [0.427, 1.041] | 0.854 [0.464, 0.932] | 0.0015 | inconclusive |
| `tiny-one.noop.mars-mac.receiver.warm` | xs | 12 | 1.025 [0.626, 1.678] | 1.049 [0.562, 1.429] | 0.9136 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-deep.fresh.mac-mars.sender.warm` | xs | 1.419 [1.317, 1.530] | 0.371 [0.303, 0.454] | 5.961 [4.774, 7.443] |
| `small-deep.fresh.mars-mac.receiver.warm` | xs | 2.244 [2.142, 2.352] | 1.722 [1.511, 1.963] | 5.060 [4.871, 5.256] |
| `small-deep.noop.mac-mars.sender.warm` | xs | 2.962 [2.592, 3.384] | 0.533 [0.429, 0.663] | 4.162 [4.093, 4.233] |
| `small-deep.noop.mars-mac.receiver.warm` | xs | 9.302 [8.629, 10.027] | 3.562 [2.804, 4.525] | 6.713 [6.631, 6.796] |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 0.971 [0.852, 1.106] | 0.295 [0.221, 0.395] | 4.161 [2.839, 6.101] |
| `small-flat.fresh.mars-mac.receiver.warm` | xs | 0.907 [0.875, 0.940] | 0.810 [0.733, 0.895] | 6.708 [6.665, 6.751] |
| `small-flat.noop.mac-mars.sender.warm` | xs | 0.976 [0.938, 1.016] | 0.368 [0.311, 0.435] | 1.329 [1.313, 1.346] |
| `small-flat.noop.mars-mac.receiver.warm` | xs | 1.141 [1.052, 1.238] | 0.417 [0.331, 0.527] | 1.734 [1.725, 1.744] |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 1.019 [0.906, 1.145] | 0.300 [0.213, 0.425] | 3.184 [2.449, 4.141] |
| `small-opaque.fresh.mars-mac.receiver.warm` | xs | 0.913 [0.863, 0.966] | 0.774 [0.668, 0.898] | 6.704 [6.669, 6.739] |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 1.015 [0.961, 1.071] | 0.331 [0.249, 0.440] | 1.323 [1.309, 1.338] |
| `small-opaque.noop.mars-mac.receiver.warm` | xs | 1.164 [1.083, 1.252] | 0.436 [0.372, 0.511] | 1.735 [1.714, 1.755] |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 1.230 [1.134, 1.334] | 1.010 [0.630, 1.620] | 1.024 [1.017, 1.031] |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs | 1.145 [1.085, 1.208] | 0.940 [0.691, 1.277] | 1.005 [0.998, 1.012] |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 1.177 [1.087, 1.275] | 0.668 [0.430, 1.038] | 1.005 [0.997, 1.013] |
| `tiny-one.noop.mars-mac.receiver.warm` | xs | 1.222 [1.116, 1.337] | 0.989 [0.653, 1.497] | 1.007 [0.999, 1.014] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs |
|---|---|---|
| `small-deep.fresh.mac-mars.sender.warm` | 28.527 | 10.522 |
| `small-deep.fresh.mars-mac.receiver.warm` | 32.848 | 57.421 |
| `small-deep.noop.mac-mars.sender.warm` | 6.426 | 3.424 |
| `small-deep.noop.mars-mac.receiver.warm` | 3.093 | 11.302 |
| `small-flat.fresh.mac-mars.sender.warm` | 14.960 | 4.390 |
| `small-flat.fresh.mars-mac.receiver.warm` | 28.729 | 23.113 |
| `small-flat.noop.mac-mars.sender.warm` | 0.945 | 0.333 |
| `small-flat.noop.mars-mac.receiver.warm` | 1.484 | 0.569 |
| `small-opaque.fresh.mac-mars.sender.warm` | 14.390 | 4.298 |
| `small-opaque.fresh.mars-mac.receiver.warm` | 27.278 | 21.152 |
| `small-opaque.noop.mac-mars.sender.warm` | 0.966 | 0.289 |
| `small-opaque.noop.mars-mac.receiver.warm` | 1.370 | 0.550 |
| `tiny-one.fresh.mac-mars.sender.warm` | 0.302 | 0.306 |
| `tiny-one.fresh.mars-mac.receiver.warm` | 0.301 | 0.292 |
| `tiny-one.noop.mac-mars.sender.warm` | 0.434 | 0.289 |
| `tiny-one.noop.mars-mac.receiver.warm` | 0.286 | 0.293 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-deep.fresh.mac-mars.sender.warm` | xs | 0.3216 | 931 | 1247 |
| `small-deep.fresh.mars-mac.receiver.warm` | xs | 0.2054 | 381 | 510 |
| `small-deep.noop.mac-mars.sender.warm` | xs | 0.3425 | 1055 | 1413 |
| `small-deep.noop.mars-mac.receiver.warm` | xs | 0.3828 | 1317 | 1765 |
| `small-flat.fresh.mac-mars.sender.warm` | xs | 0.4549 | 1859 | 2491 |
| `small-flat.fresh.mars-mac.receiver.warm` | xs | 0.1627 | 240 | 321 |
| `small-flat.noop.mac-mars.sender.warm` | xs | 0.2717 | 665 | 890 |
| `small-flat.noop.mars-mac.receiver.warm` | xs | 0.3972 | 1418 | 1899 |
| `small-opaque.fresh.mac-mars.sender.warm` | xs | 0.5463 | 2680 | 3591 |
| `small-opaque.fresh.mars-mac.receiver.warm` | xs | 0.2322 | 486 | 651 |
| `small-opaque.noop.mac-mars.sender.warm` | xs | 0.2317 | 484 | 648 |
| `small-opaque.noop.mars-mac.receiver.warm` | xs | 0.2639 | 628 | 840 |
| `tiny-one.fresh.mac-mars.sender.warm` | xs | 0.7547 | 5114 | 6853 |
| `tiny-one.fresh.mars-mac.receiver.warm` | xs | 0.6185 | 3435 | 4603 |
| `tiny-one.noop.mac-mars.sender.warm` | xs | 0.7008 | 4409 | 5909 |
| `tiny-one.noop.mars-mac.receiver.warm` | xs | 0.7762 | 5409 | 7249 |
