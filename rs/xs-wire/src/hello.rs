//! The HELLO exchange and `F_MSG`, laid out as `run_client` and `run_server` in remote.cpp write them.
//!
//! Client: magic, `var` version, role byte, `var` features (version 4 only), 32 option bytes, 7
//! `svar` options, `var` count and filter rules, `var` count and paths. Server: magic, `var`
//! version, `var` negotiated features (version 4 only).

use crate::codec::{DecodeError, Decoder, Encoder};
use crate::consts::{BOOL_OPTIONS, INT_OPTIONS, LEGACY_V3_FEATURES, MAGIC, PROTO_MIN_VERSION, PROTO_VERSION};

/// Which way the data goes, from the server's side: `R` when it receives (a push), `S` when it sends (a pull).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    Receive,
    Send,
}

impl Role {
    pub fn byte(self) -> u8 {
        match self {
            Role::Receive => b'R',
            Role::Send => b'S',
        }
    }

    pub fn from_byte(byte: u8) -> Result<Self, DecodeError> {
        match byte {
            b'R' => Ok(Role::Receive),
            b'S' => Ok(Role::Send),
            other => Err(DecodeError::Invalid(format!("unknown role byte {other:#04x}"))),
        }
    }
}

/// The options HELLO carries: `WIRE_V3_BOOL_OPTS` and `WIRE_V3_INT_OPTS`, in order.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Options {
    pub flags: [bool; 32],
    pub ints: [i64; 7],
}

impl Options {
    fn index(names: &[&str], name: &str) -> usize {
        names.iter().position(|n| *n == name).unwrap_or_else(|| panic!("no HELLO option named {name}"))
    }

    pub fn flag(&self, name: &str) -> bool {
        self.flags[Self::index(&BOOL_OPTIONS, name)]
    }

    pub fn set_flag(&mut self, name: &str, value: bool) -> &mut Self {
        self.flags[Self::index(&BOOL_OPTIONS, name)] = value;
        self
    }

    pub fn int(&self, name: &str) -> i64 {
        self.ints[Self::index(&INT_OPTIONS, name)]
    }

