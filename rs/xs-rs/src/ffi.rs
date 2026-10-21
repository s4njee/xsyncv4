//! The few system calls the standard library does not expose: XXH3-64, one-shot zstd,
//! nanosecond timestamps on symlinks, and FIFO creation, for Linux and macOS.

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::io;
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

#[repr(C)]
struct Timespec {
    tv_sec: i64,
    tv_nsec: i64,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct Xxh128 {
    low64: u64,
    high64: u64,
}

#[cfg(target_os = "linux")]
const AT_FDCWD: c_int = -100;
#[cfg(target_os = "linux")]
const AT_SYMLINK_NOFOLLOW: c_int = 0x100;
#[cfg(target_os = "linux")]
const UTIME_OMIT: i64 = (1 << 30) - 2;
#[cfg(target_os = "macos")]
const AT_FDCWD: c_int = -2;
#[cfg(target_os = "macos")]
const AT_SYMLINK_NOFOLLOW: c_int = 0x20;
#[cfg(target_os = "macos")]
const UTIME_OMIT: i64 = -2;
// Linux's values are the same on x86-64 and arm64; O_EXCL with O_CREAT never follows a symlink.
const O_WRONLY: c_int = 1;
#[cfg(target_os = "linux")]
const O_CREAT: c_int = 0o100;
#[cfg(target_os = "linux")]
const O_EXCL: c_int = 0o200;
#[cfg(target_os = "linux")]
const O_CLOEXEC: c_int = 0o2000000;
#[cfg(target_os = "linux")]
const RLIMIT_NOFILE: c_int = 7;
#[cfg(target_os = "macos")]
const O_CREAT: c_int = 0x200;
#[cfg(target_os = "macos")]
const O_EXCL: c_int = 0x800;
#[cfg(target_os = "macos")]
const O_CLOEXEC: c_int = 0x0100_0000;
#[cfg(target_os = "macos")]
const RLIMIT_NOFILE: c_int = 8;
#[cfg(target_os = "linux")]
type ModeT = u32;
#[cfg(target_os = "macos")]
type ModeT = u16;

#[repr(C)]
struct Rlimit {
    current: u64,
    maximum: u64,
}

#[repr(C)]
struct Passwd {
    pw_name: *mut c_char,
    pw_passwd: *mut c_char,
    pw_uid: u32,
    pw_gid: u32,
    pw_gecos: *mut c_char,
    pw_dir: *mut c_char,
    pw_shell: *mut c_char,
}

#[repr(C)]
struct Group {
    gr_name: *mut c_char,
    gr_passwd: *mut c_char,
    gr_gid: u32,
    gr_mem: *mut *mut c_char,
}

const NO_ID: u32 = u32::MAX;

extern "C" {
    fn getpwuid(uid: u32) -> *mut Passwd;
    fn getgrgid(gid: u32) -> *mut Group;
    fn getpwnam(name: *const c_char) -> *mut Passwd;
    fn getgrnam(name: *const c_char) -> *mut Group;
    fn geteuid() -> u32;
    fn getegid() -> u32;
    fn getgroups(size: c_int, list: *mut u32) -> c_int;
    fn chown(path: *const c_char, owner: u32, group: u32) -> c_int;
    fn lchown(path: *const c_char, owner: u32, group: u32) -> c_int;
    fn fchown(fd: c_int, owner: u32, group: u32) -> c_int;
    fn openat(dirfd: c_int, pathname: *const c_char, flags: c_int, ...) -> c_int;
    fn renameat(olddirfd: c_int, oldpath: *const c_char, newdirfd: c_int, newpath: *const c_char) -> c_int;
    fn unlinkat(dirfd: c_int, pathname: *const c_char, flags: c_int) -> c_int;
    fn futimens(fd: c_int, times: *const Timespec) -> c_int;
    fn umask(mask: ModeT) -> ModeT;
    fn getrlimit(resource: c_int, limit: *mut Rlimit) -> c_int;
    fn setrlimit(resource: c_int, limit: *const Rlimit) -> c_int;
    fn XXH3_64bits(input: *const c_void, length: usize) -> u64;
    fn XXH3_createState() -> *mut c_void;
    fn XXH3_freeState(state: *mut c_void) -> c_int;
    fn XXH3_128bits_reset(state: *mut c_void) -> c_int;
    fn XXH3_128bits_update(state: *mut c_void, input: *const c_void, length: usize) -> c_int;
    fn XXH3_128bits_digest(state: *const c_void) -> Xxh128;
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(dst: *mut c_void, dst_capacity: usize, src: *const c_void, src_size: usize, level: c_int) -> usize;
    fn ZSTD_decompress(dst: *mut c_void, dst_capacity: usize, src: *const c_void, compressed_size: usize) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
    fn ZSTD_minCLevel() -> c_int;
    fn ZSTD_maxCLevel() -> c_int;
    fn utimensat(dirfd: c_int, pathname: *const c_char, times: *const Timespec, flags: c_int) -> c_int;
    fn mkfifo(pathname: *const c_char, mode: u32) -> c_int;
    fn localtime_r(timep: *const i64, result: *mut Tm) -> *mut Tm;
    fn strftime(s: *mut c_char, max: usize, format: *const c_char, tm: *const Tm) -> usize;
}

#[repr(C)]
struct Tm {
    tm_sec: c_int,
    tm_min: c_int,
    tm_hour: c_int,
    tm_mday: c_int,
    tm_mon: c_int,
    tm_year: c_int,
    tm_wday: c_int,
    tm_yday: c_int,
    tm_isdst: c_int,
    tm_gmtoff: i64,
    tm_zone: *const c_char,
}

/// `render`'s `%t`: local time as `%Y/%m/%d %H:%M:%S`, or `?` when it is not representable.
pub fn local_time(seconds: i64) -> String {
    let mut tm = Tm {
        tm_sec: 0,
        tm_min: 0,
        tm_hour: 0,
        tm_mday: 0,
        tm_mon: 0,
        tm_year: 0,
        tm_wday: 0,
        tm_yday: 0,
        tm_isdst: 0,
        tm_gmtoff: 0,
        tm_zone: std::ptr::null(),
    };
    let format = CString::new("%Y/%m/%d %H:%M:%S").unwrap();
    let mut buffer = [0 as c_char; 64];
    // SAFETY: the seconds pointer, tm and format are valid for the call; `localtime_r`
    // copies into our storage and returns null when the value is out of range.
    unsafe {
        if localtime_r(&seconds, &mut tm).is_null() {
            return "?".into();
        }
        let n = strftime(buffer.as_mut_ptr(), buffer.len(), format.as_ptr(), &tm);
        if n == 0 {
            "?".into()
        } else {
            let bytes: Vec<u8> = buffer[..n].iter().map(|byte| byte.to_ne_bytes()[0]).collect();
            String::from_utf8_lossy(&bytes).into_owned()
        }
    }
}

pub fn xxh3_64(bytes: &[u8]) -> u64 {
    // SAFETY: the pointer and length describe a live slice for the call.
    unsafe { XXH3_64bits(bytes.as_ptr().cast(), bytes.len()) }
}

/// Incremental XXH3-128, the hash `hash_prefix_fd` computes over a resume prefix.
pub struct Xxh3_128 {
    state: *mut c_void,
}

impl Xxh3_128 {
    pub fn new() -> io::Result<Self> {
        // SAFETY: createState allocates the opaque state; we free it on drop.
        let state = unsafe { XXH3_createState() };
        if state.is_null() {
            return Err(io::Error::other("cannot allocate an XXH3-128 state"));
        }
        let hash = Self { state };
        // SAFETY: the state came from createState and is live.
        if unsafe { XXH3_128bits_reset(hash.state) } != 0 {
            return Err(io::Error::other("cannot reset an XXH3-128 state"));
        }
        Ok(hash)
    }

