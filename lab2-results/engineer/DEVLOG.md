# Engineer log

Written by benchmarks/lab/engineer.py whenever a case moves: every case that has ended or waits for its merge, with its commit, the reason (the data) and its effect (since). Do not edit; it is rewritten.

## Cases

### 2026-10-19 22:51 · xs-rs, port step `config-frames` (`2db28ea9c31a`, merged)

**The data.** xs-wire: the configuration frames that follow HELLO. The first step of xs-rs, opened by hand by the operator while B is unreachable. Diagnosis: Read remote.cpp's run_client (around 2892) and run_server (around 3209) together with wire_test.py, compression_wire_test.py, chown_wire_test.py and filter_wire_test.py. The sandbox denies the benchmarks/lab path, so I built the same parent C++ source into rs/target/cpp-build and used that as XS_BIN. The first interop run exposed that the test HELLO had to negotiate ZSTD and XATTR_STREAM; after that the C++ server accepted all configuration frames in order.

**The change.** Added rs/xs-wire/src/config.rs with typed Config variants for all configuration frames, files-data/end helpers, frame-type and feature mapping, C++ size/count limits, and unnegotiated-feature refusal. Added byte-pinned unit tests, malformed-frame tests, and an interop test that sends the whole negotiated sequence to the C++ xs --server and expects F_DEST. Exported the module from lib.rs.

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.16.

### 2026-10-20 01:47 · xs-rs, port step `mvp` (`bbde3463d312`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/bbde3463d31242a8c544be1bdb4ea35fe8153b92

**The data.** xs-rs MVP: a Linux client and server that copy trees to and from the C++ xs, at least as fast. Opened by hand on the operator's go-ahead: one long session from rs/HANDOFF.md to a client and server that interoperate with the C++ xs. Diagnosis: The previous worktree had only the wire codec. The cost was in the transfer engine: listing, NEED generation, DATA records, XXH3 checksums, zstd bodies and destination publication all had to be written and matched to remote.cpp. Measurements on real-projects through fakessh: C++ xs fresh 28.3 s and 44.6 s, xs-rs fresh 23.3 s and 36.1 s; C++ no-op 10.5 s and 11.2 s, xs-rs no-op 5.0 s and 5.1 s. The C++ runs also reported exit 23 on an unreadable source subdirectory.

