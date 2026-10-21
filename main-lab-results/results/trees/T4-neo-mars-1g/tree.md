# T4-neo-mars-1g

What limits small-file copies between a Raspberry Pi 5 and a Ryzen desktop, and which settings should be the default?

Started 2026-10-17T02:11:51Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| H0 | decided | 20261017T021151Z | H0: baseline measured; next, which side limits small files, and the default question |
| H1a | decided | 20261017T121633Z | H1a: the Pi creates small files about as fast as xs delivers them: its own receiving is the limit |
| H1b | decided | 20261017T121636Z | H1b: mars creates small files at least twice as fast as xs delivers them: look at the Pi's sending side (small-flat neo→mars local-x4 4.55× [4.42, 4.68] faster; real-congress neo→mars local-x4 3.78× [3.64, 3.93] faster; small-deep neo→mars local-x4 2.08× [1.90, 2.28] faster) |
| H3 | waiting | — |  |
| H4 | decided | 20261017T130118Z | H4: no receiving setting on the Pi beat xs's best |
| H5 | queued | 20261017T132043Z |  |
| H6 | decided | 20261017T121639Z | H6: xs's best setting was nowhere slower than its default |
| H3c | waiting | — |  |
| H4c | waiting | — |  |
| H5c | waiting | — |  |
| F4a | waiting | — |  |
