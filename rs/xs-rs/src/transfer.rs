//! The sender engine and the frame/event helpers both engines share. It walks and
//! streams DIR/NEED/DATA; the receiver in `transfer::receiver` compares, asks for
//! differences, and publishes files. One reader and one writer per side; the stream
//! stays pipelined because listings go first.

use std::collections::{HashMap, VecDeque};
use std::ffi::OsString;
use std::fs::{self, File};
use std::io::{self, BufWriter, Read, Seek, SeekFrom, Write};
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::sync::{Arc, Condvar, Mutex, OnceLock};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use xs_wire::io_control::IoControl;
use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, Frame, Suffixes};

use crate::acls;
use crate::compression::{CompressionLink, Transport};
use crate::delta::{DeltaSignature, DELTA_THRESHOLD};
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, msg_kind, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_LNK, T_REG,
};
use crate::scan::{self, SourceEntry};
use crate::xattr;
use xs_wire::output::file_type;
use xs_wire::{OutputEvent, ProgressAck};

fn msg_code(frame: &Frame) -> io::Result<Option<i32>> {
    let message = xs_wire::Message::decode(&frame.payload).map_err(decode_err)?;
    if message.kind == msg_kind::FATAL {
        if !message.text.is_empty() {
            eprintln!("xs-rs: {}", message.text);
        }
        return Ok(Some(message.code as i32));
    }
    if message.kind == msg_kind::ERROR && !message.text.is_empty() {
        eprintln!("xs-rs: {}", message.text);
    }
    Ok(None)
}

/// Report one event: a server receiver sends `F_OUTPUT`; a client receiver renders it.
fn report_event<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    local: Option<&mut Output>,
    features: u64,
    opts: &Options,
    event: OutputEvent,
) -> io::Result<()> {
    if opts.am_server {
        if features & feature::OUTPUT != 0 {
            output.send(frame_type::OUTPUT, &event.encode(features).payload)?;
        }
    } else if let Some(local) = local {
        local.push(event);
    }
    Ok(())
}

/// `Receiver::acknowledge`: at most one snapshot per 100 ms or per MiB, plus the final one.
fn progress_ack<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    features: u64,
    bytes: u64,
    files: u64,
    force: bool,
    last: &mut (u64, u64, Instant),
) -> io::Result<()> {
    if features & feature::PROGRESS_ACK == 0 {
        return Ok(());
    }
    let changed = bytes != last.0 || files != last.1;
    let now = Instant::now();
    if !force
        && (!changed || (now.duration_since(last.2) < Duration::from_millis(100) && bytes >= last.0 && bytes - last.0 < protocol::BLOCK_TARGET as u64))
    {
        return Ok(());
    }
    let frame = ProgressAck { bytes, files, ..ProgressAck::default() }.encode(features);
    output.send(frame.kind, &frame.payload)?;
    *last = (bytes, files, now);
    Ok(())
}

fn taken_event(code: &[u8], path: &[u8], source: &[u8], kind: u8, size: i64, bytes: i64) -> OutputEvent {
    OutputEvent {
        code: code.to_vec(),
        path: path.to_vec(),
        source: source.to_vec(),
        target: Vec::new(),
        kind,
        size,
        bytes,
        time: 0,
        hardlink_target: false,
    }
}

/// The event for a directory, if the output asks for one.
fn directory_event(
    opts: &Options,
    path: &[u8],
    source: &[u8],
    attrs: &Attrs,
    before: Option<&fs::Metadata>,
    created: bool,
) -> Option<OutputEvent> {
    let mut code = *b".d.........";
    let mut changed = created;
    if created {
        code = *b"cd+++++++++";
    } else if let Some(before) = before {
        if opts.times && before.mtime() != attrs.mtime {
            code[4] = b't';
            changed = true;
        }
        if opts.perms && before.mode() & 0o7777 != attrs.mode & 0o7777 {
            code[5] = b'p';
            changed = true;
        }
        if opts.owner && before.uid() != attrs.uid {
            code[6] = b'o';
            changed = true;
        }
        if opts.group && before.gid() != attrs.gid {
            code[7] = b'g';
            changed = true;
        }
    }
    if !changed && !opts.output_unchanged {
        return None;
    }
    if !changed {
        code[2..].fill(b' ');
    } else if !created && !opts.output_attrs {
        return None;
    }
    Some(taken_event(&code, path, source, file_type::DIR, attrs.size, 0))
}

