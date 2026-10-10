# F-10 bounded subtree cloning after parallel corrections — 2026-10-10

All 108 timed copies and 18 excluded warmups pass independent checksum/metadata and source-immutability verification. Six full tool-order permutations compare clean 0822c3728055 leaf-only cloning, clean 732f70718369 bounded subtree cloning and rsync, with the same explicit four-worker budget. Each clone transaction is limited to 4,096 descendant entries and 32 levels; oversized trees can clone eligible children.

| Case | Reference wall/CPU (s) | Candidate wall/CPU (s) | rsync wall (s) | Candidate wall change |
|---|---:|---:|---:|---:|
| bounded-a | 0.0237/0.0401 | 0.0252/0.0276 | 0.2342 | +6.5% |
| bounded-rlt | 0.0427/0.0994 | 0.0415/0.0756 | 0.2362 | -2.9% |
| near-limit-a | 0.0614/0.1111 | 0.0707/0.0781 | 0.7725 | +15.1% |
| near-limit-rlt | 0.1329/0.3286 | 0.1261/0.2423 | 0.7325 | -5.1% |
| over-limit-a | 0.1605/0.2796 | 0.1831/0.2254 | 1.7499 | +14.0% |
| over-limit-rlt | 0.3280/0.7345 | 0.2881/0.6662 | 1.6998 | -12.2% |

The bounded version uses less CPU in every case. Omitted-permission `-rlt` wall medians improve by 2.9%, 5.1% and 12.2% for bounded, near-limit and oversized trees. Archive `-a` wall medians remain 6.5%, 15.1% and 14.0% slower than leaf-only, respectively, while CPU is 31.0%, 29.7% and 19.4% lower. This is a workload tradeoff, not a universal wall-time improvement. The [initial serial correction regression](20261010-f10-initial-summary.md) remains retained; timings from separate runs do not isolate the parallel correction change.

Six focused subtree tests, fourteen macOS-specific tests (one existing skip), all 231 macOS differential cases and the Linux build pass. The earlier 433d1ed18a7e hosted run passed both full production gates; it does not qualify the newer parallel-correction source.

Measurements use the nearly full physical APFS volume on a busy M1 Max. Load changes from [44.50244140625, 36.625, 41.6083984375] to [54.2548828125, 44.99169921875, 44.2294921875]. Full samples and outliers are retained; do not generalize these results to a quiet or empty physical device.

F-10 acceptance is complete: the bounded implementation and its leaf-only comparison are verified and measured. The remaining archive wall regression is explicitly recorded.

Evidence: [raw samples](20261010-f10-parallel.json), [log](20261010-f10-parallel.log), [validation](20261010-f10-parallel-validation.json).
