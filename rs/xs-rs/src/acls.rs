//! POSIX ACLs as `src/acls.cpp` and `put_acls`/`get_acls` in `src/remote.cpp`
//! implement them. Linux keeps an ACL as the `system.posix_acl_access` and
//! `system.posix_acl_default` xattrs; the wire carries validated records, never
//! an opaque kernel blob.

use std::ffi::CString;
use std::io;
use std::os::raw::{c_char, c_int, c_void};
use std::os::unix::ffi::OsStrExt;
use std::path::Path;

use xs_wire::{Decoder, Encoder};

use crate::ffi;
use crate::protocol::{self, feature, Options, T_BLK, T_DIR, T_LNK, T_REG};

pub const NATIVE_ACL: u64 = feature::ACL_POSIX;
pub const MAX_RECORDS: usize = 8191;
pub const MAX_BYTES: usize = 65536;
pub const UNDEFINED: u32 = u32::MAX;

const ACCESS: &[u8] = b"system.posix_acl_access";
const DEFAULT: &[u8] = b"system.posix_acl_default";
const ENODATA: i32 = 61;
const ENOTSUP: i32 = 95;
const ERANGE: i32 = 34;

extern "C" {
    fn lgetxattr(path: *const c_char, name: *const c_char, value: *mut c_void, size: usize) -> isize;
    fn lsetxattr(path: *const c_char, name: *const c_char, value: *const c_void, size: usize, flags: c_int) -> c_int;
    fn lremovexattr(path: *const c_char, name: *const c_char) -> c_int;
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AclRecord {
    pub tag: u32,
    pub permissions: u32,
    pub flags: u32,
    pub id: u32,
    pub name: Vec<u8>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AclRecords {
    pub complete: bool,
    pub flags: u32,
    pub access: Vec<AclRecord>,
    pub defaults: Vec<AclRecord>,
}

impl Default for AclRecords {
    fn default() -> Self {
        Self { complete: true, flags: 0, access: Vec::new(), defaults: Vec::new() }
    }
}

/// The kernel-provided values, kept separately from the portable records.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AclSet {
    pub complete: bool,
    pub access: Vec<u8>,
    pub defaults: Vec<u8>,
}

impl Default for AclSet {
    fn default() -> Self {
        Self { complete: true, access: Vec::new(), defaults: Vec::new() }
    }
}

pub fn supported_type(kind: u8) -> bool {
    (T_REG..=T_BLK).contains(&kind) && kind != T_LNK
}

fn named(tag: u32) -> bool {
    tag == 2 || tag == 8
}

fn group_entry(tag: u32) -> bool {
    tag == 8
}

fn c_path(path: &Path) -> io::Result<CString> {
    CString::new(path.as_os_str().as_bytes()).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL in path"))
}

fn c_name(name: &[u8]) -> io::Result<CString> {
    CString::new(name).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL in ACL xattr name"))
}

fn absent(error: &io::Error) -> bool {
    matches!(error.raw_os_error(), Some(ENODATA | ENOTSUP))
}

fn read_value(path: &Path, name: &[u8]) -> io::Result<Option<Vec<u8>>> {
    let path = c_path(path)?;
    let name = c_name(name)?;
    for _ in 0..4 {
        let size = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), std::ptr::null_mut(), 0) };
        if size < 0 {
            let error = io::Error::last_os_error();
            if absent(&error) {
                return Ok(None);
            }
            return Err(error);
        }
        if size as usize > MAX_BYTES {
            return Err(io::Error::other("ACL value is too large"));
        }
        if size == 0 {
            return Ok(Some(Vec::new()));
        }
        let mut value = vec![0u8; size as usize];
        let got = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), value.as_mut_ptr().cast(), value.len()) };
        if got >= 0 {
            value.truncate(got as usize);
            return Ok(Some(value));
        }
        let error = io::Error::last_os_error();
        if error.raw_os_error() != Some(ERANGE) {
            if absent(&error) {
                return Ok(None);
            }
            return Err(error);
        }
    }
    Err(io::Error::other("ACL value changed while it was read"))
}

