//! The transfer frames after HELLO: DIR entries, NEED, DATA records and the ends.
//! Field order and limits are those of `put_file_attrs`, `Sender::walk`, `on_need`,
//! `Receiver::parse_dir`, `Sender::read_one` and `Receiver::data` in src/remote.cpp.

use std::io;

use xs_wire::{Decoder, Encoder};

pub use xs_wire::consts::dir_flag;
pub use xs_wire::consts::feature;
pub use xs_wire::consts::frame_type;
pub use xs_wire::consts::msg_kind;
pub use xs_wire::consts::record as rec;

pub const T_NONE: u8 = 0;
pub const T_REG: u8 = 1;
pub const T_DIR: u8 = 2;
pub const T_LNK: u8 = 3;
pub const T_FIFO: u8 = 4;
pub const T_SOCK: u8 = 5;
pub const T_CHR: u8 = 6;
pub const T_BLK: u8 = 7;

pub const DF_ATTRS: u8 = dir_flag::ATTRS;
pub const DF_SINGLE: u8 = dir_flag::SINGLE;
pub const DF_ZSTD: u8 = dir_flag::ZSTD;

pub const SMALL_MAX: u64 = 512 << 10;
pub const BLOCK_TARGET: usize = 1 << 20;

pub type Res<T> = io::Result<T>;

pub fn bad<T>(message: impl Into<String>) -> Res<T> {
    Err(io::Error::new(io::ErrorKind::InvalidData, message.into()))
}

pub fn decode_err(error: xs_wire::DecodeError) -> io::Error {
    let text = error.to_string();
    let text = if text.starts_with("protocol error") { text } else { format!("protocol error: {text}") };
    io::Error::new(io::ErrorKind::InvalidData, text)
}

/// Read the next frame, consuming legal keep-alives as `Conn::read_frame` does. A keep-alive
/// before `F_IO_CONFIG` is negotiated, or one carrying a payload, is a protocol error.
pub fn read_checked<R: io::Read>(input: &mut R, negotiated: bool, features: u64) -> io::Result<Option<xs_wire::Frame>> {
    loop {
        let Some(frame) = xs_wire::read_frame(input)
            .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error.to_string()))?
        else {
            return Ok(None);
        };
        if frame.kind == frame_type::KEEPALIVE {
            if !xs_wire::io_control::valid_keepalive(&frame, negotiated) {
                return bad("protocol error: invalid or unnegotiated keep-alive");
            }
            continue;
        }
        if frame.kind == frame_type::PROGRESS
            && (features & feature::PROGRESS_ACK == 0
                || frame.payload.len() > xs_wire::output::max_progress_len(features) as usize)
        {
            return bad("protocol error: oversized or unnegotiated progress acknowledgment");
        }
        return Ok(Some(frame));
    }
}

#[derive(Clone, Debug, Default)]
pub struct Attrs {
    pub mode: u32,
    pub uid: u32,
    pub gid: u32,
    pub mtime: i64,
    pub mtime_ns: u32,
    #[allow(dead_code)]
    pub atime: i64,
    /// `st_size`, sent for directories and non-regular entries with `PF_OUTPUT`.
    pub size: i64,
    /// The source inode fields `PF_HLINK` carries, in `put_file_attrs` order.
    pub hdev: u64,
    pub ino: u64,
    pub nlink: u64,
    pub ctime: i64,
    pub ctime_ns: u32,
}

/// What the C++ calls an entry's identity for hard-link grouping. Directories
/// are never hard-linked; a symlink's target keeps its aliases apart.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct HardlinkKey {
    pub dev: u64,
    pub ino: u64,
    pub kind: u8,
    pub target: Vec<u8>,
}

impl Attrs {
    pub fn hardlink_key(&self, kind: u8, target: &[u8]) -> Option<HardlinkKey> {
        if self.nlink < 2 || kind == T_DIR || kind == T_NONE {
            return None;
        }
        Some(HardlinkKey {
            dev: self.hdev,
            ino: self.ino,
            kind,
            target: if kind == T_LNK { target.to_vec() } else { Vec::new() },
        })
    }
}

pub fn put_hlink(e: &mut Encoder, a: &Attrs) {
    e.var(a.hdev).var(a.ino).var(a.nlink).svar(a.ctime).var(a.ctime_ns as u64);
}

