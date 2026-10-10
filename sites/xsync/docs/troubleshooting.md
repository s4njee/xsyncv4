---
title: "xs-troubleshoot(7)"
description: "What each fallback notice and common failure means, with the exact text xs prints."
manual: "xs-troubleshoot(7)"
manualName: "Troubleshooting"
sectionNumber: "7"
---

# xs-troubleshoot(7)

<div class="manual-deck"><strong>Troubleshooting</strong><p>What each fallback notice and common failure means, with the exact text xs prints.</p></div>

## FALLBACK NOTICES {#fallback}

<p>When xs cannot do something natively, it runs a real <code>rsync</code> from <code>PATH</code> instead. Before anything is written, it prints one line naming the reason: <code>xs: falling back to rsync: REASON</code>. The transfer still happens, with rsync’s speed, output and behavior. There are three causes, and each one fails in its own way with <code>--no-fallback</code> or <code>XSYNC_FALLBACK=0</code>.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Cause</th><th scope="col">Notice names</th><th scope="col">With <code>--no-fallback</code></th></tr></thead><tbody>
<tr><td>An option xs does not implement</td><td><code>--backup is not supported by xs</code></td><td>exit 1</td></tr>
<tr><td>No xs on the remote host</td><td><code>remote xsync is not installed on HOST</code></td><td>exit 127</td></tr>
<tr><td>The remote xs is too old for a requested option</td><td><code>peer does not support …</code></td><td>exit 4</td></tr>
</tbody></table></div>

<p>Transfers never fall back once they have started, and malformed protocol data never triggers fallback. <code>--progress=json</code> never falls back either, because rsync cannot produce its events.</p>

### An option xs does not implement



<div class="example-caption">An option xs does not implement runs rsync instead</div>

```sh
xs -a --backup src/ dst/
ls dst/notes.txt*
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>dst/notes.txt&#10;dst/notes.txt~</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: falling back to rsync: --backup is not supported by xs</code></pre></div>





<div class="example-caption">The same request with fallback disabled</div>

```sh
xs --no-fallback -a --backup src/ dst/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 1</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: --backup is not supported by xs (fallback disabled)</code></pre></div>



<p>The full list is under <a href="options.html#delegated">delegated options</a>. If you need the option and want xs’s speed for everything else, run the two kinds of work as separate commands.</p>

### No xs on the remote host



<div class="example-caption">No xs on the remote host: rsync carries the transfer</div>

```sh
xs -az src/ host:backup/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 0</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: falling back to rsync: remote xsync is not installed on host</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>





<div class="example-caption">No xs on the remote host, fallback disabled</div>

```sh
xs --no-fallback -az src/ host:backup/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 127</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: remote xsync is not installed on host (fallback disabled)</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<p>Install the helper with <code>xs --install user@host</code> (see <a href="install.html#remote">remote install</a>), put <code>xs</code> on the remote <code>PATH</code> or in <code>~/.local/bin</code>, or name it with <code>--rsync-path</code>. The notice still says “xsync”, the project’s old executable name.</p>

### The remote xs is too old



<div class="example-caption">A helper without hard-link support, fallback disabled</div>

```sh
xs --no-fallback -aH src/ host:backup/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 4</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: connection unexpectedly closed&#10;xs error: exiting (code 12)&#10;xs: peer does not support hard-link preservation (fallback disabled)</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>





<div class="example-caption">The same helper with fallback enabled</div>

```sh
xs -aH src/ host:backup/; echo "exit status: $?"
stat -c "%h links  %n" backup/notes.txt
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>exit status: 0&#10;2 links  backup/notes.txt</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: connection unexpectedly closed&#10;xs error: exiting (code 12)&#10;xs: falling back to rsync: peer does not support hard-link preservation</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<p>The helper here lacks hard-link support. The two lines before the reason are the helper’s own messages, forwarded over ssh when the client ends the session. They do not mean the transfer broke; the client’s line and its exit status are what count. Update the helper with <code>xs --install user@host</code>, which replaces an older version (only a newer or unrecognized one needs <code>--force</code>), or drop the option. The <a href="protocol.html#features">feature table</a> shows which option needs which feature.</p>


## REMOTE CONNECTIONS {#remote}

