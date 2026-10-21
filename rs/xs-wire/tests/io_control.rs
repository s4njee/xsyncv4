//! IO_CONTROL against the parent's C++ xs: run with XS_BIN naming an `xs` binary.
//! Every test returns early when XS_BIN is unset.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

use xs_wire::config::Config;
use xs_wire::io_control::keepalive;
use xs_wire::{feature, frame_type, msg_kind, read_frame, write_frame, ClientHello, Message, Options, Role};

fn xs_bin() -> Option<PathBuf> {
    std::env::var_os("XS_BIN").map(PathBuf::from)
}

fn temp_root(tag: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    let unique = format!(
        "xs-wire-io-{tag}-{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
    );
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

struct Server {
    child: Child,
    input: ChildStdin,
    output: ChildStdout,
}

impl Drop for Server {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn open_server(features: u64, dir: &Path) -> Option<Server> {
    let mut child = Command::new(xs_bin()?)
        .arg("--server")
        .current_dir(dir)
        .env("XSYNC_CONFIG", "")
        .env("XSYNC_OPTS", "")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("start xs --server");
    let mut input = child.stdin.take().unwrap();
    let output = child.stdout.take().unwrap();
    let hello = ClientHello {
        version: 4,
        role: Role::Receive,
        features,
        options: Options::default(),
        rules: vec![],
        paths: vec!["target".into()],
    };
    write_frame(&mut input, frame_type::HELLO, &hello.encode()).unwrap();
    input.flush().unwrap();
    Some(Server { child, input, output })
}

fn next(server: &mut Server) -> xs_wire::Frame {
    read_frame(&mut server.output).unwrap().expect("a frame from xs")
}

fn send_io(server: &mut Server, bwlimit: u64, timeout: u64) {
    let frame = Config::Io { bwlimit, timeout }.encode();
    write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
    server.input.flush().unwrap();
}

#[test]
fn the_cpp_server_accepts_io_config_then_keepalives() {
    let Some(dir) = xs_bin().map(|_| temp_root("accept")) else { return };
    let Some(mut server) = open_server(feature::CORE | feature::IO_CONTROL, &dir) else { return };
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    send_io(&mut server, 1 << 20, 1);
    let heartbeat = keepalive();
    write_frame(&mut server.input, heartbeat.kind, &heartbeat.payload).unwrap();
    server.input.flush().unwrap();
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    drop(server);
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn the_cpp_server_refuses_a_keepalive_before_io_configuration() {
    let Some(dir) = xs_bin().map(|_| temp_root("early")) else { return };
    let Some(mut server) = open_server(feature::CORE | feature::IO_CONTROL, &dir) else { return };
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    let heartbeat = keepalive();
    write_frame(&mut server.input, heartbeat.kind, &heartbeat.payload).unwrap();
    server.input.flush().unwrap();
    let frame = next(&mut server);
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    assert!(message.text.contains("keep-alive"), "{}", message.text);
    drop(server);
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn the_cpp_server_refuses_a_nonempty_or_unnegotiated_keepalive() {
    let Some(dir) = xs_bin().map(|_| temp_root("invalid")) else { return };
    {
        let Some(mut server) = open_server(feature::CORE | feature::IO_CONTROL, &dir) else { return };
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        send_io(&mut server, 0, 1);
        write_frame(&mut server.input, frame_type::KEEPALIVE, b"bad").unwrap();
        server.input.flush().unwrap();
        let mut fatal = None;
        for _ in 0..2 {
            let frame = next(&mut server);
            if frame.kind == frame_type::MSG {
                fatal = Some(frame);
                break;
            }
        }
        let frame = fatal.expect("xs refused the nonempty keep-alive");
        let message = Message::decode(&frame.payload).unwrap();
        assert!(message.text.contains("keep-alive"), "{}", message.text);
    }
    {
        let Some(mut server) = open_server(feature::CORE, &dir) else { return };
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        let heartbeat = keepalive();
        write_frame(&mut server.input, heartbeat.kind, &heartbeat.payload).unwrap();
        server.input.flush().unwrap();
        let mut fatal = None;
        for _ in 0..2 {
            let frame = next(&mut server);
            if frame.kind == frame_type::MSG {
                fatal = Some(frame);
                break;
            }
        }
        let frame = fatal.expect("xs refused the unnegotiated keep-alive");
        let message = Message::decode(&frame.payload).unwrap();
        assert!(message.text.contains("keep-alive"), "{}", message.text);
    }
    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn the_cpp_server_refuses_an_oversized_or_malformed_io_configuration() {
    let Some(dir) = xs_bin().map(|_| temp_root("malformed")) else { return };
    for payload in [vec![0u8; 21], vec![0x80], vec![0, 0, 0]] {
        let Some(mut server) = open_server(feature::CORE | feature::IO_CONTROL, &dir) else { return };
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        // xs may refuse an oversized frame from its length alone and exit before the rest is
        // written: a broken pipe here is the race, not a failure. Its refusal is still read.
        let _ = write_frame(&mut server.input, frame_type::IO_CONFIG, &payload);
        let _ = server.input.flush();
        let frame = next(&mut server);
        assert_eq!(frame.kind, frame_type::MSG);
        let message = Message::decode(&frame.payload).unwrap();
        assert_eq!(message.kind, msg_kind::FATAL);
        assert_eq!(message.code, 2);
        assert!(message.text.contains("I/O configuration"), "{}", message.text);
    }
    let _ = fs::remove_dir_all(&dir);
}
