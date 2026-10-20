//! The two engines: a sender that walks and streams DIR/NEED/DATA, and a receiver
//! that compares, asks for differences, and publishes files. One reader and one
//! writer per side; the stream stays pipelined because listings go first.

use std::collections::hash_map::Entry;
use std::collections::{BTreeMap, HashMap};
use std::ffi::{OsStr, OsString};
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufWriter, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileExt, FileTypeExt, MetadataExt, OpenOptionsExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Sender, TryRecvError};
use std::sync::{Arc, OnceLock};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use xs_wire::io_control::IoControl;
use xs_wire::{Decoder, Encoder, Frame, Suffixes};

use crate::compression::{CompressionLink, Transport};
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, msg_kind, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK,
    T_REG,
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
) -> io::Result<()> {
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
        let count = if opts.recursive { child_specs.len() as u64 } else { 0 };
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
    if opts.recursive {
        for (index, child_path, child_attrs) in child_specs {
            let child_id = *next_id;
            *next_id += 1;
            let child_rel = scan::join_rel(rel, &dirs[id as usize].as_ref().unwrap().dest_entries[index].meta.name);
            let child_entries = scan::scan_dir(&child_path, opts).unwrap_or_default();
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
) -> io::Result<()> {
    let mut file = match File::open(&entry.path) {
        Ok(file) => file,
        Err(_) => return flush_data(output, block, compress, link, opts),
    };
    let planned = entry.meta.size.max(0) as u64;
    let mut buffer = vec![0u8; protocol::BLOCK_TARGET];
    let mut offset = 0u64;
    let mut failed = false;
    loop {
        let want = (planned - offset).min(buffer.len() as u64) as usize;
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
            break;
        }
        let mut e = Encoder::new();
        e.var(id as u64).var(idx as u64).byte(rec::CHUNK);
        e.var(0).var(offset).var(planned);
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
    e.var(0).var(offset).byte(if failed { 2 } else { 0 });
    protocol::put_file_attrs(&mut e, &entry.meta.attrs, features);
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
) -> io::Result<()> {
    let mut block = Vec::with_capacity(protocol::BLOCK_TARGET);
    let mut block_skip = false;
    for &idx in indices {
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
            send_large(output, id, idx, entry, features, opts.compress && !skip, link, opts, &mut block)?;
        }
        if skip {
            flush_data(output, &mut block, false, link, opts)?;
        }
    }
    flush_data(output, &mut block, opts.compress && !block_skip, link, opts)
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
    let root = scan::build_root(sources, opts)?;
    let empty = Attrs::default();
    let attrs = root.attrs.clone().unwrap_or(empty);
    let mut flags = if root.attrs.is_some() { protocol::DF_ATTRS } else { 0 };
    if root.single {
        flags |= protocol::DF_SINGLE;
    }
    let suffixes = crate::compression::suffixes(&opts.skip_compress);
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
    )?;
    let dir_count = dirs.len() as u32;
    output.send(frame_type::LIST_END, &[])?;

    let mut needs = 0u32;
    loop {
        let Some(frame) = protocol::read_checked(input, keepalive, features)? else {
            return Ok(12);
        };
        match frame.kind {
            frame_type::OUTPUT => {
                if features & feature::OUTPUT == 0 {
                    return bad("file output without negotiated support");
                }
                let event = OutputEvent::decode(&frame.payload, features).map_err(decode_err)?;
                if let Some(local) = local_output.as_deref_mut() {
                    local.push(event);
                }
            }
            frame_type::PROGRESS => {
                ProgressAck::decode(&frame.payload, features)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed progress acknowledgment"))?;
            }
            frame_type::NEED => {
                let mut d = Decoder::new(&frame.payload);
                let id = u32::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED id"))?;
                let count = usize::try_from(d.var().map_err(decode_err)?)
                    .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "bad NEED count"))?;
                let mut indices = Vec::with_capacity(count);
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
                }
                if !d.is_empty() {
                    return bad("protocol error: trailing NEED payload");
                }
                let dir = dirs
                    .get_mut(id as usize)
                    .and_then(Option::take)
                    .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad NEED directory"))?;
                send_need_data(&mut output, id, &indices, &dir, features, &link, opts, &suffixes)?;
                needs += 1;
                if needs == dir_count {
                    let mut end = Encoder::new();
                    end.var(0);
                    output.send(frame_type::DATA_END, &end.bytes)?;
                }
            }
            frame_type::DONE => {
                let mut d = Decoder::new(&frame.payload);
                let code = i32::try_from(d.var().map_err(decode_err)?).unwrap_or(0);
                output.finish()?;
                return Ok(code);
            }
            frame_type::MSG => {
                if let Some(code) = msg_code(&frame)? {
                    return Ok(code);
                }
            }
            frame_type::IDMAP => {}
            other => return bad(format!("protocol error: unexpected frame {other} from receiver")),
        }
    }
}

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
    need: std::collections::HashSet<u32>,
    existing: Vec<Option<fs::Metadata>>,
    dir_created: Vec<bool>,
}

