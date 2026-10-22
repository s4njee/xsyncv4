//! The sender engine: walk the tree, answer NEEDs with DATA, and finish with DATA_END.
//! The walk sends DIR listings; `-j` workers read what each NEED asks for, packing small
//! records into per-worker DATA blocks across NEEDs. The receiver's frames come back here.

use std::collections::{HashMap, VecDeque};
use std::ffi::OsString;
use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::os::unix::ffi::OsStrExt;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Condvar, Mutex};

use xs_wire::io_control::IoControl;
use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, OutputEvent, ProgressAck, Suffixes};

use crate::acls;
use crate::compression::CompressionLink;
use crate::delta::{DeltaSignature, DELTA_THRESHOLD};
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{self, bad, decode_err, feature, frame_type, msg_kind, rec, Attrs, Options, T_DIR, T_REG};
use crate::scan::{self, SourceEntry};
use crate::xattr;

use super::msg_code;
use super::outbox::{FrameOut, FrameTx};

/// Automatic compression skips listings smaller than this (explicit `-z` does not).
const AUTO_LISTING_MIN: usize = 16 << 10;
/// A worker carries a partial DATA block across NEEDs up to this size, then sends it:
/// four workers can pack many one-file directories without a tiny frame each.
const DATA_BATCH: usize = 256 << 10;

struct SentDir {
    dest_entries: Vec<SourceEntry>,
}

/// xattr value streams, shared by the walk and the readers. A value's frames are queued
/// while the lock is held, so stream ids reach the wire in order, each before its first use.
struct SharedStreams(Mutex<xattr::Streams>);

impl SharedStreams {
    fn put(&self, out: &mut Encoder, attrs: &xattr::XattrSet, features: u64, tx: &FrameTx) -> io::Result<()> {
        let mut streams = self.0.lock().unwrap();
        streams.put_xattrs(out, attrs, features);
        for value in streams.drain() {
            tx.send_bounded(value.kind, value.payload)?;
        }
        Ok(())
    }
}

/// Part of one NEED, read by one worker: at most 64 files or 8 MiB, as `remote.cpp:1374-1389` splits it.
struct ReadTask {
    id: u32,
    dir: Arc<SentDir>,
    indices: Vec<u32>,
    eligible: Vec<bool>,
    prefixes: HashMap<u32, ResumePrefix>,
    /// `parallel_file_ranges`, decided over the whole NEED.
    ranges: bool,
}

#[derive(Default)]
struct WorkState {
    /// Directories to walk, newest first so the walk goes deep before wide, and how many
    /// are queued or being walked.
    walks: Vec<WalkTask>,
    walking: usize,
    tasks: VecDeque<ReadTask>,
    /// Tasks a worker has taken and not finished.
    active: usize,
    needs: u32,
    /// How many listings the walk sent, once it is over.
    dirs: Option<u32>,
    /// DATA_END is queued: no task can come after it.
    ended: bool,
    aborted: bool,
    /// Sending workers, and how many have flushed their partial DATA block.
    workers: usize,
    flushed: usize,
}

impl WorkState {
    /// DATA_END is due once the walk is over, every listing has had its NEED, and every read is done.
    fn data_end_due(&mut self) -> bool {
        if !self.ended && !self.aborted && self.dirs == Some(self.needs) && self.tasks.is_empty() && self.active == 0 {
            self.ended = true;
            return true;
        }
        false
    }
}

/// Where the reader hands a worker the delta signature it asked for.
type SignatureReply = mpsc::Sender<Option<DeltaSignature>>;

/// What the walk, the read workers and the NEED reader share.
struct Sending<'a> {
    tx: FrameTx,
    opts: &'a Options,
    features: u64,
    /// `-z`, or automatic compression with zstd negotiated: the frames this end sends may be
    /// compressed (each receiver decodes a flagged frame whenever zstd was negotiated).
    compress: bool,
    link: &'a CompressionLink,
    suffixes: Suffixes,
    resume: bool,
    delta: bool,
    streams: SharedStreams,
    dirs: Mutex<Vec<Option<Arc<SentDir>>>>,
    work: Mutex<WorkState>,
    work_changed: Condvar,
    /// Workers waiting for a delta signature, by (directory, index).
    replies: Mutex<HashMap<(u32, u32), SignatureReply>>,
    failed: Mutex<bool>,
    control: Arc<IoControl>,
    /// `--relative` and `--files-from`: the directories and entries chosen up front.
    selection: Option<&'a scan::Selection>,
    /// Ids for the listings, taken as each goes out.
    next_dir: AtomicU32,
    /// Names already described in an F_IDMAP.
    ids: Mutex<idmap::Sender>,
}

