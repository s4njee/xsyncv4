# T7-neo-freya-compress

On the gigabit wire between the Pi and freya, does compression pay, which level, and does it cost on data that will not compress?

Started 2026-10-17T16:16:16Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| W | decided | 20261016T162239Z, 20261017T161616Z | W: xs -z carries more than the wire both ways on text: only its cost on incompressible data is left to settle (large-text freya→neo xs-z 2.26 Gb/s; large-text neo→freya xs-z 2.15 Gb/s) |
| P | waiting | — |  |
| Pc | waiting | — |  |
| C | decided | 20261017T165108Z, 20261017T185524Z | C: compression is harmless on incompressible data here |
| F1a | held | 20261017T184701Z, 20261017T204111Z, 20261017T211342Z, 20261017T214431Z, 20261017T223055Z, 20261017T230123Z, 20261017T230953Z | Retired after the USB 2.5 Gb/s adapter change; old gigabit samples are preserved separately. |
