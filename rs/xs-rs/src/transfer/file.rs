//! Destination files: temporary names, partial writes and their coverage, atomic
//! publication, directory creation, and the before/after listing used to compare.

use std::collections::BTreeMap;
use std::ffi::OsString;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{DirBuilderExt, MetadataExt, OpenOptionsExt, PermissionsExt};
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::OnceLock;

use crate::acls;
use crate::ffi;
use crate::idmap;
use crate::protocol::{Attrs, EntryMeta, HardlinkKey, Options};
use crate::xattr;

pub(super) struct InFile {
    pub(super) temp: PathBuf,
    pub(super) file: File,
    pub(super) final_path: PathBuf,
    pub(super) ranges: Vec<(i64, i64)>,
    pub(super) total: Option<i64>,
    pub(super) attrs: Option<Attrs>,
    pub(super) status: Option<u8>,
    pub(super) finished: bool,
    /// Ranges handed to the write pool but not yet completed.
    pub(super) pending: usize,
    /// Everything the completion event needs once the last write returns.
    pub(super) entry: EntryMeta,
    pub(super) before: Option<fs::Metadata>,
    pub(super) event_path: Vec<u8>,
    pub(super) link_key: Option<HardlinkKey>,
    /// The verified destination prefix restored into the temporary output.
    pub(super) prefix: i64,
    pub(super) prefix_ok: bool,
    /// Incoming chunk ranges reserved before their writes finish, for overlap checks.
    pub(super) chunks: BTreeMap<i64, i64>,
    /// This attempt carries LITERAL/COPY records and a DELTA_END digest.
    pub(super) delta: bool,
    pub(super) delta_sum: [u64; 2],
    /// A basis block or temp write failed; the attempt drains but never publishes.
    pub(super) ok: bool,
}

