# T1e-recv-cap

Four or eight receiving workers on a 32-thread host make no-ops of real trees faster than sixteen, and nothing slower.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T112856Z-T1e-recv-cap.
- Valid blocks: 168. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.994 [0.985, 1.004] | 0.994 [0.985, 1.004] | 0.1958 | 1.0000 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 12 | 0.998 [0.986, 1.010] | 0.996 [0.986, 1.011] | 0.7139 | 1.0000 | equivalent |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 12 | 1.023 [0.988, 1.059] | 1.027 [0.983, 1.061] | 0.1777 | 1.0000 | inconclusive |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 12 | 1.013 [0.980, 1.048] | 1.011 [0.975, 1.053] | 0.3999 | 1.0000 | inconclusive |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.986 [0.977, 0.995] | 0.986 [0.976, 0.996] | 0.0093 | 0.2134 | equivalent |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv8 | 12 | 0.990 [0.982, 0.997] | 0.989 [0.982, 0.998] | 0.0122 | 0.2686 | equivalent |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv4 | 12 | 0.989 [0.964, 1.014] | 0.990 [0.963, 1.014] | 0.3433 | 1.0000 | inconclusive |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv8 | 12 | 1.008 [0.983, 1.034] | 1.007 [0.981, 1.035] | 0.5093 | 1.0000 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 12 | 1.075 [0.855, 1.353] | 1.055 [0.926, 1.160] | 0.5449 | 1.0000 | inconclusive |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 12 | 0.941 [0.844, 1.048] | 0.964 [0.850, 1.045] | 0.2520 | 1.0000 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | recv4 | 12 | 1.006 [0.924, 1.096] | 0.999 [0.923, 1.090] | 0.8735 | 1.0000 | inconclusive |
| `small-deep.noop.neo-freya.sender.warm` | recv8 | 12 | 0.987 [0.948, 1.028] | 0.987 [0.939, 1.035] | 0.4927 | 1.0000 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.952 [0.934, 0.971] | 0.952 [0.930, 0.972] | 0.0005 | 0.0137 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 12 | 0.993 [0.973, 1.014] | 0.994 [0.969, 1.018] | 0.4814 | 1.0000 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 12 | 1.033 [0.931, 1.146] | 1.038 [0.929, 1.167] | 0.5078 | 1.0000 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 12 | 1.091 [0.962, 1.238] | 1.126 [0.959, 1.231] | 0.1548 | 1.0000 | inconclusive |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.955 [0.942, 0.969] | 0.954 [0.941, 0.971] | 0.0005 | 0.0137 | faster |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 12 | 0.978 [0.963, 0.993] | 0.976 [0.961, 0.995] | 0.0122 | 0.2686 | inconclusive |
| `small-opaque.noop.neo-freya.sender.warm` | recv4 | 12 | 0.960 [0.872, 1.058] | 0.957 [0.864, 1.069] | 0.3687 | 1.0000 | inconclusive |
| `small-opaque.noop.neo-freya.sender.warm` | recv8 | 12 | 0.935 [0.865, 1.010] | 0.941 [0.857, 1.012] | 0.0830 | 1.0000 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.954 [0.905, 1.005] | 0.974 [0.967, 0.981] | 0.0005 | 0.0137 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 12 | 1.034 [0.966, 1.106] | 0.992 [0.983, 1.118] | 0.4980 | 1.0000 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 12 | 0.649 [0.562, 0.749] | 0.652 [0.546, 0.761] | 0.0005 | 0.0137 | faster |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 12 | 0.721 [0.621, 0.839] | 0.725 [0.601, 0.893] | 0.0010 | 0.0234 | faster |
| `tiny-one.fresh.neo-freya.sender.warm` | recv4 | 12 | 0.991 [0.964, 1.019] | 0.988 [0.963, 1.018] | 0.4785 | 1.0000 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | recv8 | 12 | 1.008 [0.989, 1.027] | 1.005 [0.984, 1.026] | 0.3711 | 1.0000 | equivalent |
| `tiny-one.noop.neo-freya.sender.warm` | recv4 | 12 | 0.987 [0.972, 1.003] | 0.987 [0.972, 1.003] | 0.0938 | 1.0000 | equivalent |
| `tiny-one.noop.neo-freya.sender.warm` | recv8 | 12 | 1.025 [0.995, 1.056] | 1.022 [0.998, 1.057] | 0.0952 | 1.0000 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 0.969 [0.954, 0.985] | 0.994 [0.985, 1.004] | 1.000 [0.995, 1.005] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.970 [0.946, 0.994] | 0.998 [0.986, 1.010] | 0.997 [0.991, 1.003] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 0.883 [0.831, 0.939] | 1.038 [0.986, 1.093] | 0.717 [0.704, 0.732] |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 0.931 [0.877, 0.988] | 1.013 [0.979, 1.048] | 0.709 [0.685, 0.734] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv4 | 0.978 [0.953, 1.004] | 0.985 [0.977, 0.994] | 1.002 [1.000, 1.005] |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv8 | 0.978 [0.960, 0.996] | 0.989 [0.982, 0.997] | 0.998 [0.996, 1.000] |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv4 | 0.750 [0.719, 0.783] | 0.990 [0.966, 1.015] | 0.744 [0.725, 0.764] |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv8 | 0.818 [0.792, 0.845] | 1.011 [0.987, 1.036] | 0.743 [0.727, 0.759] |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 0.741 [0.718, 0.764] | 1.088 [0.871, 1.361] | 0.917 [0.779, 1.081] |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 0.844 [0.815, 0.873] | 0.948 [0.854, 1.052] | 0.996 [0.841, 1.179] |
| `small-deep.noop.neo-freya.sender.warm` | recv4 | 0.571 [0.535, 0.609] | 1.007 [0.924, 1.096] | 1.032 [0.970, 1.098] |
| `small-deep.noop.neo-freya.sender.warm` | recv8 | 0.841 [0.816, 0.867] | 0.988 [0.949, 1.028] | 0.975 [0.885, 1.074] |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.984 [0.962, 1.006] | 0.947 [0.925, 0.969] | 0.897 [0.795, 1.012] |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 0.999 [0.975, 1.023] | 0.987 [0.968, 1.006] | 0.901 [0.745, 1.091] |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 1.035 [0.890, 1.203] | 1.045 [0.945, 1.157] | 0.589 [0.574, 0.604] |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 1.104 [0.931, 1.309] | 1.090 [0.962, 1.236] | 0.594 [0.581, 0.607] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 0.981 [0.960, 1.002] | 0.959 [0.940, 0.978] | 0.680 [0.503, 0.919] |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 0.980 [0.955, 1.006] | 0.977 [0.961, 0.994] | 0.833 [0.621, 1.116] |
| `small-opaque.noop.neo-freya.sender.warm` | recv4 | 0.962 [0.872, 1.060] | 0.961 [0.873, 1.058] | 0.587 [0.575, 0.600] |
| `small-opaque.noop.neo-freya.sender.warm` | recv8 | 0.903 [0.822, 0.992] | 0.935 [0.866, 1.010] | 0.585 [0.575, 0.595] |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.822 [0.809, 0.834] | 0.952 [0.904, 1.003] | 0.979 [0.951, 1.008] |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.921 [0.906, 0.936] | 1.032 [0.965, 1.105] | 0.994 [0.953, 1.037] |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 0.325 [0.305, 0.346] | 0.649 [0.563, 0.749] | 0.934 [0.864, 1.011] |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 0.594 [0.567, 0.622] | 0.722 [0.621, 0.839] | 0.968 [0.891, 1.051] |
| `tiny-one.fresh.neo-freya.sender.warm` | recv4 | 0.796 [0.759, 0.834] | 0.989 [0.963, 1.016] | 0.748 [0.734, 0.762] |
| `tiny-one.fresh.neo-freya.sender.warm` | recv8 | 0.822 [0.774, 0.874] | 1.007 [0.991, 1.024] | 0.743 [0.731, 0.756] |
| `tiny-one.noop.neo-freya.sender.warm` | recv4 | 0.747 [0.716, 0.779] | 0.987 [0.972, 1.003] | 0.731 [0.708, 0.754] |
| `tiny-one.noop.neo-freya.sender.warm` | recv8 | 0.816 [0.784, 0.849] | 1.025 [0.995, 1.056] | 0.730 [0.713, 0.746] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | recv4 | recv8 | xs |
|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.568 | 12.617 | 12.641 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | 0.196 | 0.194 | 0.192 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | 13.604 | 13.655 | 13.797 |
| `mixed-threshold.noop.neo-freya.sender.warm` | 0.161 | 0.164 | 0.163 |
| `small-deep.fresh.neo-freya.sender.warm` | 6.966 | 6.094 | 6.478 |
| `small-deep.noop.neo-freya.sender.warm` | 1.627 | 1.595 | 1.616 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.224 | 3.363 | 3.386 |
| `small-flat.noop.neo-freya.sender.warm` | 0.290 | 0.307 | 0.281 |
| `small-opaque.fresh.neo-freya.sender.warm` | 3.293 | 3.371 | 3.447 |
| `small-opaque.noop.neo-freya.sender.warm` | 0.295 | 0.287 | 0.307 |
| `small-real.fresh.neo-freya.sender.warm` | 10.867 | 11.777 | 11.393 |
| `small-real.noop.neo-freya.sender.warm` | 1.072 | 1.191 | 1.651 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.159 | 0.161 | 0.160 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.158 | 0.165 | 0.161 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv4 | 0.0147 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | recv8 | 0.0186 | 8 | 8 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv4 | 0.0550 | 30 | 39 |
| `mixed-bimodal.noop.neo-freya.sender.warm` | recv8 | 0.0527 | 27 | 36 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv4 | 0.0140 | 8 | 8 |
| `mixed-threshold.fresh.neo-freya.sender.warm` | recv8 | 0.0118 | 8 | 8 |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv4 | 0.0399 | 17 | 22 |
| `mixed-threshold.noop.neo-freya.sender.warm` | recv8 | 0.0398 | 17 | 22 |
| `small-deep.fresh.neo-freya.sender.warm` | recv4 | 0.3609 | 1171 | 1569 |
| `small-deep.fresh.neo-freya.sender.warm` | recv8 | 0.1700 | 262 | 350 |
| `small-deep.noop.neo-freya.sender.warm` | recv4 | 0.1343 | 164 | 219 |
| `small-deep.noop.neo-freya.sender.warm` | recv8 | 0.0632 | 38 | 51 |
| `small-flat.fresh.neo-freya.sender.warm` | recv4 | 0.0308 | 11 | 14 |
| `small-flat.fresh.neo-freya.sender.warm` | recv8 | 0.0323 | 12 | 15 |
| `small-flat.noop.neo-freya.sender.warm` | recv4 | 0.1635 | 242 | 324 |
| `small-flat.noop.neo-freya.sender.warm` | recv8 | 0.1986 | 356 | 477 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv4 | 0.0226 | 8 | 9 |
| `small-opaque.fresh.neo-freya.sender.warm` | recv8 | 0.0243 | 8 | 10 |
| `small-opaque.noop.neo-freya.sender.warm` | recv4 | 0.1527 | 212 | 283 |
| `small-opaque.noop.neo-freya.sender.warm` | recv8 | 0.1220 | 136 | 181 |
| `small-real.fresh.neo-freya.sender.warm` | recv4 | 0.0823 | 63 | 84 |
| `small-real.fresh.neo-freya.sender.warm` | recv8 | 0.1061 | 104 | 138 |
| `small-real.noop.neo-freya.sender.warm` | recv4 | 0.2257 | 460 | 615 |
| `small-real.noop.neo-freya.sender.warm` | recv8 | 0.2369 | 506 | 677 |
| `tiny-one.fresh.neo-freya.sender.warm` | recv4 | 0.0431 | 19 | 25 |
| `tiny-one.fresh.neo-freya.sender.warm` | recv8 | 0.0293 | 10 | 13 |
| `tiny-one.noop.neo-freya.sender.warm` | recv4 | 0.0246 | 8 | 10 |
| `tiny-one.noop.neo-freya.sender.warm` | recv8 | 0.0470 | 22 | 29 |
