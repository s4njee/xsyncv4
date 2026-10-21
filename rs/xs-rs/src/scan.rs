//! Walking the source: sorted listings, `statx`-equivalent metadata through
//! `symlink_metadata`, and the root rules of `build_root` in local.cpp.

use std::collections::BTreeMap;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io;
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::path::{Path, PathBuf};

use crate::filter::FilterList;
use crate::protocol::{self, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG, T_SOCK};

#[derive(Clone, Debug)]
pub struct SourceEntry {
    pub meta: EntryMeta,
    pub path: PathBuf,
}

#[derive(Clone, Debug, Default)]
pub struct SelectedDir {
    pub attrs: Option<Attrs>,
    pub entries: Vec<SourceEntry>,
}

#[derive(Clone, Debug, Default)]
pub struct Selection {
    pub dirs: BTreeMap<Vec<u8>, SelectedDir>,
    pub root_attrs: Option<Attrs>,
    pub root_base: PathBuf,
}

#[derive(Clone, Debug)]
pub struct SourceRoot {
    pub attrs: Option<Attrs>,
    pub entries: Vec<SourceEntry>,
    pub base: PathBuf,
    pub single: bool,
    pub selection: Option<Selection>,
}

pub fn attrs_from(m: &fs::Metadata) -> Attrs {
    Attrs {
        mode: m.mode() & 0o7777,
        uid: m.uid(),
        gid: m.gid(),
        mtime: m.mtime(),
        mtime_ns: m.mtime_nsec().clamp(0, 999_999_999) as u32,
        atime: m.atime(),
        size: m.len() as i64,
        hdev: m.dev(),
        ino: m.ino(),
        nlink: m.nlink(),
        ctime: m.ctime(),
        ctime_ns: m.ctime_nsec().clamp(0, 999_999_999) as u32,
        xattrs: crate::xattr::XattrSet::default(),
    }
}

pub(crate) fn kind_of(m: &fs::Metadata) -> u8 {
    let ft = m.file_type();
    if ft.is_file() {
        T_REG
    } else if ft.is_dir() {
        T_DIR
    } else if ft.is_symlink() {
        T_LNK
    } else if ft.is_fifo() {
        T_FIFO
    } else if ft.is_socket() {
        T_SOCK
    } else if ft.is_char_device() {
        T_CHR
    } else if ft.is_block_device() {
        T_BLK
    } else {
        protocol::T_NONE
    }
}

fn stat_for(path: &Path, opts: &Options) -> io::Result<fs::Metadata> {
    if opts.copy_links {
        fs::metadata(path)
    } else {
        fs::symlink_metadata(path)
    }
}

pub fn entry_for(path: &Path, name: Vec<u8>, opts: &Options) -> io::Result<SourceEntry> {
    entry_for_followed(path, name, opts, false)
}

pub fn entry_for_followed(path: &Path, name: Vec<u8>, opts: &Options, follow: bool) -> io::Result<SourceEntry> {
    let m = if follow || opts.copy_links { fs::metadata(path)? } else { fs::symlink_metadata(path)? };
    let kind = kind_of(&m);
    let link = if kind == T_LNK { fs::read_link(path)?.into_os_string().into_vec() } else { Vec::new() };
    let meta = EntryMeta {
        name,
        kind,
        attrs: attrs_from(&m),
        size: m.len() as i64,
        link,
        rdev: if kind == T_CHR || kind == T_BLK { m.rdev() as u32 } else { 0 },
        output_source: path.as_os_str().as_bytes().to_vec(),
        filter_source: path.as_os_str().as_bytes().to_vec(),
        selected: false,
    };
    Ok(SourceEntry { meta, path: path.to_path_buf() })
}

pub fn scan_dir(path: &Path, opts: &Options) -> io::Result<Vec<SourceEntry>> {
    let mut entries = Vec::new();
    for item in fs::read_dir(path)? {
        let item = match item {
            Ok(item) => item,
            Err(_) => continue,
        };
        let name = item.file_name().as_bytes().to_vec();
        if name.is_empty() || name == b"." || name == b".." {
            continue;
        }
        let child = path.join(item.file_name());
        let entry = match entry_for(&child, name, opts) {
            Ok(entry) => entry,
            Err(_) => continue,
        };
        let keep = match entry.meta.kind {
            T_LNK => opts.links || opts.copy_links,
            T_FIFO | T_SOCK | T_CHR | T_BLK => opts.specials || opts.devices,
            _ => true,
        };
        if !keep {
            continue;
        }
        entries.push(entry);
    }
    entries.sort_by(|a, b| a.meta.name.cmp(&b.meta.name));
    Ok(entries)
}

