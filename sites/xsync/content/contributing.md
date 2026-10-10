---
slug: contributing
title: xs-hacking(7)
name: Contributing
summary: Build and test xs, find your way around the source, and keep this manual in step with the code.
group: PROJECT
after: changelog
---

## BUILD AND TEST {#build}

```sh
cmake -S . -B build -G Ninja && cmake --build build
XSYNC_FALLBACK=0 python3 tests/difftest.py                         # differential corpus vs rsync
XSYNC_FALLBACK=0 python3 tests/difftest.py --xsync tests/xs-noclone.sh  # forced byte copies
cmake --build build --target filter_test xattr_value_test sparse_test
build/filter_test && build/xattr_value_test && build/sparse_test
```

<p>Most Python tests take the binary from <code>XSYNC_TEST_BINARY</code> (default <code>build/xs</code>), clear personal defaults with <code>XSYNC_CONFIG='' XSYNC_OPTS=''</code>, and compare against the rsync named by <code>XSYNC_TEST_RSYNC</code> or the first one on <code>PATH</code>. Remote cases run through <code>tests/fakessh.sh</code> unless <code>tests/ssh-rig.sh</code> provides a real sshd. Run any test file directly, for example <code>python3 tests/output_test.py -v</code>.</p>

## TEST MATRIX {#tests}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Area</th><th scope="col">Tests</th><th scope="col">Needs</th></tr></thead><tbody>
<tr><td>Differential corpus</td><td><code>difftest.py</code>: one fixture through rsync and xs, comparing trees and exit codes, local and remote</td><td>a reference rsync (<code>--rsync PATH</code>)</td></tr>
<tr><td>Trust regressions</td><td><code>p0_test.py</code>, <code>mount_test.py</code> (APFS image: disk full, <code>-x</code>)</td><td>fault injector; macOS for the image</td></tr>
<tr><td>Selection</td><td><code>relative_test.py</code>, <code>files_from_test.py</code>, <code>list_test.py</code>, <code>hardlink_test.py</code></td><td>reference rsync</td></tr>
<tr><td>Filters</td><td><code>filter_test.cpp</code> (table from rsync 3.4.4), <code>filter_diff_test.py</code> (seeded fuzzer), <code>filter_merge_test.py</code>, <code>filter_cvs_test.py</code>, <code>filter_after_test.py</code>, <code>filter_prune_test.py</code>, <code>filter_from0_test.py</code>, <code>filter_cvs_listing_test.py</code></td><td>reference rsync; seeds via <code>XSYNC_FILTER_SEED</code> and similar</td></tr>
<tr><td>Metadata</td><td><code>acls_test.py</code>, <code>xattrs_test.py</code>, <code>chmod_test.py</code>, <code>chown_test.py</code>, <code>executability_test.py</code>, <code>times_test.py</code>, <code>metadata_composition_test.py</code>, <code>xattrs_memory_test.py</code></td><td>reference rsync</td></tr>
<tr><td>macOS only</td><td><code>acls_darwin_test.py</code>, <code>fileflags_test.py</code>, <code>mac_specific_test.py</code>, the <code>*_cross_test.py</code> Darwin ↔ Linux tests</td><td>macOS; flags need <code>XSYNC_FILEFLAGS_RSYNC</code>; cross tests need Docker</td></tr>
<tr><td>Privileged</td><td><code>xattrs_privileged_test.py</code>, <code>chown_race_test.py</code>, <code>root_test.py</code></td><td>root on Linux (the rig for <code>root_test.py</code>)</td></tr>
<tr><td>Hostile and frozen peers</td><td><code>wire_test.py</code>, <code>protocol_test.py</code> (frozen protocol 3 and feature subsets), <code>*_wire_test.py</code></td><td>a C++ compiler for the peers</td></tr>
<tr><td>Delta, resume, limits</td><td><code>delta_test.py</code>, <code>delta_remote_test.py</code> (wire cost vs rsync), <code>resume_test.py</code>, <code>sparse_test.py</code>, <code>link_dest_test.py</code>, <code>io_limit_test.py</code></td><td><code>XSYNC_DELTA_LARGE=1</code> for the 2 GiB case</td></tr>
<tr><td>Output and progress</td><td><code>output_test.py</code>, <code>error_test.py</code>, <code>broken_stdout_test.py</code>, <code>dry_summary_test.py</code>, <code>progress_test.py</code> and the other <code>progress_*_test.py</code></td><td>tmux for some PTY tests</td></tr>
<tr><td>Real SSH</td><td><code>ssh-rig.sh</code> runs any module in a two-container rig, for example <code>ssh_test.py</code>, <code>ssh_reach_test.py</code>, <code>lookup_test.py</code>, <code>install_ssh_test.py</code>; <code>lan_test.py</code> targets a real host</td><td>Docker; <code>XSYNC_LAN_HOST</code> for the LAN check</td></tr>
<tr><td>Fallback, defaults, packaging</td><td><code>fallback_test.py</code>, <code>defaults_test.py</code>, <code>host_spec_test.py</code>, <code>packaging_test.py</code>, <code>install_test.py</code></td><td>none beyond a build</td></tr>
<tr><td>Races</td><td><code>xattrs_race_test.py</code>, <code>chmod_race_test.py</code>, <code>executability_race_test.py</code>, <code>fileflags_race_test.py</code></td><td>the <code>fault_io.cpp</code> interposer, built by the tests</td></tr>
</tbody></table></div>