fn write_value(path: &Path, name: &[u8], value: &[u8]) -> io::Result<()> {
    let path = c_path(path)?;
    let name = c_name(name)?;
    let result = if value.is_empty() {
        unsafe { lremovexattr(path.as_ptr(), name.as_ptr()) }
    } else {
        unsafe { lsetxattr(path.as_ptr(), name.as_ptr(), value.as_ptr().cast(), value.len(), 0) }
    };
    if result == 0 {
        return Ok(());
    }
    let error = io::Error::last_os_error();
    if value.is_empty() && absent(&error) {
        return Ok(());
    }
    Err(error)
}

fn read_set(path: &Path, kind: u8) -> AclSet {
    let mut result = AclSet::default();
    match read_value(path, ACCESS) {
        Ok(Some(value)) => result.access = value,
        Ok(None) => {}
        Err(_) => {
            result = AclSet { complete: false, ..AclSet::default() };
            return result;
        }
    }
    if kind == T_DIR {
        match read_value(path, DEFAULT) {
            Ok(Some(value)) => result.defaults = value,
            Ok(None) => {}
            Err(_) => {
                result = AclSet { complete: false, ..AclSet::default() };
            }
        }
    }
    result
}

fn name_of(group: bool, id: u32, numeric: bool) -> Vec<u8> {
    if numeric {
        return Vec::new();
    }
    let name = if group { ffi::group_name(id) } else { ffi::user_name(id) };
    name.filter(|name| name.len() <= 255).unwrap_or_default()
}

fn id_of(group: bool, id: u32, name: &[u8], opts: &Options) -> u32 {
    if group && opts.ownership.group_set {
        return opts.ownership.gid_for(id);
    }
    if !group && opts.ownership.user_set {
        return opts.ownership.uid_for(id);
    }
    if opts.numeric_ids || name.is_empty() {
        return id;
    }
    let mapped = if group { ffi::group_id(name) } else { ffi::user_id(name) };
    mapped.unwrap_or(id)
}

fn tag_at(data: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes([data[offset], data[offset + 1]])
}

fn id_at(data: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([data[offset], data[offset + 1], data[offset + 2], data[offset + 3]])
}

fn linux_records(value: &[u8], numeric: bool) -> Vec<AclRecord> {
    let mut result = Vec::new();
    let mut offset = 4;
    while offset + 8 <= value.len() {
        let tag = u32::from(tag_at(value, offset));
        let permissions = u32::from(tag_at(value, offset + 2));
        let id = id_at(value, offset + 4);
        let name = if named(tag) { name_of(group_entry(tag), id, numeric) } else { Vec::new() };
        result.push(AclRecord { tag, permissions, flags: 0, id, name });
        offset += 8;
    }
    result
}

fn linux_value(records: &mut [AclRecord]) -> Vec<u8> {
    if records.is_empty() {
        return Vec::new();
    }
    records.sort_by_key(|record| (record.tag, record.id));
    let mut data = vec![0u8; 4];
    data[0] = 2;
    for record in records {
        data.push(record.tag as u8);
        data.push(0);
        data.push(record.permissions as u8);
        data.push(0);
        data.extend_from_slice(&record.id.to_le_bytes());
    }
    data
}

/// Access ACL owner/other/mask permissions live in the mode bits, so only the
/// independent named entries and an owning-group access entry distinguish ACLs.
fn independent(data: &[u8]) -> Vec<u8> {
    let mut result = data.to_vec();
    let mut mask = false;
    let mut offset = 4;
    while offset + 8 <= result.len() {
        if tag_at(&result, offset) == 16 {
            mask = true;
        }
        offset += 8;
    }
    let mut offset = 4;
    while offset + 8 <= result.len() {
        let tag = u32::from(tag_at(&result, offset));
        if tag == 1 || tag == 32 || tag == 16 || (tag == 4 && !mask) {
            result[offset + 2] = 0;
            result[offset + 3] = 0;
        }
        offset += 8;
    }
    result
}

