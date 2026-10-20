//! PF_DELTA against the parent's C++ xs and against a deliberately hostile peer.
//! Interop tests skip when XS_BIN is unset; the raw tests drive the Rust server.

use std::fs;
use std::io::Write;
use std::os::raw::c_void;
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use xs_wire::{frame_type, msg_kind, read_frame, write_frame, Decoder, Encoder, Frame, Message};

const MIB: usize = 1024 * 1024;

fn xs_bin() -> Option<PathBuf> {
    std::env::var_os("XS_BIN").map(PathBuf::from)
}

fn xs_rs() -> &'static str {
    env!("CARGO_BIN_EXE_xs-rs")
}

fn repo(path: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..").join(path)
}

fn temp_root(tag: &str) -> PathBuf {
    let mut path = std::env::temp_dir();
    let unique =
        format!("xs-rs-delta-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn pattern(len: usize) -> Vec<u8> {
    (0..len).map(|index| (index.wrapping_mul(131) & 0xff) as u8).collect()
}

fn set_mtime(path: &Path, secs: u64) {
    let file = fs::OpenOptions::new().read(true).write(true).open(path).unwrap();
    let time = UNIX_EPOCH + Duration::new(secs, 0);
    file.set_times(fs::FileTimes::new().set_modified(time).set_accessed(time)).unwrap();
}

fn make_case(root: &Path) -> (PathBuf, PathBuf, Vec<u8>) {
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(4 * MIB);
    let mut changed = bytes.clone();
    changed[1_500_000..1_600_000].fill(0xaa);
    fs::write(source.join("large.bin"), &bytes).unwrap();
    fs::write(dest.join("large.bin"), &changed).unwrap();
    set_mtime(&source.join("large.bin"), 1_600_000_000);
    set_mtime(&dest.join("large.bin"), 1_500_000_000);
    (source, dest, bytes)
}

fn transfer(program: &Path, remote: &Path, log: &Path, source: &Path, dest: &Path, pull: bool) {
    let recorder = repo("rs/xs-rs/tests/frame_recorder.py");
    let helper = format!("python3 {} {} {}", recorder.display(), log.display(), remote.display());
    let mut command = Command::new(program);
    command
        .arg("-a")
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

fn sent_data_bytes(log: &Path, direction: &str) -> u64 {
    fs::read_to_string(log)
        .unwrap()
        .lines()
        .filter_map(|line| {
            let fields: Vec<_> = line.split_whitespace().collect();
            (fields.len() == 4 && fields[0] == direction && fields[1] == "4")
                .then(|| fields[2].parse::<u64>().unwrap())
        })
        .sum()
}

fn check(root: &Path, log: &Path, direction: &str, source: &Path, dest: &Path, bytes: &[u8]) {
    assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
    let sent = sent_data_bytes(log, direction);
    assert!(sent > 0, "the delta was sent");
    assert!(sent < (bytes.len() / 2) as u64, "delta DATA stays below half the file: {sent} of {} (source {})", bytes.len(), source.display());
    assert_eq!(
        fs::read_dir(dest)
            .unwrap()
            .filter_map(Result::ok)
            .filter(|entry| entry.file_name().to_string_lossy().starts_with(".large."))
            .count(),
        0
    );
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_client_pushes_a_delta_to_the_rust_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-push");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(&cpp, Path::new(xs_rs()), &log, &source, &dest, false);
    check(&root, &log, "client", &source, &dest, &bytes);
}

#[test]
fn a_rust_client_pushes_a_delta_to_the_cpp_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(Path::new(xs_rs()), &cpp, &log, &source, &dest, false);
    check(&root, &log, "client", &source, &dest, &bytes);
}

#[test]
fn a_cpp_client_pulls_a_delta_from_the_rust_sender() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-pull");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(&cpp, Path::new(xs_rs()), &log, &source, &dest, true);
    check(&root, &log, "server", &source, &dest, &bytes);
}

#[test]
fn a_rust_client_pulls_a_delta_from_the_cpp_sender() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(Path::new(xs_rs()), &cpp, &log, &source, &dest, true);
    check(&root, &log, "server", &source, &dest, &bytes);
}

#[repr(C)]
struct Xxh128 {
    low64: u64,
    high64: u64,
}

extern "C" {
    fn XXH3_64bits(input: *const c_void, length: usize) -> u64;
    fn XXH3_128bits(input: *const c_void, length: usize) -> Xxh128;
}

fn xxh3(bytes: &[u8]) -> u64 {
    unsafe { XXH3_64bits(bytes.as_ptr().cast(), bytes.len()) }
}

