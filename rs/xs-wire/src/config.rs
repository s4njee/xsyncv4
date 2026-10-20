//! Configuration frames sent after HELLO (`run_client`) and read in the same order by `run_server`.

use crate::codec::{DecodeError, Decoder, Encoder};
use crate::consts::{feature, frame_type};
use crate::frame::Frame;

pub const MAX_FILES_DATA: usize = 65536;
pub const MAX_FILTER_RULES: u64 = 10_000;
pub const MAX_LINK_DEST: u64 = 20;
#[cfg(target_os = "macos")]
pub const NATIVE_ACL: u64 = feature::ACL_DARWIN;
#[cfg(not(target_os = "macos"))]
pub const NATIVE_ACL: u64 = feature::ACL_POSIX;
fn bad(why: &str) -> DecodeError {
    DecodeError::Invalid(why.into())
}
fn one(payload: &[u8]) -> Result<(), DecodeError> {
    if payload == [1] {
        Ok(())
    } else {
        Err(bad("malformed configuration"))
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Config {
    Io { bwlimit: u64, timeout: u64 },
    Compress { explicit_level: bool, skip_compress: Vec<u8> },
    Xattr(u8),
    Acl,
    Chown { user: Vec<u8>, group: Vec<u8> },
    Sparse,
    LinkDest { dirs: Vec<Vec<u8>> },
    Relative,
    Files { mode: u8, from0: bool, path: Vec<u8> },
    Filter { cvs: Option<bool>, rules: Vec<Vec<u8>> },
    Delete,
    Prune,
    Output { attrs: bool, unchanged: bool, mkpath: bool, delete_before: bool },
}

impl Config {
    fn meta(&self) -> (u8, u64) {
        match self {
            Self::Io { .. } => (frame_type::IO_CONFIG, feature::IO_CONTROL),
            Self::Compress { .. } => (frame_type::COMPRESS_CONFIG, feature::COMPRESS_POLICY),
            Self::Xattr(_) => (frame_type::XATTR_CONFIG, feature::XATTRS),
            Self::Acl => (frame_type::ACL_CONFIG, NATIVE_ACL),
            Self::Chown { .. } => (frame_type::CHOWN_CONFIG, feature::CHOWN),
            Self::Sparse => (frame_type::SPARSE_CONFIG, feature::SPARSE),
            Self::LinkDest { .. } => (frame_type::LINKDEST_CONFIG, feature::LINK_DEST),
            Self::Relative => (frame_type::RELATIVE_CONFIG, feature::RELATIVE),
            Self::Files { .. } => (frame_type::FILES_CONFIG, feature::FILES_FROM),
            Self::Filter { .. } => (frame_type::FILTER_CONFIG, feature::FILTERS),
            Self::Delete => (frame_type::DELETE_CONFIG, feature::DELETE_AFTER),
            Self::Prune => (frame_type::PRUNE_CONFIG, feature::PRUNE_EMPTY),
            Self::Output { .. } => (frame_type::OUTPUT_CONFIG, feature::DIR_OUTPUT),
        }
    }

    pub fn encode(&self) -> Frame {
        let mut e = Encoder::new();
        match self {
            Self::Io { bwlimit, timeout } => e.var(*bwlimit).var(*timeout),
            Self::Compress { explicit_level, skip_compress } => e.byte(*explicit_level as u8).str(skip_compress),
            Self::Xattr(mode) => e.byte(*mode),
            Self::Acl | Self::Sparse | Self::Relative | Self::Delete | Self::Prune => e.byte(1),
            Self::Chown { user, group } => e.str(user).str(group),
            Self::LinkDest { dirs } => {
                e.var(dirs.len() as u64);
                for dir in dirs {
                    e.str(dir);
                }
                &mut e
            }
            Self::Files { mode, from0, path } => e.byte(*mode).byte(*from0 as u8).str(path),
            Self::Filter { cvs, rules } => {
                if let Some(cvs) = cvs {
                    e.byte(*cvs as u8);
                }
                e.var(rules.len() as u64);
                for rule in rules {
                    e.str(rule);
                }
                &mut e
            }
            Self::Output { attrs, unchanged, mkpath, delete_before } => {
                e.byte(*attrs as u8).byte(*unchanged as u8).byte(*mkpath as u8).byte(*delete_before as u8)
            }
        };
        Frame::new(self.meta().0, e.into_bytes())
    }

    pub fn decode(kind: u8, payload: &[u8], features: u64) -> Result<Self, DecodeError> {
        let config = match kind {
            frame_type::IO_CONFIG => io(payload)?,
            frame_type::COMPRESS_CONFIG => compress(payload)?,
            frame_type::XATTR_CONFIG => match payload {
                [mode @ (1 | 2)] => Self::Xattr(*mode),
                _ => return Err(bad("malformed xattr configuration")),
            },
            frame_type::ACL_CONFIG => one(payload).map(|_| Self::Acl)?,
            frame_type::CHOWN_CONFIG => chown(payload)?,
            frame_type::SPARSE_CONFIG => one(payload).map(|_| Self::Sparse)?,
            frame_type::LINKDEST_CONFIG => link_dest(payload)?,
            frame_type::RELATIVE_CONFIG => one(payload).map(|_| Self::Relative)?,
            frame_type::FILES_CONFIG => files(payload)?,
            frame_type::FILTER_CONFIG => filter(payload, features)?,
            frame_type::DELETE_CONFIG => one(payload).map(|_| Self::Delete)?,
            frame_type::PRUNE_CONFIG => one(payload).map(|_| Self::Prune)?,
            frame_type::OUTPUT_CONFIG => output(payload)?,
            _ => return Err(bad("frame is not a configuration frame")),
        };
        if features & config.meta().1 == 0 {
            return Err(bad("unnegotiated configuration frame"));
        }
        Ok(config)
    }
}
fn io(payload: &[u8]) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let (bwlimit, timeout) = (d.var()?, d.var()?);
    if payload.len() > 20 || !d.is_empty() || bwlimit > i64::MAX as u64 || bwlimit % 1024 != 0 || timeout > i32::MAX as u64 {
        return Err(bad("malformed I/O configuration"));
    }
    Ok(Config::Io { bwlimit, timeout })
}
fn compress(payload: &[u8]) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let explicit_level = d.byte()?;
    let skip_compress = d.str()?.to_vec();
    if payload.len() > 65536 + 16
        || !d.is_empty()
        || explicit_level > 1
        || skip_compress.len() > 65536
        || skip_compress.contains(&0)
    {
        return Err(bad("malformed compression configuration"));
    }
    Ok(Config::Compress { explicit_level: explicit_level != 0, skip_compress })
}
fn chown(payload: &[u8]) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let (user, group) = (d.str()?.to_vec(), d.str()?.to_vec());
    if payload.len() > 1024 * 1024
        || !d.is_empty()
        || user.iter().any(|byte| matches!(byte, b':' | b',' | 0))
        || group.iter().any(|byte| matches!(byte, b',' | 0))
    {
        return Err(bad("malformed ownership configuration"));
    }
    Ok(Config::Chown { user, group })
}
fn link_dest(payload: &[u8]) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let count = d.var()?;
    if payload.len() > 1024 * 1024 || count > MAX_LINK_DEST {
        return Err(bad("malformed link-dest configuration"));
    }
    let mut dirs = Vec::new();
    for _ in 0..count {
        let dir = d.str()?;
        if dir.contains(&0) {
            return Err(bad("malformed link-dest directory"));
        }
        dirs.push(dir.to_vec());
    }
    if !d.is_empty() {
        return Err(bad("malformed link-dest configuration"));
    }
    Ok(Config::LinkDest { dirs })
}
fn files(payload: &[u8]) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let (mode, from0, path) = (d.byte()?, d.byte()?, d.str()?.to_vec());
    if payload.len() > 1024 * 1024 + 16
        || !d.is_empty()
        || !matches!(mode, 1 | 2)
        || from0 > 1
        || path.contains(&0)
        || (mode == 1 && !path.is_empty())
        || (mode == 2 && path == b"-")
    {
        return Err(bad("malformed files-from configuration"));
    }
    Ok(Config::Files { mode, from0: from0 != 0, path })
}
fn filter(payload: &[u8], features: u64) -> Result<Config, DecodeError> {
    let mut d = Decoder::new(payload);
    let cvs = if features & feature::CVS_FILTERS != 0 {
        match d.byte()? {
            value @ (0 | 1) => Some(value != 0),
            _ => return Err(bad("malformed CVS configuration")),
        }
    } else {
        None
    };
    let count = d.var()?;
    if payload.len() > 1024 * 1024 || count > MAX_FILTER_RULES {
        return Err(bad("malformed filter configuration"));
    }
    let mut rules = Vec::new();
    for _ in 0..count {
        let rule = d.str()?.to_vec();
        let ch = rule.first().copied().unwrap_or(b'-');
        if ch == b'.' || !matches!(ch, b'+' | b'-' | b'!' | b'H' | b'S' | b'P' | b'R' | b':') {
            return Err(bad("invalid filter rule"));
        }
        if ch == b':'
            && features & (feature::MERGE_FILTERS | feature::CVS_FILTERS) != feature::MERGE_FILTERS | feature::CVS_FILTERS
        {
            return Err(bad("unnegotiated per-directory filters"));
        }
        rules.push(rule);
    }
    if !d.is_empty() || (cvs == Some(true) && features & feature::MERGE_FILTERS == 0) {
        return Err(bad("malformed filter configuration"));
    }
    Ok(Config::Filter { cvs, rules })
}
fn output(payload: &[u8]) -> Result<Config, DecodeError> {
    let [attrs, unchanged, mkpath, delete_before] = payload else {
        return Err(bad("malformed output configuration"));
    };
    if [attrs, unchanged, mkpath, delete_before].iter().any(|&&value| value > 1) {
        return Err(bad("malformed output configuration"));
    }
    Ok(Config::Output {
        attrs: *attrs != 0,
        unchanged: *unchanged != 0,
        mkpath: *mkpath != 0,
        delete_before: *delete_before != 0,
    })
}

