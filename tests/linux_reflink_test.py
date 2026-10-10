#!/usr/bin/env python3
"""Actual FICLONE success, metadata correction and COW independence on btrfs/XFS."""
import hashlib
import os
import pathlib
import random
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', ROOT / 'build/xs')).resolve()
VOLUME = os.environ.get('XSYNC_REFLINK_TEST_ROOT')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


@unittest.skipUnless(VOLUME and shutil.which('strace'), 'provide a disposable btrfs/XFS volume and strace')
class ReflinkTests(unittest.TestCase):
    def setUp(self):
        kind = subprocess.check_output(['stat', '-f', '-c', '%T', VOLUME], text=True).strip()
        self.assertIn(kind, ('btrfs', 'xfs'), 'a real supporting filesystem is required')
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-reflink-', dir=VOLUME)
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source, self.target = self.root / 'source', self.root / 'target'
        block = random.Random(745).randbytes(1 << 20)
        with self.source.open('wb') as out:
            for _ in range(64): out.write(block)
            out.write(b'unaligned tail')
        self.source.chmod(0o444)
        os.utime(self.source, ns=(1600000000123456789, 1600000000123456789))
        os.setxattr(self.source, 'user.xs-test', b'reflink metadata')

    def copy(self, *flags):
        log = self.root / 'syscalls'
        result = subprocess.run(['strace', '-f', '-e', 'trace=ioctl', '-o', str(log), str(BINARY),
                                 '-aXW', '--no-fallback', '--no-progress', *flags,
                                 str(self.source), str(self.target)], capture_output=True, timeout=30,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(digest(self.source), digest(self.target))
        self.assertEqual(self.target.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        self.assertEqual(os.getxattr(self.target, 'user.xs-test'), b'reflink metadata')
        self.assertFalse(list(self.root.glob('.target.*')))
        return log.read_text()

    def test_actual_clone_and_independent_writes(self):
        trace = self.copy()
        self.assertRegex(trace, r'FICLONE.*= 0')
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o444)
        copied = digest(self.target)
        self.source.chmod(0o640)
        with self.source.open('r+b') as source: source.write(b'changed after cloning')
        self.assertEqual(digest(self.target), copied)
        self.assertNotEqual(digest(self.source), copied)

    def test_omitted_permissions_preserve_existing_mode(self):
        self.target.write_bytes(b'old data')
        self.target.chmod(0o600)
        trace = self.copy('--no-perms')
        self.assertRegex(trace, r'FICLONE.*= 0')
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)

    def test_no_clone_disables_the_ioctl(self):
        trace = self.copy('--no-clone', '-j4')
        self.assertNotRegex(trace, r'FICLONE')


if __name__ == '__main__':
    unittest.main()
