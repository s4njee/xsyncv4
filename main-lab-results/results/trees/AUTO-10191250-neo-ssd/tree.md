# AUTO-10191250-neo-ssd

neo-ssd is idle with nothing queued, so it has 360 minutes; real-psample costs 8 minutes per sample. In LC3, rsync with eager writeback beat default xs, while xs-eager was much faster than xs. No experiment has put xs-eager against rsync-eager directly, and that comparison decides whether xs can beat rsync on this local copy. LC4 reported only the no-op cell, so the 1% update re-sync is still open. The eager plus --no-atomic combination has not been tried. The waiting tree confirmation of xs-eager against plain xs (LC3-durable-confirm) is left to the T14 tree, so it is not duplicated here. Budget: 96 minutes of screening plus 128 if the confirmation runs, then 64 and 64, about 352 minutes in total.

Started 2026-10-19T12:50:32Z; nothing new is queued after 2026-10-19T18:50Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| N0 | queued | 20261019T125032Z |  |
| N0c | waiting | — |  |
| N1 | queued | 20261019T125034Z |  |
| N2 | queued | 20261019T125035Z |  |