fn has_trailing_slash(value: &OsString) -> bool {
    let bytes = value.as_bytes();
    bytes.is_empty() || bytes == b"." || bytes.ends_with(b"/") || bytes.ends_with(b"/.")
}

/// The top-level listing: directory arguments ending in `/` contribute their
/// contents and their own attributes; anything else contributes itself.
pub fn build_root(sources: &[OsString], opts: &Options) -> io::Result<SourceRoot> {
    let mut entries = Vec::new();
    let mut attrs = None;
    let mut base = PathBuf::from(".");
    let mut all_slash = true;
    for source in sources {
        let slash = has_trailing_slash(source);
        all_slash &= slash;
        let path = if source.is_empty() { PathBuf::from(".") } else { PathBuf::from(source) };
        let m = stat_for(&path, opts)?;
        if kind_of(&m) == T_DIR && slash {
            if attrs.is_none() {
                attrs = Some(attrs_from(&m));
                base = path.clone();
            }
            entries.extend(scan_dir(&path, opts)?);
        } else {
            let mut trimmed = path.as_os_str().as_bytes().to_vec();
            while trimmed.len() > 1 && trimmed.ends_with(b"/") {
                trimmed.pop();
            }
            let name = match trimmed.iter().rposition(|&b| b == b'/') {
                Some(0) => trimmed[1..].to_vec(),
                Some(at) => trimmed[at + 1..].to_vec(),
                None => trimmed.clone(),
            };
            if name.is_empty() || name == b".." {
                continue;
            }
            entries.push(entry_for(&path, name, opts)?);
        }
    }
    entries.sort_by(|a, b| a.meta.name.cmp(&b.meta.name));
    entries.dedup_by(|a, b| a.meta.name == b.meta.name);
    let single = sources.len() == 1 && !all_slash && entries.len() == 1 && entries[0].meta.kind != T_DIR;
    Ok(SourceRoot { attrs, entries, base, single, selection: None })
}

pub(crate) fn clean_list_name(text: &[u8]) -> Vec<u8> {
    let mut parts: Vec<&[u8]> = Vec::new();
    for part in text.split(|&b| b == b'/') {
        if part == b".." {
            parts.pop();
        } else if !part.is_empty() {
            parts.push(part);
        }
    }
    let mut result = Vec::new();
    for part in parts {
        result = join_rel(&result, part);
    }
    if result.is_empty() {
        result.push(b'.');
    }
    if text.ends_with(b"/") {
        result.push(b'/');
    }
    result
}

struct RelativePath {
    base: Vec<u8>,
    logical: Vec<u8>,
    physical: PathBuf,
    contents: bool,
    cut_prefix: bool,
}

impl RelativePath {
    fn new(argument: &[u8], source: Option<&Path>, relative: bool) -> io::Result<Self> {
        let contents = argument.is_empty() || argument == b"." || argument.ends_with(b"/") || argument.ends_with(b"/.");
        let mut text = if argument.is_empty() { b".".to_vec() } else { argument.to_vec() };
        let cut = if text.starts_with(b"./") {
            Some(0)
        } else {
            text.windows(3).position(|w| w == b"/./")
        };
        let cut_prefix = cut.is_some();
        let mut base;
        if let Some(at) = cut {
            base = if at == 0 { b".".to_vec() } else { text[..at].to_vec() };
            text.drain(..at + if at == 0 { 2 } else { 3 });
        } else {
            base = if text.starts_with(b"/") { b"/".to_vec() } else { b".".to_vec() };
        }
        let mut logical = Vec::new();
        for part in text.split(|&b| b == b'/') {
            if part == b".." {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    format!("found \"..\" dir in relative path: {}", String::from_utf8_lossy(argument)),
                ));
            }
            if !part.is_empty() && part != b"." {
                logical = join_rel(&logical, part);
            }
        }
        if let Some(source) = source {
            if base == b"/" {
                base = source.as_os_str().as_bytes().to_vec();
            } else {
                base = join_rel(source.as_os_str().as_bytes(), &base);
            }
            if !relative && !logical.is_empty() {
                if contents {
                    base = if cut_prefix { join_rel(&join_rel(&base, b"."), &logical) } else { join_rel(&base, &logical) };
                    logical.clear();
                } else if let Some(at) = logical.iter().rposition(|&b| b == b'/') {
                    base = if cut_prefix { join_rel(&join_rel(&base, b"."), &logical[..at]) } else { join_rel(&base, &logical[..at]) };
                    logical = logical[at + 1..].to_vec();
                }
            }
        }
        let physical = if cut_prefix { join_rel(&join_rel(&base, b"."), &logical) } else { join_rel(&base, &logical) };
        Ok(Self {
            base,
            logical,
            physical: PathBuf::from(OsString::from_vec(physical)),
            contents,
            cut_prefix,
        })
    }
}

