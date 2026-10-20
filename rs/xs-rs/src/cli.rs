//! The command line the MVP needs: archive bits, `-z`, `-j`, `-e`, `--rsync-path`,
//! `--server`, and the host:path split `parse_remote_spec` performs in C++.
//!
//! As `main.cpp`'s parser does, an option this program does not know is a usage
//! error; it is never silently ignored (the C++ has an explicit unsupported list
//! and an `unknown option` fallthrough). `-j/--jobs` is the worker budget: an
//! explicit value above one also permits splitting one large file into ranges.

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
    pub help: bool,
    pub version: bool,
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
            "hard-links" => self.options.hard_links = on,
            "progress" => self.options.progress = on,
            "8-bit-output" => self.options.raw_names = on,
            "local-peer" => self.options.local_peer = on,
            // Accepted no-ops that C++ also accepts: their behaviour is intrinsic
            // to this engine, so there is nothing to switch off.
            "whole-file" | "protect-args" | "secluded-args" | "blocking-io" | "open-noatime" | "motd"
            | "clone" | "atomic" | "fallback" | "from0" | "stats" | "human-readable" => {}
            _ => {}
        }
    }

    fn set_jobs(&mut self, value: &OsStr) -> Result<(), String> {
        let text = text(value);
        self.options.jobs = text.parse().map_err(|_| "--jobs requires an integer".to_string())?;
        Ok(())
    }
}

/// Options `main.cpp` names explicitly as unsupported. They are refused rather
/// than ignored, before a destination is touched.
const UNSUPPORTED: &[&str] = &[
    "backup",
    "backup-dir",
    "suffix",
    "compare-dest",
    "copy-dest",
    "usermap",
    "groupmap",
    "append",
    "append-verify",
    "partial-dir",
    "delay-updates",
    "fuzzy",
    "remove-source-files",
    "keep-dirlinks",
    "copy-dirlinks",
    "copy-unsafe-links",
    "munge-links",
    "daemon",
    "port",
    "password-file",
    "write-batch",
    "read-batch",
    "only-write-batch",
    "super",
    "fake-super",
    "temp-dir",
    "iconv",
    "checksum-seed",
    "address",
    "sockopts",
    "stop-after",
    "stop-at",
    "max-alloc",
    "write-devices",
    "copy-devices",
    "delete-missing-args",
    "ignore-missing-args",
    "trust-sender",
    "copy-as",
    "early-input",
    "remote-option",
    "contimeout",
    "fsync",
    "preallocate",
    "block-size",
    "checksum-choice",
    "cc",
    "log-file-format",
    "debug",
    "outbuf",
    "inc-recursive",
    "i-r",
    "no-protect-args",
    "ipv4",
    "ipv6",
    "msgs2stderr",
    "new-compress",
    "old-compress",
    "implied-dirs",
    "old-args",
];

