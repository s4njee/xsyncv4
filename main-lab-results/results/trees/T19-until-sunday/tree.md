# T19-until-sunday

On the Mac-apollo cable, where does rsync still beat xs, does PR #34's compression pick well on fast hosts, and which settings should be xs's defaults?

Started 2026-10-23T16:37:47Z; nothing new is queued after 2026-10-25T12:00Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| CZ1 | decided | 20261023T163747Z | CZ1: a fixed zstd level beat PR #34's automatic choice at 10 GbE: confirm it, and the policy needs another look (large-text mac→apollo xs-rs-z1 2.20× [0.27, 18.04]; large-text mac→apollo xs-rs-z3 1.41× [0.11, 18.04]; large-text apollo→mac xs-rs-z3 1.17× [0.86, 1.59]; real-congress mac→apollo xs-rs-z3 1.15× [0.29, 4.52]; 2 more) |
| CZ1c | skipped | — |  |
| RW7 | decided | 20261023T172300Z | RW7: xs with --whole-file beat rsync's delta at 10 GbE: on a fast link xs should skip the delta; confirm (large-solo mac→apollo xs-cpp-W 2.66× [0.00, 11261.27]; hs-16x256m mac→apollo xs-rs-W 2.38× [0.00, 2255.51]; large-solo mac→apollo xs-cpp-W 2.30× [0.00, 657178.09]; large-text mac→apollo xs-cpp-W 1.83× [0.00, 1734.90]; 17 more) |
| RW7c | decided | 20261023T185557Z | RW7c: done (1 run) |
| RW8a | decided | 20261023T185557Z | RW8a: latency widens rsync's delta lead: xs's signature exchange costs round trips (large-text apollo→mac xs-rs 0.91× [0.45, 1.82]; hs-16x256m apollo→mac xs-rs 0.86× [0.82, 0.90]; hs-16x256m apollo→mac xs-rs 0.84× [0.67, 1.06]; hs-16x256m apollo→mac xs-cpp 0.84× [0.63, 1.11]; 13 more) |
| RW8b | decided | 20261023T201557Z | RW8b: on a slow path rsync's delta beats xs: xs must send less when bytes are the limit; a code case (large-text apollo→mac xs-rs 0.85× [0.77, 0.94]; large-text apollo→mac xs-rs 0.80× [0.71, 0.90]; large-text apollo→mac xs-cpp 0.52× [0.51, 0.52]; large-text mac→apollo xs-cpp 0.47× [0.01, 27.43]; 1 more) |
| RW3b | decided | 20261023T204057Z | RW3b: otherwise |
| RW6b | decided | 20261024T023910Z | RW6b: otherwise |
| PR1 | decided | 20261024T025320Z | PR1: PR #34 is slower than its base in some cell: confirm on fresh blocks before merging (hs-16x256m apollo→mac xs-rs 0.82× [0.29, 2.34]; local-laikav2 apollo→mac xs-rs 0.81× [0.30, 2.18]) |
| PR1r | decided | 20261024T040403Z | PR1r: done (1 run) |
| CZ2 | decided | 20261024T040404Z | CZ2: at 1 Gb/s a fixed level beat the automatic one: the rate rule's thresholds need moving (large-text apollo→mac xs-rs-z3 1.44× [1.44, 1.44]; large-text mac→apollo xs-rs-z3 1.15× [0.00, 429.31]) |
| CZ3 | decided | 20261024T072401Z | CZ3: at 100 Mb/s a fixed level beat the automatic one: the policy should climb sooner when bytes are the limit (real-congress mac→apollo xs-rs-z3 1.20× [1.00, 1.43]; real-congress mac→apollo xs-rs-z1 1.19× [0.58, 2.47]) |
| CZ4 | decided | 20261024T075240Z | CZ4: with 2 cores a fixed level beat the automatic one: the CPU veto misjudges this machine (large-text mac→apollo xs-rs-z1 1.44× [0.00, 772.06]) |
| SM1 | decided | 20261024T082417Z | SM1: skipping the rename or more workers writes small files onto APFS faster: confirm (scale-count-1000000 apollo→mac xs-cpp-noatomic 1.76× [1.67, 1.86]; real-congress apollo→mac xs-cpp-noatomic 1.42× [1.38, 1.45]; real-congress apollo→mac xs-cpp-j8 1.18× [0.89, 1.58]; real-congress apollo→mac xs-cpp-noatomic 1.08× [0.71, 1.63]) |
| SM1c | decided | 20261024T103613Z | SM1c: done (1 run) |
| PS1 | decided | 20261024T103613Z | PS1: a setting pulls psample onto the Mac faster than xs's default: confirm (real-psample apollo→mac xs-cpp-j8 1.70×; real-psample apollo→mac xs-cpp-O 1.58×; real-psample apollo→mac xs-cpp-noatomic 1.14×) |
| PS1c | skipped | — |  |
| WB1 | decided | 20261024T154821Z | WB1: eager writeback shortens the time to durable on apollo: confirm, then adopt on Linux receivers (EXA A7) (hs-16x256m mac→apollo xs-cpp-eager 2.04× [0.56, 7.42]; real-congress mac→apollo xs-cpp-eager 1.79× [1.36, 2.36]) |
| WB1c | decided | 20261024T160501Z | WB1c: done (1 run) |
| XC1 | decided | 20261024T160501Z | XC1: done (1 run) |
| LT1 | decided | 20261024T160502Z | LT1: otherwise |
| LT2 | decided | 20261024T182522Z | LT2: otherwise |
| CS1 | decided | 20261024T204310Z | CS1: otherwise |
| IN1 | decided | 20261025T001815Z | IN1: otherwise |
| JB1 | decided | 20261025T013958Z | JB1: a worker count beat xs-rs's default of 8 at 10 GbE: the default should depend on the link or the files (real-congress mac→apollo xs-rs-j16 1.27× [0.36, 4.56]; hs-16x256m apollo→mac xs-rs-j2 1.08× [0.89, 1.32]; hs-16x256m mac→apollo xs-rs-j16 1.07× [0.09, 12.91]) |
| HS2 | decided | 20261025T022919Z | HS2: PR #34 is slower than its base on large incompressible files: check the CPU probe's cost (hs-16x256m apollo→mac xs-rs 0.90× [0.72, 1.11]; hs-16x256m mac→apollo xs-rs 0.80× [0.18, 3.57]) |
| LT3 | decided | 20261025T025625Z | LT3: otherwise |
| IN2 | decided | 20261025T051236Z | IN2: otherwise |
| CK1 | decided | 20261025T065118Z | CK1: otherwise |
| DE1 | decided | 20261025T083458Z | DE1: otherwise |
| JC1 | queued | 20261025T102540Z |  |
| CP1 | waiting | — |  |
| FS1 | decided | 20261023T232159Z, 20261023T233649Z, 20261023T235157Z, 20261024T000710Z, 20261024T002223Z, 20261024T003754Z, 20261024T005242Z, 20261024T010733Z | FS1: done (8 runs) |