struct InFile {
    temp: PathBuf,
    file: File,
    final_path: PathBuf,
    ranges: Vec<(i64, i64)>,
    total: Option<i64>,
    attrs: Option<Attrs>,
    status: Option<u8>,
    finished: bool,
}

fn add_range(ranges: &mut Vec<(i64, i64)>, start: i64, end: i64) {
    let mut merged_start = start;
    let mut merged_end = end;
    ranges.retain(|&(a, b)| {
        if b < merged_start || a > merged_end {
            true
        } else {
            merged_start = merged_start.min(a);
            merged_end = merged_end.max(b);
            false
        }
    });
    ranges.push((merged_start, merged_end));
    ranges.sort_unstable();
}

fn covered(ranges: &[(i64, i64)], total: i64) -> bool {
    let mut position = 0i64;
    for &(start, end) in ranges {
        if start > position {
            return false;
        }
        if end > position {
            position = end;
        }
    }
    position >= total
}

fn create_temp(dir: &Path, name: &[u8]) -> io::Result<(PathBuf, File)> {
    for attempt in 0..100u64 {
        let mut tmp = b".".to_vec();
        let keep = name.len().min(240);
        tmp.extend_from_slice(&name[..keep]);
        tmp.push(b'.');
        let mut value = std::process::id() as u64 * 31 + attempt;
        for _ in 0..6 {
            let alphabet = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
            tmp.push(alphabet[(value % 62) as usize]);
            value /= 62;
        }
        let path = dir.join(OsString::from_vec(tmp));
        match OpenOptions::new().read(true).write(true).create_new(true).mode(0o600).open(&path) {
            Ok(file) => return Ok((path, file)),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    }
    Err(io::Error::new(io::ErrorKind::AlreadyExists, "cannot create a temporary file"))
}

fn remove_any(path: &Path) -> io::Result<()> {
    match fs::symlink_metadata(path) {
        Ok(metadata) => {
            if metadata.is_dir() {
                fs::remove_dir_all(path)
            } else {
                fs::remove_file(path)
            }
        }
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error),
    }
}

fn set_dir_working_mode(path: &Path) {
    if let Ok(metadata) = fs::metadata(path) {
        let mode = metadata.permissions().mode() & 0o7777;
        if mode & 0o300 != 0o300 {
            let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode | 0o700));
        }
    }
}