fn transferred_code(opts: &Options, before: Option<&fs::Metadata>, entry: &EntryMeta) -> Vec<u8> {
    let mut code = if opts.pushing { *b"<f+++++++++" } else { *b">f+++++++++" };
    if let Some(before) = before.filter(|before| before.is_file()) {
        code[2..].fill(b'.');
        if before.len() as i64 != entry.size {
            code[3] = b's';
        }
        if !opts.times {
            code[4] = b'T';
        } else if before.mtime() != entry.attrs.mtime {
            code[4] = b't';
        }
        if opts.perms && before.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
            code[5] = b'p';
        }
        if opts.owner && before.uid() != entry.attrs.uid {
            code[6] = b'o';
        }
        if opts.group && before.gid() != entry.attrs.gid {
            code[7] = b'g';
        }
    }
    code.to_vec()
}

fn metadata_code(opts: &Options, kind: u8, before: &fs::Metadata, entry: &EntryMeta) -> Option<Vec<u8>> {
    let letter = match kind {
        T_REG => b'f',
        T_LNK => b'L',
        T_DIR => b'd',
        T_CHR | T_BLK => b'D',
        _ => b'S',
    };
    let mut code = *b".f.........";
    code[1] = letter;
    let mut changed = false;
    if opts.times && before.mtime() != entry.attrs.mtime {
        code[4] = b't';
        changed = true;
    }
    if opts.perms && before.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
        code[5] = b'p';
        changed = true;
    }
    if opts.owner && before.uid() != entry.attrs.uid {
        code[6] = b'o';
        changed = true;
    }
    if opts.group && before.gid() != entry.attrs.gid {
        code[7] = b'g';
        changed = true;
    }
    if changed && opts.output_attrs {
        Some(code.to_vec())
    } else if !changed && opts.output_unchanged {
        code[2..].fill(b' ');
        Some(code.to_vec())
    } else {
        None
    }
}

/// Nanoseconds on the same monotonic clock for every compression observation.
fn link_now() -> u64 {
    static START: OnceLock<Instant> = OnceLock::new();
    START.get_or_init(Instant::now).elapsed().as_nanos() as u64
}

/// Write one frame, charging the rate limiter and giving the compression policy what the
/// transport saw. A keep-alive is not charged and does not count as activity.
fn write_observed(
    output: &mut impl Write,
    link: Option<&CompressionLink>,
    control: &IoControl,
    kind: u8,
    payload: &[u8],
    activity: bool,
) -> io::Result<()> {
    let mut header = [0u8; xs_wire::HEADER_LEN];
    header[..4].copy_from_slice(&(payload.len() as u32).to_le_bytes());
    header[4] = kind;
    let total = header.len() + payload.len();
    let started = activity.then(Instant::now);
    // The header and the payload go out as they are, in pieces the rate limiter grants: the
    // buffered writer gathers small frames, and a large payload passes straight through it.
    // Unlimited, a frame is one piece, and one of 256 KiB or more is written without a copy.
    let piece = if activity && control.rate_limit() != 0 { 65536 } else { total };
    let mut written = 0;
    while written < total {
        let wanted = (total - written).min(piece);
        let count = if activity { control.limiter().acquire(wanted) } else { wanted };
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
        }
        control.begin_write();
        let end = written + count;
        if written < header.len() {
            output.write_all(&header[written..end.min(header.len())])?;
        }
        if end > header.len() {
            output.write_all(&payload[written.max(header.len()) - header.len()..end - header.len()])?;
        }
        written = end;
        control.note_write(activity);
    }
    if let (Some(started), Some(link)) = (started, link) {
        link.observe(
            total as u64,
            started.elapsed().as_nanos() as u64,
            Transport::Queued,
            link_now(),
            control.rate_limit(),
        );
    }
    Ok(())
}

/// Frames waiting for the writer thread, with the bytes they hold.
#[derive(Default)]
struct Queue {
    frames: VecDeque<(u8, Vec<u8>, bool)>,
    bytes: usize,
    /// No more frames: `finish` was called, or the writer stopped.
    closed: bool,
}

#[derive(Default)]
struct Outbox {
    queue: Mutex<Queue>,
    /// The writer waits here for frames,
    ready: Condvar,
    /// and the sender's threads for room.
    room: Condvar,
}

/// `Conn::MAX_Q` (`remote.cpp:254`): a sender's listings and data wait while this much is queued.
const MAX_QUEUED: usize = 48 << 20;

