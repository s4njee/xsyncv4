# MA8-psample-pull-anchors

With a larger parent-descriptor budget, xs -aH re-syncs psample onto the Mac faster than its parent and than rsync -aH, at a no-op and after 1% of files change.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261019T132843Z-MA8-psample-pull-anchors.
- Valid blocks: 0. Voided block attempts: 1.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell |
|---|

## Voided attempts

- rsync: harness error: mac: `rsync -aH -e 'ssh -oBatchMode=yes -oCompression=no -oControlMaster=no -oConnectTimeout=10 -oHostKeyAlias=[host]' [user]@10.27.0.
