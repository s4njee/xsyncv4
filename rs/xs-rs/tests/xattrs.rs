//! Extended attributes against the parent's C++ xs. Run with
//! `XS_BIN=.../parent/build/xs cargo test --manifest-path rs/Cargo.toml`; every
//! test returns early when XS_BIN is unset.
// Linux only: user.* xattr names and POSIX ACLs kept in xattrs; macOS has neither.
#![cfg(target_os = "linux")]

use std::collections::BTreeMap;
use std::ffi::CString;
use std::fs;
use std::os::raw::{c_char, c_int, c_void};
use std::os::unix::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

extern "C" {
    fn llistxattr(path: *const c_char, list: *mut c_char, size: usize) -> isize;
    fn lgetxattr(path: *const c_char, name: *const c_char, value: *mut c_void, size: usize) -> isize;
    fn lsetxattr(path: *const c_char, name: *const c_char, value: *const c_void, size: usize, flags: c_int) -> c_int;
}

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
    let unique = format!("xs-rs-xattr-{tag}-{}-{}", std::process::id(), SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn set_attr(path: &Path, name: &[u8], value: &[u8]) {
    let path = CString::new(path.as_os_str().as_bytes()).unwrap();
    let name = CString::new(name).unwrap();
    let code = unsafe { lsetxattr(path.as_ptr(), name.as_ptr(), value.as_ptr().cast(), value.len(), 0) };
    assert_eq!(code, 0, "lsetxattr failed for {}", name.to_string_lossy());
}

fn attrs(path: &Path) -> BTreeMap<Vec<u8>, Vec<u8>> {
    let path = CString::new(path.as_os_str().as_bytes()).unwrap();
    let mut result = BTreeMap::new();
    let count = unsafe { llistxattr(path.as_ptr(), std::ptr::null_mut(), 0) };
    if count <= 0 {
        return result;
    }
    let mut names = vec![0u8; count as usize];
    let count = unsafe { llistxattr(path.as_ptr(), names.as_mut_ptr().cast(), names.len()) };
    assert!(count >= 0, "llistxattr failed");
    names.truncate(count as usize);
    for name in names.split(|&byte| byte == 0).filter(|name| !name.is_empty()) {
        let cname = CString::new(name).unwrap();
        let size = unsafe { lgetxattr(path.as_ptr(), cname.as_ptr(), std::ptr::null_mut(), 0) };
        assert!(size >= 0, "lgetxattr failed");
        let mut value = vec![0u8; size as usize];
        let size = unsafe { lgetxattr(path.as_ptr(), cname.as_ptr(), value.as_mut_ptr().cast(), value.len()) };
        assert!(size >= 0, "lgetxattr failed");
        value.truncate(size as usize);
        result.insert(name.to_vec(), value);
    }
    result
}

fn snapshot(root: &Path) -> BTreeMap<Vec<u8>, BTreeMap<Vec<u8>, Vec<u8>>> {
    fn walk(root: &Path, dir: &Path, out: &mut BTreeMap<Vec<u8>, BTreeMap<Vec<u8>, Vec<u8>>>) {
        out.insert(dir.strip_prefix(root).unwrap().as_os_str().as_bytes().to_vec(), attrs(dir));
        let mut entries: Vec<_> = fs::read_dir(dir).unwrap().map(|entry| entry.unwrap()).collect();
        entries.sort_by_key(|entry| entry.file_name());
        for entry in entries {
            let path = entry.path();
            if fs::symlink_metadata(&path).unwrap().is_dir() {
                walk(root, &path, out);
            } else {
                out.insert(path.strip_prefix(root).unwrap().as_os_str().as_bytes().to_vec(), attrs(&path));
            }
        }
    }
    let mut result = BTreeMap::new();
    walk(root, root, &mut result);
    result
}

fn without_internal(mut snapshot: BTreeMap<Vec<u8>, BTreeMap<Vec<u8>, Vec<u8>>>) -> BTreeMap<Vec<u8>, BTreeMap<Vec<u8>, Vec<u8>>> {
    for values in snapshot.values_mut() {
        values.retain(|name, _| !name.starts_with(b"user.rsync.%"));
    }
    snapshot
}

fn make_tree(root: &Path) {
    fs::create_dir_all(root.join("sub/deep")).unwrap();
    fs::write(root.join("small.txt"), b"small\n").unwrap();
    fs::write(root.join("sub/deep/large.bin"), vec![7u8; 200_000]).unwrap();
    fs::write(root.join("sub/other.txt"), b"other\n").unwrap();
    for path in [root.to_path_buf(), root.join("sub"), root.join("sub/deep")] {
        set_attr(&path, b"user.dir", b"directory");
    }
    set_attr(&root.join("small.txt"), b"user.foo", b"bar");
    set_attr(&root.join("small.txt"), b"user.empty", b"");
    set_attr(&root.join("small.txt"), b"user.binary", b"\0\xff\r\n\x01");
    set_attr(&root.join("small.txt"), b"user.keep", b"keep me");
    set_attr(&root.join("small.txt"), b"user.large", &vec![b'L'; 300]);
    set_attr(&root.join("small.txt"), b"user.rsync.%test", b"internal");
    set_attr(&root.join("sub/other.txt"), b"user.foo", b"second");
}

fn run(mut command: Command) {
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

fn command(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool, extra: &[&str]) -> Command {
    let mut command = Command::new(program);
    command.arg("-aX").args(extra).arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", remote.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

fn both_ways(cpp: &Path, tag: &str, extra: &[&str]) {
    let root = temp_root(tag);
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    for (pair, (program, remote)) in [(xs_rs(), cpp), (cpp.to_str().unwrap(), Path::new(xs_rs()))].into_iter().enumerate() {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            set_attr(&dest, b"user.stale", b"remove me");
            let expected = without_internal(snapshot(&source));
            run(command(Path::new(program), remote, &source, &dest, pull, extra));
            assert_eq!(snapshot(&dest), expected, "pair {pair} pull {pull}");
            run(command(Path::new(program), remote, &source, &dest, pull, extra));
            assert_eq!(snapshot(&dest), expected, "second pass pair {pair} pull {pull}");
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_cpp_client_carries_xattrs_to_the_rust_server_in_both_directions() {
    let Some(cpp) = xs_bin() else { return };
    both_ways(&cpp, "cpp", &[]);
}

#[test]
fn a_rust_client_carries_xattrs_to_the_cpp_server_in_both_directions() {
    let Some(cpp) = xs_bin() else { return };
    both_ways(&cpp, "rust", &[]);
}

#[test]
fn a_second_xattr_pass_includes_rsync_internal_names_both_ways() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("internal");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    for (pair, (program, remote)) in [(xs_rs(), cpp.as_path()), (cpp.to_str().unwrap(), Path::new(xs_rs()))].into_iter().enumerate() {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            run(command(Path::new(program), remote, &source, &dest, pull, &[]));
            assert!(!snapshot(&dest).get(b"small.txt".as_slice()).unwrap().contains_key(b"user.rsync.%test".as_slice()));
            run(command(Path::new(program), remote, &source, &dest, pull, &["-X"]));
            assert_eq!(snapshot(&dest), snapshot(&source), "pair {pair} pull {pull}");
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn an_xattr_filter_selects_names_on_both_sides() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("filter");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    set_attr(&source, b"user.keep", b"source root keep");
    for (pair, (program, remote)) in [(xs_rs(), cpp.as_path()), (cpp.to_str().unwrap(), Path::new(xs_rs()))].into_iter().enumerate() {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            run(command(Path::new(program), remote, &source, &dest, pull, &["-f-x user.keep"]));
            let mut expected = without_internal(snapshot(&source));
            for values in expected.values_mut() {
                values.remove(b"user.keep".as_slice());
            }
            assert_eq!(snapshot(&dest), expected, "pair {pair} pull {pull}");
        }
    }
    let _ = fs::remove_dir_all(root);
}
