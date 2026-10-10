---
title: "xs-recipes(7)"
description: "Complete, tested workflows \u2014 snapshots, safe mirrors, a Raspberry Pi, scheduled backups \u2014 with their real output."
manual: "xs-recipes(7)"
manualName: "Recipes"
sectionNumber: "7"
---

# xs-recipes(7)

<div class="manual-deck"><strong>Recipes</strong><p>Complete, tested workflows — snapshots, safe mirrors, a Raspberry Pi, scheduled backups — with their real output.</p></div>

## ABOUT THESE RECIPES {#about}

<p>Each recipe below was run against the current binary in a disposable directory, and the output shown is what it printed. Remote recipes went through an ssh stand-in that runs the other side on the same machine, so <code>host:backup/</code> is a directory next to the source. Replace <code>src/</code>, <code>dst/</code> and the host names with your own.</p>


## DATED SNAPSHOTS {#snapshots}

<p>Keep one directory per day. Each new snapshot hard-links every unchanged file to the previous day’s copy, so a full-looking snapshot costs only the space of what changed.</p>



<div class="example-caption">Dated snapshots that share unchanged files</div>

```sh
snapshot() {
  previous=$(ls -1 snapshots | tail -n 1)
  xs -a ${previous:+--link-dest=../$previous} src/ "snapshots/$1/"
}
snapshot 2026-10-09
printf 'Action items\n' >> src/notes.txt
snapshot 2026-10-10
ls snapshots
stat -c '%h links  %n' snapshots/*/notes.txt snapshots/*/docs/guide.md
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>2026-10-09&#10;2026-10-10&#10;1 links  snapshots/2026-10-09/notes.txt&#10;1 links  snapshots/2026-10-10/notes.txt&#10;2 links  snapshots/2026-10-09/docs/guide.md&#10;2 links  snapshots/2026-10-10/docs/guide.md</code></pre></div>



<p><code>notes.txt</code> changed, so each snapshot has its own copy (1 link). <code>guide.md</code> did not, so both snapshots share one file (2 links). Deleting an old snapshot directory frees only the files no other snapshot shares. Treat snapshots as read-only: an in-place write or metadata change to a shared file changes it in every snapshot (<a href="snapshots.html#shared-files">shared files</a>).</p>


## A SAFE MIRROR {#mirror}

<p>Preview first. The dry run prints the same itemized plan the real run will perform, and ends with a one-line summary.</p>



<div class="example-caption">Preview a mirror</div>

```sh
xs -ani --delete src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>.d..t...... ./&#10;.d..t...... docs/&#10;&gt;f+++++++++ docs/draft.md&#10;.d..t...... docs/images/&#10;*deleting   docs/images/diagram.svg&#10;*deleting   old/&#10;*deleting   old/a.txt&#10;*deleting   old/b.txt&#10;would transfer 1 files (6B), delete 4</code></pre></div>



<p>If the plan is what you expect, run it with a deletion limit somewhat above the planned count. A mistaken source path, such as an unmounted disk, then stops at the limit (exit 25) rather than emptying the destination.</p>



<div class="example-caption">Run the reviewed mirror with a deletion limit</div>

```sh
xs -ai --delete --max-delete=10 src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>.d..t...... ./&#10;.d..t...... docs/&#10;&gt;f+++++++++ docs/draft.md&#10;.d..t...... docs/images/&#10;*deleting   docs/images/diagram.svg&#10;*deleting   old/&#10;*deleting   old/a.txt&#10;*deleting   old/b.txt</code></pre></div>




## A RASPBERRY PI, OR ANY HOST WITHOUT XS {#raspberry-pi}

<p>Build the release binaries once (<a href="install.html#releases">release binaries</a>), install the helper, then push natively. The installer picks the ARM64 build for a 64-bit Pi.</p>



<div class="example-caption">Install xs on a host that does not have it, then push natively</div>

```sh
export XSYNC_RELEASE_DIR=releases
xs --install user@pi
xs -azi --no-fallback src/ user@pi:backup/ | tail -n 3
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>Installed xs-linux-amd64 on user@pi at ~/.local/bin/xs&#10;xs  version 0.1.0  protocol version 4  git 1fff2a09ae2c&#10;&lt;f+++++++++ notes.txt&#10;cd+++++++++ scripts/&#10;&lt;f+++++++++ scripts/build.sh</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<p>Without the helper, the same push still works but runs rsync, with a notice (<a href="troubleshooting.html#fallback">troubleshooting</a>). Adding <code>--no-fallback</code>, as here, proves the native path was used.</p>


## FILES CHOSEN BY FIND {#find}



<div class="example-caption">Copy the files find selects, with NUL delimiters</div>

