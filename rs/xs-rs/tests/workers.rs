//! `-j/--jobs` crosses the wire and splits one large file the way the C++
//! engine does. Run with `XS_BIN=.../parent/build/xs`; skip when it is unset.

use std::ffi::OsStr;
use std::fs;
use std::os::unix::ffi::OsStrExt;
use std::os::unix::fs::{MetadataExt, PermissionsExt};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

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
    let unique = format!(
        "xs-rs-workers-{tag}-{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
    );
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn make_tree(root: &Path) {
    fs::create_dir_all(root.join("d")).unwrap();
    // Past the 32 MiB threshold, so an explicit -jN takes the range path.
    let block: Vec<u8> = (0u8..=255).cycle().take(256 << 10).collect();
    let mut large = Vec::with_capacity(36 << 20);
    for index in 0..(36 << 20) / block.len() {
        large.extend_from_slice(&block);
        large[0] = index as u8;
    }
    fs::write(root.join("d/large.bin"), &large).unwrap();
    for index in 0..24 {
        fs::write(root.join("d").join(format!("small-{index:02}")), format!("small {index}\n").repeat(index + 1))
            .unwrap();
    }
    fs::set_permissions(root.join("d/large.bin"), fs::Permissions::from_mode(0o640)).unwrap();
}

fn compare(source: &Path, dest: &Path) {
    let mut names = Vec::new();
    collect(source, source, &mut names);
    for (rel, bytes, mode, mtime) in &names {
        let path = dest.join(rel);
        let metadata = fs::symlink_metadata(&path).unwrap();
        assert_eq!(metadata.mode() & 0o7777, *mode, "{} mode", rel.to_string_lossy());
        assert_eq!(metadata.mtime(), *mtime, "{} mtime", rel.to_string_lossy());
        if !metadata.is_dir() {
            assert_eq!(&fs::read(&path).unwrap(), bytes, "{} bytes", rel.to_string_lossy());
        }
    }
}

fn collect(root: &Path, dir: &Path, out: &mut Vec<(PathBuf, Vec<u8>, u32, i64)>) {
    let mut entries: Vec<_> = fs::read_dir(dir).unwrap().map(|entry| entry.unwrap()).collect();
    entries.sort_by(|left, right| left.file_name().as_bytes().cmp(right.file_name().as_bytes()));
    for entry in entries {
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path).unwrap();
        if metadata.is_dir() {
            collect(root, &path, out);
        }
        let rel = path.strip_prefix(root).unwrap().to_path_buf();
        out.push((rel, if metadata.is_file() { fs::read(&path).unwrap() } else { Vec::new() }, metadata.mode() & 0o7777, metadata.mtime()));
    }
}

fn transfer(program: &OsStr, remote: &Path, source: &Path, dest: &Path, jobs: &str, pull: bool) {
    let mut command = Command::new(program);
    command.arg("-a").arg(jobs).arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

#[test]
fn an_explicit_jobs_value_survives_the_hello_in_every_direction() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("dirs");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    let pairs: [(&OsStr, &Path); 2] = [(OsStr::new(xs_rs()), cpp.as_path()), (cpp.as_os_str(), Path::new(xs_rs()))];
    for (pair, (program, remote)) in pairs.into_iter().enumerate() {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            transfer(program, remote, &source, &dest, "-j4", pull);
            compare(&source, &dest);
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn one_worker_and_the_default_both_copy_a_large_file() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("serial");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    for (index, jobs) in ["-j1", "-j0"].into_iter().enumerate() {
        let dest = root.join(format!("dest-{index}"));
        fs::create_dir_all(&dest).unwrap();
        transfer(OsStr::new(xs_rs()), &cpp, &source, &dest, jobs, false);
        compare(&source, &dest);
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_worker_batches_small_one_file_directories_and_still_ends_cleanly() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("batched");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    // Each NEED asks for one small file; the sender carries partial blocks across them.
    let body = vec![b'x'; 2048];
    for index in 0..300 {
        let dir = source.join(format!("d{index:03}"));
        fs::create_dir_all(&dir).unwrap();
        fs::write(dir.join("file"), &body).unwrap();
    }
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    transfer(OsStr::new(xs_rs()), &cpp, &source, &dest, "-j4", false);
    compare(&source, &dest);
    // A second pass asks again for every file, still one NEED per directory.
    for index in 0..300 {
        let path = source.join(format!("d{index:03}")).join("file");
        let mut bytes = fs::read(&path).unwrap();
        bytes.extend_from_slice(b"changed");
        fs::write(&path, bytes).unwrap();
    }
    transfer(OsStr::new(xs_rs()), &cpp, &source, &dest, "-j4", false);
    compare(&source, &dest);
    let _ = fs::remove_dir_all(root);
}

#[test]
fn an_unknown_option_is_refused_before_the_destination_exists() {
    let root = temp_root("refuse");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::write(&source, b"untouched").unwrap();
    for option in ["--bogus", "--backup", "-Z"] {
        let output = Command::new(xs_rs()).arg(option).arg(&source).arg(&dest).output().unwrap();
        assert_eq!(output.status.code(), Some(1), "{option}");
        assert!(!dest.exists(), "{option}");
    }
    let _ = fs::remove_dir_all(root);
}
