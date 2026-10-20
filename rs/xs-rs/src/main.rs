//! xs-rs: a Linux client and server that speak the C++ xs version 4 stream.
//! The MVP carries regular files, directories, symlinks and FIFOs with modes
//! and nanosecond mtimes; unchanged files are compared on size and whole seconds.

mod cli;
mod compression;
mod ffi;
mod idmap;
mod protocol;
mod scan;
mod transfer;

use std::ffi::{OsStr, OsString};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::process::{Child, Command, Stdio};
use std::sync::Arc;

use xs_wire::config::Config;
use xs_wire::io_control::{ActivityReader, IoControl, Watchdog};
use xs_wire::{Decoder, Encoder, Frame};

use crate::protocol::{feature, frame_type, msg_kind, Options};
use crate::transfer::{run_receiver, run_sender};

const VERSION: u64 = 4;
const MAGIC: &[u8; 6] = b"XSYNC\x01";
const SUPPORTED: u64 = feature::CORE
    | feature::ZSTD
    | feature::IDMAP
    | feature::IO_CONTROL
    | feature::DIR_CHILDREN
    | feature::COMPRESS_POLICY
    | feature::CHOWN;

/// What a client advertises: the compression policy frame exists only with `-z`,
/// and the ownership override only with `--chown`, as `run_client` masks them.
fn client_advertised(options: &Options) -> u64 {
    let mut features = SUPPORTED;
    if !options.compress {
        features &= !feature::COMPRESS_POLICY;
    }
    if !options.ownership.requested() {
        features &= !feature::CHOWN;
    }
    features
}

struct Hello {
    role: u8,
    features: u64,
    options: Options,
    paths: Vec<Vec<u8>>,
}

fn options_from_flags(flags: &[bool; 32], ints: &[i64; 7]) -> Options {
    Options {
        recursive: flags[0],
        links: flags[2],
        copy_links: flags[3],
        perms: flags[4],
        times: flags[5],
        group: flags[6],
        owner: flags[7],
        devices: flags[8],
        specials: flags[9],
        compress: flags[10],
        numeric_ids: flags[25],
        compress_level: ints[1],
        ..Options::default()
    }
}

fn read_hello(payload: &[u8]) -> io::Result<(u64, Hello)> {
    let mut d = Decoder::new(payload);
    if d.raw(MAGIC.len()).map_err(protocol::decode_err)? != MAGIC {
        return protocol::bad("protocol error: bad hello from client");
    }
    let version = d.var().map_err(protocol::decode_err)?;
    let role = d.byte().map_err(protocol::decode_err)?;
    if version != VERSION {
        return Ok((version, Hello { role, features: 0, options: Options::default(), paths: Vec::new() }));
    }
    let features = d.var().map_err(protocol::decode_err)?;
    let mut flags = [false; 32];
    for flag in flags.iter_mut() {
        *flag = d.byte().map_err(protocol::decode_err)? != 0;
    }
    let mut ints = [0i64; 7];
    for value in ints.iter_mut() {
        *value = d.svar().map_err(protocol::decode_err)?;
    }
    let rules = d.var().map_err(protocol::decode_err)?;
    if rules > 100_000 {
        return protocol::bad("protocol error: too many filter rules");
    }
    for _ in 0..rules {
        d.str().map_err(protocol::decode_err)?;
    }
    let count = d.var().map_err(protocol::decode_err)?;
    if count > 1024 {
        return protocol::bad("protocol error: too many paths");
    }
    let mut paths = Vec::with_capacity(count as usize);
    for _ in 0..count {
        paths.push(d.str().map_err(protocol::decode_err)?.to_vec());
    }
    if !d.is_empty() {
        return protocol::bad("protocol error: trailing hello");
    }
    Ok((version, Hello { role, features, options: options_from_flags(&flags, &ints), paths }))
}

fn write_message(output: &mut impl Write, kind: u8, code: u64, text: &str) -> io::Result<()> {
    let message = xs_wire::Message { kind, code, text: text.to_string() };
    xs_wire::write_frame(output, frame_type::MSG, &message.encode())
}

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
fn read_configuration<R: Read>(
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
    Ok(())
}

