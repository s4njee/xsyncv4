---
title: "xs-output(1)"
description: "Read terminal status, capture structured events, and keep file output separate."
manual: "xs-output(1)"
manualName: "Progress & output"
sectionNumber: "1"
---

# xs-output(1)

<div class="manual-deck"><strong>Progress &amp; output</strong><p>Read terminal status, capture structured events, and keep file output separate.</p></div>

## OUTPUT STREAMS {#streams}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Stream</th><th scope="col">Contents</th></tr></thead><tbody><tr><td>stderr</td><td>Live progress, JSON progress events, fallback notices, and diagnostics</td></tr><tr><td>stdout</td><td>Listings, verbose/itemized file output, stats, and dry-run summaries</td></tr></tbody></table></div><p>Progress is automatic when stderr is a terminal. Scripts stay quiet unless progress is explicitly requested. <code>--quiet</code> suppresses progress and non-error messages.</p>



## TERMINAL PROGRESS {#terminal}



<div class="example-caption">Partial retention plus progress</div>

```sh
xs -aP src/ dst/
```

<p>Long-running files receive their own row after 200 ms; quick files share a small-files completion-rate row. The total line includes counts, bytes, throughput, and ETA when known.</p>

<p>Push progress follows successful receiver writes, rather than merely bytes read or sent. <code>sent … wire</code> is a separate count. With <code>-z</code>, the display adds wire rate and compression ratio; <code>-vv</code> adds a limiting-stage estimate.</p>

<a class="manual-back-link" href="../index.html#demo" target="_self">Replay actual xsync terminal output <span aria-hidden="true">↗</span></a>

## PHASES {#phases}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Label</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td>scanning</td><td>Discovering entries; totals can still grow</td></tr><tr><td>verifying N checks</td><td>Successful source and destination checksum checks</td></tr><tr><td>cloning path/</td><td>Whole-directory APFS clone in progress</td></tr><tr><td>deleting N</td><td>Destination entries removed</td></tr><tr><td>waiting for receiver</td><td>Push helper is finishing writes or cleanup</td></tr><tr><td>waiting for sender</td><td>Pull helper has not exited</td></tr></tbody></table></div><p>The terminal and its width determine which details fit. <code>TERM=dumb</code> and non-UTF-8 locales use ASCII fallbacks; <code>NO_COLOR</code> disables color escape sequences.</p>



## JSON EVENTS {#json}



<div class="example-caption">Capture real newline-delimited JSON on stderr</div>

```sh
xs -a --progress=json src/ dst/ 2>progress.ndjson
```

<p>Events have type <code>progress</code>, <code>file</code>, or <code>complete</code>. Counters are raw integers. Progress records include elapsed milliseconds, planned/completed counts, bytes, wire bytes, phase, and scan/dry-run flags. Completed file events include path and itemization fields; the final event includes success and exit code.</p>

<aside class="manual-note"><span>NOTE</span><p>Diagnostics can also appear on stderr. Parse JSON event lines explicitly rather than treating every stderr line as JSON. A remote JSON request requires structured file-event support; rsync fallback cannot supply JSON.</p></aside><div class="captured-doc-output"><span class="micro">ACTUAL CAPTURED EVENT</span><pre><code id="actual-json-event">{
  &quot;type&quot;: &quot;progress&quot;,
  &quot;elapsed_ms&quot;: 66,
  &quot;files&quot;: 128,
  &quot;files_total&quot;: 130,
  &quot;bytes&quot;: 103120,
  &quot;bytes_total&quot;: 6460112,
  &quot;files_seen&quot;: 130,
  &quot;wire_bytes&quot;: 0,
  &quot;phase&quot;: &quot;transferring&quot;,
  &quot;deleted&quot;: 0,
  &quot;verified&quot;: 0,
  &quot;scanning&quot;: false,
  &quot;dry_run&quot;: false
}</code></pre><a href="../recordings/progress.ndjson" download>Download the full captured stream ↗</a></div>

## FILE OUTPUT AND LOGS {#itemization}



<div class="example-caption">Itemize changes and append stdout to a log</div>

```sh
xs -ai --out-format='%i %n%L' --log-file=transfer.log src/ dst/
```

<p><code>%i %n %L %l %o %f %b %t %%</code> are supported, including field widths. <code>%b</code> counts file-content bytes before compression; clones, metadata-only changes, and dry runs count zero. This differs from rsync’s protocol-byte accounting.</p>

<p>When stdout is redirected, file events are sorted by path and buffered until the transfer ends. A terminal receives them as they finish. The log receives the same stdout stream, without extra timestamps or prefixes.</p>



## UNITS AND PIPES {#units}



<div class="example-caption">Use 1024-based display units</div>

```sh
xs -ahhP src/ dst/
```



<div class="example-caption">Use the rsync-shaped plain progress stream off a terminal</div>

```sh
xs -a --info=progress2 src/ dst/ 2>progress.log
```

<p>Default and <code>-h</code> display units use base 1000; <code>-hh</code> uses base 1024. Explicit ordinary <code>--progress</code> prints one plain line per second on pipes. JSON counters always remain unscaled integers.</p>



<div class="example-caption">Transfer statistics</div>

```sh
xs -a --stats src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>Number of files: 10 (reg: 5, dir: 4, link: 1)&#10;Number of created files: 10 (reg: 5, dir: 4, link: 1)&#10;Number of deleted files: 0&#10;Number of regular files transferred: 5&#10;Total file size: 1,289,005 bytes&#10;Total transferred file size: 1,289,005 bytes&#10;Delta literal data: 0 bytes&#10;Delta matched data: 0 bytes&#10;Total bytes sent: 1,289,005&#10;Total bytes received: 0&#10;&#10;sent 1,289,005 bytes  received 0 bytes  271,018,632.93 bytes/sec&#10;total size is 1,289,005  speedup is 1.00</code></pre></div>



<div class="example-caption">rsync-shaped progress lines on a pipe</div>

```sh
xs -a --info=progress2 src/ dst/ 2>&1 | tail -1
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>      1,289,005 100%  347.89MB/s    0:00:00 (xfr#5, to-chk=0/5)</code></pre></div>



