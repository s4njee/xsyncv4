# F-08 verified APFS no-op call stacks — 2026-10-10

The one-worker no-op run of clean 741ebdcc127f passes independent rsync checksum/metadata verification. `/usr/bin/sample` records stacks every millisecond for up to three seconds; these are sampled thread locations, not CPU attribution or throughput measurements.

Of 2,210 worker-thread samples, 1,133 have `__openat` at the top; directory traversal in `destination_open_dir`/`destination_path` and collision checking account for prominent call paths. Other frequent tops include `getattrlistbulk` (334), `__open` (263), `__getattrlist` (138), stat (92) and fstatat (63). `SourceGuard::excludes` appears in 243 worker samples under source pruning. The main thread predominantly waits for the pool. Counts from different threads must not be added as CPU percentages.

The remaining cost warrants investigating repeated directory opens and identity checks while preserving no-follow traversal and directory-swap protection. This profile alone does not justify removing those checks or establishing the under-one-second CPU target. F-08 remains open; the previous negative normalization comparison remains retained.

Evidence: [call stacks](20261010-f08-apfs-profile.txt), [product identity and verification](20261010-f08-apfs-profile-products.json), [stdout](20261010-f08-apfs-profile.stdout), [stderr](20261010-f08-apfs-profile.stderr).