impl Outbox {
    fn push(&self, kind: u8, payload: Vec<u8>, activity: bool, bounded: bool) -> io::Result<()> {
        let mut queue = self.queue.lock().unwrap();
        while bounded && queue.bytes >= MAX_QUEUED && !queue.closed {
            queue = self.room.wait(queue).unwrap();
        }
        if queue.closed {
            return Err(io::Error::new(io::ErrorKind::BrokenPipe, "the writer thread stopped"));
        }
        queue.bytes += payload.len();
        queue.frames.push_back((kind, payload, activity));
        drop(queue);
        self.ready.notify_one();
        Ok(())
    }

    fn close(&self) {
        self.queue.lock().unwrap().closed = true;
        self.ready.notify_all();
        self.room.notify_all();
    }
}

/// A writer thread and its queue. `send` never waits, so a receiver that answers each
/// listing with a NEED never deadlocks against a sender that is busy writing; the sender's
/// threads write through `FrameTx::send_bounded`, which waits while `MAX_QUEUED` is queued.
struct FrameOut<W: Write + Send + 'static> {
    outbox: Arc<Outbox>,
    handle: Option<JoinHandle<io::Result<()>>>,
    _marker: std::marker::PhantomData<W>,
}

/// A handle on a `FrameOut`'s queue that other threads can hold.
#[derive(Clone)]
struct FrameTx {
    outbox: Arc<Outbox>,
}

impl FrameTx {
    fn send(&self, kind: u8, payload: Vec<u8>) -> io::Result<()> {
        self.outbox.push(kind, payload, true, false)
    }

    fn send_bounded(&self, kind: u8, payload: Vec<u8>) -> io::Result<()> {
        self.outbox.push(kind, payload, true, true)
    }

    /// Stop the stream: queued frames are still written, and waiting or later sends fail.
    fn close(&self) {
        self.outbox.close();
    }
}

impl<W: Write + Send + 'static> FrameOut<W> {
    fn new(output: W, link: Option<Arc<CompressionLink>>, control: Arc<IoControl>) -> Self {
        let outbox = Arc::new(Outbox::default());
        control.set_writer_active(true);
        let worker_control = control.clone();
        let writer_outbox = outbox.clone();
        let handle = std::thread::spawn(move || -> io::Result<()> {
            let outbox = writer_outbox;
            let result = (|| -> io::Result<()> {
                let mut output = BufWriter::with_capacity(256 << 10, output);
                loop {
                    let mut queue = outbox.queue.lock().unwrap();
                    if queue.frames.is_empty() && !queue.closed {
                        queue = outbox.ready.wait_timeout(queue, Duration::from_millis(100)).unwrap().0;
                    }
                    if queue.frames.is_empty() {
                        let closed = queue.closed;
                        drop(queue);
                        if closed {
                            break;
                        }
                        if worker_control.heartbeat_due() {
                            write_observed(&mut output, link.as_deref(), &worker_control, frame_type::KEEPALIVE, &[], false)?;
                            output.flush()?;
                        }
                        if worker_control.timed_out() {
                            return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
                        }
                        continue;
                    }
                    // Take everything queued at once, as `Conn::writer` swaps its queue out.
                    let frames = std::mem::take(&mut queue.frames);
                    queue.bytes = 0;
                    drop(queue);
                    outbox.room.notify_all();
                    for (kind, payload, activity) in frames {
                        write_observed(&mut output, link.as_deref(), &worker_control, kind, &payload, activity)?;
                    }
                    if outbox.queue.lock().unwrap().frames.is_empty() {
                        output.flush()?;
                    }
                }
                output.flush()
            })();
            outbox.close();
            control.set_writer_active(false);
            result
        });
        Self { outbox, handle: Some(handle), _marker: std::marker::PhantomData }
    }

    fn tx(&self) -> FrameTx {
        FrameTx { outbox: self.outbox.clone() }
    }

    fn send(&mut self, kind: u8, payload: &[u8]) -> io::Result<()> {
        self.send_with(kind, payload, true)
    }

    fn send_with(&mut self, kind: u8, payload: &[u8], activity: bool) -> io::Result<()> {
        self.outbox.push(kind, payload.to_vec(), activity, false)
    }

    fn finish(mut self) -> io::Result<()> {
        self.outbox.close();
        match self.handle.take().unwrap().join() {
            Ok(result) => result,
            Err(_) => Err(io::Error::other("the writer thread panicked")),
        }
    }
}

