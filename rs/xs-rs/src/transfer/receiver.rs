//! The receiver engine: compare DIR listings, request missing entries with NEED,
//! write DATA records, then apply deferred directory metadata and send DONE.

use std::collections::{HashMap, VecDeque};
use std::ffi::OsString;
use std::fs;
use std::io::{self, Read, Write};
use std::os::unix::ffi::OsStringExt;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::Instant;

use xs_wire::io_control::IoControl;
use xs_wire::{Decoder, Encoder, OutputEvent};

use crate::acls;
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{self, bad, decode_err, feature, frame_type, Attrs, Options, T_DIR};
use crate::xattr;

use crate::parallel::WritePool;

use super::file::DestDir;
use super::hardlink::{finalize_hardlinks, HardLinks};
use super::event::progress_ack;
use super::msg_code;
use super::outbox::{send_fatal, FrameOut, FrameTx};

mod data;
mod dir;

use data::{
    apply_write, cleanup_partial, data_charge, data_job, drain_writes, finish_ready, process_delta_request, settle,
    write_job, DataState,
};
use dir::{generate, parse_dir, DirTable, FinalDir, ParsedDir};

/// One small file (a WHOLE record) for a worker to write and publish.
struct WholeJob {
    dir: Arc<DestDir>,
    name: Vec<u8>,
    final_path: PathBuf,
    attrs: Attrs,
    /// The DATA frame's records, shared by the jobs it holds.
    records: Arc<Vec<u8>>,
    bytes: std::ops::Range<usize>,
    /// Reported once the file is in place.
    event: OutputEvent,
    event_path: Vec<u8>,
    link_key: Option<crate::protocol::HardlinkKey>,
}

impl WholeJob {
    /// What a queued job is charged: its bytes, and a page for the syscalls a file costs.
    fn charge(&self) -> usize {
        self.bytes.len() + 4096
    }
}

/// The receiver holds at most this much queued for its workers (`remote.cpp:2705`).
const QUEUE_MAX: usize = 16 << 20;
/// Past this much queued data, even the workers that prefer listings write files first
/// (`q1_soft_limit`, `remote.cpp:2707`).
const WRITES_FIRST: usize = 4 << 20;

// One per turn of a worker's loop, moved once: its size does not matter.
#[allow(clippy::large_enum_variant)]
enum Job {
    Generate(ParsedDir),
    Data(Vec<u8>, usize),
    Write(WholeJob),
}

/// The workers' two queues, as the C++ pool's: listings to compare (newest first, so the walk
/// goes deep before wide) and small files to write.
#[derive(Default)]
struct Lanes {
    dirs: VecDeque<ParsedDir>,
    /// DATA frames as they arrived, with what each is charged: its raw size (`t.charge`).
    frames: VecDeque<(Vec<u8>, usize)>,
    writes: VecDeque<WholeJob>,
    write_bytes: usize,
    active: usize,
    closed: bool,
}

/// What the frame reader and the receiver's workers share. The reader decodes frames and
/// queues work; workers compare listings, create what is missing, send NEEDs and write files.
/// No lock is held across a file's creation and publication.
struct Receiving<'a> {
    opts: &'a Options,
    features: u64,
    dest: &'a Path,
    tx: FrameTx,
    local: Mutex<Option<&'a mut Output>>,
    table: Mutex<DirTable>,
    finals: Mutex<Vec<FinalDir>>,
    hardlinks: Mutex<HardLinks>,
    created_files: AtomicU64,
    created_dirs: AtomicU64,
    created_links: AtomicU64,
    partial_failure: AtomicBool,
    lanes: Mutex<Lanes>,
    work: Condvar,
    settled: Condvar,
    /// The first worker failure, already sent to the sender as a fatal message.
    failed: Mutex<Option<i32>>,
    control: Arc<IoControl>,
    /// Decoding state the reader keeps and DATA records read: xattr values by stream id, and
    /// the sender's id map. (Locked after `data` and `table`.)
    streams: Mutex<xattr::Incoming>,
    ids: Mutex<idmap::Receiver>,
    /// Large files being assembled from chunks, and their write pool. (Locked before `table`.)
    data: Mutex<DataState>,
    progress_bytes: AtomicU64,
}


