//! PF_DELTA: destination signatures, streaming block matching, and the LITERAL,
//! COPY and DELTA_END records, as src/delta.cpp and src/remote.cpp write them.

use std::collections::{HashMap, HashSet};
use std::fs::{File, OpenOptions};
use std::io;
use std::os::unix::fs::{FileExt, MetadataExt, OpenOptionsExt};
use std::path::Path;

use xs_wire::{Decoder, Encoder};

use crate::ffi;
use crate::protocol::{self, feature};

pub const DELTA_THRESHOLD: i64 = 1 << 20;
pub const DELTA_MAX_BLOCK: u32 = 1 << 18;
pub const DELTA_MAX_BLOCKS: u32 = 1 << 22;
const READ_BUFFER: usize = 1 << 20;
const LITERAL_BUFFER: usize = 1 << 16;
const COPY_RUN: i64 = 8 << 20;
const O_NOFOLLOW: i32 = 0o400000;
const O_NONBLOCK: i32 = 0o4000;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct DeltaBlock {
    pub weak: u32,
    pub strong: u64,
}

#[derive(Clone, Debug, Default)]
pub struct DeltaSignature {
    pub size: i64,
    pub block_size: u32,
    pub blocks: Vec<DeltaBlock>,
}

impl DeltaSignature {
    pub fn valid(&self) -> bool {
        self.size > 0
            && (1024..=DELTA_MAX_BLOCK).contains(&self.block_size)
            && !self.blocks.is_empty()
            && self.blocks.len() <= DELTA_MAX_BLOCKS as usize
            && (self.size - 1) / i64::from(self.block_size) + 1 == self.blocks.len() as i64
    }

    /// `DeltaSignature::length`: the bytes of `count` consecutive blocks at `first`.
    pub fn length(&self, first: u32, count: u32) -> i64 {
        if count == 0 || first >= self.blocks.len() as u32 || count > self.blocks.len() as u32 - first {
            return 0;
        }
        let start = i64::from(first) * i64::from(self.block_size);
        (self.size - start).min(i64::from(count) * i64::from(self.block_size))
    }
}

pub struct DeltaBasis {
    pub file: File,
    pub signature: DeltaSignature,
}

impl DeltaBasis {
    /// Read one basis block and recheck its advertised strong checksum. The block
    /// stays in `scratch` for the caller to write.
    pub fn read_block(&self, index: u32, scratch: &mut Vec<u8>) -> io::Result<()> {
        let length = self.signature.length(index, 1);
        if length <= 0 {
            return Err(io::Error::new(io::ErrorKind::InvalidInput, "bad delta basis block"));
        }
        scratch.resize(length as usize, 0);
        read_exact_at(&self.file, scratch, i64::from(index) * i64::from(self.signature.block_size))?;
        let strong = self.signature.blocks[index as usize].strong;
        if ffi::xxh3_64(scratch) != strong {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "delta basis changed"));
        }
        Ok(())
    }
}

fn revision(metadata: &std::fs::Metadata) -> (i64, i64, i64, i64, i64) {
    (metadata.size() as i64, metadata.mtime(), metadata.mtime_nsec(), metadata.ctime(), metadata.ctime_nsec())
}

fn unchanged(file: &File, path: &Path, before: &std::fs::Metadata) -> bool {
    let Ok(after) = file.metadata() else { return false };
    let Ok(named) = std::fs::symlink_metadata(path) else { return false };
    let expected = revision(before);
    after.is_file() && named.is_file() && revision(&after) == expected && revision(&named) == expected
}

fn read_exact_at(file: &File, mut buffer: &mut [u8], mut offset: i64) -> io::Result<()> {
    while !buffer.is_empty() {
        match file.read_at(buffer, offset as u64) {
            Ok(0) => return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "short read")),
            Ok(count) => {
                offset += count as i64;
                buffer = &mut buffer[count..];
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => return Err(error),
        }
    }
    Ok(())
}