fn with_mode(data: &[u8], mode: u32) -> Vec<u8> {
    let mut result = data.to_vec();
    let mut mask = false;
    let mut offset = 4;
    while offset + 8 <= result.len() {
        if tag_at(&result, offset) == 16 {
            mask = true;
        }
        offset += 8;
    }
    let mut offset = 4;
    while offset + 8 <= result.len() {
        let tag = u32::from(tag_at(&result, offset));
        let permissions = match tag {
            1 => Some((mode >> 6) & 7),
            32 => Some(mode & 7),
            16 => Some((mode >> 3) & 7),
            4 if !mask => Some((mode >> 3) & 7),
            _ => None,
        };
        if let Some(permissions) = permissions {
            result[offset + 2] = permissions as u8;
            result[offset + 3] = 0;
        }
        offset += 8;
    }
    result
}

fn valid(records: &AclRecords, kind: u8) -> bool {
    if (!supported_type(kind) || !records.complete) && (records.flags != 0 || !records.access.is_empty() || !records.defaults.is_empty()) {
        return false;
    }
    if kind != T_DIR && !records.defaults.is_empty() {
        return false;
    }
    if records.access.len() > MAX_RECORDS || records.defaults.len() > MAX_RECORDS {
        return false;
    }
    if records.flags != 0 {
        return false;
    }
    for list in [&records.access, &records.defaults] {
        let (mut owner, mut group, mut other, mut mask, mut have_names) = (false, false, false, false, false);
        let (mut previous_tag, mut previous_id) = (0u32, 0u32);
        for record in list {
            if record.name.len() > 255 || record.name.contains(&0) {
                return false;
            }
            if record.permissions > 7 || record.flags != 0 || record.tag < previous_tag {
                return false;
            }
            if named(record.tag) {
                if record.id == UNDEFINED || (record.tag == previous_tag && record.id < previous_id) {
                    return false;
                }
                have_names = true;
            } else {
                if record.id != UNDEFINED || !record.name.is_empty() {
                    return false;
                }
                match record.tag {
                    1 if !owner => owner = true,
                    4 if !group => group = true,
                    16 if !mask => mask = true,
                    32 if !other => other = true,
                    _ => return false,
                }
            }
            previous_tag = record.tag;
            previous_id = record.id;
        }
        if !list.is_empty() && (!owner || !group || !other || (have_names && !mask)) {
            return false;
        }
    }
    true
}

pub fn export_acls(source: &AclSet, numeric_ids: bool) -> AclRecords {
    if !source.complete {
        return AclRecords { complete: false, ..AclRecords::default() };
    }
    AclRecords {
        complete: true,
        flags: 0,
        access: linux_records(&source.access, numeric_ids),
        defaults: linux_records(&source.defaults, numeric_ids),
    }
}

pub fn import_acls(records: AclRecords, opts: &Options) -> AclSet {
    let mut result = AclSet { complete: records.complete, ..AclSet::default() };
    if !result.complete {
        return result;
    }
    let mut access = records.access;
    let mut defaults = records.defaults;
    for record in access.iter_mut().chain(defaults.iter_mut()) {
        if named(record.tag) {
            record.id = id_of(group_entry(record.tag), record.id, &record.name, opts);
        }
    }
    result.access = linux_value(&mut access);
    result.defaults = linux_value(&mut defaults);
    result
}

fn roundtrip(source: &AclSet, opts: &Options) -> AclSet {
    import_acls(export_acls(source, opts.numeric_ids), opts)
}

pub fn source_acls(path: &Path, kind: u8, opts: &Options) -> AclSet {
    if !opts.acls || !supported_type(kind) {
        return AclSet::default();
    }
    let mut result = read_set(path, kind);
    if result.complete && opts.ownership.requested() {
        result = roundtrip(&result, opts);
    }
    result
}

pub fn put_acls(e: &mut Encoder, set: &AclSet, numeric_ids: bool) {
    if !set.complete {
        e.byte(0).var(0).var(0).var(0);
        return;
    }
    let records = export_acls(set, numeric_ids);
    e.byte(1).var(u64::from(records.flags));
    for list in [&records.access, &records.defaults] {
        e.var(list.len() as u64);
        for record in list {
            e.var(u64::from(record.tag));
            e.var(u64::from(record.permissions));
            e.var(u64::from(record.flags));
            e.var(u64::from(record.id));
            e.str(&record.name);
        }
    }
}

