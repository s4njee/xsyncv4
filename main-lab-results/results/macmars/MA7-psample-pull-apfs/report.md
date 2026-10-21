# MA7-psample-pull-apfs

Skipping directory times, the rename, or giving the Mac receiver more workers or scanners recovers xs's psample pull onto APFS.

- Kind: screening. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261018T144803Z-MA7-psample-pull-apfs.
- Valid blocks: 6. Voided block attempts: 18.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `real-psample.noop.mars-mac.receiver.warm` | xs-O | 6 | 0.996 [0.974, 1.019] | 0.998 [0.963, 1.021] | 0.7188 | too few blocks |
| `real-psample.noop.mars-mac.receiver.warm` | xs-noatomic | 6 | 0.993 [0.967, 1.020] | 0.998 [0.951, 1.017] | 0.5625 | too few blocks |
| `real-psample.noop.mars-mac.receiver.warm` | xs-recv8 | 6 | 1.009 [0.994, 1.025] | 1.007 [0.995, 1.035] | 0.2188 | too few blocks |
| `real-psample.noop.mars-mac.receiver.warm` | xs-scan4 | 6 | 1.008 [0.987, 1.029] | 1.008 [0.978, 1.033] | 0.3750 | too few blocks |
| `real-psample.noop.mars-mac.receiver.warm` | rsync | 6 | 0.678 [0.659, 0.696] | 0.673 [0.657, 0.709] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `real-psample.noop.mars-mac.receiver.warm` | xs-O | 1.009 [0.997, 1.022] | 0.996 [0.975, 1.018] | 1.005 [0.877, 1.153] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-noatomic | 1.008 [0.996, 1.020] | 0.993 [0.968, 1.019] | 0.988 [0.905, 1.079] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-recv8 | 1.706 [1.669, 1.744] | 1.009 [0.994, 1.025] | 1.053 [0.944, 1.173] |
| `real-psample.noop.mars-mac.receiver.warm` | xs-scan4 | 1.002 [0.992, 1.011] | 1.008 [0.987, 1.030] | 0.990 [0.866, 1.132] |
| `real-psample.noop.mars-mac.receiver.warm` | rsync | 0.161 [0.158, 0.165] | 0.678 [0.660, 0.697] | 0.240 [0.205, 0.281] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-O | xs-noatomic | xs-recv8 | xs-scan4 |
|---|---|---|---|---|---|---|
| `real-psample.noop.mars-mac.receiver.warm` | 36.862 | 54.398 | 54.194 | 54.037 | 54.912 | 54.835 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `real-psample.noop.mars-mac.receiver.warm` | xs-O | 0.0211 | 8 | 8 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-noatomic | 0.0251 | 8 | 10 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-recv8 | 0.0149 | 8 | 8 |
| `real-psample.noop.mars-mac.receiver.warm` | xs-scan4 | 0.0201 | 8 | 8 |
| `real-psample.noop.mars-mac.receiver.warm` | rsync | 0.0260 | 9 | 11 |

## Voided attempts

- xs-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs
DIFFERS .xsyncv4-carryover/mac-root/runs/20261016T113150Z-R3-
- xs-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs/20261014T225217Z-X1a-large-one
DIFFERS .xsyncv4-carryover/mac
- xs-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs/20261015T100232Z-N2-nvme-small-read
DIFFERS blackbird/.git/ob
- xs-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs/20261016T162335Z-Z4-10g-codecs
DIFFERS audio/release/mac-arm6
- xs-O: the destination does not match the corpus manifest: DIFFERS .xsyncv4-carryover/mac-root/runs/20261017T005544Z-D1-mac-sender-knobs
DIFFERS audio/release/ma
- xs-O: the destination does not match the corpus manifest: DIFFERS audio/dist/textures
DIFFERS blackbird/.git/objects/24
DIFFERS blackbird/.git/objects/b5
DIFFER
- xs-O: the destination does not match the corpus manifest: DIFFERS audio/public/textures
DIFFERS blackbird/.git/objects/24
DIFFERS blackbird/.git/objects/36
DIFF
- xs-O: the destination does not match the corpus manifest: DIFFERS audio/release
DIFFERS blackbird/.git/objects/38
DIFFERS blackbird/.git/objects/58
DIFFERS blac
- xs-O: the destination does not match the corpus manifest: DIFFERS audio/src/modes
DIFFERS blackbird/.git/objects/c2
DIFFERS blackbird/web/src/lib
DIFFERS blog/.
- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird
DIFFERS blackbird/.git/objects/22
DIFFERS blackbird/.git/objects/2b
DIFFERS blackbir
- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/hooks
DIFFERS blackbird/.git/objects/4e
DIFFERS blackbird/.git/objects/8a
DIFFE
- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/07
DIFFERS blackbird/.git/objects/42
DIFFERS blackbird/.git/objects/5e

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/07
DIFFERS blackbird/.git/objects/42
DIFFERS blackbird/.git/objects/a7

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/0e
DIFFERS blackbird/.git/objects/2b
DIFFERS blackbird/.git/objects/9b

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/27
DIFFERS blackbird/.git/objects/88
DIFFERS blackbird/.git/objects/e2

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/34
DIFFERS blackbird/.git/objects/44
DIFFERS blackbird/.git/objects/45

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/45
DIFFERS blackbird/.git/objects/4d
DIFFERS blackbird/.git/objects/6b

- xs-O: the destination does not match the corpus manifest: DIFFERS blackbird/.git/objects/58
DIFFERS blackbird/.git/objects/5d
DIFFERS blackbird/.git/objects/61

