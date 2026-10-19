//! The codec against the C++ xs itself: run with XS_BIN naming an `xs` binary, as
//! `XS_BIN=build/xs cargo test --manifest-path rs/Cargo.toml`. Skipped without it.

use std::io::Write;
use std::process::{Command, Stdio};

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
