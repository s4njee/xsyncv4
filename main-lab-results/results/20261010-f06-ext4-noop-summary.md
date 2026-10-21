# Full-corpus ext4 no-op comparison

Neo (Raspberry Pi 5, Debian 13.5, four CPUs, 4 GiB RAM) runs a local re-sync on
its ext4 NVMe filesystem. The corpus is the full available Congress snapshot:
914,106 regular files, 417,408 directories and 10,528,134,423 logical bytes.
The clean xs product is f7e187827157, a static ARM64 musl Release build with
O3/LTO. [Product identities and hashes](20261010-f13-products.json) identify
the immutable binary used here.

| Tool | Median wall seconds | Median CPU seconds | Largest process peak MiB |
| --- | ---: | ---: | ---: |
| rsync | 99.884 | 80.856 | 284.25 |
| xs | 42.066 | 82.200 | 198.84 |

Four samples per tool alternate their starting order. Separate destinations
are seeded outside timing; every measured result passes an independent rsync
checksum/metadata dry run. Setup, verification and cleanup are untimed. All
eight samples and final cleanup complete. OS caches are retained; the corpus
is larger than Pi RAM, so this does not imply it is entirely memory-resident.

The tested product is 2.37x faster by wall-time median with similar summed CPU.
It contains both the Linux scan implementation and anchored directory reuse;
this comparison does not isolate each change's individual contribution.
[Complete raw results](20261010-f06-ext4-noop.json) and
[runner output](20261010-f06-ext4-noop.log) retain all samples.
