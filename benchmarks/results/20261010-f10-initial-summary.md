# F-10 first bounded-subtree comparison — 2026-10-10

Clean leaf-only reference 0822c3728055 and bounded candidate 433d1ed18a7e both use explicit four-worker pools. All 108 timed samples and 18 excluded warmups pass independent checksum/metadata verification and source-immutability checks. Each case has six complete tool-order permutations. The maximum transaction has 4,096 scanned descendant entries and 32 levels.

| Case | Leaf-only wall (s) | Subtree wall (s) | Leaf-only CPU (s) | Subtree CPU (s) | rsync wall (s) |
|---|---:|---:|---:|---:|---:|
| bounded-a | 0.0272 | 0.0295 | 0.0433 | 0.0267 | 0.2570 |
| bounded-rlt | 0.0413 | 0.0574 | 0.0986 | 0.0515 | 0.2245 |
| near-limit-a | 0.0635 | 0.0769 | 0.1132 | 0.0724 | 0.7467 |
| near-limit-rlt | 0.1154 | 0.1756 | 0.3221 | 0.1656 | 0.7381 |
| over-limit-a | 0.1763 | 0.1809 | 0.2739 | 0.2212 | 1.6705 |
| over-limit-rlt | 0.2898 | 0.3044 | 0.7366 | 0.6792 | 1.6673 |

The first subtree version reduces CPU in every case but increases wall time. The near-limit omitted-permissions case is 52.2% slower than the leaf-only path (0.1756 versus 0.1154 s), although it uses 48.6% less CPU and remains faster than rsync. Attribute correction after a single cloned transaction is serial; the leaf-only path corrects separate leaves in parallel. Independent directory corrections are being moved into the existing pool with at most four participating workers. That follow-up still needs correctness and performance validation.

The Mac is busy and its backing volume is nearly full. Load averages are [48.21240234375, 35.62548828125, 38.85546875] initially and [28.59765625, 32.404296875, 36.974609375] finally. The comparison is serialized after normalization measurement. These limits and every sample, including negative results, are retained.

Raw evidence: [samples](20261010-f10-initial.json), [build and measurement log](20261010-f10-initial.log).
