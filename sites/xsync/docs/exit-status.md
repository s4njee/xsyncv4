---
title: "xs-exit(7)"
description: "Inspect final status, retained partials, and original diagnostics."
manual: "xs-exit(7)"
manualName: "Exit status & errors"
sectionNumber: "7"
---

# xs-exit(7)

<div class="manual-deck"><strong>Exit status &amp; errors</strong><p>Inspect final status, retained partials, and original diagnostics.</p></div>

## DESCRIPTION {#description}

<p>A final exit status describes the process outcome. Transfer errors include a bounded summary of the first ten diagnostics, grouped by kind, on stderr. Quiet mode keeps errors visible.</p>



## EXIT STATUS {#exit-status}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Code</th><th scope="col">Meaning</th><th scope="col">Error-summary kind</th></tr></thead><tbody><tr><td><code class="nowrap">0</code></td><td>Successful operation</td><td>—</td></tr><tr><td><code class="nowrap">1</code></td><td>Syntax or usage error</td><td>syntax or usage</td></tr><tr><td><code class="nowrap">2</code></td><td>Protocol incompatibility</td><td>protocol incompatibility</td></tr><tr><td><code class="nowrap">3</code></td><td>Input/output selection error</td><td>file selection</td></tr><tr><td><code class="nowrap">4</code></td><td>Requested action unsupported, including a peer that lacks a requested feature under <code>--no-fallback</code></td><td>unsupported action</td></tr><tr><td><code class="nowrap">5</code></td><td>Failure starting the client/server protocol</td><td>protocol startup</td></tr><tr><td><code class="nowrap">11</code></td><td>File I/O error, including fatal disk-full errors</td><td>file IO</td></tr><tr><td><code class="nowrap">12</code></td><td>Protocol data-stream error, including a remote shell that exits unexpectedly</td><td>stream IO</td></tr><tr><td><code class="nowrap">13</code></td><td>Diagnostic/stdout write failure, including a closed output pipe</td><td>diagnostic IO</td></tr><tr><td><code class="nowrap">14</code></td><td>Interprocess communication error</td><td>IPC</td></tr><tr><td><code class="nowrap">20</code></td><td>SIGINT, SIGTERM, or SIGHUP</td><td>interruption</td></tr><tr><td><code class="nowrap">23</code></td><td>Some files or attributes were not transferred</td><td>partial transfer</td></tr><tr><td><code class="nowrap">24</code></td><td>Source files vanished before transfer</td><td>vanished source files</td></tr><tr><td><code class="nowrap">25</code></td><td>Deletion limit exceeded</td><td>deletion limit</td></tr><tr><td><code class="nowrap">30</code></td><td>Remote idle I/O timeout</td><td>idle timeout</td></tr><tr><td><code class="nowrap">127</code></td><td>Remote helper not found, with fallback disabled, or the remote shell command could not be run</td><td>remote command not found</td></tr><tr><td><code class="nowrap">255</code></td><td>The remote shell itself failed (for example, ssh could not connect); its status is passed through</td><td>remote shell failure</td></tr></tbody></table></div><p>Code <code>124</code> is defined for rsync compatibility but xs does not currently return it.</p>



## MISSING SOURCE {#missing-source}



<div class="example-caption">Command from the actual error recording</div>

```sh
xs -aP ./missing-source/ ./unused-backup/
```

<div class="captured-doc-output"><span class="micro">ACTUAL XSYNC DIAGNOSTIC / EXIT 23</span><pre><code id="actual-error-output">xs: link_stat &quot;./missing-source/&quot; failed: No such file or directory (2)
xs: error summary: 1 error (showing first 1)
  partial transfer (code 23): 1 error
    link_stat &quot;./missing-source/&quot; failed: No such file or directory (2)
xs error: some files/attrs were not transferred (see previous errors) (code 23)</code></pre></div>

## INTERRUPTION AND RETRY {#interruption}

<p>Ctrl-C interrupts a run with exit code 20. With <code>-P</code>, completed contiguous partial data can be retained. Rerun the same transfer to verify and reuse matching prefixes.</p>



<div class="example-caption">Retry a partial transfer</div>

```sh
xs -aP src/ dst/
```

<p>A completed-byte prefix can be reused only when it matches the source. Transfers do not invoke fallback after an active copy has failed.</p>



## SCRIPT EXAMPLE {#scripts}



<div class="example-caption">Preserve the command’s original exit status</div>

```sh
if xs -a --no-progress src/ dst/; then
  echo "transfer completed"
else
  status=$?
  echo "xs failed with code $status" >&2
  exit "$status"
fi
```

<p>An exit-23 result may include successful files and failed files in the same run. Inspect the diagnostics rather than assuming the entire destination was rolled back.</p>



