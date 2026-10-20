//! `PF_OUTPUT`, `PF_DIR_OUTPUT` and `PF_PROGRESS_ACK` against the C++ xs and a hostile
//! peer. Tests that need the C++ binary return early when XS_BIN is unset.

use std::fs;
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
        format!("xs-rs-output-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn make_tree(root: &Path) {
    fs::create_dir_all(root.join("sub")).unwrap();
    fs::write(root.join("a"), b"first\n").unwrap();
    fs::write(root.join("sub/nested"), b"nested\n").unwrap();
    std::os::unix::fs::symlink("a", root.join("link")).unwrap();
}

fn transfer(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool, extra: &[&str]) -> std::process::Output {
    let mut command = Command::new(program);
    command.arg("-a").args(extra).arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display())).env("XSYNC_CONFIG", "");
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command.output().expect("start the transfer")
}

fn text(output: &[u8]) -> String {
    String::from_utf8_lossy(output).into_owned()
}

#[test]
fn a_cpp_client_push_is_itemized_by_the_rust_receiver() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-push");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = transfer(&cpp, Path::new(xs_rs()), &source, &dest, false, &["-i"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains("<f+++++++++ a"), "{stdout:?}");
    assert!(stdout.contains("<f+++++++++ sub/nested"), "{stdout:?}");
    assert!(stdout.contains("cd+++++++++ ./"), "{stdout:?}");
    assert!(stdout.contains("cd+++++++++ sub/"), "{stdout:?}");
    assert!(stdout.contains("cL+++++++++ link"), "{stdout:?}");
    assert_eq!(fs::read(dest.join("a")).unwrap(), b"first\n");
    // A second -i run reports nothing: the files are unchanged.
    let again = transfer(&cpp, Path::new(xs_rs()), &source, &dest, false, &["-i"]);
    assert!(again.status.success(), "{}", text(&again.stderr));
    assert!(again.stdout.is_empty(), "{:?}", text(&again.stdout));
    // -ii reports every unchanged entry with spaces in the itemized columns.
    let unchanged = transfer(&cpp, Path::new(xs_rs()), &source, &dest, false, &["-ii", "--out-format=%i|%n"]);
    assert!(unchanged.status.success(), "{}", text(&unchanged.stderr));
    let rows = text(&unchanged.stdout);
    assert!(rows.contains(".d         |./"), "{rows:?}");
    assert!(rows.contains(".f         |a"), "{rows:?}");
    assert!(rows.contains(".L         |link"), "{rows:?}");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_client_pull_is_itemized_by_the_rust_sender_wire_layout() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-pull");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = transfer(&cpp, Path::new(xs_rs()), &source, &dest, true, &["-i"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains(">f+++++++++ a"), "{stdout:?}");
    assert!(stdout.contains(">f+++++++++ sub/nested"), "{stdout:?}");
    assert!(stdout.contains("cd+++++++++ ./"), "{stdout:?}");
    assert_eq!(fs::read(dest.join("sub/nested")).unwrap(), b"nested\n");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_renders_the_cpp_receivers_events_for_a_push() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = transfer(Path::new(xs_rs()), &cpp, &source, &dest, false, &["-i"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains("<f+++++++++ a"), "{stdout:?}");
    assert!(stdout.contains("<f+++++++++ sub/nested"), "{stdout:?}");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_pull_renders_local_events_with_the_cpp_senders_dir_output() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = transfer(Path::new(xs_rs()), &cpp, &source, &dest, true, &["-i"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains(">f+++++++++ a"), "{stdout:?}");
    assert!(stdout.contains(">f+++++++++ sub/nested"), "{stdout:?}");
    assert_eq!(fs::read(dest.join("a")).unwrap(), b"first\n");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_formats_fields_the_way_the_cpp_does() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("format");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output =
        transfer(Path::new(xs_rs()), &cpp, &source, &dest, false, &["--out-format=%i|%n|%o|%l|%-8b|%%"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains("<f+++++++++|a|send|6|6       |%"), "{stdout:?}");
    assert!(stdout.contains("cd+++++++++|./|send|"), "{stdout:?}");

    let escaped = transfer(Path::new(xs_rs()), &cpp, &root.join("source"), &root.join("escaped"), false, &["--out-format=%n"]);
    assert!(escaped.status.success(), "{}", text(&escaped.stderr));
    assert!(text(&escaped.stdout).contains("a\n"));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_local_copy_uses_the_receiving_arrow_like_the_cpp() {
    let root = temp_root("local");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = Command::new(xs_rs())
        .args(["-a", "-i"])
        .arg(format!("{}/", source.display()))
        .arg(format!("{}/", dest.display()))
        .env("XSYNC_CONFIG", "")
        .output()
        .unwrap();
    assert!(output.status.success(), "{}", text(&output.stderr));
    let stdout = text(&output.stdout);
    assert!(stdout.contains(">f+++++++++ a"), "{stdout:?}");
    assert!(stdout.contains("cd+++++++++ ./"), "{stdout:?}");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_progress_push_is_acknowledged_before_done() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("progress");
    let source = root.join("source");
    let dest = root.join("dest");
    make_tree(&source);
    let output = transfer(&cpp, Path::new(xs_rs()), &source, &dest, false, &["--progress"]);
    assert!(output.status.success(), "{}", text(&output.stderr));
    assert_eq!(fs::read(dest.join("sub/nested")).unwrap(), b"nested\n");
    let _ = fs::remove_dir_all(root);
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

fn open_server(features: u64, dir: &Path) -> Server {
    let mut child = Command::new(xs_rs())
        .arg("--server")
        .current_dir(dir)
        .env("XSYNC_CONFIG", "")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .unwrap();
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
    Server { child, input, output }
}

fn next(server: &mut Server) -> xs_wire::Frame {
    read_frame(&mut server.output).unwrap().expect("a frame from xs-rs")
}

#[test]
fn the_rust_server_refuses_a_malformed_output_configuration_before_creating_the_destination() {
    let root = temp_root("malformed-output");
    let mut server = open_server(feature::CORE | feature::DIR_OUTPUT, &root);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    for payload in [vec![0u8; 2], vec![0u8; 5], vec![0, 0, 2, 0]] {
        write_frame(&mut server.input, frame_type::OUTPUT_CONFIG, &payload).unwrap();
    }
    let frame = next(&mut server);
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    assert_eq!(message.code, 2);
    assert!(message.text.contains("output configuration"), "{}", message.text);
    assert_eq!(server.child.wait().unwrap().code(), Some(2));
    assert!(!root.join("target").exists());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn the_rust_server_sends_a_final_progress_ack_before_done() {
    let root = temp_root("ack");
    let mut server = open_server(feature::CORE | feature::PROGRESS_ACK, &root);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    // The root directory has no entries, so no data is needed.
    let mut body = xs_wire::Encoder::new();
    body.str(b"").var(0o755).svar(0).var(0).var(0).var(0).var(0);
    let mut dir = xs_wire::Encoder::new();
    dir.var(0).var(0).var(0).byte(1).raw(&body.bytes);
    write_frame(&mut server.input, frame_type::DIR, &dir.bytes).unwrap();
    let need = next(&mut server);
    assert_eq!((need.kind, need.payload), (frame_type::NEED, vec![0, 0]));
    let mut end = xs_wire::Encoder::new();
    end.var(0);
    write_frame(&mut server.input, frame_type::DATA_END, &end.bytes).unwrap();
    let progress = next(&mut server);
    assert_eq!(progress.kind, frame_type::PROGRESS);
    let done = next(&mut server);
    assert_eq!(done.kind, frame_type::DONE);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn the_rust_server_refuses_output_configuration_without_negotiating_it() {
    let root = temp_root("unnegotiated-output");
    let mut server = open_server(feature::CORE, &root);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    assert_eq!(next(&mut server).kind, frame_type::DEST);
    let config = Config::Output { attrs: true, unchanged: false, mkpath: false, delete_before: false }.encode();
    write_frame(&mut server.input, config.kind, &config.payload).unwrap();
    let frame = next(&mut server);
    assert_eq!(frame.kind, frame_type::MSG);
    assert_eq!(Message::decode(&frame.payload).unwrap().kind, msg_kind::FATAL);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn the_rust_client_refuses_a_hostile_peer_output_event() {
    let root = temp_root("hostile-output");
    let script = root.join("peer.py");
    let peer = r#"import struct,sys
def var(n):
 b=bytearray()
 while n>=128: b.append((n&127)|128); n>>=7
 b.append(n); return bytes(b)
def string(s):
 if isinstance(s,str): s=s.encode()
 return var(len(s))+s
def send(k,p):
 sys.stdout.buffer.write(struct.pack('<IB',len(p),k)+p); sys.stdout.buffer.flush()
def recv():
 h=sys.stdin.buffer.read(5)
 if len(h)!=5: sys.exit(0)
 n,k=struct.unpack('<IB',h); return k,sys.stdin.buffer.read(n)
recv()
send(1,b'XSYNC\1'+var(4)+var(1|4|32))
send(10,var(0)+var(0)+var(0)+var(0))
# A well-formed but control-byte itemized code is refused.
p=string('\x1bf+++++++++')+string('a')+string('')+string('')+b'\1'+var(0)+var(0)+var(0)
send(11,p)
import time; time.sleep(2)
"#;
    fs::write(&script, peer).unwrap();
    let mock = root.join("mock.sh");
    fs::write(&mock, format!("#!/bin/sh\nwhile [ \"$1\" != \"fake\" ] && [ $# -gt 0 ]; do shift; done\n[ $# -gt 0 ] && shift\nexec python3 {} \"$@\"\n", script.display()))
        .unwrap();
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(&mock, fs::Permissions::from_mode(0o755)).unwrap();
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    fs::write(source.join("a"), b"x").unwrap();
    let output = Command::new(xs_rs())
        .args(["-a", "-i", "-e"])
        .arg(&mock)
        .args(["--rsync-path=unused"])
        .arg(format!("{}/", source.display()))
        .arg(format!("fake:{}/", root.join("dest").display()))
        .env("XSYNC_CONFIG", "")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2), "{}", text(&output.stderr));
    assert!(text(&output.stderr).contains("file output"), "{}", text(&output.stderr));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn output_configuration_round_trips_the_bytes_run_client_writes() {
    let config = Config::Output { attrs: true, unchanged: true, mkpath: false, delete_before: true };
    assert_eq!(config.encode().to_bytes(), [4, 0, 0, 0, 12, 1, 1, 0, 1]);
}
