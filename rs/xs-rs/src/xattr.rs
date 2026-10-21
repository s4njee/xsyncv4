//! Extended attributes as `src/xattrs.cpp` and the XATTR_START/CHUNK/END streams
//! in `src/remote.cpp` implement them. Names stay in Linux protocol form; the
//! unprivileged user.rsync. prefix and the internal user.rsync.% namespace follow
//! the C++ rules.

use std::collections::{BTreeMap, HashMap};
use std::ffi::CString;
use std::io;
use std::os::raw::{c_char, c_int, c_void};
use std::path::Path;

use xs_wire::{Decoder, Encoder, Frame};

use crate::ffi;
use crate::filter::FilterList;
use crate::protocol::{self, feature, frame_type, Options, T_BLK, T_REG};

pub const INLINE_MAX: usize = 65536;
const MAX_NAME: usize = 1024;
const MAX_COUNT: u64 = 65536;
const MAX_ACTIVE: usize = 1024;
const CHUNK_MAX: usize = 65536;
const ENOTSUP: i32 = 95;

extern "C" {
    fn geteuid() -> u32;
    fn llistxattr(path: *const c_char, list: *mut c_char, size: usize) -> isize;
    fn lgetxattr(path: *const c_char, name: *const c_char, value: *mut c_void, size: usize) -> isize;
    fn lsetxattr(path: *const c_char, name: *const c_char, value: *const c_void, size: usize, flags: c_int) -> c_int;
    fn lremovexattr(path: *const c_char, name: *const c_char) -> c_int;
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct XattrSet {
    pub complete: bool,
    pub values: BTreeMap<Vec<u8>, Vec<u8>>,
}

impl Default for XattrSet {
    fn default() -> Self {
        Self { complete: true, values: BTreeMap::new() }
    }
}

fn unsupported(error: &io::Error) -> bool {
    error.raw_os_error() == Some(ENOTSUP)
}

fn path_arg(path: &Path) -> io::Result<CString> {
    use std::os::unix::ffi::OsStrExt;
    CString::new(path.as_os_str().as_bytes()).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL in path"))
}

fn name_arg(name: &[u8]) -> io::Result<CString> {
    CString::new(name).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL in xattr name"))
}

fn list(path: &Path) -> io::Result<Vec<Vec<u8>>> {
    let path = path_arg(path)?;
    for _ in 0..4 {
        let count = unsafe { llistxattr(path.as_ptr(), std::ptr::null_mut(), 0) };
        if count < 0 {
            let error = io::Error::last_os_error();
            if unsupported(&error) {
                return Ok(Vec::new());
            }
            return Err(error);
        }
        if count == 0 {
            return Ok(Vec::new());
        }
        let mut bytes = vec![0u8; count as usize];
        let count = unsafe { llistxattr(path.as_ptr(), bytes.as_mut_ptr().cast(), bytes.len()) };
        if count >= 0 {
            bytes.truncate(count as usize);
            let mut names = Vec::new();
            for name in bytes.split(|&byte| byte == 0) {
                if !name.is_empty() {
                    names.push(name.to_vec());
                }
            }
            return Ok(names);
        }
        let error = io::Error::last_os_error();
        if error.raw_os_error() != Some(34) {
            if unsupported(&error) {
                return Ok(Vec::new());
            }
            return Err(error);
        }
    }
    Err(io::Error::last_os_error())
}

fn get(path: &Path, name: &[u8]) -> io::Result<Vec<u8>> {
    let path = path_arg(path)?;
    let name = name_arg(name)?;
    for _ in 0..4 {
        let count = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), std::ptr::null_mut(), 0) };
        if count < 0 {
            return Err(io::Error::last_os_error());
        }
        if count == 0 {
            return Ok(Vec::new());
        }
        let mut bytes = vec![0u8; count as usize];
        let count = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), bytes.as_mut_ptr().cast(), bytes.len()) };
        if count >= 0 {
            bytes.truncate(count as usize);
            return Ok(bytes);
        }
        let error = io::Error::last_os_error();
        if error.raw_os_error() != Some(34) {
            return Err(error);
        }
    }
    Err(io::Error::last_os_error())
}

