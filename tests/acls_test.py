#!/usr/bin/env python3
"""Native ACL parity across local byte copies and APFS clones."""
import base64
import ctypes
import errno
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import unittest

import difftest
import output_test as transfer
import xattrs_test as attrs

LIBC = ctypes.CDLL(None, use_errno=True)
if attrs.DARWIN:
    LIBC.acl_get_link_np.argtypes = (ctypes.c_char_p, ctypes.c_int)
    LIBC.acl_get_link_np.restype = ctypes.c_void_p
    LIBC.acl_to_text.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    LIBC.acl_to_text.restype = ctypes.c_void_p
    LIBC.acl_free.argtypes = (ctypes.c_void_p,)


def get_acl(path):
    if not attrs.DARWIN:
        result = {}
        for name in ('system.posix_acl_access', 'system.posix_acl_default'):
            try: result[name] = base64.b64encode(os.getxattr(path, name, follow_symlinks=False)).decode()
            except OSError as error:
                if error.errno not in (errno.ENODATA, errno.ENOTSUP): raise
        return result
    acl = LIBC.acl_get_link_np(os.fsencode(path), 256)
    if not acl:
        if ctypes.get_errno() in (errno.ENOENT, errno.ENOTSUP): return ''
        raise OSError(ctypes.get_errno(), 'get ACL', str(path))
    try:
        text = LIBC.acl_to_text(acl, None)
        if not text: raise OSError(ctypes.get_errno(), 'ACL text', str(path))
        try: return ctypes.string_at(text).decode()
        finally: LIBC.acl_free(text)
    finally: LIBC.acl_free(acl)


def set_acl(path, variant=0, inherit=False, link=False):
    if attrs.DARWIN:
        subprocess.run(['chmod', *(['-h'] if link else []), '-N', str(path)], check=True, capture_output=True)
        entries = ['root allow read,readattr' if variant == 0 else 'root allow write,writeattr',
                   'group:wheel deny delete']
        if inherit: entries[0] += ',file_inherit,directory_inherit'
        for entry in entries:
            subprocess.run(['chmod', *(['-h'] if link else []), '+a', entry, str(path)], check=True, capture_output=True)
    else:
        mode = path.stat().st_mode
        records = [(1, (mode >> 6) & 7, 0xffffffff), (2, 7 if variant == 0 else 5, 60000),
                   (4, 5, 0xffffffff), (8, 5 if variant == 0 else 4, 60001),
                   (16, (mode >> 3) & 7, 0xffffffff), (32, mode & 7, 0xffffffff)]
        data = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *entry) for entry in records)
        os.setxattr(path, 'system.posix_acl_access', data)
        if inherit: os.setxattr(path, 'system.posix_acl_default', data)


def snapshot(root):
    result = attrs.snapshot(root)
    for name, entry in result.items(): entry['acl'] = get_acl(root / name)
    return result


