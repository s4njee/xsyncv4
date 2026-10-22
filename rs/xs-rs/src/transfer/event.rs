//! The receiver's output events and progress acknowledgments: the itemized codes and
//! messages `output.cpp` renders, and the snapshot `progress.cpp` sends every 100 ms.

use std::io::{self, Write};
use std::time::{Duration, Instant};

use xs_wire::output::file_type;
use xs_wire::{OutputEvent, ProgressAck};

use crate::output::Output;
use crate::protocol::{self, feature, frame_type, Attrs, EntryMeta, Options, T_BLK, T_CHR, T_DIR, T_LNK, T_REG};

use super::file;
use super::outbox::FrameOut;

pub(super) fn report_event<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    local: Option<&mut Output>,
    features: u64,
    opts: &Options,
    event: OutputEvent,
) -> io::Result<()> {
    if opts.am_server {
        if features & feature::OUTPUT != 0 {
            output.send(frame_type::OUTPUT, &event.encode(features).payload)?;
        }
    } else if let Some(local) = local {
        local.push(event);
    }
    Ok(())
}

/// `Receiver::acknowledge`: at most one snapshot per 100 ms or per MiB, plus the final one.
pub(super) fn progress_ack<W: Write + Send + 'static>(
    output: &mut FrameOut<W>,
    features: u64,
    bytes: u64,
    files: u64,
    force: bool,
    last: &mut (u64, u64, Instant),
) -> io::Result<()> {
    if features & feature::PROGRESS_ACK == 0 {
        return Ok(());
    }
    let changed = bytes != last.0 || files != last.1;
    let now = Instant::now();
    if !force
        && (!changed || (now.duration_since(last.2) < Duration::from_millis(100) && bytes >= last.0 && bytes - last.0 < protocol::BLOCK_TARGET as u64))
    {
        return Ok(());
    }
    let frame = ProgressAck { bytes, files, ..ProgressAck::default() }.encode(features);
    output.send(frame.kind, &frame.payload)?;
    *last = (bytes, files, now);
    Ok(())
}

pub(super) fn taken_event(code: &[u8], path: &[u8], source: &[u8], kind: u8, size: i64, bytes: i64) -> OutputEvent {
    OutputEvent {
        code: code.to_vec(),
        path: path.to_vec(),
        source: source.to_vec(),
        target: Vec::new(),
        kind,
        size,
        bytes,
        time: 0,
        hardlink_target: false,
    }
}

/// The event for a directory, if the output asks for one.
pub(super) fn directory_event(
    opts: &Options,
    path: &[u8],
    source: &[u8],
    attrs: &Attrs,
    before: Option<&file::Stat>,
    created: bool,
) -> Option<OutputEvent> {
    let mut code = *b".d.........";
    let mut changed = created;
    if created {
        code = *b"cd+++++++++";
    } else if let Some(before) = before {
        if opts.times && before.mtime() != attrs.mtime {
            code[4] = b't';
            changed = true;
        }
        if opts.perms && before.mode() & 0o7777 != attrs.mode & 0o7777 {
            code[5] = b'p';
            changed = true;
        }
        if opts.owner && before.uid() != attrs.uid {
            code[6] = b'o';
            changed = true;
        }
        if opts.group && before.gid() != attrs.gid {
            code[7] = b'g';
            changed = true;
        }
    }
    if !changed && !opts.output_unchanged {
        return None;
    }
    if !changed {
        code[2..].fill(b' ');
    } else if !created && !opts.output_attrs {
        return None;
    }
    Some(taken_event(&code, path, source, file_type::DIR, attrs.size, 0))
}

pub(super) fn transferred_code(opts: &Options, before: Option<&file::Stat>, entry: &EntryMeta) -> Vec<u8> {
    let mut code = if opts.pushing { *b"<f+++++++++" } else { *b">f+++++++++" };
    if let Some(before) = before.filter(|before| before.is_file()) {
        code[2..].fill(b'.');
        if before.len() as i64 != entry.size {
            code[3] = b's';
        }
        if !opts.times {
            code[4] = b'T';
        } else if before.mtime() != entry.attrs.mtime {
            code[4] = b't';
        }
        if opts.perms && before.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
            code[5] = b'p';
        }
        if opts.owner && before.uid() != entry.attrs.uid {
            code[6] = b'o';
        }
        if opts.group && before.gid() != entry.attrs.gid {
            code[7] = b'g';
        }
    }
    code.to_vec()
}

pub(super) fn metadata_code(opts: &Options, kind: u8, before: &file::Stat, entry: &EntryMeta) -> Option<Vec<u8>> {
    let letter = match kind {
        T_REG => b'f',
        T_LNK => b'L',
        T_DIR => b'd',
        T_CHR | T_BLK => b'D',
        _ => b'S',
    };
    let mut code = *b".f.........";
    code[1] = letter;
    let mut changed = false;
    if opts.times && before.mtime() != entry.attrs.mtime {
        code[4] = b't';
        changed = true;
    }
    if opts.perms && before.mode() & 0o7777 != entry.attrs.mode & 0o7777 {
        code[5] = b'p';
        changed = true;
    }
    if opts.owner && before.uid() != entry.attrs.uid {
        code[6] = b'o';
        changed = true;
    }
    if opts.group && before.gid() != entry.attrs.gid {
        code[7] = b'g';
        changed = true;
    }
    if changed && opts.output_attrs {
        Some(code.to_vec())
    } else if !changed && opts.output_unchanged {
        code[2..].fill(b' ');
        Some(code.to_vec())
    } else {
        None
    }
}
