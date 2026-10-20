//! Destination and source resume prefixes: the checks `destination_resume_prefix`,
//! `hash_prefix_fd`, `source_unchanged` and `out_restore_prefix` make in src/fs.cpp.

use std::fs::{self, File, Metadata, OpenOptions};
use std::io::{self, Read};
use std::os::unix::fs::{FileExt, MetadataExt, OpenOptionsExt};
use std::path::Path;

use xs_wire::resume::ResumePrefix;

use crate::ffi::Xxh3_128;

const O_NOFOLLOW: i32 = 0o400000;
const O_NONBLOCK: i32 = 0o4000;
const PREFIX_BUFFER: usize = 256 * 1024;

fn open_destination(path: &Path) -> io::Result<File> {
    OpenOptions::new().read(true).custom_flags(O_NOFOLLOW | O_NONBLOCK).open(path)
}

/// Hash exactly `size` bytes from the start. A short read is an error, as
/// `hash_prefix_fd` treats a zero-length read as EIO.
pub fn hash_prefix(file: &mut File, size: i64) -> io::Result<[u64; 2]> {
    if size < 0 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "negative resume prefix"));
    }
    let mut hash = Xxh3_128::new()?;
    let mut buffer = vec![0u8; PREFIX_BUFFER];
    let mut left = size as u64;
    while left > 0 {
        let want = buffer.len().min(left as usize);
        let count = file.read(&mut buffer[..want])?;
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "source ended inside a resume prefix"));
        }
        hash.update(&buffer[..count])?;
        left -= count as u64;
    }
    Ok(hash.digest())
}

fn revision(metadata: &Metadata) -> (u64, u64, i64, i64, i64, i64, i64) {
    (metadata.dev(), metadata.ino(), metadata.size() as i64, metadata.mtime(), metadata.mtime_nsec(), metadata.ctime(), metadata.ctime_nsec())
}

fn source_unchanged(file: &File, path: &Path, before: &Metadata) -> bool {
    let Ok(after) = file.metadata() else { return false };
    let Ok(named) = fs::metadata(path) else { return false };
    let expected = revision(before);
    after.is_file() && named.is_file() && revision(&after) == expected && revision(&named) == expected
}

/// `destination_resume_prefix`: the existing destination prefix and its hash, or
/// an empty prefix when the file is missing, empty, not regular, changed while
/// it was read, or longer than the source.
pub fn destination_prefix(path: &Path, limit: i64) -> ResumePrefix {
    if limit <= 0 {
        return ResumePrefix::default();
    }
    let Ok(mut file) = open_destination(path) else { return ResumePrefix::default() };
    let Ok(before) = file.metadata() else { return ResumePrefix::default() };
    if !before.is_file() || before.size() == 0 {
        return ResumePrefix::default();
    }
    let size = (before.size() as i64).min(limit);
    let Ok(sum) = hash_prefix(&mut file, size) else { return ResumePrefix::default() };
    if !source_unchanged(&file, path, &before) {
        return ResumePrefix::default();
    }
    ResumePrefix { size, sum }
}

/// The sender's check in `Sender::read_one`: the offered bytes must still hash
/// the same in the source file.
pub fn source_prefix(path: &Path, offered: &ResumePrefix) -> Option<ResumePrefix> {
    if offered.size <= 0 {
        return None;
    }
    let mut file = File::open(path).ok()?;
    if file.metadata().ok()?.size() < offered.size as u64 {
        return None;
    }
    let sum = hash_prefix(&mut file, offered.size).ok()?;
    (sum == offered.sum).then_some(*offered)
}

/// `out_restore_prefix`: copy the offered destination prefix into the temporary
/// output only after the bytes still hash to the value NEED advertised.
pub fn restore_prefix(output: &File, path: &Path, prefix: &ResumePrefix) -> io::Result<()> {
    if prefix.size <= 0 {
        return Ok(());
    }
    let mut file = open_destination(path)?;
    let before = file.metadata()?;
    if !before.is_file() || before.size() < prefix.size as u64 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "destination prefix disappeared"));
    }
    let mut hash = Xxh3_128::new()?;
    let mut buffer = vec![0u8; PREFIX_BUFFER];
    let mut offset = 0i64;
    while offset < prefix.size {
        let want = buffer.len().min((prefix.size - offset) as usize);
        let count = file.read(&mut buffer[..want])?;
        if count == 0 {
            return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "destination ended inside a resume prefix"));
        }
        hash.update(&buffer[..count])?;
        output.write_all_at(&buffer[..count], offset as u64)?;
        offset += count as i64;
    }
    if hash.digest() != prefix.sum || !source_unchanged(&file, path, &before) {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "destination prefix changed"));
    }
    Ok(())
}
