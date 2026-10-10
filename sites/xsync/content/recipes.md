---
slug: recipes
title: xs-recipes(7)
name: Recipes
summary: Complete, tested workflows — snapshots, safe mirrors, a Raspberry Pi, scheduled backups — with their real output.
group: WORKFLOWS
after: snapshots
---

## ABOUT THESE RECIPES {#about}

<p>Each recipe below was run against the current binary in a disposable directory, and the output shown is what it printed. Remote recipes went through an ssh stand-in that runs the other side on the same machine, so <code>host:backup/</code> is a directory next to the source. Replace <code>src/</code>, <code>dst/</code> and the host names with your own.</p>

## DATED SNAPSHOTS {#snapshots}

<p>Keep one directory per day. Each new snapshot hard-links every unchanged file to the previous day’s copy, so a full-looking snapshot costs only the space of what changed.</p>

<!--example:recipe-snapshots-->

<p><code>notes.txt</code> changed, so each snapshot has its own copy (1 link). <code>guide.md</code> did not, so both snapshots share one file (2 links). Deleting an old snapshot directory frees only the files no other snapshot shares. Treat snapshots as read-only: an in-place write or metadata change to a shared file changes it in every snapshot (<a href="snapshots.html#shared-files">shared files</a>).</p>

## A SAFE MIRROR {#mirror}

<p>Preview first. The dry run prints the same itemized plan the real run will perform, and ends with a one-line summary.</p>

<!--example:dry-run-mirror-->

<p>If the plan is what you expect, run it with a deletion limit somewhat above the planned count. A mistaken source path, such as an unmounted disk, then stops at the limit (exit 25) rather than emptying the destination.</p>

<!--example:mirror-execute-->

## A RASPBERRY PI, OR ANY HOST WITHOUT XS {#raspberry-pi}

<p>Build the release binaries once (<a href="install.html#releases">release binaries</a>), install the helper, then push natively. The installer picks the ARM64 build for a 64-bit Pi.</p>

<!--example:recipe-install-->

<p>Without the helper, the same push still works but runs rsync, with a notice (<a href="troubleshooting.html#fallback">troubleshooting</a>). Adding <code>--no-fallback</code>, as here, proves the native path was used.</p>

## FILES CHOSEN BY FIND {#find}

<!--example:recipe-find-->

<p>Run <code>find</code> from inside the source so the names are relative to it, and use <code>-print0</code> with <code>-0</code> so any filename survives, newlines included. In the output, xs escapes the newline as <code>\#012</code>. With <code>--files-from</code>, <code>-a</code> does not recurse into listed directories; add <code>-r</code> if the list names directories whose contents you want.</p>

## A SCHEDULED BACKUP {#scheduled}

<!--example:recipe-cron-->

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

<!--example:json-python-->

<p>Diagnostics share stderr with the events, so keep only lines that start with <code>{</code>. The last event is always <code>complete</code> once a transfer has started; check the process status too, for failures before it starts. Every field is documented in <a href="json-events.html">JSON progress events</a>.</p>

## AN OVERNIGHT PUSH ON A SLOW LINK {#overnight}

<!--example:recipe-overnight-->

<p><code>--bwlimit</code> caps the bytes on the wire after compression, so <code>-z</code> moves more file data within the same budget. <code>--timeout=60</code> ends the run with exit 30 if the connection stops moving for a minute; keep-alives stop an idle but healthy connection from tripping it. Run it again in the morning: completed files are skipped, and <code>-P</code> would also resume a large file that was cut off.</p>

## PRESERVING EVERYTHING {#preserve}

<!--example:recipe-preserve-->

<p>On Linux, <code>-aHAX</code> adds hard links, ACLs and extended attributes to archive mode. On macOS, add <code>-N</code> for creation times and <code>--fileflags</code> for BSD flags: <code>xs -aHAXN --fileflags src/ dst/</code> (not captured here, because this page is captured on Linux). Remote ACLs need both hosts on the same platform. A macOS ↔ Linux <code>-A</code> transfer falls back to rsync, and rsync rejected the tested cross-platform ACLs too, so fallback is no guarantee of a conversion.</p>
