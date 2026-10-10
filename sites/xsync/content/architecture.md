---
slug: architecture
title: xs-internals(7)
name: How it works
summary: The local engine, the remote exchange and the life of one file, with the source files behind each.
group: PROJECT
after: performance
---

## OVERVIEW {#overview}

<p>xs is one executable with three roles. As a <strong>local engine</strong> it copies between two paths on one machine. As a <strong>client</strong> it starts <code>xs --server</code> on another machine over ssh and plays the sender (push) or the receiver (pull). As that <strong>helper</strong> it plays the other role. All three share the same scanner, the same receiver-side generator and the same file writer. Parallelism comes from a worker pool with two queues: one for scanning and comparing directories, one for moving file data (<code>src/pool.h</code>).</p>

## LOCAL ENGINE {#local}

<figure class="diagram">
<svg viewBox="0 0 760 250" role="img" aria-labelledby="local-title local-desc">
<title id="local-title">Local engine</title>
<desc id="local-desc">Scan workers list source and destination directories; the generator merge-joins them and queues clone, copy, delta or delete tasks; transfer workers write files atomically and set attributes.</desc>
<defs><marker id="arrow-local" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="diagram-arrowhead"/></marker></defs>
<rect x="10" y="30" width="150" height="70" rx="3"/><text x="85" y="58" text-anchor="middle" class="diagram-title">Source tree</text><text x="85" y="78" text-anchor="middle">one listing per directory</text>
<rect x="10" y="150" width="150" height="70" rx="3"/><text x="85" y="178" text-anchor="middle" class="diagram-title">Destination tree</text><text x="85" y="198" text-anchor="middle">anchored, no symlinks followed</text>
<rect x="215" y="85" width="160" height="80" rx="3" class="diagram-strong"/><text x="295" y="113" text-anchor="middle" class="diagram-title">Scan + generator</text><text x="295" y="133" text-anchor="middle">queue 0 · merge-join</text><text x="295" y="151" text-anchor="middle">decide per entry</text>
<rect x="430" y="20" width="150" height="46" rx="3"/><text x="505" y="48" text-anchor="middle">APFS clone (whole dir)</text>
<rect x="430" y="78" width="150" height="46" rx="3"/><text x="505" y="106" text-anchor="middle">byte copy / delta</text>
<rect x="430" y="136" width="150" height="46" rx="3"/><text x="505" y="164" text-anchor="middle">attributes only</text>
<rect x="430" y="194" width="150" height="46" rx="3"/><text x="505" y="222" text-anchor="middle">delete extraneous</text>
<rect x="630" y="78" width="120" height="104" rx="3" class="diagram-strong"/><text x="690" y="112" text-anchor="middle" class="diagram-title">Transfer</text><text x="690" y="132" text-anchor="middle">queue 1 · -j N</text><text x="690" y="150" text-anchor="middle">temp + rename</text><text x="690" y="168" text-anchor="middle">then attributes</text>
<path d="M160 65 C190 65 190 110 213 115" marker-end="url(#arrow-local)"/>
<path d="M160 185 C190 185 190 140 213 135" marker-end="url(#arrow-local)"/>
<path d="M375 110 L428 43" marker-end="url(#arrow-local)"/><path d="M375 120 L428 101" marker-end="url(#arrow-local)"/>
<path d="M375 135 L428 159" marker-end="url(#arrow-local)"/><path d="M375 150 L428 217" marker-end="url(#arrow-local)"/>
<path d="M580 101 L628 115" marker-end="url(#arrow-local)"/><path d="M580 159 L628 145" marker-end="url(#arrow-local)"/>
</svg>
<figcaption>Scanning runs ahead of copying, so totals are known almost at once and new directories keep the transfer queue full.</figcaption>
</figure>

<ul>
<li><strong>Scan.</strong> Directories are listed by a pool of threads. On macOS, <code>getattrlistbulk</code> returns names and attributes in one call per directory. On Linux, each entry is a <code>readdir</code> plus an <code>fstatat</code>, and backlog F-06 tracks a faster path (<code>src/fs.cpp</code>, <code>src/local.cpp</code>).</li>
<li><strong>Generator.</strong> Source and destination listings are merge-joined per directory, and each entry is checked against the filters, case and Unicode name collisions (<code>src/names.cpp</code>), and the requested metadata. Every write goes through a directory file descriptor and never follows a symlink inside the destination (<code>src/destination.cpp</code>).</li>
<li><strong>Clones.</strong> On one APFS volume with at least <code>-pt</code>, a new directory that holds only files and symlinks is cloned in a single call, and other files are cloned one by one. <code>-X</code>, <code>-U</code>, <code>-N</code>, <code>--chmod</code>, <code>--chown</code>, <code>--fileflags</code>, <code>-S</code> and <code>--bwlimit</code> turn whole-directory clones off, because they need per-entry handling.</li>
<li><strong>Deletion</strong> runs before, during, or after transfer, depending on <code>--delete-WHEN</code>. It is skipped entirely when the source had I/O errors, unless <code>--ignore-errors</code> is given.</li>
</ul>