fn unsupported(name: &str) -> bool {
    let bare = name.strip_prefix("no-").unwrap_or(name);
    UNSUPPORTED.contains(&name) || UNSUPPORTED.contains(&bare)
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
        if s == "--help" {
            cli.help = true;
            continue;
        }
        if s == "--version" {
            cli.version = true;
            continue;
        }
        if let Some(long) = s.strip_prefix("--") {
            let (name, inline) = match long.split_once('=') {
                Some((name, value)) => (name, Some(OsString::from(value))),
                None => (long, None),
            };
            if unsupported(name) {
                return Err(format!("--{} is not supported by xs", name.strip_prefix("no-").unwrap_or(name)));
            }
            if name == "jobs" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| "--jobs needs a value".to_string())?,
                };
                cli.set_jobs(&value)?;
                continue;
            }
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
            if name == "chown" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| "--chown needs a value".to_string())?,
                };
                let supported = {
                    let text = value.as_bytes();
                    let colon = text.iter().position(|&byte| byte == b':');
                    let user = &text[..colon.unwrap_or(text.len())];
                    let group = colon.map(|at| &text[at + 1..]).unwrap_or(&[]);
                    let ownership = &mut cli.options.ownership;
                    if text.contains(&b',')
                        || text.contains(&0)
                        || (!user.is_empty() && ownership.user_set)
                        || (!group.is_empty() && ownership.group_set)
                    {
                        false
                    } else {
                        if !user.is_empty() {
                            ownership.user = user.to_vec();
                            ownership.user_set = true;
                            cli.options.owner = true;
                        }
                        if !group.is_empty() {
                            ownership.group = group.to_vec();
                            ownership.group_set = true;
                            cli.options.group = true;
                        }
                        true
                    }
                };
                if !supported {
                    return Err(format!("Invalid or repeated --chown ({})", text(&value)));
                }
                continue;
            }
            if name == "bwlimit" || name == "timeout" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| format!("--{name} needs a value"))?,
                };
                let value = text(&value);
                if name == "bwlimit" {
                    cli.options.bwlimit = xs_wire::io_control::parse_rate(&value)?;
                } else {
                    cli.options.timeout = xs_wire::io_control::parse_timeout(&value)?;
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
            if name == "out-format" || name == "log-format" {
                let value = match inline {
                    Some(value) => value,
                    None => iter.next().ok_or_else(|| format!("--{name} needs a value"))?,
                };
                cli.options.out_format = value.as_bytes().to_vec();
                cli.options.out_format_set = true;
                continue;
            }
            if name == "progress" {
                if let Some(value) = &inline {
                    if value.as_bytes() != b"json" {
                        return Err("--progress accepts only =json".into());
                    }
                }
                cli.options.progress = true;
                continue;
            }
            // Options xs itself supports but this port does not implement yet are
            // refused rather than silently doing something else.
            if matches!(
                name,
                "install"
                    | "max-delete"
                    | "max-size"
                    | "min-size"
                    | "modify-window"
                    | "exclude"
                    | "include"
                    | "exclude-from"
                    | "include-from"
                    | "filter"
                    | "info"
                    | "files-from"
                    | "link-dest"
                    | "chmod"
                    | "log-file"
                    | "list-only"
            ) {
                return Err(format!("--{name} is not supported by xs-rs"));
            }
            let (base, on) = match name.strip_prefix("no-") {
                Some(base) => (base, false),
                None => (name, true),
            };
            match base {
                "verbose" => {
                    if on {
                        cli.verbose += 1;
                    } else {
                        cli.verbose = 0;
                    }
                }
                "quiet" => cli.verbose = -1,
                "itemize-changes" => {
                    if on {
                        cli.options.itemize_level += 1;
                    } else {
                        cli.options.itemize_level = 0;
                    }
                }
                "progress" => cli.options.progress = on,
                "D" => {
                    cli.options.devices = on;
                    cli.options.specials = on;
                }
                "R" | "relative" => {}
                // `set_long` owns every other boolean and documented no-op.
                "archive"
                | "recursive"
                | "recursion"
                | "dirs"
                | "links"
                | "copy-links"
                | "perms"
                | "times"
                | "group"
                | "owner"
                | "devices"
                | "specials"
                | "compress"
                | "numeric-ids"
                | "hard-links"
                | "8-bit-output"
                | "local-peer"
                | "whole-file"
                | "protect-args"
                | "secluded-args"
                | "blocking-io"
                | "open-noatime"
                | "motd"
                | "clone"
                | "atomic"
                | "fallback"
                | "from0"
                | "stats"
                | "human-readable" => cli.set_long(base, on),
                _ => return Err(format!("--{name}: unknown option")),
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
                    'd' => {}
                    'L' => cli.options.copy_links = true,
                    'u' | 'c' | 'I' | 'x' | 'O' | 'J' | 'W' | 's' | 'S' | 'C' | 'F' | 'm' | '0' => {}
                    'A' => {
                        cli.options.perms = true;
                    }
                    'X' => {}
                    'z' => cli.options.compress = true,
                    'H' => cli.options.hard_links = true,
                    'n' => {}
                    'i' => cli.options.itemize_level += 1,
                    '8' => cli.options.raw_names = true,
                    'P' => cli.options.progress = true,
                    'h' => {}
                    'q' => cli.verbose = -1,
                    'v' => cli.verbose += 1,
                    'j' => {
                        let value = if index < bytes.len() {
                            let value = OsString::from_vec(bytes[index..].to_vec());
                            index = bytes.len();
                            value
                        } else {
                            iter.next().ok_or_else(|| "-j needs a value".to_string())?
                        };
                        cli.set_jobs(&value)?;
                    }
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
                    '4' => return Err("--ipv4 is not supported by xs".into()),
                    '6' => return Err("--ipv6 is not supported by xs".into()),
                    'B' => return Err("--block-size is not supported by xs".into()),
                    'T' => return Err("--temp-dir is not supported by xs".into()),
                    'M' => return Err("--remote-option is not supported by xs".into()),
                    'b' => return Err("--backup is not supported by xs".into()),
                    'y' => return Err("--fuzzy is not supported by xs".into()),
                    _ => return Err(format!("-{ch}: unknown option")),
                }
            }
            continue;
        }
        cli.paths.push(arg);
    }
    if compression_none {
        cli.options.compress = false;
    }
    cli.options.configure_output();
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

#[cfg(test)]
mod tests {
    use super::*;

    fn args(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn jobs_is_a_wire_integer_in_every_spelling() {
        for value in ["-j4", "-aj4"] {
            assert_eq!(parse(args(&[value, "src", "dst"])).unwrap().options.jobs, 4);
        }
        assert_eq!(parse(args(&["-j", "7", "src", "dst"])).unwrap().options.jobs, 7);
        assert_eq!(parse(args(&["--jobs=2", "src", "dst"])).unwrap().options.jobs, 2);
        assert_eq!(parse(args(&["--jobs", "3", "src", "dst"])).unwrap().options.jobs, 3);
        assert_eq!(parse(args(&["-a", "src", "dst"])).unwrap().options.jobs, 0);
    }

    #[test]
    fn an_unknown_or_unsupported_option_is_refused() {
        for option in ["--bogus", "--bogus=1", "-Z"] {
            assert!(parse(args(&[option, "src", "dst"])).is_err(), "{option}");
        }
        for option in ["--backup", "--block-size=4096", "--old-args", "--no-protect-args", "-B4096", "-T/tmp", "-4"] {
            assert!(parse(args(&[option, "src", "dst"])).is_err(), "{option}");
        }
        assert!(parse(args(&["--jobs", "src", "dst"])).is_err());
    }

    #[test]
    fn documented_no_ops_are_still_accepted() {
        for option in ["-s", "-W", "--protect-args", "--blocking-io", "--no-blocking-io", "--no-motd", "--no-clone"] {
            assert!(parse(args(&[option, "src", "dst"])).is_ok(), "{option}");
        }
    }
}
