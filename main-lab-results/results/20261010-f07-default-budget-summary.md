# F-07 automatic APFS worker budget — 2026-10-10

All 50 timed copies and 10 excluded warmups pass independent rsync checksum/metadata verification. Five rotated samples per tool/case compare clean 433d1ed18a7e automatic selection with clean 741ebdcc127f automatic selection and explicit four/eight-worker controls. Cloning is disabled. The corpus contains 76,838 files, 19,072 directories and 517,808,080 logical bytes.

| Case | Tool | Median wall (s) | Median CPU (s) | Peak process RSS (MiB) |
|---|---|---:|---:|---:|
| fresh-byte | reference-j0 | 19.705 | 33.421 | 46.7 |
| fresh-byte | candidate-j0 | 19.205 | 32.028 | 34.8 |
| fresh-byte | candidate-j4 | 19.349 | 32.044 | 33.7 |
| fresh-byte | candidate-j8 | 20.077 | 33.620 | 48.6 |
| fresh-byte | rsync | 21.632 | 26.165 | 39.1 |
| noop | reference-j0 | 2.232 | 10.032 | 39.9 |
| noop | candidate-j0 | 2.337 | 7.001 | 37.7 |
| noop | candidate-j4 | 2.344 | 6.997 | 37.8 |
| noop | candidate-j8 | 2.152 | 10.073 | 40.4 |
| noop | rsync | 2.292 | 2.846 | 25.0 |

Automatic four-worker selection reduces fresh-copy median wall time from 19.705 to 19.205 s (2.5%) and CPU from 33.421 to 32.028 s (4.2%). No-op CPU decreases from 10.032 to 7.001 s (30.2%), with wall time increasing from 2.232 to 2.337 s (4.7%). Explicit eight workers improve no-op wall time to 2.152 s but use 10.073 s CPU; fresh copies take 20.077 s. The four-worker default is a measured fresh-copy/CPU tradeoff, not the fastest no-op setting.

Native macOS build, 231 differential cases, thirteen P0 cases, six subtree-clone cases and five range cases pass (one existing range skip). Linux build, 227 differential and thirteen P0 cases pass (two existing P0 skips). Explicit -j overrides the filesystem budget, and automatic selection does not enable intra-file ranges.

This comparison runs on the physical APFS data volume at 99% capacity, with load averages rising from [20.9404296875, 27.43310546875, 34.0361328125] to [37.66650390625, 32.19384765625, 41.06494140625]. The prior [free-container comparison](20261010-f07-free-container-summary.md) covers a mostly empty 16 GiB APFS container with a nearly full backing volume. Neither comparison isolates physical free-space effects or proves quiet-disk behavior. All samples and outliers are retained.

F-07 acceptance is complete: the free APFS container was measured, descriptor-relative creation was implemented and compared, and the filesystem-specific default is selected and validated. The physical backing-space limitation remains documented.

Evidence: [samples](20261010-f07-default-budget.json), [log](20261010-f07-default-budget.log), [validation state](20261010-f07-default-budget-validation.json).