```sh
(cd src && find . -name '*.md' -print0) | xs -ai0 --files-from=- src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;&gt;f+++++++++ docs/odd\#012name.md</code></pre></div>



<p>Run <code>find</code> from inside the source so the names are relative to it, and use <code>-print0</code> with <code>-0</code> so any filename survives, newlines included. In the output, xs escapes the newline as <code>\#012</code>. With <code>--files-from</code>, <code>-a</code> does not recurse into listed directories; add <code>-r</code> if the list names directories whose contents you want.</p>


## A SCHEDULED BACKUP {#scheduled}



<div class="example-caption">A scheduled backup that logs and keeps the exit status</div>

```sh
cat > backup.sh <<'SH'
#!/bin/sh
log=backup.log
xs -a --delete --log-file="$log" --out-format='%t %i %n' src/ dst/ > /dev/null
status=$?
echo "$(date -u '+%Y/%m/%d %H:%M:%S') finished with exit status $status" >> "$log"
exit $status
SH
sh backup.sh; echo "exit status: $?"
head -n 3 backup.log; tail -n 1 backup.log
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>exit status: 0&#10;2026/10/10 16:17:47 cd+++++++++ ./&#10;2026/10/10 16:17:47 cd+++++++++ archive/&#10;2026/10/10 16:17:47 &gt;f+++++++++ archive/2026-q3.log&#10;2026/10/10 16:17:47 finished with exit status 0</code></pre></div>



<p>The log gets the same lines stdout would, plus the script’s final status line, and the script exits with xs’s status so the scheduler can alert on failure. Progress stays off on its own, because a scheduler’s stderr is not a terminal. Personal defaults still apply; set <code>XSYNC_CONFIG=''</code> and <code>XSYNC_OPTS=''</code> in the job if they should not.</p>

<div class="example-caption">Run it nightly at 02:30: a crontab line (scheduler configuration, not captured)</div>

```sh
30 2 * * * cd /path/to/backups && sh backup.sh
```

<div class="example-caption">The same with launchd on macOS: ~/Library/LaunchAgents/local.backup.plist (not captured)</div>

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>local.backup</string>
  <key>WorkingDirectory</key><string>/path/to/backups</string>
  <key>ProgramArguments</key><array><string>/bin/sh</string><string>backup.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>30</integer></dict>
</dict></plist>
```


## A WRAPPER THAT READS JSON EVENTS {#json}



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



<p>Diagnostics share stderr with the events, so keep only lines that start with <code>{</code>. The last event is always <code>complete</code> once a transfer has started; check the process status too, for failures before it starts. Every field is documented in <a href="json-events.html">JSON progress events</a>.</p>


## AN OVERNIGHT PUSH ON A SLOW LINK {#overnight}



<div class="example-caption">A bandwidth-limited push that gives up on a stalled link</div>

```sh
xs -az --bwlimit=2M --timeout=60 --stats src/ host:backup/ | tail -n 4
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>Total bytes received: 138&#10;&#10;sent 114,187 bytes  received 138 bytes  1,215,787.92 bytes/sec&#10;total size is 1,289,005  speedup is 11.27</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<p><code>--bwlimit</code> caps the bytes on the wire after compression, so <code>-z</code> moves more file data within the same budget. <code>--timeout=60</code> ends the run with exit 30 if the connection stops moving for a minute; keep-alives stop an idle but healthy connection from tripping it. Run it again in the morning: completed files are skipped, and <code>-P</code> would also resume a large file that was cut off.</p>


## PRESERVING EVERYTHING {#preserve}



<div class="example-caption">Preserve hard links, ACLs and extended attributes (Linux)</div>

```sh
xs -aHAXi src/ dst/ | head -n 6
getfacl -c dst/notes.txt | grep nobody; getfattr -d dst/docs/guide.md 2>/dev/null | grep origin || python3 -c "import os; print(os.getxattr('dst/docs/guide.md', 'user.origin'))"
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ archive/&#10;&gt;f+++++++++ archive/2026-q3.log&#10;cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;cd+++++++++ docs/images/&#10;user:nobody:r--&#10;b&#x27;scanner&#x27;</code></pre></div>



<p>On Linux, <code>-aHAX</code> adds hard links, ACLs and extended attributes to archive mode. On macOS, add <code>-N</code> for creation times and <code>--fileflags</code> for BSD flags: <code>xs -aHAXN --fileflags src/ dst/</code> (not captured here, because this page is captured on Linux). Remote ACLs need both hosts on the same platform. A macOS ↔ Linux <code>-A</code> transfer falls back to rsync, and rsync rejected the tested cross-platform ACLs too, so fallback is no guarantee of a conversion.</p>


