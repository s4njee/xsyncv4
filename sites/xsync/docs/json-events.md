---
title: "xs-json(5)"
description: "The --progress=json event stream, field by field, with a published JSON Schema."
manual: "xs-json(5)"
manualName: "JSON progress events"
sectionNumber: "5"
---

# xs-json(5)

<div class="manual-deck"><strong>JSON progress events</strong><p>The --progress=json event stream, field by field, with a published JSON Schema.</p></div>

## SYNOPSIS {#synopsis}

```sh
xs -a --progress=json SRC/ DEST/ 2> events.ndjson
```

<p><code>--progress=json</code> writes one JSON object per line to stderr: periodic <code>progress</code> totals, a <code>file</code> record for each transferred regular file, and one final <code>complete</code> record. It produces the same stream on terminals and on pipes, with no cursor escapes. Ordinary stdout (<code>-v</code>, <code>-i</code>, <code>--out-format</code>, <code>--stats</code>) is unaffected.</p>

<p>The stream is described by <a href="progress.schema.json" download>progress.schema.json ↓</a> (JSON Schema 2020-12). <code>npm run check</code> validates the published recording, and fresh local, dry-run, checksum and push streams, against it. Every field is listed, and an unlisted field fails the check.</p>

<aside class="manual-note"><span>PARSING</span><p>Diagnostics also go to stderr, as plain text. Treat only lines that start with <code>{</code> as events. All counters are raw integers that are never scaled by <code>-h</code>. The schema describes the current output and is not versioned; it is not the versioned machine interface planned for the GUI.</p></aside>


## RECORDS {#records}

<h3 id="record-progress"><code>progress</code> records</h3>

<p>Periodic totals, emitted on every display tick.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Field</th><th scope="col">Type</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td><code>type</code></td><td>string</td><td>Always <code>&quot;progress&quot;</code>.</td></tr><tr><td><code>elapsed_ms</code></td><td>integer</td><td>Milliseconds since the transfer started.</td></tr><tr><td><code>files</code></td><td>integer</td><td>Regular files completed so far.</td></tr><tr><td><code>files_total</code></td><td>integer</td><td>Regular files planned so far. Grows while scanning.</td></tr><tr><td><code>bytes</code></td><td>integer</td><td>Logical file bytes completed. On a push this follows receiver acknowledgments.</td></tr><tr><td><code>bytes_total</code></td><td>integer</td><td>Logical file bytes planned so far.</td></tr><tr><td><code>files_seen</code></td><td>integer</td><td>Source entries discovered by the scan.</td></tr><tr><td><code>wire_bytes</code></td><td>integer</td><td>Bytes sent (push) or received (pull) on the connection, including compression and framing. Zero for local copies.</td></tr><tr><td><code>phase</code></td><td>string</td><td>What the transfer is doing now. One of <code>scanning</code>, <code>transferring</code>, <code>deleting</code>, <code>verifying</code>, <code>waiting for receiver</code>, <code>waiting for sender</code>.</td></tr><tr><td><code>deleted</code></td><td>integer</td><td>Destination entries deleted.</td></tr><tr><td><code>verified</code></td><td>integer</td><td>Successful checksum checks; source and destination hashes each count once.</td></tr><tr><td><code>scanning</code></td><td>boolean</td><td>True while the source scan is still running.</td></tr><tr><td><code>dry_run</code></td><td>boolean</td><td>True for <code>-n</code>; counts describe the plan, and nothing is written.</td></tr></tbody></table></div><h3 id="record-file"><code>file</code> records</h3>

<p>One transferred regular file (including clones and hard-link members), emitted after the destination operation succeeds, or once per planned file in a dry run.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Field</th><th scope="col">Type</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td><code>type</code></td><td>string</td><td>Always <code>&quot;file&quot;</code>.</td></tr><tr><td><code>path</code></td><td>string</td><td>Transfer-relative path. Valid UTF-8 is kept; control bytes are JSON-escaped, and invalid bytes appear as the Unicode code points of their byte values.</td></tr><tr><td><code>path_bytes_hex</code></td><td>string</td><td>The exact path bytes, hex encoded. Use this when names are not UTF-8.</td></tr><tr><td><code>code</code></td><td>string</td><td>The itemize change code, as printed by <code>-i</code>.</td></tr><tr><td><code>size</code></td><td>integer</td><td>File size in bytes.</td></tr><tr><td><code>bytes</code></td><td>integer</td><td>File-content bytes transferred (literal data). Zero for clones and dry runs; only the tail for a resumed file.</td></tr><tr><td><code>dry_run</code></td><td>boolean</td><td>True for <code>-n</code>; counts describe the plan, and nothing is written.</td></tr></tbody></table></div><h3 id="record-complete"><code>complete</code> records</h3>

<p>Final totals, emitted once at the end. Always the last record.</p>

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Field</th><th scope="col">Type</th><th scope="col">Meaning</th></tr></thead><tbody><tr><td><code>type</code></td><td>string</td><td>Always <code>&quot;complete&quot;</code>.</td></tr><tr><td><code>elapsed_ms</code></td><td>integer</td><td>Milliseconds since the transfer started.</td></tr><tr><td><code>files</code></td><td>integer</td><td>Regular files completed so far.</td></tr><tr><td><code>files_total</code></td><td>integer</td><td>Regular files planned so far. Grows while scanning.</td></tr><tr><td><code>bytes</code></td><td>integer</td><td>Logical file bytes completed. On a push this follows receiver acknowledgments.</td></tr><tr><td><code>bytes_total</code></td><td>integer</td><td>Logical file bytes planned so far.</td></tr><tr><td><code>files_seen</code></td><td>integer</td><td>Source entries discovered by the scan.</td></tr><tr><td><code>wire_bytes</code></td><td>integer</td><td>Bytes sent (push) or received (pull) on the connection, including compression and framing. Zero for local copies.</td></tr><tr><td><code>phase</code></td><td>string</td><td>Always "complete". Always <code>&quot;complete&quot;</code>.</td></tr><tr><td><code>deleted</code></td><td>integer</td><td>Destination entries deleted.</td></tr><tr><td><code>verified</code></td><td>integer</td><td>Successful checksum checks; source and destination hashes each count once.</td></tr><tr><td><code>scanning</code></td><td>boolean</td><td>True while the source scan is still running.</td></tr><tr><td><code>dry_run</code></td><td>boolean</td><td>True for <code>-n</code>; counts describe the plan, and nothing is written.</td></tr><tr><td><code>success</code></td><td>boolean</td><td>True only if the transfer finished with exit status 0.</td></tr><tr><td><code>exit_code</code></td><td>integer or null</td><td>The process exit status, or null if cleanup began before a fatal status was known.</td></tr></tbody></table></div>


## EXAMPLES {#examples}



<div class="example-caption">The final JSON record of a transfer</div>

```sh
xs -a --progress=json src/ dst/ 2>&1 >/dev/null | jq -c 'select(.type == "complete")'
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>{&quot;type&quot;:&quot;complete&quot;,&quot;elapsed_ms&quot;:2,&quot;files&quot;:5,&quot;files_total&quot;:5,&quot;bytes&quot;:1289005,&quot;bytes_total&quot;:1289005,&quot;files_seen&quot;:5,&quot;wire_bytes&quot;:0,&quot;phase&quot;:&quot;complete&quot;,&quot;deleted&quot;:0,&quot;verified&quot;:0,&quot;scanning&quot;:false,&quot;dry_run&quot;:false,&quot;success&quot;:true,&quot;exit_code&quot;:0}</code></pre></div>





<div class="example-caption">Transferred files from JSON events</div>

```sh
xs -a --progress=json src/ dst/ 2>&1 >/dev/null | jq -r 'select(.type == "file") | [.code, .size, .path] | @tsv' | sort -k3
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>&gt;f+++++++++	1288895	archive/2026-q3.log&#10;&gt;f+++++++++	33	docs/guide.md&#10;&gt;f+++++++++	42	docs/images/diagram.svg&#10;&gt;f+++++++++	14	notes.txt&#10;&gt;f+++++++++	21	scripts/build.sh</code></pre></div>





<div class="example-caption">A Python consumer that ignores diagnostics and reports the outcome</div>

```sh
xs -a --delete --progress=json src/ dst/ 2> events.ndjson
python3 - events.ndjson <<'PY'
import json, sys
events = [json.loads(line) for line in open(sys.argv[1]) if line.startswith('{')]
files = [e for e in events if e['type'] == 'file']
done = events[-1]
print(f"{len(files)} files, {sum(e['bytes'] for e in files):,} bytes sent")
print(f"deleted {done['deleted']}, exit {done['exit_code']}, success {done['success']}")
PY
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>5 files, 1,289,005 bytes sent&#10;deleted 1, exit 0, success True</code></pre></div>




## BEHAVIOR {#behavior}

<ul>
<li><strong>Order.</strong> <code>progress</code> and <code>file</code> records interleave as work happens. Once a transfer starts, <code>complete</code> is its last event, even when it fails (for example, <code>"exit_code":25</code> when <code>--max-delete</code> stops deletions). A failure during setup, such as a missing source or an invalid option, exits before any event is written, so check the process exit status as well.</li>
<li><strong>Dry runs.</strong> With <code>-n</code>, <code>file</code> records describe planned operations, and <code>dry_run</code> is true throughout.</li>
<li><strong>Pushes.</strong> <code>bytes</code> follows what the receiver has acknowledged writing, so it can trail <code>wire_bytes</code>.</li>
<li><strong>Remote transfers.</strong> JSON events need a helper that supports structured file events. If the helper lacks them, or the transfer would otherwise fall back to rsync, xs exits with an error instead, because rsync cannot produce this stream.</li>
<li><strong>Suppression.</strong> <code>--no-progress</code> or <code>--quiet</code> suppresses the stream. The last progress-mode option on the command line wins.</li>
</ul>


