# Supplementary results

Experiments that are not part of the path experiments in `../lab/` and are
not evidence for the paper's claims. They use the same harness, record
format, analysis and reports, so they read the same way, but one endpoint is
a busy workstation.

## What is different here

- **One endpoint is this Mac** (`mbp-3`, APFS), the other is `mars` (Linux,
  ext4), over a path with a wireless mesh hop.
- **The Mac starts every transfer.** It accepts no SSH, so a copy to mars is
  a push and a copy to the Mac is a pull. The cell name says which:
  `mac-mars.sender` or `mars-mac.receiver`.
- **No quiet-host gate, no cold cache, no governor control.** Neither host
  has the privileged helper, and the Mac runs a desktop session throughout.
- **Background priority.** A supplementary run waits whenever a path
  experiment marks a host it shares as in use.
- **Small-file corpora only.** With the Mac and Wi-Fi in the loop, wire speed
  is not worth measuring.
- **Different rsync builds at each end:** 3.4.4 from Homebrew on the Mac,
  3.5.0 on mars. `xs` is the same commit at both ends, built natively on the
  Mac.

The noise shows it. The standard deviation of the block log-ratios is 0.16 to
0.55 on the 100,000-file corpora and 0.6 to 0.8 on the single small file,
against 0.01 to 0.19 in the path experiments. A 5% effect would need
hundreds to thousands of blocks here; these runs can show a factor of 1.3 or
more and nothing finer.

## S1-mac-mars-small

rsync `-a` against `xs -a` (`e1f05b518049`), fresh copy and no-op, both
directions, 12 blocks, 192 of 192 valid, run on 2026-10-12. Full tables in
[S1-mac-mars-small/report.md](S1-mac-mars-small/report.md). Ratios are xs
time over rsync time, with the 95% interval; below 1 is faster.

| Corpus | Scenario | Mac to mars (push) | mars to Mac (pull) |
|---|---|---|---|
| `small-flat` | fresh | 0.29 [0.22, 0.39], 4.4 s against 15.0 s | 0.81 [0.73, 0.89], 23.1 s against 28.7 s |
| `small-flat` | no-op | 0.35 [0.30, 0.42] | 0.38 [0.30, 0.49] |
| `small-opaque` | fresh | 0.30 [0.21, 0.42], 4.3 s against 14.4 s | 0.78 [0.67, 0.90], 21.2 s against 27.3 s |
| `small-opaque` | no-op | 0.30 [0.26, 0.35] | 0.40 [0.34, 0.47] |
| `small-deep` | fresh | 0.37 [0.30, 0.45], 10.5 s against 28.5 s | **1.75 [1.53, 1.99]**, 57.4 s against 32.8 s |
| `small-deep` | no-op | 0.53 [0.43, 0.66] | **3.66 [2.87, 4.66]**, 11.3 s against 3.1 s |
| `tiny-one` | both | no difference detectable | no difference detectable |

What it says:

- **Writing to ext4, xs is about three times faster than rsync on small
  files**, and two to three times faster on a no-op. This agrees with the
  path experiments.
- **Writing a flat tree to APFS, xs is about 20% faster**; the Mac's
  filesystem, not the tool, sets most of the time (20 s of kernel time on
  the Mac either way).
- **Writing a deep tree to APFS, xs is slower, fresh and no-op.** The
  corpus has the same 100,000 files as `small-flat` in 116,667 directories.
  On the Mac, xs spends 89 s of kernel time on the fresh copy where rsync
  spends 42 s, and 27 s on the no-op where rsync spends 1.9 s. Neither the
  flat tree nor a Linux receiver shows this, so it is the macOS receiver's
  per-directory work. It is the one result here worth following up, and it
  is large enough to survive the noise.

## Layout

Each experiment directory holds one directory per run (`plan.json`,
`samples.jsonl`, `blocks.jsonl`, `run.json`, the agent's log), an `analysis/`
directory of tables and a `report.md`, exactly as under `../lab/`.