pub fn get_acls(d: &mut Decoder<'_>, kind: u8, opts: &Options) -> io::Result<AclSet> {
    let complete = d.byte().map_err(protocol::decode_err)?;
    let flags = d.var().map_err(protocol::decode_err)?;
    if complete > 1 || flags > u64::from(u32::MAX) {
        return protocol::bad("protocol error: malformed ACL header");
    }
    let mut records = AclRecords { complete: complete != 0, flags: flags as u32, access: Vec::new(), defaults: Vec::new() };
    for list in [&mut records.access, &mut records.defaults] {
        let count = d.var().map_err(protocol::decode_err)?;
        if count > MAX_RECORDS as u64 {
            return protocol::bad("protocol error: oversized or truncated ACL list");
        }
        for _ in 0..count {
            let tag = u32::try_from(d.var().map_err(protocol::decode_err)?)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed ACL entry"))?;
            let permissions = u32::try_from(d.var().map_err(protocol::decode_err)?)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed ACL entry"))?;
            let entry_flags = u32::try_from(d.var().map_err(protocol::decode_err)?)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed ACL entry"))?;
            let id = u32::try_from(d.var().map_err(protocol::decode_err)?)
                .map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "protocol error: malformed ACL entry"))?;
            let name = d.str().map_err(protocol::decode_err)?.to_vec();
            if name.len() > 255 {
                return protocol::bad("protocol error: malformed ACL entry");
            }
            list.push(AclRecord { tag, permissions, flags: entry_flags, id, name });
        }
    }
    if !valid(&records, kind) {
        return protocol::bad("protocol error: invalid ACL entries");
    }
    Ok(import_acls(records, opts))
}

