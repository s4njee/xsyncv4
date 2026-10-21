# T14-neo-local-psample

How fast can a Pi 5 back up the 21 GB psample tree from its NVMe drive to a Samsung T5 over USB, and what limits it?

Started 2026-10-18T18:09:24Z.

| Node | State | Runs | Decision |
|---|---|---|---|
| A | decided | 20261018T180924Z, 20261018T184002Z | A: xs is not ahead of rsync on a local copy: look for what holds it back (workers, flushing) and still check re-syncs (real-psample neo→neo-ssd xs 0.89× [0.81, 0.99]) |
| B | decided | 20261018T215450Z | B: no worker count beats the default four on this Pi and drive |
| Bc | waiting | — |  |
| C | decided | 20261018T215452Z | C: eager writeback or --no-atomic gets the backup onto the drive sooner: confirm it (real-psample neo→neo-ssd xs-eager 1.62× [1.47, 1.78]) |
| Cc | decided | 20261019T125037Z | Cc: done (1 run) |
| D | decided | 20261018T215454Z | D: xs re-syncs the local backup at least as fast as rsync |
