//! Frames: a 5-byte header (payload length as a little-endian `u32`, then the type) and the payload.

use std::fmt;
use std::io::{self, Read, Write};

use crate::consts::{HEADER_LEN, MAX_PAYLOAD};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Frame {
    pub kind: u8,
    pub payload: Vec<u8>,
}

impl Frame {
    pub fn new(kind: u8, payload: Vec<u8>) -> Self {
        Self { kind, payload }
    }

    /// The frame as it goes on the wire.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(HEADER_LEN + self.payload.len());
        bytes.extend_from_slice(&(self.payload.len() as u32).to_le_bytes());
        bytes.push(self.kind);
        bytes.extend_from_slice(&self.payload);
        bytes
    }
}

#[derive(Debug)]
pub enum FrameError {
    Io(io::Error),
    /// The stream ended inside a frame.
    Truncated,
    /// A payload over 1 GiB, which the C++ peer refuses as a protocol error.
    Oversized(u32),
}

impl fmt::Display for FrameError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FrameError::Io(error) => write!(f, "{error}"),
            FrameError::Truncated => write!(f, "connection closed inside a frame"),
            FrameError::Oversized(len) => write!(f, "protocol error: oversized frame ({len} bytes)"),
        }
    }
}

impl std::error::Error for FrameError {}

impl From<io::Error> for FrameError {
    fn from(error: io::Error) -> Self {
        FrameError::Io(error)
    }
}

pub fn write_frame(out: &mut impl Write, kind: u8, payload: &[u8]) -> io::Result<()> {
    let len = u32::try_from(payload.len())
        .ok()
        .filter(|&len| len <= MAX_PAYLOAD)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "payload over 1 GiB"))?;
    let mut header = [0u8; HEADER_LEN];
    header[..4].copy_from_slice(&len.to_le_bytes());
    header[4] = kind;
    out.write_all(&header)?;
    out.write_all(payload)
}

/// The next frame, or `None` when the stream ends cleanly between frames.
pub fn read_frame(input: &mut impl Read) -> Result<Option<Frame>, FrameError> {
    let mut header = [0u8; HEADER_LEN];
    let mut filled = 0;
    while filled < HEADER_LEN {
        match input.read(&mut header[filled..]) {
            Ok(0) if filled == 0 => return Ok(None),
            Ok(0) => return Err(FrameError::Truncated),
            Ok(n) => filled += n,
            Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
            Err(error) => return Err(error.into()),
        }
    }
    let len = u32::from_le_bytes([header[0], header[1], header[2], header[3]]);
    if len > MAX_PAYLOAD {
        return Err(FrameError::Oversized(len));
    }
    let mut payload = vec![0u8; len as usize];
    input.read_exact(&mut payload).map_err(|error| match error.kind() {
        io::ErrorKind::UnexpectedEof => FrameError::Truncated,
        _ => FrameError::Io(error),
    })?;
    Ok(Some(Frame { kind: header[4], payload }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_is_little_endian_length_then_type() {
        let frame = Frame::new(8, b"hi".to_vec());
        assert_eq!(frame.to_bytes(), [2, 0, 0, 0, 8, b'h', b'i']);
        let mut out = Vec::new();
        write_frame(&mut out, 8, b"hi").unwrap();
        assert_eq!(out, frame.to_bytes());
    }

    #[test]
    fn frames_round_trip_and_end_cleanly() {
        let mut stream = Vec::new();
        write_frame(&mut stream, 1, b"one").unwrap();
        write_frame(&mut stream, 18, b"").unwrap();
        let mut input = stream.as_slice();
        assert_eq!(read_frame(&mut input).unwrap(), Some(Frame::new(1, b"one".to_vec())));
        assert_eq!(read_frame(&mut input).unwrap(), Some(Frame::new(18, Vec::new())));
        assert!(read_frame(&mut input).unwrap().is_none());
    }

    #[test]
    fn a_frame_cut_short_or_over_a_gibibyte_is_refused() {
        assert!(matches!(read_frame(&mut [5u8, 0, 0, 0, 1, b'a'].as_slice()), Err(FrameError::Truncated)));
        assert!(matches!(read_frame(&mut [1u8, 0].as_slice()), Err(FrameError::Truncated)));
        let oversized = ((1u32 << 30) + 1).to_le_bytes();
        let header = [oversized[0], oversized[1], oversized[2], oversized[3], 4];
        assert!(matches!(read_frame(&mut header.as_slice()), Err(FrameError::Oversized(_))));
    }
}