/// One directory for a walker to list and send (`K_WALK`).
struct WalkTask {
    parent_plus1: u32,
    pidx: u32,
    rel: Vec<u8>,
    path: PathBuf,
    attrs: Attrs,
    flags: u8,
    /// The root's entries, listed already; any other directory is listed by its walker.
    entries: Option<Vec<SourceEntry>>,
    /// The root's own filters, or a child's parent's.
    filters: Arc<crate::filter::FilterList>,
}


impl Sending<'_> {
    /// Change the work state, then wake one worker per task it added, or every worker
    /// once DATA_END is due and they can leave.
    fn update_work(&self, change: impl FnOnce(&mut WorkState)) -> io::Result<()> {
        let (due, added) = {
            let mut state = self.work.lock().unwrap();
            let queued = state.tasks.len();
            change(&mut state);
            (state.data_end_due(), state.tasks.len().saturating_sub(queued))
        };
        if due {
            self.work_changed.notify_all();
        } else {
            for _ in 0..added.min(crate::parallel::MAX_WORKERS) {
                self.work_changed.notify_one();
            }
        }
        Ok(())
    }

    /// Stop everything: workers and the walk leave, delta waits fail.
    fn abort(&self) {
        self.work.lock().unwrap().aborted = true;
        self.work_changed.notify_all();
        self.replies.lock().unwrap().clear();
    }

    fn push_walks(&self, mut tasks: Vec<WalkTask>) {
        let count = tasks.len();
        if count == 0 {
            return;
        }
        // The first child is walked first.
        tasks.reverse();
        {
            let mut state = self.work.lock().unwrap();
            state.walking += count;
            state.walks.extend(tasks);
        }
        for _ in 0..count.min(crate::parallel::MAX_WORKERS) {
            self.work_changed.notify_one();
        }
    }

    /// One walk task is over; after the last, LIST_END goes out (before DATA_END can).
    fn walked(&self) -> io::Result<()> {
        let last = {
            let mut state = self.work.lock().unwrap();
            state.walking -= 1;
            state.walking == 0
        };
        if last {
            self.tx.send_bounded(frame_type::LIST_END, Vec::new())?;
            let dirs = self.next_dir.load(Ordering::Relaxed);
            self.update_work(|state| state.dirs = Some(dirs))?;
        }
        Ok(())
    }

    /// The first error ends the transfer with a fatal message to the receiver.
    fn fail(&self, error: &io::Error) {
        let mut failed = self.failed.lock().unwrap();
        if !*failed {
            *failed = true;
            eprintln!("xs-rs: {error}");
            let message = xs_wire::Message { kind: msg_kind::FATAL, code: 2, text: error.to_string() };
            let _ = self.tx.send(frame_type::MSG, message.encode());
        }
        drop(failed);
        self.abort();
        self.control.request_stop();
    }

    /// Whether the next frame may be compressed: always with `-z`, and automatically while
    /// the link is slower than compression.
    fn compressing(&self) -> bool {
        self.compress && (self.opts.compress || self.link.auto_worthwhile())
    }

    /// `-z` follows the peer's adaptive rule; compression we chose stays cheap.
    fn level(&self) -> i32 {
        let opts = self.opts;
        if opts.compress {
            self.link.level(opts.compress_level_explicit, opts.compress_level, opts.bwlimit)
        } else {
            self.link.automatic_level(opts.bwlimit)
        }
    }

    fn has_failed(&self) -> bool {
        *self.failed.lock().unwrap()
    }
}

