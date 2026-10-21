# APFS no-op diagnostic

Run `20261010T152712Z-apfs-baseline`, source revision `415900091024`. Three alternating-order samples per tool at each xs thread count. Every sample passed independent checksum/metadata verification.

The source slice has 76,838 regular files, 19,072 directories excluding the root, and 517,808,080 logical bytes. The Mac has 64 GiB RAM. The APFS volume was 98% full with 99 GiB available; initial load averages were 14.76 / 19.98 / 19.71. These observations require quieter and free-volume confirmation before setting defaults.

| xs threads | rsync wall s | xs wall s | rsync CPU s | xs CPU s | Largest process MiB rsync / xs | Evidence |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1.626 | 5.146 | 2.248 | 4.920 | 25.0 / 27.2 | [20261010T152712Z-apfs-baseline-j1.json](20261010T152712Z-apfs-baseline-j1.json) |
| 2 | 1.835 | 4.425 | 2.437 | 6.960 | 25.0 / 30.1 | [20261010T152712Z-apfs-baseline-j2.json](20261010T152712Z-apfs-baseline-j2.json) |
| 4 | 1.613 | 2.861 | 2.204 | 10.456 | 24.7 / 36.3 | [20261010T152712Z-apfs-baseline-j4.json](20261010T152712Z-apfs-baseline-j4.json) |
| 8 | 1.740 | 3.469 | 2.294 | 18.085 | 24.7 / 44.1 | [20261010T152712Z-apfs-baseline-j8.json](20261010T152712Z-apfs-baseline-j8.json) |

[Host/source metadata](20261010T152712Z-apfs-baseline-host.json). Cache policy retains existing OS caches. Setup and verification are untimed.

[A separately verified one-thread stack profile](20261010T152712Z-apfs-baseline-j1-profile.txt) places 1,556 of 2,476 worker-stack samples in `openat`, chiefly repeated anchored destination path component walks from collision checks and listing. `getattrlistbulk` accounts for 340 samples. These are sampled stack observations, not timings of individual syscalls.

The profile run is separate from the timing matrix. It passed an independent rsync checksum/metadata dry run before cleanup. Reproduce it after the matrix finishes:

```sh
python3 benchmarks/profile_apfs.py --corpus .bench/corpus --work .bench/p3-local --xsync build-release/xs --output benchmarks/results/20261010T152712Z-apfs-baseline-j1-profile.txt
```
