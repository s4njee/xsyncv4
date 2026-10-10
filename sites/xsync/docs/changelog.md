---
title: "xs-changes(7)"
description: "What changed in each version, with links to the backlog stories behind each entry."
manual: "xs-changes(7)"
manualName: "Changelog"
sectionNumber: "7"
---

# xs-changes(7)

<div class="manual-deck"><strong>Changelog</strong><p>What changed in each version, with links to the backlog stories behind each entry.</p></div>

## CHANGES {#changes}

All notable changes to xsync (the `xs` executable). Story IDs refer to
[backlog.md](https://github.com/s4njee/xsyncv4/blob/main/backlog.md), where each one has its verification evidence.

### Unreleased — 0.1.0, protocol 4

No release has been tagged yet. This section covers everything up to the
current `main`.

#### Changed

- The executable is now `xs` in every build, install and release (`xs-linux-amd64`,
  `xs-linux-arm64`, `xs-darwin-universal`). `XSYNC_*` environment variables and
  `~/.config/xsync/config` keep their names.
- Native remote transfers use protocol 4 and still interoperate with protocol-3 peers.
  Optional capabilities are negotiated as feature bits instead of requiring equal
  versions (R-06).
- New byte-copied files are written to a temporary name and renamed after verification
  by default; `--no-atomic` writes them directly (T-11).
- Progress is shown by default when stderr is a terminal, and stays off in scripts;
  `--no-progress` and `XSYNC_PROGRESS` override it (U-06).

#### Added

- Automatic fallback to a real rsync for unsupported options, daemon URLs and remote
  hosts without a compatible `xs`, with a one-line notice; `--no-fallback` and
  `XSYNC_FALLBACK=0` for strict native runs (R-02).
- Static release binaries for Linux amd64/arm64 and a macOS universal binary (R-03),
  explicit `xs --install HOST` (R-04), automatic helper lookup on the remote host (R-05),
  `cmake --install` with a generated manpage and zsh completion (R-07), IPv6 and unusual
  host specs (R-08), and personal defaults in `XSYNC_OPTS` and a config file (R-09).
- Verified-prefix resume for `-P`/`--partial` (E-01); `--out-format`, `--log-file` and
  stable sorted script output (E-02); rsync-compatible itemization, including `-ii` (E-03).
- Block-matching delta transfers for large changed files, locally and remotely (E-04).
- Source listing and `--list-only` (E-05), and a bounded end-of-run error summary (E-06).
- `--bwlimit`, `--timeout` and keep-alives (E-07).
- Filter rule sides, merge files, `-F`, `-C`, `--delete-after` and `-m` (E-08).
- `--files-from`, `-R` and `-0` (E-09).
- Metadata beyond `-a`: `-H`, `-X`, `-A`, `-E`, `-U`, `-N`, `--fileflags`, `--chmod` and
  `--chown` (E-10).
- `-S` sparse files and `--link-dest` snapshots (E-11).
- macOS dataless files, sockets and immutable files (E-12).
- Prompt cancellation when stdout is closed, with exit 13 (E-13).
- Calmer progress rows for small files (U-02), directory clone activity (U-03),
  receiver-acknowledged push progress (U-04), wire rate, compression ratio and the
  limiting stage (U-05), `--info=progress2` and `--progress=json` (U-07), explicit
  phases such as `deleting`, `verifying` and `waiting for receiver` (U-08), dry-run plan
  summaries (U-09), one size-unit rule everywhere (U-10), and suspend/resume with
  cursor restoration on every exit path (U-11).
- A product page and manual in `sites/xsync`, generated from the executable’s help,
  the source and captured output.

#### Fixed

- Repeated syncs into a destination inside the source no longer nest without limit (T-01).
- `host:~/path` and remote wildcards expand as with rsync (T-02, T-03).
- Accepted-but-ignored options and silent attribute failures now fail or fall back
  visibly (T-04, T-05).
- Files that change while being read are detected (T-06); `--delete` stops after source
  I/O errors (T-07); interrupted remote transfers clean up (T-08).
- Disk-full handling, `-x` across mount points, case and Unicode name collisions,
  receiver symlink safety, Ctrl-C during remote transfers, and root-only paths are fixed
  and tested (T-09, T-10, T-12 to T-15).

#### Known gaps

- Real-ssh end-to-end checks on every physical target are still partial (R-01). The
  manual terminal pass was skipped at the user’s request (U-01).
- Performance work (P3) and the engineering base (P4) are open; see the backlog’s tier
  tables and `sites/xsync`’s development status page.



## VERSIONS OF THIS MANUAL {#versions}

<p>No release has been tagged yet, so this manual describes the current <code>main</code>. When the first release is tagged, its manual will be kept under its own version, and this page will link to it.</p>