/// `destination_delta_basis`: a regular destination at least 1 KiB becomes the
/// basis, with the C++ block size and block checksums. A path that changed while
/// it was read is refused, and the open descriptor stays anchored.
pub fn destination_basis(path: &Path) -> io::Result<Option<DeltaBasis>> {
    let file = match OpenOptions::new().read(true).custom_flags(O_NOFOLLOW | O_NONBLOCK).open(path) {
        Ok(file) => file,
        Err(_) => return Ok(None),
    };
    let before = match file.metadata() {
        Ok(metadata) if metadata.is_file() && metadata.size() >= 1024 => metadata,
        _ => return Ok(None),
    };
    let size = match i64::try_from(before.size()) {
        Ok(size) => size,
        Err(_) => return Ok(None),
    };
    let block_size = (2.0 * (size as f64).sqrt()).clamp(1024.0, f64::from(DELTA_MAX_BLOCK)) as u32 & !7;
    let count = (u64::try_from((size - 1) / i64::from(block_size) + 1)).unwrap_or(0);
    if count == 0 || count > u64::from(DELTA_MAX_BLOCKS) {
        return Ok(None);
    }
    let mut signature =
        DeltaSignature { size, block_size, blocks: vec![DeltaBlock::default(); count as usize] };
    let mut bytes = vec![0u8; block_size as usize];
    for index in 0..count as u32 {
        let length = signature.length(index, 1);
        if length <= 0 {
            return Ok(None);
        }
        let slice = &mut bytes[..length as usize];
        if read_exact_at(&file, slice, i64::from(index) * i64::from(block_size)).is_err() {
            return Ok(None);
        }
        signature.blocks[index as usize] = DeltaBlock { weak: weak_sum(slice), strong: ffi::xxh3_64(slice) };
    }
    if !unchanged(&file, path, &before) {
        return Ok(None);
    }
    Ok(Some(DeltaBasis { file, signature }))
}

fn signature_body(basis: Option<&DeltaSignature>) -> Vec<u8> {
    let mut body = Encoder::new();
    match basis {
        None => {
            body.byte(0);
        }
        Some(signature) => {
            body.byte(1);
            body.var(signature.size.max(0) as u64).var(u64::from(signature.block_size)).var(signature.blocks.len() as u64);
            for block in &signature.blocks {
                body.raw(&block.weak.to_le_bytes()).raw(&block.strong.to_le_bytes());
            }
        }
    }
    body.into_bytes()
}

/// `Sender::signature`: id, index, a compression flag, and the body.
pub fn signature_reply(
    id: u32,
    idx: u32,
    basis: Option<&DeltaSignature>,
    compress: bool,
    level: i64,
) -> Vec<u8> {
    let body = signature_body(basis);
    let mut frame = Encoder::new();
    frame.var(u64::from(id)).var(u64::from(idx));
    let flag = frame.bytes.len();
    frame.byte(0);
    let level = i32::try_from(level).unwrap_or(3);
    if protocol::pack_body(&mut frame, &body, compress, level) {
        frame.bytes[flag] = 1;
    }
    frame.into_bytes()
}

fn unpack_limited(input: &[u8], compressed: bool, features: u64, limit: usize) -> io::Result<Vec<u8>> {
    if !compressed {
        if input.len() > limit {
            return protocol::bad("protocol error: oversized frame body");
        }
        return Ok(input.to_vec());
    }
    if features & feature::ZSTD == 0 {
        return protocol::bad("compressed data without negotiated zstd support");
    }
    let mut d = Decoder::new(input);
    let raw = usize::try_from(d.var().map_err(protocol::decode_err)?).map_err(|_| {
        io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad compressed frame")
    })?;
    if raw > limit {
        return protocol::bad("protocol error: bad compressed frame");
    }
    ffi::zstd_decompress(d.rest(), raw)
}

