//! `F_IDMAP`: the sender describes a numeric user or group id by name so the
//! receiver can translate it to its own local id. `IdMaps::describe` and
//! `IdMaps::learn` in remote.cpp are the reference.
//!
//! A payload is a sequence of records, each a kind byte (0 user, 1 group), the
//! remote id as a `var`, and the name as a `str`. The C++ receiver stops at a
//! truncated record rather than failing the transfer, so `Entries` does too.

use crate::codec::{Decoder, Encoder};
use crate::consts::frame_type;
use crate::frame::Frame;

pub const USER: u8 = 0;
pub const GROUP: u8 = 1;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    pub kind: u8,
    pub id: u32,
    pub name: Vec<u8>,
}

/// One frame holding every record, as `describe` sends one `F_IDMAP` per listing.
pub fn encode(entries: &[Entry]) -> Frame {
    let mut e = Encoder::new();
    for entry in entries {
        e.byte(entry.kind).var(entry.id as u64).str(&entry.name);
    }
    Frame::new(frame_type::IDMAP, e.into_bytes())
}

/// The records in a payload, stopping where `RBuf` would go bad.
pub fn decode(payload: &[u8]) -> Vec<Entry> {
    let mut d = Decoder::new(payload);
    let mut entries = Vec::new();
    while let Ok(kind) = d.byte() {
        let Ok(id) = d.var() else { break };
        let Ok(name) = d.str() else { break };
        entries.push(Entry { kind, id: id as u32, name: name.to_vec() });
    }
    entries
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn records_have_the_bytes_describe_writes() {
        let entries = [Entry { kind: USER, id: 1000, name: b"alice".to_vec() }, Entry { kind: GROUP, id: 20, name: b"staff".to_vec() }];
        let frame = encode(&entries);
        assert_eq!(
            frame.to_bytes(),
            [17, 0, 0, 0, 9, 0, 0xe8, 0x07, 5, b'a', b'l', b'i', b'c', b'e', 1, 20, 5, b's', b't', b'a', b'f', b'f']
        );
        assert_eq!(decode(&frame.payload), entries);
    }

    #[test]
    fn an_id_above_a_u32_is_truncated_as_the_cpp_cast_does() {
        let mut e = Encoder::new();
        e.byte(USER).var(1 << 32).str("x");
        assert_eq!(decode(&e.bytes), [Entry { kind: USER, id: 0, name: b"x".to_vec() }]);
    }

    #[test]
    fn a_truncated_record_ends_the_list_instead_of_failing() {
        let mut e = Encoder::new();
        e.byte(GROUP).var(7).str("good");
        e.byte(USER).var(8).str("cut");
        let cut = &e.bytes[..e.bytes.len() - 1];
        assert_eq!(decode(cut), [Entry { kind: GROUP, id: 7, name: b"good".to_vec() }]);
        assert!(decode(&[USER]).is_empty());
        assert!(decode(&[USER, 1]).is_empty());
    }
}