    pub fn set_int(&mut self, name: &str, value: i64) -> &mut Self {
        self.ints[Self::index(&INT_OPTIONS, name)] = value;
        self
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientHello {
    pub version: u64,
    pub role: Role,
    /// What the client advertises; a version 3 client implies `LEGACY_V3_FEATURES`.
    pub features: u64,
    pub options: Options,
    /// Legacy filter rules, in rsync's syntax.
    pub rules: Vec<String>,
    pub paths: Vec<String>,
}

impl ClientHello {
    pub fn encode(&self) -> Vec<u8> {
        let mut e = Encoder::new();
        e.raw(MAGIC).var(self.version).byte(self.role.byte());
        if self.version >= 4 {
            e.var(self.features);
        }
        for &flag in &self.options.flags {
            e.byte(flag as u8);
        }
        for &value in &self.options.ints {
            e.svar(value);
        }
        e.var(self.rules.len() as u64);
        for rule in &self.rules {
            e.str(rule);
        }
        e.var(self.paths.len() as u64);
        for path in &self.paths {
            e.str(path);
        }
        e.into_bytes()
    }

    /// Reads a client's HELLO. A version outside 3..=4 is returned as such: the server answers it
    /// with a fatal `F_MSG` that names both versions, which the client parses (see `version_mismatch`).
    pub fn decode(payload: &[u8]) -> Result<Self, DecodeError> {
        let mut d = Decoder::new(payload);
        if d.raw(MAGIC.len())? != MAGIC {
            return Err(DecodeError::Invalid("not an xs HELLO (bad magic)".into()));
        }
        let version = d.var()?;
        let role = Role::from_byte(d.byte()?)?;
        let features = if version >= 4 { d.var()? } else { LEGACY_V3_FEATURES };
        let mut options = Options::default();
        for flag in options.flags.iter_mut() {
            *flag = d.byte()? != 0;
        }
        for value in options.ints.iter_mut() {
            *value = d.svar()?;
        }
        let rules = (0..d.var()?).map(|_| d.text()).collect::<Result<_, _>>()?;
        let paths = (0..d.var()?).map(|_| d.text()).collect::<Result<_, _>>()?;
        Ok(Self { version, role, features, options, rules, paths })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ServerHello {
    pub version: u64,
    /// The negotiated features; a version 3 server implies `LEGACY_V3_FEATURES`.
    pub features: u64,
}

impl ServerHello {
    pub fn encode(&self) -> Vec<u8> {
        let mut e = Encoder::new();
        e.raw(MAGIC).var(self.version);
        if self.version >= 4 {
            e.var(self.features);
        }
        e.into_bytes()
    }

    pub fn decode(payload: &[u8]) -> Result<Self, DecodeError> {
        let mut d = Decoder::new(payload);
        if d.raw(MAGIC.len())? != MAGIC {
            return Err(DecodeError::Invalid("not an xs HELLO (bad magic)".into()));
        }
        let version = d.var()?;
        let features = if version >= 4 { d.var()? } else { LEGACY_V3_FEATURES };
        Ok(Self { version, features })
    }
}

/// Whether a server of this crate's version accepts a client of `version`.
pub fn version_supported(version: u64) -> bool {
    (PROTO_MIN_VERSION..=PROTO_VERSION).contains(&version)
}

/// The features both sides support: what the client advertised, masked by what the server has.
pub fn negotiate(advertised: u64, supported: u64) -> u64 {
    advertised & supported
}

/// The fatal message a server sends a client whose version it refuses (`run_server`), and the
/// server version a client reads back from it to decide whether to retry with version 3.
pub fn version_mismatch(client: u64, server: u64) -> String {
    format!("protocol version mismatch: client {client}, server {server}")
}

pub fn server_version_in(text: &str) -> Option<u64> {
    let tail = text.split("server ").nth(1)?;
    tail.split(|c: char| !c.is_ascii_digit()).next()?.parse().ok()
}

/// `F_MSG`: a kind byte (0 output, 1 error, 2 fatal), a `var` exit code, then the text to the end.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Message {
    pub kind: u8,
    pub code: u64,
    pub text: String,
}

impl Message {
    pub fn encode(&self) -> Vec<u8> {
        let mut e = Encoder::new();
        e.byte(self.kind).var(self.code).raw(self.text.as_bytes());
        e.into_bytes()
    }

    pub fn decode(payload: &[u8]) -> Result<Self, DecodeError> {
        let mut d = Decoder::new(payload);
        let kind = d.byte()?;
        let code = d.var()?;
        Ok(Self { kind, code, text: String::from_utf8_lossy(d.rest()).into_owned() })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::consts::feature;

    #[test]
    fn a_client_hello_has_the_layout_run_client_writes() {
        let mut options = Options::default();
        options.set_flag("recursive", true).set_flag("times", true).set_int("verbose", 1).set_int("jobs", -1);
        let hello = ClientHello {
            version: 4,
            role: Role::Send,
            features: feature::CORE | feature::ZSTD,
            options,
            rules: vec!["- *.tmp".into()],
            paths: vec!["src/".into()],
        };
        let bytes = hello.encode();
        let mut expected = b"XSYNC\x01".to_vec();
        expected.extend([4, b'S', 3]);
        let mut flags = [0u8; 32];
        flags[0] = 1; // recursive
        flags[5] = 1; // times
        expected.extend(flags);
        expected.extend([2, 0, 0, 0, 0, 1, 0]); // verbose 1 and jobs -1, zigzagged
        expected.extend([1, 7]);
        expected.extend(b"- *.tmp");
        expected.extend([1, 4]);
        expected.extend(b"src/");
        assert_eq!(bytes, expected);
        assert_eq!(ClientHello::decode(&bytes).unwrap(), hello);
    }

    #[test]
    fn a_version_3_hello_carries_no_feature_word() {
        let hello = ClientHello {
            version: 3,
            role: Role::Receive,
            features: LEGACY_V3_FEATURES,
            options: Options::default(),
            rules: vec![],
            paths: vec!["dst".into()],
        };
        let bytes = hello.encode();
        assert_eq!(&bytes[6..8], [3, b'R']);
        assert_eq!(bytes.len(), 6 + 2 + 32 + 7 + 1 + 1 + 1 + 3);
        assert_eq!(ClientHello::decode(&bytes).unwrap(), hello);
        let server = ServerHello { version: 3, features: LEGACY_V3_FEATURES };
        assert_eq!(server.encode(), b"XSYNC\x01\x03");
        assert_eq!(ServerHello::decode(&server.encode()).unwrap(), server);
    }

    #[test]
    fn a_fatal_message_names_both_versions() {
        let message = Message { kind: 2, code: 2, text: version_mismatch(9, 4) };
        assert_eq!(Message::decode(&message.encode()).unwrap(), message);
        assert_eq!(server_version_in(&message.text), Some(4));
        assert!(version_supported(3) && version_supported(4) && !version_supported(2) && !version_supported(5));
    }
}
