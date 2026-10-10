---
title: "xs-from-rsync(7)"
description: "What stays the same, what changes, and how to switch an existing rsync habit or script to xs."
manual: "xs-from-rsync(7)"
manualName: "Coming from rsync"
sectionNumber: "7"
---

# xs-from-rsync(7)

<div class="manual-deck"><strong>Coming from rsync</strong><p>What stays the same, what changes, and how to switch an existing rsync habit or script to xs.</p></div>

## THE SHORT VERSION {#summary}

<p>xs takes rsync’s command line. Trailing-slash rules, <code>-a</code>, filters, <code>--delete</code>, itemized output and exit codes all mean what they mean in rsync. Options it does not implement are handed to a real rsync automatically, so an existing command keeps working. You need <code>xs</code> on both machines for native remote transfers; without it, those transfers fall back to rsync too.</p>

<div class="example-caption">Try it on one command before changing anything else</div>

```sh
xs -ani --delete src/ dst/      # preview: same itemize codes as rsync
xs -aP src/ dst/                # then run it
```

<aside class="manual-note"><span>ALIAS</span><p><code>alias rsync=xs</code> works for interactive use. In scripts, call <code>xs</code> by name instead, so it is clear which tool ran and fallback stays visible. Fallback runs whichever <code>rsync</code> is first on <code>PATH</code>. An alias does not change that, because aliases do not apply to the executed program.</p></aside>


## YOUR COMMANDS {#shapes}

<p>These are the invocation shapes xs was built around, taken from real shell history and project scripts.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">If you run</th><th scope="col">With xs</th></tr></thead><tbody>
<tr><td><code>rsync -axhP DIR DEST</code></td><td>Works as is. <code>-x</code> stays on one filesystem; <code>-P</code> resumes interrupted files from a verified prefix; progress is xs’s live display. <code>-h</code> uses decimal units, <code>-hh</code> binary.</td></tr>
<tr><td><code>rsync -az[P] SRC DEST</code>, with <code>--exclude</code></td><td>Works as is, locally or over ssh. <code>-z</code> uses zstd; filters keep rsync’s first-match rules.</td></tr>
<tr><td><code>rsync -e "ssh -i KEY" …</code></td><td>Works as is. Quoting in <code>-e</code>, keys and passphrase prompts behave as with rsync.</td></tr>
<tr><td><code>rsync -az --delete --out-format='%i %n'</code> in a script</td><td>Works, with stable output: file lines are sorted when stdout is not a terminal. <code>%b</code> counts file bytes rather than protocol bytes.</td></tr>
<tr><td><code>rsync -rlptz</code>, <code>--info=progress2</code></td><td>Works. <code>--info=progress2</code> prints rsync’s line shape on a pipe; <code>--progress=json</code> is the structured alternative.</td></tr>
</tbody></table></div>


## WHAT IS DIFFERENT {#differences}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Area</th><th scope="col">rsync</th><th scope="col">xs</th></tr></thead><tbody>
<tr><td>Wire protocol</td><td>rsync protocol; works with rsync daemons</td><td>Its own protocol; xs on both ends. Daemon URLs (<code>host::module</code>, <code>rsync://</code>) go to rsync.</td></tr>
<tr><td>New files</td><td>Temporary file, then rename</td><td>The same by default. <code>--no-atomic</code> writes them directly.</td></tr>
<tr><td>Progress</td><td>Off unless <code>-P</code>/<code>--progress</code></td><td>On whenever stderr is a terminal; off in scripts. <code>--no-progress</code> or <code>XSYNC_PROGRESS=0</code> turns it off.</td></tr>
<tr><td>File-line order on a pipe</td><td>As transferred</td><td>Sorted by path at the end of the run.</td></tr>
<tr><td><code>%b</code> in <code>--out-format</code></td><td>Protocol bytes</td><td>File-content bytes before compression.</td></tr>
<tr><td>Local copies on APFS</td><td>Byte copies</td><td>Copy-on-write clones, which can carry xattrs, ACLs and extra times. <code>--no-clone</code> copies bytes.</td></tr>
<tr><td><code>-z</code> on a local copy</td><td>Compresses and decompresses</td><td>Does nothing.</td></tr>
<tr><td>Symlinks inside the destination</td><td>Followed for directories with <code>--keep-dirlinks</code></td><td>Never followed by writes, metadata changes or cleanup; <code>--keep-dirlinks</code> goes to rsync.</td></tr>
<tr><td><code>-E</code></td><td>Executability (Apple’s system rsync: extended attributes)</td><td>Executability. Use <code>-X</code> for attributes.</td></tr>
<tr><td>Unsupported options</td><td>—</td><td>Handed to rsync with a notice; with <code>--no-fallback</code>, exit 1.</td></tr>
</tbody></table></div>

<p>The <a href="compatibility.html">compatibility page</a> lists the details, and <a href="options.html#delegated">delegated options</a> lists exactly which options go to rsync.</p>


## SWITCHING A SCRIPT {#scripts}

<ol>
<li>Replace <code>rsync</code> with <code>xs</code> and run the script once with <code>-n</code> added. Compare the itemized output with rsync’s; it uses the same codes (<a href="itemize.html">itemize reference</a>).</li>
<li>Look for <code>xs: falling back to rsync:</code> on stderr. Each notice names the option or condition that caused it.</li>
<li>Decide whether fallback is acceptable. If the script must be native, add <code>--no-fallback</code> or set <code>XSYNC_FALLBACK=0</code>; it then fails before writing instead of silently running rsync.</li>
<li>Pin personal defaults out of the script’s way with <code>XSYNC_CONFIG='' XSYNC_OPTS=''</code> if your interactive defaults should not apply (<a href="environment.html#deterministic">control defaults explicitly</a>).</li>
<li>Keep checking the exit status. The codes are rsync’s: 23 for a partial transfer, 24 for vanished files, 25 for the deletion limit, and so on (<a href="exit-status.html">exit status</a>).</li>
</ol>


## SPEED EXPECTATIONS {#speed}

<p>xs is built for trees of many small files and for local copies on one APFS volume, where clones and parallel workers help most. Over a 1 Gb/s network, uncompressed transfers are limited by the link, and both tools take about the same time; <code>-z</code> helps xs more. Some cases are slower today. See <a href="performance.html">performance</a> for measured numbers, losses included.</p>


