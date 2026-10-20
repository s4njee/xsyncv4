//! The receiver engine: compare DIR listings, request missing entries with NEED,
//! write DATA records, then apply deferred directory metadata and send DONE.

use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet};
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileExt, FileTypeExt, MetadataExt, PermissionsExt};
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

use xs_wire::io_control::IoControl;
use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, Frame};

use crate::delta;
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG,
};
use crate::resume;
use crate::scan;

use crate::parallel::{WriteDone, WritePool};

use super::file::{
    add_range, contiguous, covered_from, create_temp, destination_listing, finish_infile, make_dir, remove_any,
    reserve_chunk, set_dir_working_mode_with, write_whole, InFile,
};
use super::hardlink::{finalize_hardlinks, hardlink_member, HardLinks};
use super::{
    directory_event, metadata_code, msg_code, progress_ack, report_event, send_fatal, taken_event, transferred_code,
    FrameOut,
};

struct FinalDir {
    path: PathBuf,
    attrs: Attrs,
    apply: bool,
}

struct FileRequests {
    exact: HashSet<Vec<u8>>,
    parents: HashSet<Vec<u8>>,
    roots: HashSet<Vec<u8>>,
    recursive: bool,
    dirs: bool,
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
        Self { exact, parents, roots, recursive: opts.recursive, dirs: opts.dir_requested }
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
        let _ = self.dirs;
        false
    }
}

/// A directory's metadata only needs writing back when one of the attributes
/// the transfer preserves differs. An unchanged directory costs no syscalls.
fn dir_attrs_differ(opts: &Options, before: &fs::Metadata, attrs: &Attrs) -> bool {
    (opts.times && before.mtime() != attrs.mtime)
        || (opts.perms && before.mode() & 0o7777 != attrs.mode & 0o7777)
        || (opts.owner && before.uid() != attrs.uid)
        || (opts.group && before.gid() != attrs.gid)
}

