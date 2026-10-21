# AUTO-10210142-neo

neo drives the only networked link, so it alone can reproduce lab2's latency. It has 5.9 h of room (6 h minus 0.1 h left on the sentinel, nothing queued). The plan uses about 282 min including both possible confirmations, which leaves margin in case netem and the CPU cap stretch sample times. e51c1df1329a is the newest xs build on both neo and mars; no -tune build is staged on mars, so tuning (step 2) waits for a reproduced gap.

Started 2026-10-21T01:42:43Z; nothing new is queued after 2026-10-21T07:42Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| N0 | decided | 20261021T014243Z | N0: not clearly faster: the next window's plan reads this |
| N0c | waiting | — |  |
| N1 | decided | 20261021T014245Z | N1: done (1 run) |
| N2 | decided | 20261021T014247Z | N2: not clearly faster: the next window's plan reads this |
| N2c | waiting | — |  |
| N3 | queued | 20261021T014249Z |  |
