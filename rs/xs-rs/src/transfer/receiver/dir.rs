//! Directory listings on the receiver: decode a DIR frame, compare its entries
//! with the destination, create what needs no data and ask for the rest.

use std::collections::{HashMap, HashSet};
use std::ffi::OsStr;
use std::fs;
use std::io;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::Ordering;
use std::sync::Arc;

use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, Frame};

use crate::acls;
use crate::delta;
use crate::ffi;
use crate::idmap;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG,
};
use crate::resume;
use crate::scan;
use crate::xattr;

use crate::transfer::file::{destination_listing, make_dir, remove_any, set_dir_working_mode_with, DestDir, Stat};
use crate::transfer::hardlink::{hardlink_member, HardLinks};
use crate::transfer::event::{directory_event, metadata_code, taken_event};
use super::Receiving;

/// A DIR frame as the reader decodes it, in wire order, so xattr values and id maps apply
/// as they arrived; a worker does the rest (`Receiver::gen`).
pub(super) struct ParsedDir {
    pub(super) id: u32,
    pub(super) parent_plus1: u32,
    pub(super) pidx: u32,
    pub(super) flags: u8,
    pub(super) rel: Vec<u8>,
    pub(super) attrs: Attrs,
    pub(super) attr_source: Vec<u8>,
    pub(super) entries: Vec<EntryMeta>,
}

/// Directories whose generator has run, and directories waiting for their parent's.
#[derive(Default)]
pub(super) struct DirTable {
    pub(super) dirs: Vec<Option<RecvDir>>,
    pub(super) waiting: HashMap<u32, Vec<ParsedDir>>,
}

pub(super) struct FinalDir {
    pub(super) path: PathBuf,
    pub(super) attrs: Attrs,
    pub(super) apply: bool,
    /// What already matches and needs no syscall in the final pass (`mode_ok`, `time_ok`, fs.cpp).
    pub(super) mode_ok: bool,
    pub(super) time_ok: bool,
    pub(super) owner_ok: bool,
}

struct FileRequests {
    exact: HashSet<Vec<u8>>,
    parents: HashSet<Vec<u8>>,
    roots: HashSet<Vec<u8>>,
    recursive: bool,
}

impl FileRequests {
    fn new(opts: &Options) -> Self {
        let mut exact = HashSet::new();
        let mut parents = HashSet::new();
        let mut roots = HashSet::new();
        for name in &opts.file_names {
            let mut name = scan::clean_list_name(name);
            if opts.relative {
                if let Some(at) = name.windows(3).position(|w| w == b"/./") {
                    name.drain(..at + 3);
                }
            } else if let Some(at) = name.iter().rposition(|&b| b == b'/') {
                name.drain(..at + 1);
            }
            let mut path = Vec::new();
            for part in name.split(|&b| b == b'/') {
                if !part.is_empty() && part != b"." {
                    path = scan::join_rel(&path, part);
                }
            }
            if !path.is_empty() {
                exact.insert(path.clone());
            }
            if opts.recursive || opts.dir_requested {
                roots.insert(path.clone());
            }
            if opts.relative {
                let mut parent = path;
                while let Some(at) = parent.iter().rposition(|&b| b == b'/') {
                    parent.truncate(at);
                    parents.insert(parent.clone());
                }
            }
        }
        Self { exact, parents, roots, recursive: opts.recursive }
    }

    fn permits(&self, path: &[u8], directory: bool) -> bool {
        if path.is_empty() || path == b"." || self.exact.contains(path) || (directory && self.parents.contains(path)) {
            return true;
        }
        let parent = path.iter().rposition(|&b| b == b'/').map(|at| &path[..at]).unwrap_or(&[]);
        if self.roots.contains(parent) {
            return true;
        }
        if self.recursive {
            let mut parent = parent;
            while !parent.is_empty() {
                parent = parent.iter().rposition(|&b| b == b'/').map(|at| &parent[..at]).unwrap_or(&[]);
                if self.roots.contains(parent) {
                    return true;
                }
            }
        }
        false
    }
}