/// `Sender::walk` for one directory: list it, send its DIR, and queue its children, which
/// can only go out after it.
fn walk_dir(s: &Sending, task: WalkTask) -> io::Result<()> {
    let (opts, features, selection) = (s.opts, s.features, s.selection);
    let WalkTask { parent_plus1, pidx, rel, path, attrs, flags, entries, filters } = task;
    let (entries, filters) = match (entries, selection) {
        (Some(entries), _) => (entries, filters),
        (None, Some(selection)) => (
            selection.dirs.get(&rel).map(|dir| dir.entries.clone()).unwrap_or_default(),
            Arc::new(crate::filter::FilterList::default()),
        ),
        (None, None) => {
            let own = Arc::new(filters.in_directory(&path, false));
            (scan::scan_dir_filtered(&path, opts, &own, &rel).unwrap_or_default(), own)
        }
    };
    let rel = &rel[..];
    let path = path.as_path();
    let mut attrs = attrs;
    attrs.xattrs = xattr::source_xattrs(path, T_DIR, &filters, opts);
    attrs.acls = acls::source_acls(path, T_DIR, opts);
    let attrs = &attrs;
    let mut entries: Vec<SourceEntry> = if selection.is_some() {
        entries
    } else {
        entries
            .into_iter()
            .filter(|entry| !filters.excluded(&scan::join_rel(rel, &entry.meta.name), entry.meta.kind == T_DIR))
            .collect()
    };
    for entry in &mut entries {
        entry.meta.attrs.xattrs = xattr::source_xattrs(&entry.path, entry.meta.kind, &filters, opts);
        entry.meta.attrs.acls = acls::source_acls(&entry.path, entry.meta.kind, opts);
    }
    let child_specs: Vec<(usize, PathBuf, Attrs)> = entries
        .iter()
        .enumerate()
        .filter(|(_, e)| e.meta.kind == T_DIR)
        .map(|(index, e)| (index, e.path.clone(), e.meta.attrs.clone()))
        .collect();
    let mut body = Encoder::new();
    body.str(rel);
    protocol::put_dir_attrs(&mut body, attrs, features);
    if features & feature::DIR_OUTPUT != 0 {
        body.var(attrs.size.max(0) as u64);
        let mut source = path.as_os_str().as_bytes().to_vec();
        if rel.is_empty() && !source.ends_with(b"/.") {
            source.extend_from_slice(b"/.");
        }
        body.str(&source);
    }
    {
        // Decided and queued under one lock, so the names reach the wire before any DIR
        // that leaves them out because another walker described them.
        let mut ids = s.ids.lock().unwrap();
        if let Some(map) = ids.describe(opts, features, attrs, &entries) {
            s.tx.send_bounded(map.kind, map.payload)?;
        }
    }
    if features & feature::XATTRS != 0 {
        s.streams.put(&mut body, &attrs.xattrs, features, &s.tx)?;
    }
    if features & acls::NATIVE_ACL != 0 {
        acls::put_acls(&mut body, &attrs.acls, opts.numeric_ids);
    }
    if features & feature::DIR_CHILDREN != 0 {
        let count = if opts.recursive || selection.is_some() { child_specs.len() as u64 } else { 0 };
        body.var(count);
    }
    body.var(entries.len() as u64);
    for entry in &entries {
        protocol::put_entry(&mut body, &entry.meta, opts, features);
        if features & feature::XATTRS != 0 {
            s.streams.put(&mut body, &entry.meta.attrs.xattrs, features, &s.tx)?;
        }
        if features & acls::NATIVE_ACL != 0 {
            acls::put_acls(&mut body, &entry.meta.attrs.acls, opts.numeric_ids);
        }
    }
    let id = s.next_dir.fetch_add(1, Ordering::Relaxed);
    let mut frame = Encoder::new();
    frame.var(id as u64).var(parent_plus1 as u64).var(pidx as u64);
    let flag_at = frame.bytes.len();
    frame.byte(flags);
    let level = s.level();
    // Automatic compression is our choice, not the peer's `-z`: a listing is usually a
    // kilobyte or two, where a zstd frame costs more CPU than it saves on the wire.
    // With `-z`, every listing is compressed as the C++ does.
    let compress = s.compressing() && (opts.compress || body.bytes.len() >= AUTO_LISTING_MIN);
    if protocol::pack_body(&mut frame, &body.bytes, compress, level) {
        frame.bytes[flag_at] |= protocol::DF_ZSTD;
        s.link.set_last_level(level);
        if !opts.compress_level_explicit {
            s.link.count(level, body.bytes.len() as u64);
        }
    }
    // Known before it is sent: its NEED may come back at once.
    let sent = Arc::new(SentDir { dest_entries: entries });
    {
        let mut dirs = s.dirs.lock().unwrap();
        if dirs.len() <= id as usize {
            dirs.resize_with(id as usize + 1, || None);
        }
        dirs[id as usize] = Some(sent.clone());
    }
    s.tx.send_bounded(frame_type::DIR, frame.bytes)?;
    if opts.recursive || selection.is_some() {
        let children = child_specs
            .into_iter()
            .map(|(index, child_path, child_attrs)| WalkTask {
                parent_plus1: id + 1,
                pidx: index as u32,
                rel: scan::join_rel(rel, &sent.dest_entries[index].meta.name),
                path: child_path,
                attrs: child_attrs,
                flags: protocol::DF_ATTRS,
                entries: None,
                filters: filters.clone(),
            })
            .collect();
        s.push_walks(children);
    }
    Ok(())
}

/// A DATA payload's flags byte and XXH3-64, reserved at the front of each block so an
/// uncompressed block goes out as it is (`begin_block`, remote.cpp).
const DATA_HEADER: usize = 9;

