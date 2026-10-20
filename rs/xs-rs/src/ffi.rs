//! The few system calls the standard library does not expose: XXH3-64, one-shot zstd,
//! nanosecond timestamps on symlinks, and FIFO creation. Linux only, as the case asks.

use std::ffi::{c_char, c_int, c_void, CString};
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

extern "C" {
    fn XXH3_64bits(input: *const c_void, length: usize) -> u64;
    fn ZSTD_compressBound(src_size: usize) -> usize;
    fn ZSTD_compress(dst: *mut c_void, dst_capacity: usize, src: *const c_void, src_size: usize, level: c_int) -> usize;
    fn ZSTD_decompress(dst: *mut c_void, dst_capacity: usize, src: *const c_void, compressed_size: usize) -> usize;
    fn ZSTD_isError(code: usize) -> u32;
    fn utimensat(dirfd: c_int, pathname: *const c_char, times: *const Timespec, flags: c_int) -> c_int;
    fn mkfifo(pathname: *const c_char, mode: u32) -> c_int;
}

pub fn xxh3_64(bytes: &[u8]) -> u64 {
    // SAFETY: the pointer and length describe a live slice for the call.
    unsafe { XXH3_64bits(bytes.as_ptr().cast(), bytes.len()) }
}

/// One-shot zstd, as `ZSTD_compressCCtx` does for each frame. Returns None when
/// the compressed form is not smaller, so callers write the raw payload.
pub fn zstd_compress(raw: &[u8], level: i32) -> Option<Vec<u8>> {
    // SAFETY: the capacity is the library's own bound and both buffers are live.
    unsafe {
        let bound = ZSTD_compressBound(raw.len());
        let mut out = vec![0u8; bound];
        let n = ZSTD_compress(out.as_mut_ptr().cast(), bound, raw.as_ptr().cast(), raw.len(), level);
        if ZSTD_isError(n) != 0 || n >= raw.len() {
            return None;
        }
        out.truncate(n);
        Some(out)
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
