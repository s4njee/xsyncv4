---
title: "xs-snapshot(1)"
description: "Resume verified partial data, reuse unchanged snapshot files, and control writes."
manual: "xs-snapshot(1)"
manualName: "Resume & snapshots"
sectionNumber: "1"
---

# xs-snapshot(1)

<div class="manual-deck"><strong>Resume &amp; snapshots</strong><p>Resume verified partial data, reuse unchanged snapshot files, and control writes.</p></div>

## PARTIAL TRANSFERS {#resume}



<div class="example-caption">Retain partial data and show progress</div>

```sh
xs -aP src/ dst/
```

<p>With <code>--partial</code> or <code>-P</code>, xsync verifies an existing destination prefix on both sides before reusing it. A matching prefix avoids sending the same bytes again; a mismatch sends the file in full. Retained interrupted output contains its completed contiguous prefix.</p>

<aside class="manual-note"><span>NOTE</span><p>Small files up to 512 KiB use the whole-file path. A protocol-3 peer has no verified-prefix resume feature and transfers the file in full.</p></aside>

## DELTA AND WHOLE-FILE TRANSFERS {#delta}



<div class="example-caption">Allow verified reuse</div>

```sh
xs -aP --no-whole-file src/ dst/
```



<div class="example-caption">Disable resume and block matching</div>

```sh
xs -aP --whole-file src/ dst/
```

<p>Large changed local and remote files can reuse verified blocks from a readable existing destination. Eligible APFS clones remain preferred for local copies. <code>-W</code> disables resume and delta block matching.</p>



## SNAPSHOT REUSE {#link-dest}



<div class="example-caption">Reuse a previous snapshot</div>

```sh
xs -aP --link-dest=../previous/ src/ snapshots/current/
```

<p>Relative <code>--link-dest</code> paths start at the destination directory. In this example, the basis is <code>snapshots/previous/</code>. Up to 20 previous snapshot directories may be supplied.</p>

<p>Unchanged files with matching requested metadata become hard links. Changed files, different requested metadata, or cross-device links create independent copies. A previous snapshot may also supply a read-only delta basis.</p>



<div class="example-caption">A dated snapshot that hard-links unchanged files</div>

```sh
xs -ai --link-dest=../2026-10-09 src/ snapshots/2026-10-10/
stat -c "%h links  %n" snapshots/2026-10-10/notes.txt snapshots/2026-10-10/docs/guide.md
```

<div class="captured-doc-output example-output" v-pre><span class="micro">ACTUAL OUTPUT · EXIT 0</span><pre><code>created directory snapshots/2026-10-10&#10;&gt;f.st...... notes.txt&#10;1 links  snapshots/2026-10-10/notes.txt&#10;2 links  snapshots/2026-10-10/docs/guide.md</code></pre></div>



## SHARED FILES {#shared-files}

<aside class="manual-note"><span>SNAPSHOTS</span><p>Hard-linked snapshots share the same inode. Later in-place writes or metadata changes to an already shared destination can affect other links. Create a new snapshot directory and keep old snapshots read-only by workflow.</p></aside>

## ATOMIC AND IN-PLACE OUTPUT {#atomic}

<p>New byte-copied files are atomic by default: xsync writes a temporary name and publishes it by rename after verification. <code>--no-atomic</code> writes new files directly; <code>--inplace</code> explicitly writes destination files in place.</p>



<div class="example-caption">State the default atomic policy explicitly</div>

```sh
xs -aP --atomic src/ dst/
```

<p>Direct writing changes interruption behavior and can leave incomplete files under final names. Atomic staging and retained partials also need destination disk space.</p>



