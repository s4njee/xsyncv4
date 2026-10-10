---
title: "xs(1)"
description: "Parallel file transfers, familiar commands, and progress you can read."
manual: "xs(1)"
manualName: "The xsync manual"
sectionNumber: "1"
---

# xs(1)

<div class="manual-deck"><strong>The xsync manual</strong><p>Parallel file transfers, familiar commands, and progress you can read.</p></div>

## NAME {#name}

<p><strong>xs</strong> — fast, parallel rsync work-alike for macOS and Linux. The xsync project installs a single executable, <code>xs</code>.</p>



## SYNOPSIS {#synopsis}



<div class="example-caption">Command forms</div>

```sh
xs [OPTION]... SRC [SRC]... DEST
xs [OPTION]... SRC
xs [OPTION]... SRC [SRC]... [USER@]HOST:DEST
xs [OPTION]... [USER@]HOST:SRC [DEST]
```



## DESCRIPTION {#description}

<p>xsync copies file trees locally or over SSH. It uses a C++20 engine, parallel workers, a native transfer protocol, and a live progress display on stderr. A single source argument lists entries instead of copying them.</p>

<p>Use the options you already know from rsync. Native transfers require xsync on both machines. Missing remote support and unsupported options can delegate to a real rsync from PATH; <code>--no-fallback</code> requests native-only execution.</p>



## EXAMPLES {#examples}



<div class="example-caption">Copy a directory’s contents</div>

```sh
xs -aP src/ dst/
```



<div class="example-caption">Push over SSH</div>

```sh
xs -azP src/ user@host:/backup/src/
```



<div class="example-caption">Pull over SSH</div>

```sh
xs -azP user@host:/data/ data/
```



<div class="example-caption">Preview a mirror before executing</div>

```sh
xs -ani --delete src/ dst/
```

<p>The slash on <code>src/</code> means copy its contents. <code>-P</code> enables partial retention and progress. <code>-n</code> previews changes without writing.</p>



## OPTIONS {#options}

<p>Archive mode, <code>-a</code>, means <code>-rlptgoD</code>. Add <code>-H</code>, <code>-A</code>, or <code>-X</code> when you need hard links, ACLs, or extended attributes. Use <code>-j N</code> to choose worker threads.</p>

<p>See the <a href="options.html">complete option reference</a>, generated from the executable’s actual <code>--help</code>.</p>



## SEE ALSO {#see-also}

<div class="manual-links"><a href="getting-started.html">Getting started <span>↗</span></a><a href="transfers.html">Transfers &amp; path semantics <span>↗</span></a><a href="progress.html">Progress &amp; output <span>↗</span></a><a href="compatibility.html">Compatibility &amp; boundaries <span>↗</span></a></div>