/// A directory's metadata only needs writing back when one of the attributes
/// the transfer preserves differs. An unchanged directory costs no syscalls.
fn dir_attrs_differ(opts: &Options, before: &Stat, attrs: &Attrs) -> bool {
    (opts.times && before.mtime() != attrs.mtime)
        || (opts.perms && before.mode() & 0o7777 != attrs.mode & 0o7777)
        || (opts.owner && before.uid() != attrs.uid)
        || (opts.group && before.gid() != attrs.gid)
}

/// Change ownership only when a target id differs from what the entry already
/// has, as `tweak_attrs` does; a matching lchown still dirties the inode.
fn chown_changed(path: &Path, opts: &Options, attrs: &Attrs, nofollow: bool, before: Option<&Stat>) {
    let id_differs = match before {
        Some(metadata) => {
            (opts.owner && metadata.uid() != attrs.uid) || (opts.group && metadata.gid() != attrs.gid)
        }
        None => true,
    };
    if !id_differs {
        return;
    }
    let (uid, gid) = idmap::targets(opts, attrs);
    let needed = match before {
        Some(metadata) => {
            uid.is_some_and(|id| metadata.uid() != id) || gid.is_some_and(|id| metadata.gid() != id)
        }
        None => uid.is_some() || gid.is_some(),
    };
    if needed {
        idmap::chown_path(path, opts, attrs, nofollow);
    }
}

pub(super) struct RecvDir {
    pub(super) rel: Vec<u8>,
    pub(super) dest: PathBuf,
    pub(super) entries: Vec<EntryMeta>,
    pub(super) rename_to: Option<Vec<u8>>,
    pub(super) need: HashSet<u32>,
    pub(super) existing: Vec<Option<Stat>>,
    pub(super) dir_created: Vec<bool>,
    pub(super) prefixes: HashMap<u32, ResumePrefix>,
    pub(super) delta_candidates: HashSet<u32>,
    pub(super) delta_requested: HashSet<u32>,
    pub(super) bases: HashMap<u32, Arc<delta::DeltaBasis>>,
    /// The directory, open while files it needs are still to come.
    pub(super) out: Option<Arc<DestDir>>,
}

impl RecvDir {
    /// A needed entry has arrived (or failed): once none is left, let the directory go.
    pub(super) fn received(&mut self, idx: u32) {
        self.need.remove(&idx);
        if self.need.is_empty() {
            self.out = None;
        }
    }
}

