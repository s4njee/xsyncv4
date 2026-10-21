# AUTO-10210751-neo

neo has 4.0 h of room: 6 h minus 0.2 h left on the sentinel and 1.8 h for the queued L2R4 plain psample baseline, which runs first as planned. The plan uses about 190 min, including rsync's possible confirmation on real-congress, which leaves margin for netem and the CPU cap stretching sample times. Every earlier reproduction capped neo as the sender. Here neo, an arm64 Linux Pi like lab2's Graviton receiver, receives from mars with 11 ms added and is held to 2 CPUs. This tests whether a starved receiver explains the congress-sample and real-projects losses. It does not duplicate L2R3/L2R4 (psample neo>mars) or the waiting confirmations, which only run if rsync screened ahead.

Started 2026-10-21T07:52:08Z; nothing new is queued after 2026-10-21T13:51Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| N0 | decided | 20261021T075208Z | N0: not clearly faster: the next window's plan reads this |
| N0c | waiting | — |  |
| N1 | decided | 20261021T075209Z | N1: done (1 run) |
| N2 | decided | 20261021T075211Z | N2: done (1 run) |
| N3 | decided | 20261021T075213Z | N3: done (1 run) |
