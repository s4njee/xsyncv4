# T1-neo-freya-small

What limits xs's small-file copies between the Pi and freya, and is its best setting safe as the default?

Started 2026-10-16T23:54:22Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| K2a | decided | 20261016T223005Z | K2a: RAM on freya is not clearly faster than its NVMe: the Pi sending is the limit |
| K2b | decided | 20261016T222957Z | K2b: into RAM on the Pi is at least 15% faster than onto its disk: the Pi's write path matters (small-flat freya→neo-shm xs-z-best 1.81× vs K1-congress-ceiling xs-z-best) |
| D2 | waiting | — |  |
| D3 | queued | 20261017T002741Z |  |
| D4 | queued | 20261017T004209Z |  |
| D9 | queued | 20261017T002751Z |  |
| D9b | waiting | — |  |
| D10 | queued | 20261017T004214Z |  |
| D8 | waiting | — |  |
| D2c | waiting | — |  |
| D3c | waiting | — |  |
| D4c | waiting | — |  |
| D8c | waiting | — |  |
| F1a | waiting | — |  |
