# K3-congress-cold

With cold caches, xs's lead over rsync on congress grows, and the Pi sending cold is the slowest case.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T222943Z-K3-congress-cold.
- Valid blocks: 12. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.cold` | xs-z-best | 6 | 0.883 [0.859, 0.908] | 0.878 [0.865, 0.930] | 0.0312 | too few blocks |
| `real-congress.fresh.freya-neo.sender.cold` | xs | 6 | 1.148 [1.123, 1.173] | 1.145 [1.120, 1.193] | 0.0312 | too few blocks |
| `real-congress.fresh.freya-neo.sender.cold` | rsync | 6 | 1.818 [1.784, 1.852] | 1.817 [1.768, 1.860] | 0.0312 | too few blocks |
| `real-congress.fresh.neo-freya.sender.cold` | xs-z-best | 6 | 0.948 [0.828, 1.085] | 0.989 [0.731, 1.038] | 0.4688 | too few blocks |
| `real-congress.fresh.neo-freya.sender.cold` | xs | 6 | 1.095 [0.928, 1.292] | 1.116 [0.808, 1.247] | 0.1875 | too few blocks |
| `real-congress.fresh.neo-freya.sender.cold` | rsync | 6 | 3.152 [2.731, 3.637] | 3.308 [2.395, 3.462] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.cold` | xs-z-best | 0.925 [0.909, 0.941] | 0.967 [0.721, 1.298] | 0.878 [0.851, 0.907] |
| `real-congress.fresh.freya-neo.sender.cold` | xs | 1.086 [1.071, 1.100] | 0.675 [0.587, 0.776] | 1.156 [1.134, 1.178] |
| `real-congress.fresh.freya-neo.sender.cold` | rsync | 0.944 [0.932, 0.956] | 0.915 [0.798, 1.048] | 1.844 [1.808, 1.880] |
| `real-congress.fresh.neo-freya.sender.cold` | xs-z-best | 0.895 [0.878, 0.911] | 1.003 [0.985, 1.021] | 0.945 [0.820, 1.090] |
| `real-congress.fresh.neo-freya.sender.cold` | xs | 1.222 [1.189, 1.257] | 1.955 [1.858, 2.057] | 1.095 [0.928, 1.293] |
| `real-congress.fresh.neo-freya.sender.cold` | rsync | 0.786 [0.778, 0.794] | 0.282 [0.275, 0.290] | 3.174 [2.741, 3.674] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-z | xs-z-best |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.cold` | 21.676 | 13.689 | 11.924 | 10.528 |
| `real-congress.fresh.neo-freya.sender.cold` | 34.458 | 11.970 | 10.933 | 10.365 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.freya-neo.sender.cold` | xs-z-best | 0.0265 | 9 | 11 |
| `real-congress.fresh.freya-neo.sender.cold` | xs | 0.0208 | 8 | 8 |
| `real-congress.fresh.freya-neo.sender.cold` | rsync | 0.0177 | 8 | 8 |
| `real-congress.fresh.neo-freya.sender.cold` | xs-z-best | 0.1288 | 151 | 202 |
| `real-congress.fresh.neo-freya.sender.cold` | xs | 0.1577 | 226 | 301 |
| `real-congress.fresh.neo-freya.sender.cold` | rsync | 0.1364 | 169 | 226 |
