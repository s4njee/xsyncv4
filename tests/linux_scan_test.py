#!/usr/bin/env python3
"""Linux statx scanning, kernel fallback and incomplete-list deletion guards."""
import errno
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import unittest

import difftest
import output_test as transfer
from filter_diff_test import RSYNC


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux syscall path')
class LinuxScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = tempfile.TemporaryDirectory(prefix='xs-linux-scan-lib-')
        cls.addClassCleanup(cls.lib.cleanup)
        cls.deny = Path(cls.lib.name) / 'deny-syscall'
        subprocess.run(['c++', '-std=c++20', str(transfer.REPO / 'tests/deny_syscall.cpp'),
                        '-o', str(cls.deny)], check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-linux-scan-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        # This directory needs multiple getdents64 batches, including maximum
        # filename length and byte names that are not valid UTF-8.
        for number in range(2400):
            path = self.source / f'file-{number:04}-long-name-for-directory-record.json'
            path.write_bytes(f'file {number}\n'.encode())
            path.chmod(0o400 if number % 2 else 0o640)
        (self.source / ('m' * 255)).write_bytes(b'maximum name')
        byte_name = os.fsencode(self.source) + b'/non-utf8-\xff'
        with open(byte_name, 'wb') as out: out.write(b'byte-name data')
        (self.source / 'directory').mkdir()
        (self.source / 'directory/nested').write_bytes(b'nested contents')
        (self.source / 'link').symlink_to('directory/nested')
        (self.source / 'dangling').symlink_to('missing')
        os.mkfifo(self.source / 'fifo', 0o620)
        os.link(self.source / 'file-0000-long-name-for-directory-record.json', self.source / 'alias')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(self.source / 'socket')); sock.close()
        for path in [self.source, *self.source.rglob('*')]:
            os.utime(path, ns=(1500000000123456789, 1500000000123456789), follow_symlinks=False)
        self.env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')

    def command(self, destination, denied=None):
        command = [str(transfer.BINARY), '--no-fallback', '--no-clone', '-aH', '-j4',
                   str(self.source) + '/', str(destination) + '/']
        if denied: command = [str(self.deny), denied[0], str(denied[1]), *command]
        return command

    def compare(self, denied=None):
        expected, actual = self.root / 'expected', self.root / 'actual'
        subprocess.run([RSYNC, '-aH', str(self.source) + '/', str(expected) + '/'],
                       check=True, capture_output=True, timeout=30)
        before = difftest.snapshot(str(self.source))
        result = subprocess.run(self.command(actual, denied), env=self.env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(difftest.snapshot(str(actual)), difftest.snapshot(str(expected)))
        self.assertEqual(difftest.snapshot(str(self.source)), before)

    def test_statx_metadata_types_large_directory_and_byte_names(self):
        self.compare()

    def test_kernel_without_statx_uses_fstatat(self):
        self.compare(('statx', errno.ENOSYS))

    def test_seccomp_hidden_statx_uses_fstatat(self):
        self.compare(('statx', errno.EPERM))

    def test_device_numbers_roundtrip(self):
        try:
            os.mknod(self.source / 'character', stat.S_IFCHR | 0o620, os.makedev(1, 3))
            os.mknod(self.source / 'block', stat.S_IFBLK | 0o640, os.makedev(7, 0))
        except PermissionError:
            self.skipTest('requires permission to create disposable device nodes')
        for name in ('character', 'block'):
            os.utime(self.source / name, ns=(1500000000123456789, 1500000000123456789))
        self.compare()
        for name in ('character', 'block'):
            self.assertEqual((self.root / 'actual' / name).stat().st_rdev,
                             (self.source / name).stat().st_rdev)

    def test_failed_stat_and_directory_reads_preserve_deletion_candidates(self):
        for denied in (('statx', errno.EACCES), ('getdents64', errno.EIO)):
            with self.subTest(denied=denied):
                destination = self.root / 'target'
                if destination.exists(): shutil.rmtree(destination)
                destination.mkdir()
                sentinel = destination / 'keep-on-source-error'
                sentinel.write_bytes(b'destination sentinel')
                command = self.command(destination, denied)
                command.insert(command.index('-aH') + 1, '--delete')
                result = subprocess.run(command, env=self.env, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertEqual(sentinel.read_bytes(), b'destination sentinel')


if __name__ == '__main__':
    unittest.main()