/// `Sender::on_delta_reply`: read an F_DELTA_SIGNATURE, refusing every malformed
/// flag, dimension, count and trailing byte the C++ sender refuses.
pub fn decode_signature(payload: &[u8], features: u64) -> io::Result<(u32, u32, Option<DeltaSignature>)> {
    let mut d = Decoder::new(payload);
    let id = u32::try_from(d.var().map_err(protocol::decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta reply index"))?;
    let idx = u32::try_from(d.var().map_err(protocol::decode_err)?)
        .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta reply index"))?;
    let compressed = d.byte().map_err(protocol::decode_err)?;
    if compressed > 1 {
        return protocol::bad("protocol error: bad delta compression flag");
    }
    let body = unpack_limited(d.rest(), compressed == 1, features, DELTA_MAX_BLOCKS as usize * 12 + 64)?;
    let mut r = Decoder::new(&body);
    let present = r.byte().map_err(protocol::decode_err)?;
    if present > 1 {
        return protocol::bad("protocol error: bad delta signature flag");
    }
    let mut signature = None;
    if present == 1 {
        let size = i64::try_from(r.var().map_err(protocol::decode_err)?)
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta signature dimensions"))?;
        let block_size = u32::try_from(r.var().map_err(protocol::decode_err)?)
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta signature dimensions"))?;
        let count = u32::try_from(r.var().map_err(protocol::decode_err)?)
            .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: bad delta signature dimensions"))?;
        if size <= 0
            || !(1024..=DELTA_MAX_BLOCK).contains(&block_size)
            || count == 0
            || count > DELTA_MAX_BLOCKS
            || i64::from(count) != (size - 1) / i64::from(block_size) + 1
            || usize::try_from(count).unwrap_or(usize::MAX) > { let mut peek = r.clone(); peek.rest().len() } / 12
        {
            return protocol::bad("protocol error: bad delta signature dimensions");
        }
        let mut blocks = Vec::with_capacity(count as usize);
        for _ in 0..count {
            let weak = u32::from_le_bytes(r.raw(4).map_err(protocol::decode_err)?.try_into().unwrap());
            let strong = u64::from_le_bytes(r.raw(8).map_err(protocol::decode_err)?.try_into().unwrap());
            blocks.push(DeltaBlock { weak, strong });
        }
        signature = Some(DeltaSignature { size, block_size, blocks });
    }
    if !r.is_empty() {
        return protocol::bad("protocol error: trailing or truncated delta reply");
    }
    Ok((id, idx, signature))
}

fn weak_sum(bytes: &[u8]) -> u32 {
    let mut a = 0u32;
    let mut b = 0u32;
    for &byte in bytes {
        a = a.wrapping_add(u32::from(byte));
        b = b.wrapping_add(a);
    }
    (a & 65535) | (b << 16)
}

fn roll(sum: u32, old: u8, next: u8, size: u32) -> u32 {
    let a = ((sum & 65535).wrapping_sub(u32::from(old)).wrapping_add(u32::from(next))) & 65535;
    let b = ((sum >> 16)
        .wrapping_sub(size.wrapping_mul(u32::from(old)))
        .wrapping_add(a))
        & 65535;
    a | (b << 16)
}

#[derive(Clone, Copy, Debug, Default)]
pub struct DeltaResult {
    pub ok: bool,
    pub processed: i64,
    pub literal_bytes: i64,
    pub sum: [u64; 2],
}

/// `delta_match_fd`: walk the source once, emitting either a run of basis blocks
/// (`count != 0`) or a literal (`count == 0`). At most one block plus 1 MiB of
/// source is held at a time.
pub fn match_file(
    file: &File,
    size: i64,
    signature: &DeltaSignature,
    mut emit: impl FnMut(i64, u32, u32, &[u8]) -> io::Result<()>,
) -> io::Result<DeltaResult> {
    let mut result = DeltaResult::default();
    if size < 0 || !signature.valid() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "bad delta signature"));
    }
    let mut weak_keys = HashSet::new();
    let mut matches: HashMap<(u64, u64), Vec<u32>> = HashMap::new();
    for index in 0..signature.blocks.len() as u32 {
        let block = signature.blocks[index as usize];
        let key = ((signature.length(index, 1) as u64) << 32) | u64::from(block.weak);
        weak_keys.insert(key);
        matches.entry((key, block.strong)).or_default().push(index);
    }

    let block_size = signature.block_size as usize;
    let mut bytes = vec![0u8; READ_BUFFER + block_size + 1];
    let mut begin = 0usize;
    let mut end = 0usize;
    let mut position = 0i64;
    let mut digest = ffi::Xxh3_128::new()?;
    let mut literal: Vec<u8> = Vec::with_capacity(LITERAL_BUFFER);
    let mut copy: Option<(i64, u32, u32)> = None;
    let mut next_index = 0u32;
    let mut failed = false;

    macro_rules! ensure {
        ($wanted:expr) => {{
            let wanted = $wanted;
            if end - begin < wanted {
                let left = end - begin;
                bytes.copy_within(begin..end, 0);
                begin = 0;
                end = left;
                let want = (bytes.len() - left).min((size - position - left as i64).max(0) as usize);
                if want > 0 {
                    if read_exact_at(file, &mut bytes[end..end + want], position + left as i64).is_err() {
                        failed = true;
                        false
                    } else {
                        end += want;
                        end - begin >= wanted
                    }
                } else {
                    false
                }
            } else {
                true
            }
        }};
    }

    macro_rules! flush_literal {
        () => {{
            if !literal.is_empty() {
                let offset = position - literal.len() as i64;
                emit(offset, 0, 0, &literal)?;
                digest.update(&literal)?;
                result.processed += literal.len() as i64;
                result.literal_bytes += literal.len() as i64;
                literal.clear();
            }
        }};
    }
    macro_rules! flush_copy {
        () => {{
            if let Some((offset, first, count)) = copy {
                emit(offset, first, count, &[])?;
                result.processed += signature.length(first, count);
                copy = None;
            }
        }};
    }

    let tail = (size % i64::from(signature.block_size)) as u32;
    let mut full_sum = 0u32;
    let mut tail_sum = 0u32;
    let mut sums_ready = false;
    while position < size {
        let full = (i64::from(signature.block_size)).min(size - position) as u32;
        let extra = usize::from(position + i64::from(full) < size);
        if !ensure!(full as usize + extra) {
            if !failed {
                failed = true;
            }
            break;
        }
        let window = &bytes[begin..];
        if !sums_ready {
            full_sum = weak_sum(&window[..full as usize]);
            if tail != 0 && tail <= full {
                tail_sum = weak_sum(&window[..tail as usize]);
            }
        }
        let mut index = 0u32;
        let mut length = 0u32;
        for len in [full, tail] {
            if len == 0 || len > full {
                continue;
            }
            let weak = if len == full { full_sum } else { tail_sum };
            let key = (u64::from(len) << 32) | u64::from(weak);
            if !weak_keys.contains(&key) {
                continue;
            }
            let strong = ffi::xxh3_64(&window[..len as usize]);
            let Some(indices) = matches.get(&(key, strong)) else { continue };
            index = if indices.binary_search(&next_index).is_ok() { next_index } else { indices[0] };
            length = len;
            break;
        }
        if length != 0 {
            flush_literal!();
            if let Some((_, first, count)) = copy {
                if first + count != index || signature.length(first, count) + i64::from(length) > COPY_RUN {
                    flush_copy!();
                }
            }
            if copy.is_none() {
                copy = Some((position, index, 0));
            }
            if let Some((_, _, count)) = &mut copy {
                *count += 1;
            }
            digest.update(&window[..length as usize])?;
            position += i64::from(length);
            begin += length as usize;
            next_index = index + 1;
            sums_ready = false;
        } else {
            flush_copy!();
            literal.push(window[0]);
            if position + i64::from(full) < size {
                full_sum = roll(full_sum, window[0], window[full as usize], full);
                if tail != 0 {
                    tail_sum = roll(tail_sum, window[0], window[tail as usize], tail);
                }
            } else {
                let a = ((full_sum & 65535).wrapping_sub(u32::from(window[0]))) & 65535;
                let b = ((full_sum >> 16).wrapping_sub(full.wrapping_mul(u32::from(window[0])))) & 65535;
                full_sum = a | (b << 16);
                if tail != 0 && tail < full {
                    tail_sum = roll(tail_sum, window[0], window[tail as usize], tail);
                }
            }
            sums_ready = true;
            position += 1;
            begin += 1;
            if literal.len() >= LITERAL_BUFFER {
                flush_literal!();
            }
        }
    }
    flush_copy!();
    flush_literal!();
    let _ = copy;
    result.sum = digest.digest();
    result.ok = !failed && result.processed == size;
    Ok(result)
}

