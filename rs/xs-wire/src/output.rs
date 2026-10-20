//! Itemized output and progress acknowledgments: `F_OUTPUT`, `F_OUTPUT_CONFIG` and
//! `F_PROGRESS` as `send_output`, `handle_output`, `Receiver::acknowledge` and
//! `Conn::read_frame` frame them in `src/remote.cpp`.

use crate::codec::{DecodeError, Decoder, Encoder};
use crate::consts::{feature, frame_type};
use crate::frame::Frame;

/// Entry types carried by an output event, in the order of `common.h`.
pub mod file_type {
    pub const NONE: u8 = 0;
    pub const REG: u8 = 1;
    pub const DIR: u8 = 2;
    pub const LNK: u8 = 3;
    pub const FIFO: u8 = 4;
    pub const SOCK: u8 = 5;
    pub const CHR: u8 = 6;
    pub const BLK: u8 = 7;
}

/// One itemized file event, as `struct OutputEvent` in `src/output.h`.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct OutputEvent {
    pub code: Vec<u8>,
    pub path: Vec<u8>,
    pub source: Vec<u8>,
    pub target: Vec<u8>,
    pub kind: u8,
    pub size: i64,
    pub bytes: i64,
    pub time: i64,
    pub hardlink_target: bool,
}

impl OutputEvent {
    /// The frame `send_output` writes. The receiver includes the hard-link byte only
    /// when the peer negotiated `PF_HLINK`.
    pub fn encode(&self, features: u64) -> Frame {
        let mut e = Encoder::new();
        e.str(&self.code)
            .str(&self.path)
            .str(&self.source)
            .str(&self.target)
            .byte(self.kind)
            .var(self.size.max(0) as u64)
            .var(self.bytes.max(0) as u64)
            .svar(self.time);
        if features & feature::HLINK != 0 {
            e.byte(self.hardlink_target as u8);
        }
        Frame::new(frame_type::OUTPUT, e.into_bytes())
    }

    /// `handle_output`: refuse anything outside the frozen itemized-output grammar.
    pub fn decode(payload: &[u8], features: u64) -> Result<Self, DecodeError> {
        let mut d = Decoder::new(payload);
        let code = d.str()?.to_vec();
        let path = d.str()?.to_vec();
        let source = d.str()?.to_vec();
        let target = d.str()?.to_vec();
        let kind = d.byte()?;
        let size = i64::try_from(d.var()?).map_err(|_| bad("malformed file output"))?;
        let bytes = i64::try_from(d.var()?).map_err(|_| bad("malformed file output"))?;
        let time = d.svar()?;
        let hardlink_target = if features & feature::HLINK != 0 {
            match d.byte()? {
                value @ (0 | 1) => value != 0,
                _ => return Err(bad("protocol error: invalid hard-link output flag")),
            }
        } else {
            false
        };
        let expected = if features & feature::FILEFLAGS != 0 { 12 } else { 11 };
        if !d.is_empty()
            || kind > file_type::BLK
            || size < 0
            || bytes < 0
            || (code.len() != expected && code != b"*deleting  ")
            || code.iter().any(|&ch| !(32..127).contains(&ch))
        {
            return Err(bad("protocol error: malformed file output"));
        }
        Ok(Self { code, path, source, target, kind, size, bytes, time, hardlink_target })
    }
}

/// The largest `F_PROGRESS` the C++ accepts with these features.
pub fn max_progress_len(features: u64) -> u32 {
    if features & feature::APP_EVENTS != 0 {
        40
    } else if features & feature::STAGE_METRICS != 0 {
        30
    } else {
        20
    }
}

/// A receiver's completion snapshot. Optional words follow the negotiated features, as
/// `Receiver::acknowledge` writes them and the sender's reader parses them.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct ProgressAck {
    pub bytes: u64,
    pub files: u64,
    pub writing_ns: u64,
    pub completed_bytes: u64,
}

impl ProgressAck {
    pub fn encode(&self, features: u64) -> Frame {
        let mut e = Encoder::new();
        e.var(self.bytes).var(self.files);
        if features & feature::STAGE_METRICS != 0 {
            e.var(self.writing_ns);
        }
        if features & feature::APP_EVENTS != 0 {
            e.var(self.completed_bytes);
        }
        Frame::new(frame_type::PROGRESS, e.into_bytes())
    }

    pub fn decode(payload: &[u8], features: u64) -> Result<Self, DecodeError> {
        if features & feature::PROGRESS_ACK == 0 || payload.len() > max_progress_len(features) as usize {
            return Err(bad("protocol error: oversized or unnegotiated progress acknowledgment"));
        }
        let mut d = Decoder::new(payload);
        let bytes = d.var()?;
        let files = d.var()?;
        let writing_ns = if features & feature::STAGE_METRICS != 0 { d.var()? } else { 0 };
        let completed_bytes = if features & feature::APP_EVENTS != 0 { d.var()? } else { 0 };
        if !d.is_empty() {
            return Err(bad("protocol error: malformed progress acknowledgment"));
        }
        Ok(Self { bytes, files, writing_ns, completed_bytes })
    }
}

