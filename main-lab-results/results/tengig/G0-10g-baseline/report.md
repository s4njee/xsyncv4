# G0-10g-baseline

xs uses at least 80% of the 10GbE link for large files both ways, and more of it than rsync on every tree.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261017T020249Z-G0-10g-baseline, 20261017T121630Z-G0-10g-baseline.
- Valid blocks: 64. Voided block attempts: 1.
- **The runs were made from different versions of the spec.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | xs-best | 8 | 0.940 [0.854, 1.036] | 0.955 [0.851, 1.027] | 0.1406 | inconclusive |
| `large-text.fresh.freya-mac.receiver.warm` | rsync | 8 | 2.896 [2.363, 3.550] | 2.903 [2.307, 3.561] | 0.0078 | slower |
| `large-text.fresh.mac-freya.sender.warm` | xs-best | 8 | 1.031 [0.986, 1.078] | 1.023 [0.985, 1.087] | 0.1875 | inconclusive |
| `large-text.fresh.mac-freya.sender.warm` | rsync | 8 | 2.444 [2.183, 2.735] | 2.460 [2.162, 2.806] | 0.0078 | slower |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | xs-best | 8 | 0.659 [0.574, 0.758] | 0.665 [0.550, 0.769] | 0.0078 | faster |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | rsync | 8 | 2.015 [1.860, 2.182] | 2.057 [1.810, 2.162] | 0.0078 | slower |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | xs-best | 8 | 1.104 [1.006, 1.212] | 1.092 [1.009, 1.216] | 0.0312 | inconclusive |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | rsync | 8 | 3.285 [2.633, 4.098] | 3.273 [2.641, 4.172] | 0.0078 | slower |
| `real-congress.fresh.freya-mac.receiver.warm` | xs-best | 8 | 0.687 [0.628, 0.752] | 0.685 [0.627, 0.757] | 0.0078 | faster |
| `real-congress.fresh.freya-mac.receiver.warm` | rsync | 8 | 1.112 [0.885, 1.398] | 1.028 [0.911, 1.374] | 0.3984 | inconclusive |
| `real-congress.fresh.mac-freya.sender.warm` | xs-best | 8 | 0.990 [0.858, 1.142] | 1.012 [0.820, 1.136] | 0.8828 | inconclusive |
| `real-congress.fresh.mac-freya.sender.warm` | rsync | 8 | 4.292 [3.662, 5.029] | 4.242 [3.597, 5.041] | 0.0078 | slower |
| `small-flat.fresh.freya-mac.receiver.warm` | xs-best | 8 | 0.590 [0.526, 0.661] | 0.578 [0.525, 0.673] | 0.0078 | faster |
| `small-flat.fresh.freya-mac.receiver.warm` | rsync | 8 | 1.304 [1.115, 1.525] | 1.332 [1.119, 1.599] | 0.0078 | slower |
| `small-flat.fresh.mac-freya.sender.warm` | xs-best | 8 | 0.707 [0.593, 0.842] | 0.681 [0.599, 0.887] | 0.0156 | faster |
| `small-flat.fresh.mac-freya.sender.warm` | rsync | 8 | 1.712 [1.031, 2.845] | 1.411 [1.140, 2.998] | 0.0078 | slower |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | xs-best | 1.001 [0.971, 1.031] | 0.939 [0.856, 1.029] | 0.940 [0.853, 1.036] |
| `large-text.fresh.freya-mac.receiver.warm` | rsync | 1.508 [1.379, 1.649] | 1.387 [1.275, 1.509] | 2.907 [2.370, 3.566] |
| `large-text.fresh.mac-freya.sender.warm` | xs-best | 1.006 [0.995, 1.018] | 0.977 [0.908, 1.050] | 1.033 [0.990, 1.078] |
| `large-text.fresh.mac-freya.sender.warm` | rsync | 1.677 [1.538, 1.829] | 0.080 [0.074, 0.086] | 2.450 [2.193, 2.736] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | xs-best | 0.840 [0.817, 0.864] | 0.981 [0.936, 1.028] | 0.660 [0.573, 0.761] |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | rsync | 1.141 [1.099, 1.185] | 1.438 [1.326, 1.560] | 2.041 [1.883, 2.212] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | xs-best | 0.959 [0.927, 0.991] | 1.010 [0.976, 1.044] | 1.105 [1.003, 1.216] |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | rsync | 1.316 [1.130, 1.533] | 0.062 [0.059, 0.065] | 3.309 [2.651, 4.131] |
| `real-congress.fresh.freya-mac.receiver.warm` | xs-best | 0.816 [0.782, 0.851] | 1.081 [0.929, 1.259] | 0.687 [0.628, 0.753] |
| `real-congress.fresh.freya-mac.receiver.warm` | rsync | 0.882 [0.749, 1.038] | 1.374 [1.150, 1.643] | 1.113 [0.884, 1.400] |
| `real-congress.fresh.mac-freya.sender.warm` | xs-best | 0.855 [0.799, 0.915] | 1.006 [0.799, 1.266] | 0.986 [0.851, 1.141] |
| `real-congress.fresh.mac-freya.sender.warm` | rsync | 0.745 [0.682, 0.813] | 0.114 [0.103, 0.126] | 4.344 [3.705, 5.095] |
| `small-flat.fresh.freya-mac.receiver.warm` | xs-best | 0.676 [0.641, 0.712] | 0.991 [0.908, 1.080] | 0.592 [0.527, 0.664] |
| `small-flat.fresh.freya-mac.receiver.warm` | rsync | 1.068 [0.948, 1.203] | 1.611 [1.453, 1.787] | 1.309 [1.118, 1.532] |
| `small-flat.fresh.mac-freya.sender.warm` | xs-best | 0.883 [0.835, 0.934] | 0.586 [0.386, 0.889] | 0.708 [0.588, 0.852] |
| `small-flat.fresh.mac-freya.sender.warm` | rsync | 0.659 [0.517, 0.840] | 0.103 [0.068, 0.158] | 1.746 [1.032, 2.953] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-best |
|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | 31.623 | 10.919 | 10.268 |
| `large-text.fresh.mac-freya.sender.warm` | 25.782 | 10.550 | 10.877 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | 10.573 | 5.248 | 3.459 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | 6.780 | 2.064 | 2.279 |
| `real-congress.fresh.freya-mac.receiver.warm` | 60.351 | 54.255 | 37.278 |
| `real-congress.fresh.mac-freya.sender.warm` | 41.813 | 9.743 | 9.645 |
| `small-flat.fresh.freya-mac.receiver.warm` | 25.606 | 19.636 | 11.588 |
| `small-flat.fresh.mac-freya.sender.warm` | 6.610 | 3.860 | 2.727 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `large-text.fresh.freya-mac.receiver.warm` | xs-best | 0.1155 | 122 | 163 |
| `large-text.fresh.freya-mac.receiver.warm` | rsync | 0.2435 | 535 | 716 |
| `large-text.fresh.mac-freya.sender.warm` | xs-best | 0.0530 | 28 | 36 |
| `large-text.fresh.mac-freya.sender.warm` | rsync | 0.1348 | 166 | 221 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | xs-best | 0.1664 | 251 | 336 |
| `mixed-bimodal.fresh.freya-mac.receiver.warm` | rsync | 0.0955 | 84 | 112 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | xs-best | 0.1114 | 114 | 152 |
| `mixed-bimodal.fresh.mac-freya.sender.warm` | rsync | 0.2647 | 631 | 845 |
| `real-congress.fresh.freya-mac.receiver.warm` | xs-best | 0.1083 | 108 | 144 |
| `real-congress.fresh.freya-mac.receiver.warm` | rsync | 0.2734 | 673 | 901 |
| `real-congress.fresh.mac-freya.sender.warm` | xs-best | 0.1707 | 264 | 353 |
| `real-congress.fresh.mac-freya.sender.warm` | rsync | 0.1897 | 325 | 435 |
| `small-flat.fresh.freya-mac.receiver.warm` | xs-best | 0.1365 | 170 | 227 |
| `small-flat.fresh.freya-mac.receiver.warm` | rsync | 0.1868 | 316 | 422 |
| `small-flat.fresh.mac-freya.sender.warm` | xs-best | 0.2105 | 400 | 535 |
| `small-flat.fresh.mac-freya.sender.warm` | rsync | 0.6072 | 3311 | 4436 |

## Voided attempts

- stopped
