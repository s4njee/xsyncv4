# T3-mac-freya-10g

How close can xs get to 10 Gb/s between the Mac and freya, and what gets it closer?

Started 2026-10-17T02:02:49Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| G0 | decided | 20261017T020249Z, 20261017T121630Z | G0: xs carries large files below 8 Gb/s one way or both: tune them before anything else |
| G0b | decided | 20261017T020250Z | G0b: done (1 run) |
| G1 | decided | 20261017T124214Z | G1: no setting moved large files closer to the link |
| G2 | decided | 20261017T133650Z | G2: the pool holds large files below 8 Gb/s: tune its writes |
| G2b | queued | 20261017T142015Z |  |
| G3 | failed | 20261017T133652Z |  |
| G4 | waiting | — |  |
| G1c | waiting | — |  |
| G2bc | waiting | — |  |
| G3c | waiting | — |  |
| G4c | waiting | — |  |
| F3a | waiting | — |  |
| F3b | waiting | — |  |
