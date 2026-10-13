# E3b-compress-confirm

xs -z is more than 3% faster than xs on compressible corpora over gigabit, and not more than 3% slower on random data.

- Kind: confirmatory. Primary metric: `wall_s`. Control arm: `xs`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261012T210905Z-E3b-compress-confirm.
- Valid blocks: 96. Voided block attempts: 0.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | p (Holm) | Verdict |
|---|---|---|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 12 | 0.773 [0.768, 0.779] | 0.773 [0.768, 0.779] | 0.0005 | 0.0078 | faster |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 12 | 1.009 [1.003, 1.014] | 1.008 [1.003, 1.015] | 0.0020 | 0.0078 | equivalent |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 12 | 0.794 [0.779, 0.809] | 0.792 [0.778, 0.809] | 0.0005 | 0.0078 | faster |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 12 | 0.981 [0.974, 0.989] | 0.983 [0.973, 0.988] | 0.0010 | 0.0078 | equivalent |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z | 12 | 0.932 [0.917, 0.947] | 0.932 [0.916, 0.949] | 0.0005 | 0.0078 | faster |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 12 | 1.045 [1.007, 1.083] | 1.035 [1.007, 1.093] | 0.0103 | 0.0205 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z | 12 | 1.050 [1.028, 1.073] | 1.050 [1.027, 1.071] | 0.0010 | 0.0078 | inconclusive |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 12 | 1.725 [1.460, 2.038] | 1.755 [1.477, 2.043] | 0.0005 | 0.0078 | slower |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 12 | 1.035 [1.024, 1.046] | 1.035 [1.022, 1.046] | 0.0005 | 0.0078 | inconclusive |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 12 | 1.061 [1.031, 1.092] | 1.063 [1.036, 1.095] | 0.0034 | 0.0103 | slower |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 12 | 1.054 [1.043, 1.065] | 1.054 [1.041, 1.066] | 0.0005 | 0.0078 | slower |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 12 | 1.619 [1.372, 1.911] | 1.617 [1.352, 1.974] | 0.0005 | 0.0078 | slower |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 12 | 0.844 [0.785, 0.906] | 0.845 [0.783, 0.921] | 0.0005 | 0.0078 | faster |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 12 | 1.363 [1.326, 1.400] | 1.363 [1.327, 1.402] | 0.0005 | 0.0078 | slower |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 12 | 0.505 [0.481, 0.530] | 0.511 [0.493, 0.526] | 0.0005 | 0.0078 | faster |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 12 | 1.032 [0.924, 1.153] | 1.003 [0.953, 1.068] | 0.6963 | 0.6963 | inconclusive |

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `durable_s` | `rss_bytes` |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 1.096 [1.083, 1.109] | 0.782 [0.776, 0.788] | 1.507 [1.482, 1.531] |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.521 [0.515, 0.527] | 1.006 [0.997, 1.016] | 0.099 [0.098, 0.101] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 1.383 [1.312, 1.457] | 0.795 [0.780, 0.810] | 1.478 [1.445, 1.512] |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.499 [0.490, 0.509] | 0.981 [0.974, 0.989] | 0.124 [0.121, 0.126] |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z | 0.929 [0.920, 0.939] | 0.938 [0.927, 0.949] | 1.524 [1.396, 1.663] |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.674 [0.653, 0.696] | 1.045 [1.009, 1.083] | 0.100 [0.097, 0.103] |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z | 1.196 [1.092, 1.310] | 1.050 [1.030, 1.070] | 0.857 [0.741, 0.991] |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.695 [0.672, 0.718] | 1.704 [1.445, 2.008] | 0.164 [0.129, 0.208] |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 1.234 [1.218, 1.251] | 1.031 [1.018, 1.044] | 1.050 [0.954, 1.155] |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 0.695 [0.679, 0.711] | 1.057 [1.029, 1.085] | 0.100 [0.097, 0.103] |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 1.214 [1.170, 1.261] | 1.046 [1.026, 1.068] | 0.982 [0.777, 1.241] |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.676 [0.658, 0.693] | 1.588 [1.341, 1.881] | 0.154 [0.130, 0.182] |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.923 [0.893, 0.954] | 0.848 [0.791, 0.910] | 1.154 [0.802, 1.660] |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.924 [0.888, 0.962] | 1.350 [1.317, 1.384] | 1.307 [1.285, 1.331] |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 0.833 [0.818, 0.848] | 0.512 [0.486, 0.539] | 0.473 [0.450, 0.497] |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.517 [0.507, 0.528] | 1.026 [0.918, 1.146] | 0.099 [0.097, 0.101] |

## Absolute `wall_s`

Geometric mean over valid blocks, in seconds.

| Cell | rsync | xs | xs-z |
|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | 12.324 | 12.215 | 9.446 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | 12.264 | 12.498 | 9.924 |
| `small-flat.fresh.freya-neo.sender.warm` | 6.700 | 6.413 | 5.976 |
| `small-flat.fresh.neo-freya.sender.warm` | 5.822 | 3.375 | 3.545 |
| `small-opaque.fresh.freya-neo.sender.warm` | 6.780 | 6.390 | 6.613 |
| `small-opaque.fresh.neo-freya.sender.warm` | 5.564 | 3.437 | 3.622 |
| `small-real.fresh.freya-neo.sender.warm` | 22.889 | 16.797 | 14.169 |
| `small-real.fresh.neo-freya.sender.warm` | 11.791 | 11.424 | 5.765 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `mixed-bimodal.fresh.freya-neo.sender.warm` | xs-z | 0.0113 | 8 | 8 |
| `mixed-bimodal.fresh.freya-neo.sender.warm` | rsync | 0.0084 | 8 | 8 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | xs-z | 0.0301 | 11 | 13 |
| `mixed-bimodal.fresh.neo-freya.sender.warm` | rsync | 0.0121 | 8 | 8 |
| `small-flat.fresh.freya-neo.sender.warm` | xs-z | 0.0259 | 9 | 11 |
| `small-flat.fresh.freya-neo.sender.warm` | rsync | 0.0572 | 32 | 42 |
| `small-flat.fresh.neo-freya.sender.warm` | xs-z | 0.0342 | 13 | 17 |
| `small-flat.fresh.neo-freya.sender.warm` | rsync | 0.2629 | 623 | 834 |
| `small-opaque.fresh.freya-neo.sender.warm` | xs-z | 0.0166 | 8 | 8 |
| `small-opaque.fresh.freya-neo.sender.warm` | rsync | 0.0455 | 21 | 27 |
| `small-opaque.fresh.neo-freya.sender.warm` | xs-z | 0.0166 | 8 | 8 |
| `small-opaque.fresh.neo-freya.sender.warm` | rsync | 0.2610 | 614 | 822 |
| `small-real.fresh.freya-neo.sender.warm` | xs-z | 0.1125 | 116 | 155 |
| `small-real.fresh.freya-neo.sender.warm` | rsync | 0.0425 | 19 | 24 |
| `small-real.fresh.neo-freya.sender.warm` | xs-z | 0.0760 | 54 | 72 |
| `small-real.fresh.neo-freya.sender.warm` | rsync | 0.1741 | 274 | 367 |