impl<W: Write + Send + 'static> Drop for FrameOut<W> {
    fn drop(&mut self) {
        self.outbox.close();
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

fn send_fatal(output: &mut FrameOut<impl Write + Send + 'static>, text: &str) -> io::Result<()> {
    let message = xs_wire::Message { kind: msg_kind::FATAL, code: 2, text: text.to_string() };
    output.send(frame_type::MSG, &message.encode())
}

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
    tasks: VecDeque<ReadTask>,
    /// Tasks a worker has taken and not finished.
    active: usize,
    needs: u32,
    /// How many listings the walk sent, once it is over.
    dirs: Option<u32>,
    /// DATA_END is queued: no task can come after it.
    ended: bool,
    aborted: bool,
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
        if due {
            let mut end = Encoder::new();
            end.var(0);
            self.tx.send_bounded(frame_type::DATA_END, end.bytes)?;
        }
        Ok(())
    }

    /// Stop everything: workers and the walk leave, delta waits fail.
    fn abort(&self) {
        self.work.lock().unwrap().aborted = true;
        self.work_changed.notify_all();
        self.replies.lock().unwrap().clear();
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
    }

    fn has_failed(&self) -> bool {
        *self.failed.lock().unwrap()
    }
}

#[allow(clippy::too_many_arguments)]
fn send_dir(
    s: &Sending,
    ids: &mut idmap::Sender,
    id: u32,
    parent_plus1: u32,
    pidx: u32,
    rel: &[u8],
    path: &Path,
    attrs: &Attrs,
    entries: Vec<SourceEntry>,
    flags: u8,
    next_id: &mut u32,
    selection: Option<&scan::Selection>,
    filters: &crate::filter::FilterList,
) -> io::Result<()> {
    let (opts, features) = (s.opts, s.features);
    let mut attrs = attrs.clone();
    attrs.xattrs = xattr::source_xattrs(path, T_DIR, filters, opts);
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
        entry.meta.attrs.xattrs = xattr::source_xattrs(&entry.path, entry.meta.kind, filters, opts);
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
    if let Some(map) = ids.describe(opts, features, attrs, &entries) {
        s.tx.send_bounded(map.kind, map.payload)?;
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
    let mut frame = Encoder::new();
    frame.var(id as u64).var(parent_plus1 as u64).var(pidx as u64);
    let flag_at = frame.bytes.len();
    frame.byte(flags);
    let level = s.link.level(opts.compress_level_explicit, opts.compress_level, opts.bwlimit);
    if protocol::pack_body(&mut frame, &body.bytes, opts.compress, level) {
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
        for (index, child_path, child_attrs) in child_specs {
            let child_id = *next_id;
            *next_id += 1;
            let child_rel = scan::join_rel(rel, &sent.dest_entries[index].meta.name);
            let (child_entries, child_filter);
            if let Some(selection) = selection {
                child_entries = selection.dirs.get(&child_rel).map(|dir| dir.entries.clone()).unwrap_or_default();
                child_filter = crate::filter::FilterList::default();
            } else {
                child_filter = filters.in_directory(&child_path, false);
                child_entries = scan::scan_dir_filtered(&child_path, opts, &child_filter, &child_rel).unwrap_or_default();
            }
            send_dir(
                s,
                ids,
                child_id,
                id + 1,
                index as u32,
                &child_rel,
                &child_path,
                &child_attrs,
                child_entries,
                protocol::DF_ATTRS,
                next_id,
                selection,
                &child_filter,
            )?;
        }
    }
    Ok(())
}

fn record(e: Encoder, block: &mut Vec<u8>) {
    block.extend_from_slice(&e.bytes);
}

fn flush_data(s: &Sending, block: &mut Vec<u8>, compress: bool) -> io::Result<()> {
    if block.is_empty() {
        return Ok(());
    }
    let opts = s.opts;
    let digest = ffi::xxh3_64(block);
    let mut payload = Encoder::new();
    payload.byte(0).raw(&digest.to_le_bytes());
    let level = s.link.level(opts.compress_level_explicit, opts.compress_level, opts.bwlimit);
    let compressed = protocol::pack_body(&mut payload, block, compress, level);
    if compressed {
        payload.bytes[0] = 1;
        s.link.set_last_level(level);
        if !opts.compress_level_explicit {
            s.link.count(level, block.len() as u64);
        }
    }
    s.tx.send_bounded(frame_type::DATA, payload.bytes)?;
    block.clear();
    Ok(())
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
                let mut e = Encoder::new();
                e.var(id as u64).var(idx as u64).byte(rec::CHUNK);
                e.var(0);
                if resume {
                    e.var(prefix.size.max(0) as u64);
                }
                e.var(offset).var(planned);
                e.str(&bytes);
                record(e, block);
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
        let mut e = Encoder::new();
        e.var(id as u64).var(idx as u64).byte(rec::CHUNK);
        e.var(0);
        if resume {
            e.var(prefix.size.max(0) as u64);
        }
        e.var(offset).var(planned);
        e.str(&buffer[..got]);
        record(e, block);
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
fn send_task(s: &Sending, task: &ReadTask, block: &mut Vec<u8>) -> io::Result<()> {
    let (opts, features, id) = (s.opts, s.features, task.id);
    let mut block_skip = false;
    for (position, &idx) in task.indices.iter().enumerate() {
        let entry = &task.dir.dest_entries[idx as usize];
        if entry.meta.kind != T_REG {
            continue;
        }
        // A skipped suffix gets a block of its own, as `RawFileBlock` isolates it.
        let skip = opts.compress && s.suffixes.matches(&entry.meta.name);
        if skip || skip != block_skip {
            flush_data(s, block, opts.compress && !block_skip)?;
        }
        block_skip = skip;
        if entry.meta.size <= protocol::SMALL_MAX as i64 {
            match fs::read(&entry.path) {
                Ok(bytes) => {
                    let mut e = Encoder::new();
                    e.var(id as u64).var(idx as u64).byte(rec::WHOLE);
                    protocol::put_file_attrs(&mut e, &entry.meta.attrs, features);
                    if features & feature::XATTRS != 0 {
                        s.streams.put(&mut e, &entry.meta.attrs.xattrs, features, &s.tx)?;
                    }
                    if features & acls::NATIVE_ACL != 0 {
                        acls::put_acls(&mut e, &entry.meta.attrs.acls, opts.numeric_ids);
                    }
                    e.str(&bytes);
                    record(e, block);
                    if block.len() >= protocol::BLOCK_TARGET {
                        flush_data(s, block, opts.compress && !block_skip)?;
                    }
                }
                Err(_) => record(fail_record(id, idx), block),
            }
        } else {
            flush_data(s, block, opts.compress && !block_skip)?;
            send_large(
                s,
                id,
                idx,
                entry,
                opts.compress && !skip,
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
    flush_data(s, block, opts.compress && !block_skip)
}

/// A read worker: takes tasks until DATA_END is out or the transfer stops.
fn read_worker(s: &Sending) {
    let mut block = Vec::new();
    loop {
        let task = {
            let mut state = s.work.lock().unwrap();
            loop {
                if state.aborted {
                    return;
                }
                if let Some(task) = state.tasks.pop_front() {
                    state.active += 1;
                    break task;
                }
                if state.ended {
                    return;
                }
                state = s.work_changed.wait(state).unwrap();
            }
        };
        let result = send_task(s, &task, &mut block);
        drop(task);
        if let Err(error) = result.and_then(|()| s.update_work(|state| state.active -= 1)) {
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
    let output = FrameOut::new(output, Some(link.clone()), control);
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
    };
    let code = std::thread::scope(|scope| {
        let s = &s;
        let (root_entries, root_selection) = (root.entries, root.selection.as_ref());
        let (root_base, root_filters, attrs) = (&root.base, &root_filters, &attrs);
        scope.spawn(move || {
            let mut ids = idmap::Sender::default();
            let mut next_id = 1u32;
            let walked = send_dir(
                s,
                &mut ids,
                0,
                0,
                0,
                b"",
                root_base,
                attrs,
                root_entries,
                flags,
                &mut next_id,
                root_selection,
                root_filters,
            )
            .and_then(|()| s.tx.send_bounded(frame_type::LIST_END, Vec::new()))
            .and_then(|()| s.update_work(|state| state.dirs = Some(next_id)));
            if let Err(error) = walked {
                s.fail(&error);
            }
        });
        for _ in 0..crate::parallel::effective_jobs(opts.jobs) {
            scope.spawn(move || read_worker(s));
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
        let Some(frame) = protocol::read_checked(input, keepalive, features)? else {
            return Ok(if s.has_failed() { 2 } else { 12 });
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

mod file;
mod hardlink;
mod receiver;

pub use receiver::run_receiver;
