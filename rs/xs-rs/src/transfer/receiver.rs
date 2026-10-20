//! The receiver engine: compare DIR listings, request missing entries with NEED,
//! write DATA records, then apply deferred directory metadata and send DONE.

use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet};
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileTypeExt, MetadataExt, PermissionsExt};
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::Instant;

use xs_wire::io_control::IoControl;
use xs_wire::{Decoder, Encoder, Frame};

use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG,
};
use crate::scan;

use crate::parallel::{WriteDone, WritePool};

use super::file::{
    add_range, covered, create_temp, destination_listing, finish_infile, make_dir, remove_any, set_dir_working_mode,
    write_whole, InFile,
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

struct RecvDir {
    rel: Vec<u8>,
    dest: PathBuf,
    entries: Vec<EntryMeta>,
    rename_to: Option<Vec<u8>>,
    need: HashSet<u32>,
    existing: Vec<Option<fs::Metadata>>,
    dir_created: Vec<bool>,
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
    ids.apply(&mut attrs, opts);
    for entry in &mut entries {
        ids.apply(&mut entry.attrs, opts);
    }

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
        let before = if created { None } else { fs::metadata(&path).ok().filter(|m| m.is_dir()) };
        if before.is_some() {
            set_dir_working_mode(&path);
        } else if !created {
            remove_any(&path)?;
            if make_dir(&path, entry.attrs.mode)? {
                *created_dirs += 1;
            }
        }
        (path, None, true, before, created)
    };
    if apply_attrs {
        finals.push(FinalDir { path: dir_path.clone(), attrs: attrs.clone(), apply: true });
    }
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
                    let made = make_dir(&target, entry.attrs.mode)?;
                    if made {
                        *created_dirs += 1;
                    }
                    made
                } else {
                    set_dir_working_mode(&target);
                    false
                };
                dir_created[index] = made;
            }
            T_REG => {
                let same = existing
                    .filter(|m| m.is_file())
                    .map(|m| m.len() as i64 == entry.size && m.mtime() == entry.attrs.mtime)
                    .unwrap_or(false);
                if same {
                    if opts.perms {
                        if let Ok(m) = fs::metadata(&target) {
                            if m.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
                                let _ = fs::set_permissions(&target, fs::Permissions::from_mode(entry.attrs.mode & 0o7777));
                            }
                        }
                    }
                    if opts.times {
                        let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, false);
                    }
                    idmap::chown_path(&target, opts, &entry.attrs, false);
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
                    let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, true);
                }
                idmap::chown_path(&target, opts, &entry.attrs, true);
            }
            T_FIFO => {
                let same = existing.map(|m| m.file_type().is_fifo()).unwrap_or(false);
                if let Some(key) = link_key.clone() {
                    hardlinks.register_ready(key, hardlink_member(entry, &event_path, &target, existing));
                }
                if !same {
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
                    let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, false);
                }
                idmap::chown_path(&target, opts, &entry.attrs, false);
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
    let mut f = Encoder::new();
    f.var(id as u64).var(need.len() as u64);
    let mut previous = 0u32;
    for &index in &need {
        f.var((index - previous) as u64);
        previous = index;
    }
    output.send(frame_type::NEED, &f.bytes)?;
    if dirs.len() <= id as usize {
        dirs.resize_with(id as usize + 1, || None);
    }
    let need_set = need.iter().copied().collect();
    dirs[id as usize] =
        Some(RecvDir { rel, dest: dir_path, entries, rename_to, need: need_set, existing: existing_entries, dir_created });
    Ok(())
}

