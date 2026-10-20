//! Payload integers and strings: `put_var`, `put_svar`, `put_str` and `RBuf` in remote.cpp.

use std::fmt;

/// Builds a payload.
#[derive(Debug, Default, Clone)]
pub struct Encoder {
    pub bytes: Vec<u8>,
}

impl Encoder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn byte(&mut self, value: u8) -> &mut Self {
        self.bytes.push(value);
        self
    }

    pub fn raw(&mut self, value: &[u8]) -> &mut Self {
        self.bytes.extend_from_slice(value);
        self
    }

    /// Unsigned LEB128, seven bits a byte, least significant first.
    pub fn var(&mut self, mut value: u64) -> &mut Self {
        while value >= 0x80 {
            self.bytes.push((value as u8) | 0x80);
            value >>= 7;
        }
        self.bytes.push(value as u8);
        self
    }

    /// Zigzag, then LEB128: 0, -1, 1, -2 ... become 0, 1, 2, 3 ...
    pub fn svar(&mut self, value: i64) -> &mut Self {
        self.var(((value as u64) << 1) ^ ((value >> 63) as u64))
    }

    /// A `var` length, then the bytes.
    pub fn str(&mut self, value: impl AsRef<[u8]>) -> &mut Self {
        let value = value.as_ref();
        self.var(value.len() as u64);
        self.raw(value)
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.bytes
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DecodeError {
    /// The payload ended inside a value.
    Truncated,
    /// A `var` longer than ten bytes, or whose tenth byte carries more than the 64th bit.
    Overlong,
    /// A value outside what the protocol allows, with what was wrong.
    Invalid(String),
}

impl fmt::Display for DecodeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DecodeError::Truncated => write!(f, "truncated payload"),
            DecodeError::Overlong => write!(f, "overlong integer"),
            DecodeError::Invalid(why) => write!(f, "{why}"),
        }
    }
}

impl std::error::Error for DecodeError {}

/// Reads a payload, refusing anything the C++ `RBuf` would mark bad.
#[derive(Debug, Clone)]
pub struct Decoder<'a> {
    rest: &'a [u8],
}

impl<'a> Decoder<'a> {
    pub fn new(payload: &'a [u8]) -> Self {
        Self { rest: payload }
    }

    pub fn is_empty(&self) -> bool {
        self.rest.is_empty()
    }

    pub fn byte(&mut self) -> Result<u8, DecodeError> {
        let (&first, rest) = self.rest.split_first().ok_or(DecodeError::Truncated)?;
        self.rest = rest;
        Ok(first)
    }

    pub fn raw(&mut self, len: usize) -> Result<&'a [u8], DecodeError> {
        if self.rest.len() < len {
            return Err(DecodeError::Truncated);
        }
        let (taken, rest) = self.rest.split_at(len);
        self.rest = rest;
        Ok(taken)
    }

    pub fn var(&mut self) -> Result<u64, DecodeError> {
        let mut value = 0u64;
        for shift in (0..64).step_by(7) {
            let byte = self.byte()?;
            if shift == 63 && byte & 0xfe != 0 {
                return Err(DecodeError::Overlong);
            }
            value |= u64::from(byte & 0x7f) << shift;
            if byte & 0x80 == 0 {
                return Ok(value);
            }
        }
        Err(DecodeError::Overlong)
    }

    pub fn svar(&mut self) -> Result<i64, DecodeError> {
        let value = self.var()?;
        Ok(((value >> 1) as i64) ^ -((value & 1) as i64))
    }

    pub fn str(&mut self) -> Result<&'a [u8], DecodeError> {
        let len = self.var()?;
        let len = usize::try_from(len).map_err(|_| DecodeError::Truncated)?;
        self.raw(len)
    }

    /// A string that must be UTF-8, such as a path the protocol carries as text.
    pub fn text(&mut self) -> Result<String, DecodeError> {
        String::from_utf8(self.str()?.to_vec()).map_err(|_| DecodeError::Invalid("string is not UTF-8".into()))
    }

    pub fn rest(&mut self) -> &'a [u8] {
        std::mem::take(&mut self.rest)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn var(value: u64) -> Vec<u8> {
        let mut e = Encoder::new();
        e.var(value);
        e.into_bytes()
    }

    #[test]
    fn var_matches_put_var() {
        assert_eq!(var(0), [0]);
        assert_eq!(var(127), [0x7f]);
        assert_eq!(var(128), [0x80, 0x01]);
        assert_eq!(var(300), [0xac, 0x02]);
        assert_eq!(var(u64::MAX), [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x01]);
    }

    #[test]
    fn svar_is_zigzag() {
        for (value, wire) in [(0i64, 0u64), (-1, 1), (1, 2), (-2, 3), (i64::MAX, u64::MAX - 1), (i64::MIN, u64::MAX)] {
            let mut e = Encoder::new();
            e.svar(value);
            assert_eq!(e.bytes, var(wire), "{value}");
            assert_eq!(Decoder::new(&e.bytes).svar().unwrap(), value);
        }
    }

    #[test]
    fn decoding_refuses_what_rbuf_refuses() {
        assert_eq!(Decoder::new(&[0x80]).var(), Err(DecodeError::Truncated));
        // A tenth byte above 1 would overflow 64 bits.
        assert_eq!(Decoder::new(&[0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x02]).var(), Err(DecodeError::Overlong));
        assert_eq!(Decoder::new(&[0x80; 11]).var(), Err(DecodeError::Overlong));
        assert_eq!(Decoder::new(&[3, b'a']).str(), Err(DecodeError::Truncated));
    }

    #[test]
    fn values_round_trip() {
        let mut e = Encoder::new();
        e.var(1 << 40).svar(-12345).str("path/to/file").byte(7);
        let mut d = Decoder::new(&e.bytes);
        assert_eq!(d.var().unwrap(), 1 << 40);
        assert_eq!(d.svar().unwrap(), -12345);
        assert_eq!(d.text().unwrap(), "path/to/file");
        assert_eq!(d.byte().unwrap(), 7);
        assert!(d.is_empty());
    }
}