<ul>
<li><strong>Exit 255</strong> is ssh failing to connect or authenticate; xs passes ssh’s status through. Try the same <code>ssh</code> command by hand. Options for ssh itself go in <code>-e</code>, for example <code>-e "ssh -p 2222 -i ~/.ssh/backup_key"</code>.</li>
<li><strong>Exit 12</strong> with <code>connection unexpectedly closed (remote shell exited with code N)</code> means the remote shell ended with some other status, for example a login script that exits or prints errors.</li>
<li><strong>Exit 30</strong> is the <code>--timeout</code> deadline. It counts idle time only, so a slow but moving transfer does not trip it.</li>
<li><strong>Exit 2</strong> means the two versions are too far apart to talk. Each release speaks its own protocol and the previous one.</li>
<li>Password and passphrase prompts come from ssh and work as they do with rsync. For unattended runs, use keys or an agent.</li>
</ul>


## TRANSFER RESULTS {#results}

### Exit 23: some files were not transferred



<div class="example-caption">A source that does not exist</div>

```sh
xs -a missing/ dst/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 23</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: link_stat &quot;missing/&quot; failed: No such file or directory (2)&#10;xs: error summary: 1 error (showing first 1)&#10;  partial transfer (code 23): 1 error&#10;    link_stat &quot;missing/&quot; failed: No such file or directory (2)&#10;xs error: some files/attrs were not transferred (see previous errors) (code 23)</code></pre></div>



<p>Exit 23 means the run finished but some entries failed, and the error summary lists the first ten. Files that succeeded are in place; nothing is rolled back. Fix the cause and run the same command again, since unchanged files are skipped.</p>

### Exit 25: the deletion limit



<div class="example-caption">Stop when a mirror would delete too much</div>

```sh
xs -a --delete --max-delete=1 src/ dst/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 25</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: Deletions stopped due to --max-delete limit (1)&#10;xs: error summary: 1 error (showing first 1)&#10;  deletion limit (code 25): 1 error&#10;    Deletions stopped due to --max-delete limit (1)&#10;xs error: the --max-delete limit stopped deletions (code 25)</code></pre></div>



<p><code>--max-delete</code> stopped deletions after the limit; the transfer itself completed. Check with <code>-n</code> first (see <a href="filters.html#mirror">preview a mirror</a>), then raise the limit if the deletions are expected.</p>

### Exit 1: a malformed value



<div class="example-caption">A malformed value</div>

```sh
xs --no-fallback -a --bwlimit=fast src/ dst/; echo "exit status: $?"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT</span><pre><code>exit status: 1</code></pre><span class="micro stream-label">STDERR</span><pre><code>xs: --bwlimit requires a nonnegative rate: fast&#10;xs error: syntax or usage error (code 1)</code></pre></div>




## PROGRESS AND OUTPUT {#progress}

<ul>
<li><strong>No progress bar in a script.</strong> Progress is on by default only when stderr is a terminal. Use <code>--progress</code>, <code>--info=progress2</code> or <code>--progress=json</code> to get it on a pipe. If a bar appears where it shouldn’t, check <code>XSYNC_OPTS</code>, <code>XSYNC_PROGRESS</code> and the config file (<a href="environment.html#precedence">precedence</a>).</li>
<li><strong>A push bar that stops below 100%.</strong> On a push, the bar follows what the receiver reports as written, so it waits for the last writes. <code>waiting for receiver</code> means exactly that. Older helpers cannot report writes, so the bar stays at zero until they finish.</li>
<li><strong>File lines appear all at once.</strong> When stdout is a pipe or file, file lines are sorted and printed at the end, so the output is stable. On a terminal they appear as files finish.</li>
<li><strong><code>-z</code> on a local copy</strong> is accepted and does nothing: there is no connection to compress.</li>
</ul>


## SURPRISES ON MACOS {#macos}

<ul>
<li><strong>Extra metadata on copies.</strong> On one APFS volume, <code>-a</code> clones files. Clones carry extended attributes, ACLs and access and creation times even without <code>-X</code>, <code>-A</code>, <code>-U</code> or <code>-N</code>, and they share storage with the source until either is modified. Use <code>--no-clone</code> to copy bytes instead.</li>
<li><strong><code>-E</code> means something else in Apple’s rsync.</strong> Apple’s system rsync uses <code>-E</code> for extended attributes. xs uses <code>-E</code> for executability, as modern rsync does, and <code>-X</code> for attributes. Write <code>--executability</code> when a command may fall back.</li>
<li><strong>Cloud files.</strong> Files that exist only in iCloud (dataless files) are read normally, which can make the file provider download them.</li>
</ul>

<p>Every example on this page is real output, captured from the current binary on Linux. Remote examples ran through an ssh stand-in on one machine. See <a href="exit-status.html">exit status</a> for every code.</p>


