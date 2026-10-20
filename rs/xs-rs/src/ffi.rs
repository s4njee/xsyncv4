//! The few system calls the standard library does not expose: XXH3-64, one-shot zstd,
//! nanosecond timestamps on symlinks, and FIFO creation. Linux only, as the case asks.

use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::io;
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

#[repr(C)]
struct Timespec {
    tv_sec: i64,
    tv_nsec: i64,
}

const AT_FDCWD: c_int = -100;
const AT_SYMLINK_NOFOLLOW: c_int = 0x100;
const UTIME_OMIT: i64 = (1 << 30) - 2;

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
    fn XXH3_64bits(input: *const c_void, length: usize) -> u64;
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
    let mut buffer = [0i8; 64];
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
            let bytes: Vec<u8> = buffer[..n].iter().map(|&byte| byte as u8).collect();
            String::from_utf8_lossy(&bytes).into_owned()
        }
    }
}

pub fn xxh3_64(bytes: &[u8]) -> u64 {
    // SAFETY: the pointer and length describe a live slice for the call.
    unsafe { XXH3_64bits(bytes.as_ptr().cast(), bytes.len()) }
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

pub fn is_root() -> bool {
    // SAFETY: geteuid has no arguments and no failure mode.
    unsafe { geteuid() == 0 }
}

/// Whether this process may switch a file to `gid`, as `can_set_gid` in fs.cpp.
pub fn can_set_gid(gid: u32) -> bool {
    // SAFETY: getegid and getgroups are simple process queries.
    unsafe {
        if geteuid() == 0 || gid == getegid() {
            return true;
        }
        let count = getgroups(0, std::ptr::null_mut());
        if count <= 0 {
            return false;
        }
        let mut groups = vec![0u32; count as usize];
        let got = getgroups(count, groups.as_mut_ptr());
        got > 0 && groups[..got as usize].contains(&gid)
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
    fn the_level_bounds_come_from_the_library() {
        let (minimum, maximum) = zstd_level_bounds();
        assert!(minimum <= -5 && maximum >= 22);
    }
}