fn xxh3_128(bytes: &[u8]) -> [u64; 2] {
    let hash = unsafe { XXH3_128bits(bytes.as_ptr().cast(), bytes.len()) };
    [hash.low64, hash.high64]
}

fn weak(bytes: &[u8]) -> u32 {
    let (mut a, mut b) = (0u32, 0u32);
    for &byte in bytes {
        a = a.wrapping_add(u32::from(byte));
        b = b.wrapping_add(a);
    }
    (a & 65535) | (b << 16)
}

/* ---------------------------------------------------------------- raw peer */

struct Peer {
    child: Child,
    input: ChildStdin,
    output: ChildStdout,
    dest: PathBuf,
}

impl Peer {
    fn start(dest: &Path, features: u64) -> Self {
        let mut child = Command::new(xs_rs())
            .arg("--server")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .unwrap();
        let input = child.stdin.take().unwrap();
        let output = child.stdout.take().unwrap();
        let mut peer = Self { child, input, output, dest: dest.to_path_buf() };
        let mut hello = Encoder::new();
        hello.raw(b"XSYNC\x01").var(4).byte(b'R').var(features);
        let mut flags = [false; 32];
        flags[0] = true;
        flags[4] = true;
        flags[18] = true;
        for flag in flags {
            hello.byte(u8::from(flag));
        }
        for _ in 0..7 {
            hello.svar(0);
        }
        hello.var(0).var(1).str(dest.as_os_str().as_encoded_bytes());
        peer.send(frame_type::HELLO, &hello.bytes);
        loop {
            let frame = peer.read();
            if frame.kind == frame_type::DEST {
                break;
            }
            assert_eq!(frame.kind, frame_type::HELLO);
        }
        peer
    }

    fn read(&mut self) -> Frame {
        read_frame(&mut self.output).unwrap().expect("a frame from the receiver")
    }

    fn send(&mut self, kind: u8, payload: &[u8]) {
        write_frame(&mut self.input, kind, payload).unwrap();
        self.input.flush().unwrap();
    }

    fn send_dir(&mut self, size: u64, mtime: i64) {
        let mut body = Encoder::new();
        body.str(b"").var(0o755).svar(0).var(0).var(0).var(0);
        body.var(1);
        body.str(b"large.bin").byte(1).var(0o644).svar(mtime).var(0).var(size);
        let mut dir = Encoder::new();
        dir.var(0).var(0).var(0).byte(1).raw(&body.bytes);
        self.send(frame_type::DIR, &dir.bytes);
    }

    fn need(&mut self) -> Frame {
        loop {
            let frame = self.read();
            if frame.kind == frame_type::NEED {
                return frame;
            }
        }
    }

    fn request(&mut self, id: u32, idx: u32) {
        let mut request = Encoder::new();
        request.var(u64::from(id)).var(u64::from(idx));
        self.send(frame_type::DELTA_REQUEST, &request.bytes);
    }

    fn signature(&mut self) -> Frame {
        loop {
            let frame = self.read();
            if frame.kind == frame_type::DELTA_SIGNATURE {
                return frame;
            }
        }
    }

    fn data(&mut self, records: &[u8]) {
        let mut payload = Encoder::new();
        payload.byte(0).raw(&xxh3(records).to_le_bytes()).raw(records);
        self.send(frame_type::DATA, &payload.bytes);
    }

    fn finish(&mut self) -> i32 {
        self.send(frame_type::LIST_END, &[]);
        let mut end = Encoder::new();
        end.var(0);
        self.send(frame_type::DATA_END, &end.bytes);
        loop {
            let frame = self.read();
            if frame.kind == frame_type::DONE {
                let mut d = Decoder::new(&frame.payload);
                let code = d.var().unwrap() as i32;
                let _ = self.child.kill();
                let _ = self.child.wait();
                return code;
            }
        }
    }

    fn reject(mut self) {
        let frame = self.read();
        assert_eq!(frame.kind, frame_type::MSG, "a fatal message");
        let message = Message::decode(&frame.payload).unwrap();
        assert_eq!(message.kind, msg_kind::FATAL);
        assert!(message.text.contains("protocol error"), "{}", message.text);
        drop(self.input);
        let status = self.child.wait().unwrap();
        assert_eq!(status.code(), Some(2));
        assert_eq!(fs::read(self.dest.join("large.bin")).unwrap(), basis_of(&self.dest));
    }
}

fn basis_of(dest: &Path) -> Vec<u8> {
    fs::read(dest.join("large.bin")).unwrap()
}

