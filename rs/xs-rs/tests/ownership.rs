//! `PF_CHOWN` and `PF_IDMAP` against the parent's C++ xs. Tests that need the
//! C++ binary skip when `XS_BIN` is unset, as the other interop tests do.

use std::fs;
use std::os::unix::fs::MetadataExt;
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

use xs_wire::config::Config;
use xs_wire::{feature, frame_type, msg_kind, read_frame, write_frame, ClientHello, Message, Options, Role};

fn xs_bin() -> Option<PathBuf> {
    std::env::var_os("XS_BIN").map(PathBuf::from)
}

fn xs_rs() -> &'static str {
    env!("CARGO_BIN_EXE_xs-rs")
}

fn fakessh() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tests/fakessh.sh")
}

fn temp_root(tag: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    let unique =
        format!("xs-rs-own-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn run(mut command: Command) -> std::process::Output {
    command.output().expect("start the transfer")
}

fn ids() -> (u32, u32) {
    // SAFETY: both queries have no arguments and no failure mode.
    unsafe { (getuid(), getgid()) }
}

extern "C" {
    fn getuid() -> u32;
    fn getgid() -> u32;
}

#[test]
fn cpp_client_chown_override_reaches_the_rust_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-chown");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    fs::write(source.join("file"), b"ownership\n").unwrap();
    let (uid, gid) = ids();
    let output = run({
        let mut command = Command::new(cpp);
        command
            .arg("-a")
            .arg(format!("--chown={uid}:{gid}"))
            .arg("-e")
            .arg(fakessh())
            .arg(format!("--rsync-path={}", xs_rs()))
            .arg(format!("{}/", source.display()))
            .arg(format!("fake:{}/", dest.display()));
        command
    });
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    let metadata = fs::metadata(dest.join("file")).unwrap();
    assert_eq!((metadata.uid(), metadata.gid()), (uid, gid));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn rust_client_chown_override_reaches_the_cpp_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-chown");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    fs::write(source.join("file"), b"ownership\n").unwrap();
    let (uid, gid) = ids();
    let output = run({
        let mut command = Command::new(xs_rs());
        command
            .arg("-a")
            .arg(format!("--chown={uid}:{gid}"))
            .arg("-e")
            .arg(fakessh())
            .arg(format!("--rsync-path={}", cpp.display()))
            .arg(format!("{}/", source.display()))
            .arg(format!("fake:{}/", dest.display()));
        command
    });
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    let metadata = fs::metadata(dest.join("file")).unwrap();
    assert_eq!((metadata.uid(), metadata.gid()), (uid, gid));
    let _ = fs::remove_dir_all(root);
}

struct Server {
    child: Child,
    input: ChildStdin,
    output: ChildStdout,
}

fn start_server(features: u64, role: Role, helper: &[&str]) -> Server {
    let mut child = Command::new(xs_rs())
        .arg("--server")
        .args(helper)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
    let mut input = child.stdin.take().unwrap();
    let output = child.stdout.take().unwrap();
    let hello = ClientHello {
        version: 4,
        role,
        features,
        options: Options::default(),
        rules: vec![],
        paths: vec!["uncreated".into()],
    };
    write_frame(&mut input, frame_type::HELLO, &hello.encode()).unwrap();
    Server { child, input, output }
}

fn next(server: &mut Server) -> xs_wire::Frame {
    read_frame(&mut server.output).unwrap().expect("a frame from xs-rs")
}

fn fatal(frame: &xs_wire::Frame) -> (u8, u64) {
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(frame.kind, frame_type::MSG);
    assert_eq!(message.kind, msg_kind::FATAL);
    assert!(message.text.contains("protocol error") || message.text.contains("--chown"), "{}", message.text);
    (message.kind, message.code)
}

