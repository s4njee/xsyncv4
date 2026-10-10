---
title: "xs-itemize(5)"
description: "Decode every character of an -i change line and every --out-format escape."
manual: "xs-itemize(5)"
manualName: "Itemize & out-format"
sectionNumber: "5"
---

# xs-itemize(5)

<div class="manual-deck"><strong>Itemize &amp; out-format</strong><p>Decode every character of an -i change line and every --out-format escape.</p></div>

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



<div class="example-caption">Itemize a fresh copy</div>

```sh
xs -ai src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ archive/&#10;&gt;f+++++++++ archive/2026-q3.log&#10;cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;cd+++++++++ docs/images/&#10;&gt;f+++++++++ docs/images/diagram.svg&#10;cL+++++++++ latest -&gt; notes.txt&#10;&gt;f+++++++++ notes.txt&#10;cd+++++++++ scripts/&#10;&gt;f+++++++++ scripts/build.sh</code></pre></div>



<p>Directories end with <code>/</code>, and the destination root itself is <code>./</code>. A symlink shows its target after <code> -&gt; </code>.</p>


## CHANGES {#changes}

<p>The following run starts from a synced copy, then changes one attribute of each entry: content and group, time, mode, owner, access time, ACL, an extended attribute and a symlink target. It also adds a page, a device and a FIFO, and leaves a stale file in the destination.</p>



<div class="example-caption">Itemize every kind of change: content, time, mode, owner, group, access time, ACL, xattr, symlink target, new device and FIFO, deletion</div>

```sh
xs -aiXAUD --delete src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>.f....o.u.. archive/2026-q3.log&#10;.d..t...... docs/&#10;&gt;f+++++++++ docs/faq.md&#10;&gt;f..t...u.. docs/guide.md&#10;.d........x docs/images/&#10;.f......ua. docs/images/diagram.svg&#10;cLc........ latest -&gt; docs/guide.md&#10;&gt;f.s...g... notes.txt&#10;cD+++++++++ null&#10;cS+++++++++ queue&#10;.f...p..u.. scripts/build.sh&#10;*deleting   stale.txt</code></pre></div>



<p>Read <code>.f....o.u.. archive/2026-q3.log</code> as: no data sent (<code>.</code>), a regular file (<code>f</code>), owner changed (<code>o</code>), access time changed (<code>u</code>). Only the attributes were updated.</p>



<div class="example-caption">Same size and time, different content: only -c notices</div>

```sh
xs -aci src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>.f..t...... docs/guide.md&#10;&gt;fc........ notes.txt</code></pre></div>



<p>Without <code>-c</code>, a file whose size and time match is skipped, so the content change to <code>notes.txt</code> would go unnoticed.</p>



<div class="example-caption">Without -t, updated files get the transfer time (T)</div>

```sh
xs -rli src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>&gt;f.sT...... notes.txt</code></pre></div>




## HARD LINKS {#hard-links}



<div class="example-caption">Hard-link groups with -H</div>

```sh
xs -aiH src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ archive/&#10;&gt;f+++++++++ archive/2026-q3.log&#10;cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;cd+++++++++ docs/images/&#10;&gt;f+++++++++ docs/images/diagram.svg&#10;&gt;f+++++++++ docs/notes-link.txt&#10;cL+++++++++ docs/readme-link.md -&gt; guide.md&#10;hL+++++++++ docs/readme.md =&gt; docs/readme-link.md&#10;cL+++++++++ latest -&gt; notes.txt&#10;hf+++++++++ notes.txt =&gt; docs/notes-link.txt&#10;cd+++++++++ scripts/&#10;&gt;f+++++++++ scripts/build.sh</code></pre></div>



<p>With <code>-H</code>, the first member of a hard-link group is copied, and later members are reported as <code>h</code> lines that name the copied member after <code> =&gt; </code>. That is distinct from a symlink’s <code> -&gt; </code>: <code>hL</code> is a symlink that is hard-linked to another symlink.</p>


## UNCHANGED ENTRIES {#unchanged}



<div class="example-caption">Repeat -i to list unchanged entries too</div>

```sh
xs -aii src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>.d          ./&#10;.d          archive/&#10;.f          archive/2026-q3.log&#10;.d          docs/&#10;.f          docs/guide.md&#10;.d          docs/images/&#10;.f          docs/images/diagram.svg&#10;.L          latest -&gt; notes.txt&#10;.f          notes.txt&#10;.d          scripts/&#10;.f          scripts/build.sh</code></pre></div>




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



<div class="example-caption">Choose the fields of each file line</div>

```sh
xs -a --out-format='%o %i %-24n %10l %b' src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>send cd+++++++++ ./                             4096 0&#10;send cd+++++++++ archive/                       4096 0&#10;send &gt;f+++++++++ archive/2026-q3.log         1288895 1288895&#10;send cd+++++++++ docs/                          4096 0&#10;send &gt;f+++++++++ docs/guide.md                    33 33&#10;send cd+++++++++ docs/images/                   4096 0&#10;send &gt;f+++++++++ docs/images/diagram.svg          42 42&#10;send cL+++++++++ latest                            9 0&#10;send &gt;f+++++++++ notes.txt                        14 14&#10;send cd+++++++++ scripts/                       4096 0&#10;send &gt;f+++++++++ scripts/build.sh                 21 21</code></pre></div>



<aside class="manual-note"><span>DIFFERS FROM RSYNC</span><p>rsync’s <code>%b</code> counts protocol bytes, so it depends on rsync’s own framing and compression. xs counts file content. An empty <code>--out-format=''</code> suppresses file lines entirely.</p></aside>


## ORDER, LOGS AND ESCAPING {#order}

<ul>
<li><strong>Order.</strong> On a terminal, lines appear as each entry finishes. When stdout is a pipe or file, they are buffered until the end and sorted by path, so the output of a parallel transfer is still stable from run to run.</li>
<li><strong>Logs.</strong> <code>--log-file=FILE</code> appends exactly the stdout stream, with no timestamps or prefixes added. <code>-q</code> suppresses the stream.</li>
<li><strong>Escaping.</strong> Control bytes other than tab are written as <code>\#ooo</code> (octal). Valid UTF-8 is kept. Invalid high bytes are escaped unless <code>-8</code>/<code>--8-bit-output</code> is given.</li>
<li><strong>Remote transfers.</strong> <code>--out-format</code>, <code>--log-file</code> and <code>-ii</code> need a helper that supports structured output; plain <code>-v</code> and <code>-i</code> work with older helpers. See <a href="protocol.html#features">protocol features</a>.</li>
</ul>