pub fn get_hlink(d: &mut Decoder<'_>) -> Res<(u64, u64, u64, i64, u32)> {
    let hdev = d.var().map_err(decode_err)?;
    let ino = d.var().map_err(decode_err)?;
    let nlink = d.var().map_err(decode_err)?;
    let ctime = d.svar().map_err(decode_err)?;
    let ctime_ns = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("ctime nanoseconds"))?;
    Ok((hdev, ino, nlink, ctime, ctime_ns))
}

#[derive(Clone, Debug)]
pub struct EntryMeta {
    pub name: Vec<u8>,
    pub kind: u8,
    pub attrs: Attrs,
    pub size: i64,
    pub link: Vec<u8>,
    pub rdev: u32,
    /// The sender's source path, carried by every entry when `PF_OUTPUT` is negotiated.
    pub output_source: Vec<u8>,
}

/// DIR header attributes, in `put_var(mode), put_svar(mtime), put_var(mtime_ns), uid, gid` order.
pub fn put_dir_attrs(e: &mut Encoder, a: &Attrs, features: u64) {
    e.var(a.mode as u64).svar(a.mtime).var(a.mtime_ns as u64).var(a.uid as u64).var(a.gid as u64);
    if features & feature::ATIMES != 0 {
        e.svar(a.atime);
    }
}

pub fn get_dir_attrs(d: &mut Decoder<'_>, features: u64) -> Res<Attrs> {
    let mode = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("directory mode"))? & 0o7777;
    let mtime = d.svar().map_err(decode_err)?;
    let mtime_ns = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("directory mtime nanoseconds"))?;
    let uid = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("directory uid"))?;
    let gid = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("directory gid"))?;
    let atime = if features & feature::ATIMES != 0 { d.svar().map_err(decode_err)? } else { 0 };
    Ok(Attrs { mode, uid, gid, mtime, mtime_ns, atime, size: 0, ..Attrs::default() })
}

pub fn put_entry(e: &mut Encoder, entry: &EntryMeta, opts: &Options, features: u64) {
    e.str(&entry.name).byte(entry.kind).var(entry.attrs.mode as u64).svar(entry.attrs.mtime).var(entry.attrs.mtime_ns as u64);
    if opts.owner || features & feature::CHOWN != 0 {
        e.var(entry.attrs.uid as u64);
    }
    if opts.group || features & feature::CHOWN != 0 {
        e.var(entry.attrs.gid as u64);
    }
    if features & feature::ATIMES != 0 {
        e.svar(entry.attrs.atime);
    }
    match entry.kind {
        T_REG => {
            e.var(entry.size.max(0) as u64);
        }
        T_DIR => {
            e.var(0);
            if features & (feature::RELATIVE | feature::FILES_FROM) != 0 {
                e.byte(0);
            }
        }
        T_LNK => {
            e.str(&entry.link);
        }
        T_CHR | T_BLK => {
            e.var(entry.rdev as u64);
        }
        _ => {}
    }
    if features & feature::HLINK != 0 {
        put_hlink(e, &entry.attrs);
    }
    if features & feature::OUTPUT != 0 {
        if entry.kind != T_REG {
            e.var(entry.size.max(0) as u64);
        }
        e.str(&entry.output_source);
    }
}