#[test]
fn malformed_or_wrong_side_ownership_configuration_is_refused() {
    let cases: &[(&str, Role, &[u8])] = &[
        ("empty", Role::Receive, b""),
        ("truncated", Role::Receive, b"\x80"),
        ("missing-group", Role::Receive, b"\x01\x30"),
        ("empty-fields", Role::Receive, b"\0\0"),
        ("user-nul", Role::Receive, b"\x03a\0b\0"),
        ("user-colon", Role::Receive, b"\x03a:b\0"),
        ("extra-map", Role::Receive, b"\x030,1\0"),
        ("trailing", Role::Receive, b"\x010\0x"),
    ];
    for (label, role, payload) in cases {
        let mut server = start_server(feature::CORE | feature::CHOWN, *role, &[]);
        assert_eq!(next(&mut server).kind, frame_type::HELLO, "{label}");
        write_frame(&mut server.input, frame_type::CHOWN_CONFIG, payload).unwrap();
        let (_, code) = fatal(&next(&mut server));
        assert_eq!(code, 2, "{label}");
        assert_eq!(server.child.wait().unwrap().code(), Some(2), "{label}");
    }
    let mut server = start_server(feature::CORE | feature::CHOWN, Role::Send, &[]);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    let frame = Config::Chown { user: b"0".to_vec(), group: vec![] }.encode();
    write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
    assert_eq!(fatal(&next(&mut server)).1, 2);
    assert_eq!(server.child.wait().unwrap().code(), Some(2));
}

#[test]
fn an_unnegotiated_ownership_configuration_is_refused_after_dest() {
    let mut server = start_server(feature::CORE, Role::Receive, &[]);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    let frame = Config::Chown { user: b"0".to_vec(), group: vec![] }.encode();
    write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    assert_eq!(fatal(&next(&mut server)).1, 2);
    assert_eq!(server.child.wait().unwrap().code(), Some(2));
}

#[test]
fn a_helper_chown_needs_peer_negotiation_and_cannot_be_repeated() {
    let mut server = start_server(feature::CORE, Role::Receive, &["--chown=0"]);
    assert_eq!(fatal(&next(&mut server)), (msg_kind::FATAL, 4));
    assert_eq!(server.child.wait().unwrap().code(), Some(4));

    for helper in ["--chown=0", "--chown=:0"] {
        let mut server = start_server(feature::CORE | feature::IDMAP | feature::CHOWN, Role::Receive, &[helper]);
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        let (user, group): (Vec<u8>, Vec<u8>) =
            if helper == "--chown=0" { (b"0".to_vec(), vec![]) } else { (vec![], b"0".to_vec()) };
        let frame = Config::Chown { user, group }.encode();
        write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
        assert_eq!(fatal(&next(&mut server)), (msg_kind::FATAL, 1));
        assert_eq!(server.child.wait().unwrap().code(), Some(1));
    }
}

#[test]
fn a_negotiated_ownership_configuration_is_accepted() {
    let mut server = start_server(feature::CORE | feature::CHOWN, Role::Receive, &[]);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    let frame = Config::Chown { user: b"root".to_vec(), group: vec![] }.encode();
    write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    drop(server.input);
    let _ = server.child.wait();
}

#[test]
fn idmap_records_survive_an_unrelated_name_and_are_bounded() {
    // A name that cannot exist still consumes the record without failing a transfer.
    let mut server = start_server(feature::CORE | feature::IDMAP | feature::IO_CONTROL, Role::Receive, &[]);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    let io = Config::Io { bwlimit: 0, timeout: 0 }.encode();
    write_frame(&mut server.input, io.kind, &io.payload).unwrap();
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    let map = xs_wire::idmap::encode(&[xs_wire::idmap::Entry {
        kind: xs_wire::idmap::USER,
        id: 1,
        name: b"no-such-user-xs-rs".to_vec(),
    }]);
    write_frame(&mut server.input, map.kind, &map.payload).unwrap();
    write_frame(&mut server.input, frame_type::KEEPALIVE, &[]).unwrap();
    write_frame(&mut server.input, frame_type::LIST_END, &[]).unwrap();
    let mut frame = xs_wire::Encoder::new();
    frame.var(0);
    write_frame(&mut server.input, frame_type::DATA_END, &frame.bytes).unwrap();
    assert_eq!(next(&mut server).kind, frame_type::DONE);
    drop(server.input);
    assert_eq!(server.child.wait().unwrap().code(), Some(0));
}

#[test]
fn an_unnegotiated_idmap_is_refused() {
    let mut server = start_server(feature::CORE, Role::Receive, &[]);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    let map = xs_wire::idmap::encode(&[xs_wire::idmap::Entry { kind: xs_wire::idmap::USER, id: 1, name: b"root".to_vec() }]);
    write_frame(&mut server.input, map.kind, &map.payload).unwrap();
    let frame = next(&mut server);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(frame.kind, frame_type::MSG);
    assert_eq!(message.code, 2);
    assert!(message.text.contains("ID map"), "{}", message.text);
    assert_eq!(server.child.wait().unwrap().code(), Some(2));
}
