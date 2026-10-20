//! PF_RESUME against the parent's C++ xs: a destination prefix is reused only
//! when its hash still matches, and the transfer carries just the suffix.
//! Tests that need the C++ binary skip when XS_BIN is unset.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

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
        format!("xs-rs-resume-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn pattern(len: usize) -> Vec<u8> {
    (0..len).map(|index| (index.wrapping_mul(131) & 0xff) as u8).collect()
}

fn make_case(root: &Path) -> (PathBuf, PathBuf, Vec<u8>) {
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    let bytes = pattern(4 * MIB);
    fs::write(source.join("large.bin"), &bytes).unwrap();
    fs::write(dest.join("large.bin"), &bytes[..3 * MIB]).unwrap();
    (source, dest, bytes)
}

fn transfer(program: &Path, remote: &Path, log: &Path, source: &Path, dest: &Path, pull: bool) {
    let recorder = repo("rs/xs-rs/tests/frame_recorder.py");
    let helper = format!("python3 {} {} {}", recorder.display(), log.display(), remote.display());
    let mut command = Command::new(program);
    command
        .arg("-a")
        .arg("--partial")
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

/// Bytes inside DATA frames that the sender put on the wire, excluding the
/// payloads the receiver sent back.
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

fn check(root: &Path, log: &Path, direction: &str, dest: &Path, bytes: &[u8]) {
    assert_eq!(fs::read(dest.join("large.bin")).unwrap(), bytes);
    let sent = sent_data_bytes(log, direction);
    assert!(sent > 0, "the suffix was sent");
    assert!(sent < (bytes.len() / 2) as u64, "only the suffix after the verified prefix is sent: {sent} of {}", bytes.len());
    assert_eq!(fs::read_dir(dest).unwrap().filter_map(Result::ok).filter(|e| e.file_name().to_string_lossy().starts_with(".large.")).count(), 0);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_client_resumes_a_prefix_on_the_rust_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-push");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(&cpp, Path::new(xs_rs()), &log, &source, &dest, false);
    check(&root, &log, "client", &dest, &bytes);
}

#[test]
fn a_rust_client_resumes_a_prefix_on_the_cpp_server() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(Path::new(xs_rs()), &cpp, &log, &source, &dest, false);
    check(&root, &log, "client", &dest, &bytes);
}

#[test]
fn a_cpp_client_pull_resumes_a_prefix_from_the_rust_sender() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-pull");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(&cpp, Path::new(xs_rs()), &log, &source, &dest, true);
    check(&root, &log, "server", &dest, &bytes);
}

#[test]
fn a_rust_client_pull_resumes_a_prefix_from_the_cpp_sender() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let (source, dest, bytes) = make_case(&root);
    let log = root.join("frames.log");
    transfer(Path::new(xs_rs()), &cpp, &log, &source, &dest, true);
    check(&root, &log, "server", &dest, &bytes);
}