fn server<R: Read, W: Write + Send + 'static>(
    reader: &mut R,
    mut writer: W,
    server_options: &Options,
) -> io::Result<i32> {
    let control = Arc::new(IoControl::new());
    let _watchdog = Watchdog::spawn(control.clone());
    let mut input = ActivityReader::new(reader, control.clone());
    let Some(frame) =
        xs_wire::read_frame(&mut input).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e.to_string()))?
    else {
        return Ok(2);
    };
    if frame.kind != frame_type::HELLO {
        write_message(&mut writer, msg_kind::FATAL, 2, "protocol error: expected HELLO")?;
        writer.flush()?;
        return Ok(2);
    }
    let (version, mut hello) = read_hello(&frame.payload)?;
    hello.options.ownership = server_options.ownership.clone();
    if version != VERSION {
        let text = format!("protocol version mismatch: client {version}, server {VERSION} (supports 4 and 3)");
        write_message(&mut writer, msg_kind::FATAL, 2, &text)?;
        writer.flush()?;
        return Ok(2);
    }
    if hello.role != b'R' && hello.role != b'S' {
        write_message(&mut writer, msg_kind::FATAL, 2, "protocol error: malformed hello options or role")?;
        writer.flush()?;
        return Ok(2);
    }
    let features = hello.features & SUPPORTED;
    if hello.options.ownership.requested() && features & feature::CHOWN == 0 {
        write_message(&mut writer, msg_kind::FATAL, 4, "peer does not support --chown")?;
        writer.flush()?;
        return Ok(4);
    }
    if !hello.options.numeric_ids
        && (hello.options.owner || hello.options.group || hello.options.ownership.requested())
        && features & feature::IDMAP == 0
    {
        write_message(&mut writer, msg_kind::FATAL, 4, "peer does not support user/group name mapping (use --numeric-ids)")?;
        writer.flush()?;
        return Ok(4);
    }
    let mut answer = Encoder::new();
    answer.raw(MAGIC).var(VERSION).var(features);
    xs_wire::write_frame(&mut writer, frame_type::HELLO, &answer.bytes)?;
    writer.flush()?;
    control.note_write(true);
    if let Err((code, text)) = read_configuration(&mut input, &mut hello.options, features, hello.role, &control) {
        write_message(&mut writer, msg_kind::FATAL, code as u64, &text)?;
        writer.flush()?;
        return Ok(code);
    }
    if hello.role == b'R' {
        if hello.options.ownership.user_set {
            hello.options.owner = true;
        }
        if hello.options.ownership.group_set {
            hello.options.group = true;
        }
        if let Err(text) = hello.options.ownership.init() {
            write_message(&mut writer, msg_kind::FATAL, 1, &text)?;
            writer.flush()?;
            return Ok(1);
        }
    }

    if hello.role == b'R' {
        let dest = hello.paths.first().cloned().unwrap_or_else(|| b".".to_vec());
        let dest = cli::expand_home(&dest);
        run_receiver(&mut input, writer, &hello.options, features, &dest, control)
    } else {
        let sources: Vec<OsString> = hello.paths.iter().map(|path| OsString::from_vec(cli::expand_home(path))).collect();
        run_sender(&mut input, writer, &hello.options, features, &sources, control)
    }
}

fn client_hello(cli: &cli::Cli, role: u8, paths: &[OsString]) -> Vec<u8> {
    let o = &cli.options;
    let mut e = Encoder::new();
    e.raw(MAGIC).var(VERSION).byte(role).var(client_advertised(o));
    let flags = [
        o.recursive,
        false,
        o.links,
        o.copy_links,
        o.perms,
        o.times,
        o.group,
        o.owner,
        o.devices,
        o.specials,
        o.compress,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        false,
        o.numeric_ids,
        false,
        false,
        false,
        false,
        false,
        false,
    ];
    for flag in flags {
        e.byte(flag as u8);
    }
    for value in [cli.verbose, o.compress_level, 0, 0, 0, 0, 0] {
        e.svar(value);
    }
    e.var(0);
    e.var(paths.len() as u64);
    for path in paths {
        e.str(path.as_bytes());
    }
    e.into_bytes()
}

