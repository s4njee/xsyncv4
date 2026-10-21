//! The receiver engine: compare DIR listings, request missing entries with NEED,
//! write DATA records, then apply deferred directory metadata and send DONE.

use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet, VecDeque};
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileExt, PermissionsExt};
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::time::Instant;

use xs_wire::io_control::IoControl;
use xs_wire::resume::ResumePrefix;
use xs_wire::{Decoder, Encoder, Frame, OutputEvent};

use crate::acls;
use crate::delta;
use crate::ffi;
use crate::idmap;
use crate::output::Output;
use crate::protocol::{
    self, bad, decode_err, feature, frame_type, rec, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_FIFO, T_LNK, T_REG,
};
use crate::resume;
use crate::scan;
use crate::xattr;

use crate::parallel::{WriteDone, WritePool};

use super::file::{
    add_range, contiguous, covered_from, create_temp, destination_listing, finish_infile, make_dir, remove_any,
    reserve_chunk, set_dir_working_mode_with, write_whole, DestDir, InFile, Stat,
};
use super::hardlink::{finalize_hardlinks, hardlink_member, HardLinks};
use super::{
    directory_event, metadata_code, msg_code, progress_ack, send_fatal, taken_event, transferred_code, FrameOut,
    FrameTx,
};

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

/// A DIR frame as the reader decodes it, in wire order, so xattr values and id maps apply
/// as they arrived; a worker does the rest (`Receiver::gen`).
struct ParsedDir {
    id: u32,
    parent_plus1: u32,
    pidx: u32,
    flags: u8,
    rel: Vec<u8>,
    attrs: Attrs,
    attr_source: Vec<u8>,
    entries: Vec<EntryMeta>,
}

/// Directories whose generator has run, and directories waiting for their parent's.
#[derive(Default)]
struct DirTable {
    dirs: Vec<Option<RecvDir>>,
    waiting: HashMap<u32, Vec<ParsedDir>>,
}

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

struct DataState {
    infiles: HashMap<(u32, u32, u32), InFile>,
    pool: WritePool,
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

/// What a queued DATA frame is charged: a compressed frame its raw size, as the reader's
/// bound counts work, not bytes on the wire.
fn data_charge(payload: &[u8]) -> usize {
    if payload.len() > 9 && payload[0] & 1 != 0 {
        if let Ok(size) = Decoder::new(&payload[9..]).var() {
            return (size as usize).min(1 << 30) + 9;
        }
    }
    payload.len()
}

/// One DATA frame on a worker: decompress and check it with no lock held, then apply its
/// records in order.
fn data_job(r: &Receiving, payload: Vec<u8>) -> io::Result<()> {
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
fn decode_data(payload: Vec<u8>, features: u64) -> io::Result<(Arc<Vec<u8>>, usize)> {
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
fn write_job(r: &Receiving, job: WholeJob) -> io::Result<()> {
    let bytes = &job.records[job.bytes.clone()];
    write_whole(&job.dir, &job.name, &job.final_path, &job.attrs, bytes, r.opts)?;
    r.created_files.fetch_add(1, Ordering::Relaxed);
    r.emit_or_defer(job.link_key.as_ref(), &job.event_path, job.event)
}

struct FinalDir {
    path: PathBuf,
    attrs: Attrs,
    apply: bool,
    /// What already matches and needs no syscall in the final pass (`mode_ok`, `time_ok`, fs.cpp).
    mode_ok: bool,
    time_ok: bool,
    owner_ok: bool,
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

struct RecvDir {
    rel: Vec<u8>,
    dest: PathBuf,
    entries: Vec<EntryMeta>,
    rename_to: Option<Vec<u8>>,
    need: HashSet<u32>,
    existing: Vec<Option<Stat>>,
    dir_created: Vec<bool>,
    prefixes: HashMap<u32, ResumePrefix>,
    delta_candidates: HashSet<u32>,
    delta_requested: HashSet<u32>,
    bases: HashMap<u32, Arc<delta::DeltaBasis>>,
    /// The directory, open while files it needs are still to come.
    out: Option<Arc<DestDir>>,
}

impl RecvDir {
    /// A needed entry has arrived (or failed): once none is left, let the directory go.
    fn received(&mut self, idx: u32) {
        self.need.remove(&idx);
        if self.need.is_empty() {
            self.out = None;
        }
    }
}

/// Decode a DIR frame on the reader: its xattr values and id maps apply in wire order.
fn parse_dir(
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
fn generate(r: &Receiving, dir: ParsedDir) -> io::Result<()> {
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

fn data_prefix(d: &mut Decoder<'_>) -> io::Result<ResumePrefix> {
    let size = i64::try_from(d.var().map_err(decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad resume prefix"))?;
    Ok(ResumePrefix { size, ..ResumePrefix::default() })
}

fn open_infile(
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
fn process_delta_request(
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
fn process_data(
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
fn finish_ready(
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

fn drain_writes(
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
