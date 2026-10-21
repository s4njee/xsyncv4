//! POSIX ACLs against the parent's C++ xs. Run with
//! `XS_BIN=.../parent/build/xs cargo test --manifest-path rs/Cargo.toml`; every
//! test returns early when XS_BIN is unset or the filesystem has no ACLs.
// Linux only: user.* xattr names and POSIX ACLs kept in xattrs; macOS has neither.
#![cfg(target_os = "linux")]

use std::collections::BTreeMap;
use std::ffi::CString;
use std::fs;
use std::os::raw::{c_char, c_void};
use std::os::unix::ffi::OsStrExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

extern "C" {
    fn lgetxattr(path: *const c_char, name: *const c_char, value: *mut c_void, size: usize) -> isize;
    fn lsetxattr(path: *const c_char, name: *const c_char, value: *const c_void, size: usize, flags: i32) -> i32;
}

const ACCESS: &[u8] = b"system.posix_acl_access";
const DEFAULT: &[u8] = b"system.posix_acl_default";
const UNDEFINED: u32 = u32::MAX;

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
        "xs-rs-acl-{tag}-{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
    );
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn value(entries: &[(u16, u16, u32)]) -> Vec<u8> {
    let mut data = vec![2, 0, 0, 0];
    for &(tag, permissions, id) in entries {
        data.extend_from_slice(&tag.to_le_bytes());
        data.extend_from_slice(&permissions.to_le_bytes());
        data.extend_from_slice(&id.to_le_bytes());
    }
    data
}

fn set_acl(path: &Path, name: &[u8], data: &[u8]) -> std::io::Result<()> {
    let path = CString::new(path.as_os_str().as_bytes()).unwrap();
    let name = CString::new(name).unwrap();
    let rc = unsafe { lsetxattr(path.as_ptr(), name.as_ptr(), data.as_ptr().cast(), data.len(), 0) };
    if rc == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

fn get_acl(path: &Path, name: &[u8]) -> Option<Vec<u8>> {
    let path = CString::new(path.as_os_str().as_bytes()).ok()?;
    let name = CString::new(name).ok()?;
    let size = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), std::ptr::null_mut(), 0) };
    if size < 0 {
        return None;
    }
    let mut data = vec![0u8; size as usize];
    let size = unsafe { lgetxattr(path.as_ptr(), name.as_ptr(), data.as_mut_ptr().cast(), data.len()) };
    if size < 0 {
        return None;
    }
    data.truncate(size as usize);
    Some(data)
}

type Snapshot = BTreeMap<Vec<u8>, BTreeMap<Vec<u8>, Vec<u8>>>;

fn snapshot(root: &Path) -> Snapshot {
    fn walk(root: &Path, dir: &Path, out: &mut Snapshot) {
        let mut values = BTreeMap::new();
        for name in [ACCESS, DEFAULT] {
            if let Some(value) = get_acl(dir, name) {
                values.insert(name.to_vec(), value);
            }
        }
        out.insert(dir.strip_prefix(root).unwrap().as_os_str().as_bytes().to_vec(), values);
        let mut entries: Vec<_> = fs::read_dir(dir).unwrap().map(|entry| entry.unwrap()).collect();
        entries.sort_by_key(|entry| entry.file_name());
        for entry in entries {
            let path = entry.path();
            if fs::symlink_metadata(&path).unwrap().is_dir() {
                walk(root, &path, out);
            } else {
                let mut values = BTreeMap::new();
                for name in [ACCESS, DEFAULT] {
                    if let Some(value) = get_acl(&path, name) {
                        values.insert(name.to_vec(), value);
                    }
                }
                out.insert(path.strip_prefix(root).unwrap().as_os_str().as_bytes().to_vec(), values);
            }
        }
    }
    let mut result = BTreeMap::new();
    walk(root, root, &mut result);
    result
}

fn make_tree(root: &Path) -> std::io::Result<()> {
    fs::create_dir_all(root.join("sub/deep"))?;
    fs::write(root.join("plain.txt"), b"plain\n")?;
    fs::write(root.join("named.txt"), b"named\n")?;
    fs::write(root.join("sub/deep/data.bin"), vec![3u8; 4000])?;
    let access = value(&[(1, 7, UNDEFINED), (2, 4, 60000), (4, 5, UNDEFINED), (16, 5, UNDEFINED), (32, 5, UNDEFINED)]);
    let other = value(&[(1, 6, UNDEFINED), (2, 2, 60001), (4, 4, UNDEFINED), (16, 4, UNDEFINED), (32, 4, UNDEFINED)]);
    let default = value(&[(1, 7, UNDEFINED), (4, 5, UNDEFINED), (16, 5, UNDEFINED), (32, 5, UNDEFINED)]);
    set_acl(&root.join("named.txt"), ACCESS, &access)?;
    set_acl(&root.join("sub/deep/data.bin"), ACCESS, &other)?;
    set_acl(&root.join("sub"), ACCESS, &access)?;
    set_acl(&root.join("sub"), DEFAULT, &default)?;
    set_acl(&root.join("sub/deep"), DEFAULT, &default)?;
    Ok(())
}

fn run(mut command: Command) {
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

fn command(program: &Path, remote: &Path, source: &Path, dest: &Path, pull: bool) -> Command {
    let mut command = Command::new(program);
    command
        .arg("-aA")
        .arg("-e")
        .arg(fakessh())
        .arg(format!("--rsync-path={}", remote.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

#[test]
fn posix_acls_cross_both_implementations_in_both_directions() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("cross");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    if make_tree(&source).is_err() {
        let _ = fs::remove_dir_all(root);
        return;
    }
    let expected = snapshot(&source);
    for (pair, (program, remote)) in
        [(xs_rs(), cpp.as_path()), (cpp.to_str().unwrap(), Path::new(xs_rs()))].into_iter().enumerate()
    {
        for pull in [false, true] {
            let dest = root.join(format!("dest-{pair}-{pull}"));
            fs::create_dir_all(&dest).unwrap();
            run(command(Path::new(program), remote, &source, &dest, pull));
            assert_eq!(snapshot(&dest), expected, "pair {pair} pull {pull}");
            run(command(Path::new(program), remote, &source, &dest, pull));
            assert_eq!(snapshot(&dest), expected, "second pass pair {pair} pull {pull}");
        }
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_changed_named_acl_is_carried_on_the_next_pass() {
    let Some(cpp) = xs_bin() else { return };
    let root = temp_root("update");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    if make_tree(&source).is_err() {
        let _ = fs::remove_dir_all(root);
        return;
    }
    let dest = root.join("dest");
    fs::create_dir_all(&dest).unwrap();
    run(command(&cpp, Path::new(xs_rs()), &source, &dest, false));
    let changed =
        value(&[(1, 7, UNDEFINED), (2, 1, 60000), (4, 5, UNDEFINED), (16, 5, UNDEFINED), (32, 5, UNDEFINED)]);
    set_acl(&source.join("named.txt"), ACCESS, &changed).unwrap();
    let default = value(&[(1, 7, UNDEFINED), (2, 3, 60001), (4, 5, UNDEFINED), (16, 5, UNDEFINED), (32, 5, UNDEFINED)]);
    set_acl(&source.join("sub"), ACCESS, &default).unwrap();
    set_acl(&source.join("sub"), DEFAULT, &default).unwrap();
    run(command(&cpp, Path::new(xs_rs()), &source, &dest, false));
    assert_eq!(snapshot(&dest), snapshot(&source));
    let _ = fs::remove_dir_all(root);
}
