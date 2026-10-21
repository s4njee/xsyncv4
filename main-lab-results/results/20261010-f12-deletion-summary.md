# F-12: verified subtree deletion comparison

The four-worker candidate completes deletion faster than the prior serial implementation in both tree layouts. All 32 samples pass independent rsync checksum/metadata verification, and all reported deletion counts match the fixture exactly.

Candidate: `0f84904e1ad7`; reference: `738bab04d758`. Both builds use Release `-O3` and LTO on the same macOS host. Each layout contains 65,536 regular files and 1,088 nested directories; the single-root layout adds one wrapping directory. Each tool receives four samples with rotated positions. Setup and verification are untimed; OS caches are retained.

| Layout | Tool | Median wall (s) | Median CPU (s) | Largest process peak (MiB) |
|---|---|---:|---:|---:|
| many-subtrees | reference | 5.823 | 5.020 | 7.0 |
| many-subtrees | candidate-j1 | 5.060 | 4.814 | 3.9 |
| many-subtrees | candidate-j4 | 2.868 | 9.492 | 7.2 |
| many-subtrees | rsync | 3.172 | 3.038 | 6.9 |
| single-stale-root | reference | 5.794 | 5.567 | 7.0 |
| single-stale-root | candidate-j1 | 5.706 | 5.487 | 3.9 |
| single-stale-root | candidate-j4 | 3.340 | 11.431 | 7.0 |
| single-stale-root | rsync | 3.278 | 3.082 | 9.2 |

Against the prior product, four workers provide 2.03× speedup across independent stale subtrees and 1.73× under one stale root. The single-root candidate is about 2% slower than rsync on this host. Parallel removal uses approximately twice the CPU of the serial controls.

The host had high background load (one-minute load 25.48 at the start and 138.00 at the end), and the APFS volume was 98% full. These results establish tested deletion behavior and the observed wall/CPU tradeoff; they do not choose filesystem thread defaults or satisfy F-07.

Five deletion tests pass on macOS and Linux, including single-child chains, inherited merge protection, symlink sentinels, finite limits and dry runs. All 231 macOS itemized and 227 Linux data/metadata/exit-code differential cases pass. Finite limits and dry runs retain serial ordering.

[Raw verified measurements](20261010-f12-deletion.json). [Superseded partial comparison](20261010-f12-independent-subtrees-partial.json).
