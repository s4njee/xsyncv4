---
title: "xs-transfer(1)"
description: "Copy locally, push or pull remotely, and choose exactly what a path means."
manual: "xs-transfer(1)"
manualName: "Transfers & paths"
sectionNumber: "1"
---

# xs-transfer(1)

<div class="manual-deck"><strong>Transfers &amp; paths</strong><p>Copy locally, push or pull remotely, and choose exactly what a path means.</p></div>

## SYNOPSIS {#synopsis}



<div class="example-caption">Transfer form</div>

```sh
xs [OPTION]... SRC [SRC]... DEST
```



## LOCAL COPY {#local}



<div class="example-caption">Copy contents</div>

```sh
xs -aP src/ dst/
```



<div class="example-caption">Copy the source directory itself</div>

```sh
xs -aP src dst/
```

<p>A trailing source slash selects the directory’s contents. Without it, the source basename is included. For example, copying <code>src</code> to an existing <code>dst/</code> creates <code>dst/src/</code>.</p>



<div class="example-caption">Multiple local sources</div>

```sh
xs -aP notes.txt photos/ archive/
```



## SSH PUSH AND PULL {#remote}



<div class="example-caption">Push local files to the host</div>

```sh
xs -azP src/ user@host:/backup/src/
```



<div class="example-caption">Pull remote files locally</div>

```sh
xs -azP user@host:/data/ data/
```

<p><code>-z</code> compresses remote file data with zstd. It has no compression effect on local copies. A transfer may have one remote endpoint; native remote-to-remote transfers are unsupported.</p>



<div class="example-caption">Push over SSH</div>

```sh
xs -azi src/ host:backup/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ archive/&#10;&lt;f+++++++++ archive/2026-q3.log&#10;cd+++++++++ docs/&#10;&lt;f+++++++++ docs/guide.md&#10;cd+++++++++ docs/images/&#10;&lt;f+++++++++ docs/images/diagram.svg&#10;cL+++++++++ latest -&gt; notes.txt&#10;&lt;f+++++++++ notes.txt&#10;cd+++++++++ scripts/&#10;&lt;f+++++++++ scripts/build.sh</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<div class="example-caption">Pull over SSH</div>

```sh
xs -azi host:backup/ restore/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ ./&#10;cd+++++++++ archive/&#10;&gt;f+++++++++ archive/2026-q3.log&#10;cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;cd+++++++++ docs/images/&#10;&gt;f+++++++++ docs/images/diagram.svg&#10;cL+++++++++ latest -&gt; notes.txt&#10;&gt;f+++++++++ notes.txt&#10;cd+++++++++ scripts/&#10;&gt;f+++++++++ scripts/build.sh</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



<div class="example-caption">Wire and compression totals for a push</div>

```sh
xs -az --stats src/ host:backup/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>Number of files: 10 (reg: 5, dir: 4, link: 1)&#10;Number of created files: 10 (reg: 5, dir: 4, link: 1)&#10;Number of deleted files: 0&#10;Number of regular files transferred: 5&#10;Total file size: 1,289,005 bytes&#10;Total transferred file size: 1,289,005 bytes&#10;Delta literal data: 0 bytes&#10;Delta matched data: 0 bytes&#10;Total bytes sent: 114,184&#10;Total bytes received: 132&#10;&#10;sent 114,184 bytes  received 132 bytes  1,996,295.30 bytes/sec&#10;total size is 1,289,005  speedup is 11.28</code></pre><p class="example-provenance">Captured through <code>tests/fakessh.sh</code>, an ssh stand-in that runs the remote side on the same machine.</p></div>



## LISTING {#listing}



<div class="example-caption">List immediate entries, or recurse remotely</div>

```sh
xs src/
xs -r user@host:/data/
```



<div class="example-caption">Inspect sources without modifying the destination</div>

```sh
xs --list-only -a src/ dst/
```

<p>A single source argument lists metadata. A slash lists a directory’s immediate contents; <code>-r</code> includes descendants. Listings show type, permissions, byte size, modification time, and names. <code>-l</code> adds symlink targets.</p>



<div class="example-caption">List a directory’s entries</div>

```sh
xs src/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>drwxr-xr-x          4,096 2026/10/10 12:00:00 .&#10;lrwxrwxrwx              9 2026/10/10 12:00:00 latest&#10;-rw-r--r--             14 2026/10/10 12:00:00 notes.txt&#10;drwxr-xr-x          4,096 2026/10/10 12:00:00 archive&#10;drwxr-xr-x          4,096 2026/10/10 12:00:00 docs&#10;drwxr-xr-x          4,096 2026/10/10 12:00:00 scripts</code></pre></div>



<div class="example-caption">List recursively, with symlink targets</div>

```sh
xs -r src/docs
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>drwxr-xr-x          4,096 2026/10/10 12:00:00 docs&#10;-rw-r--r--             33 2026/10/10 12:00:00 docs/guide.md&#10;drwxr-xr-x          4,096 2026/10/10 12:00:00 docs/images&#10;-rw-r--r--             42 2026/10/10 12:00:00 docs/images/diagram.svg</code></pre></div>



## RELATIVE PATHS AND SELECTION {#relative}



<div class="example-caption">Create dst/project/file.txt</div>

```sh
xs -aR /data/./project/file.txt dst/
```

<p>With <code>-R</code>, <code>/./</code> cuts off the path prefix. <code>--files-from</code> selects names relative to a single source root.</p>



<div class="example-caption">NUL-delimited selection from the current directory</div>

```sh
find . -type f -print0 | xs -a0 --files-from=- ./ user@host:backup/
```

<aside class="manual-note"><span>NOTE</span><p>With a file list, <code>-a</code> preserves attributes but does not imply recursive directory traversal. Add <code>-r</code> when selected directories should be copied recursively.</p></aside>

<div class="example-caption">Keep the path after /./</div>

```sh
xs -aiR src/./docs/guide.md dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md</code></pre></div>



<div class="example-caption">Copy a list of names relative to the source</div>

```sh
printf 'notes.txt\ndocs/guide.md\n' | xs -ai --files-from=- src/ dst/
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>cd+++++++++ docs/&#10;&gt;f+++++++++ docs/guide.md&#10;&gt;f+++++++++ notes.txt</code></pre></div>



## EXISTING FILES {#existing}



<div class="example-caption">Create files that are missing at the destination</div>

```sh
xs -aP --ignore-existing src/ dst/
```



<div class="example-caption">Skip files that are newer on the receiver</div>

```sh
xs -auP src/ dst/
```

<p><code>--existing</code> skips new files. <code>--ignore-existing</code> skips existing files. <code>-u</code> skips a file when the destination is newer. These are batch transfer policies, not interactive conflict dialogs.</p>



