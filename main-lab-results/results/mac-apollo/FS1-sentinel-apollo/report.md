# FS1-sentinel-apollo

rsync, xs-c++ and xs-rs keep their congress ranking through the weekend.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T232159Z-FS1-sentinel-apollo, 20261023T233649Z-FS1-sentinel-apollo, 20261023T235157Z-FS1-sentinel-apollo, 20261024T000710Z-FS1-sentinel-apollo, 20261024T002223Z-FS1-sentinel-apollo, 20261024T003754Z-FS1-sentinel-apollo, 20261024T005242Z-FS1-sentinel-apollo, 20261024T010733Z-FS1-sentinel-apollo.
- Valid blocks: 32. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 8 | 0.304 [0.294, 0.315] | 0.305 [0.292, 0.315] | 0.0078 | faster |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 8 | 0.301 [0.296, 0.306] | 0.301 [0.296, 0.307] | 0.0078 | faster |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 8 | 0.298 [0.215, 0.414] | 0.296 [0.219, 0.456] | 0.0078 | faster |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 8 | 0.293 [0.213, 0.403] | 0.304 [0.209, 0.451] | 0.0078 | faster |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 8 | 0.550 [0.502, 0.602] | 0.547 [0.502, 0.601] | 0.0078 | faster |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 8 | 0.317 [0.294, 0.343] | 0.315 [0.290, 0.346] | 0.0078 | faster |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 8 | 0.232 [0.202, 0.268] | 0.234 [0.200, 0.281] | 0.0078 | faster |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 8 | 0.206 [0.187, 0.227] | 0.210 [0.186, 0.225] | 0.0078 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.866 [0.848, 0.885] | 0.785 [0.719, 0.857] | 0.297 [0.286, 0.308] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.803 [0.788, 0.818] | 1.054 [0.959, 1.159] | 0.293 [0.288, 0.298] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.773 [0.757, 0.790] | 5.392 [4.250, 6.842] | 0.223 [0.209, 0.239] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.104 [0.990, 1.231] | 6.559 [6.142, 7.004] | 0.214 [0.183, 0.250] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 2.081 [2.019, 2.145] | 2.718 [2.300, 3.213] | 0.542 [0.495, 0.593] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 1.236 [1.193, 1.281] | 6.805 [5.803, 7.981] | 0.306 [0.282, 0.331] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 1.116 [1.062, 1.174] | 3.053 [2.966, 3.142] | 0.232 [0.201, 0.267] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.387 [1.312, 1.467] | 8.340 [8.113, 8.574] | 0.206 [0.187, 0.227] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | 65.159 | 19.810 | 19.604 |
| `real-congress.fresh.mac-apollo.sender.warm` | 29.472 | 8.794 | 8.636 |
| `real-congress.noop.apollo-mac.receiver.warm` | 4.257 | 2.340 | 1.350 |
| `real-congress.noop.mac-apollo.sender.warm` | 6.210 | 1.443 | 1.280 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0409 | 18 | 23 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0199 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3903 | 1369 | 1835 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.3800 | 1298 | 1739 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 0.1082 | 108 | 143 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.0921 | 79 | 104 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.1693 | 260 | 347 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.1145 | 120 | 160 |
