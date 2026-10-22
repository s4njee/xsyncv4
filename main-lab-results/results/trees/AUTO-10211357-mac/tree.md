# AUTO-10211357-mac

mac has about 4.5 h of room: 6 h minus 1.5 h left on MM1, with nothing queued. Its one link, mac-mars-usb10g, cannot apply wan_delay_ms or cpus (limits.wan.hosts and limits.cpus.hosts are empty), so lab2's 11 ms and 2-vCPU conditions cannot be reproduced here. Only mixed-bimodal and small-flat have measured sample times on this link. One experiment of about 24 min checks an untested confound behind both lab2 gaps: lab2 runs 0c94b3d70b9d, while all home reproductions (L2R1 to L2R8) used e51c1df1329a. It deliberately repeats only lab2's fresh scenario with lab2's flags, so it does not duplicate MM1's baseline sweep.

Started 2026-10-21T13:57:48Z; nothing new is queued after 2026-10-21T19:57Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| N0 | decided | 20261021T135748Z | N0: done (1 run) |