fn set(path: &Path, name: &[u8], value: &[u8]) -> io::Result<()> {
    let path = path_arg(path)?;
    let name = name_arg(name)?;
    let code = unsafe { lsetxattr(path.as_ptr(), name.as_ptr(), value.as_ptr().cast(), value.len(), 0) };
    if code == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

fn remove(path: &Path, name: &[u8]) -> io::Result<()> {
    let path = path_arg(path)?;
    let name = name_arg(name)?;
    let code = unsafe { lremovexattr(path.as_ptr(), name.as_ptr()) };
    if code == 0 {
        Ok(())
    } else {
        Err(io::Error::last_os_error())
    }
}

fn am_root() -> bool {
    unsafe { geteuid() == 0 }
}

pub fn supported_type(kind: u8) -> bool {
    (T_REG..=T_BLK).contains(&kind)
}

pub fn internal(name: &[u8]) -> bool {
    name.starts_with(b"user.rsync.%")
}

pub fn wire_name(name: &[u8]) -> Vec<u8> {
    name.to_vec()
}

pub fn local_name(name: &[u8], filters: &FilterList) -> Vec<u8> {
    if am_root() || name.starts_with(b"user.") {
        name.to_vec()
    } else if filters.has_xattr_filters() {
        let mut local = b"user.rsync.".to_vec();
        local.extend_from_slice(name);
        local
    } else {
        Vec::new()
    }
}

fn eligible(name: &[u8], filters: &FilterList, source: bool, xattrs: u8) -> bool {
    if source && xattrs < 2 && internal(name) {
        return false;
    }
    if !filters.has_xattr_filters() {
        if source || am_root() {
            if name.starts_with(b"system.") {
                return false;
            }
        } else if !name.starts_with(b"user.") {
            return false;
        }
    }
    !source || !filters.xattr_excluded(name, false, false)
}

/// Read one inode's attributes in source order. A failed list or value clears the
/// set and marks it incomplete, exactly as `read` in xattrs.cpp does.
pub fn source_xattrs(path: &Path, kind: u8, filters: &FilterList, opts: &Options) -> XattrSet {
    let mut result = XattrSet::default();
    if opts.xattrs == 0 || !supported_type(kind) {
        return result;
    }
    let names = match list(path) {
        Ok(names) => names,
        Err(error) if unsupported(&error) => return result,
        Err(_) => {
            result.complete = false;
            return result;
        }
    };
    for name in names {
        if !eligible(&name, filters, true, opts.xattrs) {
            continue;
        }
        match get(path, &name) {
            Ok(value) => {
                result.values.insert(wire_name(&name), value);
            }
            Err(_) => {
                result.values.clear();
                result.complete = false;
                return result;
            }
        }
    }
    result
}

fn desired(source: &XattrSet, filters: &FilterList, opts: &Options) -> BTreeMap<Vec<u8>, Vec<u8>> {
    let mut result = BTreeMap::new();
    for (name, value) in &source.values {
        if filters.xattr_excluded(name, true, false) {
            continue;
        }
        let local = local_name(name, filters);
        if local.is_empty() || (opts.xattrs < 2 && internal(&local)) || !eligible(&local, filters, false, opts.xattrs) {
            continue;
        }
        result.insert(local, value.clone());
    }
    result
}

fn local_values(path: &Path, filters: &FilterList, opts: &Options) -> io::Result<XattrSet> {
    let mut result = XattrSet::default();
    for name in list(path)? {
        if !eligible(&name, filters, false, opts.xattrs) {
            continue;
        }
        result.values.insert(name.clone(), get(path, &name)?);
    }
    Ok(result)
}

/// Apply a received set: set values that differ and remove stale names the
/// receiver's xattr filters do not protect. Returns whether anything changed.
pub fn apply(source: &XattrSet, path: &Path, kind: u8, filters: &FilterList, opts: &Options) -> io::Result<bool> {
    if !source.complete || opts.xattrs == 0 || !supported_type(kind) {
        return Ok(false);
    }
    let wanted = desired(source, filters, opts);
    let current = match local_values(path, filters, opts) {
        Ok(values) => values,
        Err(error) if unsupported(&error) => XattrSet::default(),
        Err(error) => return Err(error),
    };
    let mut changed = false;
    for (name, value) in &wanted {
        if current.values.get(name) == Some(value) {
            continue;
        }
        set(path, name, value)?;
        changed = true;
    }
    for name in current.values.keys() {
        if wanted.contains_key(name) || filters.xattr_excluded(name, true, false) {
            continue;
        }
        remove(path, name)?;
        changed = true;
    }
    Ok(changed)
}

/// Sender side of the value stream: values over the inline limit travel in
/// XATTR_START/XATTR_CHUNK/XATTR_END frames before the metadata that refers to them.
pub struct Streams {
    next_id: u64,
    frames: Vec<Frame>,
}

impl Default for Streams {
    fn default() -> Self {
        Self::new()
    }
}

impl Streams {
    pub fn new() -> Self {
        Self { next_id: 0, frames: Vec::new() }
    }

    pub fn put_xattrs(&mut self, out: &mut Encoder, attrs: &XattrSet, features: u64) {
        out.byte(u8::from(attrs.complete));
        if !attrs.complete {
            out.var(0);
            return;
        }
        out.var(attrs.values.len() as u64);
        let stream = features & feature::XATTR_STREAM != 0;
        for (name, value) in &attrs.values {
            out.str(name);
            if stream {
                let large = value.len() > INLINE_MAX;
                out.byte(u8::from(large));
                if large {
                    let id = self.start(value);
                    out.var(id);
                    continue;
                }
            }
            out.str(value);
        }
    }

    fn start(&mut self, value: &[u8]) -> u64 {
        self.next_id += 1;
        let id = self.next_id;
        let mut frame = Encoder::new();
        frame.var(id).var(value.len() as u64);
        self.frames.push(Frame::new(frame_type::XATTR_START, frame.into_bytes()));
        for (index, chunk) in value.chunks(CHUNK_MAX).enumerate() {
            let mut frame = Encoder::new();
            frame.var(id).var((index * CHUNK_MAX) as u64).str(chunk);
            self.frames.push(Frame::new(frame_type::XATTR_CHUNK, frame.into_bytes()));
        }
        let mut frame = Encoder::new();
        frame.var(id).raw(&ffi::xxh3_64(value).to_le_bytes());
        self.frames.push(Frame::new(frame_type::XATTR_END, frame.into_bytes()));
        id
    }

    pub fn drain(&mut self) -> Vec<Frame> {
        std::mem::take(&mut self.frames)
    }
}

struct Pending {
    data: Vec<u8>,
    expected: usize,
    complete: bool,
}

/// Receiver side of the value stream, keyed by the sender's increasing ids.
pub struct Incoming {
    values: HashMap<u64, Pending>,
    last_id: u64,
    active: usize,
}

impl Default for Incoming {
    fn default() -> Self {
        Self::new()
    }
}

impl Incoming {
    pub fn new() -> Self {
        Self { values: HashMap::new(), last_id: 0, active: 0 }
    }

    pub fn receive(&mut self, kind: u8, payload: &[u8]) -> io::Result<()> {
        let mut d = Decoder::new(payload);
        let id = d.var().map_err(protocol::decode_err)?;
        if kind == frame_type::XATTR_START {
            let size = d.var().map_err(protocol::decode_err)?;
            if !d.is_empty()
                || id == 0
                || Some(id) != self.last_id.checked_add(1)
                || size == 0
                || size > i64::MAX as u64
                || self.values.len() >= 1_048_576
                || self.active >= MAX_ACTIVE
            {
                return protocol::bad("protocol error: invalid xattr value start");
            }
            let mut data = Vec::new();
            data.try_reserve_exact((size as usize).min(1 << 20))
                .map_err(|_| io::Error::other("store received extended attributes"))?;
            self.values.insert(id, Pending { data, expected: size as usize, complete: false });
            self.last_id = id;
            self.active += 1;
            return Ok(());
        }
        let pending = self
            .values
            .get_mut(&id)
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "protocol error: unknown or completed xattr value stream"))?;
        if kind == frame_type::XATTR_CHUNK {
            let offset = d.var().map_err(protocol::decode_err)?;
            let bytes = d.str().map_err(protocol::decode_err)?;
            if !d.is_empty()
                || bytes.is_empty()
                || bytes.len() > CHUNK_MAX
                || offset != pending.data.len() as u64
                || bytes.len() > pending.expected.saturating_sub(pending.data.len())
            {
                return protocol::bad("protocol error: invalid xattr value chunk");
            }
            pending.data.extend_from_slice(bytes);
            return Ok(());
        }
        let digest = d.raw(8).map_err(protocol::decode_err)?;
        if !d.is_empty() || pending.data.len() != pending.expected || pending.complete {
            return protocol::bad("protocol error: incomplete xattr value stream");
        }
        let expected = u64::from_le_bytes(digest.try_into().unwrap());
        if expected != ffi::xxh3_64(&pending.data) {
            return protocol::bad("data corruption detected in xattr stream");
        }
        pending.complete = true;
        self.active -= 1;
        Ok(())
    }

    pub fn take(&mut self, id: u64) -> io::Result<Vec<u8>> {
        match self.values.get(&id) {
            Some(pending) if pending.complete => {}
            _ => return protocol::bad("protocol error: unknown or incomplete xattr value reference"),
        }
        Ok(self.values.remove(&id).unwrap().data)
    }

    pub fn drained(&self) -> bool {
        self.values.is_empty()
    }
}