**The change.** New rs/xs-rs crate (client, --server, CLI, scanner, codec, transfer engine) in the rs workspace; system libxxhash/libzstd linked from build.rs; integration tests under rs/xs-rs/tests; README and workspace manifest updated. A root workspace package was added solely so the required `cargo fmt --manifest-path rs/Cargo.toml --check` has a target in this cargo version. (pull request #3)

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.29.

### 2026-10-20 15:22 · xs-rs, port step `zstd` (`3cdf98e39da3`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/3cdf98e39da34923a42db4a832d7b44baf087b15

**The data.** zstd: compressed directory listings and data blocks (PF_ZSTD). Diagnosis: The starting tree had only a partial zstd path: it always compressed at level 1, did not sample bodies, did not implement --skip-compress or the compression configuration frame, and did not isolate skipped suffixes. The C++ reference (src/compression.cpp, pack/unpack and flush_block in src/remote.cpp) showed the missing policy and framing rules.

**The change.** Added xs-wire::compress for the reference suffix syntax and defaults; added xs-rs::compression for compression_worthwhile, CompressionLink and adaptive/explicit levels; added pack_body matching src/remote.cpp; added COMPRESS_POLICY negotiation plus F_COMPRESS_CONFIG send/read/validation; added --skip-compress and --compress-choice; and isolated skipped-suffix DATA blocks as RawFileBlock does. (pull request #4)

**Since.** The lab's screen of xs-rs after this step (PS-3cdf98e39da3) is queued against xs-c++ and rsync. API cost $0.13.

### 2026-10-20 15:50 · xs-rs, port step `idmap` (failed)

**The data.** user and group names (PF_IDMAP, PF_CHOWN). No performance gap now warrants an engineering case, and idmap is the next unmerged port step, so the Rust port can advance without pausing the Mac runner.

**The change.** None kept.

**Since.** Failed: -R g+rwX exited 1: e052': Operation not permitted chmod: changing permissions of '~/xsyncv4-auto/XR10201529-idmap/rs/target/tmp': Operation not permitted chmod: changing permissions of '~/xsyncv4-auto/XR10201529-idmap/rs/target/CACHEDIR.TAG': Operation not permitted chmod: changing permissions of '~/xsyncv4-auto/XR10201529-idmap/rs/target/.rustc_info.json': Oper

### 2026-10-20 16:19 · xs-rs, port step `idmap` (`02bd26868504`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/02bd268685045570cd5cecf99f508d30a63d1a99

**The data.** user and group names (PF_IDMAP, PF_CHOWN). Diagnosis: Read the C++ IdMaps, run_client/run_server configuration order, and ownership resolution first, then added the wire format, sender/receiver mapping, config negotiation, CLI parsing, and actual chown calls. Verified against the parent's C++ xs with the gate tests and the repository's tests/chown_wire_test.py pointed at xs-rs; all pass.

**The change.** Added xs_wire::idmap for F_IDMAP records; added xs-rs idmap state, libc name/id lookups, --chown parsing and resolution, CHOWN_CONFIG negotiation/validation, IDMAP advertisement and send/receive, name mapping on DIR and DATA attributes, ownership overrides, and best-effort fchown/lchown/chown of files, directories, symlinks and FIFOs. Added integration tests under rs/xs-rs/tests/ownership.rs. (pull request #5)

**Since.** The lab's screen of xs-rs after this step (PS-02bd26868504) is queued against xs-c++ and rsync. API cost $0.10.

### 2026-10-20 16:56 · xs-rs, port step `io-control` (`deb9d92657aa`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/deb9d92657aaa03e66d724f982f4ce98ed834ccb

**The data.** keepalives, bandwidth limits and timeouts (PF_IO_CONTROL). Diagnosis: The C++ reference in src/rate_limit.cpp, Conn::configure/check_timeout/writer, run_client and run_server, plus tests/io_limit_test.py defined the work. The previous xs-rs advertised no IO_CONTROL, sent no IO_CONFIG, accepted keep-alives unconditionally and had no rate or idle deadline; its receiver also wrote synchronously, so it could not emit heartbeats during long work. I matched the C++ frame order and rejection messages, added a writer thread for receiver-side heartbeats, and verified pacing with a measured 512 KiB transfer at 256 KiB/s that stayed above the 1.5 s floor.

**The change.** Added xs-wire/src/io_control.rs with parse_rate/parse_timeout, the RateLimiter token bucket, IoControl deadlines and heartbeat state, an ActivityReader, and a watchdog. Added --bwlimit and --timeout to xs-rs CLI/Options, negotiated IO_CONTROL, sent and validated IO_CONFIG first after HELLO, wired rate limiting and keep-alives into the writer, moved receiver output onto the same queued writer, and enforced idle exit 30. Extended integration coverage under rs/*/tests/. (pull request #6)

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.12.

### 2026-10-20 18:04 · xs-rs, port step `output` (`2413c9f0288c`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/2413c9f0288cb568718084594ce6ba3bf55c333a

**The data.** itemized output and progress (PF_OUTPUT, PF_DIR_OUTPUT, PF_PROGRESS_ACK). Diagnosis: The work was protocol and interop work rather than benchmarking: the C++ reference puts per-entry size/source fields in DIR whenever PF_OUTPUT is negotiated, directory size/attr_source in the DIR header only with PF_DIR_OUTPUT, output events on F_OUTPUT, and completion snapshots on F_PROGRESS. The time went into matching those layouts and validating them against the parent binary; the new integration suite runs each direction across both implementations plus hostile-peer cases.

**The change.** Added xs-wire::output with byte-pinned OutputEvent, OutputConfig handling and ProgressAck codecs plus strict C++-style validation. Advertise PF_OUTPUT, PF_DIR_OUTPUT and PF_PROGRESS_ACK conditionally; send and parse OUTPUT_CONFIG in feature order; add the PF_OUTPUT per-entry fields and PF_DIR_OUTPUT directory header fields. xs-rs now renders %i/%n/%f/%L/%l/%b/%o/%t/%% with C++ escaping and sorted output, generates itemized events for local and remote receivers, sends throttled progress snapshots before DONE, and refuses malformed, unnegotiated or oversized output/progress frames. (pull request #7)

**Since.** The lab's screen of xs-rs after this step failed: stage.py build of xs-rs at 2413c9f0288c failed; see port-screen-2413c9f0288c.log API cost $0.16.

### 2026-10-20 19:02 · xs-rs, port step `hlink` (`5a4536053183`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/5a4536053183a5edf3e36a5ded4640bfdd8d93b4

**The data.** hard links (PF_HLINK). Diagnosis: Most of the work went into reading src/hardlink.cpp and remote.cpp and reproducing hardlink_finalize's anchor selection and output rows, not into transport changes. Measurements: the 5 new interop tests and 3 byte-pinned unit tests pass against the supplied C++ binary; manual -aH -i comparisons for C++ client push, C++ sender pull, Rust client push and local copy are identical to the C++ xs output; the C++ client reports one regular file transferred for four linked names and zero when a new name is added. All four required gate commands exited 0.

**The change.** Added put_hlink/get_hlink, Attrs inode fields and HardlinkKey to rs/xs-rs/src/protocol.rs; populated them in scan.rs; added -H/--hard-links and HLINK negotiation in cli.rs/main.rs; added the receiver's hard-link registry, follower skipping, link publication and C++-matching finalizer in transfer.rs. Also changed ffi.rs's local_time buffer from [i8; 64] to [c_char; 64] so the required aarch64 check passes. (pull request #8)

**Since.** The lab's screen of xs-rs after this step (PS-d84368234dad-noop, PS-d84368234dad-fresh) is queued against xs-c++ and rsync. API cost $0.15. For xs-c++: No C++ performance change follows from this step: hardlink_finalize's anchor and itemization rules were matched rather than replaced. The only portability correction was on the Rust side, using c_char rather than i8 for the strftime buffer.

### 2026-10-20 19:32 · xs-rs maintenance: simplifications and the changelog (`d84368234dad`, merged)

**The data.** Maintenance: simplify xs-rs, and log what merged in README.md. Diagnosis: The dominant problem was rs/xs-rs/src/transfer.rs at 1,826 lines, mixing the sender, receiver, hard-link grouping, destination file handling and shared frame/event helpers. I read it end to end, traced which helpers both engines use, and cut at function boundaries so no logic changed. transfer.rs is now 735 lines; the receiver is 687, hard links 266 and destination files 170. main.rs fell from 672 to 528 lines after moving 157 lines of configuration-frame handling into config.rs. The measured change is 2,562 lines including the README entry, under the 3,000-line budget.

**The change.** Moved the receiver engine to transfer/receiver.rs, hard-link logic to transfer/hardlink.rs and destination file helpers to transfer/file.rs, leaving the sender and shared helpers in transfer.rs. Extracted read_configuration, config_frame and read_config_frame into src/config.rs. Reused scan::kind_of instead of a duplicate metadata-kind mapping in the hard-link code. Factored the duplicated InFile construction used by DATA CHUNK and END records into open_infile. Removed process_dir's unused input parameter. Added module documentation and the dated README changelog listing all seven merged steps and the four cleanups.

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.08.

### 2026-10-20 19:41 · xs-rs, port step `resume` (abandoned)

**The data.** resuming partial files (PF_RESUME).

**The change.** None kept.

**Since.** Abandoned: set aside before its session started: the parallel-workers step goes first (sprint of 2026-10-20)

### 2026-10-20 20:07 · xs-rs, port step `workers` (`e3b546f679b9`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/e3b546f679b970ac4b718bc9e983ae40c35ea359

**The data.** parallel workers: -j/--jobs, default 4, splitting the file work as the C++ engine does; unsupported options are refused, not ignored. Diagnosis: The previous sender scanned and emitted DATA entirely on one thread and the receiver wrote every CHUNK inline in its frame loop; reading `src/remote.cpp:1560-1600` and `:2498-2510` showed the C++ only splits ranges when the raw `jobs` value is greater than one, and only unlocks concurrent per-file writes when that directory's `file_ranges` is true. The Rust HELLO writer also dropped the `jobs` INT_OPTIONS slot (index 5), so a C++ server never saw the client's budget. No timing regression was measured because the step is structural; correctness was measured by the parent range suite (26.25 s) and the cargo interop suite.

**The change.** Added `rs/xs-rs/src/parallel.rs` with the default budget (4, clamped to MAX_WORKERS 64), explicit-range detection, parallel pread ranges, and a bounded-by-END write pool using pwrite. Threaded `jobs` through `Options`, the client HELLO and `options_from_flags`; `send_large`/`send_need_data` now split only when `-jN` (N>1) was explicit and at most one large file is in the NEED; the receiver stores completion context in `InFile` and publishes only after all queued writes finish. Rewrote relevant CLI parsing to add `-j`/`--jobs`, the C++ unsupported list, and unknown-option refusal, with `--help`/`--version`. (pull request #9)

**Since.** Measured by the lab (PS-e3b546f679b9-noop, PS-e3b546f679b9-fresh, time to durable): xs-rs 2.008x xs-c++ [1.499, 2.691], too few blocks, on congress-sample noop (3 blocks); rsync 1.904x xs-c++ [1.724, 2.101], too few blocks, on congress-sample noop (3 blocks). API cost $0.15.

### 2026-10-20 20:46 · xs-rs, port step `resume` (`2c0bec1da693`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/2c0bec1da6930369686d8965b2c074bb47459bcd

**The data.** resuming partial files (PF_RESUME). Diagnosis: Before this step xs-rs did not advertise or parse RESUME, so a partially present destination was retransmitted in full. The C++ reference resume tests now pass 4/4 against the Rust server, and the new interop tests show a 4 MiB file with a verified 3 MiB destination prefix placing less than 2 MiB of DATA on the wire instead of the full file.

**The change.** Added xs-wire::resume for the NEED prefix layout (size, then XXH3-128 low/high) and the receiver's validation rules. Added XXH3-128 streaming through libxxhash, destination/source prefix hashing and restore in xs-rs/src/resume.rs, PF_RESUME advertisement (withdrawn by --whole-file), --partial/-P and -W/--no-whole-file parsing, prefix fields in NEED/DATA/END, overlap detection, failed-prefix rejection, and partial cleanup matching fs.cpp. (pull request #10)

**Since.** Measured by the lab (PS-2c0bec1da693-noop, PS-2c0bec1da693-fresh, time to durable): xs-rs 1.740x xs-c++ [0.949, 3.191], too few blocks, on congress-sample noop (3 blocks); rsync 1.838x xs-c++ [1.577, 2.144], too few blocks, on congress-sample noop (3 blocks). API cost $0.22.

### 2026-10-20 21:45 · xs-rs, port step `delta` (`f4e30e4ed207`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/f4e30e4ed207e8bfd17db793a42d1e8523b3e447

**The data.** delta transfer of changed files (PF_DELTA). Diagnosis: This step targets wire volume rather than a timed optimization. With the frame recorder, a 4 MiB file with a 100 KiB changed region sent less than half the file as DATA in all four interop directions; before PF_DELTA the same runs send the whole file. The new receiver tests also confirm that a bad digest or changed basis publishes nothing and exits 23.

**The change.** Added rs/xs-rs/src/delta.rs (signature generation/encoding, streaming block matcher, basis verification) and wired PF_DELTA through sender NEED parsing, F_DELTA_REQUEST/signature exchange, LITERAL/COPY/DELTA_END emission, receiver signature replies, retry acks, serialized delta writes and final digest checks. Also added --ignore-times/-I and the HELLO flag so the C++ delta tests can force a transfer. (pull request #11)

**Since.** The lab's screen of xs-rs after this step (PS-3b42279cc4fc-noop, PS-3b42279cc4fc-fresh) is queued against xs-c++ and rsync. API cost $0.22.

### 2026-10-20 22:00 · xs-rs, port step `filters` (failed)

**The data.** filters, relative paths and files-from (PF_FILTERS, PF_RELATIVE, PF_FILES_FROM).

**The change.** None kept.

**Since.** Failed: the agent session ended without a report (error_invalid_report: the last message held no valid report); $0.01 spent

### 2026-10-20 22:37 · xs-rs, tuning to beat xs-c++ on congress-sample noop (`3b42279cc4fc`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/3b42279cc4fc50390170c444a157cdece631c751

**The data.** xs-rs performance: beat xs-c++ on congress-sample noop. Diagnosis: strace -f -c on the congress-sample no-op (25,246 files, 9,797 directories, source and dest both warm) showed xs-rs making 449,121 syscalls against xs-c++'s 438,098, but with a very different mix: 35,044 chown, 35,044 utimensat and 9,798 chmod calls, plus an extra fs::metadata statx per unchanged file (124,725 statx total versus C++'s 62,216). Reading src/fs.cpp:tweak_attrs and the same_secs path showed C++ only calls set_mtime/chmod/chown when the attribute differs; its no-op run had one utimensat and no chown or chmod. The rs receiver applied final directory metadata unconditionally too, dirtying every directory inode. Those writes are cheap on a local warm cache but are exactly the per-inode work that is expensive on the lab's AWS receiver and its durable sync.

**The change.** In rs/xs-rs/src/transfer/receiver.rs and transfer/file.rs: reuse the parent DIR listing's destination metadata instead of stat-ing each child directory again; skip mtime/perms/chown on unchanged regular files, symlinks and FIFOs; add chown_changed() and dir_attrs_differ() so ownership and directory metadata are written only when they differ; only push a FinalDir when the directory was created, modified, or its working mode changed. dir_modified tracks child creation/removal/transfer so a directory whose contents changed still gets its source mtime and mode restored. (pull request #12)

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.10.

### 2026-10-20 23:38 · xs-rs, port step `filters` (`3b891bf5e8fb`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/3b891bf5e8fb51c26f64347a4163e81fe3c0c2d9

**The data.** filters, relative paths and files-from (PF_FILTERS, PF_RELATIVE, PF_FILES_FROM). Diagnosis: The gate counted 1,231 changed lines because it includes both additions and deletions: 1,198 additions plus 33 deletions. I removed 32 implementation lines that were not needed for the wire feature (the unused --exclude-from/--include-from file reader, the -F short option, and legacy '+ '/'- ' old-style overrides), leaving 1,162 additions and 33 deletions. The full suite reports 21+5+9+6+5+9+5+12+8+4+3+31+4+4 passing tests, including the six new filters/relative/files-from interop tests.

**The change.** Added rs/xs-rs/src/filter.rs (rule parsing, wildmatch, per-directory merge rules); extended DIR entries with the selected-directory byte and filter-source string; taught the server to read RELATIVE_CONFIG, the FILES_CONFIG/FILES_DATA/FILES_END stream with acknowledgement, and FILTER_CONFIG in C++ order; taught the client to advertise and send those frames plus HELLO legacy rules; added --filter/-f, --exclude/--include, --files-from, -0/--from0 and -C; and added relative/files-from selection with implied directories, selected flags, duplicate-name merging and receiver-side unrequested-name rejection. (pull request #13)

**Since.** Measured by the lab (PS-8428aac9a210-fresh, PS-8428aac9a210-update-10pct, time to durable): xs-rs 1.213x xs-c++ [0.496, 2.969], too few blocks, on congress-sample fresh (3 blocks); rsync 0.906x xs-c++ [0.887, 0.924], too few blocks, on congress-sample fresh (3 blocks); xs-rs 1.025x xs-c++ [0.036, 29.180], too few blocks, on congress-sample update-10pct (2 blocks); rsync 1.047x xs-c++ [0.281, 3.899], too few blocks, on congress-sample update-10pct (2 blocks). API cost $0.27.

### 2026-10-20 23:47 · xs-rs, port step `xattrs` (failed)

**The data.** extended attributes (PF_XATTRS, PF_XATTR_STREAM).

**The change.** None kept.

**Since.** Failed: ~/xsyncv4/benchmarks/lab/engineer.py prepare exited 1: ubprocess.py", line 577, in run raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr) subprocess.CalledProcessError: Command '['git', '-C', '~/xsyncv4', 'worktree', 'add', '-b', 'auto/XR10202347-xattrs', '~/xsyncv4-auto/XR10202347-xattrs', '3b891bf5e8f

### 2026-10-20 23:55 · xs-rs, port step `xattrs` (failed)

**The data.** extended attributes (PF_XATTRS, PF_XATTR_STREAM).

**The change.** None kept.

**Since.** Failed: ~/xsyncv4/benchmarks/lab/engineer.py prepare exited 1: ubprocess.py", line 577, in run raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr) subprocess.CalledProcessError: Command '['git', '-C', '~/xsyncv4', 'worktree', 'add', '-b', 'auto/XR10202355-xattrs', '~/xsyncv4-auto/XR10202355-xattrs', '3b891bf5e8f

### 2026-10-21 00:05 · xs-rs, port step `xattrs` (failed)

**The data.** extended attributes (PF_XATTRS, PF_XATTR_STREAM).

**The change.** None kept.

**Since.** Failed: ~/xsyncv4/benchmarks/lab/engineer.py prepare exited 1: ubprocess.py", line 577, in run raise CalledProcessError(retcode, process.args, output=stdout, stderr=stderr) subprocess.CalledProcessError: Command '['git', '-C', '~/xsyncv4', 'worktree', 'add', '-b', 'auto/XR10210005-xattrs', '~/xsyncv4-auto/XR10210005-xattrs', '3b891bf5e8f

### 2026-10-21 00:53 · xs-rs, tuning to beat xs-c++ on congress-sample noop (abandoned)

**The data.** xs-rs performance: beat xs-c++ on congress-sample noop.

**The change.** None kept.

**Since.** Abandoned: postponed: the lab works on copies that move data for now, and comes back to no-op copies later

### 2026-10-21 12:47 · xs-rs, port step `xattrs` (`b47b9014adfd`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/b47b9014adfd8df2a8bfce805ba849329df8fa76

**The data.** extended attributes (PF_XATTRS, PF_XATTR_STREAM). Diagnosis: Most work went into matching src/xattrs.cpp namespace rules (user.*, user.rsync.% internal names, -X versus -XX) and the remote.cpp framing: XATTR_CONFIG after compression, XATTR_START/CHUNK/END before the DIR/DATA that references them, and xattr fields after filter_source and after HLINK. Tests pin the exact list bytes and verify a 65 KiB streamed value round-trips with the C++ digest.

**The change.** New rs/xs-rs/src/xattr.rs implements xattr reading/writing via llistxattr/lgetxattr/lsetxattr/lremovexattr, protocol list encoding/decoding, stream sender/receiver, namespace mapping and filters. Wired -X/--xattrs/--no-xattrs and -XX into CLI, HELLO feature advertisement and validation, XATTR_CONFIG handling, DIR entry and DATA attribute encoding/decoding, and receiver application for files, directories, links and special files. Added xattr filter predicates to FilterList. (pull request #14)

**Since.** Measured by the lab (PS-b47b9014adfd-fresh, PS-b47b9014adfd-update-10pct, time to durable): xs-rs 0.988x xs-c++ [0.892, 1.093], too few blocks, on congress-sample fresh (3 blocks); rsync 0.897x xs-c++ [0.837, 0.961], too few blocks, on congress-sample fresh (3 blocks); xs-rs 1.193x xs-c++ [1.023, 1.392], too few blocks, on congress-sample update-10pct (2 blocks); rsync 1.110x xs-c++ [0.724, 1.703], too few blocks, on congress-sample update-10pct (2 blocks). API cost $0.21. For xs-c++: Nothing to change: xs-c++'s put_xattrs/get_xattrs, namespace rules and stream framing are correct and are followed byte for byte; the new code lives entirely under rs/.

### 2026-10-21 13:34 · xs-rs, port step `acls` (`71872a77ee26`, merged)

**Commit.** https://github.com/s4njee/xsyncv4/commit/71872a77ee26922af3eb19089d87342ab2185980

**The data.** POSIX ACLs (PF_ACL_POSIX). Diagnosis: The work was protocol and metadata conversion, not throughput: Linux system.posix_acl_access/default values are exported to validated records and imported back to canonical kernel values, mirroring src/acls.cpp and put_acls/get_acls. Under -A the only added steady-state cost is up to two lgetxattr reads per inode; no transfer timing regression was measured or targeted for this metadata step.

**The change.** Added rs/xs-rs/src/acls.rs with POSIX ACL read/write, record export/import, the C++ validation rules, and exact put_acls/get_acls codecs. Wired -A/--acls through cli, Options and HELLO advertisement; added ACL style refusals and ACL_CONFIG send/read in the C++ frame order; encoded ACLs after xattrs in DIR and DATA records; applied ACLs to files, FIFOs, specials and directories; and marked incomplete ACL metadata so existing destination files are preserved and the transfer exits 23. (pull request #15)

**Since.** Measured by the lab (PS-61d1dd83a530-fresh, PS-61d1dd83a530-update-10pct, time to durable): xs-rs 0.846x xs-c++ [0.780, 0.918], too few blocks, on congress-sample fresh (3 blocks); rsync 0.908x xs-c++ [0.840, 0.982], too few blocks, on congress-sample fresh (3 blocks); xs-rs 1.192x xs-c++ [0.047, 30.253], too few blocks, on congress-sample update-10pct (2 blocks); rsync 1.194x xs-c++ [0.859, 1.659], too few blocks, on congress-sample update-10pct (2 blocks). API cost $0.20.

### 2026-10-21 19:44 · xs-rs maintenance: simplifications and the changelog (`61d1dd83a530`, merged)

**The data.** Maintenance: simplify xs-rs, and log what merged in README.md. Diagnosis: The first gate measured 5,147 changed lines because splitting both `transfer.rs` and `transfer/receiver.rs` moved roughly 2,500 lines in each direction. I kept the receiver split only: `transfer/receiver.rs` went from 1,710 to 546 lines, with `receiver/dir.rs` (632) and `receiver/data.rs` (593). Final diff is 1,255 insertions and 1,182 deletions, total 2,437, under the 3,000-line ceiling.

**The change.** Moved directory decoding/comparison/generation into `transfer/receiver/dir.rs` and DATA decoding/assembly/publication into `transfer/receiver/data.rs`, leaving `receiver.rs` as coordination and worker scheduling. Removed the unused `FileRequests.dirs` field and its dead-code suppression. README gained only the dated changelog section.

**Since.** Merged; the lab has not screened xs-rs since. API cost $0.15.