fn insert_entry(selection: &mut Selection, parent: &[u8], entry: SourceEntry) {
    let entries = &mut selection.dirs.entry(parent.to_vec()).or_default().entries;
    if let Some(existing) = entries.iter_mut().find(|existing| existing.meta.name == entry.meta.name) {
        if existing.meta.kind != T_DIR && entry.meta.kind == T_DIR {
            *existing = entry;
        }
        return;
    }
    entries.push(entry);
}

#[allow(clippy::too_many_arguments)]
fn scan_selected(
    selection: &mut Selection,
    logical: &[u8],
    physical: &Path,
    attrs: &Attrs,
    opts: &Options,
    filters: &FilterList,
    recursive: bool,
    visited: &mut std::collections::HashSet<Vec<u8>>,
) -> io::Result<()> {
    if !visited.insert(logical.to_vec()) {
        return Ok(());
    }
    let context = filters.in_directory(physical, false);
    let mut entries = scan_dir_filtered(physical, opts, &context, logical)?;
    for entry in &mut entries {
        if entry.meta.kind == T_DIR {
            entry.meta.selected = true;
        }
    }
    for entry in &entries {
        if entry.meta.kind == T_DIR {
            let slot = selection.dirs.entry(join_rel(logical, &entry.meta.name)).or_default();
            if slot.attrs.is_none() {
                slot.attrs = Some(entry.meta.attrs.clone());
            }
        }
    }
    let dir = selection.dirs.entry(logical.to_vec()).or_default();
    dir.attrs = Some(attrs.clone());
    dir.entries.extend(entries);
    if recursive {
        let children: Vec<SourceEntry> = selection.dirs[logical]
            .entries
            .iter()
            .filter(|entry| entry.meta.kind == T_DIR)
            .cloned()
            .collect();
        for child in children {
            let child_rel = join_rel(logical, &child.meta.name);
            scan_selected(selection, &child_rel, &child.path, &child.meta.attrs, opts, &context, true, visited)?;
        }
    }
    Ok(())
}

pub fn scan_dir_filtered(path: &Path, opts: &Options, filters: &FilterList, rel: &[u8]) -> io::Result<Vec<SourceEntry>> {
    let mut entries = scan_dir(path, opts)?;
    entries.retain(|entry| {
        let child_rel = join_rel(rel, &entry.meta.name);
        !filters.excluded(&child_rel, entry.meta.kind == T_DIR)
    });
    Ok(entries)
}