pub fn get_entry(d: &mut Decoder<'_>, opts: &Options, features: u64) -> Res<EntryMeta> {
    let name = d.str().map_err(decode_err)?.to_vec();
    if name.is_empty() || name == b"." || name == b".." || name.contains(&b'/') || name.contains(&0) {
        return bad("protocol error: unsafe file name from sender");
    }
    let kind = d.byte().map_err(decode_err)?;
    let mode = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("entry mode"))? & 0o7777;
    let mtime = d.svar().map_err(decode_err)?;
    let mtime_ns = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("entry mtime nanoseconds"))?;
    let uid = if opts.owner || features & feature::CHOWN != 0 {
        u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("entry uid"))?
    } else {
        0
    };
    let gid = if opts.group || features & feature::CHOWN != 0 {
        u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("entry gid"))?
    } else {
        0
    };
    let atime = if features & feature::ATIMES != 0 { d.svar().map_err(decode_err)? } else { 0 };
    let mut attrs = Attrs { mode, uid, gid, mtime, mtime_ns, atime, size: 0, ..Attrs::default() };
    let mut size = 0i64;
    let mut link = Vec::new();
    let mut rdev = 0u32;
    match kind {
        T_REG => {
            size = i64::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("file size"))?;
        }
        T_DIR => {
            rdev = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("directory rdev"))?;
            if features & (feature::RELATIVE | feature::FILES_FROM) != 0 && d.byte().map_err(decode_err)? > 1 {
                return bad("protocol error: bad selected directory flag");
            }
        }
        T_LNK => {
            link = d.str().map_err(decode_err)?.to_vec();
            if link.contains(&0) {
                return bad("protocol error: NUL in symlink target");
            }
        }
        T_CHR | T_BLK => {
            rdev = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("device rdev"))?;
        }
        _ => {}
    }
    if features & feature::HLINK != 0 {
        (attrs.hdev, attrs.ino, attrs.nlink, attrs.ctime, attrs.ctime_ns) = get_hlink(d)?;
    }
    let mut output_source = Vec::new();
    if features & feature::OUTPUT != 0 {
        if kind != T_REG {
            size = i64::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("entry size"))?;
        }
        attrs.size = size;
        output_source = d.str().map_err(decode_err)?.to_vec();
    }
    Ok(EntryMeta { name, kind, attrs, size, link, rdev, output_source })
}

/// File attributes inside DATA records: mode, uid, gid, mtime, nanoseconds.
pub fn put_file_attrs(e: &mut Encoder, a: &Attrs, features: u64) {
    e.var(a.mode as u64).var(a.uid as u64).var(a.gid as u64).svar(a.mtime).var(a.mtime_ns as u64);
    if features & feature::ATIMES != 0 {
        e.svar(a.atime);
    }
    if features & feature::HLINK != 0 {
        put_hlink(e, a);
    }
}

pub fn get_file_attrs(d: &mut Decoder<'_>, features: u64) -> Res<Attrs> {
    let mode = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("file mode"))? & 0o7777;
    let uid = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("file uid"))?;
    let gid = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("file gid"))?;
    let mtime = d.svar().map_err(decode_err)?;
    let mtime_ns = u32::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("file mtime nanoseconds"))?;
    let atime = if features & feature::ATIMES != 0 { d.svar().map_err(decode_err)? } else { 0 };
    let mut attrs = Attrs { mode, uid, gid, mtime, mtime_ns, atime, size: 0, ..Attrs::default() };
    if features & feature::HLINK != 0 {
        (attrs.hdev, attrs.ino, attrs.nlink, attrs.ctime, attrs.ctime_ns) = get_hlink(d)?;
    }
    Ok(attrs)
}

fn io_err(what: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, format!("protocol error: bad {what}"))
}

/// `--chown` and the `F_CHOWN_CONFIG` fields, as `OwnershipOverride` in ownership.h.
#[derive(Clone, Debug, Default)]
pub struct Ownership {
    pub user: Vec<u8>,
    pub group: Vec<u8>,
    pub user_set: bool,
    pub group_set: bool,
    pub uid: Option<u32>,
    pub gid: Option<u32>,
}

impl Ownership {
    pub fn requested(&self) -> bool {
        self.user_set || self.group_set
    }

    /// Resolve names and numeric ids once, as `init_ownership` does. An unknown
    /// name leaves that field unset; an id above a `u32` is a syntax error.
    pub fn init(&mut self) -> Result<(), String> {
        self.uid = None;
        self.gid = None;
        if self.user_set {
            self.uid = resolve(&self.user, crate::ffi::user_id)?;
            if self.uid.is_none() {
                eprintln!("xs-rs: Unknown --usermap name on receiver: {}", String::from_utf8_lossy(&self.user));
            }
        }
        if self.group_set {
            self.gid = resolve(&self.group, crate::ffi::group_id)?;
            if self.gid.is_none() {
                eprintln!("xs-rs: Unknown --groupmap name on receiver: {}", String::from_utf8_lossy(&self.group));
            }
        }
        Ok(())
    }

    pub fn uid_for(&self, source: u32) -> u32 {
        self.uid.unwrap_or(source)
    }