## REMOTE EXCHANGE {#remote}

<figure class="diagram">
<svg viewBox="0 0 760 290" role="img" aria-labelledby="remote-title remote-desc">
<title id="remote-title">Remote push</title>
<desc id="remote-desc">The client sender streams directory listings to the helper receiver, which answers with the files it needs; data blocks flow back the other way of the request, and the receiver acknowledges progress.</desc>
<defs><marker id="arrow-remote" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="diagram-arrowhead"/></marker></defs>
<rect x="10" y="20" width="250" height="250" rx="3" class="diagram-strong"/><text x="135" y="46" text-anchor="middle" class="diagram-title">Client · sender (push)</text>
<rect x="30" y="66" width="210" height="40" rx="3"/><text x="135" y="91" text-anchor="middle">scan workers → F_DIR</text>
<rect x="30" y="140" width="210" height="40" rx="3"/><text x="135" y="165" text-anchor="middle">readers → zstd → F_DATA</text>
<rect x="30" y="214" width="210" height="40" rx="3"/><text x="135" y="239" text-anchor="middle">progress bar ← F_PROGRESS</text>
<rect x="500" y="20" width="250" height="250" rx="3" class="diagram-strong"/><text x="625" y="46" text-anchor="middle" class="diagram-title">Helper · receiver (xs --server)</text>
<rect x="520" y="66" width="210" height="40" rx="3"/><text x="625" y="91" text-anchor="middle">generator → F_NEED</text>
<rect x="520" y="140" width="210" height="40" rx="3"/><text x="625" y="165" text-anchor="middle">decompress → write pool</text>
<rect x="520" y="214" width="210" height="40" rx="3"/><text x="625" y="239" text-anchor="middle">acknowledge written bytes</text>
<text x="380" y="34" text-anchor="middle" class="diagram-note">one ssh stream</text>
<path d="M242 86 L518 86" marker-end="url(#arrow-remote)"/><text x="380" y="78" text-anchor="middle">F_DIR per directory</text>
<path d="M518 118 L242 118" marker-end="url(#arrow-remote)"/><text x="380" y="110" text-anchor="middle">F_NEED: wanted files, prefixes</text>
<path d="M242 160 L518 160" marker-end="url(#arrow-remote)"/><text x="380" y="152" text-anchor="middle">F_DATA ≈1 MiB blocks, XXH3</text>
<path d="M518 234 L242 234" marker-end="url(#arrow-remote)"/><text x="380" y="226" text-anchor="middle">F_PROGRESS, F_OUTPUT, F_PHASE</text>
</svg>
<figcaption>Listing, reading, compressing, sending and writing all overlap. A pull swaps the roles: the helper sends and the client receives.</figcaption>
</figure>

<ul>
<li><strong>Pipelining.</strong> The sender does not wait for the full file list. Each directory’s listing goes out as soon as it is scanned, and the receiver answers per directory, so data starts flowing while most of the tree is still being walked.</li>
<li><strong>Blocks.</strong> Files up to 512 KiB are packed together into blocks of about 1 MiB, so thousands of small files cost a few large writes on the wire. With <code>-z</code>, each block is compressed with zstd and decompressed on several threads. Every block carries an XXH3 checksum (<code>src/remote.cpp</code>).</li>
<li><strong>Acknowledged progress.</strong> On a push, the progress bar follows what the receiver reports as written, not what was sent, so it cannot reach 100% before the data has landed.</li>
<li><strong>One stream.</strong> Everything shares one ssh connection, so on a fast LAN the ssh cipher can become the limit before the disks do (backlog F-03).</li>
</ul>

<p>The frames are listed in the <a href="protocol.html#frames">protocol reference</a>.</p>

## THE LIFE OF ONE FILE {#file}

