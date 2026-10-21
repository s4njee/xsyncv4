# N4-mac-receive-tune

Some receiving worker count or --no-atomic makes small-file copies onto APFS faster.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T113055Z-N4-mac-receive-tune.
- Valid blocks: 10. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv1 | 3 | 0.997 [0.828, 1.201] | 0.988 | 1.0000 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv2 | 3 | 0.914 [0.458, 1.826] | 0.952 | 1.0000 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv8 | 3 | 0.966 [0.507, 1.838] | 0.992 | 1.0000 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | no-atomic | 3 | 0.618 [0.348, 1.096] | 0.633 | 0.2500 | too few blocks |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 3 | 1.929 [1.071, 3.477] | 1.976 | 0.2500 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 3 | 1.442 [1.179, 1.763] | 1.439 | 0.2500 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 3 | 1.237 [0.835, 1.831] | 1.223 | 0.2500 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 3 | 1.126 [1.085, 1.169] | 1.126 | 0.2500 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | no-atomic | 3 | 0.944 [0.601, 1.481] | 0.933 | 0.7500 | too few blocks |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 3 | 0.620 [0.531, 0.725] | 0.626 | 0.2500 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | recv1 | 4 | 0.909 [0.783, 1.054] | 0.909 | 0.2500 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | recv2 | 4 | 0.921 [0.839, 1.011] | 0.926 | 0.1250 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | recv8 | 4 | 1.069 [0.815, 1.402] | 1.003 | 0.7500 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | no-atomic | 4 | 0.588 [0.481, 0.719] | 0.581 | 0.1250 | too few blocks |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 4 | 1.101 [0.983, 1.232] | 1.101 | 0.1250 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv1 | 0.890 [0.829, 0.956] | 1.001 [0.888, 1.128] | 0.997 [0.835, 1.190] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv2 | 0.968 [0.846, 1.108] | 0.998 [0.878, 1.134] | 0.917 [0.458, 1.838] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv8 | 1.013 [0.934, 1.098] | 1.006 [0.924, 1.095] | 0.968 [0.502, 1.864] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | no-atomic | 0.830 [0.802, 0.859] | 0.940 [0.743, 1.191] | 0.620 [0.350, 1.099] |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 1.181 [1.117, 1.249] | 1.324 [1.181, 1.483] | 1.945 [1.080, 3.503] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 0.746 [0.691, 0.804] | 0.834 [0.711, 0.978] | 1.444 [1.182, 1.763] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 0.882 [0.813, 0.956] | 0.906 [0.747, 1.099] | 1.238 [0.836, 1.833] |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 1.102 [1.068, 1.138] | 0.950 [0.760, 1.187] | 1.127 [1.086, 1.169] |
| `small-deep.fresh.mars-mac.receiver.warm` | no-atomic | 0.968 [0.950, 0.988] | 1.088 [0.945, 1.253] | 0.944 [0.601, 1.484] |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.399 [0.386, 0.412] | 1.257 [0.932, 1.695] | 0.614 [0.519, 0.726] |
| `small-flat.fresh.mars-mac.receiver.warm` | recv1 | 0.823 [0.775, 0.874] | 1.050 [0.947, 1.164] | 0.907 [0.786, 1.046] |
| `small-flat.fresh.mars-mac.receiver.warm` | recv2 | 0.963 [0.931, 0.996] | 1.033 [0.883, 1.209] | 0.925 [0.841, 1.016] |
| `small-flat.fresh.mars-mac.receiver.warm` | recv8 | 1.016 [0.940, 1.099] | 1.023 [0.947, 1.106] | 1.068 [0.828, 1.378] |
| `small-flat.fresh.mars-mac.receiver.warm` | no-atomic | 0.664 [0.625, 0.706] | 1.074 [0.932, 1.239] | 0.592 [0.488, 0.718] |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 1.005 [0.970, 1.042] | 1.457 [1.282, 1.656] | 1.108 [1.003, 1.223] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | no-atomic | recv1 | recv2 | recv8 | rsync | xs |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | 3.152 | 5.087 | 4.664 | 4.925 | 9.842 | 5.101 |
| `small-deep.fresh.mars-mac.receiver.warm` | 44.409 | 67.852 | 58.195 | 52.983 | 29.182 | 47.055 |
| `small-flat.fresh.mars-mac.receiver.warm` | 13.709 | 21.205 | 21.478 | 24.930 | 25.678 | 23.330 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv1 | 0.0750 | 53 | 70 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv2 | 0.2784 | 698 | 935 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | recv8 | 0.2592 | 605 | 810 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | no-atomic | 0.2307 | 480 | 642 |
| `mixed-bimodal.fresh.mars-mac.receiver.warm` | rsync | 0.2371 | 507 | 679 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv1 | 0.0809 | 61 | 81 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv2 | 0.1580 | 226 | 303 |
| `small-deep.fresh.mars-mac.receiver.warm` | recv8 | 0.0149 | 8 | 8 |
| `small-deep.fresh.mars-mac.receiver.warm` | no-atomic | 0.1815 | 298 | 399 |
| `small-deep.fresh.mars-mac.receiver.warm` | rsync | 0.0627 | 38 | 50 |
| `small-flat.fresh.mars-mac.receiver.warm` | recv1 | 0.0933 | 81 | 107 |
| `small-flat.fresh.mars-mac.receiver.warm` | recv2 | 0.0587 | 33 | 44 |
| `small-flat.fresh.mars-mac.receiver.warm` | recv8 | 0.1706 | 264 | 353 |
| `small-flat.fresh.mars-mac.receiver.warm` | no-atomic | 0.1264 | 146 | 195 |
| `small-flat.fresh.mars-mac.receiver.warm` | rsync | 0.0708 | 47 | 63 |

## Voided attempts

- stopped