<p><code>tests/fixtures/protocol3.tar.gz</code> is the frozen protocol-3 source used by <code>protocol_test.py</code>. Never regenerate it; add a new fixture when the supported version window moves (<a href="protocol.html#adding">adding a feature</a>).</p>

## SOURCE LAYOUT {#layout}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">File</th><th scope="col">Responsibility</th></tr></thead><tbody>
<tr><td><code>common.h</code></td><td>Shared types, version and protocol constants, feature bits, options and global state.</td></tr>
<tr><td><code>engine.h</code>, <code>pool.h</code></td><td>Entry points of the local, client and server engines and what they share; the two-queue worker pool.</td></tr>
<tr><td><code>main.cpp</code></td><td>Help and version text, option parsing, signals, the final summary, and dispatch to an engine.</td></tr>
<tr><td><code>arguments.cpp</code></td><td>Merges personal defaults into the effective argument list.</td></tr>
<tr><td><code>fallback.cpp</code></td><td>Keeps the original arguments, stdin and umask so a real rsync can be run instead.</td></tr>
<tr><td><code>transport.cpp</code></td><td>Parses <code>[user@]host:path</code> and <code>rsync://</code>, splits shell words, picks the remote shell.</td></tr>
<tr><td><code>install.cpp</code></td><td><code>--install HOST</code>: detects the platform, chooses the release, installs atomically.</td></tr>
<tr><td><code>local.cpp</code></td><td>The same-machine engine: parallel scan and copy, plus shared setup.</td></tr>
<tr><td><code>remote.cpp</code></td><td>The wire protocol: framing, negotiation, sender, receiver and the client/server glue.</td></tr>
<tr><td><code>fs.cpp</code></td><td>Filesystem primitives, directory listing and the receiver-side generator and writer.</td></tr>
<tr><td><code>destination.cpp</code></td><td>Every receiver-side operation, relative to an anchored directory, without following symlinks.</td></tr>
<tr><td><code>names.cpp</code></td><td>Case-folding and Unicode name equivalence on the destination, via ICU.</td></tr>
<tr><td><code>listing.cpp</code>, <code>selection.cpp</code></td><td>Source listings; <code>--files-from</code> parsing and selected directories.</td></tr>
<tr><td><code>filter.cpp</code></td><td>rsync filter rules, merge files and CVS rules, with separate sender and receiver decisions.</td></tr>
<tr><td><code>delta.cpp</code></td><td>Streaming block matching for local copies and negotiated remote deltas.</td></tr>
<tr><td><code>hardlink.cpp</code>, <code>link_dest.cpp</code>, <code>sparse.cpp</code></td><td><code>-H</code> link groups; <code>--link-dest</code> snapshot reuse; sparse writes.</td></tr>
<tr><td><code>permissions.cpp</code>, <code>ownership.cpp</code></td><td><code>--chmod</code> rules; <code>--chown</code> mapping.</td></tr>
<tr><td><code>acls.cpp</code>, <code>xattrs.cpp</code>, <code>xattr_value.cpp</code></td><td>Native ACLs on Linux and macOS; extended attributes; bounded attribute storage that spills to a temporary file.</td></tr>
<tr><td><code>output.cpp</code>, <code>progress.cpp</code></td><td>Itemize and <code>--out-format</code> output and logs; the live display and JSON events.</td></tr>
<tr><td><code>rate_limit.cpp</code>, <code>util.cpp</code></td><td>The <code>--bwlimit</code> token bucket; global state, error reporting and number formatting.</td></tr>
</tbody></table></div>

## THIS MANUAL {#site}

<p>The manual lives in <code>sites/xsync</code> and builds with VitePress. Facts that the code defines are generated rather than written by hand, and <code>npm run check</code> fails when any of them drift:</p>

<ul>
<li><strong>From the binary:</strong> the option tables (<code>xs --help</code>), the manpage, the terminal recordings and every captured example.</li>
<li><strong>From the source:</strong> exit codes, protocol constants, feature bits, frames, and the lists of accepted and delegated options.</li>
<li><strong>From the repository:</strong> development status (the <code>backlog.md</code> tier tables), benchmark results (<code>benchmarks/results/</code>) and the changelog.</li>
<li><strong>Curated:</strong> workflow pages and notes in <code>content/*.md</code> and <code>scripts/*_notes.py</code>. These are fingerprinted against the README and benchmark README, so a changed source flags the pages to re-read.</li>
</ul>

```sh
cd sites/xsync
npm ci
npm run docs:refresh                 # help, manpage and derived inputs from ../../build/xs
python3 scripts/capture-examples.py  # rerun every documented example
python3 scripts/capture-output.py    # terminal recordings for the product page
npm run build && npm run check       # commit, then run check again to prove the build reproduces
```

<p>Two examples need an older helper, built with <code>cmake -S ../.. -B /tmp/xs-old -DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=127</code>. Pass it as <code>--old-helper /tmp/xs-old/xs</code>; without it, those two keep their previous capture. Captures need <code>setfacl</code>, <code>jq</code> and <code>rsync</code>. After re-reading pages whose sources changed, <code>npm run docs:review</code> records new fingerprints.</p>
