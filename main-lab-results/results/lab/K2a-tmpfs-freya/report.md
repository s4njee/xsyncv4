# K2a-tmpfs-freya

xs copies small trees into RAM on freya no faster than onto its NVMe: the receiver's disk is not the limit.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T223005Z-K2a-tmpfs-freya.
- Valid blocks: 18. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-z-best | 6 | 0.997 [0.953, 1.042] | 0.993 [0.938, 1.062] | 0.8125 | too few blocks |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs | 6 | 1.421 [1.370, 1.473] | 1.416 [1.359, 1.503] | 0.0312 | too few blocks |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-best | 6 | 1.376 [1.333, 1.421] | 1.370 [1.334, 1.447] | 0.0312 | too few blocks |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-z-best | 6 | 0.993 [0.927, 1.063] | 0.990 [0.923, 1.096] | 0.8125 | too few blocks |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs | 6 | 0.974 [0.961, 0.988] | 0.973 [0.956, 0.986] | 0.0312 | too few blocks |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-best | 6 | 0.946 [0.910, 0.982] | 0.944 [0.907, 1.007] | 0.0625 | too few blocks |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-z-best | 6 | 1.032 [0.959, 1.111] | 1.038 [0.924, 1.117] | 0.3125 | too few blocks |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs | 6 | 1.204 [1.126, 1.287] | 1.206 [1.101, 1.319] | 0.0312 | too few blocks |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-best | 6 | 1.205 [1.124, 1.291] | 1.204 [1.097, 1.321] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.766 [0.757, 0.775] | 1.007 [0.953, 1.064] | 0.997 [0.953, 1.042] |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs | 1.185 [1.158, 1.212] | 2.364 [2.319, 2.410] | 1.421 [1.370, 1.473] |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-best | 0.908 [0.889, 0.929] | 2.340 [2.226, 2.461] | 1.376 [1.333, 1.421] |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.636 [0.626, 0.647] | 1.005 [0.955, 1.058] | 0.993 [0.927, 1.063] |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs | 0.927 [0.878, 0.979] | 1.094 [0.920, 1.301] | 0.974 [0.961, 0.988] |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-best | 0.588 [0.567, 0.611] | 0.987 [0.891, 1.094] | 0.946 [0.910, 0.982] |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.959 [0.943, 0.975] | 0.513 [0.493, 0.535] | 1.032 [0.959, 1.111] |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs | 0.904 [0.886, 0.923] | 2.538 [2.322, 2.774] | 1.204 [1.126, 1.287] |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-best | 0.841 [0.801, 0.883] | 2.607 [2.511, 2.706] | 1.205 [1.124, 1.291] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-best | xs-z | xs-z-best |
|---|---|---|---|---|
| `real-congress.fresh.neo-freya-shm.sender.warm` | 11.354 | 10.998 | 7.992 | 7.968 |
| `small-deep.fresh.neo-freya-shm.sender.warm` | 5.263 | 5.108 | 5.402 | 5.363 |
| `small-flat.fresh.neo-freya-shm.sender.warm` | 2.942 | 2.945 | 2.444 | 2.523 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.0425 | 19 | 24 |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs | 0.0343 | 13 | 17 |
| `real-congress.fresh.neo-freya-shm.sender.warm` | xs-best | 0.0303 | 11 | 14 |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.0655 | 41 | 54 |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs | 0.0130 | 8 | 8 |
| `small-deep.fresh.neo-freya-shm.sender.warm` | xs-best | 0.0361 | 14 | 18 |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-z-best | 0.0703 | 47 | 62 |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs | 0.0639 | 39 | 52 |
| `small-flat.fresh.neo-freya-shm.sender.warm` | xs-best | 0.0660 | 42 | 55 |
