---
title: "xsync-transfer(1)"
description: "Copy locally, push or pull remotely, and choose exactly what a path means."
manual: "xsync-transfer(1)"
manualName: "Transfers & paths"
sectionNumber: "1"
---

# xsync-transfer(1)

<div class="manual-deck"><strong>Transfers &amp; paths</strong><p>Copy locally, push or pull remotely, and choose exactly what a path means.</p></div>

## SYNOPSIS {#synopsis}



<div class="example-caption">Transfer form</div>

```sh
xsync [OPTION]... SRC [SRC]... DEST
```



## LOCAL COPY {#local}



<div class="example-caption">Copy contents</div>

```sh
xsync -aP src/ dst/
```



<div class="example-caption">Copy the source directory itself</div>

```sh
xsync -aP src dst/
```

<p>A trailing source slash selects the directory’s contents. Without it, the source basename is included. For example, copying <code>src</code> to an existing <code>dst/</code> creates <code>dst/src/</code>.</p>



<div class="example-caption">Multiple local sources</div>

```sh
xsync -aP notes.txt photos/ archive/
```



## SSH PUSH AND PULL {#remote}



<div class="example-caption">Push local files to the host</div>

```sh
xsync -azP src/ user@host:/backup/src/
```



<div class="example-caption">Pull remote files locally</div>

```sh
xsync -azP user@host:/data/ data/
```

<p><code>-z</code> compresses remote file data with zstd. It has no compression effect on local copies. A transfer may have one remote endpoint; native remote-to-remote transfers are unsupported.</p>



## LISTING {#listing}



<div class="example-caption">List immediate entries, or recurse remotely</div>

```sh
xsync src/
xsync -r user@host:/data/
```



<div class="example-caption">Inspect sources without modifying the destination</div>

```sh
xsync --list-only -a src/ dst/
```

<p>A single source argument lists metadata. A slash lists a directory’s immediate contents; <code>-r</code> includes descendants. Listings show type, permissions, byte size, modification time, and names. <code>-l</code> adds symlink targets.</p>



## RELATIVE PATHS AND SELECTION {#relative}



<div class="example-caption">Create dst/project/file.txt</div>

```sh
xsync -aR /data/./project/file.txt dst/
```

<p>With <code>-R</code>, <code>/./</code> cuts off the path prefix. <code>--files-from</code> selects names relative to a single source root.</p>



<div class="example-caption">NUL-delimited selection from the current directory</div>

```sh
find . -type f -print0 | xsync -a0 --files-from=- ./ user@host:backup/
```

<aside class="manual-note"><span>NOTE</span><p>With a file list, <code>-a</code> preserves attributes but does not imply recursive directory traversal. Add <code>-r</code> when selected directories should be copied recursively.</p></aside>

## EXISTING FILES {#existing}



<div class="example-caption">Create files that are missing at the destination</div>

```sh
xsync -aP --ignore-existing src/ dst/
```



<div class="example-caption">Skip files that are newer on the receiver</div>

```sh
xsync -auP src/ dst/
```

<p><code>--existing</code> skips new files. <code>--ignore-existing</code> skips existing files. <code>-u</code> skips a file when the destination is newer. These are batch transfer policies, not interactive conflict dialogs.</p>



