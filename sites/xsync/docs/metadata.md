---
title: "xs-metadata(1)"
description: "Choose the attributes you preserve and understand platform-specific behavior."
manual: "xs-metadata(1)"
manualName: "Metadata & filesystems"
sectionNumber: "1"
---

# xs-metadata(1)

<div class="manual-deck"><strong>Metadata &amp; filesystems</strong><p>Choose the attributes you preserve and understand platform-specific behavior.</p></div>

## ARCHIVE MODE {#archive}

<p><code>-a</code> means <code>-rlptgoD</code>: recurse, preserve symlinks, permissions, modification times, groups, owners, devices, and special files. Ownership and special-node operations require the appropriate privileges.</p>

<aside class="manual-note"><span>NOTE</span><p>Archive mode does not imply hard links, ACLs, extended attributes, access times, creation times, or BSD file flags.</p></aside>

## HARD LINKS, ACLS, AND XATTRS {#extended}



<div class="example-caption">Preserve hard links, ACLs, and extended attributes</div>

```sh
xs -aHAXP src/ dst/
```

<p><code>-H</code> preserves selected hard-link groups. <code>-X</code> copies supported extended attributes; <code>-XX</code> also selects rsync-internal attributes. <code>-A</code> preserves ACLs and implies permissions.</p>

<p>Native remote ACL transfers require matching ACL styles. macOS ↔ Linux ACL requests delegate or fail before destination writes; fallback does not guarantee a cross-platform ACL conversion.</p>



## PERMISSION AND OWNER OVERRIDES {#permissions}



<div class="example-caption">Set incoming directory and file modes</div>

```sh
xs -aP --chmod='D755,F644' src/ dst/
```



<div class="example-caption">Set incoming owner and group</div>

```sh
xs -aP --chown=backup:backup src/ dst/
```

<p>Names in <code>--chown</code> resolve on the destination host. Overrides do not bypass filesystem privileges. <code>--chmod</code> modifies incoming modes; ordinary preservation rules still determine whether existing modes change.</p>

<p><code>--executability</code> preserves executable status when permissions are not being preserved. Apple’s system rsync uses <code>-E</code> for different semantics; use the long name when fallback must be unambiguous.</p>



## TIMES AND FILE FLAGS {#times}

<div class="manual-table-wrap"><table><thead><tr><th scope="col">Option</th><th scope="col">Native behavior</th></tr></thead><tbody><tr><td><code>-U</code></td><td>Preserve file and special-inode access times</td></tr><tr><td><code>-UU</code></td><td>Also request open-noatime where supported</td></tr><tr><td><code>-N</code></td><td>Preserve creation times on macOS</td></tr><tr><td><code>--fileflags</code></td><td>Preserve BSD file flags on macOS</td></tr><tr><td><code>-O / -J</code></td><td>Omit directory / symlink time writes</td></tr></tbody></table></div><p>Linux creation-time and native BSD-flag preservation are unsupported. Existing immutable destinations keep their protection; a failed replacement reports an error.</p>



## APFS CLONES {#clones}



<div class="example-caption">Force ordinary file data copies</div>

```sh
xs -aP --no-clone src/ dst/
```

<p>Eligible local copies on the same APFS volume use copy-on-write clones. Clones are independent files that share storage until modified. They can carry a metadata superset, including xattrs, ACLs, and access/creation times, even without corresponding preservation flags. Use <code>--no-clone</code> when that difference matters.</p>



## SPARSE AND SPECIAL FILES {#sparse}



<div class="example-caption">Create holes for zero-filled file regions</div>

```sh
xs -aSP image-tree/ backup/
```

<p><code>-S</code> disables cloning and creates sparse output on supported filesystems, including local, push, pull, delta, resumed, and in-place writes. If hole refinement is unavailable, bytes remain correct but disk allocation may be larger.</p>

<p>On macOS, dataless files bypass cloning and ordinary reads can request cloud hydration. Unix sockets are copied as inactive nodes. Some socket metadata operations remain unsupported; see <a href="compatibility.html">compatibility</a>.</p>