    pub fn update(&mut self, bytes: &[u8]) -> io::Result<()> {
        // SAFETY: the state is live and the slice describes readable bytes.
        let code = unsafe { XXH3_128bits_update(self.state, bytes.as_ptr().cast(), bytes.len()) };
        if code == 0 {
            Ok(())
        } else {
            Err(io::Error::other("XXH3-128 update failed"))
        }
    }

    pub fn digest(&self) -> [u64; 2] {
        // SAFETY: digest only reads the live state.
        let hash = unsafe { XXH3_128bits_digest(self.state) };
        [hash.low64, hash.high64]
    }
}

impl Drop for Xxh3_128 {
    fn drop(&mut self) {
        // SAFETY: the state was allocated by createState and has not been freed.
        unsafe { XXH3_freeState(self.state) };
    }
}

/// The levels this libzstd accepts, `ZSTD_minCLevel` to `ZSTD_maxCLevel`.
pub fn zstd_level_bounds() -> (i32, i32) {
    // SAFETY: both are constant queries with no arguments.
    unsafe { (ZSTD_minCLevel(), ZSTD_maxCLevel()) }
}

/// One zstd frame, whatever its size, as `ZSTD_compressCCtx` writes it for `level`.
pub fn zstd_compress_exact(raw: &[u8], level: i32) -> io::Result<Vec<u8>> {
    // SAFETY: the capacity is the library's own bound and both buffers are live.
    unsafe {
        let bound = ZSTD_compressBound(raw.len());
        let mut out = vec![0u8; bound];
        let n = ZSTD_compress(out.as_mut_ptr().cast(), bound, raw.as_ptr().cast(), raw.len(), level);
        if ZSTD_isError(n) != 0 {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "zstd compression failed"));
        }
        out.truncate(n);
        Ok(out)
    }
}

