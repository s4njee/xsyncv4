//! The configuration frames that follow HELLO: reading and applying the
//! negotiated IO, compression, ownership and output settings.

use std::io::{self, Read};

use xs_wire::config::Config;
use xs_wire::io_control::IoControl;
use xs_wire::Frame;

use crate::protocol::{self, feature, frame_type, Options};

/// One configuration frame, with the header bound checked before its body is read: a
/// hostile peer cannot make us wait for a megabyte it never sends. Legal keep-alives are
/// swallowed here, exactly as `Conn::read_frame` does.
fn read_config_frame<R: Read>(reader: &mut R, allow_keepalive: bool) -> io::Result<Option<Frame>> {
    loop {
        let mut header = [0u8; xs_wire::HEADER_LEN];
        let mut filled = 0;
        while filled < header.len() {
            match reader.read(&mut header[filled..]) {
                Ok(0) if filled == 0 => return Ok(None),
                Ok(0) => return protocol::bad("connection closed inside a configuration frame"),
                Ok(n) => filled += n,
                Err(error) if error.kind() == io::ErrorKind::Interrupted => {}
                Err(error) => return Err(error),
            }
        }
        let len = u32::from_le_bytes([header[0], header[1], header[2], header[3]]);
        let kind = header[4];
        if len > xs_wire::MAX_PAYLOAD {
            return protocol::bad("protocol error: oversized frame");
        }
        if kind == frame_type::IO_CONFIG && len > 20 {
            return protocol::bad("protocol error: malformed I/O configuration (oversized)");
        }
        if kind == frame_type::KEEPALIVE && len != 0 {
            return protocol::bad("protocol error: invalid or unnegotiated keep-alive");
        }
        if kind == frame_type::COMPRESS_CONFIG && len > 65536 + 16 {
            return protocol::bad("protocol error: oversized or unnegotiated compression configuration");
        }
        if kind == frame_type::CHOWN_CONFIG && len > 1024 * 1024 {
            return protocol::bad("protocol error: oversized ownership configuration");
        }
        let mut payload = vec![0u8; len as usize];
        reader.read_exact(&mut payload).map_err(|error| match error.kind() {
            io::ErrorKind::UnexpectedEof => io::Error::new(io::ErrorKind::InvalidData, "connection closed inside a frame"),
            _ => error,
        })?;
        let frame = Frame::new(kind, payload);
        if frame.kind == frame_type::KEEPALIVE {
            if !allow_keepalive || !frame.payload.is_empty() {
                return protocol::bad("protocol error: invalid or unnegotiated keep-alive");
            }
            continue;
        }
        return Ok(Some(frame));
    }
}

type ConfigResult<T> = Result<T, (i32, String)>;

fn config_frame<R: Read>(reader: &mut R, allow_keepalive: bool) -> ConfigResult<Frame> {
    match read_config_frame(reader, allow_keepalive) {
        Ok(Some(frame)) => Ok(frame),
        Ok(None) => Err((12, "connection closed inside a configuration frame".into())),
        Err(error) => Err((2, error.to_string())),
    }
}

/// The client sends configuration frames in feature order: IO, compression, ownership.
/// This implementation negotiates only those three.
pub(crate) fn read_configuration<R: Read>(
    reader: &mut R,
    options: &mut Options,
    features: u64,
    role: u8,
    control: &IoControl,
) -> ConfigResult<()> {
    if features & feature::IO_CONTROL != 0 {
        let frame = config_frame(reader, false)?;
        if frame.kind != frame_type::IO_CONFIG {
            return Err((2, "protocol error: malformed I/O configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        let Config::Io { bwlimit, timeout } = config else {
            return Err((2, "protocol error: malformed I/O configuration".into()));
        };
        options.bwlimit = bwlimit;
        options.timeout = timeout as u32;
        control.configure(bwlimit, timeout as u32, true);
    }
    if features & feature::COMPRESS_POLICY != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::COMPRESS_CONFIG {
            return Err((2, "protocol error: malformed compression configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        match config {
            Config::Compress { explicit_level, skip_compress } => {
                if !options.compress {
                    return Err((2, "protocol error: malformed compression configuration".into()));
                }
                options.compress_level_explicit = explicit_level;
                options.skip_compress = skip_compress;
                options.skip_compress_set = true;
            }
            _ => return Err((2, "protocol error: malformed compression configuration".into())),
        }
    }
    if features & feature::CHOWN != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::CHOWN_CONFIG {
            return Err((2, "protocol error: malformed ownership configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        let Config::Chown { user, group } = config else {
            return Err((2, "protocol error: malformed ownership configuration".into()));
        };
        // A pushing client names its overrides; a pulling client's fields are empty.
        let wrong_side = if role == b'R' { user.is_empty() && group.is_empty() } else { !user.is_empty() || !group.is_empty() };
        if wrong_side {
            return Err((2, "protocol error: malformed ownership configuration".into()));
        }
        if (!user.is_empty() && options.ownership.user_set) || (!group.is_empty() && options.ownership.group_set) {
            return Err((1, "You can only specify a user/group-affecting --chown once".into()));
        }
        if !user.is_empty() {
            options.ownership.user = user;
            options.ownership.user_set = true;
        }
        if !group.is_empty() {
            options.ownership.group = group;
            options.ownership.group_set = true;
        }
    }
    if features & feature::DIR_OUTPUT != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::OUTPUT_CONFIG {
            return Err((2, "protocol error: malformed output configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        let Config::Output { attrs, unchanged, mkpath, delete_before } = config else {
            return Err((2, "protocol error: malformed output configuration".into()));
        };
        options.output_attrs = attrs;
        options.output_unchanged = unchanged;
        options.mkpath = mkpath;
        options.delete_before = delete_before;
    }
    Ok(())
}

