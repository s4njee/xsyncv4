# Where rsync wins, Mac ↔ apollo (2026-10-23)

The deliverable of the user's 24-hour mac-mac plan (phase 2, the RW hunt), run against apollo: mars's box on Arch
Linux, ext4 on NVMe, Intel X540 on the Mac's direct 10 GbE cable. Cells where rsync -a is at least 5% faster to durable
than xs-c++ (cc8288d4, -a -j4) or xs-rs (e671c84a -a -j4, or PR #34's ac1aeef0 at plain -a), as the geometric mean of
each block's time over rsync's in the same block. RW cells have 3 blocks (screening); MM2 cells 17–20.

## Ranked

| xs / rsync | Build | Cell | Arm | Blocks |
|---|---|---|---|---|
| 3.58 | e671c84 | large-text update-1pct Mac→apollo | xs-c++ | 3 |
| 3.04 | e671c84 | large-text append-1pct apollo→Mac | xs-c++ | 3 |
| 2.62 | e671c84 | large-solo update-1pct apollo→Mac | xs-c++ | 3 |
| 2.55 | e671c84 | large-text update-1pct apollo→Mac | xs-c++ | 3 |
| 2.53 | PR #34 | large-solo update-1pct apollo→Mac | xs-c++ | 3 |
| 2.49 | PR #34 | large-text update-1pct apollo→Mac | xs-c++ | 3 |
| 2.47 | e671c84 | large-text append-1pct Mac→apollo | xs-c++ | 3 |
| 2.32 | MM2 | large-solo update-1pct apollo→Mac | xs-c++ | 20 |
| 2.31 | e671c84 | large-solo append-1pct apollo→Mac | xs-c++ | 3 |
| 2.28 | PR #34 | large-solo append-1pct apollo→Mac | xs-c++ | 3 |
| 2.27 | e671c84 | mixed-threshold fresh Mac→apollo | xs-c++ | 3 |
| 2.23 | PR #34 | large-text append-1pct apollo→Mac | xs-c++ | 3 |
| 1.70 | e671c84 | large-solo append-1pct Mac→apollo | xs-c++ | 3 |
| 1.61 | e671c84 | large-text update-1pct Mac→apollo | xs-rs | 3 |
| 1.58 | PR #34 | large-text append-1pct Mac→apollo | xs-c++ | 3 |
| 1.47 | e671c84 | large-solo append-1pct Mac→apollo | xs-rs | 3 |
| 1.42 | PR #34 | large-text append-1pct Mac→apollo | xs-rs | 3 |
| 1.39 | e671c84 | large-solo update-1pct Mac→apollo | xs-c++ | 3 |
| 1.34 | e671c84 | large-solo update-1pct Mac→apollo | xs-rs | 3 |
| 1.33 | e671c84 | large-text append-1pct Mac→apollo | xs-rs | 3 |
| 1.30 | e671c84 | large-text append-1pct apollo→Mac | xs-rs | 3 |
| 1.30 | e671c84 | large-solo update-1pct apollo→Mac | xs-rs | 3 |
| 1.26 | e671c84 | large-solo append-1pct apollo→Mac | xs-rs | 3 |
| 1.25 | PR #34 | large-solo update-1pct apollo→Mac | xs-rs | 3 |
| 1.25 | MM2 | large-solo update-1pct apollo→Mac | xs-rs | 20 |
| 1.23 | PR #34 | large-text append-1pct apollo→Mac | xs-rs | 3 |
| 1.22 | PR #34 | large-solo append-1pct apollo→Mac | xs-rs | 3 |
| 1.21 | PR #34 | large-text update-1pct apollo→Mac | xs-rs | 3 |
| 1.21 | MM2 | large-solo update-1pct Mac→apollo | xs-c++ | 17 |
| 1.18 | e671c84 | large-text update-1pct apollo→Mac | xs-rs | 3 |
| 1.16 | MM2 | local-laikav2 update-10pct apollo→Mac | xs-rs | 17 |
| 1.12 | e671c84 | local-laikav2 fresh Mac→apollo | xs-c++ | 3 |
| 1.12 | PR #34 | large-solo append-1pct Mac→apollo | xs-c++ | 3 |
| 1.08 | MM2 | large-solo update-1pct Mac→apollo | xs-rs | 17 |

(The "PR #34" rows' xs-c++ is the same cc8288d4 build; only their xs-rs differs.)

## For the next development case

1. **Delta updates of large files are the case.** 29 of the 34 rows are small changes in big files: a 4 KiB edit
   (update-1pct) or a grown tail (append-1pct) in large-text (8 × 1 GiB) or large-solo (4 GiB). rsync sends only the
   changed blocks; xs-c++ is 1.4–3.6× slower, xs-rs 1.1–1.6×. xs-rs is about twice as close as xs-c++ here, so its
   approach is the one to study. PR #34 does not change it.
2. **mixed-threshold fresh, Mac→apollo, xs-c++ 2.27×**: the one large loss on a fresh copy, files of 1 KiB–8 MiB
   around xs's split thresholds. Worth a confirmatory run before treating it as real (3 blocks).
3. Small: local-laikav2 update-10pct apollo→Mac for xs-rs (1.16×, 17 blocks), and laikav2 fresh Mac→apollo for
   xs-c++ (1.12×, 3 blocks).

No --checksum no-op (RW2), many-file no-op (RW3), 1 MiB / 16 MiB fresh (RW4), --delete (RW5) or -H (RW6) cell shows
rsync ahead by 5% on apollo: on Linux xs wins those, unlike real-psample's pull on macOS (NT1021).
