# AP10211357-L2B1-lab2-build-small-fresh

0c94b3d70b9d is within 5% of e51c1df1329a and still well ahead of rsync -a on small-flat and mixed-bimodal fresh copies, so the build difference does not explain lab2's losses; -j2 is no faster than -j4.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-lab2`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T135748Z-AP10211357-L2B1-lab2-build-small-fresh.
- Valid blocks: 20. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-home | 10 | 0.940 [0.783, 1.127] | 0.971 [0.772, 1.114] | 0.5215 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 10 | 1.033 [0.801, 1.334] | 0.965 [0.843, 1.406] | 0.8828 | inconclusive |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 10 | 1.637 [1.430, 1.873] | 1.610 [1.418, 1.852] | 0.0020 | slower |
| `small-flat.fresh.mac-mars.sender.warm` | xs-home | 10 | 0.978 [0.929, 1.029] | 0.977 [0.935, 1.019] | 0.3594 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 10 | 0.997 [0.941, 1.057] | 0.993 [0.938, 1.050] | 0.9121 | inconclusive |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 10 | 1.365 [1.246, 1.496] | 1.370 [1.247, 1.492] | 0.0020 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-home | 0.988 [0.929, 1.050] | 0.973 [0.919, 1.030] | 0.942 [0.784, 1.131] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 0.957 [0.922, 0.993] | 0.970 [0.924, 1.018] | 1.015 [0.789, 1.307] |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 1.348 [1.287, 1.413] | 0.050 [0.049, 0.052] | 1.653 [1.447, 1.888] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-home | 0.988 [0.957, 1.021] | 1.010 [0.969, 1.052] | 0.980 [0.938, 1.024] |
| `small-flat.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 0.946 [0.915, 0.978] | 0.872 [0.816, 0.932] | 0.998 [0.948, 1.050] |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 1.138 [1.082, 1.198] | 0.064 [0.062, 0.066] | 1.370 [1.253, 1.497] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs-home | xs-lab2 | xs-lab2-j2 |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | 8.317 | 4.774 | 5.081 | 5.251 |
| `small-flat.fresh.mac-mars.sender.warm` | 20.784 | 14.885 | 15.224 | 15.181 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-home | 0.2546 | 584 | 782 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 0.3567 | 1144 | 1533 |
| `mixed-bimodal.fresh.mac-mars.sender.warm` | rsync | 0.1885 | 321 | 430 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-home | 0.0719 | 49 | 65 |
| `small-flat.fresh.mac-mars.sender.warm` | xs-lab2-j2 | 0.0811 | 61 | 82 |
| `small-flat.fresh.mac-mars.sender.warm` | rsync | 0.1280 | 150 | 200 |
