# D10-lan-noop-best

xs's best small-file setting is faster than its default on no-op copies of small trees.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T174642Z-D10-lan-noop-best.
- Valid blocks: 37. Voided block attempts: 84.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.noop.freya-neo.sender.warm` | xs-best | 1 | 1.032 |  |  | too few blocks |
| `real-congress.noop.freya-neo.sender.warm` | rsync | 1 | 5.096 |  |  | too few blocks |
| `real-congress.noop.neo-freya.sender.warm` | xs-best | 8 | 0.769 [0.689, 0.858] | 0.782 [0.674, 0.840] | 0.0078 | faster |
| `real-congress.noop.neo-freya.sender.warm` | rsync | 8 | 2.057 [1.809, 2.339] | 2.047 [1.805, 2.417] | 0.0078 | slower |
| `small-deep.noop.neo-freya.sender.warm` | xs-best | 8 | 0.854 [0.693, 1.052] | 0.804 [0.728, 1.099] | 0.1250 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 8 | 1.428 [1.305, 1.562] | 1.469 [1.290, 1.542] | 0.0078 | slower |
| `small-flat.noop.freya-neo.sender.warm` | xs-best | 4 | 1.029 [0.904, 1.171] | 1.029 | 0.5000 | too few blocks |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 4 | 2.462 [2.272, 2.669] | 2.462 | 0.1250 | too few blocks |
| `small-flat.noop.neo-freya.sender.warm` | xs-best | 8 | 1.076 [0.937, 1.236] | 1.109 [0.899, 1.217] | 0.2344 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 8 | 2.416 [2.129, 2.741] | 2.454 [2.100, 2.750] | 0.0078 | slower |
| `small-real.noop.neo-freya.sender.warm` | xs-best | 8 | 0.609 [0.546, 0.680] | 0.609 [0.529, 0.692] | 0.0078 | faster |
| `small-real.noop.neo-freya.sender.warm` | rsync | 8 | 1.136 [1.053, 1.225] | 1.134 [1.046, 1.230] | 0.0156 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.noop.freya-neo.sender.warm` | xs-best | 1.005 | 0.990 | 1.032 |
| `real-congress.noop.freya-neo.sender.warm` | rsync | 0.478 | 2.011 | 5.139 |
| `real-congress.noop.neo-freya.sender.warm` | xs-best | 0.378 [0.347, 0.413] | 0.958 [0.895, 1.026] | 0.767 [0.686, 0.857] |
| `real-congress.noop.neo-freya.sender.warm` | rsync | 0.176 [0.154, 0.202] | 0.320 [0.307, 0.333] | 2.070 [1.818, 2.357] |
| `small-deep.noop.neo-freya.sender.warm` | xs-best | 0.508 [0.476, 0.543] | 0.927 [0.845, 1.018] | 0.853 [0.691, 1.052] |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 0.145 [0.138, 0.152] | 0.179 [0.166, 0.194] | 1.430 [1.308, 1.564] |
| `small-flat.noop.freya-neo.sender.warm` | xs-best | 1.030 [1.005, 1.055] | 0.988 [0.951, 1.027] | 1.029 [0.898, 1.178] |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.878 [0.831, 0.928] | 0.451 [0.420, 0.484] | 2.495 [2.270, 2.743] |
| `small-flat.noop.neo-freya.sender.warm` | xs-best | 1.054 [0.805, 1.380] | 0.564 [0.549, 0.580] | 1.069 [0.918, 1.244] |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.767 [0.609, 0.967] | 0.553 [0.539, 0.566] | 2.497 [2.188, 2.849] |
| `small-real.noop.neo-freya.sender.warm` | xs-best | 0.296 [0.269, 0.327] | 0.980 [0.851, 1.128] | 0.606 [0.542, 0.678] |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.095 [0.088, 0.103] | 0.210 [0.204, 0.216] | 1.138 [1.054, 1.229] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-best |
|---|---|---|---|
| `real-congress.noop.freya-neo.sender.warm` | 5.421 | 1.064 | 1.098 |
| `real-congress.noop.neo-freya.sender.warm` | 2.287 | 1.111 | 0.854 |
| `small-deep.noop.neo-freya.sender.warm` | 2.286 | 1.601 | 1.367 |
| `small-flat.noop.freya-neo.sender.warm` | 0.649 | 0.264 | 0.271 |
| `small-flat.noop.neo-freya.sender.warm` | 0.603 | 0.250 | 0.269 |
| `small-real.noop.neo-freya.sender.warm` | 1.647 | 1.450 | 0.883 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.noop.neo-freya.sender.warm` | xs-best | 0.1314 | 157 | 210 |
| `real-congress.noop.neo-freya.sender.warm` | rsync | 0.1537 | 214 | 286 |
| `small-deep.noop.neo-freya.sender.warm` | xs-best | 0.2493 | 560 | 750 |
| `small-deep.noop.neo-freya.sender.warm` | rsync | 0.1073 | 106 | 141 |
| `small-flat.noop.freya-neo.sender.warm` | xs-best | 0.0811 | 62 | 82 |
| `small-flat.noop.freya-neo.sender.warm` | rsync | 0.0507 | 26 | 33 |
| `small-flat.noop.neo-freya.sender.warm` | xs-best | 0.1659 | 250 | 334 |
| `small-flat.noop.neo-freya.sender.warm` | rsync | 0.1510 | 207 | 277 |
| `small-real.noop.neo-freya.sender.warm` | xs-best | 0.1308 | 156 | 208 |
| `small-real.noop.neo-freya.sender.warm` | rsync | 0.0903 | 76 | 101 |

## Voided attempts

- neo does not answer ping
