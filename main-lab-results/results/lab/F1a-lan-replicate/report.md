# F1a-lan-replicate

xs's best setting with -z stays ahead of rsync -az from run to run.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T184701Z-F1a-lan-replicate, 20261017T202542Z-F1a-lan-replicate, 20261017T204111Z-F1a-lan-replicate, 20261017T205646Z-F1a-lan-replicate, 20261017T211342Z-F1a-lan-replicate, 20261017T212914Z-F1a-lan-replicate, 20261017T214431Z-F1a-lan-replicate, 20261017T215941Z-F1a-lan-replicate, 20261017T223055Z-F1a-lan-replicate, 20261017T224604Z-F1a-lan-replicate, 20261017T230123Z-F1a-lan-replicate.
- Valid blocks: 87. Voided block attempts: 252.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-best | 1 | 0.998 |  |  | too few blocks |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 1 | 0.961 |  |  | too few blocks |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-best | 28 | 1.006 [0.988, 1.024] | 0.998 [0.989, 1.014] | 0.5091 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 28 | 1.437 [1.401, 1.474] | 1.438 [1.389, 1.476] | 0.0000 | slower |
| `real-congress.fresh.freya-neo.sender.warm` | xs-z-best | 1 | 1.126 |  |  | too few blocks |
| `real-congress.fresh.freya-neo.sender.warm` | rsync-z | 1 | 1.347 |  |  | too few blocks |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 28 | 1.004 [0.985, 1.024] | 1.004 [0.984, 1.024] | 0.6804 | equivalent |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 28 | 3.214 [3.142, 3.287] | 3.212 [3.135, 3.287] | 0.0000 | slower |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-best | 1 | 0.705 |  |  | too few blocks |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-z | 1 | 1.202 |  |  | too few blocks |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 28 | 0.654 [0.628, 0.681] | 0.651 [0.628, 0.682] | 0.0000 | faster |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-z | 28 | 2.541 [2.415, 2.674] | 2.560 [2.436, 2.681] | 0.0000 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z-best | 0.959 | 0.985 | 0.999 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync-z | 0.811 | 0.082 | 0.958 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-best | 1.015 [0.965, 1.068] | 0.983 [0.966, 1.000] | 1.006 [0.988, 1.024] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 0.864 [0.830, 0.900] | 0.079 [0.078, 0.081] | 1.440 [1.404, 1.476] |
| `real-congress.fresh.freya-neo.sender.warm` | xs-z-best | 0.892 | 0.901 | 1.134 |
| `real-congress.fresh.freya-neo.sender.warm` | rsync-z | 0.643 | 0.846 | 1.365 |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 0.777 [0.769, 0.784] | 0.984 [0.950, 1.020] | 1.007 [0.987, 1.027] |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 0.673 [0.665, 0.681] | 0.316 [0.306, 0.327] | 3.252 [3.177, 3.328] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z-best | 0.827 | 0.982 | 0.691 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync-z | 0.845 | 0.055 | 1.211 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 0.735 [0.702, 0.769] | 0.261 [0.235, 0.289] | 0.654 [0.627, 0.682] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-z | 1.028 [0.985, 1.074] | 0.156 [0.140, 0.174] | 2.584 [2.456, 2.719] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync-z | xs-z | xs-z-best |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 9.581 | 9.967 | 9.949 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 14.018 | 9.755 | 9.814 |
| `real-congress.fresh.freya-neo.sender.warm` | 16.798 | 12.469 | 14.046 |
| `real-congress.fresh.neo-freya.sender.warm` | 28.455 | 8.855 | 8.890 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.322 | 5.259 | 3.707 |
| `small-flat.fresh.neo-freya.sender.warm` | 9.139 | 3.596 | 2.353 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z-best | 0.0465 | 22 | 28 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync-z | 0.0652 | 41 | 54 |
| `real-congress.fresh.neo-freya.sender.warm` | xs-z-best | 0.0503 | 25 | 33 |
| `real-congress.fresh.neo-freya.sender.warm` | rsync-z | 0.0581 | 33 | 43 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z-best | 0.1043 | 100 | 133 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync-z | 0.1309 | 156 | 209 |

## Voided attempts

- neo does not answer ping