pub(super) fn add_range(ranges: &mut Vec<(i64, i64)>, start: i64, end: i64) {
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

pub(super) fn covered_from(ranges: &[(i64, i64)], prefix: i64, total: i64) -> bool {
    let mut position = prefix;
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

/// The bytes to keep from a partly transferred file: the contiguous run from zero.
pub(super) fn contiguous(ranges: &[(i64, i64)], total: i64) -> i64 {
    let mut position = 0i64;
    for &(start, end) in ranges {
        if start > position {
            break;
        }
        if end > position {
            position = end;
        }
    }
    position.min(total)
}

/// Reserve a chunk before its write is queued. The C++ `std::map<i64,i64>`
/// rejects any overlap, including one that arrives in the same DATA frame.
pub(super) fn reserve_chunk(chunks: &mut BTreeMap<i64, i64>, start: i64, end: i64) -> bool {
    if start >= end {
        return false;
    }
    if let Some((_, &previous_end)) = chunks.range(..=start).next_back() {
        if previous_end > start {
            return false;
        }
    }
    if let Some((&next_start, _)) = chunks.range(start..).next() {
        if next_start < end {
            return false;
        }
    }
    chunks.insert(start, end);
    true
}

/// `.name.XXXXXX`, the temporary name a file is written under before it is renamed into place.
fn temp_name(name: &[u8], attempt: u64) -> Vec<u8> {
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
    tmp
}

/// Destination directories held open at once, and how many may be: half the open-file
/// limit, raised to its hard limit first, as `RLIMIT_NOFILE` allows.
static OPEN_DIRS: AtomicUsize = AtomicUsize::new(0);

fn open_dir_budget() -> usize {
    static BUDGET: OnceLock<usize> = OnceLock::new();
    *BUDGET.get_or_init(|| (ffi::raise_open_files() / 2).min(1 << 16) as usize)
}

/// A destination directory held open while its files are written, so each one is created,
/// timed and renamed relative to it instead of by walking its path again. Past the budget,
/// or when the directory cannot be opened, files fall back to paths.
pub(super) struct DestDir {
    pub(super) path: PathBuf,
    fd: Option<File>,
    /// The group a file created here gets: the directory's on macOS, or on Linux when it is
    /// setgid, ours otherwise (`need_dgid`, fs.cpp). A file already in that group needs no fchown.
    new_gid: Option<u32>,
}

impl DestDir {
    pub(super) fn open(path: &Path) -> Self {
        let mut dir = Self::by_path(path);
        if OPEN_DIRS.fetch_add(1, Ordering::Relaxed) < open_dir_budget() {
            if let Ok(fd) = File::open(path) {
                dir.new_gid = fd.metadata().ok().map(|metadata| {
                    if cfg!(target_os = "macos") || metadata.mode() & 0o2000 != 0 {
                        metadata.gid()
                    } else {
                        ffi::effective_gid()
                    }
                });
                dir.fd = Some(fd);
                return dir;
            }
        }
        OPEN_DIRS.fetch_sub(1, Ordering::Relaxed);
        dir
    }

    pub(super) fn by_path(path: &Path) -> Self {
        Self { path: path.to_path_buf(), fd: None, new_gid: None }
    }
}

impl Drop for DestDir {
    fn drop(&mut self) {
        if self.fd.is_some() {
            OPEN_DIRS.fetch_sub(1, Ordering::Relaxed);
        }
    }
}

pub(super) fn create_temp(dir: &Path, name: &[u8]) -> io::Result<(PathBuf, File)> {
    for attempt in 0..100u64 {
        let path = dir.join(OsString::from_vec(temp_name(name, attempt)));
        match OpenOptions::new().read(true).write(true).create_new(true).mode(0o600).open(&path) {
            Ok(file) => return Ok((path, file)),
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    }
    Err(io::Error::new(io::ErrorKind::AlreadyExists, "cannot create a temporary file"))
}

pub(super) fn remove_any(path: &Path) -> io::Result<()> {
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

pub(super) fn set_dir_working_mode_with(path: &Path, metadata: &fs::Metadata) -> bool {
    let mode = metadata.permissions().mode() & 0o7777;
    if mode & 0o300 != 0o300 {
        let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode | 0o700));
        true
    } else {
        false
    }
}

pub(super) fn set_dir_working_mode(path: &Path) -> bool {
    match fs::metadata(path) {
        Ok(metadata) => set_dir_working_mode_with(path, &metadata),
        Err(_) => false,
    }
}

pub(super) fn finish_infile(infile: &mut InFile, opts: &Options) -> io::Result<bool> {
    let Some(total) = infile.total else { return Ok(false) };
    if infile.status != Some(0) || !covered_from(&infile.ranges, infile.prefix, total) {
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
    if opts.xattrs != 0 {
        let _ = xattr::apply(&attrs.xattrs, &infile.temp, crate::protocol::T_REG, &opts.filters, opts);
    }
    if opts.acls {
        let _ = acls::apply(&attrs.acls, &infile.temp, crate::protocol::T_REG, attrs.mode, opts);
    }
    match fs::rename(&infile.temp, &infile.final_path) {
        Ok(()) => Ok(true),
        Err(error) => {
            let _ = fs::remove_file(&infile.temp);
            Err(error)
        }
    }
}

/// Write a small file under a temporary name in `dir` and rename it into place, with the
/// syscalls fs.cpp makes: create, write, fchown and fchmod only when they change something,
/// futimens, close, rename. No path is walked when the directory is open.
pub(super) fn write_whole(dir: &DestDir, name: &[u8], final_path: &Path, attrs: &Attrs, bytes: &[u8], opts: &Options) -> io::Result<()> {
    let Some(fd) = &dir.fd else {
        return write_whole_by_path(&dir.path, name, final_path, attrs, bytes, opts);
    };
    let created = if opts.perms { (attrs.mode & 0o7777) | 0o600 } else { 0o600 };
    let mut made = None;
    for attempt in 0..100u64 {
        let temp = temp_name(name, attempt);
        match ffi::create_at(fd, &temp, created) {
            Ok(file) => {
                made = Some((temp, file));
                break;
            }
            Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error),
        }
    }
    let Some((temp, mut file)) = made else {
        return Err(io::Error::new(io::ErrorKind::AlreadyExists, "cannot create a temporary file"));
    };
    let result = (|| {
        file.write_all(bytes)?;
        let uid = (opts.owner && ffi::is_root() && attrs.uid != ffi::effective_uid()).then_some(attrs.uid);
        let gid = (opts.group && ffi::can_set_gid(attrs.gid) && Some(attrs.gid) != dir.new_gid).then_some(attrs.gid);
        if uid.is_some() || gid.is_some() {
            let _ = ffi::fchown_fd(file.as_raw_fd(), uid, gid);
        }
        if opts.perms {
            // Set-id and sticky bits are always set explicitly: create may drop them, and so does fchown.
            let mode = attrs.mode & 0o7777;
            if mode & 0o7000 != 0 || created & 0o777 & !ffi::current_umask() != mode {
                file.set_permissions(fs::Permissions::from_mode(mode))?;
            }
        }
        if opts.times {
            let _ = ffi::set_file_mtime(&file, attrs.mtime, attrs.mtime_ns as i64);
        }
        if opts.xattrs != 0 || opts.acls {
            let temp_path = dir.path.join(OsString::from_vec(temp.clone()));
            if opts.xattrs != 0 {
                let _ = xattr::apply(&attrs.xattrs, &temp_path, crate::protocol::T_REG, &opts.filters, opts);
            }
            if opts.acls {
                let _ = acls::apply(&attrs.acls, &temp_path, crate::protocol::T_REG, attrs.mode, opts);
            }
        }
        drop(file);
        ffi::rename_at(fd, &temp, name)
    })();
    if result.is_err() {
        let _ = ffi::unlink_at(fd, &temp);
    }
    result
}

fn write_whole_by_path(path_dir: &Path, name: &[u8], final_path: &Path, attrs: &Attrs, bytes: &[u8], opts: &Options) -> io::Result<()> {
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
        if opts.xattrs != 0 {
            let _ = xattr::apply(&attrs.xattrs, &temp, crate::protocol::T_REG, &opts.filters, opts);
        }
        if opts.acls {
            let _ = acls::apply(&attrs.acls, &temp, crate::protocol::T_REG, attrs.mode, opts);
        }
        drop(file);
        fs::rename(&temp, final_path)
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp);
    }
    result
}

pub(super) fn make_dir(path: &Path, mode: u32) -> io::Result<bool> {
    let working = (mode & 0o7777) | 0o700;
    match fs::DirBuilder::new().mode(working).create(path) {
        Ok(()) => {
            // The final pass sets the real mode; until then only our own rwx matters, which
            // the umask rarely touches.
            if ffi::current_umask() & 0o700 != 0 {
                let _ = fs::set_permissions(path, fs::Permissions::from_mode(working));
            }
            Ok(true)
        }
        Err(error) if error.kind() == io::ErrorKind::AlreadyExists => {
            set_dir_working_mode(path);
            Ok(false)
        }
        Err(error) => Err(error),
    }
}

pub(super) fn destination_listing(path: &Path) -> BTreeMap<Vec<u8>, fs::Metadata> {
    let mut map = BTreeMap::new();
    if let Ok(items) = fs::read_dir(path) {
        for item in items.flatten() {
            // Not followed, and on Linux a statx relative to the directory's fd.
            if let Ok(metadata) = item.metadata() {
                map.insert(item.file_name().as_bytes().to_vec(), metadata);
            }
        }
    }
    map
}
