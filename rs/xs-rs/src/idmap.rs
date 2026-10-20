//! Name mapping and ownership overrides: `IdMaps` in remote.cpp and `Ownership`
//! in ownership.cpp. The wire records themselves live in `xs_wire::idmap`.

use std::collections::{HashMap, HashSet};

use xs_wire::idmap::{self, Entry as WireEntry};
use xs_wire::Frame;

use crate::ffi;
use crate::protocol::{feature, Attrs, Options};
use crate::scan::SourceEntry;

/// Sender state: each (kind, id) is described once per transfer.
#[derive(Default)]
pub struct Sender {
    sent: HashSet<(u8, u32)>,
}

impl Sender {
    fn record(&mut self, kind: u8, id: u32, wanted: bool, out: &mut Vec<WireEntry>) {
        if !wanted || !self.sent.insert((kind, id)) {
            return;
        }
        let name = if kind == idmap::USER { ffi::user_name(id) } else { ffi::group_name(id) };
        if let Some(name) = name {
            out.push(WireEntry { kind, id, name });
        }
    }

    /// The `F_IDMAP` frame for a directory and its entries, if any id is new.
    pub fn describe(&mut self, opts: &Options, features: u64, attrs: &Attrs, entries: &[SourceEntry]) -> Option<Frame> {
        if opts.numeric_ids
            || (!opts.owner && !opts.group && !opts.ownership.requested())
            || features & feature::IDMAP == 0
        {
            return None;
        }
        let users = opts.owner || opts.ownership.user_set;
        let groups = opts.group || opts.ownership.group_set;
        let mut records = Vec::new();
        self.record(idmap::USER, attrs.uid, users, &mut records);
        self.record(idmap::GROUP, attrs.gid, groups, &mut records);
        for entry in entries {
            self.record(idmap::USER, entry.meta.attrs.uid, users, &mut records);
            self.record(idmap::GROUP, entry.meta.attrs.gid, groups, &mut records);
        }
        if records.is_empty() {
            None
        } else {
            Some(idmap::encode(&records))
        }
    }
}

/// Receiver state: remote id to local id, as `IdMaps::learn` and `map`.
#[derive(Default)]
pub struct Receiver {
    uid: HashMap<u32, u32>,
    gid: HashMap<u32, u32>,
}

impl Receiver {
    pub fn learn(&mut self, payload: &[u8]) {
        for entry in idmap::decode(payload) {
            match entry.kind {
                idmap::USER => {
                    if let Some(id) = ffi::user_id(&entry.name) {
                        self.uid.insert(entry.id, id);
                    }
                }
                idmap::GROUP => {
                    if let Some(id) = ffi::group_id(&entry.name) {
                        self.gid.insert(entry.id, id);
                    }
                }
                _ => {}
            }
        }
    }

    /// Map names when `-o`/`-g` asked for them, then apply a local `--chown`.
    pub fn apply(&self, attrs: &mut Attrs, opts: &Options) {
        if opts.maps_names() {
            if let Some(&id) = self.uid.get(&attrs.uid) {
                attrs.uid = id;
            }
            if let Some(&id) = self.gid.get(&attrs.gid) {
                attrs.gid = id;
            }
        }
        attrs.uid = opts.ownership.uid_for(attrs.uid);
        attrs.gid = opts.ownership.gid_for(attrs.gid);
    }
}

/// The ids this process can actually set, as fs.cpp decides them.
pub fn targets(opts: &Options, attrs: &Attrs) -> (Option<u32>, Option<u32>) {
    let uid = if opts.owner && ffi::is_root() { Some(attrs.uid) } else { None };
    let gid = if opts.group && ffi::can_set_gid(attrs.gid) { Some(attrs.gid) } else { None };
    (uid, gid)
}

/// Apply `targets` to an open file before it is published.
pub fn chown_file(file: &std::fs::File, opts: &Options, attrs: &Attrs) {
    use std::os::unix::io::AsRawFd;
    let (uid, gid) = targets(opts, attrs);
    if uid.is_some() || gid.is_some() {
        let _ = ffi::fchown_fd(file.as_raw_fd(), uid, gid);
    }
}

/// Apply `targets` to a path; symlinks are changed without following them.
pub fn chown_path(path: &std::path::Path, opts: &Options, attrs: &Attrs, nofollow: bool) {
    let (uid, gid) = targets(opts, attrs);
    if uid.is_some() || gid.is_some() {
        let _ = ffi::chown_path(path, uid, gid, nofollow);
    }
}

#[cfg(test)]
mod tests {
    use crate::protocol::Ownership;

    #[test]
    fn numeric_names_resolve_without_libc() {
        let mut ownership = Ownership { user: b"1234".to_vec(), group: b"5678".to_vec(), user_set: true, group_set: true, ..Default::default() };
        ownership.init().unwrap();
        assert_eq!(ownership.uid_for(1), 1234);
        assert_eq!(ownership.gid_for(2), 5678);
        assert_eq!(ownership.uid_for(9), 1234);
    }

    #[test]
    fn a_missing_map_leaves_the_source_id_alone() {
        let ownership = Ownership::default();
        assert_eq!(ownership.uid_for(42), 42);
        assert_eq!(ownership.gid_for(43), 43);
    }

    #[test]
    fn a_numeric_id_above_a_u32_is_a_syntax_error() {
        let mut ownership = Ownership { user: b"4294967296".to_vec(), user_set: true, ..Default::default() };
        assert!(ownership.init().is_err());
    }
}
