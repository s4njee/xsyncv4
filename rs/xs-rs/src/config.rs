//! The configuration frames that follow HELLO: reading and applying the
//! negotiated IO, compression, ownership and output settings.

use std::ffi::OsString;
use std::io::{self, Read, Write};
use std::os::unix::ffi::OsStringExt;
use std::path::PathBuf;

use xs_wire::config::{decode_files_end, files_data, files_end, Config};
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
pub(crate) fn read_configuration<R: Read, W: Write>(
    reader: &mut R,
    writer: &mut W,
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
    if features & feature::RELATIVE != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::RELATIVE_CONFIG {
            return Err((2, "protocol error: malformed relative configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        if config != Config::Relative {
            return Err((2, "protocol error: malformed relative configuration".into()));
        }
        options.relative = true;
    }
    if features & feature::FILES_FROM != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::FILES_CONFIG {
            return Err((2, "protocol error: malformed files-from configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        let Config::Files { mode, from0, path } = config else {
            return Err((2, "protocol error: malformed files-from configuration".into()));
        };
        options.files_from_set = true;
        if role == b'S' {
            options.dir_requested = true;
        }
        if mode == 1 && role == b'S' {
            options.from0 = true;
        }
        if mode == 2 {
            options.from0 |= from0;
        }
        let record_from0 = if mode == 2 { options.from0 } else { from0 };
        let ack = Frame::new(frame_type::FILES_CONFIG, vec![u8::from(record_from0)]);
        xs_wire::write_frame(writer, ack.kind, &ack.payload)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        writer.flush().map_err(|error| (2, format!("protocol error: {error}")))?;
        if mode == 1 {
            options.file_names = receive_files(reader, record_from0, role == b'S')?;
        } else {
            let path = if path.is_empty() { if role == b'S' { b".".to_vec() } else { Vec::new() } } else { path };
            send_files(
                writer,
                &PathBuf::from(OsString::from_vec(path)),
                record_from0,
                if role == b'S' { Some(&mut options.file_names) } else { None },
            )?;
        }
    }
    if features & feature::FILTERS != 0 {
        let frame = config_frame(reader, control.keepalive_enabled())?;
        if frame.kind != frame_type::FILTER_CONFIG {
            return Err((2, "protocol error: malformed filter configuration".into()));
        }
        let config = Config::decode(frame.kind, &frame.payload, features)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        let Config::Filter { cvs, rules } = config else {
            return Err((2, "protocol error: malformed filter configuration".into()));
        };
        if !options.filters.empty() {
            return Err((2, "protocol error: malformed filter configuration".into()));
        }
        for rule in &rules {
            options
                .filters
                .add_filter(rule)
                .map_err(|error| (2, format!("protocol error: bad configured filter: {error}")))?;
        }
        if cvs == Some(true) && role == b'S' {
            let _ = options.filters.add_filter(b"-C");
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

pub(crate) fn parse_names(content: &[u8], from0: bool, names: &mut Vec<Vec<u8>>, record: &mut Vec<u8>) {
    feed_names(content, from0, names, record, true);
}

fn feed_names(chunk: &[u8], from0: bool, names: &mut Vec<Vec<u8>>, record: &mut Vec<u8>, final_chunk: bool) {
    fn flush(record: &mut Vec<u8>, names: &mut Vec<Vec<u8>>) {
        let line = &record[..record.iter().position(|&b| b == 0).unwrap_or(record.len())];
        if !line.is_empty() && !matches!(line[0], b'#' | b';') {
            names.push(line.to_vec());
        }
        record.clear();
    }
    for &byte in chunk {
        if (from0 && byte == 0) || (!from0 && (byte == b'\r' || byte == b'\n')) {
            flush(record, names);
        } else if !from0 && byte == 0 {
        } else if record.len() < 1024 * 1024 {
            record.push(byte);
        }
    }
    if final_chunk {
        flush(record, names);
    }
}

fn receive_files<R: Read>(reader: &mut R, from0: bool, names: bool) -> ConfigResult<Vec<Vec<u8>>> {
    let mut out = Vec::new();
    let mut record = Vec::new();
    let mut bytes = 0u64;
    loop {
        let frame = config_frame(reader, true)?;
        match frame.kind {
            frame_type::FILES_DATA => {
                if frame.payload.is_empty() || frame.payload.len() > 65536 {
                    return Err((2, "protocol error: malformed files-from data frame".into()));
                }
                bytes += frame.payload.len() as u64;
                if names {
                    feed_names(&frame.payload, from0, &mut out, &mut record, false);
                }
            }
            frame_type::FILES_END => {
                let expected = decode_files_end(&frame.payload).map_err(|error| (2, format!("protocol error: {error}")))?;
                if expected != bytes {
                    return Err((2, "protocol error: incomplete files-from stream".into()));
                }
                if names {
                    feed_names(&[], from0, &mut out, &mut record, true);
                }
                return Ok(out);
            }
            frame_type::MSG => {}
            _ => return Err((2, "protocol error: unexpected files-from frame".into())),
        }
    }
}

fn send_files<W: Write>(
    writer: &mut W,
    path: &PathBuf,
    from0: bool,
    names: Option<&mut Vec<Vec<u8>>>,
) -> ConfigResult<()> {
    let content = if path.as_os_str().is_empty() {
        Vec::new()
    } else {
        std::fs::read(path).map_err(|error| (12, format!("failed to open files-from file {}: {error}", path.display())))?
    };
    if let Some(names) = names {
        let mut record = Vec::new();
        feed_names(&content, from0, names, &mut record, true);
    }
    let mut written = 0;
    while written < content.len() {
        let end = (written + 65536).min(content.len());
        let frame = files_data(&content[written..end]).map_err(|error| (2, format!("protocol error: {error}")))?;
        xs_wire::write_frame(writer, frame.kind, &frame.payload)
            .map_err(|error| (2, format!("protocol error: {error}")))?;
        written = end;
    }
    let end = files_end(content.len() as u64);
    xs_wire::write_frame(writer, end.kind, &end.payload)
        .map_err(|error| (2, format!("protocol error: {error}")))?;
    writer.flush().map_err(|error| (2, format!("protocol error: {error}")))?;
    Ok(())
}
