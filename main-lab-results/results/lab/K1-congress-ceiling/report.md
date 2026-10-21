# K1-congress-ceiling

Each receiver creates small files locally much faster than xs delivers them over gigabit.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T223011Z-K1-congress-ceiling.
- Valid blocks: 36. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | xs-z-best | 6 | 0.904 [0.869, 0.941] | 0.896 [0.863, 0.964] | 0.0312 | too few blocks |
| `real-congress.fresh.freya-neo.sender.warm` | local-x1 | 6 | 2.675 [2.579, 2.774] | 2.657 [2.600, 2.853] | 0.0312 | too few blocks |
| `real-congress.fresh.freya-neo.sender.warm` | local-x4 | 6 | 1.384 [1.351, 1.417] | 1.383 [1.341, 1.423] | 0.0312 | too few blocks |
| `real-congress.fresh.freya-neo.sender.warm` | local-x8 | 6 | 1.287 [1.223, 1.355] | 1.302 [1.238, 1.372] | 0.0312 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 6 | 0.895 [0.649, 1.233] | 0.987 [0.484, 1.115] | 0.5938 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | local-x1 | 6 | 0.534 [0.374, 0.761] | 0.596 [0.270, 0.665] | 0.0312 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | local-x4 | 6 | 0.300 [0.208, 0.432] | 0.340 [0.148, 0.362] | 0.0312 | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | local-x8 | 6 | 0.296 [0.210, 0.415] | 0.332 [0.156, 0.376] | 0.0312 | too few blocks |
| `small-deep.fresh.freya-neo.sender.warm` | xs-z-best | 6 | 0.954 [0.915, 0.995] | 0.956 [0.906, 1.008] | 0.0625 | too few blocks |
| `small-deep.fresh.freya-neo.sender.warm` | local-x1 | 6 | 1.028 [0.988, 1.070] | 1.033 [0.962, 1.071] | 0.1562 | too few blocks |
| `small-deep.fresh.freya-neo.sender.warm` | local-x4 | 6 | 0.975 [0.895, 1.062] | 0.972 [0.905, 1.131] | 0.4688 | too few blocks |
| `small-deep.fresh.freya-neo.sender.warm` | local-x8 | 6 | 0.918 [0.869, 0.970] | 0.918 [0.869, 0.983] | 0.0312 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | xs-z-best | 6 | 2.208 [1.140, 4.273] | 2.123 [1.140, 6.081] | 0.0312 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | local-x1 | 6 | 0.670 [0.497, 0.903] | 0.683 [0.441, 0.927] | 0.0312 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | local-x4 | 6 | 0.492 [0.296, 0.816] | 0.458 [0.313, 1.188] | 0.0625 | too few blocks |
| `small-deep.fresh.neo-freya.sender.warm` | local-x8 | 6 | 0.422 [0.309, 0.575] | 0.425 [0.265, 0.552] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-best | 6 | 0.695 [0.685, 0.705] | 0.693 [0.685, 0.712] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | local-x1 | 6 | 1.826 [1.688, 1.975] | 1.844 [1.601, 1.981] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | local-x4 | 6 | 0.855 [0.813, 0.900] | 0.856 [0.804, 0.903] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | local-x8 | 6 | 0.777 [0.717, 0.842] | 0.782 [0.680, 0.852] | 0.0312 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 6 | 0.736 [0.686, 0.791] | 0.740 [0.666, 0.792] | 0.0312 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | local-x1 | 6 | 0.517 [0.509, 0.526] | 0.518 [0.505, 0.526] | 0.0312 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | local-x4 | 6 | 0.225 [0.188, 0.269] | 0.222 [0.181, 0.266] | 0.0312 | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | local-x8 | 6 | 0.178 [0.151, 0.209] | 0.172 [0.153, 0.236] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | xs-z-best | 0.945 [0.919, 0.972] | 1.700 [1.205, 2.399] | 0.899 [0.864, 0.936] |
| `real-congress.fresh.freya-neo.sender.warm` | local-x1 |  |  | 2.721 [2.621, 2.826] |
| `real-congress.fresh.freya-neo.sender.warm` | local-x4 |  |  | 1.383 [1.353, 1.414] |
| `real-congress.fresh.freya-neo.sender.warm` | local-x8 |  |  | 1.291 [1.223, 1.362] |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 0.768 [0.739, 0.798] | 0.907 [0.663, 1.240] | 0.891 [0.635, 1.252] |
| `real-congress.fresh.neo-freya.sender.warm` | local-x1 |  |  | 0.519 [0.361, 0.748] |
| `real-congress.fresh.neo-freya.sender.warm` | local-x4 |  |  | 0.281 [0.186, 0.427] |
| `real-congress.fresh.neo-freya.sender.warm` | local-x8 |  |  | 0.284 [0.197, 0.408] |
| `small-deep.fresh.freya-neo.sender.warm` | xs-z-best | 0.983 [0.962, 1.004] | 1.010 [0.972, 1.050] | 0.953 [0.919, 0.988] |
| `small-deep.fresh.freya-neo.sender.warm` | local-x1 |  |  | 1.033 [0.990, 1.077] |
| `small-deep.fresh.freya-neo.sender.warm` | local-x4 |  |  | 0.978 [0.897, 1.066] |
| `small-deep.fresh.freya-neo.sender.warm` | local-x8 |  |  | 0.919 [0.868, 0.974] |
| `small-deep.fresh.neo-freya.sender.warm` | xs-z-best | 0.987 [0.622, 1.567] | 1.032 [0.771, 1.383] | 2.217 [1.136, 4.329] |
| `small-deep.fresh.neo-freya.sender.warm` | local-x1 |  |  | 0.631 [0.470, 0.849] |
| `small-deep.fresh.neo-freya.sender.warm` | local-x4 |  |  | 0.398 [0.292, 0.543] |
| `small-deep.fresh.neo-freya.sender.warm` | local-x8 |  |  | 0.397 [0.283, 0.557] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-best | 0.820 [0.815, 0.826] | 0.898 [0.762, 1.059] | 0.681 [0.672, 0.689] |
| `small-flat.fresh.freya-neo.sender.warm` | local-x1 |  |  | 1.874 [1.734, 2.024] |
| `small-flat.fresh.freya-neo.sender.warm` | local-x4 |  |  | 0.847 [0.806, 0.890] |
| `small-flat.fresh.freya-neo.sender.warm` | local-x8 |  |  | 0.762 [0.699, 0.832] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 0.766 [0.699, 0.839] | 0.293 [0.198, 0.435] | 0.736 [0.681, 0.795] |
| `small-flat.fresh.neo-freya.sender.warm` | local-x1 |  |  | 0.508 [0.493, 0.523] |
| `small-flat.fresh.neo-freya.sender.warm` | local-x4 |  |  | 0.182 [0.169, 0.196] |
| `small-flat.fresh.neo-freya.sender.warm` | local-x8 |  |  | 0.159 [0.152, 0.166] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | local-x1 | local-x4 | local-x8 | xs-z | xs-z-best |
|---|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | 33.010 | 17.076 | 15.883 | 12.342 | 11.160 |
| `real-congress.fresh.neo-freya.sender.warm` | 4.999 | 2.809 | 2.769 | 9.367 | 8.379 |
| `small-deep.fresh.freya-neo.sender.warm` | 14.397 | 13.654 | 12.858 | 14.005 | 13.367 |
| `small-deep.fresh.neo-freya.sender.warm` | 4.919 | 3.613 | 3.096 | 7.344 | 16.211 |
| `small-flat.fresh.freya-neo.sender.warm` | 9.685 | 4.536 | 4.122 | 5.304 | 3.685 |
| `small-flat.fresh.neo-freya.sender.warm` | 1.853 | 0.807 | 0.637 | 3.584 | 2.640 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.warm` | xs-z-best | 0.0376 | 15 | 19 |
| `real-congress.fresh.freya-neo.sender.warm` | local-x1 | 0.0346 | 13 | 17 |
| `real-congress.fresh.freya-neo.sender.warm` | local-x4 | 0.0230 | 8 | 9 |
| `real-congress.fresh.freya-neo.sender.warm` | local-x8 | 0.0489 | 24 | 31 |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 0.3054 | 840 | 1124 |
| `real-congress.fresh.neo-freya.sender.warm` | local-x1 | 0.3383 | 1030 | 1379 |
| `real-congress.fresh.neo-freya.sender.warm` | local-x4 | 0.3478 | 1088 | 1457 |
| `real-congress.fresh.neo-freya.sender.warm` | local-x8 | 0.3239 | 944 | 1264 |
| `small-deep.fresh.freya-neo.sender.warm` | xs-z-best | 0.0398 | 17 | 22 |
| `small-deep.fresh.freya-neo.sender.warm` | local-x1 | 0.0379 | 15 | 20 |
| `small-deep.fresh.freya-neo.sender.warm` | local-x4 | 0.0814 | 62 | 82 |
| `small-deep.fresh.freya-neo.sender.warm` | local-x8 | 0.0522 | 27 | 35 |
| `small-deep.fresh.neo-freya.sender.warm` | xs-z-best | 0.6293 | 3556 | 4766 |
| `small-deep.fresh.neo-freya.sender.warm` | local-x1 | 0.2846 | 729 | 976 |
| `small-deep.fresh.neo-freya.sender.warm` | local-x4 | 0.4827 | 2093 | 2805 |
| `small-deep.fresh.neo-freya.sender.warm` | local-x8 | 0.2950 | 783 | 1049 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-best | 0.0139 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | local-x1 | 0.0750 | 53 | 70 |
| `small-flat.fresh.freya-neo.sender.warm` | local-x4 | 0.0486 | 24 | 31 |
| `small-flat.fresh.freya-neo.sender.warm` | local-x8 | 0.0765 | 55 | 73 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 0.0678 | 44 | 58 |
| `small-flat.fresh.neo-freya.sender.warm` | local-x1 | 0.0155 | 8 | 8 |
| `small-flat.fresh.neo-freya.sender.warm` | local-x4 | 0.1700 | 262 | 350 |
| `small-flat.fresh.neo-freya.sender.warm` | local-x8 | 0.1547 | 217 | 290 |