#[allow(clippy::too_many_arguments)]
fn copy_record(id: u32, idx: u32, attempt: u32, offset: i64, total: i64, first: u32, count: u32, tag: &mut Vec<u8>) {
    let mut e = Encoder::new();
    e.var(u64::from(id)).var(u64::from(idx)).byte(xs_wire::consts::record::COPY);
    e.var(u64::from(attempt)).var(offset.max(0) as u64).var(total.max(0) as u64);
    e.var(u64::from(first)).var(u64::from(count));
    tag.extend_from_slice(&e.bytes);
}

fn literal_record(id: u32, idx: u32, attempt: u32, offset: i64, total: i64, bytes: &[u8], tag: &mut Vec<u8>) {
    let mut e = Encoder::new();
    e.var(u64::from(id)).var(u64::from(idx)).byte(xs_wire::consts::record::LITERAL);
    e.var(u64::from(attempt)).var(offset.max(0) as u64).var(total.max(0) as u64);
    e.str(bytes);
    tag.extend_from_slice(&e.bytes);
}

fn end_record(id: u32, idx: u32, attempt: u32, total: i64, status: u8, sum: [u64; 2], tag: &mut Vec<u8>) {
    let mut e = Encoder::new();
    e.var(u64::from(id)).var(u64::from(idx)).byte(xs_wire::consts::record::DELTA_END);
    e.var(u64::from(attempt)).var(total.max(0) as u64).byte(status);
    e.var(0o644).var(0).var(0).svar(0).var(0);
    e.raw(&sum[0].to_le_bytes()).raw(&sum[1].to_le_bytes());
    tag.extend_from_slice(&e.bytes);
}

fn signature_body(frame: &Frame) -> (u64, u64, Vec<u8>) {
    let mut d = Decoder::new(&frame.payload);
    let id = d.var().unwrap();
    let idx = d.var().unwrap();
    let compressed = d.byte().unwrap();
    assert_eq!(compressed, 0, "the reply is uncompressed without -z");
    (id, idx, d.rest().to_vec())
}

