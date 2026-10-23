# MM2b-local-laikav2

On the user's laikav2 project as it is on the Mac (6.5 GB, 13,246 files, mostly its Rust target folder, with hard links), rsync -a, xs-c++ -a -j4 and xs-rs -a -j4 differ by more than 5% in time to durable in some cell.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261022T114746Z-MM2b-local-laikav2.
- Valid blocks: 120. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-cpp | 20 | 0.487 [0.460, 0.515] | 0.495 [0.459, 0.506] | 0.0000 | faster |
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-rs | 20 | 0.488 [0.464, 0.513] | 0.496 [0.462, 0.507] | 0.0000 | faster |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-cpp | 20 | 0.483 [0.458, 0.509] | 0.493 [0.458, 0.517] | 0.0000 | faster |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-rs | 20 | 0.491 [0.467, 0.517] | 0.498 [0.465, 0.521] | 0.0000 | faster |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-cpp | 20 | 0.609 [0.578, 0.642] | 0.622 [0.609, 0.634] | 0.0000 | faster |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-rs | 20 | 0.541 [0.487, 0.601] | 0.529 [0.518, 0.544] | 0.0000 | faster |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-cpp | 20 | 0.700 [0.648, 0.755] | 0.711 [0.684, 0.750] | 0.0000 | faster |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-rs | 20 | 0.545 [0.501, 0.593] | 0.558 [0.529, 0.589] | 0.0000 | faster |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-cpp | 20 | 0.834 [0.784, 0.887] | 0.834 [0.780, 0.893] | 0.0000 | faster |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-rs | 20 | 1.162 [1.112, 1.214] | 1.160 [1.107, 1.207] | 0.0000 | slower |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-cpp | 20 | 0.849 [0.812, 0.887] | 0.848 [0.813, 0.885] | 0.0000 | faster |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-rs | 20 | 1.125 [1.076, 1.175] | 1.132 [1.074, 1.179] | 0.0001 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-cpp | 0.549 [0.538, 0.561] | 26.145 [25.046, 27.293] | 0.477 [0.450, 0.505] |
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-rs | 0.392 [0.382, 0.403] | 54.281 [52.781, 55.823] | 0.478 [0.455, 0.503] |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-cpp | 0.604 [0.591, 0.617] | 2.346 [2.296, 2.397] | 0.480 [0.455, 0.507] |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-rs | 0.450 [0.438, 0.463] | 3.726 [3.676, 3.777] | 0.488 [0.464, 0.514] |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-cpp | 1.371 [1.330, 1.413] | 1.521 [1.502, 1.540] | 0.550 [0.539, 0.561] |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-rs | 0.879 [0.851, 0.908] | 1.351 [1.334, 1.367] | 0.445 [0.424, 0.467] |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-cpp | 1.468 [1.388, 1.553] | 1.713 [1.655, 1.774] | 0.647 [0.590, 0.710] |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-rs | 0.868 [0.822, 0.916] | 1.645 [1.570, 1.723] | 0.464 [0.423, 0.509] |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-cpp | 1.873 [1.820, 1.929] | 3.573 [3.269, 3.905] | 0.824 [0.772, 0.879] |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-rs | 1.384 [1.356, 1.412] | 3.733 [3.577, 3.895] | 1.175 [1.121, 1.231] |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-cpp | 1.890 [1.845, 1.935] | 5.075 [4.427, 5.818] | 0.842 [0.801, 0.886] |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-rs | 1.200 [1.185, 1.215] | 3.814 [3.685, 3.947] | 1.136 [1.083, 1.191] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-cpp | xs-rs |
|---|---|---|---|
| `local-laikav2.fresh.mac-mars.sender.warm` | 19.798 | 9.639 | 9.655 |
| `local-laikav2.fresh.mars-mac.receiver.warm` | 22.411 | 10.822 | 11.008 |
| `local-laikav2.noop.mac-mars.sender.warm` | 0.532 | 0.324 | 0.288 |
| `local-laikav2.noop.mars-mac.receiver.warm` | 0.508 | 0.355 | 0.277 |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | 1.445 | 1.205 | 1.678 |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | 1.456 | 1.236 | 1.638 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-cpp | 0.1190 | 130 | 173 |
| `local-laikav2.fresh.mac-mars.sender.warm` | xs-rs | 0.1067 | 105 | 139 |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-cpp | 0.1144 | 120 | 160 |
| `local-laikav2.fresh.mars-mac.receiver.warm` | xs-rs | 0.1091 | 109 | 146 |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-cpp | 0.1113 | 114 | 152 |
| `local-laikav2.noop.mac-mars.sender.warm` | xs-rs | 0.2265 | 463 | 619 |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-cpp | 0.1625 | 239 | 320 |
| `local-laikav2.noop.mars-mac.receiver.warm` | xs-rs | 0.1808 | 296 | 396 |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-cpp | 0.1313 | 157 | 210 |
| `local-laikav2.update-10pct.mac-mars.sender.warm` | xs-rs | 0.0937 | 81 | 108 |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-cpp | 0.0942 | 82 | 109 |
| `local-laikav2.update-10pct.mars-mac.receiver.warm` | xs-rs | 0.0943 | 82 | 109 |
