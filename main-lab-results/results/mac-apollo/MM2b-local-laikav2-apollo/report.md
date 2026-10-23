# MM2b-local-laikav2-apollo

On the user's laikav2 project as it is on the Mac (6.5 GB, 13,246 files, mostly its Rust target folder, with hard links), rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T162409Z-MM2b-local-laikav2-apollo, 20261023T040629Z-MM2b-local-laikav2-apollo.
- Valid blocks: 114. Voided block attempts: 205.
- **The runs were made from different versions of the spec.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 19 | 0.372 [0.361, 0.383] | 0.377 [0.359, 0.385] | 0.0000 | faster |
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-rs | 19 | 0.362 [0.353, 0.371] | 0.364 [0.353, 0.372] | 0.0000 | faster |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 20 | 0.734 [0.613, 0.878] | 0.707 [0.612, 0.866] | 0.0026 | faster |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-rs | 20 | 0.665 [0.563, 0.785] | 0.675 [0.568, 0.757] | 0.0001 | faster |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 18 | 0.727 [0.691, 0.766] | 0.727 [0.694, 0.767] | 0.0000 | faster |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 18 | 0.646 [0.613, 0.680] | 0.642 [0.615, 0.681] | 0.0000 | faster |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 20 | 0.568 [0.404, 0.798] | 0.552 [0.511, 0.595] | 0.0015 | faster |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 20 | 0.454 [0.368, 0.561] | 0.487 [0.460, 0.523] | 0.0000 | faster |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 17 | 0.821 [0.771, 0.873] | 0.810 [0.769, 0.866] | 0.0001 | faster |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-rs | 17 | 1.164 [1.093, 1.239] | 1.172 [1.090, 1.237] | 0.0003 | slower |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-cpp | 20 | 0.712 [0.348, 1.454] | 0.672 [0.296, 1.589] | 0.3267 | inconclusive |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-rs | 20 | 0.887 [0.452, 1.740] | 1.058 [0.419, 2.053] | 0.7145 | inconclusive |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.719 [0.706, 0.732] | 0.752 [0.722, 0.783] | 0.368 [0.358, 0.379] |
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-rs | 0.445 [0.435, 0.455] | 1.403 [1.327, 1.482] | 0.358 [0.350, 0.367] |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.621 [0.599, 0.644] | 16.437 [13.319, 20.285] | 0.379 [0.355, 0.404] |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-rs | 0.309 [0.297, 0.321] | 31.549 [26.053, 38.205] | 0.379 [0.356, 0.403] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 1.837 [1.721, 1.960] | 1.017 [1.008, 1.027] | 0.670 [0.629, 0.714] |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 1.023 [0.966, 1.084] | 0.998 [0.986, 1.010] | 0.560 [0.522, 0.601] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 1.197 [1.154, 1.242] | 0.997 [0.989, 1.006] | 0.546 [0.527, 0.566] |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.905 [0.875, 0.937] | 0.997 [0.988, 1.005] | 0.476 [0.462, 0.489] |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 2.107 [2.028, 2.189] | 5.244 [4.388, 6.268] | 0.818 [0.768, 0.871] |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-rs | 1.325 [1.282, 1.369] | 2.223 [2.049, 2.412] | 1.187 [1.116, 1.263] |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.533 [1.474, 1.594] | 2.160 [1.918, 2.432] | 0.683 [0.369, 1.266] |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-rs | 1.442 [1.377, 1.511] | 2.592 [2.366, 2.839] | 0.924 [0.494, 1.731] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | 19.431 | 7.227 | 7.035 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | 25.371 | 18.618 | 16.866 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | 0.436 | 0.317 | 0.282 |
| `local-laikav2.noop.mac-apollo.sender.warm` | 0.446 | 0.253 | 0.203 |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | 1.460 | 1.198 | 1.699 |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | 2.068 | 1.472 | 1.834 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-cpp | 0.0600 | 35 | 46 |
| `local-laikav2.fresh.apollo-mac.receiver.warm` | xs-rs | 0.0506 | 26 | 33 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-cpp | 0.3842 | 1327 | 1778 |
| `local-laikav2.fresh.mac-apollo.sender.warm` | xs-rs | 0.3559 | 1139 | 1526 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-cpp | 0.1027 | 97 | 129 |
| `local-laikav2.noop.apollo-mac.receiver.warm` | xs-rs | 0.1038 | 99 | 132 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-cpp | 0.7267 | 4742 | 6354 |
| `local-laikav2.noop.mac-apollo.sender.warm` | xs-rs | 0.4500 | 1820 | 2438 |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-cpp | 0.1209 | 134 | 178 |
| `local-laikav2.update-10pct.apollo-mac.receiver.warm` | xs-rs | 0.1226 | 137 | 183 |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-cpp | 1.5257 | 20891 | 27998 |
| `local-laikav2.update-10pct.mac-apollo.sender.warm` | xs-rs | 1.4399 | 18607 | 24938 |

## Voided attempts

- mac reaches apollo by en4, not bridge100
- rsync: did not settle: apollo has 1056 MiB dirty
- rsync: did not settle: apollo has 1067 MiB dirty
- rsync: did not settle: apollo has 1559 MiB dirty
- rsync: did not settle: apollo has 184 MiB dirty
- rsync: did not settle: apollo has 266 MiB dirty
- rsync: did not settle: apollo has 607 MiB dirty
- rsync: did not settle: apollo has 736 MiB dirty
- rsync: did not settle: apollo has 82 MiB dirty
- rsync: did not settle: apollo has 893 MiB dirty
- xs-cpp: did not settle: apollo has 1072 MiB dirty
- xs-cpp: did not settle: apollo has 1358 MiB dirty
- xs-cpp: did not settle: apollo has 298 MiB dirty
- xs-cpp: did not settle: apollo has 361 MiB dirty
- xs-cpp: did not settle: apollo has 369 MiB dirty
- xs-cpp: did not settle: apollo has 418 MiB dirty
- xs-cpp: did not settle: apollo has 454 MiB dirty
- xs-cpp: did not settle: apollo has 685 MiB dirty
- xs-cpp: did not settle: apollo has 718 MiB dirty
- xs-cpp: did not settle: apollo has 747 MiB dirty
- xs-rs: did not settle: apollo has 1700 MiB dirty
- xs-rs: did not settle: apollo has 406 MiB dirty
- xs-rs: did not settle: apollo has 452 MiB dirty
- xs-rs: did not settle: apollo has 781 MiB dirty
- xs-rs: did not settle: apollo has 811 MiB dirty
- xs-rs: did not settle: apollo has 918 MiB dirty
