# X1a-large-one

On a ~3 Gb/s direct link, xs -a copies large files at least as fast as rsync -a, and ChaCha20 slows both against AES-GCM.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T225217Z-X1a-large-one.
- Valid blocks: 11. Voided block attempts: 15.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-chacha | 8 | 1.413 [1.085, 1.841] | 1.488 [1.068, 1.855] | 0.0234 | slower |
| `large-one.fresh.mac-mars.sender.warm` | xs | 8 | 0.474 [0.290, 0.777] | 0.598 [0.299, 0.697] | 0.0078 | faster |
| `large-one.fresh.mac-mars.sender.warm` | xs-chacha | 8 | 1.018 [0.585, 1.772] | 1.280 [0.622, 1.577] | 0.9609 | inconclusive |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 3 | 1.313 [0.629, 2.741] | 1.355 | 0.5000 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 3 | 0.398 [0.091, 1.734] | 0.424 | 0.2500 | too few blocks |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 3 | 1.711 [0.008, 354.475] | 1.434 | 1.0000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-chacha | 1.579 [1.460, 1.708] | 0.985 [0.944, 1.027] | 1.413 [1.085, 1.841] |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.530 [0.424, 0.663] | 8.544 [8.218, 8.883] | 0.474 [0.289, 0.777] |
| `large-one.fresh.mac-mars.sender.warm` | xs-chacha | 1.159 [0.935, 1.437] | 8.686 [8.301, 9.088] | 1.018 [0.585, 1.772] |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 1.474 [1.111, 1.957] | 1.002 [0.923, 1.087] | 1.313 [0.628, 2.744] |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.471 [0.196, 1.129] | 0.729 [0.687, 0.773] | 0.397 [0.091, 1.724] |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 0.887 [0.376, 2.089] | 0.735 [0.700, 0.772] | 0.582 [0.149, 2.271] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-chacha | xs | xs-chacha |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | 58.595 | 82.809 | 27.794 | 59.669 |
| `large-one.fresh.mars-mac.receiver.warm` | 70.862 | 93.037 | 28.215 | 121.3 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-one.fresh.mac-mars.sender.warm` | rsync-chacha | 0.3162 | 900 | 1205 |
| `large-one.fresh.mac-mars.sender.warm` | xs | 0.5906 | 3132 | 4197 |
| `large-one.fresh.mac-mars.sender.warm` | xs-chacha | 0.6623 | 3939 | 5278 |
| `large-one.fresh.mars-mac.receiver.warm` | rsync-chacha | 0.2963 | 790 | 1058 |
| `large-one.fresh.mars-mac.receiver.warm` | xs | 0.5923 | 3151 | 4222 |
| `large-one.fresh.mars-mac.receiver.warm` | xs-chacha | 2.1470 | 41363 | 55437 |

## Voided attempts

- rsync-chacha: the transfer exited 11: ync: [receiver] write failed on "~/benchmarks/xsbench.noindex/work/20261014T225217Z-X1a-large-one/large-one.fr
- rsync-chacha: the transfer exited 13: rsync error: errors with program diagnostics (code 13) at log.c(245) [receiver=3.4.4]
- rsync: the transfer exited 13: rsync error: errors with program diagnostics (code 13) at log.c(245) [receiver=3.4.4]
- xs-chacha: the transfer exited 11: ummary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks/xsbench.noindex/
- xs: the transfer exited 11: error summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    write failed on "~/benchmarks/xsbench.noindex/