fn record(e: Encoder, block: &mut Vec<u8>) {
    if block.is_empty() {
        block.resize(DATA_HEADER, 0);
    }
    block.extend_from_slice(&e.bytes);
}

/// Encode a record straight into the DATA block, after its reserved header.
fn encode_into(block: &mut Vec<u8>, write: impl FnOnce(&mut Encoder) -> io::Result<()>) -> io::Result<()> {
    if block.is_empty() {
        block.resize(DATA_HEADER, 0);
    }
    let mut e = Encoder { bytes: std::mem::take(block) };
    let result = write(&mut e);
    *block = e.bytes;
    result
}

fn flush_data(s: &Sending, block: &mut Vec<u8>, compress: bool) -> io::Result<()> {
    if block.len() <= DATA_HEADER {
        return Ok(());
    }
    let opts = s.opts;
    let records = &block[DATA_HEADER..];
    let digest = ffi::xxh3_64(records);
    let level = s.level();
    if let Some(compressed) = (compress && s.compressing()).then(|| protocol::compress_body(records, level)).flatten() {
        let mut payload = Encoder { bytes: Vec::with_capacity(DATA_HEADER + 10 + compressed.len()) };
        payload.byte(1).raw(&digest.to_le_bytes()).var(records.len() as u64).raw(&compressed);
        s.link.set_last_level(level);
        if !opts.compress_level_explicit {
            s.link.count(level, records.len() as u64);
        }
        block.clear();
        return s.tx.send_bounded(frame_type::DATA, payload.bytes);
    }
    block[0] = 0;
    block[1..DATA_HEADER].copy_from_slice(&digest.to_le_bytes());
    let payload = std::mem::replace(block, Vec::with_capacity(protocol::BLOCK_TARGET + (64 << 10)));
    s.tx.send_bounded(frame_type::DATA, payload)
}

/// The attributes, xattrs and ACLs that close a WHOLE, END or DELTA_END record.
fn put_record_attrs(s: &Sending, e: &mut Encoder, attrs: &Attrs) -> io::Result<()> {
    protocol::put_file_attrs(e, attrs, s.features);
    if s.features & feature::XATTRS != 0 {
        s.streams.put(e, &attrs.xattrs, s.features, &s.tx)?;
    }
    if s.features & acls::NATIVE_ACL != 0 {
        acls::put_acls(e, &attrs.acls, s.opts.numeric_ids);
    }
    Ok(())
}

fn fail_record(id: u32, idx: u32) -> Encoder {
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::FAIL);
    e
}

/// One CHUNK record: the file's identity, its resume prefix (`Some` even when empty), and a
/// slice of its bytes.
fn chunk_record(e: &mut Encoder, id: u32, idx: u32, prefix: Option<i64>, offset: u64, planned: u64, bytes: &[u8]) {
    e.var(id as u64).var(idx as u64).byte(rec::CHUNK);
    e.var(0);
    if let Some(prefix) = prefix {
        e.var(prefix.max(0) as u64);
    }
    e.var(offset).var(planned);
    e.str(bytes);
}

/// Ask the receiver for a file's delta signature and wait for it; only this worker waits.
fn request_signature(s: &Sending, id: u32, idx: u32) -> io::Result<Option<DeltaSignature>> {
    let (reply, wait) = mpsc::channel();
    s.replies.lock().unwrap().insert((id, idx), reply);
    let mut request = Encoder::new();
    request.var(id as u64).var(idx as u64);
    s.tx.send_bounded(frame_type::DELTA_REQUEST, request.bytes)?;
    wait.recv().map_err(|_| io::Error::new(io::ErrorKind::UnexpectedEof, "receiver closed before its delta signature"))
}

