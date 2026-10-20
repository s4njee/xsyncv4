//! Walking the source: sorted listings, `statx`-equivalent metadata through
//! `symlink_metadata`, and the root rules of `build_root` in local.cpp.

use std::ffi::OsString;
use std::fs;
use std::io;
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileTypeExt, MetadataExt};
use std::path::{Path, PathBuf};

use crate::protocol::{self, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG, T_SOCK};

#[derive(Clone, Debug)]
pub struct SourceEntry {
    pub meta: EntryMeta,
    pub path: PathBuf,
}

#[derive(Clone, Debug)]
pub struct SourceRoot {
    pub attrs: Option<Attrs>,
    pub entries: Vec<SourceEntry>,
    pub base: PathBuf,
    pub single: bool,
}

pub fn attrs_from(m: &fs::Metadata) -> Attrs {
    Attrs {
        mode: m.mode() & 0o7777,
        uid: m.uid(),
        gid: m.gid(),
        mtime: m.mtime(),
        mtime_ns: m.mtime_nsec().clamp(0, 999_999_999) as u32,
        atime: m.atime(),
    }
}

fn kind_of(m: &fs::Metadata) -> u8 {
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
    let m = stat_for(path, opts)?;
    let kind = kind_of(&m);
    let link = if kind == T_LNK { fs::read_link(path)?.into_os_string().into_vec() } else { Vec::new() };
    let mut meta = EntryMeta {
        name,
        kind,
        attrs: attrs_from(&m),
        size: m.len() as i64,
        link,
        rdev: if kind == T_CHR || kind == T_BLK { m.rdev() as u32 } else { 0 },
    };
    if kind == T_DIR {
        meta.size = 0;
    }
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
    Ok(SourceRoot { attrs, entries, base, single })
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
