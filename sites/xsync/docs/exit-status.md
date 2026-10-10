---
title: "xsync-exit(7)"
description: "Inspect final status, retained partials, and original diagnostics."
manual: "xsync-exit(7)"
manualName: "Exit status & errors"
sectionNumber: "7"
---

# xsync-exit(7)

<div class="manual-deck"><strong>Exit status &amp; errors</strong><p>Inspect final status, retained partials, and original diagnostics.</p></div>

## DESCRIPTION {#description}

<p>A final exit status describes the process outcome. Transfer errors include a bounded summary of the first ten diagnostics, grouped by kind, on stderr. Quiet mode keeps errors visible.</p>



## EXIT STATUS {#exit-status}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Code</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td>0</td><td>Successful operation</td></tr><tr><td>1</td><td>Syntax or usage error</td></tr><tr><td>2</td><td>Protocol incompatibility</td></tr><tr><td>3</td><td>Input/output selection error</td></tr><tr><td>4</td><td>Requested action unsupported</td></tr><tr><td>5</td><td>Failure starting the client/server protocol</td></tr><tr><td>11</td><td>File I/O error, including fatal disk-full errors</td></tr><tr><td>12</td><td>Protocol data-stream error</td></tr><tr><td>13</td><td>Diagnostic/stdout write failure, including a closed output pipe</td></tr><tr><td>14</td><td>Interprocess communication error</td></tr><tr><td>20</td><td>SIGINT, SIGTERM, or SIGHUP</td></tr><tr><td>23</td><td>Some files or attributes were not transferred</td></tr><tr><td>24</td><td>Source files vanished before transfer</td></tr><tr><td>25</td><td>Deletion limit exceeded</td></tr><tr><td>30</td><td>Remote idle I/O timeout</td></tr></tbody></table></div>

## MISSING SOURCE {#missing-source}



<div class="example-caption">Command from the actual error recording</div>

```sh
xsync -aP ./missing-source/ ./unused-backup/
```

<div class="captured-doc-output"><span class="micro">ACTUAL XSYNC DIAGNOSTIC / EXIT 23</span><pre><code id="actual-error-output">xsync: link_stat &quot;./missing-source/&quot; failed: No such file or directory (2)
xsync: error summary: 1 error (showing first 1)
  partial transfer (code 23): 1 error
    link_stat &quot;./missing-source/&quot; failed: No such file or directory (2)
xsync error: some files/attrs were not transferred (see previous errors) (code 23)</code></pre></div>

## INTERRUPTION AND RETRY {#interruption}

<p>Ctrl-C interrupts a run with exit code 20. With <code>-P</code>, completed contiguous partial data can be retained. Rerun the same transfer to verify and reuse matching prefixes.</p>



<div class="example-caption">Retry a partial transfer</div>

```sh
xsync -aP src/ dst/
```

<p>A completed-byte prefix can be reused only when it matches the source. Transfers do not invoke fallback after an active copy has failed.</p>



## SCRIPT EXAMPLE {#scripts}



<div class="example-caption">Preserve the command’s original exit status</div>

```sh
if xsync -a --no-progress src/ dst/; then
  echo "transfer completed"
else
  status=$?
  echo "xsync failed with code $status" >&2
  exit "$status"
fi
```

<p>An exit-23 result may include successful files and failed files in the same run. Inspect the diagnostics rather than assuming the entire destination was rolled back.</p>