#[allow(clippy::too_many_arguments)]
fn send_large(
    s: &Sending,
    id: u32,
    idx: u32,
    entry: &SourceEntry,
    compress: bool,
    block: &mut Vec<u8>,
    ranges: bool,
    offered: Option<&ResumePrefix>,
    eligible: bool,
) -> io::Result<()> {
    let (opts, resume) = (s.opts, s.resume);
    let planned = entry.meta.size.max(0) as u64;
    let mut prefix = if resume {
        offered
            .filter(|p| p.size <= planned as i64)
            .and_then(|p| crate::resume::source_prefix(&entry.path, p))
            .unwrap_or_default()
    } else {
        ResumePrefix::default()
    };
    if s.delta && eligible && prefix.is_empty() && planned > DELTA_THRESHOLD as u64 {
        flush_data(s, block, compress)?;
        if let Some(signature) = request_signature(s, id, idx)? {
            return send_delta(s, id, idx, entry, compress, block, &signature, planned);
        }
    }
    if ranges && prefix.is_empty() && planned >= crate::parallel::RANGE_MIN {
        let jobs = crate::parallel::effective_jobs(opts.jobs);
        let complete = crate::parallel::read_ranges(
            &entry.path,
            planned,
            jobs,
            crate::parallel::RANGE_SPAN,
            |offset, bytes| {
                encode_into(block, |e| {
                    chunk_record(e, id, idx, resume.then_some(prefix.size), offset, planned, &bytes);
                    Ok(())
                })?;
                if block.len() >= protocol::BLOCK_TARGET {
                    flush_data(s, block, compress)?;
                }
                Ok(())
            },
        )?;
        flush_data(s, block, compress)?;
        let mut e = Encoder::new();
        e.var(id as u64).var(idx as u64).byte(rec::END);
        e.var(0);
        if resume {
            e.var(prefix.size.max(0) as u64);
        }
        e.var(planned).byte(if complete { 0 } else { 2 });
        put_record_attrs(s, &mut e, &entry.meta.attrs)?;
        record(e, block);
        return flush_data(s, block, compress);
    }
    let mut file = match File::open(&entry.path) {
        Ok(file) => file,
        Err(_) => return flush_data(s, block, compress),
    };
    let mut buffer = vec![0u8; protocol::BLOCK_TARGET];
    let mut offset = prefix.size.max(0) as u64;
    if offset > 0 && file.seek(SeekFrom::Start(offset)).is_err() {
        prefix = ResumePrefix::default();
        offset = 0;
    }
    let mut failed = false;
    loop {
        let want = (planned.saturating_sub(offset)).min(buffer.len() as u64) as usize;
        if want == 0 {
            break;
        }
        let mut got = 0;
        while got < want {
            match file.read(&mut buffer[got..want]) {
                Ok(0) => break,
                Ok(n) => got += n,
                Err(error) if error.kind() == io::ErrorKind::Interrupted => continue,
                Err(_) => {
                    failed = true;
                    break;
                }
            }
        }
        if got == 0 {
            failed = true;
            break;
        }
        encode_into(block, |e| {
            chunk_record(e, id, idx, resume.then_some(prefix.size), offset, planned, &buffer[..got]);
            Ok(())
        })?;
        offset += got as u64;
        if block.len() >= protocol::BLOCK_TARGET || failed {
            flush_data(s, block, compress)?;
        }
        if failed {
            break;
        }
    }
    flush_data(s, block, compress)?;
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::END);
    e.var(0);
    if resume {
        e.var(prefix.size.max(0) as u64);
    }
    let complete = !failed && offset == planned;
    e.var(offset).byte(if complete { 0 } else { 2 });
    put_record_attrs(s, &mut e, &entry.meta.attrs)?;
    record(e, block);
    flush_data(s, block, compress)
}

/// `Sender::read_one`'s delta branch: one LITERAL or COPY record per emitted op,
/// then DELTA_END with the source digest.
#[allow(clippy::too_many_arguments)]
fn send_delta(
    s: &Sending,
    id: u32,
    idx: u32,
    entry: &SourceEntry,
    compress: bool,
    block: &mut Vec<u8>,
    signature: &DeltaSignature,
    planned: u64,
) -> io::Result<()> {
    let matched = match File::open(&entry.path) {
        Ok(file) => crate::delta::match_file(&file, planned as i64, signature, |offset, first, count, literal| {
            let mut e = Encoder::new();
            e.var(id as u64).var(idx as u64).byte(if count != 0 { rec::COPY } else { rec::LITERAL });
            e.var(0).var(offset.max(0) as u64).var(planned);
            if count != 0 {
                e.var(first as u64).var(count as u64);
            } else {
                e.str(literal);
            }
            record(e, block);
            if block.len() >= protocol::BLOCK_TARGET {
                flush_data(s, block, compress)?;
            }
            Ok(())
        }),
        Err(error) => Err(error),
    };
    let (processed, status, sum) = match matched {
        Ok(result) if result.ok => (result.processed, 0u8, result.sum),
        Ok(result) => (result.processed, 2u8, result.sum),
        Err(_) => (0, 2u8, [0u64; 2]),
    };
    flush_data(s, block, compress)?;
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::DELTA_END);
    e.var(0).var(processed.max(0) as u64).byte(status);
    put_record_attrs(s, &mut e, &entry.meta.attrs)?;
    e.raw(&sum[0].to_le_bytes()).raw(&sum[1].to_le_bytes());
    record(e, block);
    flush_data(s, block, compress)
}