/// Apply a received set, writing only what differs and using the destination
/// mode for the mode-linked owner/group/other/mask entries.
pub fn apply(source: &AclSet, path: &Path, kind: u8, mode: u32, opts: &Options) -> io::Result<bool> {
    if !source.complete || !opts.acls || !supported_type(kind) {
        return Ok(false);
    }
    let current = read_set(path, kind);
    if !current.complete {
        return Ok(false);
    }
    let changed = independent(&source.access) != independent(&current.access) || source.defaults != current.defaults;
    let desired = with_mode(&source.access, mode);
    if desired != current.access {
        write_value(path, ACCESS, &desired)?;
    }
    if kind == T_DIR && source.defaults != current.defaults {
        write_value(path, DEFAULT, &source.defaults)?;
    }
    Ok(changed)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record(tag: u32, permissions: u32, id: u32, name: &[u8]) -> Vec<u8> {
        let mut e = Encoder::new();
        e.var(u64::from(tag)).var(u64::from(permissions)).var(0).var(u64::from(id)).str(name);
        e.bytes
    }

    fn acl(access: &[Vec<u8>], defaults: &[Vec<u8>], complete: u8, flags: u32) -> Vec<u8> {
        let mut e = Encoder::new();
        e.byte(complete).var(u64::from(flags)).var(access.len() as u64);
        for value in access {
            e.raw(value);
        }
        e.var(defaults.len() as u64);
        for value in defaults {
            e.raw(value);
        }
        e.bytes
    }

    fn numeric() -> Options {
        Options { acls: true, numeric_ids: true, ..Options::default() }
    }

    fn linux(entries: &[(u16, u16, u32)]) -> Vec<u8> {
        let mut value = vec![2, 0, 0, 0];
        for &(tag, permissions, id) in entries {
            value.extend_from_slice(&tag.to_le_bytes());
            value.extend_from_slice(&permissions.to_le_bytes());
            value.extend_from_slice(&id.to_le_bytes());
        }
        value
    }

    #[test]
    fn the_record_encoding_is_the_bytes_put_acls_writes() {
        let set = AclSet {
            complete: true,
            access: linux(&[(1, 7, UNDEFINED), (2, 4, 60000), (4, 5, UNDEFINED), (16, 5, UNDEFINED), (32, 5, UNDEFINED)]),
            defaults: linux(&[(1, 7, UNDEFINED), (4, 5, UNDEFINED), (32, 5, UNDEFINED)]),
        };
        let mut e = Encoder::new();
        put_acls(&mut e, &set, true);
        let expected = [
            1, 0, 5, 1, 7, 0, 0xff, 0xff, 0xff, 0xff, 0x0f, 0, 2, 4, 0, 0xe0, 0xd4, 3, 0, 4, 5, 0, 0xff, 0xff, 0xff,
            0xff, 0x0f, 0, 16, 5, 0, 0xff, 0xff, 0xff, 0xff, 0x0f, 0, 32, 5, 0, 0xff, 0xff, 0xff, 0xff, 0x0f, 0, 3,
            1, 7, 0, 0xff, 0xff, 0xff, 0xff, 0x0f, 0, 4, 5, 0, 0xff, 0xff, 0xff, 0xff, 0x0f, 0, 32, 5, 0, 0xff, 0xff,
            0xff, 0xff, 0x0f, 0,
        ];
        assert_eq!(e.bytes, expected);
        let mut d = Decoder::new(&e.bytes);
        let parsed = get_acls(&mut d, T_DIR, &numeric()).unwrap();
        assert!(d.is_empty());
        assert_eq!(parsed, set);
    }

    #[test]
    fn a_named_id_keeps_the_numeric_identity_and_a_name_maps_on_import() {
        let bytes = acl(&[record(1, 6, UNDEFINED, b""), record(2, 4, 60000, b""), record(4, 4, UNDEFINED, b""),
            record(16, 4, UNDEFINED, b""), record(32, 4, UNDEFINED, b"")], &[], 1, 0);
        let parsed = get_acls(&mut Decoder::new(&bytes), T_REG, &numeric()).unwrap();
        assert_eq!(id_at(&parsed.access, 16), 60000);
        let named = acl(&[record(1, 6, UNDEFINED, b""), record(2, 4, 60000, b"root"), record(4, 4, UNDEFINED, b""),
            record(16, 4, UNDEFINED, b""), record(32, 4, UNDEFINED, b"")], &[], 1, 0);
        let opts = Options { acls: true, ..Options::default() };
        let parsed = get_acls(&mut Decoder::new(&named), T_REG, &opts).unwrap();
        assert_eq!(id_at(&parsed.access, 16), ffi::user_id(b"root").unwrap_or(60000));
    }

    #[test]
    fn an_incomplete_set_sends_an_empty_header() {
        let set = AclSet { complete: false, access: vec![1, 2, 3, 4], defaults: vec![5] };
        let mut e = Encoder::new();
        put_acls(&mut e, &set, true);
        assert_eq!(e.bytes, [0, 0, 0, 0]);
    }

    #[test]
    fn malformed_and_unbalanced_records_are_refused() {
        let bad = [
            b"".to_vec(),
            vec![2, 0, 0, 0],
            vec![1, 0x80],
            vec![1, 0, 0x80],
            acl(&[record(0, 4, UNDEFINED, b"")], &[], 1, 0),
            acl(&[record(1, 8, UNDEFINED, b"")], &[], 1, 0),
            acl(&[record(1, 4, 60000, b"")], &[], 1, 0),
            acl(&[record(1, 4, UNDEFINED, b"a\0b")], &[], 1, 0),
            acl(&[record(2, 4, 60000, b"")], &[], 1, 0),
            acl(&[record(1, 4, UNDEFINED, b"")], &[], 1, 1),
            acl(&[record(1, 4, UNDEFINED, b"")], &[record(1, 4, UNDEFINED, b"")], 1, 0),
            acl(&[record(1, 4, UNDEFINED, b"")], &[], 0, 0),
        ];
        for bytes in bad {
            assert!(get_acls(&mut Decoder::new(&bytes), T_REG, &numeric()).is_err(), "{bytes:?}");
        }
    }

    #[test]
    fn mode_linked_entries_are_the_destination_mode() {
        let value = linux(&[(1, 7, UNDEFINED), (2, 4, 60000), (4, 4, UNDEFINED), (16, 4, UNDEFINED), (32, 7, UNDEFINED)]);
        let adjusted = with_mode(&value, 0o640);
        assert_eq!(tag_at(&adjusted, 4), 1);
        assert_eq!(tag_at(&adjusted, 6), 6);
        assert_eq!(tag_at(&adjusted, 20), 4);
        assert_eq!(tag_at(&adjusted, 22), 4);
        assert_eq!(tag_at(&adjusted, 36), 32);
        assert_eq!(tag_at(&adjusted, 38), 0);
        assert_eq!(independent(&value), independent(&adjusted));
    }
}