pub fn build_selection(sources: &[OsString], names: Option<&[Vec<u8>]>, opts: &Options, filters: &FilterList) -> io::Result<SourceRoot> {
    let mut selection = Selection { root_base: PathBuf::from("."), ..Selection::default() };
    selection.dirs.insert(Vec::new(), SelectedDir::default());
    let arguments: Vec<Vec<u8>> = match names {
        Some(names) => names.iter().map(|name| clean_list_name(name)).collect(),
        None => sources.iter().map(|source| source.as_bytes().to_vec()).collect(),
    };
    let source = sources.first().map(PathBuf::from);
    let mut any_contents = false;
    let mut visited = std::collections::HashSet::new();
    for argument in &arguments {
        let relative = opts.relative;
        let path = RelativePath::new(argument, if names.is_some() { source.as_deref() } else { None }, relative)?;
        let follow = opts.copy_links || path.contents;
        let metadata = match if follow { fs::metadata(&path.physical) } else { fs::symlink_metadata(&path.physical) } {
            Ok(metadata) => metadata,
            Err(_) => continue,
        };
        let kind = kind_of(&metadata);
        if kind == T_DIR && !opts.recursive && !opts.dir_requested {
            continue;
        }
        if !path.logical.is_empty() && filters.excluded(&path.logical, kind == T_DIR) {
            continue;
        }
        let mut logical = Vec::new();
        let mut physical = if path.cut_prefix {
            PathBuf::from(OsString::from_vec(join_rel(&path.base, b".")))
        } else {
            PathBuf::from(OsString::from_vec(path.base.clone()))
        };
        let mut start = 0;
        while let Some(offset) = path.logical[start..].iter().position(|&b| b == b'/') {
            let end = start + offset;
            let name = path.logical[start..end].to_vec();
            physical = physical.join(OsStr::from_bytes(&name));
            let Ok(implied_meta) = fs::metadata(&physical) else { break };
            if kind_of(&implied_meta) != T_DIR {
                break;
            }
            let implied = SourceEntry {
                meta: EntryMeta {
                    name: name.clone(),
                    kind: T_DIR,
                    attrs: attrs_from(&implied_meta),
                    size: implied_meta.len() as i64,
                    link: Vec::new(),
                    rdev: 0,
                    output_source: physical.as_os_str().as_bytes().to_vec(),
                    filter_source: physical.as_os_str().as_bytes().to_vec(),
                    selected: true,
                },
                path: physical.clone(),
            };
            insert_entry(&mut selection, &logical, implied);
            logical = join_rel(&logical, &name);
            let slot = selection.dirs.entry(logical.clone()).or_default();
            if slot.attrs.is_none() {
                slot.attrs = Some(attrs_from(&implied_meta));
            }
            start = end + 1;
        }
        let name = path.logical[start..].to_vec();
        if name.is_empty() {
            let attrs = attrs_from(&metadata);
            selection.root_attrs = Some(attrs.clone());
            selection.root_base = PathBuf::from(OsString::from_vec(join_rel(path.physical.as_os_str().as_bytes(), b".")));
            any_contents = true;
            scan_selected(&mut selection, b"", &path.physical, &attrs, opts, filters, opts.recursive, &mut visited)?;
            continue;
        }
        let mut entry = entry_for_followed(&path.physical, name.clone(), opts, path.contents)?;
        if entry.meta.kind == T_DIR {
            entry.meta.selected = true;
        }
        let child_rel = join_rel(&logical, &name);
        if entry.meta.kind == T_DIR {
            selection.dirs.entry(child_rel.clone()).or_default().attrs = Some(entry.meta.attrs.clone());
            if opts.recursive || path.contents {
                scan_selected(
                    &mut selection,
                    &child_rel,
                    &entry.path,
                    &entry.meta.attrs,
                    opts,
                    filters,
                    opts.recursive,
                    &mut visited,
                )?;
            }
        }
        let context = if names.is_some() { FilterList::default() } else { filters.in_directory(&path.physical, false) };
        if context.excluded(&entry.meta.name, entry.meta.kind == T_DIR) {
            continue;
        }
        insert_entry(&mut selection, &logical, entry);
        any_contents |= path.contents;
    }
    for dir in selection.dirs.values_mut() {
        dir.entries.sort_by(|a, b| a.meta.name.cmp(&b.meta.name));
    }
    let root = selection.dirs.get(&Vec::new()).cloned().unwrap_or_default();
    let single = sources.len() == 1
        && names.is_none()
        && !any_contents
        && root.entries.len() == 1
        && root.entries[0].meta.kind != T_DIR;
    Ok(SourceRoot {
        attrs: selection.root_attrs.clone(),
        entries: root.entries,
        base: selection.root_base.clone(),
        single,
        selection: Some(selection),
    })
}

pub fn join_rel(parent: &[u8], name: &[u8]) -> Vec<u8> {
    if parent.is_empty() {
        return name.to_vec();
    }
    let mut out = Vec::with_capacity(parent.len() + 1 + name.len());
    out.extend_from_slice(parent);
    out.push(b'/');
    out.extend_from_slice(name);
    out
}