fn finish_infile(infile: &mut InFile, opts: &Options) -> io::Result<bool> {
    let Some(total) = infile.total else { return Ok(false) };
    if infile.status != Some(0) || !covered(&infile.ranges, total) {
        return Ok(false);
    }
    infile.finished = true;
    infile.file.set_len(total as u64)?;
    let attrs = infile.attrs.clone().unwrap_or_default();
    idmap::chown_file(&infile.file, opts, &attrs);
    if opts.perms {
        let _ = infile.file.set_permissions(fs::Permissions::from_mode(attrs.mode & 0o7777));
    }
    if opts.times {
        let _ = ffi::set_mtime(&infile.temp, attrs.mtime, attrs.mtime_ns as i64, false);
    }
    match fs::rename(&infile.temp, &infile.final_path) {
        Ok(()) => Ok(true),
        Err(error) => {
            let _ = fs::remove_file(&infile.temp);
            Err(error)
        }
    }
}

fn write_whole(path_dir: &Path, name: &[u8], final_path: &Path, attrs: &Attrs, bytes: &[u8], opts: &Options) -> io::Result<()> {
    let (temp, mut file) = create_temp(path_dir, name)?;
    let result = (|| {
        file.write_all(bytes)?;
        file.set_len(bytes.len() as u64)?;
        idmap::chown_file(&file, opts, attrs);
        if opts.perms {
            file.set_permissions(fs::Permissions::from_mode(attrs.mode & 0o7777))?;
        }
        if opts.times {
            let _ = ffi::set_mtime(&temp, attrs.mtime, attrs.mtime_ns as i64, false);
        }
        drop(file);
        fs::rename(&temp, final_path)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp);
    }
    result
}

fn make_dir(path: &Path, mode: u32) -> io::Result<bool> {
    match fs::create_dir(path) {
        Ok(()) => {
            let _ = fs::set_permissions(path, fs::Permissions::from_mode((mode & 0o7777) | 0o700));
            Ok(true)
        }
        Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
            set_dir_working_mode(path);
            Ok(false)
        }
        Err(error) => Err(error),
    }
}

fn destination_listing(path: &Path) -> BTreeMap<Vec<u8>, fs::Metadata> {
    let mut map = BTreeMap::new();
    if let Ok(items) = fs::read_dir(path) {
        for item in items.flatten() {
            if let Ok(metadata) = fs::symlink_metadata(item.path()) {
                map.insert(item.file_name().as_bytes().to_vec(), metadata);
            }
        }
    }
    map
}

