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
use std::sync::mpsc::{channel, Sender, TryRecvError};
use std::sync::{Arc, OnceLock};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use xs_wire::io_control::IoControl;
use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, Frame, Suffixes};

use crate::compression::{CompressionLink, Transport};
use crate::delta::{DeltaSignature, DELTA_THRESHOLD};
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, msg_kind, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_LNK, T_REG,
};
use crate::scan::{self, SourceEntry};
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

#[allow(clippy::too_many_arguments)]
fn directory_event(
    output: &mut FrameOut<impl Write + Send + 'static>,
    local: Option<&mut Output>,
    features: u64,
    opts: &Options,
    path: &[u8],
    source: &[u8],
    attrs: &Attrs,
    before: Option<&fs::Metadata>,
    created: bool,
) -> io::Result<()> {
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
        return Ok(());
    }
    if !changed {
        code[2..].fill(b' ');
    } else if !created && !opts.output_attrs {
        return Ok(());
    }
    report_event(output, local, features, opts, taken_event(&code, path, source, file_type::DIR, attrs.size, 0))
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
    let mut bytes = Vec::with_capacity(xs_wire::HEADER_LEN + payload.len());
    bytes.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    bytes.push(kind);
    bytes.extend_from_slice(payload);
    let started = activity.then(Instant::now);
    let mut written = 0;
    while written < bytes.len() {
        let wanted = (bytes.len() - written).min(65536);
        let count = if activity { control.limiter().acquire(wanted) } else { wanted };
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
        }
        control.begin_write();
        output.write_all(&bytes[written..written + count])?;
        written += count;
        control.note_write(activity);
    }
    if let (Some(started), Some(link)) = (started, link) {
        link.observe(
            bytes.len() as u64,
            started.elapsed().as_nanos() as u64,
            Transport::Queued,
            link_now(),
            control.rate_limit(),
        );
    }
    Ok(())
}

/// A writer thread with an unbounded queue. Listings can be produced while the
/// peer's NEED pipe is momentarily full, so the two directions never deadlock.
struct FrameOut<W: Write + Send + 'static> {
    tx: Option<Sender<(u8, Vec<u8>, bool)>>,
    handle: Option<JoinHandle<io::Result<()>>>,
    _marker: std::marker::PhantomData<W>,
}

impl<W: Write + Send + 'static> FrameOut<W> {
    fn new(output: W, link: Option<Arc<CompressionLink>>, control: Arc<IoControl>) -> Self {
        let (tx, rx) = channel::<(u8, Vec<u8>, bool)>();
        control.set_writer_active(true);
        let worker_control = control.clone();
        let handle = std::thread::spawn(move || -> io::Result<()> {
            let result = (|| -> io::Result<()> {
                let mut output = BufWriter::with_capacity(256 << 10, output);
                loop {
                    match rx.try_recv() {
                        Ok((kind, payload, activity)) => {
                            write_observed(&mut output, link.as_deref(), &worker_control, kind, &payload, activity)?
                        }
                        Err(TryRecvError::Empty) => {
                            output.flush()?;
                            match rx.recv_timeout(Duration::from_millis(100)) {
                                Ok((kind, payload, activity)) => write_observed(
                                    &mut output,
                                    link.as_deref(),
                                    &worker_control,
                                    kind,
                                    &payload,
                                    activity,
                                )?,
                                Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {
                                    if worker_control.heartbeat_due() {
                                        write_observed(
                                            &mut output,
                                            link.as_deref(),
                                            &worker_control,
                                            frame_type::KEEPALIVE,
                                            &[],
                                            false,
                                        )?;
                                        output.flush()?;
                                    }
                                    if worker_control.timed_out() {
                                        return Err(io::Error::new(io::ErrorKind::TimedOut, "I/O timeout"));
                                    }
                                }
                                Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => break,
                            }
                        }
                        Err(TryRecvError::Disconnected) => break,
                    }
                }
                output.flush()
            })();
            control.set_writer_active(false);
            result
        });
        Self { tx: Some(tx), handle: Some(handle), _marker: std::marker::PhantomData }
    }

    fn send(&mut self, kind: u8, payload: &[u8]) -> io::Result<()> {
        self.send_with(kind, payload, true)
    }

    fn send_with(&mut self, kind: u8, payload: &[u8], activity: bool) -> io::Result<()> {
        self.tx
            .as_ref()
            .ok_or_else(|| io::Error::new(io::ErrorKind::BrokenPipe, "sender already finished"))?
            .send((kind, payload.to_vec(), activity))
            .map_err(|_| io::Error::new(io::ErrorKind::BrokenPipe, "the writer thread stopped"))
    }

    fn finish(mut self) -> io::Result<()> {
        self.tx.take();
        match self.handle.take().unwrap().join() {
            Ok(result) => result,
            Err(_) => Err(io::Error::other("the writer thread panicked")),
        }
    }
}

