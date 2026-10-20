//! Filters, relative paths and files-from against the parent's C++ xs.
//! Skipped when XS_BIN is unset.

use std::fs;
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
        "xs-rs-filter-{tag}-{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
    );
    path.push(unique);
    fs::create_dir_all(&path).unwrap();
    path
}

fn run(mut command: Command) {
    let output = command.output().expect("start the transfer");
    assert!(output.status.success(), "transfer failed: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr));
}

fn make_tree(root: &Path) {
    fs::create_dir_all(root.join("a/b/c")).unwrap();
    fs::create_dir_all(root.join("skip")).unwrap();
    fs::write(root.join("a/b/c/keep.txt"), b"keep\n").unwrap();
    fs::write(root.join("a/b/c/drop.tmp"), b"drop\n").unwrap();
    fs::write(root.join("a/b/other.log"), b"log\n").unwrap();
    fs::write(root.join("skip/x.txt"), b"x\n").unwrap();
}

fn cpp(source: &Path, dest: &Path, pull: bool) -> Command {
    let cpp = xs_bin().unwrap();
    let mut command = Command::new(cpp);
    command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", xs_rs()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

fn rust(cpp_bin: &Path, source: &Path, dest: &Path, pull: bool) -> Command {
    let mut command = Command::new(xs_rs());
    command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", cpp_bin.display()));
    if pull {
        command.arg(format!("fake:{}/", source.display())).arg(format!("{}/", dest.display()));
    } else {
        command.arg(format!("{}/", source.display())).arg(format!("fake:{}/", dest.display()));
    }
    command
}

#[test]
fn a_cpp_client_filter_selects_files_for_the_rust_server() {
    let Some(_) = xs_bin() else { return };
    let root = temp_root("cpp-filter");
    let source = root.join("source");
    fs::create_dir_all(&source).unwrap();
    make_tree(&source);
    for pull in [false, true] {
        let dest = root.join(format!("dest-{pull}"));
        fs::create_dir_all(&dest).unwrap();
        let mut command = cpp(&source, &dest, pull);
        command.args(["--filter=- *.tmp", "--filter=- skip"]);
        run(command);
        assert!(dest.join("a/b/c/keep.txt").exists());
        assert!(!dest.join("a/b/c/drop.tmp").exists());
        assert!(!dest.join("a/b/c/other.log").exists());
        assert!(!dest.join("skip").exists());
    }
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_rust_client_filter_selects_files_for_the_cpp_server() {
    let Some(cpp_bin) = xs_bin() else { return };
    let root = temp_root("rust-filter");
    let source = root.join("source");
    let dest = root.join("dest");
    fs::create_dir_all(&source).unwrap();
    fs::create_dir_all(&dest).unwrap();
    make_tree(&source);
    let mut command = rust(&cpp_bin, &source, &dest, false);
    command.args(["--filter=- *.tmp", "--filter=- skip"]);
    run(command);
    assert!(dest.join("a/b/c/keep.txt").exists());
    assert!(!dest.join("a/b/c/drop.tmp").exists());
    assert!(!dest.join("skip").exists());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn relative_paths_survive_a_cpp_push_and_a_rust_pull() {
    let Some(cpp_bin) = xs_bin() else { return };
    let root = temp_root("relative");
    let source = root.join("source");
    fs::create_dir_all(source.join("dir1/deep")).unwrap();
    fs::write(source.join("dir1/deep/c.o"), b"object\n").unwrap();
    fs::write(source.join("dir1/a.txt"), b"a\n").unwrap();
    let leaf = format!("{}/./dir1/deep/c.o", source.display());
    let dest = root.join("push");
    fs::create_dir_all(&dest).unwrap();
    let mut command = cpp_bin_command(&cpp_bin, &leaf, &dest, false);
    command.arg("-R");
    run(command);
    assert_eq!(fs::read(dest.join("dir1/deep/c.o")).unwrap(), b"object\n");
    assert!(!dest.join("dir1/a.txt").exists());

    let dest = root.join("pull");
    fs::create_dir_all(&dest).unwrap();
    let mut command = Command::new(xs_rs());
    command
        .arg("-aR")
        .arg("-e")
        .arg(fakessh())
        .arg(format!("--rsync-path={}", cpp_bin.display()))
        .arg(format!("fake:{}", leaf))
        .arg(format!("{}/", dest.display()));
    run(command);
    assert_eq!(fs::read(dest.join("dir1/deep/c.o")).unwrap(), b"object\n");
    assert!(!dest.join("dir1/a.txt").exists());

    let dest = root.join("cpp-pull-rust");
    fs::create_dir_all(&dest).unwrap();
    let mut command = cpp_bin_command(&cpp_bin, &leaf, &dest, true);
    command.arg("-R");
    run(command);
    assert_eq!(fs::read(dest.join("dir1/deep/c.o")).unwrap(), b"object\n");
    assert!(!dest.join("dir1/a.txt").exists());
    let _ = fs::remove_dir_all(root);
}

fn cpp_bin_command(cpp: &Path, source: &str, dest: &Path, pull: bool) -> Command {
    let mut command = Command::new(cpp);
    command.arg("-a").arg("-e").arg(fakessh()).arg(format!("--rsync-path={}", xs_rs()));
    if pull {
        command.arg(format!("fake:{source}")).arg(format!("{}/", dest.display()));
    } else {
        command.arg(source).arg(format!("fake:{}/", dest.display()));
    }
    command
}

#[test]
fn relative_paths_survive_a_rust_push_and_a_cpp_pull() {
    let Some(cpp_bin) = xs_bin() else { return };
    let root = temp_root("relative-rust");
    let source = root.join("source");
    fs::create_dir_all(source.join("dir1/deep")).unwrap();
    fs::write(source.join("dir1/deep/c.o"), b"object\n").unwrap();
    fs::write(source.join("dir1/a.txt"), b"a\n").unwrap();
    let leaf = format!("{}/./dir1/deep/c.o", source.display());
    let dest = root.join("push");
    fs::create_dir_all(&dest).unwrap();
    let mut command = Command::new(xs_rs());
    command
        .arg("-aR")
        .arg("-e")
        .arg(fakessh())
        .arg(format!("--rsync-path={}", cpp_bin.display()))
        .arg(&leaf)
        .arg(format!("fake:{}/", dest.display()));
    run(command);
    assert_eq!(fs::read(dest.join("dir1/deep/c.o")).unwrap(), b"object\n");
    assert!(!dest.join("dir1/a.txt").exists());

    let dest = root.join("pull");
    fs::create_dir_all(&dest).unwrap();
    let mut command = cpp_bin_command(&cpp_bin, &leaf, &dest, true);
    command.arg("-R");
    run(command);
    assert_eq!(fs::read(dest.join("dir1/deep/c.o")).unwrap(), b"object\n");
    assert!(!dest.join("dir1/a.txt").exists());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn files_from_a_list_copies_only_those_names_both_ways() {
    let Some(cpp_bin) = xs_bin() else { return };
    let root = temp_root("files-from");
    let source = root.join("source");
    fs::create_dir_all(source.join("a/b")).unwrap();
    fs::write(source.join("a/b/one.txt"), b"one\n").unwrap();
    fs::write(source.join("a/b/two.txt"), b"two\n").unwrap();
    let list = root.join("names");
    fs::write(&list, b"a/b/one.txt\n").unwrap();

    let dest = root.join("cpp-push");
    fs::create_dir_all(&dest).unwrap();
    let mut command = cpp(&source, &dest, false);
    command.arg(format!("--files-from={}", list.display()));
    run(command);
    assert_eq!(fs::read(dest.join("a/b/one.txt")).unwrap(), b"one\n");
    assert!(!dest.join("a/b/two.txt").exists());

    let dest = root.join("rust-push");
    fs::create_dir_all(&dest).unwrap();
    let mut command = rust(&cpp_bin, &source, &dest, false);
    command.arg(format!("--files-from={}", list.display()));
    run(command);
    assert_eq!(fs::read(dest.join("a/b/one.txt")).unwrap(), b"one\n");
    assert!(!dest.join("a/b/two.txt").exists());

    let dest = root.join("rust-pull");
    fs::create_dir_all(&dest).unwrap();
    let mut command = rust(&cpp_bin, &source, &dest, true);
    command.arg(format!("--files-from={}", list.display()));
    run(command);
    assert_eq!(fs::read(dest.join("a/b/one.txt")).unwrap(), b"one\n");
    assert!(!dest.join("a/b/two.txt").exists());

    let dest = root.join("cpp-pull");
    fs::create_dir_all(&dest).unwrap();
    let mut command = cpp(&source, &dest, true);
    command.arg(format!("--files-from={}", list.display()));
    run(command);
    assert_eq!(fs::read(dest.join("a/b/one.txt")).unwrap(), b"one\n");
    assert!(!dest.join("a/b/two.txt").exists());
    let _ = fs::remove_dir_all(root);
}

#[test]
fn a_merge_file_filters_in_each_directory() {
    let Some(cpp_bin) = xs_bin() else { return };
    let root = temp_root("merge");
    let source = root.join("source");
    fs::create_dir_all(source.join("a")).unwrap();
    fs::create_dir_all(source.join("b")).unwrap();
    fs::write(source.join("a/keep.txt"), b"keep\n").unwrap();
    fs::write(source.join("a/drop.tmp"), b"drop\n").unwrap();
    fs::write(source.join("b/keep.txt"), b"keep\n").unwrap();
    fs::write(source.join("b/.rules"), b"+ keep.txt\n- *.txt\n").unwrap();
    fs::write(source.join(".rules"), b"- *.tmp\n").unwrap();

    for pull in [false, true] {
        let dest = root.join(format!("dest-{pull}"));
        fs::create_dir_all(&dest).unwrap();
        let mut command = cpp_bin_command(&cpp_bin, &format!("{}/", source.display()), &dest, pull);
        command.args(["--filter=: .rules"]);
        run(command);
        assert!(dest.join("a/keep.txt").exists());
        assert!(!dest.join("a/drop.tmp").exists());
        assert!(dest.join("b/keep.txt").exists());
    }
    let dest = root.join("rust-dest");
    fs::create_dir_all(&dest).unwrap();
    let mut command = rust(&cpp_bin, &source, &dest, false);
    command.args(["--filter=: .rules"]);
    run(command);
    assert!(dest.join("a/keep.txt").exists());
    assert!(!dest.join("a/drop.tmp").exists());
    assert!(dest.join("b/keep.txt").exists());
    let _ = fs::remove_dir_all(root);
}

