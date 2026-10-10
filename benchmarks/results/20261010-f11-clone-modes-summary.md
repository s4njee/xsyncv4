# APFS clones without permission preservation

Reference product `415900091024`; candidate `3c8ec2d22165`. Both were built with AppleClang Release `-O3` and LTO. Five samples per tool, rotated order, four xs workers and umask `0077`. Setup and independent checksum/metadata verification are excluded.

The 1 GiB file is read-only. The small fixture has 1,000 files (64 KiB each), 40 leaf directories and a symlink; rsync omits the symlink with `-rt`. Every result matches rsync contents, selection, modes, owner/group and nanosecond mtimes. Source metadata stays unchanged.

| Fixture | Options | Old xs s | Corrected clones s | xs byte copy s | rsync s | Gain vs old xs |
|---|---|---:|---:|---:|---:|---:|
| large | `-rt` | 0.297 | 0.008 | 0.294 | 2.144 | 37.3× |
| large | `-rlt` | 0.309 | 0.009 | 0.296 | 2.377 | 33.1× |
| small | `-rt` | 0.292 | 0.041 | 0.290 | 0.425 | 7.1× |
| small | `-rlt` | 0.281 | 0.044 | 0.275 | 0.430 | 6.4× |

The Mac had ten CPUs, high background load (1-minute average 25.3 at start, 44.1 at finish) and a 98%-full APFS data volume. This establishes the clone-path improvement on these fixtures; it does not select filesystem thread defaults or satisfy F-07’s free-volume measurement.

[Full verified measurements](20261010-f11-clone-modes.json) include binary/harness hashes, commands and resource metrics. [The initial per-file-only measurements](20261010-f11-per-file-clone-modes.json) retain the small-file regression that motivated leaf cloning.