impl Receiving<'_> {
    /// Report one event: a server receiver sends `F_OUTPUT`; a client receiver renders it.
    fn emit(&self, event: OutputEvent) -> io::Result<()> {
        if self.opts.am_server {
            if self.features & feature::OUTPUT != 0 {
                self.tx.send(frame_type::OUTPUT, event.encode(self.features).payload)?;
            }
        } else if let Some(local) = self.local.lock().unwrap().as_deref_mut() {
            local.push(event);
        }
        Ok(())
    }

    /// A hard-link member's event waits for its group; any other is reported now.
    fn emit_or_defer(&self, link_key: Option<&crate::protocol::HardlinkKey>, path: &[u8], event: OutputEvent) -> io::Result<()> {
        match link_key {
            Some(key) => {
                self.hardlinks.lock().unwrap().defer_event(key, path, event);
                Ok(())
            }
            None => self.emit(event),
        }
    }

    fn queue_dir(&self, dir: ParsedDir) {
        self.lanes.lock().unwrap().dirs.push_back(dir);
        self.work.notify_one();
    }

    fn queue_write(&self, job: WholeJob) {
        {
            let mut lanes = self.lanes.lock().unwrap();
            lanes.write_bytes += job.charge();
            lanes.writes.push_back(job);
        }
        self.work.notify_one();
    }

    /// A DIR goes to the workers once its parent's generator has run (`p->waiters`).
    fn dir_arrived(&self, dir: ParsedDir) {
        if dir.parent_plus1 != 0 {
            let parent = dir.parent_plus1 - 1;
            let mut table = self.table.lock().unwrap();
            if table.dirs.get(parent as usize).is_none_or(Option::is_none) {
                table.waiting.entry(parent).or_default().push(dir);
                return;
            }
        }
        self.queue_dir(dir);
    }

    /// Wait until `done` holds for the queues, or a worker failed.
    fn wait_lanes(&self, done: impl Fn(&Lanes) -> bool) {
        let mut lanes = self.lanes.lock().unwrap();
        while !done(&lanes) && !lanes.closed {
            lanes = self.settled.wait(lanes).unwrap();
        }
    }

    fn idle(lanes: &Lanes) -> bool {
        lanes.dirs.is_empty() && lanes.frames.is_empty() && lanes.writes.is_empty() && lanes.active == 0
    }

    /// A DATA frame goes to the workers whole, as `K_DATA` does: they decompress, check and
    /// apply it, so a small receiver's reader only reads.
    fn queue_frame(&self, payload: Vec<u8>) {
        let charge = data_charge(&payload);
        {
            let mut lanes = self.lanes.lock().unwrap();
            lanes.write_bytes += charge;
            lanes.frames.push_back((payload, charge));
        }
        self.work.notify_one();
    }

    /// Stop the workers; queued work is dropped.
    fn close(&self) {
        {
            let mut lanes = self.lanes.lock().unwrap();
            lanes.closed = true;
            lanes.dirs.clear();
            lanes.frames.clear();
            lanes.writes.clear();
            lanes.write_bytes = 0;
        }
        self.work.notify_all();
        self.settled.notify_all();
    }

    /// The first failure ends the transfer with a fatal message to the sender.
    fn fail(&self, error: &io::Error) {
        let text = error.to_string();
        let code = if text.starts_with("rejecting ") { 4 } else { 2 };
        {
            let mut failed = self.failed.lock().unwrap();
            if failed.is_none() {
                *failed = Some(code);
                let message = xs_wire::Message { kind: protocol::msg_kind::FATAL, code: code as u64, text };
                let _ = self.tx.send(frame_type::MSG, message.encode());
            }
        }
        self.close();
        self.control.request_stop();
    }

    fn failure(&self) -> Option<i32> {
        *self.failed.lock().unwrap()
    }
}