/// Read one task's files into DATA frames of about `BLOCK_TARGET`.
fn send_task(s: &Sending, task: &ReadTask, block: &mut Vec<u8>, contents: &mut Vec<u8>) -> io::Result<()> {
    let (opts, features, id) = (s.opts, s.features, task.id);
    let mut block_skip = false;
    for (position, &idx) in task.indices.iter().enumerate() {
        let entry = &task.dir.dest_entries[idx as usize];
        if entry.meta.kind != T_REG {
            continue;
        }
        // A skipped suffix gets a block of its own, as `RawFileBlock` isolates it.
        let skip = s.compress && s.suffixes.matches(&entry.meta.name);
        if skip || skip != block_skip {
            flush_data(s, block, s.compress && !block_skip)?;
        }
        block_skip = skip;
        if entry.meta.size <= protocol::SMALL_MAX as i64 {
            // Read into the worker's reused buffer, then once into the block (`read_one`).
            contents.clear();
            match File::open(&entry.path).and_then(|mut file| file.read_to_end(&mut *contents)) {
                Ok(_) => {
                    encode_into(block, |e| {
                        e.var(id as u64).var(idx as u64).byte(rec::WHOLE);
                        protocol::put_file_attrs(e, &entry.meta.attrs, features);
                        if features & feature::XATTRS != 0 {
                            s.streams.put(e, &entry.meta.attrs.xattrs, features, &s.tx)?;
                        }
                        if features & acls::NATIVE_ACL != 0 {
                            acls::put_acls(e, &entry.meta.attrs.acls, opts.numeric_ids);
                        }
                        e.str(&contents[..]);
                        Ok(())
                    })?;
                    if block.len() >= DATA_BATCH {
                        flush_data(s, block, s.compress && !block_skip)?;
                    }
                }
                Err(_) => record(fail_record(id, idx), block),
            }
        } else {
            flush_data(s, block, s.compress && !block_skip)?;
            send_large(
                s,
                id,
                idx,
                entry,
                s.compress && !skip,
                block,
                task.ranges,
                task.prefixes.get(&idx),
                task.eligible[position],
            )?;
        }
        if skip {
            flush_data(s, block, false)?;
        }
    }
    // The block stays with the worker: a NEED often asks for one file, and flushing
    // every task would send a tiny DATA frame per directory. It is flushed when it
    // reaches its batch limit or when the worker has no more reads.
    Ok(())
}

enum SendJob {
    Walk(WalkTask),
    Read(ReadTask),
}

/// A sending worker, as the C++ pool's: walks directories and reads what NEEDs ask for until
/// DATA_END is out or the transfer stops. Half prefer walking (`scan_workers`), but reads come
/// first for everyone once 64 are queued (`q1_soft_limit`).
fn send_worker(s: &Sending, prefers_walk: bool) {
    let mut block = Vec::new();
    let mut contents = Vec::new();
    loop {
        let mut idle = false;
        let job = {
            let mut state = s.work.lock().unwrap();
            loop {
                if state.aborted {
                    return;
                }
                let walk_first = prefers_walk && state.tasks.len() < 64;
                let job = if walk_first {
                    state.walks.pop().map(SendJob::Walk).or_else(|| state.tasks.pop_front().map(SendJob::Read))
                } else {
                    state.tasks.pop_front().map(SendJob::Read).or_else(|| state.walks.pop().map(SendJob::Walk))
                };
                if let Some(job) = job {
                    if matches!(job, SendJob::Read(_)) {
                        state.active += 1;
                    }
                    break Some(job);
                }
                if state.ended {
                    break None;
                }
                // As the C++ pool's `on_idle`: a worker with a partial DATA block and
                // nothing to do puts it on the wire instead of letting the receiver wait.
                if !block.is_empty() {
                    idle = true;
                    break None;
                }
                state = s.work_changed.wait(state).unwrap();
            }
        };
        if idle {
            if let Err(error) = flush_data(s, &mut block, s.compress) {
                s.fail(&error);
                return;
            }
            continue;
        }
        let Some(job) = job else {
            // No more reads: put this worker's partial block on the wire before the
            // last worker sends DATA_END, so DATA never follows the end marker.
            if let Err(error) = flush_data(s, &mut block, s.compress) {
                s.fail(&error);
                return;
            }
            let last = {
                let mut state = s.work.lock().unwrap();
                state.flushed += 1;
                state.flushed == state.workers
            };
            if last {
                let mut end = Encoder::new();
                end.var(0);
                if let Err(error) = s.tx.send_bounded(frame_type::DATA_END, end.bytes) {
                    s.fail(&error);
                }
            }
            return;
        };
        let result = match job {
            SendJob::Walk(task) => walk_dir(s, task).and_then(|()| s.walked()),
            SendJob::Read(task) => {
                let result = send_task(s, &task, &mut block, &mut contents);
                drop(task);
                result.and_then(|()| s.update_work(|state| state.active -= 1))
            }
        };
        if let Err(error) = result {
            s.fail(&error);
            return;
        }
    }
}

