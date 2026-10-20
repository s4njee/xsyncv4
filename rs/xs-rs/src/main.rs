//! xs-rs: a Linux client and server that speak the C++ xs version 4 stream.
//! The MVP carries regular files, directories, symlinks and FIFOs with modes
//! and nanosecond mtimes; unchanged files are compared on size and whole seconds.

mod cli;
mod ffi;
mod protocol;
mod scan;
mod transfer;

use std::ffi::{OsStr, OsString};
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::process::{Child, Command, Stdio};

use xs_wire::{Decoder, Encoder, Frame};

use crate::protocol::{feature, frame_type, msg_kind, Options};
use crate::transfer::{run_receiver, run_sender};

const VERSION: u64 = 4;
const MAGIC: &[u8; 6] = b"XSYNC\x01";
const SUPPORTED: u64 = feature::CORE | feature::ZSTD | feature::IDMAP | feature::DIR_CHILDREN;

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

fn server<R: Read, W: Write + Send + 'static>(reader: &mut R, mut writer: W) -> io::Result<i32> {
    let Some(frame) = xs_wire::read_frame(reader).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e.to_string()))? else {
        return Ok(2);
    };
    if frame.kind != frame_type::HELLO {
        write_message(&mut writer, msg_kind::FATAL, 2, "protocol error: expected HELLO")?;
        writer.flush()?;
        return Ok(2);
    }
    let (version, hello) = read_hello(&frame.payload)?;
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
    let mut answer = Encoder::new();
    answer.raw(MAGIC).var(VERSION).var(features);
    xs_wire::write_frame(&mut writer, frame_type::HELLO, &answer.bytes)?;
    writer.flush()?;

    if hello.role == b'R' {
        let dest = hello.paths.first().cloned().unwrap_or_else(|| b".".to_vec());
        let dest = cli::expand_home(&dest);
        run_receiver(reader, writer, &hello.options, features, &dest)
    } else {
        let sources: Vec<OsString> = hello.paths.iter().map(|path| OsString::from_vec(cli::expand_home(path))).collect();
        run_sender(reader, writer, &hello.options, features, &sources)
    }
}

fn client_hello(cli: &cli::Cli, role: u8, paths: &[OsString]) -> Vec<u8> {
    let o = &cli.options;
    let mut e = Encoder::new();
    e.raw(MAGIC).var(VERSION).byte(role).var(SUPPORTED);
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
        return Command::new(std::env::current_exe()?)
            .arg("--server")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn();
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

fn run_client(cli: &cli::Cli) -> io::Result<i32> {
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
    let mut input = BufReader::new(child.stdout.take().unwrap());
    let mut output = BufWriter::new(child.stdin.take().unwrap());
    xs_wire::write_frame(&mut output, frame_type::HELLO, &hello)?;
    output.flush()?;

    let reply: Frame = loop {
        let Some(frame) =
            xs_wire::read_frame(&mut input).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e.to_string()))?
        else {
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
    let features = d.var().map_err(protocol::decode_err)? & SUPPORTED;
    if !d.is_empty() {
        return protocol::bad("protocol error: malformed server hello");
    }

    let result = if push {
        run_sender(&mut input, output, &cli.options, features, &local_sources)
    } else {
        run_receiver(&mut input, output, &cli.options, features, &local_dest)
    };
    drop(input);
    let status = child.wait()?;
    let code = result?;
    if code != 0 {
        Ok(code)
    } else {
        Ok(status.code().unwrap_or(0))
    }
}

fn main() {
    let cli = match cli::parse(std::env::args_os().skip(1).collect()) {
        Ok(cli) => cli,
        Err(message) => {
            eprintln!("xs-rs: {message}");
            std::process::exit(1);
        }
    };
    let result = if cli.server {
        let mut reader = BufReader::new(io::stdin());
        server(&mut reader, BufWriter::new(io::stdout()))
    } else {
        run_client(&cli)
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
