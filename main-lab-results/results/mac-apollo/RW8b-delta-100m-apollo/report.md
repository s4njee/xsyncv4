# RW8b-delta-100m-apollo

Over a 20 ms, 100 Mb/s path, rsync is at least 5% faster than xs in some delta cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T201557Z-RW8b-delta-100m-apollo.
- Valid blocks: 8. Voided block attempts: 0.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 1.938 [1.917, 1.960] | 1.938 | 0.5000 | too few blocks |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.252 [1.107, 1.416] | 1.252 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 2.136 [0.036, 125.187] | 2.136 | 0.5000 | too few blocks |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 1.036 [0.070, 15.387] | 1.036 | 1.0000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 2 | 2.224 [1.822, 2.717] | 2.224 | 0.5000 | too few blocks |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 2 | 1.176 [1.059, 1.305] | 1.176 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 2 | 0.755 [0.716, 0.797] | 0.755 | 0.5000 | too few blocks |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 2 | 0.675 [0.016, 28.587] | 0.675 | 0.5000 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.507 [1.369, 1.659] | 0.998 [0.972, 1.024] | 1.977 [1.821, 2.146] |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 1.123 [0.922, 1.368] | 1.000 [0.997, 1.003] | 1.264 [1.041, 1.535] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 1.589 [1.070, 2.361] | 0.990 [0.867, 1.131] | 2.139 [0.036, 126.269] |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 1.171 [1.159, 1.183] | 0.988 [0.980, 0.996] | 1.036 [0.069, 15.508] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 1.443 [1.178, 1.769] | 0.986 [0.823, 1.182] | 2.266 [1.910, 2.689] |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 1.128 [0.985, 1.292] | 0.993 [0.937, 1.052] | 1.182 [1.062, 1.316] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.999 [0.281, 3.560] | 0.984 [0.786, 1.231] | 0.742 [0.584, 0.944] |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.949 [0.231, 3.899] | 0.973 [0.769, 1.230] | 0.676 [0.016, 28.011] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | 1.833 | 3.553 | 2.296 |
| `large-text.append-1pct.mac-apollo.sender.warm` | 2.506 | 5.353 | 2.596 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | 1.770 | 3.938 | 2.081 |
| `large-text.update-1pct.mac-apollo.sender.warm` | 6.054 | 4.574 | 4.086 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0012 | 8 | 8 |
| `large-text.append-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0137 | 8 | 8 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-cpp | 0.4531 | 1844 | 2471 |
| `large-text.append-1pct.mac-apollo.sender.warm` | xs-rs | 0.3003 | 812 | 1087 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-cpp | 0.0222 | 8 | 8 |
| `large-text.update-1pct.apollo-mac.receiver.warm` | xs-rs | 0.0116 | 8 | 8 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-cpp | 0.0059 | 8 | 8 |
| `large-text.update-1pct.mac-apollo.sender.warm` | xs-rs | 0.4170 | 1562 | 2093 |