fn spawn_peer(cli: &cli::Cli, host: &[u8], local: bool) -> io::Result<Child> {
    if local {
        let mut command = Command::new(std::env::current_exe()?);
        command.arg("--server");
        if cli.options.ownership.requested() {
            let mut value = cli.options.ownership.user.clone();
            if cli.options.ownership.group_set {
                value.push(b':');
                value.extend_from_slice(&cli.options.ownership.group);
            }
            let mut argument = b"--chown=".to_vec();
            argument.extend_from_slice(&value);
            command.arg(OsString::from_vec(argument));
        }
        return command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit()).spawn();
    }
    let rsh = cli
        .rsh
        .clone()
        .or_else(|| std::env::var_os("XSYNC_RSH"))
        .or_else(|| std::env::var_os("RSYNC_RSH"))
        .unwrap_or_else(|| OsString::from("ssh"));
    let words = cli::split_words(&rsh);
    if words.is_empty() {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "empty remote shell command"));
    }
    let mut command = Command::new(&words[0]);
    command.args(&words[1..]);
    command.arg(OsStr::from_bytes(host));
    match &cli.rsync_path {
        Some(program) => {
            command.arg(program);
        }
        None => {
            command.arg("xs");
        }
    }
    command.arg("--server");
    command.stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::inherit()).spawn()
}