pub fn zstd_decompress(src: &[u8], raw_len: usize) -> io::Result<Vec<u8>> {
    let mut out = vec![0u8; raw_len];
    // SAFETY: `out` has exactly `raw_len` bytes, which is the advertised size.
    let n = unsafe { ZSTD_decompress(out.as_mut_ptr().cast(), raw_len, src.as_ptr().cast(), src.len()) };
    if n == raw_len && unsafe { ZSTD_isError(n) } == 0 {
        Ok(out)
    } else {
        Err(io::Error::new(io::ErrorKind::InvalidData, "zstd frame did not decompress to its advertised size"))
    }
}

fn c_path(path: &Path) -> io::Result<CString> {
    CString::new(path.as_os_str().as_bytes()).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "path contains NUL"))
}

/// Set the modification time (and leave the access time alone), optionally without
/// following a final symlink, with nanoseconds.
pub fn set_mtime(path: &Path, sec: i64, nsec: i64, nofollow: bool) -> io::Result<()> {
    let path = c_path(path)?;
    let times = [Timespec { tv_sec: 0, tv_nsec: UTIME_OMIT }, Timespec { tv_sec: sec, tv_nsec: nsec.clamp(0, 999_999_999) }];
    let flags = if nofollow { AT_SYMLINK_NOFOLLOW } else { 0 };
    // SAFETY: both pointers are valid for the duration of the call.
    let rc = unsafe { utimensat(AT_FDCWD, path.as_ptr(), times.as_ptr(), flags) };
    if rc == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

pub fn make_fifo(path: &Path, mode: u32) -> io::Result<()> {
    let path = c_path(path)?;
    // SAFETY: the C string is NUL terminated and lives through the call.
    let rc = unsafe { mkfifo(path.as_ptr(), mode & 0o7777) };
    if rc == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

fn name_ptr(ptr: *mut c_char) -> Option<Vec<u8>> {
    if ptr.is_null() {
        return None;
    }
    // SAFETY: libc returned a NUL-terminated string that lives until the next lookup.
    Some(unsafe { CStr::from_ptr(ptr) }.to_bytes().to_vec())
}

/// `getpwuid`: the name the sender puts in an `F_IDMAP` record.
pub fn user_name(id: u32) -> Option<Vec<u8>> {
    // SAFETY: getpwuid returns either null or a pointer to static passwd storage.
    let entry = unsafe { getpwuid(id) };
    if entry.is_null() {
        None
    } else {
        // SAFETY: the pointer is non-null and owned by libc.
        name_ptr(unsafe { (*entry).pw_name })
    }
}

/// `getgrgid`: the group name the sender puts in an `F_IDMAP` record.
pub fn group_name(id: u32) -> Option<Vec<u8>> {
    // SAFETY: getgrgid returns either null or a pointer to static group storage.
    let entry = unsafe { getgrgid(id) };
    if entry.is_null() {
        None
    } else {
        // SAFETY: the pointer is non-null and owned by libc.
        name_ptr(unsafe { (*entry).gr_name })
    }
}

/// `getpwnam`: the local id the receiver learns from a name.
pub fn user_id(name: &[u8]) -> Option<u32> {
    let name = CString::new(name).ok()?;
    // SAFETY: the name is NUL terminated and lives for the call; the result is static.
    let entry = unsafe { getpwnam(name.as_ptr()) };
    if entry.is_null() {
        None
    } else {
        // SAFETY: the pointer is non-null and owned by libc.
        Some(unsafe { (*entry).pw_uid })
    }
}

/// `getgrnam`: the local id the receiver learns from a name.
pub fn group_id(name: &[u8]) -> Option<u32> {
    let name = CString::new(name).ok()?;
    // SAFETY: the name is NUL terminated and lives for the call; the result is static.
    let entry = unsafe { getgrnam(name.as_ptr()) };
    if entry.is_null() {
        None
    } else {
        // SAFETY: the pointer is non-null and owned by libc.
        Some(unsafe { (*entry).gr_gid })
    }
}

/// This process's ids and groups, looked up once, as `init_ids` in fs.cpp.
struct Ids {
    uid: u32,
    gid: u32,
    groups: Vec<u32>,
}

fn ids() -> &'static Ids {
    static IDS: std::sync::OnceLock<Ids> = std::sync::OnceLock::new();
    IDS.get_or_init(|| {
        // SAFETY: geteuid, getegid and getgroups are simple process queries.
        unsafe {
            let mut groups = Vec::new();
            let count = getgroups(0, std::ptr::null_mut());
            if count > 0 {
                groups.resize(count as usize, 0);
                let got = getgroups(count, groups.as_mut_ptr());
                groups.truncate(got.max(0) as usize);
            }
            Ids { uid: geteuid(), gid: getegid(), groups }
        }
    })
}

pub fn is_root() -> bool {
    ids().uid == 0
}

pub fn effective_uid() -> u32 {
    ids().uid
}

pub fn effective_gid() -> u32 {
    ids().gid
}

/// Whether this process may switch a file to `gid`, as `can_set_gid` in fs.cpp.
pub fn can_set_gid(gid: u32) -> bool {
    let ids = ids();
    ids.uid == 0 || gid == ids.gid || ids.groups.contains(&gid)
}

/// The process umask, read once.
pub fn current_umask() -> u32 {
    static UMASK: std::sync::OnceLock<u32> = std::sync::OnceLock::new();
    *UMASK.get_or_init(|| {
        // SAFETY: umask cannot fail; the old mask is put straight back.
        unsafe {
            let old = umask(0o077);
            umask(old);
            #[allow(clippy::useless_conversion)] // mode_t is u16 on macOS
            let old = u32::from(old);
            old & 0o777
        }
    })
}

/// Raise the open-file limit toward its hard limit and return the limit now in force,
/// so destination directories can stay open while their files are written.
pub fn raise_open_files() -> u64 {
    let mut limit = Rlimit { current: 0, maximum: 0 };
    // SAFETY: the struct is valid for writing.
    if unsafe { getrlimit(RLIMIT_NOFILE, &mut limit) } != 0 {
        return 256;
    }
    // macOS refuses a soft limit above kern.maxfilesperproc: halve until one is taken.
    let mut want = limit.maximum.min(1 << 20);
    while want > limit.current {
        let next = Rlimit { current: want, maximum: limit.maximum };
        // SAFETY: the struct is valid for reading.
        if unsafe { setrlimit(RLIMIT_NOFILE, &next) } == 0 {
            return want;
        }
        want /= 2;
    }
    limit.current
}

fn c_name(name: &[u8]) -> io::Result<CString> {
    CString::new(name).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "name contains NUL"))
}

