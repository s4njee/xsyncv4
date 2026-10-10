#!/usr/bin/env python3
"""Verify Linux kernel copy fallback offsets, source retries and atomic failures."""
import hashlib
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', ROOT / 'build/xs')).resolve()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


class LargeCopyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xs-large-copy-lib-')
        cls.library = pathlib.Path(cls.library_tmp.name) / 'fault.so'
        if sys.platform.startswith('linux'):
            subprocess.run(['c++', '-std=c++20', '-shared', '-fPIC', str(ROOT / 'tests/large_copy_fault.cpp'),
                            '-o', str(cls.library), '-ldl'], check=True)
        cls.data = random.Random(918).randbytes(16 * 1024 * 1024 + 191)

    @classmethod
    def tearDownClass(cls):
        cls.library_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-large-copy-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'
        self.destination = self.root / 'destination'
        self.source.write_bytes(self.data)
        self.source.chmod(0o444)
        os.utime(self.source, ns=(1600000000123456789, 1600000000123456789))

    def copy(self, *flags, fault=None):
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
        if fault:
            env.update(LD_PRELOAD=str(self.library), XS_LARGE_COPY_FAULT=fault,
                       XS_LARGE_COPY_SOURCE=str(self.source))
        return subprocess.run([str(BINARY), '-aW', '--no-fallback', '--no-progress', *flags,
                               str(self.source), str(self.destination)], capture_output=True, env=env, timeout=30)

    def verify(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(digest(self.destination), digest(self.source))
        self.assertEqual(self.destination.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        self.assertEqual(self.destination.stat().st_mode & 0o777, self.source.stat().st_mode & 0o777)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['destination', 'source'])

    def test_large_regular_copy_and_metadata(self):
        self.verify(self.copy())

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux kernel-copy faults')
    def test_short_calls_interruption_zero_and_partial_fallback(self):
        for fault in ('short', 'eintr', 'zero', 'enosys', 'partial-fallback'):
            with self.subTest(fault=fault):
                self.destination.unlink(missing_ok=True)
                self.verify(self.copy(fault=fault))

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux kernel-copy faults')
    def test_source_change_retries_with_fresh_snapshot(self):
        self.source.chmod(0o640)
        self.verify(self.copy(fault='mutate'))
        self.assertEqual(self.source.read_bytes()[0], ord('X'))

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux kernel-copy faults')
    def test_io_failure_preserves_existing_destination(self):
        self.destination.write_bytes(b'original destination')
        result = self.copy(fault='eio')
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(self.destination.read_bytes(), b'original destination')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['destination', 'source'])

    def test_gigabyte_sparse_copy_exercises_cache_threshold(self):
        self.source.chmod(0o640)
        with self.source.open('wb') as stream:
            stream.write(b'head')
            stream.seek((1 << 30) + 17)
            stream.write(b'tail')
        self.verify(self.copy('--no-clone', '--sparse'))
        self.assertLess(self.destination.stat().st_blocks * 512, 1024 * 1024)

    def test_inplace_keeps_inode_and_sparse_keeps_holes(self):
        self.destination.write_bytes(b'old')
        inode = self.destination.stat().st_ino
        self.verify(self.copy('--inplace'))
        self.assertEqual(self.destination.stat().st_ino, inode)
        self.destination.unlink()
        self.source.chmod(0o640)
        with self.source.open('wb') as stream:
            stream.seek(32 * 1024 * 1024)
            stream.write(b'tail')
        self.verify(self.copy('--sparse'))
        self.assertLess(self.destination.stat().st_blocks * 512, self.destination.stat().st_size // 4)


if __name__ == '__main__':
    unittest.main()
