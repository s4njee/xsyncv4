# Z1-10g-compress

xs -z delivers corpus data faster than xs without it on compressible trees, and faster than rsync -z.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T153158Z-Z1-10g-compress.
- Valid blocks: 6. Voided block attempts: 1.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-z | 1 | 0.521 |  |  | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-z1 | 1 | 0.540 |  |  | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | xs-z3 | 1 | 0.677 |  |  | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync | 1 | 1.684 |  |  | too few blocks |
| `large-half.fresh.mac-mars.sender.warm` | rsync-z | 1 | 3.128 |  |  | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z | 1 | 0.750 |  |  | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z1 | 1 | 0.734 |  |  | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z3 | 1 | 0.738 |  |  | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync | 1 | 4.988 |  |  | too few blocks |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-z | 1 | 2.439 |  |  | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z | 1 | 0.748 |  |  | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z1 | 1 | 0.430 |  |  | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 1 | 1.058 |  |  | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync | 1 | 2.046 |  |  | too few blocks |
| `large-text.fresh.mac-mars.sender.warm` | rsync-z | 1 | 3.322 |  |  | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z | 1 | 0.904 |  |  | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z1 | 1 | 0.455 |  |  | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 1 | 1.095 |  |  | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync | 1 | 4.079 |  |  | too few blocks |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-z | 1 | 2.515 |  |  | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z | 1 | 1.694 |  |  | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z1 | 1 | 0.869 |  |  | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z3 | 1 | 0.786 |  |  | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 1 | 3.510 |  |  | too few blocks |
| `real-congress.fresh.mac-mars.sender.warm` | rsync-z | 1 | 3.711 |  |  | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z | 1 | 0.808 |  |  | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z1 | 1 | 0.965 |  |  | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z3 | 1 | 0.664 |  |  | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 1 | 1.026 |  |  | too few blocks |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync-z | 1 | 0.802 |  |  | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | xs-z | 1.350 | 1.618 | 0.521 |
| `large-half.fresh.mac-mars.sender.warm` | xs-z1 | 1.363 | 1.645 | 0.540 |
| `large-half.fresh.mac-mars.sender.warm` | xs-z3 | 1.631 | 2.416 | 0.677 |
| `large-half.fresh.mac-mars.sender.warm` | rsync | 1.810 | 0.093 | 1.685 |
| `large-half.fresh.mac-mars.sender.warm` | rsync-z | 2.883 | 0.093 | 3.129 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z | 1.246 | 1.646 | 0.747 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z1 | 1.266 | 1.642 | 0.731 |
| `large-half.fresh.mars-mac.receiver.warm` | xs-z3 | 1.380 | 2.298 | 0.736 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync | 1.741 | 1.345 | 5.002 |
| `large-half.fresh.mars-mac.receiver.warm` | rsync-z | 1.729 | 1.352 | 2.443 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z | 1.777 | 2.325 | 0.747 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z1 | 1.716 | 2.076 | 0.430 |
| `large-text.fresh.mac-mars.sender.warm` | xs-z3 | 2.307 | 2.774 | 1.058 |
| `large-text.fresh.mac-mars.sender.warm` | rsync | 1.877 | 0.104 | 2.047 |
| `large-text.fresh.mac-mars.sender.warm` | rsync-z | 3.238 | 0.103 | 3.324 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z | 1.561 | 1.724 | 0.903 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z1 | 1.512 | 1.691 | 0.452 |
| `large-text.fresh.mars-mac.receiver.warm` | xs-z3 | 1.806 | 2.351 | 1.095 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync | 1.884 | 1.415 | 4.089 |
| `large-text.fresh.mars-mac.receiver.warm` | rsync-z | 2.095 | 1.428 | 2.518 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z | 0.974 | 0.483 | 1.696 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z1 | 0.944 | 0.522 | 0.872 |
| `real-congress.fresh.mac-mars.sender.warm` | xs-z3 | 0.996 | 1.035 | 0.781 |
| `real-congress.fresh.mac-mars.sender.warm` | rsync | 1.030 | 0.144 | 3.523 |
| `real-congress.fresh.mac-mars.sender.warm` | rsync-z | 1.017 | 0.142 | 3.726 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z | 0.977 | 0.562 | 0.808 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z1 | 1.015 | 0.574 | 0.965 |
| `real-congress.fresh.mars-mac.receiver.warm` | xs-z3 | 0.966 | 0.583 | 0.664 |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync | 0.870 | 1.379 | 1.026 |
| `real-congress.fresh.mars-mac.receiver.warm` | rsync-z | 0.680 | 0.192 | 0.802 |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | rsync-z | xs | xs-z | xs-z1 | xs-z3 |
|---|---|---|---|---|---|---|
| `large-half.fresh.mac-mars.sender.warm` | 41.393 | 76.856 | 24.574 | 12.815 | 13.282 | 16.640 |
| `large-half.fresh.mars-mac.receiver.warm` | 58.635 | 28.676 | 11.755 | 8.813 | 8.625 | 8.676 |
| `large-text.fresh.mac-mars.sender.warm` | 44.927 | 72.945 | 21.956 | 16.413 | 9.450 | 23.226 |
| `large-text.fresh.mars-mac.receiver.warm` | 52.308 | 32.254 | 12.824 | 11.594 | 5.829 | 14.041 |
| `real-congress.fresh.mac-mars.sender.warm` | 66.737 | 70.568 | 19.014 | 32.210 | 16.516 | 14.942 |
| `real-congress.fresh.mars-mac.receiver.warm` | 93.312 | 72.921 | 90.973 | 73.483 | 87.748 | 60.424 |

## Voided attempts

- stopped