/// Decode one NEED and queue its reads.
fn queue_need(s: &Sending, payload: &[u8]) -> io::Result<()> {
    let mut d = Decoder::new(payload);
    let id = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED id"))?;
    let count = usize::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED count"))?;
    let dir = s
        .dirs
        .lock()
        .unwrap()
        .get_mut(id as usize)
        .and_then(Option::take)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad NEED directory"))?;
    let mut indices = Vec::with_capacity(count.min(dir.dest_entries.len()));
    let mut eligible = Vec::with_capacity(indices.capacity());
    let mut prefixes = HashMap::new();
    let mut previous = 0u32;
    for i in 0..count {
        let difference =
            u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED index"))?;
        if i > 0 && difference == 0 {
            return bad("protocol error: bad NEED index");
        }
        previous = previous.checked_add(difference).ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "bad NEED index"))?;
        let entry = dir
            .dest_entries
            .get(previous as usize)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad NEED index"))?;
        let prefix = if s.resume { ResumePrefix::get(&mut d).map_err(decode_err)? } else { ResumePrefix::default() };
        let candidate = if s.delta {
            let value = d.byte().map_err(decode_err)?;
            if value > 1 {
                return bad("protocol error: bad delta candidate");
            }
            value != 0
        } else {
            false
        };
        if prefix.size > entry.meta.size {
            return bad("protocol error: bad resume prefix");
        }
        if candidate && entry.meta.kind != T_REG {
            return bad("protocol error: bad delta candidate");
        }
        if !prefix.is_empty() {
            prefixes.insert(previous, prefix);
        }
        indices.push(previous);
        eligible.push(candidate);
    }
    if !d.is_empty() {
        return bad("protocol error: trailing NEED payload");
    }
    // `parallel_file_ranges`: split only when an explicit -jN asked for it and
    // the NEED does not already offer several large files as parallel work.
    let large = indices
        .iter()
        .filter(|&&idx| {
            let entry = &dir.dest_entries[idx as usize];
            entry.meta.kind == T_REG && entry.meta.size >= crate::parallel::RANGE_MIN as i64
        })
        .count();
    let ranges = crate::parallel::explicit_ranges(s.opts.jobs) && large <= 1;
    let mut tasks = Vec::new();
    let (mut start, mut bytes) = (0usize, 0i64);
    for i in 0..indices.len() {
        bytes += dir.dest_entries[indices[i] as usize].meta.size.max(0);
        if i + 1 - start >= 64 || bytes >= 8 << 20 || i + 1 == indices.len() {
            let task_prefixes =
                indices[start..=i].iter().filter_map(|idx| prefixes.get(idx).map(|prefix| (*idx, *prefix))).collect();
            tasks.push(ReadTask {
                id,
                dir: dir.clone(),
                indices: indices[start..=i].to_vec(),
                eligible: eligible[start..=i].to_vec(),
                prefixes: task_prefixes,
                ranges,
            });
            (start, bytes) = (i + 1, 0);
        }
    }
    s.update_work(|state| {
        state.tasks.extend(tasks);
        state.needs += 1;
    })
}

