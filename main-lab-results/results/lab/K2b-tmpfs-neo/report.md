# K2b-tmpfs-neo

xs copies small trees into RAM on the Pi much faster than onto its NVMe: the Pi's filesystem is the limit.

- Kind: screening. Primary metric: `durable_s`. Control arm: `xs-z`.
- Smallest effect of interest: 3%. Interval level: 95.0%.
- Runs: 20261016T222957Z-K2b-tmpfs-neo.
- Valid blocks: 6. Voided block attempts: 36.
- **Fewer than 8 blocks in some cells: estimates only, no verdict.**

## Ratio to the control

Time of the arm divided by time of the control in the same block; below 1 is faster. The interval is the paired t interval; the robust column is the Hodges-Lehmann estimate with its distribution-free interval.

| Cell | Arm | Blocks | Ratio | Robust | p | Verdict |
|---|---|---|---|---|---|---|
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-z-best | 6 | 0.856 [0.775, 0.946] | 0.829 [0.799, 1.032] | 0.0625 | too few blocks |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs | 6 | 1.254 [1.227, 1.282] | 1.258 [1.207, 1.280] | 0.0312 | too few blocks |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-best | 6 | 1.280 [1.234, 1.328] | 1.283 [1.212, 1.326] | 0.0312 | too few blocks |

This is a screening experiment: the p-values are unadjusted and nothing here is a claim. A candidate is re-measured in a confirmatory run.

## Other metrics

Descriptive only; the same ratio and interval for each.

| Cell | Arm | `cpu_s` | `rss_bytes` | `wall_s` |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-z-best | 0.951 [0.931, 0.971] | 0.956 [0.856, 1.069] | 0.856 [0.775, 0.946] |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs | 0.860 [0.818, 0.903] | 0.605 [0.564, 0.648] | 1.254 [1.227, 1.282] |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-best | 0.761 [0.681, 0.851] | 0.605 [0.560, 0.654] | 1.280 [1.235, 1.328] |

## Absolute `durable_s`

Geometric mean over valid blocks, in seconds.

| Cell | xs | xs-best | xs-z | xs-z-best |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo-shm.sender.warm` | 2.975 | 3.037 | 2.372 | 2.032 |

## Noise

Standard deviation of the block log-ratios, and the blocks that would give 80% power for the 95% interval to exclude 1 at a true effect of 3%, and for the verdict equivalent at no effect.

| Cell | Arm | sigma_d | Blocks to detect 3% | Blocks for equivalent at 3% |
|---|---|---|---|---|
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-z-best | 0.0947 | 83 | 110 |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs | 0.0208 | 8 | 8 |
| `small-flat.fresh.freya-neo-shm.sender.warm` | xs-best | 0.0348 | 13 | 17 |

## Voided attempts

- xs-best: the transfer exited 11: buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] 
- xs-best: the transfer exited 11: error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T
- xs-best: the transfer exited 11: fering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] No 
- xs-best: the transfer exited 11: mmary: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/
- xs-best: the transfer exited 11: summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/wor
- xs-best: the transfer exited 11: ummary: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work
- xs-z-best: the transfer exited 11: ffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] 
- xs-z-best: the transfer exited 11: mary: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work
- xs-z-best: the transfer exited 11: ng first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T222957Z-K2
- xs-z-best: the transfer exited 11: or (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T2
- xs-z-best: the transfer exited 11: ry: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/2
- xs-z-best: the transfer exited 11: ummary: 1 error (showing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/wo
- xs-z-best: the transfer exited 11: wing first 1)
  file IO (code 11): 1 error
    open failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T222957Z-
- xs-z: the transfer exited 11:  summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/wo
- xs-z: the transfer exited 11: (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T222957
- xs-z: the transfer exited 11: buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] No 
- xs-z: the transfer exited 11: e, buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] 
- xs-z: the transfer exited 11: error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/work/20261016T
- xs-z: the transfer exited 11: mary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/work/2
- xs-z: the transfer exited 11: mmary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/work/
- xs-z: the transfer exited 11: summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/wor
- xs-z: the transfer exited 11: ummary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/work
- xs: the transfer exited 11: , buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] No 
- xs: the transfer exited 11: ode, buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: [Errno 28] 
- xs: the transfer exited 11: r summary: 1 error (showing first 1)
  file IO (code 11): 1 error
    mkstemp failed on "~/benchmarks/xsyncv4/lab-shm/wor
