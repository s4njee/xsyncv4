//! Protocol constants, with the values `src/common.h` and `src/remote.cpp` give them.

/// The frame magic at the start of each HELLO (`MAGIC` in remote.cpp, without its terminating NUL).
pub const MAGIC: &[u8; 6] = b"XSYNC\x01";
/// `PROTO_VERSION` and `PROTO_MIN_VERSION`: a server accepts a client from 3 to 4.
pub const PROTO_VERSION: u64 = 4;
pub const PROTO_MIN_VERSION: u64 = 3;
/// Version 3 has no feature word; it implies these (`LEGACY_V3_FEATURES`).
pub const LEGACY_V3_FEATURES: u64 = 15;
/// Bytes of a frame header: `u32` payload length (little-endian) and `u8` type.
pub const HEADER_LEN: usize = 5;
/// The largest payload a peer accepts (`1u << 30`).
pub const MAX_PAYLOAD: u32 = 1 << 30;

/// Frame types, numbered from 1 in the order of remote.cpp's enum.
pub mod frame_type {
    pub const HELLO: u8 = 1;
    pub const DIR: u8 = 2;
    pub const NEED: u8 = 3;
    pub const DATA: u8 = 4;
    pub const LIST_END: u8 = 5;
    pub const DATA_END: u8 = 6;
    pub const DONE: u8 = 7;
    pub const MSG: u8 = 8;
    pub const IDMAP: u8 = 9;
    pub const DEST: u8 = 10;
    pub const OUTPUT: u8 = 11;
    pub const OUTPUT_CONFIG: u8 = 12;
    pub const DELTA_REQUEST: u8 = 13;
    pub const DELTA_SIGNATURE: u8 = 14;
    pub const DELTA_RETRY_ACK: u8 = 15;
    pub const LIST_ENTRY: u8 = 16;
    pub const IO_CONFIG: u8 = 17;
    pub const KEEPALIVE: u8 = 18;
    pub const FILTER_CONFIG: u8 = 19;
    pub const DELETE_CONFIG: u8 = 20;
    pub const PRUNE_CONFIG: u8 = 21;
    pub const RELATIVE_CONFIG: u8 = 22;
    pub const FILES_CONFIG: u8 = 23;
    pub const FILES_DATA: u8 = 24;
    pub const FILES_END: u8 = 25;
    pub const XATTR_CONFIG: u8 = 26;
    pub const XATTR_START: u8 = 27;
    pub const XATTR_CHUNK: u8 = 28;
    pub const XATTR_END: u8 = 29;
    pub const ACL_CONFIG: u8 = 30;
    pub const CHOWN_CONFIG: u8 = 31;
    pub const SPARSE_CONFIG: u8 = 32;
    pub const LINKDEST_CONFIG: u8 = 33;
    pub const PROGRESS: u8 = 34;
    pub const STAGE: u8 = 35;
    pub const PHASE: u8 = 36;
    pub const COMPRESS_CONFIG: u8 = 37;
    pub const APP_EVENT: u8 = 38;
    pub const APP_CONTROL: u8 = 39;
    pub const APP_END: u8 = 40;
}

/// Directory frame flags (`DF_*`).
pub mod dir_flag {
    pub const ATTRS: u8 = 1;
    pub const SINGLE: u8 = 2;
    pub const NODELETE: u8 = 4;
    pub const ZSTD: u8 = 8;
    pub const APP_SCAN_FAILED: u8 = 16;
}

/// Record kinds inside a DATA frame (`R_*`).
pub mod record {
    pub const WHOLE: u8 = 1;
    pub const CHUNK: u8 = 2;
    pub const FAIL: u8 = 4;
    pub const END: u8 = 8;
    pub const LITERAL: u8 = 16;
    pub const DELTA_END: u8 = 32;
    pub const COPY: u8 = 64;
}

/// `F_MSG` kinds: plain output, an error, or a fatal error after which the sender exits.
pub mod msg_kind {
    pub const OUT: u8 = 0;
    pub const ERROR: u8 = 1;
    pub const FATAL: u8 = 2;
}

/// Feature bits (`PF_*`). The negotiated set is what both sides advertise.
pub mod feature {
    pub const CORE: u64 = 1;
    pub const ZSTD: u64 = 1 << 1;
    pub const IDMAP: u64 = 1 << 2;
    pub const SAFE_LINKS: u64 = 1 << 3;
    pub const RESUME: u64 = 1 << 4;
    pub const OUTPUT: u64 = 1 << 5;
    pub const DIR_OUTPUT: u64 = 1 << 6;
    pub const HLINK: u64 = 1 << 7;
    pub const DELTA: u64 = 1 << 8;
    pub const LIST: u64 = 1 << 9;
    pub const IO_CONTROL: u64 = 1 << 10;
    pub const FILTERS: u64 = 1 << 11;
    pub const MERGE_FILTERS: u64 = 1 << 12;
    pub const CVS_FILTERS: u64 = 1 << 13;
    pub const DELETE_AFTER: u64 = 1 << 14;
    pub const PRUNE_EMPTY: u64 = 1 << 15;
    pub const RELATIVE: u64 = 1 << 16;
    pub const FILES_FROM: u64 = 1 << 17;
    pub const XATTRS: u64 = 1 << 18;
    pub const XATTR_STREAM: u64 = 1 << 19;
    pub const ACL_POSIX: u64 = 1 << 20;
    pub const ACL_DARWIN: u64 = 1 << 21;
    pub const ACL_UUID: u64 = 1 << 22;
    pub const ATIMES: u64 = 1 << 23;
    pub const CRTIMES: u64 = 1 << 24;
    pub const OPEN_NOATIME: u64 = 1 << 25;
    pub const EXECUTABILITY: u64 = 1 << 26;
    pub const FILEFLAGS: u64 = 1 << 27;
    pub const CHOWN: u64 = 1 << 28;
    pub const SPARSE: u64 = 1 << 29;
    pub const LINK_DEST: u64 = 1 << 30;
    pub const PROGRESS_ACK: u64 = 1 << 31;
    pub const STAGE_METRICS: u64 = 1 << 32;
    pub const PROGRESS_PHASE: u64 = 1 << 33;
    pub const COMPRESS_POLICY: u64 = 1 << 34;
    pub const DIR_CHILDREN: u64 = 1 << 35;
    pub const APP_EVENTS: u64 = 1 << 36;
    pub const APP_CONTROLS: u64 = 1 << 37;
    pub const APP_LEASE: u64 = 1 << 38;
    pub const APP_PARTIALS: u64 = 1 << 39;
}

/// The boolean options of HELLO, one byte each, in `WIRE_V3_BOOL_OPTS` order.
pub const BOOL_OPTIONS: [&str; 32] = [
    "recursive",
    "dirs",
    "links",
    "copy_links",
    "perms",
    "times",
    "group",
    "owner",
    "devices",
    "specials",
    "compress",
    "dry_run",
    "del",
    "delete_excluded",
    "force",
    "update",
    "checksum",
    "size_only",
    "ignore_times",
    "ignore_existing",
    "existing",
    "one_fs",
    "inplace",
    "omit_dir_times",
    "omit_link_times",
    "numeric_ids",
    "itemize",
    "partial",
    "clone",
    "direct_new",
    "ignore_errors",
    "safe_links",
];

/// The integer options of HELLO, each an `svar`, in `WIRE_V3_INT_OPTS` order.
pub const INT_OPTIONS: [&str; 7] = ["verbose", "compress_level", "max_size", "min_size", "modify_window", "jobs", "max_delete"];
