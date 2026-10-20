//! `PF_HLINK` against the parent's C++ xs. Tests that need the C++ binary
//! return early when XS_BIN is unset, as the other interop tests do.

use std::collections::BTreeMap;
use std::fs;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

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
        format!("xs-rs-hlink-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn set_mtime(path: &Path, secs: u64, nanos: u32) {
    let file = fs::OpenOptions::new().read(true).write(true).open(path).or_else(|_| fs::File::open(path)).unwrap();
    let time = UNIX_EPOCH + Duration::new(secs, nanos);
    file.set_times(fs::FileTimes::new().set_modified(time).set_accessed(time)).unwrap();
}

fn make_hardlink_tree(root: &Path) {
    fs::create_dir_all(root.join("sub")).unwrap();
    fs::write(root.join("a"), b"0123456789abcdef".repeat(140_000)).unwrap();
    for name in ["m", "z", "sub/q"] {
        fs::hard_link(root.join("a"), root.join(name)).unwrap();
    }
    std::os::unix::fs::symlink("a", root.join("sym")).unwrap();
    fs::hard_link(root.join("sym"), root.join("sym2")).unwrap();
    let fifo = root.join("pipe");
    let status = Command::new("mkfifo").arg(&fifo).status().unwrap();
    assert!(status.success());
    fs::hard_link(&fifo, root.join("pipe2")).unwrap();
    for path in root_walk(root) {
        set_mtime(&path, 1_000_000_000, 0);
    }
    fs::set_permissions(root.join("a"), fs::Permissions::from_mode(0o640)).unwrap();
}

fn root_walk(root: &Path) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in fs::read_dir(dir).unwrap().flatten() {
            let path = entry.path();
            if fs::symlink_metadata(&path).unwrap().is_dir() {
                stack.push(path.clone());
            }
            paths.push(path);
        }
    }
    paths.sort();
    paths
}

/// `rel -> sorted names sharing its inode`, discarding the inode number itself.
fn groups(root: &Path) -> BTreeMap<Vec<u8>, Vec<Vec<u8>>> {
    let mut inodes: BTreeMap<(u64, u64), Vec<Vec<u8>>> = BTreeMap::new();
    let mut names = Vec::new();
    for path in root_walk(root) {
        let metadata = fs::symlink_metadata(&path).unwrap();
        if metadata.is_dir() {
            continue;
        }
        let rel = path.strip_prefix(root).unwrap().as_os_str().as_bytes().to_vec();
        inodes.entry((metadata.dev(), metadata.ino())).or_default().push(rel.clone());
        names.push(rel);
    }
    names
        .into_iter()
        .map(|rel| {
            let group = inodes
                .iter()
                .find_map(|(_, shared)| shared.contains(&rel).then(|| shared.clone()))
                .unwrap();
            (rel, if group.len() > 1 { group } else { Vec::new() })
        })
        .collect()
}

fn assert_same_hardlinks(source: &Path, dest: &Path) {
    assert_eq!(groups(source), groups(dest));
}

fn transfer(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool, extra: &[&str]) -> Output {
    let mut command = Command::new(program);
    command.arg("-aH").args(extra).arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command.output().expect("start the transfer")
}

fn run(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool, extra: &[&str]) -> String {
    let output = transfer(program, remote, source, dest, pull, extra);
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    String::from_utf8_lossy(&output.stdout).into_owned()
}

#[test]
fn a_cpp_client_push_preserves_the_cpp_hard_link_fields() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cpp-push");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    make_hardlink_tree(&source);
    let stats = run(&cpp, Path::new(xs_rs()), &source, &dest, false, &["--stats"]);
    assert!(stats.contains("Number of regular files transferred: 1\n"), "{stats}");
    assert_same_hardlinks(&source, &dest);

    // A second run changes nothing.
    run(&cpp, Path::new(xs_rs()), &source, &dest, false, &[]);
    assert_same_hardlinks(&source, &dest);

    // A new name of an inode already at the destination is linked, not sent.
    fs::hard_link(source.join("a"), source.join("new")).unwrap();
    let stats = run(&cpp, Path::new(xs_rs()), &source, &dest, false, &["--stats"]);
    assert!(stats.contains("Number of regular files transferred: 0\n"), "{stats}");
    assert!(stats.contains("Number of created files: 1 (reg: 1, dir: 0)\n"), "{stats}");
    assert_same_hardlinks(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_push_links_the_names_on_the_cpp_receiver() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-push");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    make_hardlink_tree(&source);
    run(Path::new(xs_rs()), &cpp, &source, &dest, false, &[]);
    assert_same_hardlinks(&source, &dest);
    fs::hard_link(source.join("a"), source.join("new")).unwrap();
    run(Path::new(xs_rs()), &cpp, &source, &dest, false, &[]);
    assert_same_hardlinks(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_pull_links_the_names_from_the_cpp_sender() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("rs-pull");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    make_hardlink_tree(&source);
    run(Path::new(xs_rs()), &cpp, &source, &dest, true, &[]);
    assert_same_hardlinks(&source, &dest);
    fs::hard_link(source.join("a"), source.join("new")).unwrap();
    run(Path::new(xs_rs()), &cpp, &source, &dest, true, &[]);
    assert_same_hardlinks(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_local_rust_copy_preserves_links_across_directories() {
    let root = temp_root("local");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    make_hardlink_tree(&source);
    let output = Command::new(xs_rs())
        .args(["-aH", "-i"])
        .arg(format!("{}/", source.display()))
        .arg(format!("{}/", dest.display()))
        .output()
        .unwrap();
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("hf+++++++++ m => a") || stdout.contains("hf+++++++++ m => sub/q"), "{stdout}");
    assert_same_hardlinks(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn only_negotiated_peers_receive_hlink_fields() {
    let Some(cpp) = xs_bin() else { return };
    // A C++ client without -H still interoperates, and the receiver must not
    // invent hard links from inode numbers that were never sent.
    let root = temp_root("unnegotiated");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    make_hardlink_tree(&source);
    let output = Command::new(&cpp)
        .args(["-a", "-e"])
        .arg(fakessh())
        .arg(format!("--rsync-path={}", xs_rs()))
        .arg(format!("{}/", source.display()))
        .arg(format!("fake:{}/", dest.display()))
        .output()
        .unwrap();
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
    assert_eq!(fs::read(dest.join("m")).unwrap(), fs::read(source.join("a")).unwrap());
    let m = fs::metadata(dest.join("m")).unwrap();
    let a = fs::metadata(dest.join("a")).unwrap();
    assert_ne!((m.dev(), m.ino()), (a.dev(), a.ino()), "unnegotiated hard links must stay separate files");
    let _ = fs::remove_dir_all(root);
}