fn run_client(cli: &mut cli::Cli) -> io::Result<i32> {
    if cli.paths.len() < 2 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "usage: xs-rs [options] SRC... DEST"));
    }
    let specs: Vec<cli::RemoteSpec> = cli.paths.iter().map(|path| cli::parse_remote(path)).collect();
    let remote_indices: Vec<usize> = specs.iter().enumerate().filter(|(_, spec)| spec.remote).map(|(i, _)| i).collect();
    let local = remote_indices.is_empty();
    let push = local || remote_indices.iter().all(|&i| i + 1 == cli.paths.len());
    let (host, remote_paths, local_sources, local_dest): (Vec<u8>, Vec<Vec<u8>>, Vec<OsString>, Vec<u8>) = if local {
        let dest = cli.paths.last().unwrap().as_bytes().to_vec();
        (Vec::new(), vec![dest.clone()], cli.paths[..cli.paths.len() - 1].to_vec(), dest)
    } else if push {
        let dest_spec = &specs[*remote_indices.last().unwrap()];
        (dest_spec.host.clone(), vec![dest_spec.path.clone()], cli.paths[..cli.paths.len() - 1].to_vec(), Vec::new())
    } else {
        let dest = cli.paths.last().unwrap().as_bytes().to_vec();
        let sources: Vec<OsString> = cli.paths[..cli.paths.len() - 1].to_vec();
        let mut remote = Vec::new();
        for &index in &remote_indices {
            remote.push(specs[index].path.clone());
        }
        (specs[remote_indices[0]].host.clone(), remote, sources, dest)
    };
    let role = if push { b'R' } else { b'S' };
    let hello_paths: Vec<OsString> = remote_paths.iter().map(|p| OsString::from_vec(p.clone())).collect();
    let hello = client_hello(cli, role, &hello_paths);

    let mut child = spawn_peer(cli, &host, local)?;
    let control = Arc::new(IoControl::new());
    control.configure(0, cli.options.timeout, false);
    let _watchdog = Watchdog::spawn(control.clone());
    let mut input = ActivityReader::new(BufReader::new(child.stdout.take().unwrap()), control.clone());
    let mut output = BufWriter::new(child.stdin.take().unwrap());
    xs_wire::write_frame(&mut output, frame_type::HELLO, &hello)?;
    output.flush()?;
    control.note_write(true);

    let reply: Frame = loop {
        let Some(frame) = protocol::read_checked(&mut input, false)? else {
            let status = child.wait()?;
            return Ok(status.code().unwrap_or(12));
        };
        match frame.kind {
            frame_type::HELLO => break frame,
            frame_type::MSG => {
                let message = xs_wire::Message::decode(&frame.payload).map_err(protocol::decode_err)?;
                if message.kind == msg_kind::FATAL {
                    if !message.text.is_empty() {
                        eprintln!("xs-rs: {}", message.text);
                    }
                    let _ = child.kill();
                    let _ = child.wait();
                    return Ok(message.code as i32);
                }
                if !message.text.is_empty() {
                    eprintln!("xs-rs: {}", message.text);
                }
            }
            other => {
                let _ = child.kill();
                let _ = child.wait();
                return protocol::bad(format!("protocol error: unexpected frame {other} from server"));
            }
        }
    };
    let mut d = Decoder::new(&reply.payload);
    if d.raw(MAGIC.len()).map_err(protocol::decode_err)? != MAGIC {
        return protocol::bad("protocol error: the remote side did not answer as xs");
    }
    let version = d.var().map_err(protocol::decode_err)?;
    if version != VERSION {
        eprintln!("xs-rs: protocol version mismatch: client {VERSION}, server {version}");
        let _ = child.kill();
        let _ = child.wait();
        return Ok(2);
    }
    let features = d.var().map_err(protocol::decode_err)? & client_advertised(&cli.options);
    if !d.is_empty() {
        return protocol::bad("protocol error: malformed server hello");
    }
    if cli.options.ownership.requested() && features & feature::CHOWN == 0 {
        eprintln!("xs-rs: peer does not support --chown");
        let _ = child.kill();
        let _ = child.wait();
        return Ok(4);
    }
    if !cli.options.numeric_ids
        && (cli.options.owner || cli.options.group || cli.options.ownership.requested())
        && features & feature::IDMAP == 0
    {
        eprintln!("xs-rs: peer does not support user/group name mapping (use --numeric-ids)");
        let _ = child.kill();
        let _ = child.wait();
        return Ok(4);
    }
    if (cli.options.bwlimit != 0 || cli.options.timeout != 0) && features & feature::IO_CONTROL == 0 {
        eprintln!("xs-rs: peer does not support bandwidth limits and idle timeouts");
        let _ = child.kill();
        let _ = child.wait();
        return Ok(4);
    }
    if cli.options.compress
        && cli.options.skip_compress_set
        && role == b'S'
        && features & feature::COMPRESS_POLICY == 0
    {
        eprintln!("xs-rs: peer does not support --skip-compress");
        let _ = child.kill();
        let _ = child.wait();
        return Ok(4);
    }
    if features & feature::IO_CONTROL != 0 {
        let config = Config::Io { bwlimit: cli.options.bwlimit, timeout: u64::from(cli.options.timeout) }.encode();
        control.configure(cli.options.bwlimit, cli.options.timeout, true);
        xs_wire::write_frame(&mut output, config.kind, &config.payload)?;
        output.flush()?;
        control.note_write(true);
    }
    if features & feature::COMPRESS_POLICY != 0 {
        let config = Config::Compress {
            explicit_level: cli.options.compress_level_explicit,
            skip_compress: cli.options.skip_compress.clone(),
        }
        .encode();
        xs_wire::write_frame(&mut output, config.kind, &config.payload)?;
        output.flush()?;
        control.note_write(true);
    }
    if features & feature::CHOWN != 0 {
        let (user, group) = if push {
            (cli.options.ownership.user.clone(), cli.options.ownership.group.clone())
        } else {
            (Vec::new(), Vec::new())
        };
        let config = Config::Chown { user, group }.encode();
        xs_wire::write_frame(&mut output, config.kind, &config.payload)?;
        output.flush()?;
        control.note_write(true);
    }
    if !push {
        if let Err(text) = cli.options.ownership.init() {
            eprintln!("xs-rs: {text}");
            let _ = child.kill();
            let _ = child.wait();
            return Ok(1);
        }
    }

    let result = if push {
        run_sender(&mut input, output, &cli.options, features, &local_sources, control)
    } else {
        run_receiver(&mut input, output, &cli.options, features, &local_dest, control)
    };
    drop(input);
    let status = child.wait()?;
    let code = result?;
    if code == 12 && status.code() == Some(30) {
        eprintln!("xs-rs: remote peer timed out in data send/receive");
        return Ok(30);
    }
    if code != 0 {
        Ok(code)
    } else {
        Ok(status.code().unwrap_or(0))
    }
}

fn main() {
    let mut cli = match cli::parse(std::env::args_os().skip(1).collect()) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("xs-rs: {message}");
            std::process::exit(1);
        }
    };
    let result = if cli.server {
        let mut reader = BufReader::new(io::stdin());
        server(&mut reader, BufWriter::new(io::stdout()), &cli.options)
    } else {
        run_client(&mut cli)
    };
    match result {
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("xs-rs: {error}");
            let code = if error.kind() == io::ErrorKind::InvalidData { 2 } else { 12 };
            std::process::exit(code);
        }
    }
}
