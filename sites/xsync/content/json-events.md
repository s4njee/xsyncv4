---
slug: json-events
title: xs-json(5)
name: JSON progress events
summary: The --progress=json event stream, field by field, with a published JSON Schema.
group: REFERENCE
after: itemize
---

## SYNOPSIS {#synopsis}

```sh
xs -a --progress=json SRC/ DEST/ 2> events.ndjson
```

<p><code>--progress=json</code> writes one JSON object per line to stderr: periodic <code>progress</code> totals, a <code>file</code> record for each transferred regular file, and one final <code>complete</code> record. It produces the same stream on terminals and on pipes, with no cursor escapes. Ordinary stdout (<code>-v</code>, <code>-i</code>, <code>--out-format</code>, <code>--stats</code>) is unaffected.</p>

<p>The stream is described by <a href="progress.schema.json" download>progress.schema.json ↓</a> (JSON Schema 2020-12). <code>npm run check</code> validates the published recording, and fresh local, dry-run, checksum and push streams, against it. Every field is listed, and an unlisted field fails the check.</p>

<aside class="manual-note"><span>PARSING</span><p>Diagnostics also go to stderr, as plain text. Treat only lines that start with <code>{</code> as events. All counters are raw integers that are never scaled by <code>-h</code>. The schema describes the current output and is not versioned; it is not the versioned machine interface planned for the GUI.</p></aside>

## RECORDS {#records}

<!--generated:json-schema-->

## EXAMPLES {#examples}

<!--example:json-complete-->

<!--example:json-files-->

<!--example:json-python-->

## BEHAVIOR {#behavior}

<ul>
<li><strong>Order.</strong> <code>progress</code> and <code>file</code> records interleave as work happens. Once a transfer starts, <code>complete</code> is its last event, even when it fails (for example, <code>"exit_code":25</code> when <code>--max-delete</code> stops deletions). A failure during setup, such as a missing source or an invalid option, exits before any event is written, so check the process exit status as well.</li>
<li><strong>Dry runs.</strong> With <code>-n</code>, <code>file</code> records describe planned operations, and <code>dry_run</code> is true throughout.</li>
<li><strong>Pushes.</strong> <code>bytes</code> follows what the receiver has acknowledged writing, so it can trail <code>wire_bytes</code>.</li>
<li><strong>Remote transfers.</strong> JSON events need a helper that supports structured file events. If the helper lacks them, or the transfer would otherwise fall back to rsync, xs exits with an error instead, because rsync cannot produce this stream.</li>
<li><strong>Suppression.</strong> <code>--no-progress</code> or <code>--quiet</code> suppresses the stream. The last progress-mode option on the command line wins.</li>
</ul>
