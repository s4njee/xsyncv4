//! The xs wire protocol, as the C++ xs speaks it (`src/remote.cpp`, `src/common.h`).
//!
//! A connection is one byte stream each way (the stdin and stdout of `xs --server`, spawned through
//! ssh). Every frame is a 5-byte header, the payload length as a little-endian `u32` and a type byte,
//! then the payload. Integers inside payloads are unsigned LEB128 (`var`) or zigzag LEB128 (`svar`);
//! strings are a `var` length and the bytes.

pub mod codec;
pub mod compress;
pub mod config;
pub mod consts;
pub mod frame;
pub mod hello;
pub mod idmap;
pub mod io_control;
pub mod output;
pub mod resume;

pub use compress::{Suffixes, DEFAULT_SKIP_COMPRESS};

pub use codec::{DecodeError, Decoder, Encoder};
pub use consts::*;
pub use frame::{read_frame, write_frame, Frame, FrameError};
pub use hello::{ClientHello, Message, Options, Role, ServerHello};
pub use output::{OutputEvent, ProgressAck};
