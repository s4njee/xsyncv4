//! The codec against the C++ xs itself: run with XS_BIN naming an `xs` binary, as
//! `XS_BIN=build/xs cargo test --manifest-path rs/Cargo.toml`. Skipped without it.

use std::io::Write;
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

use xs_wire::config::{files_data, files_end, Config};
use xs_wire::{feature, frame_type, msg_kind, read_frame, write_frame, ClientHello, Message, Options, Role, ServerHello};

/// Sends one client HELLO to `xs --server` and returns the first frame it answers with.
fn first_answer(hello: &ClientHello) -> Option<xs_wire::Frame> {
    let binary = std::env::var_os("XS_BIN")?;
    let dir = std::env::temp_dir();
    let mut child = Command::new(binary)
        .arg("--server")
        .current_dir(dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("start xs --server");
    let mut stdin = child.stdin.take().unwrap();
    write_frame(&mut stdin, frame_type::HELLO, &hello.encode()).unwrap();
    stdin.flush().unwrap();
    let mut stdout = child.stdout.take().unwrap();
    let frame = read_frame(&mut stdout).expect("a frame from xs").expect("xs answered");
    drop(stdin);
    let _ = child.kill();
    let _ = child.wait();
    Some(frame)
}

fn hello(version: u64, features: u64) -> ClientHello {
    let mut options = Options::default();
    options.set_flag("recursive", true);
    ClientHello { version, role: Role::Send, features, options, rules: vec![], paths: vec!["xs-wire-interop-missing".into()] }
}

#[test]
fn the_cpp_server_answers_a_version_4_hello_with_the_negotiated_features() {
    let Some(frame) = first_answer(&hello(4, feature::CORE | feature::ZSTD | (1 << 45))) else { return };
    assert_eq!(frame.kind, frame_type::HELLO);
    let answer = ServerHello::decode(&frame.payload).unwrap();
    assert_eq!(answer.version, 4);
    // A bit no xs knows is masked off; the ones both have stay.
    assert_eq!(answer.features, feature::CORE | feature::ZSTD);
}

#[test]
fn the_cpp_server_still_speaks_version_3() {
    let Some(frame) = first_answer(&hello(3, 15)) else { return };
    assert_eq!(frame.kind, frame_type::HELLO);
    assert_eq!(frame.payload, b"XSYNC\x01\x03", "a version 3 server HELLO has no feature word");
}

#[test]
fn the_cpp_server_refuses_an_unknown_version_with_a_fatal_message_naming_its_own() {
    let Some(frame) = first_answer(&hello(9, feature::CORE)) else { return };
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    assert!(message.text.contains("protocol version mismatch: client 9, server 4"), "{}", message.text);
    assert_eq!(xs_wire::hello::server_version_in(&message.text), Some(4));
}

fn open_server(features: u64, options: Options) -> Option<(Child, ChildStdin, ChildStdout, PathBuf)> {
    let binary = std::env::var_os("XS_BIN")?;
    let dir = std::env::temp_dir().join(format!("xs-wire-config-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    let mut child = Command::new(binary)
        .arg("--server")
        .current_dir(&dir)
        .env("XSYNC_CONFIG", "")
        .env("XSYNC_OPTS", "")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .expect("start xs --server");
    let mut input = child.stdin.take().unwrap();
    let mut output = child.stdout.take().unwrap();
    let hello = ClientHello { version: 4, role: Role::Receive, features, options, rules: vec![], paths: vec!["target".into()] };
    write_frame(&mut input, frame_type::HELLO, &hello.encode()).unwrap();
    let answer = read_frame(&mut output).expect("a HELLO from xs").expect("xs answered");
    assert_eq!(answer.kind, frame_type::HELLO, "{:?}", Message::decode(&answer.payload));
    Some((child, input, output, dir))
}

fn send(input: &mut ChildStdin, config: &Config) {
    let frame = config.encode();
    write_frame(input, frame.kind, &frame.payload).unwrap();
}

#[test]
fn the_cpp_server_accepts_every_configuration_frame_in_order() {
    let mut options = Options::default();
    options.set_flag("recursive", true).set_flag("compress", true).set_flag("del", true);
    // Every feature but listing and what this platform's xs does not have (PF_UNSUPPORTED_NATIVE, common.h).
    #[cfg(target_os = "macos")]
    let unsupported = feature::ACL_POSIX;
    #[cfg(not(target_os = "macos"))]
    let unsupported = feature::ACL_DARWIN | feature::ACL_UUID | feature::CRTIMES | feature::FILEFLAGS;
    let features = !(feature::LIST | unsupported);
    let Some((mut child, mut input, mut output, dir)) = open_server(features, options) else { return };
    for config in [
        Config::Io { bwlimit: 1 << 20, timeout: 60 },
        Config::Compress { explicit_level: true, skip_compress: b"gz/zip".to_vec() },
        Config::Xattr(2),
        Config::Acl,
        Config::Chown { user: b"1000".to_vec(), group: b"1000".to_vec() },
        Config::Sparse,
        Config::LinkDest { dirs: vec![b"../snapshot".to_vec()] },
        Config::Relative,
        Config::Files { mode: 1, from0: false, path: vec![] },
    ] {
        send(&mut input, &config);
    }
    let ack = read_frame(&mut output).expect("a files-from acknowledgement").expect("xs answered");
    assert_eq!((ack.kind, ack.payload), (frame_type::FILES_CONFIG, vec![0]));
    for frame in [files_data(b"x\n").unwrap(), files_end(2)] {
        write_frame(&mut input, frame.kind, &frame.payload).unwrap();
    }
    for config in [
        Config::Filter { cvs: Some(true), rules: vec![b"P keep".to_vec(), b"- *.tmp".to_vec()] },
        Config::Delete,
        Config::Prune,
        Config::Output { attrs: true, unchanged: false, mkpath: true, delete_before: false },
    ] {
        send(&mut input, &config);
    }
    let frame = read_frame(&mut output).expect("a frame from xs").expect("xs answered");
    assert_eq!(frame.kind, frame_type::DEST, "xs refused a configuration: {:?}", Message::decode(&frame.payload));
    let _ = child.kill();
    let _ = child.wait();
    let _ = std::fs::remove_dir_all(dir);
}