    pub fn gid_for(&self, source: u32) -> u32 {
        self.gid.unwrap_or(source)
    }
}

fn resolve(name: &[u8], lookup: fn(&[u8]) -> Option<u32>) -> Result<Option<u32>, String> {
    if !name.is_empty() && name.iter().all(u8::is_ascii_digit) {
        let mut value = 0u64;
        for &byte in name {
            value = value * 10 + u64::from(byte - b'0');
            if value > u32::MAX as u64 {
                return Err(format!("Invalid ID number: {}", String::from_utf8_lossy(name)));
            }
        }
        Ok(Some(value as u32))
    } else {
        Ok(lookup(name))
    }
}

#[derive(Clone, Debug)]
pub struct Options {
    pub recursive: bool,
    pub links: bool,
    pub copy_links: bool,
    pub perms: bool,
    pub times: bool,
    pub group: bool,
    pub owner: bool,
    pub devices: bool,
    pub specials: bool,
    pub compress: bool,
    pub numeric_ids: bool,
    /// `-j/--jobs`; zero means the default worker budget (four), as the wire's
    /// INT_OPTIONS value does for the C++ engine.
    pub jobs: i64,
    pub compress_level: i64,
    pub compress_level_explicit: bool,
    pub skip_compress: Vec<u8>,
    pub skip_compress_set: bool,
    pub ownership: Ownership,
    pub bwlimit: u64,
    pub timeout: u32,
    pub itemize_level: u32,
    pub out_format: Vec<u8>,
    pub out_format_set: bool,
    pub output_attrs: bool,
    pub output_unchanged: bool,
    pub mkpath: bool,
    pub delete_before: bool,
    pub progress: bool,
    pub partial: bool,
    pub whole_file: bool,
    pub ignore_times: bool,
    pub raw_names: bool,
    pub hard_links: bool,
    pub am_server: bool,
    pub pushing: bool,
    pub local_peer: bool,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            recursive: false,
            links: false,
            copy_links: false,
            perms: false,
            times: false,
            group: false,
            owner: false,
            devices: false,
            specials: false,
            compress: false,
            numeric_ids: false,
            jobs: 0,
            compress_level: 3,
            compress_level_explicit: false,
            skip_compress: xs_wire::DEFAULT_SKIP_COMPRESS.as_bytes().to_vec(),
            skip_compress_set: false,
            ownership: Ownership::default(),
            bwlimit: 0,
            timeout: 0,
            itemize_level: 0,
            out_format: Vec::new(),
            out_format_set: false,
            output_attrs: false,
            output_unchanged: false,
            mkpath: false,
            delete_before: false,
            progress: false,
            partial: false,
            whole_file: false,
            ignore_times: false,
            raw_names: false,
            hard_links: false,
            am_server: false,
            pushing: false,
            local_peer: false,
        }
    }
}

impl Options {
    /// The C++ receiver maps names only for `-o`/`-g` and not `--numeric-ids`.
    pub fn maps_names(&self) -> bool {
        (self.owner || self.group) && !self.numeric_ids
    }

    /// `output_enabled` for the flags this client implements.
    pub fn output_enabled(&self, verbose: i64) -> bool {
        self.itemize_level > 0 || verbose > 0 || self.out_format_set
    }

    /// `output_configure`: `-i` and a format with `%i` need attributes, `-ii` unchanged rows.
    pub fn configure_output(&mut self) {
        self.output_attrs = self.itemize_level > 0 || self.out_format.contains(&b'i');
        self.output_unchanged = self.itemize_level > 1;
    }
}

/// Append a compressed body when `compress` is on: `var raw_len` then one independent
/// zstd frame. This is `pack` in remote.cpp: small bodies and blocks whose sample does
/// not shrink are left raw, and compression is kept only when it is smaller.
pub fn pack_body(frame: &mut Encoder, body: &[u8], compress: bool, level: i32) -> bool {
    if !compress || body.len() < 128 || !crate::compression::worthwhile(body) {
        frame.raw(body);
        return false;
    }
    let (minimum, maximum) = crate::ffi::zstd_level_bounds();
    let level = level.clamp(minimum, maximum);
    match crate::ffi::zstd_compress_exact(body, level) {
        Ok(compressed) if compressed.len() < body.len() => {
            frame.var(body.len() as u64).raw(&compressed);
            true
        }
        _ => {
            frame.raw(body);
            false
        }
    }
}