/// Sender: wait for the receiver's F_DEST, then walk and send listings on one thread while
/// `-j` workers read what each NEED asks for and this thread reads the receiver's frames.
/// DATA_END follows the last read; the receiver's DONE ends it.
pub fn run_sender<R: Read, W: Write + Send + 'static>(
    input: &mut R,
    output: W,
    opts: &Options,
    features: u64,
    sources: &[OsString],
    control: Arc<IoControl>,
    local_output: Option<&mut Output>,
) -> io::Result<i32> {
    let link = Arc::new(CompressionLink::new());
    let output = FrameOut::new(output, Some(link.clone()), control.clone());
    let keepalive = features & feature::IO_CONTROL != 0;
    loop {
        let Some(frame) = protocol::read_checked(input, keepalive, features)? else {
            return Ok(12);
        };
        match frame.kind {
            frame_type::DEST => break,
            frame_type::MSG => {
                if let Some(code) = msg_code(&frame)? {
                    return Ok(code);
                }
            }
            frame_type::IDMAP => {}
            _ => return bad(format!("protocol error: unexpected frame {} before F_DEST", frame.kind)),
        }
    }
    let root = if opts.relative || opts.files_from_set {
        let names = if opts.files_from_set { Some(opts.file_names.as_slice()) } else { None };
        scan::build_selection(sources, names, opts, &opts.filters)?
    } else {
        scan::build_root(sources, opts)?
    };
    let root_filters = if root.selection.is_some() {
        crate::filter::FilterList::default()
    } else {
        opts.filters.in_directory(&root.base, false)
    };
    let attrs = root.attrs.clone().unwrap_or_default();
    let mut flags = if root.attrs.is_some() { protocol::DF_ATTRS } else { 0 };
    if root.single {
        flags |= protocol::DF_SINGLE;
    }
    let s = Sending {
        tx: output.tx(),
        opts,
        features,
        compress: opts.compress || (opts.auto_compress && features & feature::ZSTD != 0),
        link: &link,
        suffixes: crate::compression::suffixes(&opts.skip_compress),
        resume: opts.partial && features & feature::RESUME != 0,
        delta: features & feature::DELTA != 0,
        streams: SharedStreams(Mutex::new(xattr::Streams::new())),
        dirs: Mutex::new(Vec::new()),
        work: Mutex::new(WorkState::default()),
        work_changed: Condvar::new(),
        replies: Mutex::new(HashMap::new()),
        failed: Mutex::new(false),
        control,
        selection: root.selection.as_ref(),
        next_dir: AtomicU32::new(0),
        ids: Mutex::new(idmap::Sender::default()),
    };
    let jobs = crate::parallel::effective_jobs(opts.jobs);
    s.work.lock().unwrap().workers = jobs;
    s.push_walks(vec![WalkTask {
        parent_plus1: 0,
        pidx: 0,
        rel: Vec::new(),
        path: root.base.clone(),
        attrs,
        flags,
        entries: Some(root.entries),
        filters: Arc::new(root_filters),
    }]);
    let code = std::thread::scope(|scope| {
        let s = &s;
        for worker in 0..jobs {
            // Half of them, at least one, prefer walking (`scan_workers`).
            let prefers_walk = worker < (jobs / 2).max(1);
            scope.spawn(move || send_worker(s, prefers_walk));
        }
        let code = read_replies(s, input, keepalive, local_output);
        // Whatever ended it, the walk and the workers stop now; frames already queued still go out.
        s.abort();
        s.tx.close();
        code
    });
    output.finish()?;
    code
}

/// The sender's reading side: NEEDs become read tasks, delta signatures go to the worker
/// waiting for them, and the receiver's DONE (or failure) ends the transfer.
fn read_replies<R: Read>(s: &Sending, input: &mut R, keepalive: bool, mut local_output: Option<&mut Output>) -> io::Result<i32> {
    let features = s.features;
    loop {
        let frame = match protocol::read_checked(input, keepalive, features) {
            Ok(Some(frame)) => frame,
            Ok(None) => return Ok(if s.has_failed() { 2 } else { 12 }),
            // A worker's failure has been sent already; this read only stopped for it.
            Err(_) if s.has_failed() => return Ok(2),
            Err(error) => return Err(error),
        };
        let action: io::Result<Option<i32>> = match frame.kind {
            frame_type::OUTPUT => {
                if features & feature::OUTPUT == 0 {
                    bad("file output without negotiated support")
                } else {
                    OutputEvent::decode(&frame.payload, features).map_err(decode_err).map(|event| {
                        if let Some(local) = local_output.as_deref_mut() {
                            local.push(event);
                        }
                        None
                    })
                }
            }
            frame_type::PROGRESS => ProgressAck::decode(&frame.payload, features)
                .map(|_| None)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed progress acknowledgment")),
            frame_type::NEED => queue_need(s, &frame.payload).map(|()| None),
            frame_type::DELTA_SIGNATURE => crate::delta::decode_signature(&frame.payload, features).and_then(|(id, idx, signature)| {
                match s.replies.lock().unwrap().remove(&(id, idx)) {
                    Some(reply) => {
                        let _ = reply.send(signature);
                        Ok(None)
                    }
                    None => bad("protocol error: unsolicited delta reply"),
                }
            }),
            frame_type::DONE => {
                let mut d = Decoder::new(&frame.payload);
                d.var().map_err(decode_err).map(|code| Some(i32::try_from(code).unwrap_or(0)))
            }
            frame_type::MSG => msg_code(&frame),
            frame_type::IDMAP => Ok(None),
            other => bad(format!("protocol error: unexpected frame {other} from receiver")),
        };
        match action {
            Ok(Some(code)) => return Ok(if s.has_failed() { 2 } else { code }),
            Ok(None) => {}
            Err(error) => {
                s.fail(&error);
                return Ok(2);
            }
        }
    }
}