impl<W: Write + Send + 'static> Drop for FrameOut<W> {
    fn drop(&mut self) {
        self.tx.take();
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

#[allow(clippy::too_many_arguments)]
fn send_dir<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    opts: &Options,
    features: u64,
    link: &CompressionLink,
    ids: &mut idmap::Sender,
    id: u32,
    parent_plus1: u32,
    pidx: u32,
    rel: &[u8],
    path: &Path,
    attrs: &Attrs,
    entries: Vec<SourceEntry>,
    flags: u8,
    dirs: &mut Vec<Option<SentDir>>,
    next_id: &mut u32,
    selection: Option<&scan::Selection>,
    filters: &crate::filter::FilterList,
) -> io::Result<()> {
    let entries: Vec<SourceEntry> = if selection.is_some() {
        entries
    } else {
        entries
            .into_iter()
            .filter(|entry| !filters.excluded(&scan::join_rel(rel, &entry.meta.name), entry.meta.kind == T_DIR))
            .collect()
    };
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
    if features & feature::DIR_CHILDREN != 0 {
        let count = if opts.recursive || selection.is_some() { child_specs.len() as u64 } else { 0 };
        body.var(count);
    }
    body.var(entries.len() as u64);
    for entry in &entries {
        protocol::put_entry(&mut body, &entry.meta, opts, features);
    }
    let mut frame = Encoder::new();
    frame.var(id as u64).var(parent_plus1 as u64).var(pidx as u64);
    let flag_at = frame.bytes.len();
    frame.byte(flags);
    let level = link.level(opts.compress_level_explicit, opts.compress_level, opts.bwlimit);
    if protocol::pack_body(&mut frame, &body.bytes, opts.compress, level) {
        frame.bytes[flag_at] |= protocol::DF_ZSTD;
        link.set_last_level(level);
        if !opts.compress_level_explicit {
            link.count(level, body.bytes.len() as u64);
        }
    }
    if let Some(map) = ids.describe(opts, features, attrs, &entries) {
        output.send(map.kind, &map.payload)?;
    }
    output.send(frame_type::DIR, &frame.bytes)?;
    if dirs.len() <= id as usize {
        dirs.resize_with(id as usize + 1, || None);
    }
    dirs[id as usize] = Some(SentDir { dest_entries: entries });
    if opts.recursive || selection.is_some() {
        for (index, child_path, child_attrs) in child_specs {
            let child_id = *next_id;
            *next_id += 1;
            let child_rel = scan::join_rel(rel, &dirs[id as usize].as_ref().unwrap().dest_entries[index].meta.name);
            let (child_entries, child_filter);
            if let Some(selection) = selection {
                child_entries = selection.dirs.get(&child_rel).map(|dir| dir.entries.clone()).unwrap_or_default();
                child_filter = crate::filter::FilterList::default();
            } else {
                child_filter = filters.in_directory(&child_path, false);
                child_entries = scan::scan_dir_filtered(&child_path, opts, &child_filter, &child_rel).unwrap_or_default();
            }
            send_dir(
                output,
                opts,
                features,
                link,
                ids,
                child_id,
                id + 1,
                index as u32,
                &child_rel,
                &child_path,
                &child_attrs,
                child_entries,
                protocol::DF_ATTRS,
                dirs,
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

fn flush_data<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    block: &mut Vec<u8>,
    compress: bool,
    link: &CompressionLink,
    opts: &Options,
) -> io::Result<()> {
    if block.is_empty() {
        return Ok(());
    }
    let digest = ffi::xxh3_64(block);
    let mut payload = Encoder::new();
    payload.byte(0).raw(&digest.to_le_bytes());
    let level = link.level(opts.compress_level_explicit, opts.compress_level, opts.bwlimit);
    let compressed = protocol::pack_body(&mut payload, block, compress, level);
    if compressed {
        payload.bytes[0] = 1;
        link.set_last_level(level);
        if !opts.compress_level_explicit {
            link.count(level, block.len() as u64);
        }
    }
    output.send(frame_type::DATA, &payload.bytes)?;
    block.clear();
    Ok(())
}

fn whole_record(id: u32, idx: u32, attrs: &Attrs, bytes: &[u8], features: u64) -> Encoder {
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::WHOLE);
    protocol::put_file_attrs(&mut e, attrs, features);
    e.str(bytes);
    e
}

fn fail_record(id: u32, idx: u32) -> Encoder {
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::FAIL);
    e
}

#[allow(clippy::too_many_arguments)]
fn send_large<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    id: u32,
    idx: u32,
    entry: &SourceEntry,
    features: u64,
    compress: bool,
    link: &CompressionLink,
    opts: &Options,
    block: &mut Vec<u8>,
    ranges: bool,
    offered: Option<&ResumePrefix>,
    resume: bool,
    delta: bool,
    eligible: bool,
    wait: &mut dyn FnMut(u32, u32) -> io::Result<Option<DeltaSignature>>,
) -> io::Result<()> {
    let planned = entry.meta.size.max(0) as u64;
    let mut prefix = if resume {
        offered
            .filter(|p| p.size <= planned as i64)
            .and_then(|p| crate::resume::source_prefix(&entry.path, p))
            .unwrap_or_default()
    } else {
        ResumePrefix::default()
    };
    if delta && eligible && prefix.is_empty() && planned > DELTA_THRESHOLD as u64 {
        flush_data(output, block, compress, link, opts)?;
        let mut request = Encoder::new();
        request.var(id as u64).var(idx as u64);
        output.send(frame_type::DELTA_REQUEST, &request.bytes)?;
        if let Some(signature) = wait(id, idx)? {
            return send_delta(output, id, idx, entry, features, compress, link, opts, block, &signature, planned);
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
                    flush_data(output, block, compress, link, opts)?;
                }
                Ok(())
            },
        )?;
        flush_data(output, block, compress, link, opts)?;
        let mut e = Encoder::new();
        e.var(id as u64).var(idx as u64).byte(rec::END);
        e.var(0);
        if resume {
            e.var(prefix.size.max(0) as u64);
        }
        e.var(planned).byte(if complete { 0 } else { 2 });
        protocol::put_file_attrs(&mut e, &entry.meta.attrs, features);
        record(e, block);
        return flush_data(output, block, compress, link, opts);
    }
    let mut file = match File::open(&entry.path) {
        Ok(file) => file,
        Err(_) => return flush_data(output, block, compress, link, opts),
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
            flush_data(output, block, compress, link, opts)?;
        }
        if failed {
            break;
        }
    }
    flush_data(output, block, compress, link, opts)?;
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::END);
    e.var(0);
    if resume {
        e.var(prefix.size.max(0) as u64);
    }
    let complete = !failed && offset == planned;
    e.var(offset).byte(if complete { 0 } else { 2 });
    protocol::put_file_attrs(&mut e, &entry.meta.attrs, features);
    record(e, block);
    flush_data(output, block, compress, link, opts)
}

