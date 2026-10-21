//! DATA records on a worker: decompress and verify a frame, decode its records,
//! assemble large files from chunks, and publish each file once its writes settle.

use std::collections::hash_map::Entry;
use std::collections::HashMap;
use std::ffi::OsStr;
use std::fs;
use std::io;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::FileExt;
use std::os::unix::io::AsRawFd;
use std::sync::atomic::Ordering;
use std::sync::Arc;

use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder};

use crate::acls;
use crate::delta;
use crate::ffi;
use crate::idmap;
use crate::protocol::{self, bad, decode_err, feature, frame_type, rec, EntryMeta, Options, T_REG};
use crate::resume;
use crate::scan;
use crate::xattr;

use crate::parallel::{WriteDone, WritePool};

use crate::transfer::file::{
    add_range, contiguous, covered_from, create_temp, finish_infile, reserve_chunk, write_whole, DestDir, InFile, Stat,
};
use crate::transfer::hardlink::HardLinks;
use crate::transfer::{taken_event, transferred_code, FrameTx};

use super::dir::RecvDir;
use super::{Receiving, WholeJob};

pub(super) struct DataState {
    pub(super) infiles: HashMap<(u32, u32, u32), InFile>,
    pub(super) pool: WritePool,
}

/// What a queued DATA frame is charged: a compressed frame its raw size, as the reader's
/// bound counts work, not bytes on the wire.
pub(super) fn data_charge(payload: &[u8]) -> usize {
    if payload.len() > 9 && payload[0] & 1 != 0 {
        if let Ok(size) = Decoder::new(&payload[9..]).var() {
            return (size as usize).min(1 << 30) + 9;
        }
    }
    payload.len()
}

/// One DATA frame on a worker: decompress and check it with no lock held, then apply its
/// records in order.
pub(super) fn data_job(r: &Receiving, payload: Vec<u8>) -> io::Result<()> {
    let (records, base) = decode_data(payload, r.features)?;
    let mut data = r.data.lock().unwrap();
    let data = &mut *data;
    let mut table = r.table.lock().unwrap();
    let table = &mut *table;
    let bytes = {
        let mut streams = r.streams.lock().unwrap();
        let ids = r.ids.lock().unwrap();
        process_data(&records, base, r.opts, r.features, &mut streams, &ids, &mut table.dirs, &mut data.infiles, &mut data.pool, r)?
    };
    r.progress_bytes.fetch_add(bytes, Ordering::Relaxed);
    let finished = drain_writes(r, &mut table.dirs, &mut data.infiles, &data.pool)?;
    r.created_files.fetch_add(finished, Ordering::Relaxed);
    Ok(())
}

/// A DATA frame's records, decompressed if they were and checked against their XXH3-64,
/// and where in the buffer they start. Uncompressed records stay where they arrived.
pub(super) fn decode_data(payload: Vec<u8>, features: u64) -> io::Result<(Arc<Vec<u8>>, usize)> {
    if payload.len() < 9 {
        return bad("protocol error: short DATA frame");
    }
    let compressed = payload[0] & 1 != 0;
    let want = u64::from_le_bytes(payload[1..9].try_into().unwrap());
    let (records, base) = if compressed {
        (Arc::new(protocol::unpack_body(&payload[9..], compressed, features)?), 0)
    } else {
        (Arc::new(payload), 9)
    };
    if ffi::xxh3_64(&records[base..]) != want {
        return bad("data corruption detected in transfer stream");
    }
    Ok((records, base))
}

/// Write one small file and report it.
pub(super) fn write_job(r: &Receiving, job: WholeJob) -> io::Result<()> {
    let bytes = &job.records[job.bytes.clone()];
    write_whole(&job.dir, &job.name, &job.final_path, &job.attrs, bytes, r.opts)?;
    r.created_files.fetch_add(1, Ordering::Relaxed);
    r.emit_or_defer(job.link_key.as_ref(), &job.event_path, job.event)
}

pub(super) fn data_prefix(d: &mut Decoder<'_>) -> io::Result<ResumePrefix> {
    let size = i64::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad resume prefix"))?;
    Ok(ResumePrefix { size, ..ResumePrefix::default() })
}

