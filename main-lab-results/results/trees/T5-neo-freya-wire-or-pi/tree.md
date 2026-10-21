# T5-neo-freya-wire-or-pi

On the gigabit wire between the Pi and freya, is xs limited by the link or by the Pi's sending, and what should the default be?

Started 2026-10-17T15:23:01Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| B | decided | 20261017T153637Z | B: xs fills the wire both ways on large files: the link is the limit, and only the small-file default is left (large-text neo→freya xs 0.93 Gb/s; large-text freya→neo xs 0.92 Gb/s) |
| C | waiting | — |  |
| Cc | waiting | — |  |
| S | decided | 20261017T162644Z | S: xs's best setting was nowhere slower than its default |
| Sb | waiting | — |  |
| N | decided | 20261017T174642Z | N: xs's best setting was faster on no-op copies too (small-real neo→freya xs-best 1.64× [1.47, 1.83] faster; real-congress neo→freya xs-best 1.30× [1.17, 1.45] faster) |
| F1a | held | 20261017T202542Z, 20261017T205646Z, 20261017T212914Z, 20261017T215941Z, 20261017T224604Z, 20261017T230759Z | Retired after the USB 2.5 Gb/s adapter change; old gigabit samples are preserved separately. |