/// `Sender::read_one`'s delta branch: one LITERAL or COPY record per emitted op,
/// then DELTA_END with the source digest.
#[allow(clippy::too_many_arguments)]
fn send_delta<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    id: u32,
    idx: u32,
    entry: &SourceEntry,
    features: u64,
    compress: bool,
    link: &CompressionLink,
    opts: &Options,
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
                flush_data(output, block, compress, link, opts)?;
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
    flush_data(output, block, compress, link, opts)?;
    let mut e = Encoder::new();
    e.var(id as u64).var(idx as u64).byte(rec::DELTA_END);
    e.var(0).var(processed.max(0) as u64).byte(status);
    protocol::put_file_attrs(&mut e, &entry.meta.attrs, features);
    e.raw(&sum[0].to_le_bytes()).raw(&sum[1].to_le_bytes());
    record(e, block);
    flush_data(output, block, compress, link, opts)
}

#[allow(clippy::too_many_arguments)]
fn send_need_data<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    id: u32,
    indices: &[u32],
    dir: &SentDir,
    features: u64,
    link: &CompressionLink,
    opts: &Options,
    suffixes: &Suffixes,
    prefixes: &HashMap<u32, ResumePrefix>,
    resume: bool,
    delta: bool,
    eligible: &[bool],
    wait: &mut dyn FnMut(u32, u32) -> io::Result<Option<DeltaSignature>>,
) -> io::Result<()> {
    // `parallel_file_ranges`: split only when an explicit -jN asked for it and
    // the NEED does not already offer several large files as parallel work.
    let large = indices
        .iter()
        .filter(|&&idx| {
            dir.dest_entries
                .get(idx as usize)
                .map(|entry| entry.meta.kind == T_REG && entry.meta.size >= crate::parallel::RANGE_MIN as i64)
                .unwrap_or(false)
        })
        .count();
    let ranges = crate::parallel::explicit_ranges(opts.jobs) && large <= 1;
    let mut block = Vec::with_capacity(protocol::BLOCK_TARGET);
    let mut block_skip = false;
    for (position, &idx) in indices.iter().enumerate() {
        let Some(entry) = dir.dest_entries.get(idx as usize) else {
            return bad("protocol error: bad NEED index");
        };
        if entry.meta.kind != T_REG {
            continue;
        }
        // A skipped suffix gets a block of its own, as `RawFileBlock` isolates it.
        let skip = opts.compress && suffixes.matches(&entry.meta.name);
        if skip || skip != block_skip {
            flush_data(output, &mut block, opts.compress && !block_skip, link, opts)?;
        }
        block_skip = skip;
        if entry.meta.size <= protocol::SMALL_MAX as i64 {
            match fs::read(&entry.path) {
                Ok(bytes) => {
                    record(whole_record(id, idx, &entry.meta.attrs, &bytes, features), &mut block);
                    if block.len() >= protocol::BLOCK_TARGET {
                        flush_data(output, &mut block, opts.compress && !block_skip, link, opts)?;
                    }
                }
                Err(_) => {
                    record(fail_record(id, idx), &mut block);
                }
            }
        } else {
            flush_data(output, &mut block, opts.compress && !block_skip, link, opts)?;
            send_large(
                output,
                id,
                idx,
                entry,
                features,
                opts.compress && !skip,
                link,
                opts,
                &mut block,
                ranges,
                prefixes.get(&idx),
                resume,
                delta,
                eligible.get(position).copied().unwrap_or(false),
                wait,
            )?;
        }
        if skip {
            flush_data(output, &mut block, false, link, opts)?;
        }
    }
    flush_data(output, &mut block, opts.compress && !block_skip, link, opts)
}