fn open_infile(
    dir: &RecvDir,
    entry: &EntryMeta,
    total: i64,
    before: Option<fs::Metadata>,
    link_key: Option<crate::protocol::HardlinkKey>,
) -> io::Result<InFile> {
    let name = dir.rename_to.clone().unwrap_or_else(|| entry.name.clone());
    let final_path = dir.dest.join(OsStr::from_bytes(&name));
    let (temp, file) = create_temp(&dir.dest, &name)?;
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
    })
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
            rec::CHUNK => {
                let attempt = u32::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad attempt"))?;
                let offset = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad chunk offset"))?;
                let total = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad chunk total"))?;
                let bytes = d.str().map_err(decode_err)?;
                if offset < 0
                    || total < 0
                    || bytes.is_empty()
                    || offset.checked_add(bytes.len() as i64).map(|e| e > total).unwrap_or(true)
                {
                    return bad("protocol error: bad chunk");
                }
                let key = (id, idx, attempt);
                let infile = match infiles.entry(key) {
                    Entry::Occupied(occupied) => occupied.into_mut(),
                    Entry::Vacant(vacant) => {
                        vacant.insert(open_infile(dir, &entry, total, before.clone(), link_key.clone())?)
                    }
                };
                if infile.total != Some(total) {
                    return bad("protocol error: inconsistent file size");
                }
                infile.pending += 1;
                pool.submit(
                    infile.file.as_raw_fd(),
                    bytes.to_vec(),
                    offset,
                    offset + bytes.len() as i64,
                    key,
                );
                added_bytes += bytes.len() as u64;
            }
            rec::END => {
                let attempt = u32::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad attempt"))?;
                let total = i64::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad file total"))?;
                let status = d.byte().map_err(decode_err)?;
                let mut attrs = protocol::get_file_attrs(&mut d, features)?;
                ids.apply(&mut attrs, opts);
                if status > 2 || total < 0 {
                    return bad("protocol error: bad file completion");
                }
                let key = (id, idx, attempt);
                let infile = match infiles.entry(key) {
                    Entry::Occupied(occupied) => occupied.into_mut(),
                    Entry::Vacant(vacant) => {
                        vacant.insert(open_infile(dir, &entry, total, before.clone(), link_key.clone())?)
                    }
                };
                infile.total = Some(total);
                infile.attrs = Some(attrs);
                infile.status = Some(status);
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
) -> io::Result<u64> {
    let Some((pending, status, total)) =
        infiles.get(&key).map(|infile| (infile.pending, infile.status, infile.total.unwrap_or(0)))
    else {
        return Ok(0);
    };
    if pending != 0 {
        return Ok(0);
    }
    let Some(status) = status else {
        return Ok(0);
    };
    if status != 0 || !infiles.get(&key).map(|infile| covered(&infile.ranges, total)).unwrap_or(false) {
        if status == 0 {
            return Ok(0);
        }
        let infile = infiles.remove(&key).unwrap();
        let _ = fs::remove_file(&infile.temp);
        if let Some(dir) = dirs.get_mut(key.0 as usize).and_then(Option::as_mut) {
            dir.need.remove(&key.1);
        }
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
    let mut ended = false;
    let ack_enabled = opts.am_server && features & feature::PROGRESS_ACK != 0;
    let mut progress_bytes = 0u64;
    let mut progress_files = 0u64;
    let mut progress_last = (0u64, 0u64, Instant::now());
    while !ended {
        let frame = match protocol::read_checked(input, keepalive, features) {
            Ok(Some(frame)) => frame,
            Ok(None) => return Ok(12),
            Err(error) => {
                let _ = send_fatal(&mut output, &error.to_string());
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
            let _ = send_fatal(&mut output, &error.to_string());
            return Ok(2);
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
    )?;
    created_files += finished;
    progress_files += finished;
    for (_, infile) in infiles.drain() {
        if !infile.finished {
            let _ = fs::remove_file(&infile.temp);
        }
    }
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
    let mut done = Encoder::new();
    done.var(if sender_code != 0 { sender_code as u64 } else { 0 });
    done.var(created_files).var(created_dirs).var(created_links).var(0).var(0);
    output.send(frame_type::DONE, &done.bytes)?;
    output.finish()?;
    Ok(if sender_code != 0 { sender_code } else { 0 })
}