<figure class="diagram">
<svg viewBox="0 0 760 210" role="img" aria-labelledby="file-title file-desc">
<title id="file-title">Writing one file</title>
<desc id="file-desc">A needed file is sent whole, resumed from a verified prefix, or rebuilt from verified blocks; it is written under a temporary name, checked, renamed into place, and then given its attributes.</desc>
<defs><marker id="arrow-file" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" class="diagram-arrowhead"/></marker></defs>
<rect x="10" y="80" width="110" height="50" rx="3" class="diagram-strong"/><text x="65" y="110" text-anchor="middle" class="diagram-title">Needed file</text>
<rect x="170" y="10" width="170" height="50" rx="3"/><text x="255" y="32" text-anchor="middle">whole file</text><text x="255" y="49" text-anchor="middle" class="diagram-note">new, small, or -W</text>
<rect x="170" y="80" width="170" height="50" rx="3"/><text x="255" y="102" text-anchor="middle">verified-prefix resume</text><text x="255" y="119" text-anchor="middle" class="diagram-note">--partial, XXH3-128 match</text>
<rect x="170" y="150" width="170" height="50" rx="3"/><text x="255" y="172" text-anchor="middle">delta from basis</text><text x="255" y="189" text-anchor="middle" class="diagram-note">over 1 MiB, existing file</text>
<rect x="390" y="80" width="120" height="50" rx="3"/><text x="450" y="102" text-anchor="middle">temporary name</text><text x="450" y="119" text-anchor="middle" class="diagram-note">in the same directory</text>
<rect x="545" y="80" width="90" height="50" rx="3"/><text x="590" y="102" text-anchor="middle">verify</text><text x="590" y="119" text-anchor="middle" class="diagram-note">checksum</text>
<rect x="670" y="80" width="80" height="50" rx="3" class="diagram-strong"/><text x="710" y="102" text-anchor="middle">rename</text><text x="710" y="119" text-anchor="middle" class="diagram-note">+ attributes</text>
<path d="M120 100 L168 38" marker-end="url(#arrow-file)"/><path d="M120 105 L168 105" marker-end="url(#arrow-file)"/><path d="M120 110 L168 172" marker-end="url(#arrow-file)"/>
<path d="M340 38 L388 98" marker-end="url(#arrow-file)"/><path d="M340 105 L388 105" marker-end="url(#arrow-file)"/><path d="M340 172 L388 112" marker-end="url(#arrow-file)"/>
<path d="M510 105 L543 105" marker-end="url(#arrow-file)"/><path d="M635 105 L668 105" marker-end="url(#arrow-file)"/>
</svg>
<figcaption>A reader never sees a half-written file under its final name. <code>--no-atomic</code> and <code>--inplace</code> trade that guarantee for fewer renames.</figcaption>
</figure>

<ul>
<li><strong>Resume.</strong> With <code>--partial</code>, both sides hash an existing destination prefix with XXH3-128. If the hashes match, only the remaining bytes are sent. The receiver re-checks the prefix while copying it, so a prefix that changes meanwhile fails rather than producing mixed data (<code>src/remote.cpp</code>, <code>src/local.cpp</code>).</li>
<li><strong>Delta.</strong> For changed files over 1 MiB, a rolling weak checksum finds candidate blocks in the existing file, and XXH3 confirms them. The sender then sends block references and literal data. The matcher keeps one block plus 1 MiB of source data in memory, and the rebuilt file is checked as a whole before it is published (<code>src/delta.cpp</code>).</li>
<li><strong>Source changes.</strong> A source file that changes while it is being read is detected, and a delta transfer retries once. A file that still cannot be read consistently is reported as an error (exit 23) and not published.</li>
<li><strong>Interruption.</strong> On Ctrl-C, a timeout or a closed output pipe, temporary files are removed. With <code>--partial</code>, the completed contiguous prefix is kept for the next run.</li>
</ul>

## SOURCE MAP {#source-map}

<p>Where each part lives. The full list of source files and tests is on the <a href="contributing.html#layout">contributing page</a>.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Concern</th><th scope="col">Files</th></tr></thead><tbody>
<tr><td>Command line, defaults, fallback</td><td><code>main.cpp</code>, <code>arguments.cpp</code>, <code>fallback.cpp</code>, <code>transport.cpp</code></td></tr>
<tr><td>Local engine and shared setup</td><td><code>local.cpp</code>, <code>engine.h</code>, <code>pool.h</code></td></tr>
<tr><td>Scanning, generator, file writing</td><td><code>fs.cpp</code>, <code>destination.cpp</code>, <code>names.cpp</code></td></tr>
<tr><td>Remote protocol, sender and receiver</td><td><code>remote.cpp</code></td></tr>
<tr><td>Data reuse</td><td><code>delta.cpp</code>, <code>sparse.cpp</code>, <code>link_dest.cpp</code>, <code>hardlink.cpp</code></td></tr>
<tr><td>Metadata</td><td><code>acls.cpp</code>, <code>xattrs.cpp</code>, <code>xattr_value.cpp</code>, <code>permissions.cpp</code>, <code>ownership.cpp</code></td></tr>
<tr><td>Selection and filters</td><td><code>filter.cpp</code>, <code>selection.cpp</code>, <code>listing.cpp</code></td></tr>
<tr><td>Output and progress</td><td><code>output.cpp</code>, <code>progress.cpp</code>, <code>rate_limit.cpp</code>, <code>util.cpp</code></td></tr>
</tbody></table></div>