pub fn files_data(chunk: &[u8]) -> Result<Frame, DecodeError> {
    if chunk.is_empty() || chunk.len() > MAX_FILES_DATA {
        return Err(bad("malformed files-from data frame"));
    }
    Ok(Frame::new(frame_type::FILES_DATA, chunk.to_vec()))
}
pub fn files_end(bytes: u64) -> Frame {
    let mut e = Encoder::new();
    e.var(bytes);
    Frame::new(frame_type::FILES_END, e.into_bytes())
}
pub fn decode_files_end(payload: &[u8]) -> Result<u64, DecodeError> {
    let mut d = Decoder::new(payload);
    let bytes = d.var()?;
    if payload.len() > 10 || !d.is_empty() {
        return Err(bad("malformed files-from end frame"));
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    const FEATURES: u64 = u64::MAX;

    macro_rules! case {
        ($config:expr, $kind:literal, $payload:expr) => {{
            let expected = Frame::new($kind, $payload.to_vec()).to_bytes();
            assert_eq!($config.encode().to_bytes(), expected);
            assert_eq!(Config::decode($kind, &expected[5..], FEATURES).unwrap(), $config);
        }};
    }

    #[test]
    fn every_configuration_has_the_bytes_run_client_writes() {
        case!(Config::Io { bwlimit: 1 << 20, timeout: 60 }, 17, [0x80, 0x80, 0x40, 0x3c]);
        case!(
            Config::Compress { explicit_level: true, skip_compress: b"gz/zip".to_vec() },
            37,
            [1, 6, b'g', b'z', b'/', b'z', b'i', b'p']
        );
        case!(Config::Xattr(2), 26, [2]);
        case!(Config::Acl, 30, [1]);
        case!(
            Config::Chown { user: b"1000".to_vec(), group: b"staff".to_vec() },
            31,
            [4, b'1', b'0', b'0', b'0', 5, b's', b't', b'a', b'f', b'f']
        );
        case!(Config::Sparse, 32, [1]);
        case!(
            Config::LinkDest { dirs: vec![b"../a".to_vec(), b"../b".to_vec()] },
            33,
            [2, 4, b'.', b'.', b'/', b'a', 4, b'.', b'.', b'/', b'b']
        );
        case!(Config::Relative, 22, [1]);
        case!(Config::Files { mode: 1, from0: false, path: vec![] }, 23, [1, 0, 0]);
        case!(
            Config::Filter { cvs: Some(true), rules: vec![b"P keep".to_vec(), b"- *.tmp".to_vec()] },
            19,
            [1, 2, 6, b'P', b' ', b'k', b'e', b'e', b'p', 7, b'-', b' ', b'*', b'.', b't', b'm', b'p']
        );
        case!(Config::Delete, 20, [1]);
        case!(Config::Prune, 21, [1]);
        case!(Config::Output { attrs: true, unchanged: false, mkpath: true, delete_before: false }, 12, [1, 0, 1, 0]);
    }

    #[test]
    fn hostile_or_unnegotiated_configurations_are_refused() {
        assert!(Config::decode(17, &[0, 0], feature::CORE).is_err());
        assert!(Config::decode(37, &[0, 3, b'a', 0, b'b'], FEATURES).is_err());
        assert!(Config::decode(31, &[3, b'a', b':', b'b', 0], FEATURES).is_err());
        assert!(Config::decode(32, &[1], feature::CORE).is_err());
        assert!(Config::decode(33, &[1, 3, b'a', 0, b'b'], FEATURES).is_err());
        assert!(Config::decode(19, &[0, 1, 8, b'.', b' ', b'/', b'e', b't', b'c', b'/', b'p'], FEATURES).is_err());
        assert!(Config::decode(12, &[0, 0, 0, 2], FEATURES).is_err());
        assert!(Config::decode(2, &[], FEATURES).is_err());
    }

    #[test]
    fn the_files_from_stream_is_bounded_and_counted() {
        assert_eq!(files_data(b"ab").unwrap().to_bytes(), Frame::new(24, b"ab".to_vec()).to_bytes());
        assert!(files_data(b"").is_err());
        assert!(files_data(&vec![0; MAX_FILES_DATA + 1]).is_err());
        assert_eq!(files_end(2).to_bytes(), Frame::new(25, vec![2]).to_bytes());
        assert_eq!(decode_files_end(&[2]).unwrap(), 2);
        assert!(decode_files_end(&[0x80]).is_err());
        assert!(decode_files_end(&[0, 1]).is_err());
    }
}