/// A receiving worker: half of them prefer listings, the rest files (`scan_workers`).
fn receive_worker(r: &Receiving, prefers_dirs: bool) {
    loop {
        let job = {
            let mut lanes = r.lanes.lock().unwrap();
            loop {
                let dirs_first = prefers_dirs && lanes.write_bytes < WRITES_FIRST;
                let frame = |lanes: &mut Lanes| lanes.frames.pop_front().map(|(payload, charge)| Job::Data(payload, charge));
                let job = if dirs_first {
                    lanes
                        .dirs
                        .pop_back()
                        .map(Job::Generate)
                        .or_else(|| frame(&mut lanes))
                        .or_else(|| lanes.writes.pop_front().map(Job::Write))
                } else {
                    frame(&mut lanes)
                        .or_else(|| lanes.writes.pop_front().map(Job::Write))
                        .or_else(|| lanes.dirs.pop_back().map(Job::Generate))
                };
                if let Some(job) = job {
                    lanes.active += 1;
                    break job;
                }
                if lanes.closed {
                    return;
                }
                lanes = r.work.wait(lanes).unwrap();
            }
        };
        let (result, charge) = match job {
            Job::Generate(dir) => (generate(r, dir), 0),
            Job::Data(payload, charge) => (data_job(r, payload), charge),
            Job::Write(job) => {
                let charge = job.charge();
                (write_job(r, job), charge)
            }
        };
        {
            let mut lanes = r.lanes.lock().unwrap();
            lanes.active -= 1;
            lanes.write_bytes = lanes.write_bytes.saturating_sub(charge);
        }
        r.settled.notify_all();
        if let Err(error) = result {
            r.fail(&error);
        }
    }
}

/// Receiver: send F_DEST; the reader decodes the sender's frames while `-j` workers compare
/// listings (answering each with a NEED) and write small files, as `Receiver::run` does;
/// then apply deferred directory metadata and send DONE.
pub fn run_receiver<R: Read, W: Write + Send + 'static>(
    input: &mut R,
    output: W,
    opts: &Options,
    features: u64,
    dest: &[u8],
    control: Arc<IoControl>,
    local_output: Option<&mut Output>,
) -> io::Result<i32> {
    let mut output = FrameOut::new(output, None, control.clone());
    let keepalive = features & feature::IO_CONTROL != 0;
    let mut identity = Encoder::new();
    identity.str(b"").str(b"").var(0).var(0);
    output.send(frame_type::DEST, &identity.bytes)?;
    let dest_path = PathBuf::from(OsString::from_vec(dest.to_vec()));
    let r = Receiving {
        opts,
        features,
        dest: &dest_path,
        tx: output.tx(),
        local: Mutex::new(local_output),
        table: Mutex::new(DirTable::default()),
        finals: Mutex::new(Vec::new()),
        hardlinks: Mutex::new(HardLinks::new(opts.hard_links && features & feature::HLINK != 0)),
        created_files: AtomicU64::new(0),
        created_dirs: AtomicU64::new(0),
        created_links: AtomicU64::new(0),
        partial_failure: AtomicBool::new(false),
        lanes: Mutex::new(Lanes::default()),
        work: Condvar::new(),
        settled: Condvar::new(),
        failed: Mutex::new(None),
        control,
        streams: Mutex::new(xattr::Incoming::new()),
        ids: Mutex::new(idmap::Receiver::default()),
        // Like the C++ receiver, one file's ranges stay serial unless an explicit
        // -jN (N > 1) asked for range concurrency; the default budget is for files.
        data: Mutex::new(DataState {
            infiles: HashMap::new(),
            pool: WritePool::new(if crate::parallel::explicit_ranges(opts.jobs) {
                crate::parallel::effective_jobs(opts.jobs)
            } else {
                1
            }),
        }),
        progress_bytes: AtomicU64::new(0),
    };
    let jobs = crate::parallel::effective_jobs(opts.jobs);
    let received = std::thread::scope(|scope| {
        let r = &r;
        for worker in 0..jobs {
            // Half of them, at least one, prefer listings (`pool.scan_workers`).
            let prefers_dirs = worker < (jobs / 2).max(1);
            scope.spawn(move || receive_worker(r, prefers_dirs));
        }
        let received = receive(r, &mut output, input, keepalive);
        r.close();
        received
    });
    match received {
        Ok((code, true)) => {
            output.finish()?;
            Ok(code)
        }
        Ok((code, false)) => Ok(code),
        Err(error) => Err(error),
    }
}

