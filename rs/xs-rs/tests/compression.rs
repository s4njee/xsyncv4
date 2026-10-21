//! ZSTD interop with the parent's C++ xs: frame flags, skip suffixes, explicit levels,
//! and the refusals a hostile or older peer meets. Skipped when XS_BIN is unset.

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{SystemTime, UNIX_EPOCH};

use xs_wire::{frame_type, msg_kind, read_frame, write_frame, Encoder, Message};

fn xs_bin() -> Option<PathBuf> {
    std::env::var_os("XS_BIN").map(PathBuf::from)
}

fn xs_rs() -> &'static str {
    env!("CARGO_BIN_EXE_xs-rs")
}

fn repo(path: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../").join(path)
}

fn temp_root(tag: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    let unique =
        format!("xs-rs-comp-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn make_source(source: &Path) {
    fs::create_dir_all(source).unwrap();
    fs::write(source.join("text.txt"), b"compressible line of text\n".repeat(32 * 1024)).unwrap();
    fs::write(source.join("archive.gz"), b"compressed suffix but plain bytes\n".repeat(16 * 1024)).unwrap();
    fs::write(source.join("movie.mp4"), b"another suffix that may be skipped\n".repeat(16 * 1024)).unwrap();
}

#[derive(Debug, Clone)]
struct Frame {
    direction: String,
    kind: u8,
    bytes: usize,
    flag: i32,
}

fn captured(program: &Path, remote: &Path, log: &Path, source: &Path, dest: &Path, pull: bool, flags: &[&str]) {
    let recorder = repo("rs/xs-rs/tests/frame_recorder.py");
    let helper = format!(
        "python3 {} {} {}",
        recorder.display(),
        log.display(),
        remote.display()
    );
    let mut command = Command::new(program);
    command
        .arg("-a")
        .args(flags)
        .arg("-e")
        .arg(repo("tests/fakessh.sh"))
        .arg(format!("--rsync-path={helper}"))
        .arg("--no-progress")
        .arg("--no-fallback");
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

fn frames(log: &Path) -> Vec<Frame> {
    fs::read_to_string(log)
        .unwrap()
        .lines()
        .map(|line| {
            let mut fields = line.split_whitespace();
            Frame {
                direction: fields.next().unwrap().to_string(),
                kind: fields.next().unwrap().parse().unwrap(),
                bytes: fields.next().unwrap().parse().unwrap(),
                flag: fields.next().unwrap().parse().unwrap(),
            }
        })
        .collect()
}

#[test]
fn a_rust_sender_carries_the_cpp_compression_policy_and_skips_suffixes() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let source = root.join("source");
    make_source(&source);

    let default_dest = root.join("default");
    fs::create_dir_all(&default_dest).unwrap();
    let default_log = root.join("default.log");
    captured(Path::new(xs_rs()), &cpp, &default_log, &source, &default_dest, false, &["-z"]);
    let default_frames = frames(&default_log);
    assert_eq!(fs::read(default_dest.join("archive.gz")).unwrap(), fs::read(source.join("archive.gz")).unwrap());
    let config: Vec<_> = default_frames.iter().filter(|f| f.kind == 37 && f.direction == "client").collect();
    assert_eq!(config.len(), 1, "the client sends one compression configuration");
    assert_eq!(config[0].flag, 0, "the default level is adaptive");
    let data: Vec<_> = default_frames.iter().filter(|f| f.kind == 4 && f.direction == "client").collect();
    assert!(!data.is_empty());
    assert!(data.iter().any(|f| f.flag == 1), "compressible data is packed");
    // The .gz payload is isolated raw, byte for byte as the C++ sender does it.
    assert!(data.iter().any(|f| f.flag == 0 && f.bytes > 10_000), "a skipped suffix stays raw");

    let all_dest = root.join("all");
    fs::create_dir_all(&all_dest).unwrap();
    let all_log = root.join("all.log");
    captured(Path::new(xs_rs()), &cpp, &all_log, &source, &all_dest, false, &["-z", "--skip-compress="]);
    let all_frames = frames(&all_log);
    assert_eq!(fs::read(all_dest.join("archive.gz")).unwrap(), fs::read(source.join("archive.gz")).unwrap());
    assert!(all_frames.iter().filter(|f| f.kind == 4 && f.direction == "client").any(|f| f.flag == 1));

    let explicit_dest = root.join("explicit");
    fs::create_dir_all(&explicit_dest).unwrap();
    let explicit_log = root.join("explicit.log");
    captured(Path::new(xs_rs()), &cpp, &explicit_log, &source, &explicit_dest, false, &["-z", "--compress-level=9"]);
    let explicit_frames = frames(&explicit_log);
    let config: Vec<_> = explicit_frames.iter().filter(|f| f.kind == 37 && f.direction == "client").collect();
    assert_eq!(config[0].flag, 1, "an explicit level is marked on the wire");
    assert_eq!(fs::read(explicit_dest.join("text.txt")).unwrap(), fs::read(source.join("text.txt")).unwrap());

    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_sender_uses_the_policy_a_cpp_client_sends() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let source = root.join("source");
    make_source(&source);

    let default_dest = root.join("default");
    fs::create_dir_all(&default_dest).unwrap();
    let default_log = root.join("default.log");
    captured(&cpp, Path::new(xs_rs()), &default_log, &source, &default_dest, true, &["-z"]);
    let default_frames = frames(&default_log);
    assert_eq!(fs::read(default_dest.join("archive.gz")).unwrap(), fs::read(source.join("archive.gz")).unwrap());
    let sent: Vec<_> = default_frames.iter().filter(|f| f.kind == 4 && f.direction == "server").collect();
    assert!(!sent.is_empty());
    assert!(sent.iter().any(|f| f.flag == 1), "compressible data is packed");
    assert!(sent.iter().any(|f| f.flag == 0 && f.bytes > 10_000), "the default .gz suffix stays raw");

    let custom_dest = root.join("custom");
    fs::create_dir_all(&custom_dest).unwrap();
    let custom_log = root.join("custom.log");
    captured(&cpp, Path::new(xs_rs()), &custom_log, &source, &custom_dest, true, &["-z", "--skip-compress=mp[34]"]);
    let custom_frames = frames(&custom_log);
    let sent: Vec<_> = custom_frames.iter().filter(|f| f.kind == 4 && f.direction == "server").collect();
    assert!(sent.iter().any(|f| f.flag == 0 && f.bytes > 10_000), "mp4 is isolated raw by the class");
    assert!(sent.iter().any(|f| f.flag == 1), "the .gz file is compressed when it is not on the list");

    let none_dest = root.join("none");
    fs::create_dir_all(&none_dest).unwrap();
    let none_log = root.join("none.log");
    captured(&cpp, Path::new(xs_rs()), &none_log, &source, &none_dest, true, &["-z", "--compress-choice=none", "-z"]);
    let none_frames = frames(&none_log);
    assert!(!none_frames.iter().any(|f| f.kind == 37), "--compress-choice=none advertises no policy");
    assert!(none_frames.iter().filter(|f| f.kind == 4).all(|f| f.flag == 0));

    let _ = fs::remove_dir_all(root);
}

fn hostile_server(compress: bool, features: u64) -> (std::process::Child, std::process::ChildStdin, std::process::ChildStdout) {
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
    hello.raw(b"XSYNC\x01").var(4).byte(b'R').var(features);
    for index in 0..32 {
        hello.byte(u8::from(index == 0 || (compress && index == 10)));
    }
    for _ in 0..7 {
        hello.svar(0);
    }
    hello.var(0).var(1).str(b"target");
    write_frame(&mut input, frame_type::HELLO, &hello.bytes).unwrap();
    let answer = read_frame(&mut output).unwrap().expect("the server HELLO");
    assert_eq!(answer.kind, frame_type::HELLO);
    (child, input, output)
}

fn rejected(mut child: std::process::Child, mut input: std::process::ChildStdin, mut output: std::process::ChildStdout, data: &[u8]) {
    input.write_all(data).unwrap();
    input.flush().unwrap();
    let mut frame = read_frame(&mut output).unwrap().expect("a refusal");
    if frame.kind == frame_type::DEST {
        frame = read_frame(&mut output).unwrap().expect("a refusal after F_DEST");
    }
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    assert_eq!(message.code, 2);
    let status = child.wait().unwrap();
    assert_eq!(status.code(), Some(2));
}

fn frame(kind: u8, payload: &[u8]) -> Vec<u8> {
    let mut bytes = (payload.len() as u32).to_le_bytes().to_vec();
    bytes.push(kind);
    bytes.extend_from_slice(payload);
    bytes
}

#[test]
fn the_rust_server_refuses_malformed_compression_configurations() {
    let policy = 1 | 2 | (1 << 34);
    let mut cases = vec![
        frame(37, b""),
        frame(37, &[2, 2, b'g', b'z']),
        frame(37, &[0, 5, b'g', b'z']),
        frame(37, &[0, 2, b'[', b']']),
        frame(37, &[0, 6, b'g', b'z', 0, b'z', b'i', b'p']),
        frame(37, &[0, 2, b'g', b'z', b'x']),
        frame(2, b""),
    ];
    let oversized = {
        let mut bytes = (1u32 << 20).to_le_bytes().to_vec();
        bytes.push(37);
        bytes
    };
    cases.push(oversized);
    for data in cases {
        let (child, input, output) = hostile_server(true, policy);
        rejected(child, input, output, &data);
    }
    let (child, input, output) = hostile_server(false, policy);
    rejected(child, input, output, &frame(37, &[0, 2, b'g', b'z']));
}

#[test]
fn the_rust_server_refuses_compressed_data_without_zstd() {
    let (mut child, mut input, mut output) = hostile_server(false, 1);
    let dest = read_frame(&mut output).unwrap().expect("F_DEST");
    assert_eq!(dest.kind, frame_type::DEST);
    let mut payload = vec![1u8];
    payload.extend_from_slice(&0u64.to_le_bytes());
    payload.extend_from_slice(&[1, 0]);
    input.write_all(&frame(4, &payload)).unwrap();
    input.flush().unwrap();
    let frame = read_frame(&mut output).unwrap().expect("a refusal");
    assert_eq!(frame.kind, frame_type::MSG);
    let message = Message::decode(&frame.payload).unwrap();
    assert_eq!(message.kind, msg_kind::FATAL);
    assert!(message.text.contains("without negotiated zstd"), "{}", message.text);
    let _ = child.wait();
}

#[test]
fn a_cpp_server_still_accepts_a_rust_compression_configuration() {
    // The compressed push and pull tests above prove this end to end; this one
    // checks explicitly that a raw choice sends no configuration at all.
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("raw");
    let source = root.join("source");
    make_source(&source);
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let log = root.join("raw.log");
    captured(Path::new(xs_rs()), &cpp, &log, &source, &dest, false, &["--no-auto-compress"]);
    let frames = frames(&log);
    assert!(!frames.iter().any(|f| f.kind == 37));
    assert!(frames.iter().filter(|f| f.kind == 4).all(|f| f.flag == 0));
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_server_takes_an_automatically_compressed_push() {
    // Without -z a pushing xs-rs still compresses while the link is slower than compression
    // (from the start, here); C++ decodes any flagged frame once zstd is negotiated.
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("auto");
    let source = root.join("source");
    make_source(&source);
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let log = root.join("auto.log");
    captured(Path::new(xs_rs()), &cpp, &log, &source, &dest, false, &[]);
    let frames = frames(&log);
    assert!(!frames.iter().any(|f| f.kind == 37), "no -z, no policy frame");
    assert!(frames.iter().any(|f| f.kind == 4 && f.flag == 1), "compressible data is packed");
    assert_eq!(fs::read(dest.join("archive.gz")).unwrap(), fs::read(source.join("archive.gz")).unwrap());
    let _ = fs::remove_dir_all(root);
}