/// Decode one list. `Incoming` supplies the values referenced by stream ids.
pub fn get_xattrs(d: &mut Decoder<'_>, features: u64, streams: &mut Incoming) -> io::Result<XattrSet> {
    let complete = d.byte().map_err(protocol::decode_err)?;
    let count = d.var().map_err(protocol::decode_err)?;
    if complete > 1 || count > MAX_COUNT || (complete == 0 && count != 0) {
        return protocol::bad("protocol error: malformed xattr list");
    }
    let stream = features & feature::XATTR_STREAM != 0;
    let mut result = XattrSet { complete: complete != 0, values: BTreeMap::new() };
    for _ in 0..count {
        let name = d.str().map_err(protocol::decode_err)?.to_vec();
        if name.is_empty() || name.len() > MAX_NAME || name.contains(&0) || result.values.contains_key(&name) {
            return protocol::bad("protocol error: invalid or duplicate xattr name/value");
        }
        let value = if stream {
            let kind = d.byte().map_err(protocol::decode_err)?;
            if kind > 1 {
                return protocol::bad("protocol error: bad xattr value kind");
            }
            if kind != 0 {
                let id = d.var().map_err(protocol::decode_err)?;
                streams.take(id)?
            } else {
                let value = d.str().map_err(protocol::decode_err)?;
                if value.len() > INLINE_MAX {
                    return protocol::bad("protocol error: truncated or oversized inline xattr value");
                }
                value.to_vec()
            }
        } else {
            d.str().map_err(protocol::decode_err)?.to_vec()
        };
        result.values.insert(name, value);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(pairs: &[(&[u8], &[u8])]) -> XattrSet {
        XattrSet {
            complete: true,
            values: pairs.iter().map(|(name, value)| (name.to_vec(), value.to_vec())).collect(),
        }
    }

    #[test]
    fn the_list_matches_put_xattrs_bytes() {
        let attrs = set(&[(b"user.foo", b"bar")]);
        let mut out = Encoder::new();
        Streams::new().put_xattrs(&mut out, &attrs, feature::XATTRS);
        assert_eq!(out.bytes, b"\x01\x01\x08user.foo\x03bar");
        let mut out = Encoder::new();
        Streams::new().put_xattrs(&mut out, &attrs, feature::XATTRS | feature::XATTR_STREAM);
        assert_eq!(out.bytes, b"\x01\x01\x08user.foo\x00\x03bar");
    }

    #[test]
    fn an_incomplete_set_sends_no_values() {
        let attrs = XattrSet { complete: false, values: BTreeMap::from([(b"user.foo".to_vec(), b"bar".to_vec())]) };
        let mut out = Encoder::new();
        Streams::new().put_xattrs(&mut out, &attrs, feature::XATTRS | feature::XATTR_STREAM);
        assert_eq!(out.bytes, [0, 0]);
    }

    #[test]
    fn a_large_value_streams_before_its_reference_and_verifies_its_digest() {
        let value = vec![0x5a; INLINE_MAX + 5];
        let attrs = set(&[(b"user.large", &value)]);
        let mut out = Encoder::new();
        let mut sender = Streams::new();
        sender.put_xattrs(&mut out, &attrs, feature::XATTRS | feature::XATTR_STREAM);
        let frames = sender.drain();
        assert_eq!(frames.len(), 4);
        assert_eq!(frames[0].kind, frame_type::XATTR_START);
        assert_eq!(frames[1].kind, frame_type::XATTR_CHUNK);
        assert_eq!(frames[2].kind, frame_type::XATTR_CHUNK);
        assert_eq!(frames[3].kind, frame_type::XATTR_END);
        let mut incoming = Incoming::new();
        for frame in &frames {
            incoming.receive(frame.kind, &frame.payload).unwrap();
        }
        let mut d = Decoder::new(&out.bytes);
        let decoded = get_xattrs(&mut d, feature::XATTRS | feature::XATTR_STREAM, &mut incoming).unwrap();
        assert!(d.is_empty());
        assert_eq!(decoded, attrs);
        assert!(incoming.drained());
    }

    #[test]
    fn a_duplicate_or_empty_name_is_refused() {
        let mut incoming = Incoming::new();
        assert!(get_xattrs(&mut Decoder::new(b"\x01\x01\x00\x00"), feature::XATTRS, &mut incoming).is_err());
        let mut incoming = Incoming::new();
        assert!(get_xattrs(&mut Decoder::new(b"\x01\x02\x08user.foo\x00\x01\x08user.foo\x01"), feature::XATTRS, &mut incoming)
            .is_err());
    }

    #[test]
    fn a_bad_stream_id_or_digest_is_refused() {
        let mut incoming = Incoming::new();
        let mut start = Encoder::new();
        start.var(2).var(1);
        assert!(incoming.receive(frame_type::XATTR_START, &start.bytes).is_err());
        let mut start = Encoder::new();
        start.var(1).var(1);
        incoming.receive(frame_type::XATTR_START, &start.bytes).unwrap();
        let mut chunk = Encoder::new();
        chunk.var(1).var(0).str(b"x");
        incoming.receive(frame_type::XATTR_CHUNK, &chunk.bytes).unwrap();
        let mut end = Encoder::new();
        end.var(1).raw(&0u64.to_le_bytes());
        assert!(incoming.receive(frame_type::XATTR_END, &end.bytes).is_err());
    }
}
