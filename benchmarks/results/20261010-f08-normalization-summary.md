# F-08 path normalization comparison — 2026-10-10

All 36 timed no-op samples and six excluded warmups pass independent rsync checksum/metadata verification. There are six rotated timed samples per tool. Reference ed8b84137035 and candidate 3fee9c2d9714 are clean identified products; only destination.cpp path normalization/decomposition differs in their source.

| Tool | Median wall (s) | Median CPU (s) | Peak process RSS (MiB) |
|---|---:|---:|---:|
| reference-j4 | 2.465 | 7.078 | 38.0 |
| candidate-j1 | 4.951 | 3.851 | 29.7 |
| candidate-j2 | 3.055 | 4.704 | 33.3 |
| candidate-j4 | 2.361 | 7.108 | 38.2 |
| candidate-j8 | 2.164 | 9.960 | 43.0 |
| rsync | 2.361 | 2.890 | 25.0 |

At the matched four-worker budget, candidate wall time is 4.2% lower and CPU is 0.4% higher. This does not establish a CPU reduction. Even the one-worker candidate uses 3.85 s of CPU with substantially longer wall time. The under-one-second CPU requirement is not met, and no destination manifest is implemented; F-08 remains open.

The Mac remains busy and its physical backing volume is nearly full. Load averages are [89.0693359375, 55.46875, 46.0654296875] initially and [50.048828125, 34.396484375, 38.57958984375] finally. Samples are retained without trimming. These limitations make a small wall-time difference weak evidence; the comparison was serialized after the previous APFS matrix and before subtree-clone measurement. A new verified call-stack sample is queued after the filesystem-budget comparison to identify the remaining cost.

Raw evidence: [samples](20261010-f08-normalization.json), [complete log](20261010-f08-normalization.log).
