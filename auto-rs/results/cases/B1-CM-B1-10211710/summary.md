# B1: Re-measure no-op syncs

A measurement designed by Claude Opus 5.5 for this node, run 20261021T221144Z-CM-B1-10211710 (failed): xs-rs still takes longer than rsync on congress no-op, especially on pull, and its CPU seconds far exceed rsync's on one end. Receiver-side CPU dominating, mostly on pull, would point at destination path walks (A3). Sender-side CPU dominating would point at file-list and stat cost (B2/B3). Little change from -j1 to -j8 would mean a serial bottleneck. The lab records total CPU per end, not the user/kernel split the node asks for, and cannot profile, so syscall-heavy and compute-heavy costs are not separated.

Time to durable, seconds, and CPU seconds in brackets (geometric means of the blocks):

| cell | rsync | xs-cpp-j4 | xs-rs-j1 | xs-rs-j4 | xs-rs-j8 |
|---|---|---|---|---|---|
| real-congress.noop.mac>mars | 6.48 (8.1) | 2.29 (11.5) | 3.36 (5.6) | 1.75 (7.7) | 1.61 (10.4) |
| real-congress.noop.mars>mac | 4.78 (7.1) | 2.69 (12.8) | 2.79 (5.7) | 1.47 (7.1) | 1.28 (9.4) |
| real-psample.noop.mac>mars | 88.13 (87.7) | 26.98 (141.1) | 37.09 (52.7) | 20.39 (84.1) | 16.28 (113.5) |
| real-psample.noop.mars>mac | 75.72 (73.6) | 151.59 (273.3) | 62.08 (74.0) | 45.42 (97.0) | 14.47 (116.7) |
