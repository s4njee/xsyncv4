//! Interop against the parent's C++ xs. Run with
//! `XS_BIN=.../parent/build/xs cargo test --manifest-path rs/Cargo.toml`; every test
//! that needs the C++ binary returns early when XS_BIN is unset.

use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::Read;
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{FileTypeExt, MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use xs_wire::{frame_type, msg_kind, read_frame, write_frame, Encoder, Message};

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
        format!("xs-rs-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn set_mtime(path: &Path, secs: u64, nanos: u32) {
    let file = fs::OpenOptions::new().read(true).write(true).open(path).or_else(|_| fs::File::open(path)).unwrap();
    let time = UNIX_EPOCH + Duration::new(secs, nanos);
    file.set_times(fs::FileTimes::new().set_modified(time).set_accessed(time)).unwrap();
}

fn make_tree(root: &Path) {
    fs::create_dir_all(root.join("a/b/c")).unwrap();
    fs::create_dir_all(root.join("empty-dir")).unwrap();
    fs::write(root.join("a/b/c/small.txt"), b"hello\n".repeat(400)).unwrap();
    fs::write(root.join("a/big.bin"), (0u8..=255).cycle().take(700_000).collect::<Vec<_>>()).unwrap();
    fs::write(root.join("a/huge.bin"), (0u8..=255).cycle().take(2_500_000).collect::<Vec<_>>()).unwrap();
    fs::write(root.join("empty"), b"").unwrap();
    fs::write(root.join("with space.txt"), b"space").unwrap();
    fs::write(root.join(OsStr::from_bytes(b"non-utf8-\xff")), b"raw name").unwrap();
    fs::set_permissions(root.join("a/b/c/small.txt"), fs::Permissions::from_mode(0o640)).unwrap();
    std::os::unix::fs::symlink("a/b/c/small.txt", root.join("link")).unwrap();
    std::os::unix::fs::symlink("missing-target", root.join("dangling")).unwrap();
    set_mtime(&root.join("a/big.bin"), 1_600_000_000, 123_456_789);
    set_mtime(&root.join("a/b/c/small.txt"), 1_500_000_111, 987_654_321);
    set_mtime(&root.join("empty"), 1_500_000_222, 5);
    set_mtime(&root.join("a"), 1_400_000_000, 42);
}

#[derive(Debug, PartialEq, Eq)]
enum Kind {
    File,
    Dir,
    Link(Vec<u8>),
    Fifo,
    Other,
}

#[derive(Debug, PartialEq, Eq)]
struct Node {
    kind: Kind,
    mode: u32,
    mtime: i64,
    mtime_ns: i64,
    bytes: Vec<u8>,
}

fn read_node(path: &Path) -> Node {
    let m = fs::symlink_metadata(path).unwrap();
    let ft = m.file_type();
    let kind = if ft.is_symlink() {
        Kind::Link(fs::read_link(path).unwrap().into_os_string().into_vec())
    } else if ft.is_dir() {
        Kind::Dir
    } else if ft.is_file() {
        Kind::File
    } else if ft.is_fifo() {
        Kind::Fifo
    } else {
        Kind::Other
    };
    Node {
        kind,
        mode: m.mode() & 0o7777,
        mtime: m.mtime(),
        mtime_ns: m.mtime_nsec(),
        bytes: if ft.is_file() { fs::read(path).unwrap() } else { Vec::new() },
    }
}

fn compare_tree(source: &Path, dest: &Path) {
    let mut source_nodes = Vec::new();
    let mut dest_nodes = Vec::new();
    collect(source, source, &mut source_nodes);
    collect(dest, dest, &mut dest_nodes);
    assert_eq!(source_nodes.len(), dest_nodes.len(), "different entry counts");
    for ((srel, snode), (drel, dnode)) in source_nodes.iter().zip(dest_nodes.iter()) {
        assert_eq!(srel, drel);
        assert_eq!(snode, dnode, "{} differs", srel.to_string_lossy());
    }
}

fn collect(root: &Path, dir: &Path, out: &mut Vec<(PathBuf, Node)>) {
    let mut entries: Vec<_> = fs::read_dir(dir).unwrap().map(|e| e.unwrap()).collect();
    entries.sort_by(|a, b| a.file_name().as_bytes().cmp(b.file_name().as_bytes()));
    for entry in entries {
        let path = entry.path();
        let rel = path.strip_prefix(root).unwrap().to_path_buf();
        let metadata = fs::symlink_metadata(&path).unwrap();
        if metadata.is_dir() {
            collect(root, &path, out);
        }
        out.push((rel, read_node(&path)));
    }
}

fn cpp_remote_command(cpp: &Path, source: &Path, dest: &Path, pull: bool) -> Command {
    let mut command = Command::new(cpp);
    command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", xs_rs()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

fn rust_remote_command(cpp: &Path, source: &Path, dest: &Path, pull: bool) -> Command {
    let mut command = Command::new(xs_rs());
    command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", cpp.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

fn run(mut command: Command) {
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

#[test]
fn cpp_client_pushes_to_the_rust_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-push");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    make_tree(&source);
    run(cpp_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    // A second run is a no-op and must leave the same tree.
    run(cpp_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    fs::write(source.join("a/b/c/small.txt"), b"changed after the first copy").unwrap();
    set_mtime(&source.join("a/b/c/small.txt"), 1_500_000_333, 7);
    run(cpp_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn cpp_client_pulls_from_the_rust_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-pull");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    make_tree(&source);
    run(cpp_remote_command(&cpp, &source, &dest, true));
    compare_tree(&source, &dest);
    run(cpp_remote_command(&cpp, &source, &dest, true));
    compare_tree(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn rust_client_pushes_to_the_cpp_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    make_tree(&source);
    run(rust_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    run(rust_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    fs::write(source.join("a/huge.bin"), b"shrunk").unwrap();
    set_mtime(&source.join("a/huge.bin"), 1_500_000_444, 99);
    run(rust_remote_command(&cpp, &source, &dest, false));
    compare_tree(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn rust_client_pulls_from_the_cpp_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    make_tree(&source);
    run(rust_remote_command(&cpp, &source, &dest, true));
    compare_tree(&source, &dest);
    run(rust_remote_command(&cpp, &source, &dest, true));
    compare_tree(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn compressed_transfers_interoperate() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("zstd");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    let programs: [(&str, &Path); 2] = [(xs_rs(), cpp.as_path()), (cpp.to_str().unwrap(), Path::new(xs_rs()))];
    for (pair, (program, remote)) in programs.into_iter().enumerate() {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            let mut command = Command::new(program);
            command.arg("-az").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
            if pull {
                command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
            } else {
                command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
            }
            run(command);
            compare_tree(&source, &dest);
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_single_file_destination_is_created_under_its_own_name() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("single");
    let source = root.join("file.txt");
    fs::write(&source, b"one file\n".repeat(1000)).unwrap();
    set_mtime(&source, 1_510_000_000, 123);
    let cases: [(&OsStr, &Path, bool); 4] = [
        (OsStr::new(xs_rs()), cpp.as_path(), false),
        (OsStr::new(xs_rs()), cpp.as_path(), true),
        (cpp.as_os_str(), Path::new(xs_rs()), false),
        (cpp.as_os_str(), Path::new(xs_rs()), true),
    ];
    for (index, (program, remote, pull)) in cases.into_iter().enumerate() {
        let dest = root.join(format!("single-{index}"));
        let mut command = Command::new(program);
        command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
        if pull {
            command.arg(format!("fake:{}", source.display())).arg(dest.display().to_string());
        } else {
            command.arg(source.display().to_string()).arg(format!("fake:{}", dest.display()));
        }
        run(command);
        assert_eq!(fs::read(&dest).unwrap(), fs::read(&source).unwrap());
        let metadata = fs::metadata(&dest).unwrap();
        assert_eq!(metadata.mtime(), 1_510_000_000);
        assert_eq!(metadata.mtime_nsec(), 123);
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn the_rust_server_refuses_an_unknown_protocol_version() {
    for version in [3u64, 9] {
        let mut child = Command::new(xs_rs())
            .arg("--server")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .unwrap();
        let mut input = child.stdin.take().unwrap();
        let mut output = child.stdout.take().unwrap();
        let mut hello = Encoder::new();
        hello.raw(b"XSYNC\x01").var(version).byte(b'R');
        if version >= 4 {
            hello.var(1);
        }
        write_frame(&mut input, frame_type::HELLO, &hello.bytes).unwrap();
        drop(input);
        let frame = read_frame(&mut output).unwrap().expect("a refusal");
        assert_eq!(frame.kind, frame_type::MSG);
        let message = Message::decode(&frame.payload).unwrap();
        assert_eq!(message.kind, msg_kind::FATAL);
        assert_eq!(message.code, 2);
        assert!(message.text.contains(&format!("client {version}")), "{}", message.text);
        assert!(message.text.contains("server 4"), "{}", message.text);
        let status = child.wait().unwrap();
        assert_eq!(status.code(), Some(2));
        let mut trailing = Vec::new();
        output.read_to_end(&mut trailing).unwrap();
    }
}

#[test]
fn the_rust_server_refuses_a_hostile_file_name() {
    let mut child =
        Command::new(xs_rs()).arg("--server").stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().unwrap();
    let mut input = child.stdin.take().unwrap();
    let mut output = child.stdout.take().unwrap();
    let mut hello = Encoder::new();
    hello.raw(b"XSYNC\x01").var(4).byte(b'R').var(1);
    for index in 0..32 {
        hello.byte(u8::from(index == 6 || index == 7));
    }
    for _ in 0..7 {
        hello.svar(0);
    }
    hello.var(0).var(1).str(b"dst");
    write_frame(&mut input, frame_type::HELLO, &hello.bytes).unwrap();
    let _ = read_frame(&mut output).unwrap().expect("the server HELLO");
    let dest = read_frame(&mut output).unwrap().expect("F_DEST");
    assert_eq!(dest.kind, frame_type::DEST);
    let mut body = Encoder::new();
    body.str(b"").var(0o755).svar(0).var(0).var(0).var(0).var(1).var(1);
    body.str(b"../escape").byte(1).var(0o644).svar(0).var(0).var(0).var(0).var(0);
    let mut dir = Encoder::new();
    dir.var(0).var(0).var(0).byte(1).raw(&body.bytes);
    write_frame(&mut input, frame_type::DIR, &dir.bytes).unwrap();
    let frame = read_frame(&mut output).unwrap().expect("a refusal");
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    let _ = child.kill();
    let _ = child.wait();
}

#[test]
fn the_rust_client_reports_a_servers_refusal() {
    // A tiny peer that answers the HELLO with a fatal version message.
    let child = Command::new(xs_rs())
        .args(["-a", "src/", "fake:dst/"])
        .env("XSYNC_RSH", fake_server_script())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert_eq!(output.status.code(), Some(2));
    assert!(String::from_utf8_lossy(&output.stderr).contains("protocol version mismatch"));
}

fn fake_server_script() -> OsString {
    // The script ignores the host and the program name and answers a fixed MSG.
    // Writing it in a temp file keeps the test independent of shell quoting.
    let root = temp_root("fake-ssh");
    let script = root.join("fake-ssh.sh");
    let python = root.join("refuser.py");
    fs::write(
        &python,
        b"import sys,struct\nh=sys.stdin.buffer.read(5)\nn=struct.unpack('<I',h[:4])[0]\nsys.stdin.buffer.read(n)\np=b'\\x02\\x02protocol version mismatch: client 9, server 4'\nsys.stdout.buffer.write(struct.pack('<IB',len(p),8)+p)\nsys.stdout.buffer.flush()\nsys.exit(2)\n",
    )
    .unwrap();
    fs::write(
        &script,
        format!(
            "#!/bin/sh\nwhile [ \"$1\" != \"fake\" ] && [ $# -gt 0 ]; do shift; done\n[ $# -gt 0 ] && shift\nexec python3 {} \"$@\"\n",
            python.display()
        ),
    )
    .unwrap();
    fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).unwrap();
    script.into_os_string()
}
