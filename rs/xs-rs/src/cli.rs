//! The command line the MVP needs: archive bits, `-z`, `-e`, `--rsync-path`,
//! `--server`, and the host:path split `parse_remote_spec` performs in C++.

use std::ffi::{OsStr, OsString};
use std::os::unix::ffi::{OsStrExt, OsStringExt};

use crate::protocol::Options;

#[derive(Clone, Debug, Default)]
pub struct Cli {
    pub server: bool,
    pub options: Options,
    pub rsh: Option<OsString>,
    pub rsync_path: Option<OsString>,
    pub paths: Vec<OsString>,
    pub verbose: i64,
}

impl Cli {
    fn archive(&mut self) {
        self.options.recursive = true;
        self.options.links = true;
        self.options.perms = true;
        self.options.times = true;
        self.options.group = true;
        self.options.owner = true;
        self.options.devices = true;
        self.options.specials = true;
    }

    fn set_long(&mut self, name: &str, value: bool) {
        let on = value;
        match name {
            "archive" => {
                if on {
                    self.archive();
                }
            }
            "recursive" | "recursion" => self.options.recursive = on,
            "dirs" => {}
            "links" => self.options.links = on,
            "copy-links" => self.options.copy_links = on,
            "perms" => self.options.perms = on,
            "times" => self.options.times = on,
            "group" => self.options.group = on,
            "owner" => self.options.owner = on,
            "devices" => self.options.devices = on,
            "specials" => self.options.specials = on,
            "compress" => self.options.compress = on,
            "numeric-ids" => self.options.numeric_ids = on,
            _ => {}
        }
    }
}

fn text(arg: &OsStr) -> String {
    arg.to_string_lossy().into_owned()
}

pub fn parse(args: Vec<OsString>) -> Result<Cli, String> {
    let mut cli = Cli::default();
    let mut iter = args.into_iter().peekable();
    let mut rest = false;
    let mut compression_none = false;
    while let Some(arg) = iter.next() {
        let s = text(&arg);
        if rest {
            cli.paths.push(arg);
            continue;
        }
        if s == "--" {
            rest = true;
            continue;
        }
        if s == "--server" {
            cli.server = true;
            continue;
        }
        if let Some(long) = s.strip_prefix("--") {
            let (name, inline) = match long.split_once('=') {
                Some((name, value)) => (name, Some(OsString::from(value))),
                None => (long, None),
            };
            if name == "rsh" || name == "rsync-path" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| format!("--{name} needs a value"))?,
                };
                if name == "rsh" {
                    cli.rsh = Some(value);
                } else {
                    cli.rsync_path = Some(value);
                }
                continue;
            }
            if name == "compress-level" || name == "zl" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| "--compress-level needs a value".to_string())?,
                };
                cli.options.compress_level =
                    text(&value).parse().map_err(|_| "--compress-level requires an integer".to_string())?;
                cli.options.compress_level_explicit = true;
                cli.options.compress = true;
                continue;
            }
            if name == "skip-compress" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| "--skip-compress needs a value".to_string())?,
                };
                let list = value.as_bytes().to_vec();
                if !xs_wire::Suffixes::default().assign(&list) {
                    return Err("invalid --skip-compress suffix list".into());
                }
                cli.options.skip_compress = list;
                cli.options.skip_compress_set = true;
                continue;
            }
            if name == "compress-choice" || name == "zc" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| "--compress-choice needs a value".to_string())?,
                };
                match text(&value).as_str() {
                    "zstd" => {
                        cli.options.compress = true;
                        compression_none = false;
                    }
                    "none" => compression_none = true,
                    _ => return Err("--compress-choice supports only zstd or none".into()),
                }
                continue;
            }
            if name == "verbose" {
                cli.verbose += 1;
                continue;
            }
            if let Some(negative) = name.strip_prefix("no-") {
                cli.set_long(negative, false);
            } else if inline.is_none()
                || matches!(name, "archive" | "recursive" | "links" | "perms" | "times" | "group" | "owner" | "compress")
            {
                cli.set_long(name, true);
            } else {
                // Unknown options with a value were already consumed by the '=' split;
                // tolerate them so older client invocations still reach the protocol.
            }
            continue;
        }
        if s.len() > 1 && s.starts_with('-') {
            let bytes = arg.as_bytes();
            let mut index = 1;
            while index < bytes.len() {
                let ch = bytes[index] as char;
                index += 1;
                match ch {
                    'a' => cli.archive(),
                    'r' => cli.options.recursive = true,
                    'l' => cli.options.links = true,
                    'p' => cli.options.perms = true,
                    't' => cli.options.times = true,
                    'g' => cli.options.group = true,
                    'o' => cli.options.owner = true,
                    'D' => {
                        cli.options.devices = true;
                        cli.options.specials = true;
                    }
                    'z' => cli.options.compress = true,
                    'n' => {}
                    'q' => cli.verbose = -1,
                    'v' => cli.verbose += 1,
                    'e' => {
                        let value = if index < bytes.len() {
                            let value = OsString::from_vec(bytes[index..].to_vec());
                            index = bytes.len();
                            value
                        } else {
                            iter.next().ok_or_else(|| "-e needs a command".to_string())?
                        };
                        cli.rsh = Some(value);
                    }
                    _ => {}
                }
            }
            continue;
        }
        cli.paths.push(arg);
    }
    if compression_none {
        cli.options.compress = false;
    }
    Ok(cli)
}