/// The reader's side of a receive, and its end. Returns the exit code, and whether the
/// output should be finished cleanly.
fn receive<R: Read, W: Write + Send + 'static>(
    r: &Receiving,
    output: &mut FrameOut<W>,
    input: &mut R,
    keepalive: bool,
) -> io::Result<(i32, bool)> {
    let (opts, features) = (r.opts, r.features);
    let mut seen_dirs: Vec<bool> = Vec::new();
    // On every way out but the clean one, let large files' writes settle and keep or
    // remove what they left.
    let abandon = || {
        let mut data = r.data.lock().unwrap();
        let data = &mut *data;
        settle(&mut data.infiles, &data.pool);
        cleanup_partial(&mut data.infiles, opts);
    };
    let mut sender_code: Option<i32> = None;
    let mut ended = false;
    let ack_enabled = opts.am_server && features & feature::PROGRESS_ACK != 0;
    let mut progress_last = (0u64, 0u64, Instant::now());
    while !ended {
        let mut frame = match protocol::read_checked(input, keepalive, features) {
            Ok(Some(frame)) => frame,
            Ok(None) => {
                r.close();
                abandon();
                return Ok((r.failure().unwrap_or(12), false));
            }
            Err(error) => {
                // A worker's failure has been sent already; this read only stopped for it.
                let code = r.failure().unwrap_or_else(|| {
                    let _ = send_fatal(output, &error.to_string());
                    2
                });
                r.close();
                abandon();
                return Ok((code, false));
            }
        };
        let result = match frame.kind {
            frame_type::DIR => {
                let parsed = {
                    let mut streams = r.streams.lock().unwrap();
                    let ids = r.ids.lock().unwrap();
                    parse_dir(opts, features, &frame, &mut streams, &ids, &mut seen_dirs)
                };
                parsed.map(|dir| r.dir_arrived(dir))
            }
            frame_type::DATA => {
                r.queue_frame(std::mem::take(&mut frame.payload));
                Ok(())
            }
            frame_type::DELTA_REQUEST => {
                let mut table = r.table.lock().unwrap();
                process_delta_request(&r.tx, &frame.payload, opts, features, &mut table.dirs)
            }
            frame_type::XATTR_START | frame_type::XATTR_CHUNK | frame_type::XATTR_END => {
                if features & feature::XATTR_STREAM == 0 {
                    bad("protocol error: unnegotiated xattr value stream")
                } else {
                    r.streams.lock().unwrap().receive(frame.kind, &frame.payload)
                }
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
                    r.ids.lock().unwrap().learn(&frame.payload);
                    Ok(())
                }
            }
            frame_type::CHOWN_CONFIG => bad("protocol error: unnegotiated ownership configuration"),
            frame_type::MSG => match msg_code(&frame) {
                Ok(Some(code)) => return Ok((code, false)),
                Ok(None) => Ok(()),
                Err(error) => Err(error),
            },
            other => bad(format!("protocol error: unexpected frame {other} from sender")),
        };
        let result = result.and_then(|()| {
            if frame.kind == frame_type::DATA {
                let (bytes, files) = (r.progress_bytes.load(Ordering::Relaxed), r.created_files.load(Ordering::Relaxed));
                progress_ack(output, features, bytes, files, false, &mut progress_last)?;
                // Wait for the workers while too much is queued for them.
                r.wait_lanes(|lanes| lanes.write_bytes <= QUEUE_MAX);
            }
            Ok(())
        });
        if let Err(error) = result {
            r.fail(&error);
        }
        if let Some(code) = r.failure() {
            r.close();
            abandon();
            return Ok((code, false));
        }
    }
    // Every listing has been compared and every frame applied once the workers are idle.
    r.wait_lanes(Receiving::idle);
    if let Some(code) = r.failure() {
        abandon();
        return Ok((code, false));
    }
    let mut data = r.data.lock().unwrap();
    let DataState { infiles, pool } = &mut *data;
    if !r.streams.lock().unwrap().drained() {
        let _ = send_fatal(output, "protocol error: unreferenced xattr value stream");
        cleanup_partial(infiles, opts);
        return Ok((2, true));
    }
    let mut table = r.table.lock().unwrap();
    let table = &mut *table;
    // DATA_END may follow the last END while that file's range writes are still
    // in the pool; drain every completion before publishing or cleaning up.
    while infiles.values().any(|infile| infile.pending > 0) {
        let Some(done) = pool.recv_done() else {
            break;
        };
        if let Some(key) = apply_write(done, infiles)? {
            let finished = finish_ready(r, &mut table.dirs, infiles, key)?;
            r.created_files.fetch_add(finished, Ordering::Relaxed);
        }
    }
    let finished = drain_writes(r, &mut table.dirs, infiles, pool)?;
    r.created_files.fetch_add(finished, Ordering::Relaxed);
    let missing = !table.waiting.is_empty() || table.dirs.iter().flatten().any(|dir| !dir.need.is_empty());
    if !infiles.is_empty() || missing {
        let _ = send_fatal(output, "protocol error: incomplete file data");
        cleanup_partial(infiles, opts);
        return Ok((2, true));
    }
    cleanup_partial(infiles, opts);
    let mut created_files = r.created_files.load(Ordering::Relaxed);
    let mut hardlinks = r.hardlinks.lock().unwrap();
    if hardlinks.enabled {
        let local = r.local.lock().unwrap().take();
        finalize_hardlinks(&mut hardlinks, output, features, opts, &mut created_files, local)?;
    }
    // Deepest first, so setting a directory's times comes after every change inside it.
    let mut finals = std::mem::take(&mut *r.finals.lock().unwrap());
    finals.sort_by_key(|final_dir| std::cmp::Reverse(final_dir.path.components().count()));
    for final_dir in finals {
        if !final_dir.apply {
            continue;
        }
        // Only what differs: a directory already right costs no syscall, as in fs.cpp's final pass.
        if !final_dir.owner_ok {
            idmap::chown_path(&final_dir.path, opts, &final_dir.attrs, false);
        }
        let mode = final_dir.attrs.mode & 0o7777;
        if opts.perms && (!final_dir.mode_ok || (!final_dir.owner_ok && mode & 0o6000 != 0)) {
            let _ = fs::set_permissions(&final_dir.path, fs::Permissions::from_mode(mode));
        }
        if opts.times && !final_dir.time_ok {
            let _ = ffi::set_mtime(&final_dir.path, final_dir.attrs.mtime, final_dir.attrs.mtime_ns as i64, false);
        }
        if opts.xattrs != 0 {
            let _ = xattr::apply(&final_dir.attrs.xattrs, &final_dir.path, T_DIR, &opts.filters, opts);
        }
        if opts.acls {
            let _ = acls::apply(&final_dir.attrs.acls, &final_dir.path, T_DIR, final_dir.attrs.mode, opts);
        }
    }
    if ack_enabled {
        let bytes = r.progress_bytes.load(Ordering::Relaxed);
        progress_ack(output, features, bytes, created_files, true, &mut progress_last)?;
    }
    let sender_code = sender_code.unwrap_or(0);
    let partial_failure = r.partial_failure.load(Ordering::Relaxed);
    let code = if sender_code != 0 { sender_code } else if partial_failure { 23 } else { 0 };
    let mut done = Encoder::new();
    done.var(code as u64);
    done.var(created_files)
        .var(r.created_dirs.load(Ordering::Relaxed))
        .var(r.created_links.load(Ordering::Relaxed))
        .var(0)
        .var(0);
    output.send(frame_type::DONE, &done.bytes)?;
    Ok((code, true))
}