/// Read until the reply to one F_DELTA_REQUEST. Any other frame is kept for the
/// main loop, because the C++ receiver pipelines NEEDs from other directories.
fn wait_signature<R: Read>(
    input: &mut R,
    pending: &mut VecDeque<Frame>,
    keepalive: bool,
    features: u64,
    id: u32,
    idx: u32,
) -> io::Result<Option<DeltaSignature>> {
    loop {
        let Some(frame) = protocol::read_checked(input, keepalive, features)? else {
            return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "receiver closed before its delta signature"));
        };
        match frame.kind {
            frame_type::DELTA_SIGNATURE => {
                let (reply_id, reply_idx, signature) = crate::delta::decode_signature(&frame.payload, features)?;
                if reply_id != id || reply_idx != idx {
                    return bad("protocol error: unsolicited delta reply");
                }
                return Ok(signature);
            }
            frame_type::NEED | frame_type::OUTPUT | frame_type::PROGRESS | frame_type::IDMAP => {
                pending.push_back(frame);
            }
            frame_type::MSG => {
                if let Some(code) = msg_code(&frame)? {
                    return Err(io::Error::other(format!("receiver exited with status {code}")));
                }
            }
            other => return bad(format!("protocol error: unexpected frame {other} before a delta reply")),
        }
    }
}

