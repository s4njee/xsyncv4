# CM-B1-10211710

xs-rs still takes longer than rsync on congress no-op, especially on pull, and its CPU seconds far exceed rsync's on one end. Receiver-side CPU dominating, mostly on pull, would point at destination path walks (A3). Sender-side CPU dominating would point at file-list and stat cost (B2/B3). Little change from -j1 to -j8 would mean a serial bottleneck. The lab records total CPU per end, not the user

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T221144Z-CM-B1-10211710.
- Valid blocks: 37. Voided block attempts: 10.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j4 | 10 | 0.269 [0.235, 0.309] | 0.277 [0.231, 0.320] | 0.0020 | faster |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j1 | 10 | 0.519 [0.470, 0.573] | 0.522 [0.466, 0.576] | 0.0020 | faster |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j8 | 10 | 0.249 [0.229, 0.270] | 0.246 [0.229, 0.271] | 0.0020 | faster |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp-j4 | 10 | 0.353 [0.320, 0.390] | 0.354 [0.322, 0.388] | 0.0020 | faster |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j4 | 10 | 0.308 [0.262, 0.361] | 0.314 [0.245, 0.367] | 0.0020 | faster |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j1 | 10 | 0.584 [0.466, 0.731] | 0.566 [0.460, 0.806] | 0.0039 | faster |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j8 | 10 | 0.268 [0.246, 0.293] | 0.267 [0.247, 0.292] | 0.0020 | faster |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 10 | 0.562 [0.496, 0.638] | 0.576 [0.465, 0.639] | 0.0020 | faster |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j4 | 8 | 0.231 [0.219, 0.245] | 0.230 [0.220, 0.248] | 0.0078 | faster |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j1 | 8 | 0.421 [0.396, 0.447] | 0.429 [0.390, 0.440] | 0.0078 | faster |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j8 | 8 | 0.185 [0.174, 0.196] | 0.185 [0.174, 0.197] | 0.0078 | faster |
| `real-psample.noop.mac-mars.sender.warm` | xs-cpp-j4 | 8 | 0.306 [0.284, 0.329] | 0.303 [0.285, 0.332] | 0.0078 | faster |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j4 | 9 | 0.600 [0.213, 1.689] | 0.612 [0.204, 2.127] | 0.3008 | inconclusive |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j1 | 9 | 0.820 [0.317, 2.121] | 0.577 [0.371, 2.338] | 0.6445 | inconclusive |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j8 | 9 | 0.191 [0.147, 0.249] | 0.202 [0.147, 0.245] | 0.0039 | faster |
| `real-psample.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 9 | 2.002 [0.912, 4.393] | 2.112 [0.884, 5.320] | 0.1055 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j4 | 0.957 [0.913, 1.002] | 3.798 [3.535, 4.081] | 0.256 [0.221, 0.297] |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j1 | 0.691 [0.664, 0.719] | 3.847 [3.587, 4.124] | 0.508 [0.457, 0.564] |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j8 | 1.280 [1.212, 1.352] | 3.874 [3.600, 4.168] | 0.235 [0.214, 0.259] |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp-j4 | 1.418 [1.358, 1.481] | 1.812 [1.542, 2.130] | 0.329 [0.297, 0.364] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j4 | 1.002 [0.951, 1.056] | 5.061 [4.476, 5.721] | 0.296 [0.252, 0.348] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j1 | 0.799 [0.716, 0.891] | 4.894 [4.415, 5.424] | 0.578 [0.460, 0.726] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j8 | 1.317 [1.253, 1.384] | 5.292 [4.772, 5.870] | 0.257 [0.234, 0.281] |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 1.801 [1.689, 1.920] | 2.768 [2.227, 3.440] | 0.555 [0.488, 0.632] |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j4 | 0.960 [0.907, 1.015] | 5.909 [5.302, 6.584] | 0.230 [0.217, 0.244] |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j1 | 0.601 [0.571, 0.633] | 6.130 [5.643, 6.659] | 0.419 [0.395, 0.444] |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j8 | 1.295 [1.215, 1.380] | 5.730 [5.344, 6.145] | 0.183 [0.173, 0.195] |
| `real-psample.noop.mac-mars.sender.warm` | xs-cpp-j4 | 1.609 [1.503, 1.723] | 3.443 [3.160, 3.750] | 0.305 [0.283, 0.328] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j4 | 1.317 [1.141, 1.521] | 7.864 [7.346, 8.418] | 0.599 [0.212, 1.689] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j1 | 1.005 [0.736, 1.372] | 7.737 [7.184, 8.334] | 0.820 [0.317, 2.122] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j8 | 1.585 [1.504, 1.669] | 8.022 [7.592, 8.477] | 0.190 [0.146, 0.248] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 3.712 [3.321, 4.148] | 4.096 [3.731, 4.496] | 2.003 [0.912, 4.396] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp-j4 | xs-rs-j1 | xs-rs-j4 | xs-rs-j8 |
|---|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | 6.482 | 2.289 | 3.363 | 1.747 | 1.612 |
| `real-congress.noop.mars-mac.receiver.warm` | 4.775 | 2.685 | 2.787 | 1.468 | 1.281 |
| `real-psample.noop.mac-mars.sender.warm` | 88.126 | 26.981 | 37.087 | 20.395 | 16.281 |
| `real-psample.noop.mars-mac.receiver.warm` | 75.716 | 151.6 | 62.081 | 45.418 | 14.469 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j4 | 0.1895 | 325 | 435 |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j1 | 0.1379 | 173 | 231 |
| `real-congress.noop.mac-mars.sender.warm` | xs-rs-j8 | 0.1177 | 127 | 169 |
| `real-congress.noop.mac-mars.sender.warm` | xs-cpp-j4 | 0.1390 | 176 | 235 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j4 | 0.2229 | 448 | 600 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j1 | 0.3138 | 886 | 1187 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-rs-j8 | 0.1234 | 139 | 186 |
| `real-congress.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 0.1767 | 283 | 378 |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j4 | 0.0681 | 44 | 58 |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j1 | 0.0722 | 49 | 65 |
| `real-psample.noop.mac-mars.sender.warm` | xs-rs-j8 | 0.0707 | 47 | 63 |
| `real-psample.noop.mac-mars.sender.warm` | xs-cpp-j4 | 0.0879 | 72 | 95 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j4 | 1.3470 | 16284 | 21824 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j1 | 1.2364 | 13720 | 18387 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-rs-j8 | 0.3449 | 1070 | 1433 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-cpp-j4 | 1.0223 | 9380 | 12570 |

## Voided attempts

- rsync: harness error: mars: `find /Volumes/xsbench/lab/corpora/real-psample -type f -exec cat {} + > /dev/null` exited 255: 
- voided afterwards: the compression study ran disk and loopback transfers on the Mac 06:10-06:15Z, CPU about 87% busy; rsync took 105 s against 81-97 s in blocks
- xs-rs-j1: the peer process failed or left no metrics
- xs-rs-j4: the peer process failed or left no metrics
- xs-rs-j8: the peer process failed or left no metrics
