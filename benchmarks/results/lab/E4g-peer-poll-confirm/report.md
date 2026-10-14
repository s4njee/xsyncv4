# E4g-peer-poll-confirm

Polling for the peer's exit every 1 ms instead of 25 makes no-ops more than 3% faster and no transfer slower.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261014T020832Z-E4g-peer-poll-confirm.
- Valid blocks: 192. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | poll1 | 16 | 1.001 [0.987, 1.014] | 1.003 [0.987, 1.018] | 0.9337 | 1.0000 | equivalent |
| `small-flat.fresh.neo-freya.sender.warm` | poll1 | 16 | 1.004 [0.995, 1.014] | 1.005 [0.994, 1.014] | 0.3553 | 1.0000 | equivalent |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 16 | 0.956 [0.914, 1.000] | 0.958 [0.911, 1.001] | 0.0523 | 0.4710 | inconclusive |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 16 | 0.926 [0.856, 1.002] | 0.926 [0.844, 1.021] | 0.0570 | 0.4710 | inconclusive |
| `small-real.fresh.freya-neo.sender.warm` | poll1 | 16 | 1.003 [0.960, 1.047] | 1.004 [0.959, 1.053] | 0.8962 | 1.0000 | inconclusive |
| `small-real.fresh.neo-freya.sender.warm` | poll1 | 16 | 0.990 [0.796, 1.232] | 0.996 [0.942, 1.139] | 0.9067 | 1.0000 | inconclusive |
| `small-real.noop.freya-neo.sender.warm` | poll1 | 16 | 0.976 [0.873, 1.091] | 1.016 [0.963, 1.061] | 0.9096 | 1.0000 | inconclusive |
| `small-real.noop.neo-freya.sender.warm` | poll1 | 16 | 0.859 [0.744, 0.992] | 0.851 [0.726, 1.001] | 0.0421 | 0.4214 | inconclusive |
| `tiny-one.fresh.freya-neo.sender.warm` | poll1 | 16 | 0.967 [0.928, 1.007] | 0.967 [0.926, 1.011] | 0.1021 | 0.7144 | inconclusive |
| `tiny-one.fresh.neo-freya.sender.warm` | poll1 | 16 | 0.868 [0.854, 0.882] | 0.868 [0.852, 0.885] | 0.0000 | 0.0004 | faster |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 16 | 0.984 [0.956, 1.012] | 0.986 [0.954, 1.015] | 0.2350 | 1.0000 | inconclusive |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 16 | 0.899 [0.876, 0.922] | 0.898 [0.877, 0.919] | 0.0001 | 0.0007 | faster |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | poll1 | 1.000 [0.991, 1.009] | 1.000 [0.988, 1.013] | 0.995 [0.978, 1.012] |
| `small-flat.fresh.neo-freya.sender.warm` | poll1 | 1.007 [0.988, 1.026] | 1.006 [0.994, 1.018] | 1.013 [0.864, 1.187] |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 0.983 [0.934, 1.034] | 0.958 [0.917, 1.002] | 1.002 [0.992, 1.012] |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 0.981 [0.868, 1.108] | 0.928 [0.858, 1.004] | 0.996 [0.984, 1.008] |
| `small-real.fresh.freya-neo.sender.warm` | poll1 | 1.005 [0.985, 1.024] | 1.005 [0.964, 1.047] | 1.009 [0.992, 1.025] |
| `small-real.fresh.neo-freya.sender.warm` | poll1 | 1.003 [0.982, 1.025] | 0.996 [0.797, 1.244] | 1.005 [0.980, 1.030] |
| `small-real.noop.freya-neo.sender.warm` | poll1 | 0.966 [0.929, 1.003] | 0.976 [0.873, 1.090] | 1.019 [0.989, 1.049] |
| `small-real.noop.neo-freya.sender.warm` | poll1 | 0.953 [0.940, 0.966] | 0.859 [0.744, 0.992] | 0.997 [0.944, 1.053] |
| `tiny-one.fresh.freya-neo.sender.warm` | poll1 | 0.940 [0.901, 0.981] | 0.973 [0.935, 1.013] | 0.981 [0.961, 1.002] |
| `tiny-one.fresh.neo-freya.sender.warm` | poll1 | 0.978 [0.946, 1.010] | 0.855 [0.821, 0.890] | 0.998 [0.991, 1.005] |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 0.991 [0.933, 1.053] | 0.985 [0.958, 1.013] | 0.999 [0.984, 1.015] |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 0.985 [0.946, 1.025] | 0.897 [0.868, 0.927] | 0.996 [0.984, 1.009] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | poll1 | xs |
|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | 6.576 | 6.573 |
| `small-flat.fresh.neo-freya.sender.warm` | 3.390 | 3.375 |
| `small-flat.noop.freya-neo.sender.warm` | 0.303 | 0.316 |
| `small-flat.noop.neo-freya.sender.warm` | 0.271 | 0.292 |
| `small-real.fresh.freya-neo.sender.warm` | 16.537 | 16.494 |
| `small-real.fresh.neo-freya.sender.warm` | 12.149 | 12.273 |
| `small-real.noop.freya-neo.sender.warm` | 1.469 | 1.505 |
| `small-real.noop.neo-freya.sender.warm` | 1.374 | 1.601 |
| `tiny-one.fresh.freya-neo.sender.warm` | 0.202 | 0.209 |
| `tiny-one.fresh.neo-freya.sender.warm` | 0.141 | 0.162 |
| `tiny-one.noop.freya-neo.sender.warm` | 0.201 | 0.205 |
| `tiny-one.noop.neo-freya.sender.warm` | 0.143 | 0.159 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo.sender.warm` | poll1 | 0.0249 | 8 | 10 |
| `small-flat.fresh.neo-freya.sender.warm` | poll1 | 0.0182 | 8 | 8 |
| `small-flat.noop.freya-neo.sender.warm` | poll1 | 0.0842 | 66 | 88 |
| `small-flat.noop.neo-freya.sender.warm` | poll1 | 0.1476 | 198 | 265 |
| `small-real.fresh.freya-neo.sender.warm` | poll1 | 0.0808 | 61 | 81 |
| `small-real.fresh.neo-freya.sender.warm` | poll1 | 0.4098 | 1509 | 2022 |
| `small-real.noop.freya-neo.sender.warm` | poll1 | 0.2091 | 395 | 528 |
| `small-real.noop.neo-freya.sender.warm` | poll1 | 0.2702 | 657 | 880 |
| `tiny-one.fresh.freya-neo.sender.warm` | poll1 | 0.0769 | 56 | 74 |
| `tiny-one.fresh.neo-freya.sender.warm` | poll1 | 0.0309 | 11 | 14 |
| `tiny-one.noop.freya-neo.sender.warm` | poll1 | 0.0540 | 29 | 38 |
| `tiny-one.noop.neo-freya.sender.warm` | poll1 | 0.0482 | 23 | 30 |
