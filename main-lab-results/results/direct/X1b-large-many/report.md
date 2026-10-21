# X1b-large-many

On a ~3 Gb/s direct link, xs -a copies large files at least as fast as rsync -a, and ChaCha20 slows both against AES-GCM.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T225219Z-X1b-large-many, 20261015T012150Z-X1b-large-many, 20261015T030424Z-X1b-large-many.
- Valid blocks: 16. Voided block attempts: 96.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | rsync-chacha | 8 | 1.694 [1.580, 1.816] | 1.727 [1.577, 1.804] | 0.0078 | slower |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 8 | 0.576 [0.512, 0.647] | 0.581 [0.503, 0.649] | 0.0078 | faster |
| `large-four.fresh.mars-mac.receiver.warm` | xs-chacha | 8 | 0.955 [0.868, 1.052] | 0.932 [0.884, 1.069] | 0.2812 | inconclusive |
| `large-mixed.fresh.mars-mac.receiver.warm` | rsync-chacha | 8 | 1.626 [1.387, 1.906] | 1.712 [1.336, 1.841] | 0.0078 | slower |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 8 | 0.555 [0.472, 0.653] | 0.576 [0.452, 0.635] | 0.0078 | faster |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs-chacha | 8 | 0.890 [0.732, 1.082] | 0.937 [0.693, 1.042] | 0.1406 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | rsync-chacha | 1.680 [1.635, 1.727] | 1.008 [0.987, 1.028] | 1.696 [1.581, 1.818] |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 0.563 [0.544, 0.583] | 0.720 [0.658, 0.787] | 0.575 [0.512, 0.646] |
| `large-four.fresh.mars-mac.receiver.warm` | xs-chacha | 1.139 [1.105, 1.174] | 0.723 [0.707, 0.739] | 0.955 [0.867, 1.052] |
| `large-mixed.fresh.mars-mac.receiver.warm` | rsync-chacha | 1.676 [1.599, 1.757] | 1.000 [0.975, 1.025] | 1.627 [1.388, 1.907] |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 0.661 [0.628, 0.696] | 0.654 [0.585, 0.730] | 0.555 [0.471, 0.652] |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs-chacha | 1.223 [1.163, 1.286] | 0.710 [0.700, 0.721] | 0.890 [0.731, 1.082] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-chacha | xs | xs-chacha |
|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | 38.963 | 66.006 | 22.436 | 37.223 |
| `large-mixed.fresh.mars-mac.receiver.warm` | 42.601 | 69.259 | 23.657 | 37.910 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-four.fresh.mars-mac.receiver.warm` | rsync-chacha | 0.0833 | 65 | 86 |
| `large-four.fresh.mars-mac.receiver.warm` | xs | 0.1396 | 177 | 237 |
| `large-four.fresh.mars-mac.receiver.warm` | xs-chacha | 0.1151 | 121 | 162 |
| `large-mixed.fresh.mars-mac.receiver.warm` | rsync-chacha | 0.1901 | 327 | 437 |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs | 0.1936 | 339 | 453 |
| `large-mixed.fresh.mars-mac.receiver.warm` | xs-chacha | 0.2339 | 493 | 660 |

## Voided attempts

- rsync-chacha: the destination does not match the corpus manifest: 
- rsync-chacha: the transfer exited 11: rsync: [receiver] write failed on "~/benchmarks/xsbench.noindex/work/20261014T225219Z-X1b-large-many/large-fou
- rsync-chacha: the transfer exited 11: rsync: [receiver] write failed on "~/benchmarks/xsbench.noindex/work/20261014T225219Z-X1b-large-many/large-mix
- rsync-chacha: the transfer exited 13: rsync error: errors with program diagnostics (code 13) at log.c(245) [receiver=3.4.4]
- rsync-chacha: the transfer exited 13: rsync error: errors with program diagnostics (code 13) at log.c(245) [receiver=3.4.4]
rsync: [generator] write error: Brok
- rsync: the destination does not match the corpus manifest: 
- rsync: the transfer exited 11: rsync: [receiver] write failed on "~/benchmarks/xsbench.noindex/work/20261014T225219Z-X1b-large-many/large-four.fresh
- rsync: the transfer exited 11: rsync: [receiver] write failed on "~/benchmarks/xsbench.noindex/work/20261014T225219Z-X1b-large-many/large-mixed.fres
- rsync: the transfer exited 13: rsync error: errors with program diagnostics (code 13) at log.c(245) [receiver=3.4.4]
- xs-chacha: the destination does not match the corpus manifest: 
- xs-chacha: the transfer exited 11:  (28)
xs: error summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks
- xs-chacha: the transfer exited 11: (28)
xs: error summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks/
- xs: the destination does not match the corpus manifest: 
- xs: the transfer exited 11:  device (28)
xs: error summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks
- xs: the transfer exited 11: device (28)
xs: error summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks/
