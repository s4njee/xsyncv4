#!/usr/bin/env python3
"""Darwin resource-fork and inline-quota scaling with per-process RSS evidence."""
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

import output_test as transfer
from xattrs_test import attr_name, set_attr, get_attrs


def fork_digest(path):
    anchor = os.open(path, os.O_RDONLY)
    try:
        fd = os.open('..namedfork/rsrc', os.O_RDONLY, dir_fd=anchor)
        try:
            digest = hashlib.sha256()
            while True:
                chunk = os.read(fd, 65536)
                if not chunk: break
                digest.update(chunk)
            return digest.digest(), os.fstat(fd).st_size
        finally: os.close(fd)
    finally: os.close(anchor)


@unittest.skipUnless(sys.platform == 'darwin', 'Darwin resource forks and time RSS units')
class XattrMemoryTests(unittest.TestCase):
    def test_bounded_resource_forks_and_inline_quota(self):
        with tempfile.TemporaryDirectory(prefix='xsync xattr memory ') as tmp:
            root = Path(tmp)
            helper = root / 'measured-helper'
            helper.write_text('#!/bin/sh\nulimit -n 64\nexec /usr/bin/time -l ' + shlex.quote(str(transfer.BINARY)) + ' "$@"\n')
            helper.chmod(0o700)
            spool = root / 'private temporary storage'; spool.mkdir()
            env = dict(os.environ, TMPDIR=str(spool))
            for kind, count, size in (('fork', 4, 4 << 20), ('fork', 32, 4 << 20), ('fork', 128, 4 << 20), ('inline', 512, 32768)):
                source = root / (kind + str(count)); source.mkdir()
                for index in range(count):
                    path = source / str(index)
                    path.write_bytes(b'data')
                    if kind == 'fork':
                        anchor = os.open(path, os.O_RDONLY)
                        try:
                            fd = os.open('..namedfork/rsrc', os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=anchor)
                            try:
                                os.ftruncate(fd, size)
                                os.pwrite(fd, index.to_bytes(4, 'little'), size - 4)
                            finally: os.close(fd)
                        finally: os.close(anchor)
                    else:
                        set_attr(path, attr_name('quota'), bytes([index % 251]) * size)
                    os.utime(path, ns=(1500000000000000000, 1500000000000000000))
                before = {p.name: (fork_digest(p) if kind == 'fork' else get_attrs(p), p.stat().st_mtime_ns) for p in source.iterdir()}
                for direction in ('local', 'push', 'pull'):
                    with self.subTest(kind=kind, count=count, direction=direction):
                        target = root / (kind + str(count) + '-' + direction)
                        src, dst = str(source) + '/', str(target) + '/'
                        command = ['/usr/bin/time', '-l', str(transfer.BINARY), '--no-fallback', '--no-clone', '-aX', '-j8']
                        if direction != 'local':
                            command += ['-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.quote(str(helper))]
                            if direction == 'push': dst = 'fake:' + dst
                            else: src = 'fake:' + src
                        result = subprocess.run(command + [src, dst], capture_output=True, timeout=180, env=env)
                        self.assertEqual(result.returncode, 0, result.stderr.decode())
                        rss = [int(n) for n in re.findall(rb'(\d+)\s+maximum resident set size', result.stderr)]
                        self.assertEqual(len(rss), 1 if direction == 'local' else 2, result.stderr)
                        # Transport queues may fill as the tree grows, but neither
                        # side may retain the 512 MiB directory's attribute values.
                        self.assertLess(max(rss), 160 << 20, (kind, count, direction, rss))
                        print(f'{kind} files={count} value_bytes={size} direction={direction} rss_bytes={rss}', flush=True)
                        for name, (attrs, mtime) in before.items():
                            for tree in (source, target):
                                path = tree / name
                                self.assertEqual(path.read_bytes(), b'data')
                                self.assertEqual(path.stat().st_mtime_ns, mtime)
                                self.assertEqual(fork_digest(path) if kind == 'fork' else get_attrs(path), attrs)
                        self.assertEqual(list(spool.iterdir()), [])


    def test_source_storage_failure_preserves_existing_files_and_deletion(self):
        with tempfile.TemporaryDirectory(prefix='xsync xattr failed storage ') as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            path = source / 'file'; path.write_bytes(b'new!')
            anchor = os.open(path, os.O_RDONLY)
            try:
                fd = os.open('..namedfork/rsrc', os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=anchor)
                try: os.ftruncate(fd, 1 << 20)
                finally: os.close(fd)
            finally: os.close(anchor)
            for direction in ('local', 'push', 'pull'):
                target = root / direction; target.mkdir()
                (target / 'file').write_bytes(b'old!')
                set_attr(target / 'file', attr_name('keep'), b'protected')
                before = get_attrs(target / 'file')
                (target / 'extra').write_bytes(b'keep extra')
                src, dst = str(source) + '/', str(target) + '/'
                command = [str(transfer.BINARY), '--no-fallback', '--no-clone', '-aX', '--delete']
                if direction != 'local':
                    command += ['-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.quote(str(transfer.BINARY))]
                    if direction == 'push': dst = 'fake:' + dst
                    else: src = 'fake:' + src
                result = subprocess.run(command + [src, dst], capture_output=True, timeout=30,
                                        env=dict(os.environ, TMPDIR=str(root / 'missing storage')))
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertEqual((target / 'file').read_bytes(), b'old!')
                self.assertEqual(get_attrs(target / 'file'), before)
                self.assertEqual((target / 'extra').read_bytes(), b'keep extra')


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux small-value spill coverage')
class XattrQuotaTests(unittest.TestCase):
    def test_small_values_spill_and_copy_with_one_storage_descriptor(self):
        with tempfile.TemporaryDirectory(prefix='xsync xattr quota ') as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            spool = root / 'spool'; spool.mkdir()
            helper = root / 'limited-helper'
            helper.write_text('#!/bin/sh\nulimit -n 64\nexec ' + shlex.quote(str(transfer.BINARY)) + ' "$@"\n')
            helper.chmod(0o700)
            for index in range(5000):
                path = source / str(index); path.write_bytes(b'data')
                set_attr(path, attr_name('quota'), bytes([index % 251]) * 2048)
            for direction in ('local', 'push', 'pull'):
                src, dst = str(source) + '/', str(root / direction) + '/'
                command = [str(helper), '--no-fallback', '--no-clone', '-aX', '-j8']
                if direction != 'local':
                    command += ['-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.quote(str(helper))]
                    if direction == 'push': dst = 'fake:' + dst
                    else: src = 'fake:' + src
                result = subprocess.run(command + [src, dst], capture_output=True, timeout=180,
                                        env=dict(os.environ, TMPDIR=str(spool)))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(list(spool.iterdir()), [])
                for index in range(5000):
                    for tree in (source, root / direction):
                        path = tree / str(index)
                        self.assertEqual(path.read_bytes(), b'data')
                        self.assertEqual(os.getxattr(path, attr_name('quota')), bytes([index % 251]) * 2048)


if __name__ == '__main__': unittest.main()
