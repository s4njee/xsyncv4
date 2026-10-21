# Z1b-10g-compress

xs -z delivers corpus data faster than xs without it on compressible trees, and faster than rsync -z.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T161838Z-Z1b-10g-compress.
- Valid blocks: 24. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-z | 6 | 0.702 [0.274, 1.803] | 0.901 [0.145, 1.830] | 0.4375 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-z1 | 6 | 0.656 [0.426, 1.010] | 0.717 [0.326, 1.016] | 0.0625 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-z3 | 6 | 0.843 [0.392, 1.812] | 0.856 [0.297, 2.472] | 0.5312 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync | 6 | 2.540 [1.662, 3.884] | 2.627 [1.262, 4.377] | 0.0312 | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync-z | 6 | 3.552 [2.026, 6.228] | 3.491 [1.590, 8.345] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z | 6 | 0.971 [0.586, 1.608] | 1.028 [0.443, 1.580] | 0.9062 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z1 | 6 | 1.095 [0.726, 1.650] | 1.143 [0.622, 1.726] | 0.5938 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z3 | 6 | 0.863 [0.504, 1.477] | 0.813 [0.448, 2.159] | 0.5000 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync | 6 | 4.659 [2.848, 7.622] | 4.660 [2.291, 9.480] | 0.0312 | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-z | 6 | 2.496 [1.511, 4.123] | 2.161 [1.750, 6.520] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z | 6 | 0.814 [0.521, 1.272] | 0.810 [0.439, 1.493] | 0.3125 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z1 | 6 | 0.897 [0.561, 1.435] | 0.863 [0.653, 2.023] | 0.5938 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 6 | 0.842 [0.565, 1.255] | 0.802 [0.503, 1.350] | 0.3438 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync | 6 | 2.574 [1.641, 4.039] | 2.463 [1.642, 4.936] | 0.0312 | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync-z | 6 | 3.918 [2.680, 5.727] | 3.938 [2.280, 5.970] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z | 6 | 0.392 [0.202, 0.761] | 0.397 [0.154, 1.062] | 0.0625 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z1 | 6 | 0.421 [0.171, 1.034] | 0.420 [0.132, 1.833] | 0.0625 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 6 | 0.356 [0.214, 0.592] | 0.347 [0.216, 0.686] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync | 6 | 3.426 [2.587, 4.536] | 3.395 [2.321, 5.385] | 0.0312 | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-z | 6 | 1.528 [0.964, 2.422] | 1.618 [0.743, 2.459] | 0.0938 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-z | 1.331 [1.191, 1.489] | 1.939 [1.828, 2.056] | 0.702 [0.274, 1.804] |
| `large-half.fresh.mac-mars.sender.warm` | xs-z1 | 1.399 [1.281, 1.528] | 1.870 [1.831, 1.909] | 0.656 [0.426, 1.010] |
| `large-half.fresh.mac-mars.sender.warm` | xs-z3 | 1.714 [1.571, 1.871] | 2.468 [2.239, 2.719] | 0.843 [0.392, 1.812] |
| `large-half.fresh.mac-mars.sender.warm` | rsync | 2.018 [1.861, 2.188] | 0.103 [0.098, 0.108] | 2.542 [1.662, 3.887] |
| `large-half.fresh.mac-mars.sender.warm` | rsync-z | 3.023 [2.720, 3.360] | 0.102 [0.097, 0.107] | 3.555 [2.027, 6.234] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z | 1.253 [1.184, 1.326] | 1.612 [1.535, 1.694] | 0.970 [0.585, 1.608] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z1 | 1.280 [1.199, 1.367] | 1.615 [1.535, 1.700] | 1.095 [0.725, 1.653] |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z3 | 1.350 [1.258, 1.449] | 2.276 [2.165, 2.393] | 0.862 [0.503, 1.478] |
| `large-half.fresh.mars-mac.receiver.warm` | rsync | 1.888 [1.592, 2.240] | 1.364 [1.297, 1.436] | 4.675 [2.856, 7.652] |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-z | 1.878 [1.696, 2.080] | 1.362 [1.301, 1.425] | 2.503 [1.513, 4.138] |
| `large-text.fresh.mac-mars.sender.warm` | xs-z | 1.847 [1.710, 1.994] | 2.268 [2.006, 2.564] | 0.814 [0.521, 1.273] |
| `large-text.fresh.mac-mars.sender.warm` | xs-z1 | 1.786 [1.657, 1.925] | 2.133 [2.028, 2.243] | 0.897 [0.561, 1.436] |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 2.400 [2.212, 2.604] | 2.595 [2.232, 3.018] | 0.842 [0.565, 1.255] |
| `large-text.fresh.mac-mars.sender.warm` | rsync | 2.017 [1.808, 2.250] | 0.101 [0.098, 0.103] | 2.576 [1.641, 4.043] |
| `large-text.fresh.mac-mars.sender.warm` | rsync-z | 3.355 [3.162, 3.561] | 0.100 [0.096, 0.104] | 3.921 [2.681, 5.734] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z | 1.411 [1.317, 1.512] | 1.611 [1.521, 1.707] | 0.390 [0.200, 0.759] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z1 | 1.382 [1.304, 1.464] | 1.529 [1.428, 1.639] | 0.418 [0.169, 1.032] |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 1.571 [1.471, 1.678] | 2.129 [1.988, 2.281] | 0.353 [0.211, 0.590] |
| `large-text.fresh.mars-mac.receiver.warm` | rsync | 1.995 [1.726, 2.308] | 1.277 [1.187, 1.374] | 3.436 [2.596, 4.548] |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-z | 1.971 [1.849, 2.102] | 1.294 [1.202, 1.393] | 1.505 [0.964, 2.351] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z | xs-z1 | xs-z3 |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | 82.405 | 115.2 | 32.439 | 22.785 | 21.289 | 27.351 |
| `large-half.fresh.mars-mac.receiver.warm` | 107.8 | 57.752 | 23.139 | 22.464 | 25.330 | 19.966 |
| `large-text.fresh.mac-mars.sender.warm` | 64.367 | 97.958 | 25.002 | 20.354 | 22.433 | 21.057 |
| `large-text.fresh.mars-mac.receiver.warm` | 103.2 | 46.030 | 30.125 | 11.810 | 12.670 | 10.715 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-z | 0.8985 | 7247 | 9712 |
| `large-half.fresh.mac-mars.sender.warm` | xs-z1 | 0.4109 | 1518 | 2033 |
| `large-half.fresh.mac-mars.sender.warm` | xs-z3 | 0.7288 | 4769 | 6390 |
| `large-half.fresh.mac-mars.sender.warm` | rsync | 0.4045 | 1471 | 1971 |
| `large-half.fresh.mac-mars.sender.warm` | rsync-z | 0.5350 | 2571 | 3445 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z | 0.4809 | 2078 | 2784 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z1 | 0.3908 | 1373 | 1839 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z3 | 0.5121 | 2356 | 3157 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync | 0.4691 | 1977 | 2648 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-z | 0.4783 | 2055 | 2754 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z | 0.4254 | 1627 | 2179 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z1 | 0.4472 | 1797 | 2407 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 0.3801 | 1299 | 1740 |
| `large-text.fresh.mac-mars.sender.warm` | rsync | 0.4291 | 1655 | 2217 |
| `large-text.fresh.mac-mars.sender.warm` | rsync-z | 0.3617 | 1176 | 1576 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z | 0.6321 | 3587 | 4807 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z1 | 0.8568 | 6590 | 8832 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 0.4857 | 2119 | 2839 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync | 0.2675 | 644 | 863 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-z | 0.4391 | 1732 | 2321 |