/// Decode a DIR frame on the reader: its xattr values and id maps apply in wire order.
pub(super) fn parse_dir(
    opts: &Options,
    features: u64,
    frame: &Frame,
    streams: &mut xattr::Incoming,
    ids: &idmap::Receiver,
    seen: &mut Vec<bool>,
) -> io::Result<ParsedDir> {
    let mut header = Decoder::new(&frame.payload);
    let id =
        u32::try_from(header.var().map_err(decode_err)?).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DIR id"))?;
    let parent_plus1 = u32::try_from(header.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DIR parent"))?;
    let pidx = u32::try_from(header.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DIR index"))?;
    let flags = header.byte().map_err(decode_err)?;
    if id > (1 << 28) || ((parent_plus1 == 0) != (id == 0)) {
        return bad("protocol error: bad DIR header");
    }
    if seen.len() <= id as usize {
        seen.resize(id as usize + 1, false);
    }
    if seen[id as usize] {
        return bad("protocol error: duplicate directory");
    }
    if parent_plus1 != 0 && !seen.get(parent_plus1 as usize - 1).copied().unwrap_or(false) {
        return bad("protocol error: DIR frame before its parent");
    }
    seen[id as usize] = true;
    let body = protocol::unpack_body(header.rest(), flags & protocol::DF_ZSTD != 0, features)?;
    let mut d = Decoder::new(&body);
    let rel = d.str().map_err(decode_err)?.to_vec();
    let mut attrs = protocol::get_dir_attrs(&mut d, features)?;
    let mut attr_source = Vec::new();
    if features & feature::DIR_OUTPUT != 0 {
        attrs.size = i64::try_from(d.var().map_err(decode_err)?).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: negative directory size"))?;
        attr_source = d.str().map_err(decode_err)?.to_vec();
    }
    if features & feature::XATTRS != 0 {
        attrs.xattrs = xattr::get_xattrs(&mut d, features, streams)?;
    }
    if features & acls::NATIVE_ACL != 0 {
        attrs.acls = acls::get_acls(&mut d, T_DIR, opts)?;
    }
    if features & feature::DIR_CHILDREN != 0 {
        let _children = d.var().map_err(decode_err)?;
    }
    let count = usize::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DIR entry count"))?;
    if count > 1 << 28 {
        return bad("protocol error: bad DIR frame");
    }
    let mut entries = Vec::with_capacity(count);
    for _ in 0..count {
        let mut entry = protocol::get_entry(&mut d, opts, features)?;
        if features & feature::XATTRS != 0 {
            entry.attrs.xattrs = xattr::get_xattrs(&mut d, features, streams)?;
        }
        if features & acls::NATIVE_ACL != 0 {
            entry.attrs.acls = acls::get_acls(&mut d, entry.kind, opts)?;
        }
        entries.push(entry);
    }
    if !d.is_empty() {
        return bad("protocol error: trailing DIR payload");
    }
    if opts.files_from_set && !opts.am_server {
        let requests = FileRequests::new(opts);
        for entry in &entries {
            let path = scan::join_rel(&rel, &entry.name);
            if !requests.permits(&path, entry.kind == T_DIR) {
                return bad(format!(
                    "rejecting unrequested file-list name: {}",
                    String::from_utf8_lossy(&path)
                ));
            }
        }
    }
    ids.apply(&mut attrs, opts);
    for entry in &mut entries {
        ids.apply(&mut entry.attrs, opts);
    }
    Ok(ParsedDir { id, parent_plus1, pidx, flags, rel, attrs, attr_source, entries })
}

/// `Receiver::gen` for one directory, on a worker: find or make it, compare its listing
/// with the destination's, create what needs no data, and ask for the rest with a NEED.
/// Its parent's generator has run.
pub(super) fn generate(r: &Receiving, dir: ParsedDir) -> io::Result<()> {
    let (opts, features, dest_arg) = (r.opts, r.features, r.dest);
    let ParsedDir { id, parent_plus1, pidx, flags, rel, attrs, attr_source, entries } = dir;
    let mut working_changed = false;
    let (dir_path, rename_to, apply_attrs, before, created) = if parent_plus1 == 0 {
        if !rel.is_empty() || id != 0 {
            return bad("protocol error: nonempty root path");
        }
        let trailing = dest_arg.as_os_str().as_bytes().ends_with(b"/");
        let exists = fs::metadata(dest_arg).ok();
        let is_dir = exists.as_ref().map(|m| m.is_dir()).unwrap_or(false);
        if flags & protocol::DF_SINGLE != 0 && !trailing && !is_dir {
            let parent = dest_arg.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
            let name = dest_arg.file_name().map(|n| n.as_bytes().to_vec()).unwrap_or_default();
            if name.is_empty() {
                return bad("protocol error: bad single-file destination");
            }
            (parent.to_path_buf(), Some(name), false, None, false)
        } else {
            let created = if let Some(metadata) = &exists {
                if !metadata.is_dir() {
                    return bad("ERROR: destination must be a directory when copying more than 1 file");
                }
                false
            } else {
                fs::create_dir_all(dest_arg)?;
                r.created_dirs.fetch_add(1, Ordering::Relaxed);
                true
            };
            (dest_arg.to_path_buf(), None, flags & protocol::DF_ATTRS != 0, exists.as_ref().map(Stat::from), created)
        }
    } else {
        let (path, created, before, mode) = {
            let table = r.table.lock().unwrap();
            let parent = table
                .dirs
                .get((parent_plus1 - 1) as usize)
                .and_then(|d| d.as_ref())
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: DIR frame before its parent"))?;
            let entry = parent
                .entries
                .get(pidx as usize)
                .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad parent in DIR frame"))?;
            if entry.kind != T_DIR {
                return bad("protocol error: inconsistent directory path");
            }
            let expected = scan::join_rel(&parent.rel, &entry.name);
            if expected != rel {
                return bad("protocol error: inconsistent directory path");
            }
            let path = parent.dest.join(OsStr::from_bytes(&entry.name));
            let created = parent.dir_created.get(pidx as usize).copied().unwrap_or(false);
            // The parent's destination listing already carries this entry's metadata;
            // do not stat it again just to decide whether it needs work.
            let before = if created {
                None
            } else {
                parent.existing.get(pidx as usize).cloned().flatten().filter(|m| m.is_dir())
            };
            (path, created, before, entry.attrs.mode)
        };
        if let Some(metadata) = &before {
            working_changed = set_dir_working_mode_with(&path, metadata);
        } else if !created {
            remove_any(&path)?;
            if make_dir(&path, mode)? {
                r.created_dirs.fetch_add(1, Ordering::Relaxed);
            }
        }
        (path, None, true, before, created)
    };
    let mut dir_modified = created;
    if rename_to.is_none() {
        let source = if attr_source.is_empty() { dir_path.as_os_str().as_bytes() } else { &attr_source };
        if let Some(event) = directory_event(opts, &rel, source, &attrs, before.as_ref(), created) {
            r.emit(event)?;
        }
    }

    // A directory made just now is empty: nothing to list (`if (!w.created)`, fs.cpp).
    let listing = if created { Default::default() } else { destination_listing(&dir_path) };
    let mut need = Vec::new();
    let mut existing_entries = Vec::with_capacity(entries.len());
    let mut dir_created = vec![false; entries.len()];
    for (index, entry) in entries.iter().enumerate() {
        let name = rename_to.clone().unwrap_or_else(|| entry.name.clone());
        let target = dir_path.join(OsStr::from_bytes(&name));
        let before = listing.get(&name).cloned();
        let existing = before.as_ref();
        let event_path = scan::join_rel(&rel, &entry.name);
        let link_key = HardLinks::key(entry, features);
        if (opts.xattrs != 0 || opts.acls) && (!entry.attrs.xattrs.complete || !entry.attrs.acls.complete) {
            r.partial_failure.store(true, Ordering::Relaxed);
            existing_entries.push(before);
            continue;
        }
        match entry.kind {
            T_DIR => {
                let keep = existing.map(|m| m.is_dir()).unwrap_or(false);
                let made = if !keep {
                    if existing.is_some() {
                        remove_any(&target)?;
                    }
                    dir_modified = true;
                    let made = make_dir(&target, entry.attrs.mode)?;
                    if made {
                        r.created_dirs.fetch_add(1, Ordering::Relaxed);
                    }
                    made
                } else {
                    if let Some(metadata) = existing {
                        set_dir_working_mode_with(&target, metadata);
                    }
                    false
                };
                dir_created[index] = made;
            }
            T_REG => {
                let same = existing
                    .filter(|m| m.is_file())
                    .map(|m| !opts.ignore_times && m.len() as i64 == entry.size && m.mtime() == entry.attrs.mtime)
                    .unwrap_or(false);
                if same {
                    if let Some(metadata) = existing {
                        if opts.perms && metadata.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
                            let _ = fs::set_permissions(&target, fs::Permissions::from_mode(entry.attrs.mode & 0o7777));
                        }
                        if opts.times && metadata.mtime() != entry.attrs.mtime {
                            let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, false);
                        }
                        chown_changed(&target, opts, &entry.attrs, false, Some(metadata));
                    }
                    if opts.xattrs != 0 {
                        xattr::apply(&entry.attrs.xattrs, &target, T_REG, &opts.filters, opts)?;
                    }
                    if opts.acls {
                        acls::apply(&entry.attrs.acls, &target, T_REG, entry.attrs.mode, opts)?;
                    }
                    if let Some(key) = link_key.clone() {
                        r.hardlinks.lock().unwrap().register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                    }
                    if let Some(before) = existing {
                        if let Some(code) = metadata_code(opts, T_REG, before, entry) {
                            let event = taken_event(&code, &event_path, &entry.output_source, T_REG, entry.size, 0);
                            r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                        }
                    }
                } else {
                    dir_modified = true;
                    if let Some(m) = existing {
                        if !m.is_file() {
                            remove_any(&target)?;
                        }
                    }
                    let follow = match link_key.clone() {
                        Some(key) => {
                            let member = hardlink_member(entry, &event_path, &target, existing);
                            r.hardlinks.lock().unwrap().register_transfer(key, member, existing.is_none())
                        }
                        None => false,
                    };
                    if !follow {
                        need.push(index as u32);
                    }
                }
            }
            T_LNK => {
                let same = existing
                    .and_then(|m| if m.is_symlink() { fs::read_link(&target).ok() } else { None })
                    .map(|p| p.as_os_str().as_bytes() == entry.link.as_slice())
                    .unwrap_or(false);
                if let Some(key) = link_key.clone() {
                    r.hardlinks.lock().unwrap().register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if !same {
                    dir_modified = true;
                    if existing.is_some() {
                        remove_any(&target)?;
                    }
                    std::os::unix::fs::symlink(OsStr::from_bytes(&entry.link), &target)?;
                    r.created_links.fetch_add(1, Ordering::Relaxed);
                    let mut event =
                        taken_event(b"cL+++++++++", &event_path, &entry.output_source, T_LNK, entry.size, 0);
                    event.target = entry.link.clone();
                    r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_LNK, before, entry) {
                        let mut event = taken_event(&code, &event_path, &entry.output_source, T_LNK, entry.size, 0);
                        event.target = entry.link.clone();
                        r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                    }
                }
                if opts.times {
                    let need = match (same, existing) {
                        (true, Some(metadata)) => metadata.mtime() != entry.attrs.mtime,
                        _ => true,
                    };
                    if need {
                        let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, true);
                    }
                }
                chown_changed(&target, opts, &entry.attrs, true, if same { existing } else { None });
                if opts.xattrs != 0 {
                    xattr::apply(&entry.attrs.xattrs, &target, T_LNK, &opts.filters, opts)?;
                }
            }
            T_FIFO => {
                let same = existing.map(|m| m.is_fifo()).unwrap_or(false);
                if let Some(key) = link_key.clone() {
                    r.hardlinks.lock().unwrap().register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if !same {
                    dir_modified = true;
                    remove_any(&target)?;
                    ffi::make_fifo(&target, entry.attrs.mode)?;
                    let event = taken_event(b"cS+++++++++", &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                    r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_FIFO, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                        r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                    }
                }
                if opts.times {
                    let need = match (same, existing) {
                        (true, Some(metadata)) => metadata.mtime() != entry.attrs.mtime,
                        _ => true,
                    };
                    if need {
                        let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, false);
                    }
                }
                chown_changed(&target, opts, &entry.attrs, false, if same { existing } else { None });
                if opts.xattrs != 0 {
                    xattr::apply(&entry.attrs.xattrs, &target, T_FIFO, &opts.filters, opts)?;
                }
                if opts.acls {
                    acls::apply(&entry.attrs.acls, &target, T_FIFO, entry.attrs.mode, opts)?;
                }
            }
            T_CHR | T_BLK => {
                if let Some(key) = link_key.clone() {
                    r.hardlinks.lock().unwrap().register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, entry.kind, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, entry.kind, entry.size, 0);
                        r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
                    }
                }
                if opts.xattrs != 0 {
                    let _ = xattr::apply(&entry.attrs.xattrs, &target, entry.kind, &opts.filters, opts);
                }
                if opts.acls {
                    let _ = acls::apply(&entry.attrs.acls, &target, entry.kind, entry.attrs.mode, opts);
                }
            }
            _ => {}
        }
        existing_entries.push(before);
    }
    let apply_attrs = apply_attrs
        && (opts.xattrs != 0
            || opts.acls
            || dir_modified
            || working_changed
            || match &before {
                Some(metadata) => dir_attrs_differ(opts, metadata, &attrs),
                None => true,
            });
    if apply_attrs {
        let mode = attrs.mode & 0o7777;
        let (uid, gid) = idmap::targets(opts, &attrs);
        let (mode_ok, time_ok, owner_ok) = match &before {
            Some(metadata) => (
                !working_changed && metadata.mode() & 0o7777 == mode,
                !dir_modified && metadata.mtime() == attrs.mtime && metadata.mtime_nsec() == attrs.mtime_ns as i64,
                uid.is_none_or(|id| metadata.uid() == id) && gid.is_none_or(|id| metadata.gid() == id),
            ),
            // Made by make_dir with mode | 0700 under the umask; its times changed as it filled.
            None => (
                mode & 0o7000 == 0 && (mode | 0o700) & !ffi::current_umask() == mode,
                false,
                uid.is_none() && gid.is_none(),
            ),
        };
        r.finals.lock().unwrap().push(FinalDir {
            path: dir_path.clone(),
            attrs: attrs.clone(),
            apply: true,
            mode_ok,
            time_ok,
            owner_ok,
        });
    }
    let resume_enabled = opts.partial && features & feature::RESUME != 0;
    let delta_enabled = features & feature::DELTA != 0;
    let mut prefixes = HashMap::new();
    let mut delta_candidates = HashSet::new();
    let mut f = Encoder::new();
    f.var(id as u64).var(need.len() as u64);
    let mut previous = 0u32;
    for &index in &need {
        f.var((index - previous) as u64);
        previous = index;
        if resume_enabled {
            let entry = &entries[index as usize];
            let prefix = if entry.size > protocol::SMALL_MAX as i64 {
                let name = rename_to.as_deref().unwrap_or(&entry.name);
                resume::destination_prefix(&dir_path.join(OsStr::from_bytes(name)), entry.size)
            } else {
                ResumePrefix::default()
            };
            prefix.put(&mut f);
            if !prefix.is_empty() {
                prefixes.insert(index, prefix);
            }
        }
        if delta_enabled {
            let eligible = existing_entries[index as usize].as_ref().map(|m| m.is_file()).unwrap_or(false);
            f.byte(u8::from(eligible));
            if eligible {
                delta_candidates.insert(index);
            }
        }
    }
    // Known before its NEED goes out, since data for it may follow at once; then its
    // children may run.
    let need_set: HashSet<u32> = need.iter().copied().collect();
    let out = (!need_set.is_empty()).then(|| Arc::new(DestDir::open(&dir_path)));
    let children = {
        let mut table = r.table.lock().unwrap();
        if table.dirs.len() <= id as usize {
            table.dirs.resize_with(id as usize + 1, || None);
        }
        table.dirs[id as usize] = Some(RecvDir {
            out,
            rel,
            dest: dir_path,
            entries,
            rename_to,
            need: need_set,
            existing: existing_entries,
            dir_created,
            prefixes,
            delta_candidates,
            delta_requested: HashSet::new(),
            bases: HashMap::new(),
        });
        table.waiting.remove(&id).unwrap_or_default()
    };
    r.tx.send(frame_type::NEED, f.bytes)?;
    for child in children {
        r.queue_dir(child);
    }
    Ok(())
}