pub(super) fn open_infile(
    dir: &RecvDir,
    entry: &EntryMeta,
    total: i64,
    before: Option<Stat>,
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
pub(super) fn process_delta_request(
    tx: &FrameTx,
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
    tx.send(frame_type::DELTA_SIGNATURE, reply)
}

#[allow(clippy::too_many_arguments)]
pub(super) fn process_data(
    records: &Arc<Vec<u8>>,
    base: usize,
    opts: &Options,
    features: u64,
    streams: &mut xattr::Incoming,
    ids: &idmap::Receiver,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    pool: &mut WritePool,
    r: &Receiving,
) -> io::Result<u64> {
    let mut added_bytes = 0u64;
    let raw = &records[base..];
    let resume_enabled = opts.partial && features & feature::RESUME != 0;
    let mut d = Decoder::new(raw);
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
                if features & feature::XATTRS != 0 {
                    attrs.xattrs = xattr::get_xattrs(&mut d, features, streams)?;
                    if !attrs.xattrs.complete {
                        return bad("protocol error: truncated DATA record or incomplete file xattrs");
                    }
                }
                if features & acls::NATIVE_ACL != 0 {
                    attrs.acls = acls::get_acls(&mut d, T_REG, opts)?;
                    if !attrs.acls.complete {
                        return bad("protocol error: truncated DATA record or incomplete file xattrs");
                    }
                }
                ids.apply(&mut attrs, opts);
                let bytes = d.str().map_err(decode_err)?;
                let start = bytes.as_ptr() as usize - records.as_ptr() as usize;
                let name = dir.rename_to.clone().unwrap_or_else(|| entry.name.clone());
                let final_path = dir.dest.join(OsStr::from_bytes(&name));
                added_bytes += bytes.len() as u64;
                let target = dir.out.clone().unwrap_or_else(|| Arc::new(DestDir::by_path(&dir.dest)));
                dir.received(idx);
                let code = transferred_code(opts, before.as_ref(), &entry);
                let event = taken_event(&code, &event_path, &event_source, T_REG, bytes.len() as i64, bytes.len() as i64);
                r.queue_write(WholeJob {
                    dir: target,
                    name,
                    final_path,
                    attrs,
                    records: records.clone(),
                    bytes: start..start + bytes.len(),
                    event,
                    event_path,
                    link_key,
                });
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
                        vacant.insert(open_infile(dir, &entry, total, before, link_key.clone(), restore, is_delta)?)
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
                    let start = bytes.as_ptr() as usize - records.as_ptr() as usize;
                    pool.submit(infile.file.as_raw_fd(), records.clone(), start..start + bytes.len(), offset, end, key);
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
                if features & feature::XATTRS != 0 {
                    attrs.xattrs = xattr::get_xattrs(&mut d, features, streams)?;
                    if !attrs.xattrs.complete {
                        return bad("protocol error: truncated DATA record or incomplete file xattrs");
                    }
                }
                if features & acls::NATIVE_ACL != 0 {
                    attrs.acls = acls::get_acls(&mut d, T_REG, opts)?;
                    if status == 0 && !attrs.acls.complete {
                        return bad("protocol error: bad file completion");
                    }
                }
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
                        vacant.insert(open_infile(dir, &entry, total, before, link_key.clone(), restore, is_delta)?)
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
                dir.received(idx);
            }
            _ => return bad("protocol error: unknown DATA record"),
        }
    }
    Ok(added_bytes)
}

pub(super) fn apply_write(done: WriteDone, infiles: &mut HashMap<(u32, u32, u32), InFile>) -> io::Result<Option<(u32, u32, u32)>> {
    done.result?;
    let Some(infile) = infiles.get_mut(&done.key) else {
        return Ok(None);
    };
    infile.pending = infile.pending.saturating_sub(1);
    add_range(&mut infile.ranges, done.start, done.end);
    Ok(Some(done.key))
}

pub(super) fn settle(infiles: &mut HashMap<(u32, u32, u32), InFile>, pool: &WritePool) {
    while infiles.values().any(|infile| infile.pending > 0) {
        let Some(done) = pool.recv_done() else { break };
        let _ = apply_write(done, infiles);
    }
}

/// The C++ cleanup path: with --partial, keep the contiguous prefix and rename
/// it over the destination; otherwise remove the temporary file.
pub(super) fn cleanup_partial(infiles: &mut HashMap<(u32, u32, u32), InFile>, opts: &Options) {
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
pub(super) fn finish_ready(
    r: &Receiving,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    key: (u32, u32, u32),
) -> io::Result<u64> {
    let opts = r.opts;
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
            r.tx.send(frame_type::DELTA_RETRY_ACK, ack.bytes)?;
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
            dir.received(key.1);
            dir.bases.remove(&key.1);
        }
        r.partial_failure.store(true, Ordering::Relaxed);
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
    let before = infile.before;
    let event_path = infile.event_path.clone();
    let link_key = infile.link_key.clone();
    infiles.remove(&key);
    if let Some(dir) = dirs.get_mut(key.0 as usize).and_then(Option::as_mut) {
        dir.received(key.1);
        dir.bases.remove(&key.1);
    }
    let code = transferred_code(opts, before.as_ref(), &entry);
    let event = taken_event(&code, &event_path, &entry.output_source, T_REG, total, total);
    r.emit_or_defer(link_key.as_ref(), &event_path, event)?;
    Ok(1)
}

pub(super) fn drain_writes(
    r: &Receiving,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    pool: &WritePool,
) -> io::Result<u64> {
    let mut files = 0;
    while let Some(done) = pool.try_done() {
        if let Some(key) = apply_write(done, infiles)? {
            files += finish_ready(r, dirs, infiles, key)?;
        }
    }
    // An END can arrive after the last write already completed. Try every
    // settled entry, not only those whose completion this call observed.
    let keys: Vec<_> = infiles.keys().copied().collect();
    for key in keys {
        files += finish_ready(r, dirs, infiles, key)?;
    }
    Ok(files)
}
