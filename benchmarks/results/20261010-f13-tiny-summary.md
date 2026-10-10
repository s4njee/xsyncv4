# Tiny SSH transfers on the quiet LAN pair

Revision `f7e187827157` runs on both endpoints. Each sample copies one 19-byte
file to a fresh destination; `rsync -anci --delete` independently verifies it.
There are 12 samples per tool per direction, with six samples per starting
tool order. All 48 samples and both endpoint processes succeed. Compression
and SSH connection sharing are disabled. The client is neo for both flows.

| Flow | rsync median ms | xs median ms | xs minus rsync ms | Evidence |
|---|---:|---:|---:|---|
| neo → freya | 189.135 | 168.813 | −20.322 | [JSON](20261010-f13-tiny-push.json) |
| freya → neo | 168.058 | 177.005 | +8.947 | [JSON](20261010-f13-tiny-pull.json) |

Both direction medians meet the target of at most 10 ms extra cost relative to
rsync. Individual samples vary: push rsync/xs ranges are 176.301–194.163 /
158.912–179.550 ms; pull ranges are 163.467–176.485 / 171.955–183.884 ms.
The result is a median comparison, not a latency guarantee for every transfer.

[All sample lines](20261010-f13-tiny.log),
[source/build identities and binary hashes](20261010-f13-products.json),
[native freya build output](20261010-f13-freya-build.log), and
[pre-run host load/cache snapshots](20261010-f13-load.json) are retained.
Neo uses the static musl Release product; freya compiles the same exported
source with its native GCC, O3 and LTO, linking its installed zstd and ICU.
Neither benchmark product replaces an installed helper or the frozen original
paired-suite binary. Initial three-sample baseline results remain retained
separately in the [paired table](20261010T144748Z-715fa0-summary.md).