/// Create `name` in the directory `dir` for writing; it must not exist (a symlink counts).
pub fn create_at(dir: &std::fs::File, name: &[u8], mode: u32) -> io::Result<std::fs::File> {
    use std::os::unix::io::{AsRawFd, FromRawFd};
    let name = c_name(name)?;
    // SAFETY: the name is NUL terminated; the mode goes through the variadic slot as an unsigned int.
    let fd = unsafe {
        openat(dir.as_raw_fd(), name.as_ptr(), O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, (mode & 0o7777) as std::ffi::c_uint)
    };
    if fd < 0 {
        return Err(io::Error::last_os_error());
    }
    // SAFETY: openat returned a new descriptor that nothing else owns.
    Ok(unsafe { std::fs::File::from_raw_fd(fd) })
}

/// Rename within one directory.
pub fn rename_at(dir: &std::fs::File, from: &[u8], to: &[u8]) -> io::Result<()> {
    use std::os::unix::io::AsRawFd;
    let (from, to) = (c_name(from)?, c_name(to)?);
    // SAFETY: both names are NUL terminated and live through the call.
    if unsafe { renameat(dir.as_raw_fd(), from.as_ptr(), dir.as_raw_fd(), to.as_ptr()) } == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

pub fn unlink_at(dir: &std::fs::File, name: &[u8]) -> io::Result<()> {
    use std::os::unix::io::AsRawFd;
    let name = c_name(name)?;
    // SAFETY: the name is NUL terminated and lives through the call.
    if unsafe { unlinkat(dir.as_raw_fd(), name.as_ptr(), 0) } == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

/// Set an open file's modification time with nanoseconds, leaving its access time alone.
pub fn set_file_mtime(file: &std::fs::File, sec: i64, nsec: i64) -> io::Result<()> {
    use std::os::unix::io::AsRawFd;
    let times = [Timespec { tv_sec: 0, tv_nsec: UTIME_OMIT }, Timespec { tv_sec: sec, tv_nsec: nsec.clamp(0, 999_999_999) }];
    // SAFETY: the descriptor is live and the array holds two timespecs.
    if unsafe { futimens(file.as_raw_fd(), times.as_ptr()) } == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

/// Change the owner or group of an open file, leaving the other one alone.
pub fn fchown_fd(fd: c_int, uid: Option<u32>, gid: Option<u32>) -> io::Result<()> {
    // SAFETY: fd is a live descriptor; -1 (NO_ID) tells the kernel to leave that id alone.
    let rc = unsafe { fchown(fd, uid.unwrap_or(NO_ID), gid.unwrap_or(NO_ID)) };
    if rc == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

/// Change the owner or group of a path, optionally without following a symlink.
pub fn chown_path(path: &Path, uid: Option<u32>, gid: Option<u32>, nofollow: bool) -> io::Result<()> {
    let path = c_path(path)?;
    // SAFETY: the C string is NUL terminated and lives through the call.
    let rc = unsafe {
        let owner = uid.unwrap_or(NO_ID);
        let group = gid.unwrap_or(NO_ID);
        if nofollow {
            lchown(path.as_ptr(), owner, group)
        } else {
            chown(path.as_ptr(), owner, group)
        }
    };
    if rc == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_zstd_frame_is_the_one_the_cpp_reference_writes() {
        // Hex from ZSTD_compressCCtx on the parent's libzstd, level 3, for this input.
        let raw = b"xs zstd compressor test\n".repeat(20);
        let expected = [
            0x28, 0xb5, 0x2f, 0xfd, 0x60, 0xe0, 0x00, 0xfd, 0x00, 0x00, 0xc0, 0x78, 0x73, 0x20, 0x7a, 0x73, 0x74, 0x64,
            0x20, 0x63, 0x6f, 0x6d, 0x70, 0x72, 0x65, 0x73, 0x73, 0x6f, 0x72, 0x20, 0x74, 0x65, 0x73, 0x74, 0x0a, 0x01,
            0x00, 0x14, 0xaf, 0x3a, 0xc7,
        ];
        assert_eq!(zstd_compress_exact(&raw, 3).unwrap(), expected);
        assert_eq!(zstd_decompress(&expected, raw.len()).unwrap(), raw);
    }

    #[test]
    fn the_resume_hash_is_xxh3_128_as_the_cpp_computes_it() {
        let mut hash = Xxh3_128::new().unwrap();
        assert_eq!(hash.digest(), [0x6001_c324_468d_497f, 0x99aa_06d3_0147_98d8]);
        hash.update(b"a").unwrap();
        hash.update(b"bc").unwrap();
        assert_eq!(hash.digest(), [0x78af_5f94_892f_3950, 0x06b0_5ab6_733a_6185]);
    }

    #[test]
    fn the_level_bounds_come_from_the_library() {
        let (minimum, maximum) = zstd_level_bounds();
        assert!(minimum <= -5 && maximum >= 22);
    }
}