class AclDifferentials(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync ACL ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, identical=False, inherited=True, readonly=False):
        for side in ('src', 'dst'):
            path = self.root / side
            if path.exists():
                path.chmod(0o750)
                for directory in path.rglob('*'):
                    if directory.is_dir() and not directory.is_symlink(): directory.chmod(0o750)
                shutil.rmtree(path)
            path.mkdir(mode=0o750)
            (path / 'sub').mkdir(mode=0o750)
            for name in ('same', 'changed', 'plain', 'sub/file'):
                (path / name).write_bytes(b'old' if side == 'dst' and name == 'changed' else b'data')
            if side == 'src': (path / 'new').write_bytes(b'new')
            (path / 'link').symlink_to('same')
            os.mkfifo(path / 'pipe')
            set_acl(path, 0 if side == 'src' or identical else 1, inherit=inherited)
            set_acl(path / 'sub', 0 if side == 'src' or identical else 1, inherit=inherited)
            for name in ('same', 'changed', 'sub/file', 'pipe'):
                set_acl(path / name, 0 if side == 'src' or identical else 1)
            if side == 'dst': set_acl(path / 'plain', 1)
            if attrs.DARWIN: set_acl(path / 'link', 0 if side == 'src' else 1, link=True)
            for name in ('same', 'changed'):
                attrs.set_attr(path / name, attrs.attr_name('ordinary'), side.encode())
            for leaf in path.rglob('*'):
                os.utime(leaf, ns=(1500000000000000000, 1500000000000000000), follow_symlinks=False)
            os.utime(path, ns=(1500000000000000000, 1500000000000000000))
        if identical:
            os.chmod(self.root / 'src/same', 0o640)
            os.chmod(self.root / 'dst/same', 0o600)
        if readonly:
            # Source directory permissions must not prevent destination children
            # from being created before the final mode is restored.
            for name in ('src', 'src/sub'):
                os.chmod(self.root / name, 0o550)

    def check_case(self, flags, clone=False, rules=(), **fixture):
        results = []
        window = (time.time_ns() - 2_000_000_000, time.time_ns() + 30_000_000_000)
        for native in (False, True):
            self.fixture(**fixture)
            before = snapshot(self.root / 'src')
            command = [str(transfer.BINARY) if native else attrs.RSYNC, '-i', '--out-format=%i|%n', *[flag for flag in flags if native or flag != '--no-atomic']]
            if native:
                command += ['--no-fallback', '-j8']
                if not clone: command += ['--no-clone']
            command += ['--filter=' + rule for rule in rules]
            result = subprocess.run(command + [str(self.root / 'src') + '/', str(self.root / 'dst') + '/'],
                                    capture_output=True, timeout=30, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (command, result.stdout, result.stderr))
            self.assertEqual(snapshot(self.root / 'src'), before)
            results.append((snapshot(self.root / 'dst'), sorted(result.stdout.splitlines())))
        expected, reference_output = results[0]
        actual, output = results[1]
        self.assertFalse(difftest.compare(expected, actual, window=window), difftest.compare(expected, actual, window=window))
        self.assertEqual({n: e['acl'] for n,e in actual.items()}, {n:e['acl'] for n,e in expected.items()})
        # Without -X clones retain ordinary xattrs as documented. ACLs must agree.
        if '-aAX' in flags or not clone:
            self.assertEqual({n:e['xattrs'] for n,e in actual.items()}, {n:e['xattrs'] for n,e in expected.items()})
        self.assertEqual(output, reference_output)

    def test_local_acl_metadata_and_data_paths(self):
        for flags in (['-aA'], ['-aAX'], ['-rA'], ['-aAn'], ['-aA', '--inplace'],
                      ['-aA', '--no-atomic'], ['-aA', '--partial'], ['-aA', '--checksum'], ['-aAL'], ['-aA', '--no-perms']):
            with self.subTest(flags=flags): self.check_case(flags)
        self.check_case(['-aAX'], rules=['-x *'])

    @unittest.skipUnless(attrs.DARWIN, 'APFS clone ACL correction')
    def test_clone_acl_metadata_and_data_paths(self):
        for flags in (['-aA'], ['-aAX'], ['-aAL']):
            with self.subTest(flags=flags): self.check_case(flags, clone=True)

    def test_mode_only_updates_do_not_itemize_acl_changes(self):
        self.check_case(['-aA'], identical=True)

    def test_readonly_directories_and_repeat_sync(self):
        try:
            self.check_case(['-aA'], readonly=True)
            command = [str(transfer.BINARY), '--no-fallback', '--no-clone', '-aAi',
                       str(self.root / 'src') + '/', str(self.root / 'dst') + '/']
            before = snapshot(self.root / 'dst')
            result = subprocess.run(command, capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(snapshot(self.root / 'dst'), before)
        finally:
            for side in ('src', 'dst'):
                for name in ('', 'sub'):
                    path = self.root / side / name
                    if path.exists(): path.chmod(0o750)


if __name__ == '__main__': unittest.main()
