# PB1-neo-vpsb-cpp-vs-rsync

Over a 122 ms internet path, rsync -a beats xs -a -j4 on fresh copies of real trees, as on lab2, while xs wins no-ops.

- Kind: screening. Primary metric: `durable_s`. Control arm: `rsync`.
- Smallest effect of interest: 5%. Interval level: 95.0%.
- Runs: 20261021T141745Z-PB1-neo-vpsb-cpp-vs-rsync, 20261021T144636Z-PB1-neo-vpsb-cpp-vs-rsync, 20261022T000326Z-PB1-neo-vpsb-cpp-vs-rsync.
- Valid blocks: 0. Voided block attempts: 54.

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell |
|---|

## Voided attempts

- rsync: did not settle: vpsb is 15% busy
- rsync: harness error: vpsb: `python3 ~/mainlab/lib/a3dbc824d281/probe.py snapshot --interface ens3` exited 255: ssh: connect to host [host] po
- rsync: the destination does not match the corpus manifest: 58cde6f2ac0/corpus.py", line 580, in <module>
    main()
    ~~~~^^
  File "~/lab/lib/f58
- rsync: the transfer exited 255: ssh: connect to host [host] port 22: Connection timed out
rsync: connection unexpectedly closed (0 bytes received so far) 
- xs-cpp: did not settle: vpsb is 15% busy
- xs-cpp: the destination does not match the corpus manifest: 58cde6f2ac0/corpus.py", line 580, in <module>
    main()
    ~~~~^^
  File "~/lab/lib/f5