#[test]
fn the_rust_receiver_asks_for_the_cpp_signature_and_reconstructs_it() {
    let root = temp_root("signature");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(2 * MIB);
    fs::write(dest.join("large.bin"), &bytes).unwrap();
    set_mtime(&dest.join("large.bin"), 1_500_000_000);

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    let need = peer.need();
    assert_eq!(need.payload, [0, 1, 0, 1], "one index and an eligible delta candidate");

    peer.request(0, 0);
    let frame = peer.signature();
    let (id, idx, body) = signature_body(&frame);
    assert_eq!((id, idx), (0, 0));
    let mut d = Decoder::new(&body);
    assert_eq!(d.byte().unwrap(), 1, "a signature is present");
    let size = d.var().unwrap();
    let block = d.var().unwrap() as usize;
    let count = d.var().unwrap() as usize;
    assert_eq!(size as usize, bytes.len());
    assert_eq!(block, 2896);
    assert_eq!(count, (bytes.len() - 1) / block + 1);
    let weak_sum = u32::from_le_bytes(d.raw(4).unwrap().try_into().unwrap());
    let strong = u64::from_le_bytes(d.raw(8).unwrap().try_into().unwrap());
    assert_eq!(weak_sum, weak(&bytes[..block]));
    assert_eq!(strong, xxh3(&bytes[..block]));
    assert_eq!(d.rest().len(), 12 * (count - 1));

    let mut records = Vec::new();
    copy_record(0, 0, 0, 0, bytes.len() as i64, 0, count as u32, &mut records);
    end_record(0, 0, 0, bytes.len() as i64, 0, xxh3_128(&bytes), &mut records);
    peer.data(&records);
    assert_eq!(peer.finish(), 0);
    assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn unnegotiated_duplicate_and_unrequested_delta_frames_are_refused() {
    let root = temp_root("hostile");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(2 * MIB);
    fs::write(dest.join("large.bin"), &bytes).unwrap();
    set_mtime(&dest.join("large.bin"), 1_500_000_000);

    let mut peer = Peer::start(&dest, 1);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    let need = peer.need();
    assert_eq!(need.payload, [0, 1, 0], "no delta byte without PF_DELTA");
    peer.request(0, 0);
    peer.reject();

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    peer.need();
    peer.request(0, 0);
    peer.signature();
    peer.request(0, 0);
    peer.reject();

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    peer.need();
    let mut records = Vec::new();
    literal_record(0, 0, 0, 0, bytes.len() as i64, b"x", &mut records);
    peer.data(&records);
    peer.reject();
    let _ = fs::remove_dir_all(root);
}

#[test]
fn bad_references_and_a_bad_digest_never_publish_the_temp_file() {
    let root = temp_root("badref");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(2 * MIB);
    fs::write(dest.join("large.bin"), &bytes).unwrap();
    set_mtime(&dest.join("large.bin"), 1_500_000_000);

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    peer.need();
    peer.request(0, 0);
    let frame = peer.signature();
    let (_, _, body) = signature_body(&frame);
    let mut d = Decoder::new(&body);
    d.byte().unwrap();
    d.var().unwrap();
    d.var().unwrap();
    let count = d.var().unwrap() as u32;
    let mut records = Vec::new();
    copy_record(0, 0, 0, 0, bytes.len() as i64, 0, count + 1, &mut records);
    peer.data(&records);
    peer.reject();

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    peer.need();
    peer.request(0, 0);
    let frame = peer.signature();
    let (_, _, body) = signature_body(&frame);
    let mut d = Decoder::new(&body);
    d.byte().unwrap();
    d.var().unwrap();
    d.var().unwrap();
    let count = d.var().unwrap() as u32;
    let mut records = Vec::new();
    copy_record(0, 0, 0, 0, bytes.len() as i64, 0, count, &mut records);
    end_record(0, 0, 0, bytes.len() as i64, 0, [0, 0], &mut records);
    peer.data(&records);
    assert_eq!(peer.finish(), 23);
    assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
    assert_eq!(fs::read_dir(&dest).unwrap().filter_map(Result::ok).count(), 1, "only the basis remains");
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_changed_basis_fails_and_a_replaced_path_stays_anchored() {
    let root = temp_root("basis");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(2 * MIB);
    let outside = root.join("outside");
    fs::write(&outside, b"outside sentinel").unwrap();

    for replace in [false, true] {
        fs::write(dest.join("large.bin"), &bytes).unwrap();
        set_mtime(&dest.join("large.bin"), 1_500_000_000);
        let mut peer = Peer::start(&dest, 1 | 256);
        peer.send_dir(bytes.len() as u64, 1_600_000_000);
        peer.need();
        peer.request(0, 0);
        let frame = peer.signature();
        let (_, _, body) = signature_body(&frame);
        let mut d = Decoder::new(&body);
        d.byte().unwrap();
        d.var().unwrap();
        d.var().unwrap();
        let count = d.var().unwrap() as u32;
        if replace {
            fs::remove_file(dest.join("large.bin")).unwrap();
            std::os::unix::fs::symlink(&outside, dest.join("large.bin")).unwrap();
        } else {
            let mut file = fs::OpenOptions::new().write(true).open(dest.join("large.bin")).unwrap();
            file.write_all(b"changed basis").unwrap();
        }
        let mut records = Vec::new();
        copy_record(0, 0, 0, 0, bytes.len() as i64, 0, count, &mut records);
        end_record(0, 0, 0, bytes.len() as i64, 0, xxh3_128(&bytes), &mut records);
        peer.data(&records);
        assert_eq!(peer.finish(), if replace { 0 } else { 23 });
        if replace {
            assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
        }
        assert_eq!(fs::read(&outside).unwrap(), b"outside sentinel");
        assert_eq!(
            fs::read_dir(&dest)
                .unwrap()
                .filter_map(Result::ok)
                .filter(|entry| entry.file_name().to_string_lossy().starts_with(".large."))
                .count(),
            0
        );
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_delta_retry_waits_for_its_ack_and_then_publishes() {
    let root = temp_root("retry");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(2 * MIB);
    fs::write(dest.join("large.bin"), &bytes).unwrap();
    set_mtime(&dest.join("large.bin"), 1_500_000_000);

    let mut peer = Peer::start(&dest, 1 | 256);
    peer.send_dir(bytes.len() as u64, 1_600_000_000);
    peer.need();
    peer.request(0, 0);
    let frame = peer.signature();
    let (_, _, body) = signature_body(&frame);
    let mut d = Decoder::new(&body);
    d.byte().unwrap();
    d.var().unwrap();
    d.var().unwrap();
    let count = d.var().unwrap() as u32;

    let mut first = Vec::new();
    copy_record(0, 0, 0, 0, bytes.len() as i64, 0, count, &mut first);
    end_record(0, 0, 0, bytes.len() as i64, 1, [0, 0], &mut first);
    peer.data(&first);
    loop {
        let frame = peer.read();
        if frame.kind == frame_type::DELTA_RETRY_ACK {
            let mut ack = Decoder::new(&frame.payload);
            assert_eq!((ack.var().unwrap(), ack.var().unwrap()), (0, 0));
            break;
        }
    }

    let mut second = Vec::new();
    copy_record(0, 0, 1, 0, bytes.len() as i64, 0, count, &mut second);
    end_record(0, 0, 1, bytes.len() as i64, 0, xxh3_128(&bytes), &mut second);
    peer.data(&second);
    assert_eq!(peer.finish(), 0);
    assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
    let _ = fs::remove_dir_all(root);
}
