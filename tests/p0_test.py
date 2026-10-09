#!/usr/bin/env python3
"""Trust regressions that intentionally differ from rsync or need fault fixtures."""
import os
import pathlib
import pwd
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get("XSYNC_TEST_BINARY", REPO / "build/xsync")).resolve()
SSH = REPO / "tests/fakessh.sh"


class TrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fault_tmp = tempfile.TemporaryDirectory(prefix="xsync-fault-lib-")
        cls.fault_lib = pathlib.Path(cls.fault_tmp.name) / "fault_io.so"
        command = ["c++", "-std=c++20", "-shared", "-fPIC", str(REPO / "tests/fault_io.cpp"), "-o", str(cls.fault_lib)]
        if sys.platform == "darwin":
            command[2] = "-dynamiclib"
        else:
            command.append("-ldl")
        subprocess.run(command, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.fault_tmp.cleanup()

    def fault_env(self, path):
        env = dict(os.environ)
        env["DYLD_INSERT_LIBRARIES" if sys.platform == "darwin" else "LD_PRELOAD"] = str(self.fault_lib)
        env["XSYNC_FAULT_PATH"] = str(path.resolve())
        return env

    def test_source_changes(self):
        for transport in ("local", "push", "pull"):
            for size, change in ((8192, "grow"), (8 * 1024 * 1024, "shrink"),
                                 (8 * 1024 * 1024, "same_size"), (8 * 1024 * 1024, "replace")):
                for mutations in (1, 2):
                    with self.subTest(transport=transport, size=size, change=change, mutations=mutations), tempfile.TemporaryDirectory() as tmp:
                        root = pathlib.Path(tmp)
                        src = root / "source"
                        src.write_bytes(b"a" * size)
                        dest = root / "dest"
                        dest.write_bytes(b"old destination")
                        env = self.fault_env(src)
                        env["XSYNC_FAULT_READ_NOTIFY"] = str(root / "read")
                        env["XSYNC_FAULT_READ_DELAY_US"] = "200000"
                        a, b = str(src), str(dest)
                        flags = ["-a", "--no-clone", "-j4"]
                        if transport != "local":
                            flags += ["-e", f"{sys.executable} {REPO / 'tests/fault_ssh.py'}", "--rsync-path=" + str(BINARY)]
                            if transport == "push":
                                b = "fake:" + b
                            else:
                                a = "fake:" + a
                        proc = subprocess.Popen([str(BINARY), *flags, a, b], cwd=root, env=env,
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        try:
                            for attempt in range(1, mutations + 1):
                                marker = root / f"read.{attempt}"
                                deadline = time.monotonic() + 10
                                while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                                    time.sleep(0.005)
                                self.assertTrue(marker.exists(), "sender never began the expected read")
                                length = size + attempt * 1024 if change == "grow" else size - attempt * 1024 if change == "shrink" else size
                                content = bytes([ord("a") + attempt]) * length
                                if change == "replace":
                                    replacement = root / "replacement"
                                    replacement.write_bytes(content)
                                    replacement.replace(src)
                                else:
                                    src.write_bytes(content)
                            out, err = proc.communicate(timeout=15)
                            self.assertEqual(proc.returncode, 0 if mutations == 1 else 23, err.decode())
                            if mutations == 1:
                                self.assertEqual(dest.read_bytes(), src.read_bytes())
                                self.assertEqual(dest.stat().st_mtime_ns, src.stat().st_mtime_ns)
                            else:
                                self.assertIn(b"changed during transfer after retry", err)
                                self.assertEqual(dest.read_bytes(), b"old destination")
                            self.assertFalse(any(p.name.startswith(".dest.") for p in root.iterdir()))
                        finally:
                            if proc.poll() is None:
                                proc.kill()
                            proc.communicate()

    def run_sync(self, args, cwd, env=None, rc=0):
        result = subprocess.run([str(BINARY), *map(str, args)], cwd=cwd,
                                env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, rc, result.stderr.decode())
        return result

    def remote(self, args):
        return ["-e", str(SSH), "--rsync-path=" + str(BINARY), *args]

    def test_read_error_protects_deletions(self):
        for transport in ("local", "push", "pull"):
            for ignore in (False, True):
                with self.subTest(transport=transport, ignore=ignore), tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    src, dst = root / "src", root / "dst"
                    src.mkdir()
                    dst.mkdir()
                    (src / "unreadable").write_bytes(b"source")
                    (dst / "extra").write_bytes(b"keep")
                    env = self.fault_env(src / "unreadable")
                    env["XSYNC_FAULT_READ_ERROR"] = "1"
                    a, b = str(src) + "/", str(dst) + "/"
                    flags = ["-a", "--delete", "--no-clone"] + (["--ignore-errors"] if ignore else [])
                    if transport != "local":
                        flags += ["-e", f"{sys.executable} {REPO / 'tests/fault_ssh.py'}", "--rsync-path=" + str(BINARY)]
                        if transport == "push":
                            b = "fake:" + b
                        else:
                            a = "fake:" + a
                    result = self.run_sync([*flags, a, b], root, env, rc=23)
                    self.assertEqual((dst / "extra").exists(), not ignore)
                    if not ignore:
                        self.assertIn(b"skipping file deletion", result.stderr)

    def test_remote_disconnect_cleanup(self):
        for transport in ("push", "pull"):
            for event in ("disconnect", "signal"):
                for partial in (False, True):
                    with self.subTest(transport=transport, event=event, partial=partial), tempfile.TemporaryDirectory() as tmp:
                        root = pathlib.Path(tmp)
                        src, dst = root / "src", root / "dst"
                        src.mkdir()
                        dst.mkdir()
                        (src / "large").write_bytes(b"a" * (32 * 1024 * 1024))
                        env = self.fault_env(root)
                        env["XSYNC_FAULT_WRITE_DELAY_US"] = "100000"
                        env["XSYNC_FAULT_EACH_READ_DELAY_US"] = "100000"
                        env["XSYNC_FAULT_SERVER_PID"] = str(root / "server.pid")
                        a, b = str(src) + "/", str(dst) + "/"
                        if transport == "push":
                            b = "fake:" + b
                        else:
                            a = "fake:" + a
                        flags = ["-a", "--atomic", "-j4", "-e", f"{sys.executable} {REPO / 'tests/fault_ssh.py'}",
                                 "--rsync-path=" + str(BINARY)] + (["--partial"] if partial else [])
                        proc = subprocess.Popen([str(BINARY), *flags, a, b], cwd=root, env=env,
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                        try:
                            deadline = time.monotonic() + 10
                            while time.monotonic() < deadline and proc.poll() is None:
                                temps = list(dst.glob(".large.*"))
                                if temps and any(p.stat().st_size > 0 for p in temps):
                                    break
                                time.sleep(0.005)
                            self.assertTrue(temps, "no receiver temporary file")
                            server = int((root / "server.pid").read_text())
                            if event == "signal":
                                os.kill(proc.pid, signal.SIGINT)
                            else:
                                os.kill(proc.pid if transport == "push" else server, signal.SIGKILL)
                            out, err = proc.communicate(timeout=5)
                            expected = 20 if event == "signal" else -signal.SIGKILL if transport == "push" else 12
                            self.assertEqual(proc.returncode, expected, err.decode())
                            self.assertEqual(list(dst.glob(".large.*")), [])
                            self.assertEqual((dst / "large").exists(), partial)
                            if partial:
                                self.assertLess((dst / "large").stat().st_size, (src / "large").stat().st_size)
                        finally:
                            try:
                                os.killpg(proc.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            proc.communicate()

    def test_atomic_default(self):
        for flags, direct in (([], False), (["--no-atomic"], True), (["--inplace"], True)):
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                src, dst = root / "source", root / "dest"
                src.write_bytes(b"a" * (8 * 1024 * 1024))
                env = self.fault_env(src)
                env["XSYNC_FAULT_READ_NOTIFY"] = str(root / "read")
                env["XSYNC_FAULT_READ_DELAY_US"] = "500000"
                proc = subprocess.Popen([str(BINARY), "-a", "--no-clone", *flags, str(src), str(dst)], env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    deadline = time.monotonic() + 5
                    while not (root / "read.1").exists() and time.monotonic() < deadline:
                        time.sleep(0.005)
                    self.assertTrue((root / "read.1").exists())
                    self.assertEqual(dst.exists(), direct)
                    self.assertEqual(bool(list(root.glob(".dest.*"))), not direct)
                    proc.send_signal(signal.SIGINT)
                    out, err = proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode, 20, err.decode())
                    self.assertFalse(dst.exists())
                    self.assertEqual(list(root.glob(".dest.*")), [])
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.communicate()

    def test_no_silent_options(self):
        unsupported = ["--out-format=%p", "--timeout=1", "--contimeout=1", "-S",
                       "--sparse", "--no-sparse", "--fsync", "--preallocate",
                       "--skip-compress=jpg", "--block-size=4096", "--checksum-choice=md5",
                       "--cc=md5", "--log-file-format=%n", "--debug=ALL", "-B4096",
                       "-T/tmp", "-M--fake-super", "-4", "-6", "--ipv4", "--ipv6",
                       "--inc-recursive", "--no-inc-recursive", "--i-r", "--no-i-r",
                       "--old-args", "--no-protect-args", "--open-noatime",
                       "--new-compress", "--old-compress", "--msgs2stderr", "--no-msgs2stderr",
                       "--implied-dirs", "--no-implied-dirs", "--outbuf=L",
                       "--compress-choice=zlib", "--zc=invalid", "--info=name1"]
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "source").write_text("untouched")
            for option in unsupported:
                with self.subTest(option=option):
                    result = self.run_sync(["--no-fallback", option, "source", "dest"], root, rc=1)
                    self.assertIn(b"xsync:", result.stderr)
                    self.assertFalse((root / "dest").exists())
            help_text = self.run_sync(["--help"], root).stdout
            noops = ["--whole-file", "--no-whole-file", "--protect-args", "--secluded-args", "--blocking-io",
                     "--no-blocking-io", "--8-bit-output", "--no-motd"]
            for option in noops:
                self.assertIn(option.encode(), help_text)
                self.run_sync([option, "source", "dest"], root)
            self.run_sync(["-Ws8", "source", "dest"], root)
            self.run_sync(["--compress-choice=zstd", "source", "dest"], root)
            self.run_sync(["--compress-choice=none", "source", "dest"], root)
            self.run_sync(["--info=PROGRESS0,STATS0", "source", "dest"], root)

    def test_receiver_symlink_swaps(self):
        scenarios = ("atomic", "direct", "inplace", "clone", "file_swap", "metadata", "times", "delete", "interrupt", "partial")
        for transport in ("local", "push", "pull"):
            for scenario in scenarios:
                if scenario == "clone" and transport != "local":
                    continue
                with self.subTest(transport=transport, scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp).resolve()
                    src, dst, outside = root / "src", root / "dst", root / "outside"
                    (src / "hot").mkdir(parents=True)
                    (dst / "hot").mkdir(parents=True)
                    outside.mkdir()
                    for name in ("file", "extra"):
                        (outside / name).write_bytes(b"outside must survive")
                        os.utime(outside / name, ns=(1234567890000000000, 1234567890123456789))
                    before = {p.name: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in outside.iterdir()}
                    directory_before = (outside.stat().st_mode, outside.stat().st_mtime_ns)
                    flags = ["-a", "-j1"]
                    if scenario != "clone":
                        flags.append("--no-clone")
                    operation, match, prefix = "open", ".file.", True
                    if scenario == "delete":
                        (dst / "hot/extra").write_bytes(b"delete me")
                        flags.append("--delete")
                        operation, match, prefix = "unlink", "extra", False
                    else:
                        (src / "hot/file").write_bytes(b"new contents" * 1000)
                        if scenario in ("inplace", "file_swap"):
                            (dst / "hot/file").write_bytes(b"old")
                            flags.append("--inplace")
                            match, prefix = "file", False
                        elif scenario == "direct":
                            flags.append("--no-atomic")
                            match, prefix = "file", False
                        elif scenario in ("metadata", "times"):
                            (dst / "hot/file").write_bytes((src / "hot/file").read_bytes())
                            flags.append("--size-only")
                            (src / "hot/file").chmod(0o640)
                            (dst / "hot/file").chmod(0o600 if scenario == "metadata" else 0o640)
                            os.utime(src / "hot/file", (1000000000, 1000000000))
                            os.utime(dst / "hot/file", (2000000000, 2000000000))
                            operation = ("chmod" if sys.platform == "darwin" else "open") if scenario == "metadata" else "times"
                            match, prefix = "file", False
                        if scenario == "partial":
                            flags.append("--partial")
                    env = self.fault_env(dst / "hot")
                    marker = root / "paused"
                    env.update(XSYNC_FAULT_AT_OP=operation, XSYNC_FAULT_AT_NAME=match, XSYNC_FAULT_AT_NOTIFY=str(marker))
                    if prefix:
                        env["XSYNC_FAULT_AT_PREFIX"] = "1"
                    sources, dest = str(src) + "/", str(dst) + "/"
                    if transport != "local":
                        flags += ["-e", f"{sys.executable} {REPO / 'tests/fault_ssh.py'}", "--rsync-path=" + str(BINARY)]
                        if transport == "push":
                            dest = "fake:" + dest
                        else:
                            sources = "fake:" + sources
                    proc = subprocess.Popen([str(BINARY), *flags, sources, dest], cwd=root, env=env,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        deadline = time.monotonic() + 10
                        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                            time.sleep(0.005)
                        self.assertTrue(marker.exists(), "receiver never reached the selected syscall")
                        if scenario in ("file_swap", "metadata", "times"):
                            (dst / "hot/file").unlink()
                            (dst / "hot/file").symlink_to(outside / "file")
                        else:
                            (dst / "hot").rename(root / "parked")
                            (dst / "hot").symlink_to(outside, target_is_directory=True)
                        if scenario in ("interrupt", "partial"):
                            proc.send_signal(signal.SIGINT)
                        out, err = proc.communicate(timeout=15)
                        self.assertIn(proc.returncode, (20,) if scenario in ("interrupt", "partial") else (0, 23), err.decode())
                        after = {p.name: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns) for p in outside.iterdir()}
                        self.assertEqual(before, after)
                        self.assertEqual(directory_before, (outside.stat().st_mode, outside.stat().st_mtime_ns))
                        parked = root / "parked"
                        if parked.exists():
                            self.assertFalse(any(p.name.startswith(".file.") for p in parked.iterdir()))
                            if scenario in ("atomic", "direct", "inplace", "clone"):
                                self.assertEqual((parked / "file").read_bytes(), (src / "hot/file").read_bytes())
                        if scenario == "file_swap":
                            self.assertIn(b"open --inplace", err)
                    finally:
                        if proc.poll() is None:
                            proc.kill()
                        proc.communicate()

    def test_destination_name_collisions(self):
        pairs = [("A", "a"), ("\u00e9.txt", "e\u0301.txt"), ("\u03a3", "\u03c3"), ("stra\u00dfe", "STRASSE"), ("\ufb00", "ff")]
        for transport in ("local", "push", "pull"):
            for first, second in pairs:
                with self.subTest(transport=transport, first=first, second=second), tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    probe = root / "probe"
                    probe.mkdir()
                    (probe / first).write_bytes(b"probe")
                    collides = (probe / second).exists()
                    (probe / first).unlink()
                    probe.rmdir()
                    a, b, dst = root / "one", root / "two", root / "dst"
                    a.mkdir()
                    b.mkdir()
                    dst.mkdir()
                    (a / first).write_bytes(b"first")
                    (b / second).write_bytes(b"second")
                    (a / "other").write_bytes(b"unrelated")
                    (dst / "extra").write_bytes(b"must survive collision")
                    args = [str(a / first), str(b / second), str(a / "other")]
                    dest = str(dst) + "/"
                    flags = ["-a", "--delete", "-j8"]
                    if transport != "local":
                        flags += self.remote([])
                        if transport == "push":
                            dest = "fake:" + dest
                        else:
                            args = ["fake:" + arg for arg in args]
                    result = self.run_sync([*flags, *args, dest], root, rc=23 if collides else 0)
                    if collides:
                        self.assertEqual(result.stderr.count(b"destination name collision"), 1)
                        self.assertFalse((dst / first).exists())
                        self.assertFalse((dst / second).exists())
                        self.assertTrue((dst / "extra").exists())
                    else:
                        self.assertEqual((dst / first).read_bytes(), b"first")
                        self.assertEqual((dst / second).read_bytes(), b"second")
                    self.assertEqual((dst / "other").read_bytes(), b"unrelated")

    def test_directory_name_collisions(self):
        for transport in ("local", "push", "pull"):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                a, b, dst = root / "one", root / "two", root / "dst"
                (a / "A").mkdir(parents=True)
                (b / "a").mkdir(parents=True)
                (a / "A/first").write_bytes(b"first")
                (b / "a/second").write_bytes(b"second")
                dst.mkdir()
                (dst / "extra").write_bytes(b"protected")
                (dst / "caseprobe").touch()
                collides = (dst / "CASEPROBE").exists()
                (dst / "caseprobe").unlink()
                sources, dest = [str(a) + "/", str(b) + "/"], str(dst) + "/"
                flags = ["-a", "--delete"]
                if transport != "local":
                    flags += self.remote([])
                    if transport == "push":
                        dest = "fake:" + dest
                    else:
                        sources = ["fake:" + s for s in sources]
                result = self.run_sync([*flags, *sources, dest], root, rc=23 if collides else 0)
                if collides:
                    self.assertEqual(result.stderr.count(b"destination name collision"), 1)
                    self.assertEqual(sorted(p.name for p in dst.iterdir()), ["extra"])
                else:
                    self.assertEqual((dst / "A/first").read_bytes(), b"first")
                    self.assertEqual((dst / "a/second").read_bytes(), b"second")

    @unittest.skipUnless(sys.platform == "darwin", "requires a case-sensitive APFS image")
    def test_case_sensitive_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp).resolve()
            image, mount = root / "case.dmg", root / "mounted"
            mount.mkdir()
            subprocess.run(["hdiutil", "create", "-quiet", "-size", "64m", "-fs", "Case-sensitive APFS", "-volname", "xsync-case", str(image)],
                           check=True, capture_output=True)
            subprocess.run(["hdiutil", "attach", "-quiet", "-nobrowse", "-mountpoint", str(mount), str(image)],
                           check=True, capture_output=True)
            try:
                a, b = root / "one", root / "two"
                a.mkdir()
                b.mkdir()
                for first, second, rc in (("A", "a", 0), ("\u00e9", "e\u0301", 23)):
                    (a / first).write_bytes(b"first")
                    (b / second).write_bytes(b"second")
                    dst = mount / ("case" if rc == 0 else "normalization")
                    result = self.run_sync(["-a", a / first, b / second, str(dst) + "/"], root, rc=rc)
                    if rc == 0:
                        self.assertEqual((dst / first).read_bytes(), b"first")
                        self.assertEqual((dst / second).read_bytes(), b"second")
                    else:
                        self.assertIn(b"destination name collision", result.stderr)
                        self.assertEqual(list(dst.iterdir()), [])
            finally:
                subprocess.run(["hdiutil", "detach", "-quiet", str(mount)], check=True, capture_output=True)

    @unittest.skipIf(os.geteuid() == 0, "unreadable source fixture requires a non-root user")
    def test_source_error_protects_siblings(self):
        for transport in ("local", "push", "pull"):
            for ignore in (False, True):
                with self.subTest(transport=transport, ignore=ignore), tempfile.TemporaryDirectory() as tmp:
                    root = pathlib.Path(tmp)
                    src, dst = root / "src", root / "dst"
                    (src / "a_unreadable").mkdir(parents=True)
                    (src / "a_unreadable/hidden").write_text("source")
                    (src / "good").mkdir()
                    (src / "good/keep").write_text("keep")
                    (dst / "good").mkdir(parents=True)
                    (dst / "good/extra").write_text("must survive errors")
                    (dst / "root_extra").write_text("must survive errors")
                    (src / "a_unreadable").chmod(0)
                    a, b = str(src) + "/", str(dst) + "/"
                    flags = ["-a", "--delete", "--no-clone"] + (["--ignore-errors"] if ignore else [])
                    if transport != "local":
                        flags += self.remote([])
                        if transport == "push":
                            b = "fake:" + b
                        else:
                            a = "fake:" + a
                    try:
                        result = self.run_sync([*flags, a, b], root, rc=23)
                        self.assertEqual((dst / "good/extra").exists(), not ignore)
                        self.assertEqual((dst / "root_extra").exists(), not ignore)
                        self.assertEqual((dst / "good/keep").read_text(), "keep")
                        if not ignore:
                            self.assertIn(b"skipping file deletion", result.stderr)
                    finally:
                        (src / "a_unreadable").chmod(0o700)

    def test_nested_destination_alias(self):
        for transport in ("local", "push", "pull"):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                src = root / "src"
                src.mkdir()
                (src / "data").write_text("ok")
                (src / "backup").mkdir()
                (src / "alias").symlink_to(src / "backup", target_is_directory=True)
                a, b = str(src) + "/", str(src / "backup") + "/"
                flags = ["-aL"]
                if transport != "local":
                    flags += self.remote([])
                    if transport == "push":
                        b = "fake:" + b
                    else:
                        a = "fake:" + a
                for _ in range(2):
                    self.run_sync(flags + [a, b], root)
                self.assertEqual(sorted(p.name for p in (src / "backup").iterdir()), ["data"])

    def test_remote_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "home with spaces").mkdir()
            home = root / "home with spaces"
            (home / "source").mkdir()
            (home / "source/data").write_text("home expansion")
            env = dict(os.environ, HOME=str(home))
            self.run_sync(["-a", *self.remote(["fake:~/source/", "pulled/"])], root, env)
            self.assertEqual((root / "pulled/data").read_text(), "home expansion")
            self.run_sync(["-a", *self.remote(["pulled/", "fake:~/pushed/"])], root, env)
            self.assertEqual((home / "pushed/data").read_text(), "home expansion")
            self.assertFalse((root / "~").exists())
            self.run_sync(["-a", *self.remote(["fake:~/source/d?t?", "globbed/"])], root, env)
            self.assertEqual((root / "globbed/data").read_text(), "home expansion")
            self.run_sync(["-a", *self.remote(["pulled/", "fake:~/literal*destination/"])], root, env)
            self.assertEqual((home / "literal*destination/data").read_text(), "home expansion")
            # ~user comes from the account database, independently of fake HOME.
            user = pwd.getpwuid(os.geteuid())
            with tempfile.TemporaryDirectory(prefix="xsync-tilde-", dir=user.pw_dir) as actual:
                suffix = pathlib.Path(actual).name
                (pathlib.Path(actual) / "input").write_text("named home")
                self.run_sync(["-a", *self.remote([f"fake:~{user.pw_name}/{suffix}/input", "named"])], root, env)
                self.assertEqual((root / "named").read_text(), "named home")
                self.run_sync(["-a", *self.remote(["named", f"fake:~{user.pw_name}/{suffix}/output"])], root, env)
                self.assertEqual((pathlib.Path(actual) / "output").read_text(), "named home")
            self.run_sync(["-a", *self.remote(["pulled/", "fake:~xsync_no_such_user_817/dst"])], root, env, rc=3)


    def test_hardlink_anchor_replacement_is_rejected(self):
        for direction in ("local", "push", "pull"):
            with self.subTest(direction=direction), tempfile.TemporaryDirectory(prefix="xsync hardlink race ") as tmp:
                root = pathlib.Path(tmp)
                source, dest = root / "source", root / "destination"
                source.mkdir()
                (source / "a").write_bytes(b"validated data")
                os.link(source / "a", source / "z")
                outside = root / "outside"
                outside.write_bytes(b"outside sentinel")
                outside_before = outside.stat()
                marker = root / "link selected"
                env = self.fault_env(dest)
                env.update(XSYNC_FAULT_AT_OP="link", XSYNC_FAULT_AT_NAME="z", XSYNC_FAULT_AT_NOTIFY=str(marker))
                args = [str(BINARY), "--no-fallback", "-aHi", "--no-clone"]
                a, b = str(source) + "/", str(dest) + "/"
                if direction != "local":
                    args += ["-e", f"{sys.executable} {REPO / 'tests/fault_ssh.py'}", "--rsync-path=" + str(BINARY)]
                    if direction == "push": b = "fake:" + b
                    else: a = "fake:" + a
                proc = subprocess.Popen(args + [a, b], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                try:
                    deadline = time.monotonic() + 10
                    while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                        time.sleep(0.005)
                    self.assertTrue(marker.exists(), "hard-link publication was not reached")
                    (dest / "z").unlink()
                    (dest / "z").symlink_to(outside)
                    stdout, stderr = proc.communicate(timeout=10)
                finally:
                    if proc.poll() is None: proc.kill()
                    proc.communicate()
                self.assertEqual(proc.returncode, 23, stderr)
                self.assertIn(b"hard link", stderr)
                self.assertEqual((dest / "a").read_bytes(), b"validated data")
                self.assertEqual(outside.read_bytes(), b"outside sentinel")
                self.assertEqual((outside.stat().st_ino, outside.stat().st_nlink, outside.stat().st_mtime_ns),
                                 (outside_before.st_ino, outside_before.st_nlink, outside_before.st_mtime_ns))
                self.assertFalse(any(path.name.startswith(".xsync-hardlink-") for path in dest.iterdir()))

if __name__ == "__main__":
    unittest.main(verbosity=2)