/// `delta_verify_fd`: the reconstructed file must hash to the sender's digest.
pub fn verify_file(file: &File, size: i64, sum: [u64; 2]) -> io::Result<bool> {
    if size < 0 {
        return Ok(false);
    }
    let mut hash = ffi::Xxh3_128::new()?;
    let mut buffer = vec![0u8; READ_BUFFER];
    let mut offset = 0i64;
    while offset < size {
        let want = (buffer.len() as i64).min(size - offset) as usize;
        let slice = &mut buffer[..want];
        match file.read_at(slice, offset as u64) {
            Ok(0) => return Ok(false),
            Ok(count) => {
                hash.update(&slice[..count])?;
                offset += count as i64;
            }
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => return Err(error),
        }
    }
    Ok(hash.digest() == sum)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pattern(len: usize) -> Vec<u8> {
        (0..len).map(|index| (index.wrapping_mul(131) & 0xff) as u8).collect()
    }

    #[test]
    fn the_block_size_and_checksums_match_delta_cpp() {
        let bytes = pattern(2 * 1024 * 1024);
        let size = bytes.len() as i64;
        let block_size = (2.0 * (size as f64).sqrt()).clamp(1024.0, f64::from(DELTA_MAX_BLOCK)) as u32 & !7;
        assert_eq!(block_size, 2896);
        let first = &bytes[..block_size as usize];
        assert_eq!(ffi::xxh3_64(first), 0x922d_bbc7_fa6f_1d7a);
        assert_eq!(weak_sum(first), 0xc758_a088);
        let signature = DeltaSignature {
            size,
            block_size,
            blocks: vec![DeltaBlock { weak: weak_sum(first), strong: ffi::xxh3_64(first) }; 1],
        };
        assert!(!signature.valid(), "the block count must match the size");
    }

    #[test]
    fn rolling_matches_a_fresh_weak_sum() {
        let bytes = pattern(8192);
        let mut sum = weak_sum(&bytes[..4096]);
        for index in 0..4096 {
            sum = roll(sum, bytes[index], bytes[index + 4096], 4096);
            assert_eq!(sum, weak_sum(&bytes[index + 1..index + 4097]));
        }
    }
}