fn bad(why: &str) -> DecodeError {
    DecodeError::Invalid(why.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn output_event_bytes_are_the_ones_send_output_writes() {
        let event = OutputEvent {
            code: b">f+++++++++".to_vec(),
            path: b"a".to_vec(),
            source: b"/src/a".to_vec(),
            target: vec![],
            kind: file_type::REG,
            size: 5,
            bytes: 5,
            time: 1_700_000_000,
            hardlink_target: false,
        };
        let expected = Frame::new(
            11,
            [
                11, b'>', b'f', b'+', b'+', b'+', b'+', b'+', b'+', b'+', b'+', b'+', 1, b'a', 6, b'/', b's', b'r', b'c',
                b'/', b'a', 0, 1, 5, 5, 0x80, 0xc4, 0x9f, 0xd5, 0x0c,
            ]
            .to_vec(),
        );
        assert_eq!(event.encode(feature::CORE).to_bytes(), expected.to_bytes());
        assert_eq!(OutputEvent::decode(&expected.payload, feature::CORE).unwrap(), event);
        assert_eq!(OutputEvent::decode(&event.encode(feature::CORE).payload, feature::CORE).unwrap(), event);
    }

    #[test]
    fn hard_link_and_file_flag_fields_are_conditional() {
        let event = OutputEvent {
            code: b".f....f.....".to_vec(),
            path: b"x".to_vec(),
            kind: file_type::REG,
            hardlink_target: true,
            ..OutputEvent::default()
        };
        let frame = event.encode(feature::CORE | feature::HLINK | feature::FILEFLAGS);
        assert_eq!(OutputEvent::decode(&frame.payload, feature::CORE | feature::HLINK | feature::FILEFLAGS).unwrap(), event);
        let without = OutputEvent { hardlink_target: false, ..event.clone() };
        assert!(OutputEvent::decode(&frame.payload, feature::CORE | feature::FILEFLAGS).is_err());
        assert!(OutputEvent::decode(
            &without.encode(feature::CORE | feature::FILEFLAGS).payload,
            feature::CORE | feature::HLINK | feature::FILEFLAGS
        )
        .is_err());
    }

    #[test]
    fn hostile_output_events_are_refused() {
        let valid = OutputEvent {
            code: b">f+++++++++".to_vec(),
            path: b"p".to_vec(),
            kind: file_type::REG,
            ..OutputEvent::default()
        }
        .encode(feature::CORE);
        let mut trailing = valid.payload.clone();
        trailing.push(b'x');
        assert!(OutputEvent::decode(&trailing, feature::CORE).is_err());
        let mut control = valid.clone();
        control.payload[0] = b'\x1b';
        assert!(OutputEvent::decode(&control.payload, feature::CORE).is_err());
        let negative = {
            let mut e = Encoder::new();
            e.str(b">f+++++++++").str(b"p").str(b"").str(b"").byte(1).var(u64::MAX).var(0).svar(0);
            e.bytes
        };
        assert!(OutputEvent::decode(&negative, feature::CORE).is_err());
        let deleting =
            OutputEvent { code: b"*deleting  ".to_vec(), path: b"gone".to_vec(), ..OutputEvent::default() };
        assert_eq!(OutputEvent::decode(&deleting.encode(feature::CORE).payload, feature::CORE).unwrap(), deleting);
    }

    #[test]
    fn progress_words_match_the_feature_set_and_are_bounded() {
        assert_eq!(ProgressAck { bytes: 1, files: 2, ..ProgressAck::default() }.encode(feature::CORE).payload, [1, 2]);
        let features = feature::CORE | feature::PROGRESS_ACK | feature::STAGE_METRICS | feature::APP_EVENTS;
        let frame = ProgressAck { bytes: 300, files: 4, writing_ns: 5, completed_bytes: 6 }.encode(features);
        assert_eq!(frame.payload, [0xac, 2, 4, 5, 6]);
        assert_eq!(
            ProgressAck::decode(&frame.payload, features).unwrap(),
            ProgressAck { bytes: 300, files: 4, writing_ns: 5, completed_bytes: 6 }
        );
        assert!(ProgressAck::decode(&[0, 0], feature::CORE).is_err());
        assert!(ProgressAck::decode(&[0; 21], feature::CORE | feature::PROGRESS_ACK).is_err());
        assert!(ProgressAck::decode(&[0, 0, 0], feature::CORE | feature::PROGRESS_ACK).is_err());
    }
}