#[allow(clippy::too_many_arguments)]
fn process_dir<R: Read, W: Write + Send + 'static>(
    _input: &mut R,
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
                    if let Some(before) = existing {
                        if let Some(code) = metadata_code(opts, T_REG, before, entry) {
                            let event = taken_event(&code, &event_path, &entry.output_source, T_REG, entry.size, 0);
                            report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                        }
                    }
                } else {
                    if let Some(m) = existing {
                        if !m.is_file() {
                            remove_any(&target)?;
                        }
                    }
                    need.push(index as u32);
                }
            }
            T_LNK => {
                let same = existing
                    .and_then(|m| if m.file_type().is_symlink() { fs::read_link(&target).ok() } else { None })
                    .map(|p| p.as_os_str().as_bytes() == entry.link.as_slice())
                    .unwrap_or(false);
                if !same {
                    remove_any(&target)?;
                    std::os::unix::fs::symlink(OsStr::from_bytes(&entry.link), &target)?;
                    *created_links += 1;
                    let event =
                        taken_event(b"cL+++++++++", &event_path, &entry.output_source, T_LNK, entry.size, 0);
                    report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_LNK, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, T_LNK, entry.size, 0);
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                    }
                }
                if opts.times {
                    let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, true);
                }
                idmap::chown_path(&target, opts, &entry.attrs, true);
            }
            T_FIFO => {
                let same = existing.map(|m| m.file_type().is_fifo()).unwrap_or(false);
                if !same {
                    remove_any(&target)?;
                    ffi::make_fifo(&target, entry.attrs.mode)?;
                    let event = taken_event(b"cS+++++++++", &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                    report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                } else if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, T_FIFO, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, T_FIFO, entry.size, 0);
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                    }
                }
                if opts.times {
                    let _ = ffi::set_mtime(&target, entry.attrs.mtime, entry.attrs.mtime_ns as i64, false);
                }
                idmap::chown_path(&target, opts, &entry.attrs, false);
            }
            T_CHR | T_BLK => {
                if let Some(before) = existing {
                    if let Some(code) = metadata_code(opts, entry.kind, before, entry) {
                        let event = taken_event(&code, &event_path, &entry.output_source, entry.kind, entry.size, 0);
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
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

#[allow(clippy::too_many_arguments)]
fn process_data<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    payload: &[u8],
    opts: &Options,
    features: u64,
    ids: &idmap::Receiver,
    dirs: &mut [Option<RecvDir>],
    infiles: &mut HashMap<(u32, u32, u32), InFile>,
    created_files: &mut u64,
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
                report_event(output, local_output.as_deref_mut(), features, opts, event)?;
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
                        let name = dir.rename_to.as_deref().unwrap_or(&entry.name);
                        let final_path = dir.dest.join(OsStr::from_bytes(name));
                        let (temp, file) = create_temp(&dir.dest, name)?;
                        vacant.insert(InFile {
                            temp,
                            file,
                            final_path,
                            ranges: Vec::new(),
                            total: Some(total),
                            attrs: None,
                            status: None,
                            finished: false,
                        })
                    }
                };
                if infile.total != Some(total) {
                    return bad("protocol error: inconsistent file size");
                }
                infile.file.write_all_at(bytes, offset as u64)?;
                add_range(&mut infile.ranges, offset, offset + bytes.len() as i64);
                added_bytes += bytes.len() as u64;
                if infile.status == Some(0) && finish_infile(infile, opts)? {
                    *created_files += 1;
                    added_files += 1;
                    let total = infile.total.unwrap_or(0);
                    infiles.remove(&key);
                    dir.need.remove(&idx);
                    let code = transferred_code(opts, before.as_ref(), &entry);
                    let event = taken_event(&code, &event_path, &event_source, T_REG, total, total);
                    report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                }
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
                        let name = dir.rename_to.as_deref().unwrap_or(&entry.name);
                        let final_path = dir.dest.join(OsStr::from_bytes(name));
                        let (temp, file) = create_temp(&dir.dest, name)?;
                        vacant.insert(InFile {
                            temp,
                            file,
                            final_path,
                            ranges: Vec::new(),
                            total: Some(total),
                            attrs: None,
                            status: None,
                            finished: false,
                        })
                    }
                };
                infile.total = Some(total);
                infile.attrs = Some(attrs);
                infile.status = Some(status);
                if status == 2 {
                    let _ = fs::remove_file(&infile.temp);
                    infiles.remove(&key);
                    dir.need.remove(&idx);
                } else if status == 0 {
                    if finish_infile(infile, opts)? {
                        *created_files += 1;
                        added_files += 1;
                        infiles.remove(&key);
                        dir.need.remove(&idx);
                        let code = transferred_code(opts, before.as_ref(), &entry);
                        let event = taken_event(&code, &event_path, &event_source, T_REG, total, total);
                        report_event(output, local_output.as_deref_mut(), features, opts, event)?;
                    }
                } else {
                    let _ = fs::remove_file(&infile.temp);
                    infiles.remove(&key);
                    dir.need.remove(&idx);
                }
            }
            rec::FAIL => {
                dir.need.remove(&idx);
            }
            _ => return bad("protocol error: unknown DATA record"),
        }
    }
    Ok((added_bytes, added_files))
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
                input,
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
                &mut created_files,
                local_output.as_deref_mut(),
            ) {
                Ok((bytes, files)) => {
                    progress_bytes += bytes;
                    progress_files += files;
                    progress_ack(&mut output, features, progress_bytes, progress_files, false, &mut progress_last)
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
    for (_, infile) in infiles.drain() {
        if !infile.finished {
            let _ = fs::remove_file(&infile.temp);
        }
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
