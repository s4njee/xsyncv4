//! `PF_IO_CONTROL` end to end: C++ clients and servers, the Rust pair, rate pacing,
//! idle deadlines and the keep-alives each side sends. Tests that need the C++
//! binary return early when XS_BIN is unset, as the other interop tests do.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use xs_wire::config::Config;
use xs_wire::io_control::keepalive;
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
        format!("xs-rs-io-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn make_source(root: &Path, bytes: usize) {
    fs::create_dir_all(root.join("dir")).unwrap();
    fs::write(root.join("small.txt"), b"one small file\n").unwrap();
    fs::write(root.join("dir/big.bin"), (0u8..=255).cycle().take(bytes).collect::<Vec<_>>()).unwrap();
}

fn run(mut command: Command) -> std::process::Output {
    command.output().expect("start the transfer")
}

fn transfer(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool, extra: &[&str]) -> std::process::Output {
    let mut command = Command::new(program);
    command.arg("-a").args(extra).arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    run(command)
}

fn assert_same(source: &Path, dest: &Path) {
    assert_eq!(fs::read(source.join("small.txt")).unwrap(), fs::read(dest.join("small.txt")).unwrap());
    assert_eq!(fs::read(source.join("dir/big.bin")).unwrap(), fs::read(dest.join("dir/big.bin")).unwrap());
}

#[test]
fn io_control_crosses_both_implementations_in_both_directions() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cross");
    let source = root.join("source");
    make_source(&source, 300_000);
    for (program, remote) in [(xs_rs(), cpp.as_path()), (cpp.to_str().unwrap(), Path::new(xs_rs()))] {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{}-{pull}", program.replace('/', "_")));
            fs::create_dir_all(&dest).unwrap();
            let output = transfer(Path::new(program), remote, &source, &dest, pull, &["--bwlimit=1m", "--timeout=2"]);
            assert!(
                output.status.success(),
                "{program} {:?} failed: {}",
                output.status,
                String::from_utf8_lossy(&output.stderr)
            );
            assert_same(&source, &dest);
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_sender_charges_compressed_bytes_to_the_rate_limit() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rate");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    fs::write(source.join("file"), vec![b'x'; 512 * 1024]).unwrap();
    let started = Instant::now();
    let output =
        transfer(Path::new(xs_rs()), &cpp, &source, &dest, false, &["--bwlimit=256k", "--timeout=5"]);
    let elapsed = started.elapsed();
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    assert_eq!(fs::read(dest.join("file")).unwrap(), vec![b'x'; 512 * 1024]);
    // 512 KiB at 256 KiB/s cannot finish in less than a second and a half.
    assert!(elapsed >= Duration::from_millis(1500), "rate was bypassed: {elapsed:?}");
    assert!(elapsed < Duration::from_secs(12), "rate was far too slow: {elapsed:?}");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn an_idle_rust_client_times_out_with_code_30() {
    let root = temp_root("timeout");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    fs::write(source.join("file"), b"data").unwrap();
    let dest = root.join("dest");
    let started = Instant::now();
    let output = run({
        let mut command = Command::new(xs_rs());
        command
            .arg("--timeout=1")
            .arg("-e")
            .arg("sh -c 'sleep 3'")
            .arg("--rsync-path=unused")
            .arg(format!("{}/", source.display()))
            .arg(format!("fake:{}/", dest.display()));
        command
    });
    let elapsed = started.elapsed();
    assert_eq!(output.status.code(), Some(30), "{}", String::from_utf8_lossy(&output.stderr));
    assert!(String::from_utf8_lossy(&output.stderr).contains("I/O timeout after 1 second"));
    assert!(elapsed < Duration::from_secs(4), "timeout was late: {elapsed:?}");
    assert!(!dest.exists());
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

fn send_io(server: &mut Server) {
    let frame = Config::Io { bwlimit: 0, timeout: 1 }.encode();
    write_frame(&mut server.input, frame.kind, &frame.payload).unwrap();
    server.input.flush().unwrap();
}

#[test]
fn the_rust_server_refuses_invalid_and_unnegotiated_keepalives() {
    let root = temp_root("server-keepalive");
    {
        let mut server = open_server(feature::CORE | feature::IO_CONTROL, &root);
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        send_io(&mut server);
        write_frame(&mut server.input, frame_type::KEEPALIVE, b"bad").unwrap();
        let mut fatal = None;
        for _ in 0..2 {
            let frame = next(&mut server);
            if frame.kind == frame_type::MSG {
                fatal = Some(frame);
                break;
            }
        }
        let frame = fatal.expect("xs-rs refused the nonempty keep-alive");
        let message = Message::decode(&frame.payload).unwrap();
        assert_eq!(message.kind, msg_kind::FATAL);
        assert!(message.text.contains("keep-alive"), "{}", message.text);
        assert_eq!(server.child.wait().unwrap().code(), Some(2));
    }
    {
        let mut server = open_server(feature::CORE, &root);
        assert_eq!(next(&mut server).kind, frame_type::HELLO);
        let heartbeat = keepalive();
        write_frame(&mut server.input, heartbeat.kind, &heartbeat.payload).unwrap();
        let mut fatal = None;
        for _ in 0..2 {
            let frame = next(&mut server);
            if frame.kind == frame_type::MSG {
                fatal = Some(frame);
                break;
            }
        }
        let frame = fatal.expect("xs-rs refused the unnegotiated keep-alive");
        assert!(Message::decode(&frame.payload).unwrap().text.contains("keep-alive"));
        assert_eq!(server.child.wait().unwrap().code(), Some(2));
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn the_rust_server_refuses_a_malformed_io_configuration_before_creating_the_destination() {
    let root = temp_root("server-malformed");
    let mut server = open_server(feature::CORE | feature::IO_CONTROL, &root);
    assert_eq!(next(&mut server).kind, frame_type::HELLO);
    for payload in [vec![0u8; 21], vec![0x80], vec![0, 0, 0], vec![0u8; 1]] {
        write_frame(&mut server.input, frame_type::IO_CONFIG, &payload).unwrap();
    }
    // Only the first is read; it must be refused before the destination appears.
    let frame = next(&mut server);
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.code, 2);
    assert!(message.text.contains("I/O configuration"), "{}", message.text);
    assert_eq!(server.child.wait().unwrap().code(), Some(2));
    assert!(!root.join("target").exists());
    let _ = fs::remove_dir_all(root);
}
