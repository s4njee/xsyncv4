# FS1-sentinel-apollo

rsync, xs-c++ and xs-rs keep their congress ranking through the weekend.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261023T232159Z-FS1-sentinel-apollo, 20261023T233649Z-FS1-sentinel-apollo, 20261023T235157Z-FS1-sentinel-apollo, 20261024T000710Z-FS1-sentinel-apollo, 20261024T002223Z-FS1-sentinel-apollo, 20261024T003754Z-FS1-sentinel-apollo, 20261024T005242Z-FS1-sentinel-apollo, 20261024T010733Z-FS1-sentinel-apollo, 20261025T114038Z-FS1-sentinel-apollo, 20261025T115549Z-FS1-sentinel-apollo.
- Valid blocks: 40. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.303 [0.295, 0.311] | 0.302 [0.295, 0.311] | 0.0020 | faster |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 10 | 0.301 [0.297, 0.305] | 0.301 [0.296, 0.306] | 0.0020 | faster |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 10 | 0.291 [0.226, 0.373] | 0.270 [0.224, 0.368] | 0.0020 | faster |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 10 | 0.343 [0.241, 0.489] | 0.319 [0.216, 0.476] | 0.0020 | faster |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 10 | 0.548 [0.512, 0.587] | 0.547 [0.507, 0.588] | 0.0020 | faster |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 10 | 0.314 [0.296, 0.334] | 0.311 [0.298, 0.334] | 0.0020 | faster |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 10 | 0.229 [0.205, 0.256] | 0.224 [0.206, 0.255] | 0.0020 | faster |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 10 | 0.208 [0.193, 0.225] | 0.212 [0.191, 0.223] | 0.0020 | faster |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.862 [0.846, 0.877] | 0.778 [0.720, 0.840] | 0.296 [0.287, 0.305] |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.800 [0.789, 0.812] | 1.058 [0.966, 1.158] | 0.293 [0.289, 0.296] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.776 [0.762, 0.789] | 5.560 [4.519, 6.839] | 0.224 [0.212, 0.236] |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 1.111 [1.022, 1.208] | 6.800 [6.278, 7.365] | 0.234 [0.191, 0.286] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 2.066 [2.012, 2.122] | 2.663 [2.331, 3.041] | 0.540 [0.504, 0.579] |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 1.220 [1.179, 1.262] | 6.600 [5.788, 7.525] | 0.302 [0.284, 0.322] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 1.128 [1.082, 1.175] | 3.054 [2.986, 3.124] | 0.229 [0.205, 0.255] |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 1.408 [1.342, 1.478] | 8.276 [8.068, 8.489] | 0.208 [0.193, 0.224] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | 66.015 | 19.983 | 19.853 |
| `real-congress.fresh.mac-apollo.sender.warm` | 28.754 | 8.357 | 9.875 |
| `real-congress.noop.apollo-mac.receiver.warm` | 4.270 | 2.340 | 1.342 |
| `real-congress.noop.mac-apollo.sender.warm` | 6.097 | 1.397 | 1.271 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0372 | 15 | 19 |
| `real-congress.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0193 | 8 | 8 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3490 | 1095 | 1467 |
| `real-congress.fresh.mac-apollo.sender.warm` | xs-rs | 0.4926 | 2180 | 2920 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-cpp | 0.0967 | 86 | 115 |
| `real-congress.noop.apollo-mac.receiver.warm` | xs-rs | 0.0845 | 67 | 88 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-cpp | 0.1529 | 212 | 284 |
| `real-congress.noop.mac-apollo.sender.warm` | xs-rs | 0.1042 | 100 | 133 |