#[derive(Clone, Debug)]
pub struct RemoteSpec {
    pub remote: bool,
    pub host: Vec<u8>,
    pub path: Vec<u8>,
}

pub fn parse_remote(arg: &OsStr) -> RemoteSpec {
    let bytes = arg.as_bytes();
    if bytes.starts_with(b"rsync://") {
        return RemoteSpec { remote: true, host: Vec::new(), path: Vec::new() };
    }
    for (i, &ch) in bytes.iter().enumerate() {
        if ch == b'/' {
            break;
        }
        if ch == b':' {
            if i + 1 < bytes.len() && bytes[i + 1] == b':' {
                return RemoteSpec { remote: true, host: bytes[..i].to_vec(), path: bytes[i + 2..].to_vec() };
            }
            let mut path = bytes[i + 1..].to_vec();
            if path.is_empty() {
                path.push(b'.');
            }
            return RemoteSpec { remote: true, host: bytes[..i].to_vec(), path };
        }
    }
    RemoteSpec { remote: false, host: bytes.to_vec(), path: bytes.to_vec() }
}

pub fn split_words(command: &OsStr) -> Vec<OsString> {
    let bytes = command.as_bytes();
    let mut words = Vec::new();
    let mut word = Vec::new();
    let mut quote = 0u8;
    let mut present = false;
    let mut i = 0;
    while i < bytes.len() {
        let ch = bytes[i];
        i += 1;
        if ch == b'\\' && quote != b'\'' {
            if i == bytes.len() {
                break;
            }
            word.push(bytes[i]);
            present = true;
            i += 1;
        } else if quote != 0 {
            if ch == quote {
                quote = 0;
            } else {
                word.push(ch);
            }
        } else if ch == b'\'' || ch == b'"' {
            quote = ch;
            present = true;
        } else if matches!(ch, b' ' | b'\t' | b'\n') {
            if present {
                words.push(OsString::from_vec(std::mem::take(&mut word)));
                present = false;
            }
        } else {
            word.push(ch);
            present = true;
        }
    }
    if present {
        words.push(OsString::from_vec(word));
    }
    words
}

pub fn expand_home(path: &[u8]) -> Vec<u8> {
    if !path.starts_with(b"~") {
        return path.to_vec();
    }
    let slash = path.iter().position(|&b| b == b'/');
    let user = &path[1..slash.unwrap_or(path.len())];
    let home = if user.is_empty() {
        std::env::var_os("HOME").map(|v| v.into_vec()).unwrap_or_default()
    } else {
        // A user name lookup outside the MVP; leave it unchanged rather than guessing.
        return path.to_vec();
    };
    if home.is_empty() {
        return path.to_vec();
    }
    let mut out = home;
    if let Some(slash) = slash {
        out.extend_from_slice(&path[slash..]);
    }
    out
}
