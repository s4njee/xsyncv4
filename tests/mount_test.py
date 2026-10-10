#!/usr/bin/env python3
"""macOS real-filesystem regressions for ENOSPC and -x (small disposable APFS image)."""
import errno
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get("XSYNC_TEST_BINARY", REPO / "build/xs")).resolve()
SSH = REPO / "tests/fakessh.sh"


@unittest.skipUnless(sys.platform == "darwin", "requires macOS disk images")
class MountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="xsync-mount-")
        cls.root = pathlib.Path(cls.scratch.name).resolve()
        (cls.root / "src").mkdir()
        cls.mount = cls.root / "src/mounted"
        cls.mount.mkdir()
        cls.image = cls.root / "test.dmg"
        try:
            subprocess.run(["hdiutil", "create", "-quiet", "-size", "64m", "-fs", "APFS",
                            "-volname", "xsync-test", str(cls.image)], check=True, capture_output=True)
            subprocess.run(["hdiutil", "attach", "-quiet", "-nobrowse", "-mountpoint", str(cls.mount),
                            str(cls.image)], check=True, capture_output=True)
        except subprocess.CalledProcessError as error:
            cls.scratch.cleanup()
            raise RuntimeError(error.stderr.decode()) from error

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["hdiutil", "detach", "-quiet", str(cls.mount)], check=True, capture_output=True)
        cls.scratch.cleanup()

    def args(self, transport, source, dest, flags):
        args = [str(BINARY), *flags]
        if transport != "local":
            args += ["-e", str(SSH), "--rsync-path=" + str(BINARY)]
            if transport == "push":
                dest = "fake:" + str(dest)
            else:
                source = "fake:" + str(source)
        return [*args, str(source), str(dest)]

    def test_01_one_file_system(self):
        (self.root / "src/ordinary").write_bytes(b"ordinary")
        (self.mount / "hidden").write_bytes(b"mounted data")
        self.assertNotEqual(self.mount.stat().st_dev, (self.root / "src").stat().st_dev)
        for transport in ("local", "push", "pull"):
            with self.subTest(transport=transport):
                dst = self.root / ("one-fs-" + transport)
                result = subprocess.run(self.args(transport, str(self.root / "src") + "/", str(dst) + "/", ["-ax"]),
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual((dst / "ordinary").read_bytes(), b"ordinary")
                self.assertTrue((dst / "mounted").is_dir())
                self.assertEqual(list((dst / "mounted").iterdir()), [])
                self.assertEqual((dst / "mounted").stat().st_mode & 0o7777, self.mount.stat().st_mode & 0o7777)
                self.assertEqual((dst / "mounted").stat().st_mtime_ns, self.mount.stat().st_mtime_ns)
                shutil.rmtree(dst)
        result = subprocess.run(self.args("local", str(self.root / "src") + "/", self.root / "all-fs", ["-a"]),
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual((self.root / "all-fs/mounted/hidden").read_bytes(), b"mounted data")
        shutil.rmtree(self.root / "all-fs")
        (self.mount / "hidden").unlink()

    def test_02_disk_full(self):
        source = self.root / "full-source"
        source.mkdir()
        (source / "large").write_bytes(b"a" * (16 * 1024 * 1024))
        for transport in ("local", "push", "pull"):
            for existing in (False, True):
                with self.subTest(transport=transport, existing=existing):
                    dst = self.mount / "dst"
                    dst.mkdir()
                    if existing:
                        (dst / "large").write_bytes(b"previous valid file")
                    filler = self.mount / "filler"
                    try:
                        # Leave about 2 MiB so failure happens during a data write.
                        available = shutil.disk_usage(self.mount).free - 2 * 1024 * 1024
                        with filler.open("wb", buffering=0) as stream:
                            block = b"f" * (1024 * 1024)
                            while available > 0:
                                count = min(available, len(block))
                                stream.write(block[:count])
                                available -= count
                        result = subprocess.run(self.args(transport, str(source) + "/", str(dst) + "/",
                                                          ["-a", "--no-clone", "--atomic", "-j4"]),
                                                capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, 11, result.stderr.decode())
                        diagnostics = result.stderr.split(b"xs: error summary:")[0]
                        self.assertEqual(diagnostics.lower().count(b"no space left"), 1, result.stderr.decode())
                        self.assertIn(b"error summary: 1 error (showing first 1)", result.stderr)
                        self.assertEqual(list(dst.glob(".large.*")), [])
                        if existing:
                            self.assertEqual((dst / "large").read_bytes(), b"previous valid file")
                        else:
                            self.assertFalse((dst / "large").exists())
                    finally:
                        filler.unlink(missing_ok=True)
                        shutil.rmtree(dst)


if __name__ == "__main__":
    unittest.main(verbosity=2)
