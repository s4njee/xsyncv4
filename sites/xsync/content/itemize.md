---
slug: itemize
title: xs-itemize(5)
name: Itemize & out-format
summary: Decode every character of an -i change line and every --out-format escape.
group: REFERENCE
after: progress
---

## SYNOPSIS {#synopsis}

```sh
xs -ai SRC/ DEST/                 # one line per changed entry
xs -aii SRC/ DEST/                # also unchanged entries
xs -a --out-format='%i %n%L' SRC/ DEST/
```

<p><code>-i</code> prints one line for each entry the transfer changes. The line starts with an eleven-character change code, followed by the name. The code uses rsync’s layout, <code>YXcstpoguax</code>, so scripts written for rsync read it the same way. With <code>--fileflags</code> the code has a twelfth character. Every example below is real output from the current binary.</p>

## THE CHANGE CODE {#code}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Position</th><th scope="col">Values</th><th scope="col">Meaning</th></tr></thead><tbody>
<tr><td>1 · <code>Y</code></td><td><code>&lt;</code> <code>&gt;</code> <code>c</code> <code>h</code> <code>.</code> <code>*</code></td><td>What happened. <code>&lt;</code> file data sent to the remote side (push); <code>&gt;</code> file data received (local copy or pull); <code>c</code> a directory, symlink, device or special file was created or changed; <code>h</code> a hard link to another entry in the transfer (<code>-H</code>); <code>.</code> no data was transferred, so only attributes changed, or nothing did (<code>-ii</code>); <code>*</code> the rest of the line is a message, such as <code>*deleting</code>.</td></tr>
<tr><td>2 · <code>X</code></td><td><code>f</code> <code>d</code> <code>L</code> <code>D</code> <code>S</code></td><td>Entry type: regular file, directory, symlink, device, or special file (FIFO or socket).</td></tr>
<tr><td>3 · <code>c</code></td><td><code>c</code></td><td>A regular file’s checksum differs (only computed with <code>-c</code>), or a symlink’s target changed.</td></tr>
<tr><td>4 · <code>s</code></td><td><code>s</code></td><td>Size differs.</td></tr>
<tr><td>5 · <code>t</code></td><td><code>t</code> <code>T</code></td><td>Modification time differs. <code>T</code> means the time is being set to the transfer time because times are not preserved (no <code>-t</code>).</td></tr>
<tr><td>6 · <code>p</code></td><td><code>p</code></td><td>Permissions differ.</td></tr>
<tr><td>7 · <code>o</code></td><td><code>o</code></td><td>Owner differs.</td></tr>
<tr><td>8 · <code>g</code></td><td><code>g</code></td><td>Group differs.</td></tr>
<tr><td>9 · <code>u</code></td><td><code>u</code> <code>n</code> <code>b</code></td><td>Access time (<code>u</code>, with <code>-U</code>), creation time (<code>n</code>, with <code>-N</code> on macOS), or both (<code>b</code>) differ.</td></tr>
<tr><td>10 · <code>a</code></td><td><code>a</code></td><td>ACL differs (<code>-A</code>).</td></tr>
<tr><td>11 · <code>x</code></td><td><code>x</code></td><td>Extended attributes differ (<code>-X</code>).</td></tr>
<tr><td>12 · <code>f</code></td><td><code>f</code></td><td>BSD file flags differ. Present only with <code>--fileflags</code>, which is macOS only.</td></tr>
</tbody></table></div>

<p>In positions 3 onward, <code>.</code> means “unchanged”. A new entry shows <code>+</code> in every attribute position, and <code>-ii</code> shows unchanged entries with spaces. Positions for attributes the transfer does not compare, such as ACLs without <code>-A</code>, stay <code>.</code>.</p>

## NEW ENTRIES {#new}

<!--example:itemize-new-->

<p>Directories end with <code>/</code>, and the destination root itself is <code>./</code>. A symlink shows its target after <code> -&gt; </code>.</p>