pub fn unpack_body(input: &[u8], compressed: bool, features: u64) -> Res<Vec<u8>> {
    if !compressed {
        return Ok(input.to_vec());
    }
    if features & feature::ZSTD == 0 {
        return bad("compressed data without negotiated zstd support");
    }
    let mut d = Decoder::new(input);
    let raw = usize::try_from(d.var().map_err(decode_err)?).map_err(|_| io_err("compressed size"))?;
    if raw > 1 << 30 {
        return bad("protocol error: bad compressed frame");
    }
    crate::ffi::zstd_decompress(d.rest(), raw)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn attrs() -> Attrs {
        Attrs {
            mode: 0o644,
            uid: 1000,
            gid: 100,
            mtime: 1,
            mtime_ns: 5,
            size: 3,
            hdev: 2049,
            ino: 42,
            nlink: 2,
            ctime: -5,
            ctime_ns: 7,
            ..Attrs::default()
        }
    }

    #[test]
    fn file_attrs_carry_hlink_after_times_as_put_file_attrs_writes_them() {
        let mut e = Encoder::new();
        put_file_attrs(&mut e, &attrs(), feature::CORE | feature::HLINK);
        assert_eq!(e.bytes, [0xa4, 0x03, 0xe8, 0x07, 0x64, 0x02, 0x05, 0x81, 0x10, 0x2a, 0x02, 0x09, 0x07]);
        let mut d = Decoder::new(&e.bytes);
        let parsed = get_file_attrs(&mut d, feature::CORE | feature::HLINK).unwrap();
        assert!(d.is_empty());
        assert_eq!((parsed.hdev, parsed.ino, parsed.nlink, parsed.ctime, parsed.ctime_ns), (2049, 42, 2, -5, 7));

        let mut without = Encoder::new();
        put_file_attrs(&mut without, &attrs(), feature::CORE);
        assert_eq!(without.bytes, [0xa4, 0x03, 0xe8, 0x07, 0x64, 0x02, 0x05]);
        let mut d = Decoder::new(&without.bytes);
        let parsed = get_file_attrs(&mut d, feature::CORE).unwrap();
        assert_eq!((parsed.hdev, parsed.ino, parsed.nlink), (0, 0, 0));
    }

    #[test]
    fn a_directory_entry_puts_hlink_after_its_kind_fields_and_before_output() {
        let entry = EntryMeta {
            name: b"a".to_vec(),
            kind: T_REG,
            attrs: attrs(),
            size: 3,
            link: Vec::new(),
            rdev: 0,
            output_source: b"/s/a".to_vec(),
        };
        let opts = Options { owner: true, group: true, ..Options::default() };
        let features = feature::CORE | feature::HLINK | feature::OUTPUT;
        let mut e = Encoder::new();
        put_entry(&mut e, &entry, &opts, features);
        assert_eq!(
            e.bytes,
            [
                1, b'a', 1, 0xa4, 0x03, 0x02, 0x05, 0xe8, 0x07, 0x64, 3, 0x81, 0x10, 0x2a, 0x02, 0x09, 0x07, 4, b'/',
                b's', b'/', b'a'
            ]
        );
        let mut d = Decoder::new(&e.bytes);
        let parsed = get_entry(&mut d, &opts, features).unwrap();
        assert!(d.is_empty());
        assert_eq!(parsed.name, entry.name);
        assert_eq!(parsed.attrs.hdev, 2049);
        assert_eq!(parsed.attrs.ino, 42);
        assert_eq!(parsed.attrs.nlink, 2);
        assert_eq!(parsed.attrs.ctime, -5);
        assert_eq!(parsed.output_source, b"/s/a");
    }

    #[test]
    fn only_a_linked_non_directory_forms_a_hard_link_group() {
        let linked = attrs();
        assert!(linked.hardlink_key(T_REG, b"").is_some());
        assert!(linked.hardlink_key(T_LNK, b"target").is_some());
        assert!(linked.hardlink_key(T_DIR, b"").is_none());
        let single = Attrs { nlink: 1, ..attrs() };
        assert!(single.hardlink_key(T_REG, b"").is_none());
    }
}
