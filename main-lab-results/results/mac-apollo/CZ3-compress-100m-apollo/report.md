# CZ3-compress-100m-apollo

Held to 100 Mb/s, xs-rs -z at its automatic level is within 5% of the fastest fixed level, and compression beats none.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-rs-z`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261024T072401Z-CZ3-compress-100m-apollo.
- Valid blocks: 4. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 2 | 4.677 [4.218, 5.185] | 4.677 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 2 | 4.590 [3.987, 5.285] | 4.590 | 0.5000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 2 | 1.018 [0.793, 1.306] | 1.018 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 2 | 1.081 [0.342, 3.411] | 1.081 | 1.0000 | too few blocks |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z6 | 2 | 0.980 [0.575, 1.669] | 0.980 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 2 | 6.732 [5.230, 8.666] | 6.732 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 2 | 1.169 [0.014, 96.169] | 1.169 | 1.0000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 2 | 0.838 [0.405, 1.735] | 0.838 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 2 | 0.837 [0.697, 1.004] | 0.837 | 0.5000 | too few blocks |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z6 | 2 | 1.503 [0.320, 7.068] | 1.503 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 1.246 [0.544, 2.852] | 0.996 [0.925, 1.073] | 4.766 [3.981, 5.705] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 1.240 [0.573, 2.679] | 1.783 [0.372, 8.539] | 4.675 [4.329, 5.048] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.993 [0.883, 1.116] | 0.985 [0.873, 1.112] | 1.019 [0.686, 1.513] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 1.013 [0.766, 1.339] | 0.986 [0.725, 1.340] | 1.043 [0.460, 2.364] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z6 | 1.019 [0.920, 1.130] | 1.026 [0.876, 1.202] | 0.969 [0.669, 1.403] |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 1.283 [0.930, 1.769] | 0.127 [0.055, 0.292] | 7.860 [6.115, 10.104] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.010 [0.972, 1.050] | 1.000 [0.615, 1.624] | 0.979 [0.807, 1.188] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 1.001 [0.765, 1.310] | 0.966 [0.170, 5.495] | 0.977 [0.466, 2.048] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 1.028 [0.596, 1.775] | 1.050 [0.704, 1.566] | 0.929 [0.728, 1.184] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z6 | 1.110 [0.761, 1.621] | 0.972 [0.927, 1.020] | 0.898 [0.614, 1.312] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-rs | xs-rs-z | xs-rs-z1 | xs-rs-z3 | xs-rs-z6 |
|---|---|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | 101.5 | 99.647 | 21.709 | 22.097 | 23.464 | 21.275 |
| `real-congress.fresh.mac-apollo.sender.warm` | 99.477 | 17.276 | 14.776 | 12.386 | 12.361 | 22.211 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | rsync | 0.0115 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0157 | 8 | 8 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z1 | 0.0278 | 9 | 12 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z3 | 0.1279 | 149 | 199 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs-z6 | 0.0593 | 34 | 45 |
| `real-congress.fresh.mac-apollo.sender.warm` | rsync | 0.0281 | 10 | 12 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.4908 | 2164 | 2900 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z1 | 0.0810 | 61 | 81 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z3 | 0.0203 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs-z6 | 0.1723 | 269 | 360 |