## CHANGES {#changes}

<p>The following run starts from a synced copy, then changes one attribute of each entry: content and group, time, mode, owner, access time, ACL, an extended attribute and a symlink target. It also adds a page, a device and a FIFO, and leaves a stale file in the destination.</p>

<!--example:itemize-changes-->

<p>Read <code>.f....o.u.. archive/2026-q3.log</code> as: no data sent (<code>.</code>), a regular file (<code>f</code>), owner changed (<code>o</code>), access time changed (<code>u</code>). Only the attributes were updated.</p>

<!--example:itemize-checksum-->

<p>Without <code>-c</code>, a file whose size and time match is skipped, so the content change to <code>notes.txt</code> would go unnoticed.</p>

<!--example:itemize-no-times-->

## HARD LINKS {#hard-links}

<!--example:itemize-hardlinks-->

<p>With <code>-H</code>, the first member of a hard-link group is copied, and later members are reported as <code>h</code> lines that name the copied member after <code> =&gt; </code>. That is distinct from a symlink’s <code> -&gt; </code>: <code>hL</code> is a symlink that is hard-linked to another symlink.</p>

## UNCHANGED ENTRIES {#unchanged}

<!--example:itemize-unchanged-->

## --OUT-FORMAT {#out-format}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Escape</th><th scope="col">Expands to</th></tr></thead><tbody>
<tr><td><code>%i</code></td><td>The change code described above.</td></tr>
<tr><td><code>%n</code></td><td>The transfer-relative name, with a trailing <code>/</code> for directories.</td></tr>
<tr><td><code>%L</code></td><td><code> -&gt; TARGET</code> for a symlink, <code> =&gt; NAME</code> for a hard link, otherwise empty.</td></tr>
<tr><td><code>%l</code></td><td>The source length in bytes.</td></tr>
<tr><td><code>%o</code></td><td>The operation: <code>send</code>, <code>recv</code> or <code>del.</code></td></tr>
<tr><td><code>%f</code></td><td>The long source name on a sender, or the short name on a remote pull.</td></tr>
<tr><td><code>%b</code></td><td>File-content bytes transferred before compression, excluding framing. A resumed file counts only the tail that was sent; clones, metadata-only updates and dry runs count zero.</td></tr>
<tr><td><code>%t</code></td><td>The local date and time.</td></tr>
<tr><td><code>%%</code></td><td>A literal <code>%</code>.</td></tr>
</tbody></table></div>

<p>An optional width pads with spaces: <code>%-24n</code> left-aligns the name in 24 columns, and <code>%10l</code> right-aligns the length in 10.</p>

<!--example:out-format-->

<aside class="manual-note"><span>DIFFERS FROM RSYNC</span><p>rsync’s <code>%b</code> counts protocol bytes, so it depends on rsync’s own framing and compression. xs counts file content. An empty <code>--out-format=''</code> suppresses file lines entirely.</p></aside>

## ORDER, LOGS AND ESCAPING {#order}

<ul>
<li><strong>Order.</strong> On a terminal, lines appear as each entry finishes. When stdout is a pipe or file, they are buffered until the end and sorted by path, so the output of a parallel transfer is still stable from run to run.</li>
<li><strong>Logs.</strong> <code>--log-file=FILE</code> appends exactly the stdout stream, with no timestamps or prefixes added. <code>-q</code> suppresses the stream.</li>
<li><strong>Escaping.</strong> Control bytes other than tab are written as <code>\#ooo</code> (octal). Valid UTF-8 is kept. Invalid high bytes are escaped unless <code>-8</code>/<code>--8-bit-output</code> is given.</li>
<li><strong>Remote transfers.</strong> <code>--out-format</code>, <code>--log-file</code> and <code>-ii</code> need a helper that supports structured output; plain <code>-v</code> and <code>-i</code> work with older helpers. See <a href="protocol.html#features">protocol features</a>.</li>
</ul>