/// Change ownership only when a target id differs from what the entry already
/// has, as `tweak_attrs` does; a matching lchown still dirties the inode.
fn chown_changed(path: &Path, opts: &Options, attrs: &Attrs, nofollow: bool, before: Option<&fs::Metadata>) {
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

struct RecvDir {
    rel: Vec<u8>,
    dest: PathBuf,
    entries: Vec<EntryMeta>,
    rename_to: Option<Vec<u8>>,
    need: HashSet<u32>,
    existing: Vec<Option<fs::Metadata>>,
    dir_created: Vec<bool>,
    prefixes: HashMap<u32, ResumePrefix>,
    delta_candidates: HashSet<u32>,
    delta_requested: HashSet<u32>,
    bases: HashMap<u32, Arc<delta::DeltaBasis>>,
}

#[allow(clippy::too_many_arguments)]
fn process_dir<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    opts: &Options,
    features: u64,
    dest_arg: &Path,
    frame: &Frame,
    ids: &idmap::Receiver,
    dirs: &mut Vec<Option<RecvDir>>,
    finals: &mut Vec<FinalDir>,
    created_dirs: &mut u64,
    created_links: &mut u64,
    seen: &mut Vec<bool>,
    hardlinks: &mut HardLinks,
    mut local_output: Option<&mut Output>,
) -> io::Result<()> {
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
        entries.push(protocol::get_entry(&mut d, opts, features)?);
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
                *created_dirs += 1;
                true
            };
            (dest_arg.to_path_buf(), None, flags & protocol::DF_ATTRS != 0, exists, created)
        }
    } else {
        let parent_index = (parent_plus1 - 1) as usize;
        let parent = dirs
            .get(parent_index)
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
        if let Some(metadata) = &before {
            working_changed = set_dir_working_mode_with(&path, metadata);
        } else if !created {
            remove_any(&path)?;
            if make_dir(&path, entry.attrs.mode)? {
                *created_dirs += 1;
            }
        }
        (path, None, true, before, created)
    };
    let mut dir_modified = created;
    if rename_to.is_none() {
        directory_event(
            output,
            local_output.as_deref_mut(),
            features,
            opts,
            &rel,
            if attr_source.is_empty() { dir_path.as_os_str().as_bytes() } else { &attr_source },
            &attrs,
            before.as_ref(),
            created,
        )?;
    }

    let listing = destination_listing(&dir_path);
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
        match entry.kind {
            T_DIR => {
                let keep = existing.map(|m| m.is_dir()).unwrap_or(false);
                let made = if !keep {
                    remove_any(&target)?;
                    dir_modified = true;
                    let made = make_dir(&target, entry.attrs.mode)?;
                    if made {
                        *created_dirs += 1;
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
                    if let Some(key) = link_key.clone() {
                        hardlinks.register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                    }
                    if let Some(before) = existing {
                        if let Some(code) = metadata_code(opts, T_REG, before, entry) {
                            let event = taken_event(&code, &event_path, &entry.output_source, T_REG, entry.size, 0);
                            if let Some(key) = &link_key {
                                hardlinks.defer_event(key, &event_path, event);
                            } else {
        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                            }
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
                            hardlinks.register_transfer(key, member, existing.is_none())
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
                    .and_then(|m| if m.file_type().is_symlink() { fs::read_link(&target).ok() } else { None })
                    .map(|p| p.as_os_str().as_bytes() == entry.link.as_slice())
                    .unwrap_or(false);
                if let Some(key) = link_key.clone() {
                    hardlinks.register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if !same {
                    dir_modified = true;
                    remove_any(&target)?;
                    std::os::unix::fs::symlink(OsStr::from_bytes(&entry.link), &target)?;
                    *created_links += 1;
                    let mut event =
                        taken_event(b"cL+++++++++", &event_path, &entry.output_source, T_LNK, entry.size, 0);
                    event.target = entry.link.clone();
                    if let Some(key) = &link_key {
                        hardlinks.defer_event(key, &event_path, event);
                    } else {
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                    }
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_LNK, before, entry) {
                        let mut event = taken_event(&code, &event_path, &entry.output_source, T_LNK, entry.size, 0);
                        event.target = entry.link.clone();
                        if let Some(key) = &link_key {
                            hardlinks.defer_event(key, &event_path, event);
                        } else {
                            report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                        }
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
            }
            T_FIFO => {
                let same = existing.map(|m| m.file_type().is_fifo()).unwrap_or(false);
                if let Some(key) = link_key.clone() {
                    hardlinks.register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if !same {
                    dir_modified = true;
                    remove_any(&target)?;
                    ffi::make_fifo(&target, entry.attrs.mode)?;
                    let event = taken_event(b"cS+++++++++", &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                    if let Some(key) = &link_key {
                        hardlinks.defer_event(key, &event_path, event);
                    } else {
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                    }
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_FIFO, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                        if let Some(key) = &link_key {
                            hardlinks.defer_event(key, &event_path, event);
                        } else {
                            report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                        }
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
            }
            T_CHR | T_BLK => {
                if let Some(key) = link_key.clone() {
                    hardlinks.register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, entry.kind, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, entry.kind, entry.size, 0);
                        if let Some(key) = &link_key {
                            hardlinks.defer_event(key, &event_path, event);
                        } else {
                            report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                        }
                    }
                }
            }
            _ => {}
        }
        existing_entries.push(before);
    }
    let apply_attrs = apply_attrs
        && (dir_modified
            || working_changed
            || match &before {
                Some(metadata) => dir_attrs_differ(opts, metadata, &attrs),
                None => true,
            });
    if apply_attrs {
        finals.push(FinalDir { path: dir_path.clone(), attrs: attrs.clone(), apply: true });
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
    output.send(frame_type::NEED, &f.bytes)?;
    if dirs.len() <= id as usize {
        dirs.resize_with(id as usize + 1, || None);
    }
    let need_set = need.iter().copied().collect();
    dirs[id as usize] = Some(RecvDir {
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
    Ok(())
}

fn data_prefix(d: &mut Decoder<'_>) -> io::Result<ResumePrefix> {
    let size = i64::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad resume prefix"))?;
    Ok(ResumePrefix { size, ..ResumePrefix::default() })
}

fn open_infile(
    dir: &RecvDir,
    entry: &EntryMeta,
    total: i64,
    before: Option<fs::Metadata>,
    link_key: Option<crate::protocol::HardlinkKey>,
    prefix: ResumePrefix,
    delta: bool,
) -> io::Result<InFile> {
    let name = dir.rename_to.clone().unwrap_or_else(|| entry.name.clone());
    let final_path = dir.dest.join(OsStr::from_bytes(&name));
    let (temp, file) = create_temp(&dir.dest, &name)?;
    let prefix_ok = prefix.is_empty() || resume::restore_prefix(&file, &final_path, &prefix).is_ok();
    Ok(InFile {
        temp,
        file,
        final_path,
        ranges: Vec::new(),
        total: Some(total),
        attrs: None,
        status: None,
        finished: false,
        pending: 0,
        entry: entry.clone(),
        before,
        event_path: scan::join_rel(&dir.rel, &entry.name),
        link_key,
        prefix: prefix.size,
        prefix_ok,
        chunks: Default::default(),
        delta,
        delta_sum: [0, 0],
        ok: true,
    })
}

/// `Receiver::on_delta_request`: only a requested regular file gets a basis, and
/// one request per file is allowed. The reply carries the signature or a zero
/// presence byte, compressed exactly as the C++ sender reads it.
fn process_delta_request<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    payload: &[u8],
    opts: &Options,
    features: u64,
    dirs: &mut [Option<RecvDir>],
) -> io::Result<()> {
    if features & feature::DELTA == 0 {
        return bad("protocol error: unnegotiated delta request");
    }
    let mut d = Decoder::new(payload);
    let id = u32::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta request"))?;
    let idx = u32::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta request"))?;
    if !d.is_empty() {
        return bad("protocol error: trailing delta request");
    }
    let dir = dirs
        .get_mut(id as usize)
        .and_then(Option::as_mut)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: premature delta request"))?;
    let entry = dir
        .entries
        .get(idx as usize)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: unrequested delta basis"))?;
    if entry.kind != T_REG || !dir.need.contains(&idx) || !dir.delta_candidates.contains(&idx) {
        return bad("protocol error: unrequested delta basis");
    }
    if !dir.delta_requested.insert(idx) {
        return bad("protocol error: duplicate delta request");
    }
    let name = dir.rename_to.clone().unwrap_or_else(|| entry.name.clone());
    let path = dir.dest.join(OsStr::from_bytes(&name));
    let basis = delta::destination_basis(&path).ok().flatten().map(Arc::new);
    let signature = basis.as_ref().map(|basis| basis.signature.clone());
    let reply = delta::signature_reply(id, idx, signature.as_ref(), opts.compress, opts.compress_level);
    if let Some(basis) = basis {
        dir.bases.insert(idx, basis);
    }
    output.send(frame_type::DELTA_SIGNATURE, &reply)
}

#[allow(clippy::too_many_arguments)]
fn process_data<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    payload: &[u8],
    opts: &Options,
    features: u64,
    ids: &idmap::Receiver,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    pool: &mut WritePool,
    created_files: &mut u64,
    hardlinks: &mut HardLinks,
    mut local_output: Option<&mut Output>,
) -> io::Result<(u64, u64)> {
    let mut added_bytes = 0u64;
    let mut added_files = 0u64;
    if payload.len() < 9 {
        return bad("protocol error: short DATA frame");
    }
    let compressed = payload[0] & 1 != 0;
    let want = u64::from_le_bytes(payload[1..9].try_into().unwrap());
    let raw = protocol::unpack_body(&payload[9..], compressed, features)?;
    if ffi::xxh3_64(&raw) != want {
        return bad("data corruption detected in transfer stream");
    }
    let resume_enabled = opts.partial && features & feature::RESUME != 0;
    let mut d = Decoder::new(&raw);
    while !d.is_empty() {
        let id =
            u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DATA id"))?;
        let idx = u32::try_from(d.var().map_err(decode_err)?)
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad DATA index"))?;
        let kind = d.byte().map_err(decode_err)?;
        let dir = dirs
            .get_mut(id as usize)
            .and_then(|d| d.as_mut())
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad DATA record"))?;
        let entry = dir
            .entries
            .get(idx as usize)
            .cloned()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad DATA record"))?;
        if entry.kind != T_REG || !dir.need.contains(&idx) {
            return bad("protocol error: unrequested file data");
        }
        let before = dir.existing.get(idx as usize).and_then(Clone::clone);
        let event_path = scan::join_rel(&dir.rel, &entry.name);
        let event_source = entry.output_source.clone();
        let link_key = HardLinks::key(&entry, features);
        let delta = matches!(kind, rec::LITERAL | rec::COPY | rec::DELTA_END);
        let basis = if delta {
            if features & feature::DELTA == 0 {
                return bad("protocol error: unnegotiated delta data");
            }
            match dir.bases.get(&idx) {
                Some(basis) => Some(basis.clone()),
                None => return bad("protocol error: unrequested delta data"),
            }
        } else {
            None
        };
        match kind {
            rec::WHOLE => {
                let mut attrs = protocol::get_file_attrs(&mut d, features)?;
                ids.apply(&mut attrs, opts);
                let bytes = d.str().map_err(decode_err)?;
                let name = dir.rename_to.as_deref().unwrap_or(&entry.name);
                let final_path = dir.dest.join(OsStr::from_bytes(name));
                write_whole(&dir.dest, name, &final_path, &attrs, bytes, opts)?;
                *created_files += 1;
                added_bytes += bytes.len() as u64;
                added_files += 1;
                dir.need.remove(&idx);
                let code = transferred_code(opts, before.as_ref(), &entry);
                let event = taken_event(&code, &event_path, &event_source, T_REG, bytes.len() as i64, bytes.len() as i64);
                if let Some(key) = &link_key {
                    hardlinks.defer_event(key, &event_path, event);
                } else {
                    report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                }
            }
            rec::CHUNK | rec::LITERAL | rec::COPY => {
                let is_delta = kind != rec::CHUNK;
                let attempt = u32::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad attempt"))?;
                let prefix = if !is_delta && resume_enabled { data_prefix(&mut d)? } else { ResumePrefix::default() };
                let offset = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad chunk offset"))?;
                let total = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad chunk total"))?;
                let mut first = 0u32;
                let mut count = 0u32;
                let bytes = if kind == rec::COPY {
                    first = u32::try_from(d.var().map_err(decode_err)?)
                        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta reference"))?;
                    count = u32::try_from(d.var().map_err(decode_err)?)
                        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta reference"))?;
                    &[][..]
                } else {
                    d.str().map_err(decode_err)?
                };
                let length = if kind == rec::COPY {
                    let signature = &basis.as_ref().unwrap().signature;
                    signature.length(first, count)
                } else {
                    bytes.len() as i64
                };
                if offset < 0
                    || total < 0
                    || length <= 0
                    || length > total
                    || offset > total - length
                    || (is_delta && bytes.len() > (1 << 16))
                    || (kind == rec::COPY && length > (8 << 20))
                {
                    return bad("protocol error: bad chunk");
                }
                let offered = dir.prefixes.get(&idx);
                if !xs_wire::resume::verified(offered, prefix.size, total, attempt, offset, false) {
                    return bad("protocol error: unverified resume prefix");
                }
                let key = (id, idx, attempt);
                let infile = match infiles.entry(key) {
                    Entry::Occupied(occupied) => occupied.into_mut(),
                    Entry::Vacant(vacant) => {
                        if prefix.size > 0 {
                            added_bytes += prefix.size as u64;
                        }
                        let restore = if prefix.size > 0 { offered.copied().unwrap_or_default() } else { ResumePrefix::default() };
                        vacant.insert(open_infile(dir, &entry, total, before.clone(), link_key.clone(), restore, is_delta)?)
                    }
                };
                if infile.total != Some(total) {
                    return bad("protocol error: inconsistent file size");
                }
                let end = offset + length;
                if let Some(status) = infile.status {
                    let strict = if is_delta { status == 0 } else { status != 2 };
                    if end > total || (strict && total != infile.total.unwrap_or(total)) {
                        return bad("protocol error: inconsistent file size");
                    }
                }
                if infile.prefix != prefix.size || infile.delta != is_delta {
                    return bad("protocol error: inconsistent transfer method");
                }
                if !reserve_chunk(&mut infile.chunks, offset, end) {
                    return bad("protocol error: overlapping file chunks");
                }
                if is_delta {
                    let basis = basis.as_ref().unwrap();
                    if infile.ok {
                        let written = if count != 0 {
                            let mut scratch = Vec::new();
                            let mut at = offset;
                            let mut written = Ok(());
                            for index in first..first + count {
                                if let Err(error) = basis.read_block(index, &mut scratch) {
                                    written = Err(error);
                                    break;
                                }
                                if let Err(error) = infile.file.write_all_at(&scratch, at as u64) {
                                    written = Err(error);
                                    break;
                                }
                                at += scratch.len() as i64;
                            }
                            written
                        } else {
                            infile.file.write_all_at(bytes, offset as u64)
                        };
                        if written.is_err() {
                            infile.ok = false;
                        }
                    }
                    add_range(&mut infile.ranges, offset, end);
                    added_bytes += length as u64;
                } else {
                    infile.pending += 1;
                    pool.submit(infile.file.as_raw_fd(), bytes.to_vec(), offset, end, key);
                    added_bytes += bytes.len() as u64;
                }
            }
            rec::END | rec::DELTA_END => {
                let is_delta = kind == rec::DELTA_END;
                let attempt = u32::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad attempt"))?;
                let prefix = if !is_delta && resume_enabled { data_prefix(&mut d)? } else { ResumePrefix::default() };
                let total = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad file total"))?;
                let status = d.byte().map_err(decode_err)?;
                let mut attrs = protocol::get_file_attrs(&mut d, features)?;
                ids.apply(&mut attrs, opts);
                let mut delta_sum = [0u64; 2];
                if is_delta {
                    let digest = d.raw(16).map_err(decode_err)?;
                    delta_sum[0] = u64::from_le_bytes(digest[..8].try_into().unwrap());
                    delta_sum[1] = u64::from_le_bytes(digest[8..].try_into().unwrap());
                }
                if status > 2 || total < 0 {
                    return bad("protocol error: bad file completion");
                }
                let offered = dir.prefixes.get(&idx);
                if !xs_wire::resume::verified(offered, prefix.size, total, attempt, 0, true) {
                    return bad("protocol error: unverified resume prefix");
                }
                let key = (id, idx, attempt);
                let infile = match infiles.entry(key) {
                    Entry::Occupied(occupied) => occupied.into_mut(),
                    Entry::Vacant(vacant) => {
                        if prefix.size > 0 {
                            added_bytes += prefix.size as u64;
                        }
                        let restore = if prefix.size > 0 { offered.copied().unwrap_or_default() } else { ResumePrefix::default() };
                        vacant.insert(open_infile(dir, &entry, total, before.clone(), link_key.clone(), restore, is_delta)?)
                    }
                };
                if infile.prefix != prefix.size || infile.delta != is_delta {
                    return bad("protocol error: inconsistent transfer method");
                }
                if infile.status.is_some() {
                    return bad("protocol error: duplicate file completion");
                }
                if let Some(current) = infile.total {
                    let strict = status != 2;
                    if total > current || (strict && total != current) {
                        return bad("protocol error: inconsistent file size");
                    }
                    if infile.chunks.iter().next_back().map(|(_, &end)| end > total).unwrap_or(false) {
                        return bad("protocol error: inconsistent file size");
                    }
                }
                infile.total = Some(total);
                infile.attrs = Some(attrs);
                infile.status = Some(status);
                infile.delta_sum = delta_sum;
            }
            rec::FAIL => {
                dir.need.remove(&idx);
            }
            _ => return bad("protocol error: unknown DATA record"),
        }
    }
    Ok((added_bytes, added_files))
}

fn apply_write(done: WriteDone, infiles: &mut HashMap<(u32, u32, u32), InFile>) -> io::Result<Option<(u32, u32, u32)>> {
    done.result?;
    let Some(infile) = infiles.get_mut(&done.key) else {
        return Ok(None);
    };
    infile.pending = infile.pending.saturating_sub(1);
    add_range(&mut infile.ranges, done.start, done.end);
    Ok(Some(done.key))
}

fn settle(infiles: &mut HashMap<(u32, u32, u32), InFile>, pool: &WritePool) {
    while infiles.values().any(|infile| infile.pending > 0) {
        let Some(done) = pool.recv_done() else { break };
        let _ = apply_write(done, infiles);
    }
}

/// The C++ cleanup path: with --partial, keep the contiguous prefix and rename
/// it over the destination; otherwise remove the temporary file.
fn cleanup_partial(infiles: &mut HashMap<(u32, u32, u32), InFile>, opts: &Options) {
    for (_, infile) in infiles.drain() {
        if infile.finished {
            continue;
        }
        if opts.partial && infile.prefix_ok && infile.status != Some(1) {
            let total = infile.total.unwrap_or(0);
            let keep = contiguous(&infile.ranges, total);
            if infile.file.set_len(keep as u64).is_ok() && fs::rename(&infile.temp, &infile.final_path).is_ok() {
                continue;
            }
        }
        let _ = fs::remove_file(&infile.temp);
    }
}

/// Publish a file once its END has arrived and every queued range write has
/// returned; a failed attempt is removed only after its writes have drained.
#[allow(clippy::too_many_arguments)]
fn finish_ready<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    opts: &Options,
    features: u64,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    key: (u32, u32, u32),
    hardlinks: &mut HardLinks,
    local_output: Option<&mut Output>,
    partial_failure: &mut bool,
) -> io::Result<u64> {
    let Some((pending, status, total, prefix, prefix_ok, delta, delta_sum, ok)) = infiles.get(&key).map(|infile| {
        (
            infile.pending,
            infile.status,
            infile.total.unwrap_or(0),
            infile.prefix,
            infile.prefix_ok,
            infile.delta,
            infile.delta_sum,
            infile.ok,
        )
    }) else {
        return Ok(0);
    };
    if pending != 0 {
        return Ok(0);
    }
    let Some(status) = status else {
        return Ok(0);
    };
    // Completion is published only after every byte range has arrived; END can
    // precede the COPY records it authorizes.
    if !infiles.get(&key).map(|infile| covered_from(&infile.ranges, prefix, total)).unwrap_or(false) {
        return Ok(0);
    }
    // A source that changed between attempts ends with status 1. The sender will
    // resend the same file; a delta retry waits for our acknowledgment first.
    if status == 1 {
        let infile = infiles.remove(&key).unwrap();
        let _ = fs::remove_file(&infile.temp);
        if delta {
            let mut ack = Encoder::new();
            ack.var(u64::from(key.0)).var(u64::from(key.1));
            output.send(frame_type::DELTA_RETRY_ACK, &ack.bytes)?;
        }
        return Ok(0);
    }
    let verified = if delta && status == 0 && prefix_ok {
        delta::verify_file(&infiles.get(&key).unwrap().file, total, delta_sum).unwrap_or(false)
    } else {
        true
    };
    if !prefix_ok || status != 0 || !ok || !verified {
        let infile = infiles.remove(&key).unwrap();
        if let Some(dir) = dirs.get_mut(key.0 as usize).and_then(Option::as_mut) {
            dir.need.remove(&key.1);
            dir.bases.remove(&key.1);
        }
        *partial_failure = true;
        if opts.partial && prefix_ok && status == 2 {
            let keep = contiguous(&infile.ranges, total);
            if infile.file.set_len(keep as u64).is_ok() && fs::rename(&infile.temp, &infile.final_path).is_ok() {
                return Ok(0);
            }
        }
        let _ = fs::remove_file(&infile.temp);
        return Ok(0);
    }
    let infile = infiles.get_mut(&key).unwrap();
    if !finish_infile(infile, opts)? {
        return Ok(0);
    }
    let entry = infile.entry.clone();
    let before = infile.before.clone();
    let event_path = infile.event_path.clone();
    let link_key = infile.link_key.clone();
    infiles.remove(&key);
    if let Some(dir) = dirs.get_mut(key.0 as usize).and_then(Option::as_mut) {
        dir.need.remove(&key.1);
        dir.bases.remove(&key.1);
    }
    let code = transferred_code(opts, before.as_ref(), &entry);
    let event = taken_event(&code, &event_path, &entry.output_source, T_REG, total, total);
    if let Some(key) = &link_key {
        hardlinks.defer_event(key, &event_path, event);
    } else {
        report_event(output, local_output, features, opts, event)?;
    }
    Ok(1)
}

#[allow(clippy::too_many_arguments)]
fn drain_writes<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    opts: &Options,
    features: u64,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    pool: &WritePool,
    hardlinks: &mut HardLinks,
    mut local_output: Option<&mut Output>,
    partial_failure: &mut bool,
) -> io::Result<u64> {
    let mut files = 0;
    while let Some(done) = pool.try_done() {
        if let Some(key) = apply_write(done, infiles)? {
            files += finish_ready(
                output,
                opts,
                features,
                dirs,
                infiles,
                key,
                hardlinks,
                local_output.as_deref_mut(),
                partial_failure,
            )?;
        }
    }
    // An END can arrive after the last write already completed. Try every
    // settled entry, not only those whose completion this call observed.
    let keys: Vec<_> = infiles.keys().copied().collect();
    for key in keys {
        files += finish_ready(
            output,
            opts,
            features,
            dirs,
            infiles,
            key,
            hardlinks,
            local_output.as_deref_mut(),
            partial_failure,
        )?;
    }
    Ok(files)
}

/// Receiver: send F_DEST, answer each DIR with a NEED, write DATA records, then
/// apply deferred directory metadata and send DONE.
pub fn run_receiver<R: Read, W: Write + Send + 'static>(
    input: &mut R,
    output: W,
    opts: &Options,
    features: u64,
    dest: &[u8],
    control: Arc<IoControl>,
    mut local_output: Option<&mut Output>,
) -> io::Result<i32> {
    let mut output = FrameOut::new(output, None, control);
    let keepalive = features & feature::IO_CONTROL != 0;
    let mut identity = Encoder::new();
    identity.str(b"").str(b"").var(0).var(0);
    output.send(frame_type::DEST, &identity.bytes)?;
    let dest_path = PathBuf::from(OsString::from_vec(dest.to_vec()));
    let mut ids = idmap::Receiver::default();
    let mut dirs: Vec<Option<RecvDir>> = Vec::new();
    let mut seen_dirs: Vec<bool> = Vec::new();
    let mut finals: Vec<FinalDir> = Vec::new();
    let mut infiles: HashMap<(u32, u32, u32), InFile> = HashMap::new();
    // Like the C++ receiver, one file's ranges stay serial unless an explicit
    // -jN (N > 1) asked for range concurrency; the default budget is for files.
    let write_workers =
        if crate::parallel::explicit_ranges(opts.jobs) { crate::parallel::effective_jobs(opts.jobs) } else { 1 };
    let mut pool = WritePool::new(write_workers);
    let mut hardlinks = HardLinks::new(opts.hard_links && features & feature::HLINK != 0);
    let mut created_files = 0u64;
    let mut created_dirs = 0u64;
    let mut created_links = 0u64;
    let mut sender_code: Option<i32> = None;
    let mut partial_failure = false;
    let mut ended = false;
    let ack_enabled = opts.am_server && features & feature::PROGRESS_ACK != 0;
    let mut progress_bytes = 0u64;
    let mut progress_files = 0u64;
    let mut progress_last = (0u64, 0u64, Instant::now());
    while !ended {
        let frame = match protocol::read_checked(input, keepalive, features) {
            Ok(Some(frame)) => frame,
            Ok(None) => {
                settle(&mut infiles, &pool);
                cleanup_partial(&mut infiles, opts);
                return Ok(12);
            }
            Err(error) => {
                let _ = send_fatal(&mut output, &error.to_string());
                settle(&mut infiles, &pool);
                cleanup_partial(&mut infiles, opts);
                return Ok(2);
            }
        };
        let result = match frame.kind {
            frame_type::DIR => process_dir(
                &mut output,
                opts,
                features,
                &dest_path,
                &frame,
                &ids,
                &mut dirs,
                &mut finals,
                &mut created_dirs,
                &mut created_links,
                &mut seen_dirs,
                &mut hardlinks,
                local_output.as_deref_mut(),
            ),
            frame_type::DATA => match process_data(
                &mut output,
                &frame.payload,
                opts,
                features,
                &ids,
                &mut dirs,
                &mut infiles,
                &mut pool,
                &mut created_files,
                &mut hardlinks,
                local_output.as_deref_mut(),
            ) {
                Ok((bytes, files)) => {
                    progress_bytes += bytes;
                    progress_files += files;
                    match drain_writes(
                        &mut output,
                        opts,
                        features,
                        &mut dirs,
                        &mut infiles,
                        &pool,
                        &mut hardlinks,
                        local_output.as_deref_mut(),
                        &mut partial_failure,
                    ) {
                        Ok(finished) => {
                            created_files += finished;
                            progress_files += finished;
                            progress_ack(&mut output, features, progress_bytes, progress_files, false, &mut progress_last)
                        }
                        Err(error) => Err(error),
                    }
                }
                Err(error) => Err(error),
            },
            frame_type::DELTA_REQUEST => {
                process_delta_request(&mut output, &frame.payload, opts, features, &mut dirs)
            }
            frame_type::LIST_END => Ok(()),
            frame_type::DATA_END => {
                let mut d = Decoder::new(&frame.payload);
                match d.var().map_err(decode_err) {
                    Ok(code) => {
                        sender_code = Some(i32::try_from(code).unwrap_or(23));
                        ended = true;
                        Ok(())
                    }
                    Err(error) => Err(error),
                }
            }
            frame_type::IDMAP => {
                if features & feature::IDMAP == 0 {
                    bad("ID map without negotiated name-mapping support")
                } else {
                    ids.learn(&frame.payload);
                    Ok(())
                }
            }
            frame_type::CHOWN_CONFIG => bad("protocol error: unnegotiated ownership configuration"),
            frame_type::MSG => match msg_code(&frame) {
                Ok(Some(code)) => return Ok(code),
                Ok(None) => Ok(()),
                Err(error) => Err(error),
            },
            other => bad(format!("protocol error: unexpected frame {other} from sender")),
        };
        if let Err(error) = result {
            let text = error.to_string();
            let code = if text.starts_with("rejecting ") { 4 } else { 2 };
            let message = xs_wire::Message { kind: protocol::msg_kind::FATAL, code, text };
            let _ = output.send(frame_type::MSG, &message.encode());
            settle(&mut infiles, &pool);
            cleanup_partial(&mut infiles, opts);
            return Ok(code as i32);
        }
    }
    // DATA_END may follow the last END while that file's range writes are still
    // in the pool; drain every completion before publishing or cleaning up.
    while infiles.values().any(|infile| infile.pending > 0) {
        let Some(done) = pool.recv_done() else {
            break;
        };
        if let Some(key) = apply_write(done, &mut infiles)? {
            let finished = finish_ready(
                &mut output,
                opts,
                features,
                &mut dirs,
                &mut infiles,
                key,
                &mut hardlinks,
                local_output.as_deref_mut(),
                &mut partial_failure,
            )?;
            created_files += finished;
            progress_files += finished;
        }
    }
    let finished = drain_writes(
        &mut output,
        opts,
        features,
        &mut dirs,
        &mut infiles,
        &pool,
        &mut hardlinks,
        local_output.as_deref_mut(),
        &mut partial_failure,
    )?;
    created_files += finished;
    progress_files += finished;
    let missing = dirs.iter().flatten().any(|dir| !dir.need.is_empty());
    if !infiles.is_empty() || missing {
        let _ = send_fatal(&mut output, "protocol error: incomplete file data");
        cleanup_partial(&mut infiles, opts);
        output.finish()?;
        return Ok(2);
    }
    cleanup_partial(&mut infiles, opts);
    if hardlinks.enabled {
        finalize_hardlinks(
            &mut hardlinks,
            &mut output,
            features,
            opts,
            &mut created_files,
            local_output,
        )?;
    }
    for final_dir in finals.into_iter().rev() {
        if !final_dir.apply {
            continue;
        }
        idmap::chown_path(&final_dir.path, opts, &final_dir.attrs, false);
        if opts.perms {
            let _ = fs::set_permissions(&final_dir.path, fs::Permissions::from_mode(final_dir.attrs.mode & 0o7777));
        }
        if opts.times {
            let _ = ffi::set_mtime(&final_dir.path, final_dir.attrs.mtime, final_dir.attrs.mtime_ns as i64, false);
        }
    }
    if ack_enabled {
        progress_ack(&mut output, features, progress_bytes, progress_files, true, &mut progress_last)?;
    }
    let sender_code = sender_code.unwrap_or(0);
    let code = if sender_code != 0 { sender_code } else if partial_failure { 23 } else { 0 };
    let mut done = Encoder::new();
    done.var(code as u64);
    done.var(created_files).var(created_dirs).var(created_links).var(0).var(0);
    output.send(frame_type::DONE, &done.bytes)?;
    output.finish()?;
    Ok(code)
}