/// Sender: wait for the receiver's F_DEST, send every listing, then answer each
/// NEED with DATA and finish with LIST_END, DATA_END and the receiver's DONE.
pub fn run_sender<R: Read, W: Write + Send + 'static>(
    input: &mut R,
    output: W,
    opts: &Options,
    features: u64,
    sources: &[OsString],
    control: Arc<IoControl>,
    mut local_output: Option<&mut Output>,
) -> io::Result<i32> {
    let link = Arc::new(CompressionLink::new());
    let mut output = FrameOut::new(output, Some(link.clone()), control);
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
    let empty = Attrs::default();
    let attrs = root.attrs.clone().unwrap_or(empty);
    let mut flags = if root.attrs.is_some() { protocol::DF_ATTRS } else { 0 };
    if root.single {
        flags |= protocol::DF_SINGLE;
    }
    let suffixes = crate::compression::suffixes(&opts.skip_compress);
    let resume = opts.partial && features & feature::RESUME != 0;
    let delta = features & feature::DELTA != 0;
    let mut ids = idmap::Sender::default();
    let mut dirs: Vec<Option<SentDir>> = Vec::new();
    let mut next_id = 1u32;
    send_dir(
        &mut output,
        opts,
        features,
        &link,
        &mut ids,
        0,
        0,
        0,
        b"",
        &root.base,
        &attrs,
        root.entries,
        flags,
        &mut dirs,
        &mut next_id,
        root.selection.as_ref(),
        &root_filters,
    )?;
    let dir_count = dirs.len() as u32;
    output.send(frame_type::LIST_END, &[])?;

    let mut needs = 0u32;
    let mut pending: VecDeque<Frame> = VecDeque::new();
    loop {
        let frame = match pending.pop_front() {
            Some(frame) => frame,
            None => {
                let Some(frame) = protocol::read_checked(input, keepalive, features)? else {
                    return Ok(12);
                };
                frame
            }
        };
        let action: io::Result<Option<i32>> = (|| {
            match frame.kind {
                frame_type::OUTPUT => {
                    if features & feature::OUTPUT == 0 {
                        return bad("file output without negotiated support");
                    }
                    let event = OutputEvent::decode(&frame.payload, features).map_err(decode_err)?;
                    if let Some(local) = local_output.as_deref_mut() {
                        local.push(event);
                    }
                    Ok(None)
                }
                frame_type::PROGRESS => {
                    ProgressAck::decode(&frame.payload, features).map_err(|_| {
                        io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed progress acknowledgment")
                    })?;
                    Ok(None)
                }
                frame_type::NEED => {
                    let mut d = Decoder::new(&frame.payload);
                    let id = u32::try_from(d.var().map_err(decode_err)?)
                        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED id"))?;
                    let count = usize::try_from(d.var().map_err(decode_err)?)
                        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED count"))?;
                    let mut indices = Vec::with_capacity(count);
                    let mut offered = Vec::with_capacity(count);
                    let mut eligible = Vec::with_capacity(count);
                    let mut previous = 0u32;
                    for i in 0..count {
                        let difference = u32::try_from(d.var().map_err(decode_err)?)
                            .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED index"))?;
                        if i > 0 && difference == 0 {
                            return bad("protocol error: bad NEED index");
                        }
                        previous = previous
                            .checked_add(difference)
                            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "bad NEED index"))?;
                        indices.push(previous);
                        offered.push(if resume { ResumePrefix::get(&mut d).map_err(decode_err)? } else { ResumePrefix::default() });
                        eligible.push(if delta {
                            let value = d.byte().map_err(decode_err)?;
                            if value > 1 {
                                return bad("protocol error: bad delta candidate");
                            }
                            value != 0
                        } else {
                            false
                        });
                    }
                    if !d.is_empty() {
                        return bad("protocol error: trailing NEED payload");
                    }
                    let dir = dirs
                        .get_mut(id as usize)
                        .and_then(Option::take)
                        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad NEED directory"))?;
                    let mut prefixes = HashMap::new();
                    for (position, (&idx, prefix)) in indices.iter().zip(&offered).enumerate() {
                        let entry = dir
                            .dest_entries
                            .get(idx as usize)
                            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad NEED index"))?;
                        if prefix.size > entry.meta.size {
                            return bad("protocol error: bad resume prefix");
                        }
                        if eligible[position] && entry.meta.kind != T_REG {
                            return bad("protocol error: bad delta candidate");
                        }
                        if !prefix.is_empty() {
                            prefixes.insert(idx, *prefix);
                        }
                    }
                    send_need_data(
                        &mut output,
                        id,
                        &indices,
                        &dir,
                        features,
                        &link,
                        opts,
                        &suffixes,
                        &prefixes,
                        resume,
                        delta,
                        &eligible,
                        &mut |id, idx| wait_signature(input, &mut pending, keepalive, features, id, idx),
                    )?;
                    needs += 1;
                    if needs == dir_count {
                        let mut end = Encoder::new();
                        end.var(0);
                        output.send(frame_type::DATA_END, &end.bytes)?;
                    }
                    Ok(None)
                }
                frame_type::DONE => {
                    let mut d = Decoder::new(&frame.payload);
                    let code = i32::try_from(d.var().map_err(decode_err)?).unwrap_or(0);
                    Ok(Some(code))
                }
                frame_type::MSG => Ok(msg_code(&frame)?),
                frame_type::IDMAP => Ok(None),
                other => bad(format!("protocol error: unexpected frame {other} from receiver")),
            }
        })();
        match action {
            Ok(Some(code)) => {
                output.finish()?;
                return Ok(code);
            }
            Ok(None) => {}
            Err(error) => {
                eprintln!("xs-rs: {error}");
                let _ = send_fatal(&mut output, &error.to_string());
                output.finish()?;
                return Ok(2);
            }
        }
    }
}

mod file;
mod hardlink;
mod receiver;

pub use receiver::run_receiver;
