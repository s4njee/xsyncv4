//! Client-side itemized output: `render` and `output_event` from `src/output.cpp`.
//! Events are collected and sorted when stdout is not a terminal, as the C++ does,
//! and printed as they arrive on a terminal.

use std::io::{self, IsTerminal, Write};

use xs_wire::output::file_type;
use xs_wire::OutputEvent;

use crate::protocol::Options;

pub struct Output {
    itemize: bool,
    format: Vec<u8>,
    format_set: bool,
    pushing: bool,
    raw_names: bool,
    enabled: bool,
    ordered: bool,
    lines: Vec<(Vec<u8>, Vec<u8>)>,
}

impl Output {
    pub fn new(options: &Options, verbose: i64) -> Self {
        Self {
            itemize: options.itemize_level > 0,
            format: options.out_format.clone(),
            format_set: options.out_format_set,
            pushing: options.pushing,
            raw_names: options.raw_names,
            enabled: options.output_enabled(verbose) && !(options.out_format_set && options.out_format.is_empty()),
            ordered: !io::stdout().is_terminal(),
            lines: Vec::new(),
        }
    }

    pub fn push(&mut self, mut event: OutputEvent) {
        if !self.enabled {
            return;
        }
        if event.time == 0 {
            event.time = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_secs() as i64)
                .unwrap_or(0);
        }
        let text = self.render(&event);
        if self.ordered {
            self.lines.push((event.path, text));
        } else {
            let _ = io::stdout().write_all(&text);
        }
    }

    pub fn flush(&mut self) {
        self.lines.sort_by(|left, right| left.0.cmp(&right.0).then_with(|| left.1.cmp(&right.1)));
        let mut stdout = io::stdout().lock();
        for (_, text) in self.lines.drain(..) {
            if stdout.write_all(&text).is_err() {
                break;
            }
        }
        let _ = stdout.flush();
    }

    fn render(&self, event: &OutputEvent) -> Vec<u8> {
        let format: &[u8] = if self.format_set {
            self.format.as_slice()
        } else if self.itemize {
            b"%i %n%L"
        } else {
            b"%n%L"
        };
        let mut path = if event.path.is_empty() { b".".to_vec() } else { event.path.clone() };
        let source_dot = event.source.ends_with(b"/.");
        let mut source = if !self.pushing || event.source.is_empty() { path.clone() } else { event.source.clone() };
        source = normalize(&source);
        if source_dot && source != b"." {
            source.extend_from_slice(b"/.");
        }
        if event.kind == file_type::DIR {
            path.push(b'/');
        }
        let mut result = Vec::new();
        let mut index = 0;
        while index < format.len() {
            if format[index] != b'%' || index + 1 == format.len() {
                result.push(format[index]);
                index += 1;
                continue;
            }
            index += 1;
            let left = format[index] == b'-';
            if left {
                index += 1;
            }
            let mut width = 0usize;
            while index < format.len() && format[index].is_ascii_digit() {
                width = (width * 10 + usize::from(format[index] - b'0')).min(4096);
                index += 1;
            }
            if index == format.len() {
                break;
            }
            let escape = format[index];
            index += 1;
            let mut prefix = Vec::new();
            let value = match escape {
                b'%' => b"%".to_vec(),
                b'i' => event.code.clone(),
                b'n' => escape_name(&path, self.raw_names),
                b'f' => escape_name(&source, self.raw_names),
                b'L' => match (event.target.is_empty(), width) {
                    (false, _) => {
                        prefix = if event.hardlink_target { b" => ".to_vec() } else { b" -> ".to_vec() };
                        escape_name(&event.target, self.raw_names)
                    }
                    (true, width) if width > 0 => {
                        prefix = b"    ".to_vec();
                        Vec::new()
                    }
                    _ => Vec::new(),
                },
                b'l' => event.size.to_string().into_bytes(),
                b'b' => event.bytes.to_string().into_bytes(),
                b'o' => {
                    if event.code.starts_with(b"*deleting") {
                        b"del.".to_vec()
                    } else if self.pushing {
                        b"send".to_vec()
                    } else {
                        b"recv".to_vec()
                    }
                }
                b't' => crate::ffi::local_time(event.time).into_bytes(),
                _ => Vec::new(),
            };
            let mut padded = value;
            if padded.len() < width {
                if left {
                    padded.resize(width, b' ');
                } else {
                    let mut filler = vec![b' '; width - padded.len()];
                    filler.extend_from_slice(&padded);
                    padded = filler;
                }
            }
            result.extend_from_slice(&prefix);
            result.extend_from_slice(&padded);
        }
        if !self.format_set && !self.itemize && event.code.starts_with(b"*deleting") {
            result.splice(0..0, b"deleting ".iter().copied());
        }
        result.push(b'\n');
        result
    }
}

/// `std::filesystem::path::lexically_normal`, then the sender strips a leading slash.
fn normalize(name: &[u8]) -> Vec<u8> {
    let mut parts: Vec<&[u8]> = Vec::new();
    for part in name.split(|&byte| byte == b'/') {
        match part {
            b"" | b"." => {}
            b".." if !parts.is_empty() && parts.last() != Some(&&b".."[..]) => {
                parts.pop();
            }
            other => parts.push(other),
        }
    }
    let mut out = Vec::new();
    for part in parts {
        if !out.is_empty() {
            out.push(b'/');
        }
        out.extend_from_slice(part);
    }
    if out.is_empty() {
        out.push(b'.');
    }
    out
}

/// `escaped` in output.cpp: invalid bytes and control bytes become `\#ooo`.
fn escape_name(name: &[u8], raw_names: bool) -> Vec<u8> {
    let mut out = Vec::new();
    let mut i = 0;
    while i < name.len() {
        let c = name[i];
        let mut count = match c {
            0x00..=0x7f => 1,
            0xc2..=0xdf => 2,
            0xe0..=0xef => 3,
            0xf0..=0xf4 => 4,
            _ => 0,
        };
        let mut valid = count > 0 && i + count <= name.len();
        for k in 1..count {
            if !valid {
                break;
            }
            valid = i + k < name.len() && name[i + k] & 0xc0 == 0x80;
        }
        if valid && count >= 3 {
            let next = name[i + 1];
            valid = !(c == 0xe0 && next < 0xa0)
                && !(c == 0xed && next >= 0xa0)
                && !(c == 0xf0 && next < 0x90)
                && !(c == 0xf4 && next >= 0x90);
        }
        if raw_names && c >= 128 {
            valid = true;
            count = 1;
        }
        let octal_backslash = c == b'\\'
            && i + 4 < name.len()
            && name[i + 1] == b'#'
            && (b'0'..=b'7').contains(&name[i + 2])
            && (b'0'..=b'7').contains(&name[i + 3])
            && (b'0'..=b'7').contains(&name[i + 4]);
        if !valid || (c < 32 && c != b'\t') || c == 127 || octal_backslash {
            out.extend_from_slice(format!("\\#{c:03o}").as_bytes());
            i += 1;
        } else {
            out.extend_from_slice(&name[i..i + count]);
            i += count;
        }
    }
    out
}
