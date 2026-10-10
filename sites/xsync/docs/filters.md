---
title: "xs-filter(1)"
description: "Select files and preview a mirror with explicit deletion behavior."
manual: "xs-filter(1)"
manualName: "Filters & mirroring"
sectionNumber: "1"
---

# xs-filter(1)

<div class="manual-deck"><strong>Filters &amp; mirroring</strong><p>Select files and preview a mirror with explicit deletion behavior.</p></div>

## DESCRIPTION {#description}

<p>Filters use first-match ordering. Include/exclude rules normally affect both the source list and deletion protection. Use quoted patterns so your shell does not expand them first.</p>



## EXCLUDE AND INCLUDE {#excludes}



<div class="example-caption">Exclude generated and repository internals</div>

```sh
xs -aP --exclude='node_modules/' --exclude='.git/' project/ backup/
```



<div class="example-caption">Select text files while keeping directory traversal</div>

```sh
xs -aP --include='*/' --include='*.txt' --exclude='*' src/ dst/
```

<p>The directory include comes first so xsync can descend into directories that contain matching files. <code>-m</code> prunes empty directory chains from the filtered source list.</p>



## PREVIEW A MIRROR {#mirror}



<div class="example-caption">Dry run — no writes or deletions</div>

```sh
xs -ani --delete src/ dst/
```

<p>Inspect the itemized plan and the <code>would transfer …, delete …</code> summary. When the plan matches your intent, execute the same source and destination with <code>-n</code> removed.</p>



<div class="example-caption">Execute with an explicit deletion limit</div>

```sh
xs -aiP --delete --max-delete=100 src/ dst/
```

<aside class="manual-note"><span>DELETION</span><p><code>--delete</code> removes destination entries absent from the selected source tree. Source I/O errors suppress deletion unless <code>--ignore-errors</code> is explicitly requested. Exceeding <code>--max-delete</code> exits with code 25.</p></aside>

## SOURCE AND RECEIVER RULES {#sides}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Rule</th><th scope="col">Applies to</th></tr></thead><tbody><tr><td><code>H / S</code></td><td>Hide/show entries in the source list</td></tr><tr><td><code>P / R</code></td><td>Protect/risk entries during destination deletion</td></tr><tr><td><code>+ / −</code></td><td>Include/exclude; normally both sides</td></tr></tbody></table></div>

<div class="example-caption">Protect a receiver-only directory</div>

```sh
xs -aP --delete --filter='P local-notes/' src/ dst/
```

<p><code>--delete-excluded</code> makes unqualified include/exclude rules sender-only and allows excluded destination entries to be deleted. Explicit receiver protection still applies.</p>



## MERGE FILES {#merge}



<div class="example-caption">Load per-directory .rsync-filter files</div>

```sh
xs -aP -F src/ dst/
```



<div class="example-caption">Exclude filter files and defer deletion</div>

```sh
xs -aP -FF --delete-after src/ dst/
```

<p>A second <code>-F</code> excludes the merge files themselves. <code>--delete-after</code> reloads receiver rules from the updated tree after transfers finish, so newly transferred protection rules affect that deletion pass.</p>



## FILE LISTS {#file-lists}



<div class="example-caption">Copy selected directory trees recursively</div>

```sh
xs -arP --files-from=selected.txt src/ dst/
```

<p>Each list entry is relative to the source root. Leading slashes refer to that root; <code>..</code> cannot escape it. Use <code>-0</code>/<code>--from0</code> for filenames or patterns containing newlines.</p>



