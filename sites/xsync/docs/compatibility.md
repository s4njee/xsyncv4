---
title: "xsync-compat(7)"
description: "Know the native path, delegation behavior, and platform boundaries."
manual: "xsync-compat(7)"
manualName: "Compatibility"
sectionNumber: "7"
---

# xsync-compat(7)

<div class="manual-deck"><strong>Compatibility</strong><p>Know the native path, delegation behavior, and platform boundaries.</p></div>

## NATIVE PROTOCOL {#protocol}

<p>xsync is a rsync work-alike, not a wire-compatible rsync implementation. Current protocol 4 interoperates with protocols 4 and 3. Capabilities are intersected during negotiation; missing requested semantics fail or delegate before destination writes.</p>



## FALLBACK {#fallback}



<div class="example-caption">Require native xs on both ends</div>

```sh
xs --no-fallback -azP src/ user@host:/backup/
```

<p>By default, unsupported flags, missing remote helpers, unsupported protocol versions, and daemon URLs can re-execute a real rsync from PATH. One stderr notice explains the delegation. Original arguments are retained after xsync-only worker/clone/atomic extensions are removed.</p>

<p>Malformed protocol data and failures during a transfer do not trigger fallback. An explicit <code>--rsync-path</code> is retained, so it must also be an appropriate rsync command if delegation is needed.</p>



## DELEGATED OPTIONS {#delegated}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Request</th><th scope="col">Behavior</th></tr></thead><tbody><tr><td><code>-b / --backup</code></td><td>Delegate to rsync</td></tr><tr><td><code>--compare-dest / --copy-dest</code></td><td>Delegate to rsync</td></tr><tr><td><code>--append / --partial-dir</code></td><td>Delegate to rsync</td></tr><tr><td><code>--remove-source-files</code></td><td>Delegate to rsync</td></tr><tr><td><code>host::module / rsync://</code></td><td>Delegate daemon transport to rsync</td></tr><tr><td><code>--fsync / --preallocate / --contimeout</code></td><td>Unsupported natively; delegate or fail in strict mode</td></tr></tbody></table></div><p>Options such as <code>--skip-compress</code>, <code>--block-size</code>, <code>--checksum-choice</code>, <code>--log-file-format</code>, and <code>--debug</code> also delegate. Native <code>--compress-choice</code> accepts zstd or none.</p>



## BEHAVIORAL DIFFERENCES {#differences}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Area</th><th scope="col">xs behavior</th></tr></thead><tbody><tr><td>New byte-copied files</td><td>Atomic temporary file + rename by default</td></tr><tr><td>Local compression</td><td>-z has no compression effect locally</td></tr><tr><td>APFS clones</td><td>Can preserve more metadata than -a requests</td></tr><tr><td>Output ordering</td><td>Non-terminal file output is sorted at end of run</td></tr><tr><td>%b</td><td>File-content bytes before compression; not rsync wire bytes</td></tr><tr><td>JSON progress</td><td>Requires native structured events; never supplied by fallback</td></tr></tbody></table></div>

## PLATFORM BOUNDARIES {#platforms}

<p>macOS and Linux are current targets. Creation times and BSD flags are macOS features; native remote ACLs need matching styles. Unsupported macOS socket metadata requests can return exit 23. Deep source paths beyond PATH_MAX report path-length errors.</p>

<p>Native Windows support, additional protocols, and remote-to-remote copies are proposed follow-on work in the GUI backlog. They are not current CLI capabilities.</p>



## DOCUMENTED NO-OPS {#noops}

<p><code>-s</code>/<code>--protect-args</code>/<code>--secluded-args</code> need no extra action because native paths travel as protocol data. Blocking-I/O switches cannot alter the internally polled pipe transport. <code>--no-motd</code> has no native daemon greeting to suppress.</p>



