# F-07 free APFS container comparison — 2026-10-10

All 72 timed samples and 12 excluded warmups complete and pass independent rsync checksum/metadata verification. Each tool/case has six rotated timed samples. Reference 7c3072c821cc and candidate 24b82c5d5134 are clean identified products; rsync is 3.4.4. Cloning is disabled.

| Case | Tool | Median wall (s) | Median CPU (s) | Peak process RSS (MiB) |
|---|---|---:|---:|---:|
| fresh-byte | reference-j4 | 37.663 | 39.704 | 61.8 |
| fresh-byte | candidate-j1 | 38.241 | 22.634 | 58.6 |
| fresh-byte | candidate-j2 | 30.661 | 26.376 | 59.6 |
| fresh-byte | candidate-j4 | 29.833 | 29.105 | 63.3 |
| fresh-byte | candidate-j8 | 29.910 | 32.649 | 68.2 |
| fresh-byte | rsync | 28.556 | 23.843 | 37.5 |
| noop | reference-j4 | 4.428 | 10.990 | 38.0 |
| noop | candidate-j1 | 5.282 | 4.116 | 30.9 |
| noop | candidate-j2 | 3.873 | 4.971 | 33.4 |
| noop | candidate-j4 | 2.619 | 6.757 | 40.0 |
| noop | candidate-j8 | 2.372 | 9.194 | 46.9 |
| noop | rsync | 2.335 | 2.544 | 26.6 |

The candidate at four workers improves fresh byte-copy wall time 1.26x and no-op wall time 1.69x against the reference at four. Four and eight candidate workers have similar fresh-copy medians (29.833/29.910 s); eight uses 12.2% more CPU. Eight workers improve no-op wall time by 9.4% relative to four, with 36.1% more CPU.

Interpret these as measurements on this host, not quiet physical-disk qualification. The sparse image had a mostly empty 16 GiB APFS container, but its physical backing volume was 98% full. Load averages rose from [46.74072265625, 29.39404296875, 26.728515625] to [96.3193359375, 53.7626953125, 45.20361328125]. Local builds, gate self-tests and correctness suites overlapped early fresh-copy measurements. All outliers are retained, including the 90.775 s reference fresh sample, 51.136 s candidate-j2 fresh sample and 7.294 s rsync no-op sample. A virtualization process held handles to the disposable image after measurement; the runner saved a complete result before normal detach failed.

The comparison shows the wall/CPU tradeoff between four and eight APFS workers. It does not isolate physical free-space effects or establish the final automatic filesystem budget. F-07 remains partial.

Raw evidence: [samples](20261010-f07-free-container.json), [log](20261010-f07-free-container.log), [container/backing metadata](20261010-f07-free-container-metadata.json), [cleanup](20261010-f07-free-container-cleanup.json).
