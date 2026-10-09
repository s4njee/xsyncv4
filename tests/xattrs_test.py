#!/usr/bin/env python3
"""Native extended-attribute transfers compared with current rsync."""
import base64
import ctypes
import errno
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import difftest
import output_test as transfer
from filter_diff_test import RSYNC

DARWIN = sys.platform == 'darwin'
LIBC = ctypes.CDLL(None, use_errno=True) if DARWIN else None
if DARWIN:
    LIBC.listxattr.restype = LIBC.getxattr.restype = ctypes.c_ssize_t
    LIBC.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    LIBC.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    LIBC.setxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]


def attr_name(name):
    return name if DARWIN else 'user.' + name


def set_attr(path, name, value):
    if not DARWIN:
        os.setxattr(path, name, value, follow_symlinks=False)
    elif LIBC.setxattr(os.fsencode(path), os.fsencode(name), value, len(value), 0, 1) < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(path))


def get_attrs(path):
    if not DARWIN:
        return {name: base64.b64encode(os.getxattr(path, name, follow_symlinks=False)).decode()
                for name in os.listxattr(path, follow_symlinks=False)}
    length = LIBC.listxattr(os.fsencode(path), None, 0, 1)
    if length < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(path))
    names = ctypes.create_string_buffer(length)
    length = LIBC.listxattr(os.fsencode(path), names, length, 1)
    if length < 0:
        raise OSError(ctypes.get_errno(), 'listxattr failed', str(path))
    result = {}
    for name in names.raw[:length].split(b'\0'):
        if not name:
            continue
        size = LIBC.getxattr(os.fsencode(path), name, None, 0, 0, 1)
        if size < 0:
            raise OSError(ctypes.get_errno(), 'getxattr failed', str(path))
        value = ctypes.create_string_buffer(size)
        size = LIBC.getxattr(os.fsencode(path), name, value, size, 0, 1)
        if size < 0:
            raise OSError(ctypes.get_errno(), 'getxattr failed', str(path))
        result[os.fsdecode(name)] = base64.b64encode(value.raw[:size]).decode()
    return result


def snapshot(root):
    result = difftest.snapshot(str(root))
    for name, entry in result.items():
        entry['xattrs'] = get_attrs(root / name)
    return result


class XattrDifferentials(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='xsync-xattrs-')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def fixture(self, rulefiles=None, hardlinks=False, destination_link=False, readonly=False, resource_forks=False):
        for name in ('src', 'dst', 'outside'):
            path = self.root / name
            if path.exists():
                shutil.rmtree(path)
        tree = difftest.Tree(str(self.root))
        tree.d('src', 0o750)
        tree.d('dst', 0o750)
        tree.d('outside', 0o750)
        tree.d('src/sub/deep', 0o750)
        tree.d('dst/sub/deep', 0o750)
        for name, data in (
            ('src/same', b'same'), ('dst/same', b'same'),
            ('src/changed', b'changed data'), ('dst/changed', b'old'),
            ('src/new', b'new data'), ('src/plain', b'plain'), ('dst/plain', b'plain'),
            ('src/big', b'0123456789abcdef' * 131072), ('dst/big', b'0123456789abcdeg' * 131072),
            ('src/sub/deep/file', b'nested'), ('dst/sub/deep/file', b'nested'),
            ('outside/sentinel', b'outside sentinel'),
        ):
            tree.f(name, data)
        tree.ln('src/link', 'same')
        tree.ln('dst/link', 'same')
        tree.fifo('src/pipe')
        tree.fifo('dst/pipe')
        if hardlinks:
            tree.hl('src/new-link', 'src/new')
            tree.hl('src/sub/deep/new-link', 'src/new')
        for name, data in (rulefiles or {}).items():
            tree.f(name, data)
        for directory in ('src', 'dst', 'src/sub', 'dst/sub', 'src/sub/deep', 'dst/sub/deep'):
            set_attr(self.root / directory, attr_name('dir'), b'source directory' if directory.startswith('src') else b'destination directory')
            set_attr(self.root / directory, attr_name('keep'), b'source keep' if directory.startswith('src') else b'destination keep')
        for name in ('same', 'changed', 'new', 'big', 'sub/deep/file'):
            path = self.root / 'src' / name
            for attr, value in (('foo', b'source value'), ('empty', b''), ('binary', b'\0\xff\r\n\x01'),
                                ('keep', b'source keep'), ('rsync.%test', b'source internal')):
                set_attr(path, attr_name(attr), value)
        set_attr(self.root / 'src/new', attr_name('large'), b'large binary attribute\0\xff' * 100)
        for name in ('same', 'changed', 'plain', 'big', 'sub/deep/file'):
            path = self.root / 'dst' / name
            for attr, value in (('foo', b'destination value'), ('stale', b'remove me'),
                                ('keep', b'destination keep'), ('rsync.%test', b'destination internal')):
                set_attr(path, attr_name(attr), value)
        set_attr(self.root / 'dst/same', attr_name('rsync.security.stale'), b'stale disguised namespace')
        if DARWIN:
            # Darwin allows supported xattrs on symlinks without following them.
            for side in ('src', 'dst'):
                try:
                    set_attr(self.root / side / 'link', 'com.apple.test', side.encode())
                except OSError as error:
                    if error.errno not in (errno.EPERM, errno.ENOTSUP):
                        raise
        if destination_link:
            shutil.rmtree(self.root / 'dst/sub')
            tree.dirs = {key: value for key, value in tree.dirs.items() if key != 'dst/sub' and not key.startswith('dst/sub/')}
            tree.ln('dst/sub', '../outside')
        tree.done()
        if resource_forks:
            for side in ('src', 'dst'):
                for name in ('same', 'changed'):
                    path = self.root / side / name
                    before = path.stat()
                    set_attr(path, 'com.apple.ResourceFork', (b'S' if side == 'src' else b'D') * 32768)
                    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        if readonly:
            for side in ('src', 'dst'):
                for name in ('same', 'changed', 'new', 'big'):
                    path = self.root / side / name
                    if path.exists(): path.chmod(0o400)
        return snapshot(self.root)

    def check_case(self, flags, rules=(), clone=False, source='src/', **fixture_options):
        results = []
        begin = time.time_ns() - 2_000_000_000
        for native in (False, True):
            before = self.fixture(**fixture_options)
            command = [str(transfer.BINARY) if native else RSYNC, '-i', '--out-format=%i|%n',
                       *[flag for flag in flags if native or flag != '--no-atomic']]
            if native:
                command += ['--no-fallback', '-j8']
                if not clone:
                    command += ['--no-clone']
            command += ['--filter=' + rule for rule in rules]
            command += [str(self.root) + '/' + source, str(self.root / 'dst') + '/']
            result = subprocess.run(command, capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            if not native:
                reference_code = result.returncode
                self.assertIn(reference_code, (0, 23) if fixture_options.get('readonly') else (0,), (command, result.stderr))
            else:
                self.assertEqual(result.returncode, reference_code, (command, result.stderr))
            after = snapshot(self.root)
            immutable = lambda data: {key: value for key, value in data.items()
                                      if key == 'src' or key.startswith('src/') or key == 'outside' or key.startswith('outside/')}
            self.assertEqual(immutable(after), immutable(before))
            output = sorted(line for line in result.stdout.splitlines() if len(line) > 11 and line[11:12] == b'|')
            results.append((after, output))
        expected, reference_output = results[0]
        actual, output = results[1]
        differences = difftest.compare(expected, actual, window=(begin, time.time_ns() + 2_000_000_000))
        self.assertFalse(differences, '\n'.join(differences))
        self.assertEqual({name: entry['xattrs'] for name, entry in expected.items()},
                         {name: entry['xattrs'] for name, entry in actual.items()})
        if reference_code == 0:
            self.assertEqual(output, reference_output)
        else:
            # rsync prints planned data before open failures; xsync reports completed transfers.
            self.assertTrue(all(line in reference_output for line in output))
            self.assertIn(b'Permission denied', result.stderr)

    def test_local(self):
        for flags in (['-aX'], ['-aXX'], ['-rX'], ['-aXn'], ['-aXXn'], ['-aX', '--inplace'],
                      ['-aX', '--no-atomic'], ['-aX', '--partial'], ['-aX', '--checksum'],
                      ['-aX', '--size-only'], ['-aX', '--ignore-existing'], ['-aX', '--existing'],
                      ['-aX', '--min-size=8'], ['-aX', '--max-size=1m'], ['-aX', '--delete'],
                      ['-aX', '--delete-after'], ['-aX', '-m'], ['-aX', '-L'],
                      ['-aXX', '--no-X', '-X'], ['--xattrs', '-a', '--xattrs']):
            with self.subTest(flags=flags):
                self.check_case(flags)

    def test_clone(self):
        for flags in (['-aX'], ['-aXX'], ['-aX', '--checksum']):
            for rules in ([], ['-x ' + attr_name('keep')], ['-xs ' + attr_name('keep')]):
                with self.subTest(flags=flags, rules=rules):
                    self.check_case(flags, rules, clone=True)

    def test_filters(self):
        name = attr_name('keep')
        for flags in (['-aX'], ['-aXn'], ['-aX', '--inplace'], ['-aX', '--delete-excluded']):
            for rules in (['-x ' + name], ['-xs ' + name], ['-xr ' + name],
                          ['+x ' + name, '-x *'], ['-x *'], ['-x stale'], ['-x /' + name],
                          ['-x! ' + name], ['-x ' + name, '+x *']):
                with self.subTest(flags=flags, rules=rules):
                    self.check_case(flags, rules)

    def test_merges(self):
        name = attr_name('keep')
        cases = [
            ({'src/.rules': ('-x ' + name + '\n').encode()}, [': .rules']),
            ({'src/sub/.rules': ('-x ' + name + '\n').encode()}, [': .rules']),
            ({'dst/sub/.rules': ('-x ' + name + '\n').encode()}, [': .rules']),
            ({'src/.rules': ('-x ' + name + '\n').encode(), 'dst/.rules': ('-x ' + name + '\n').encode()}, [': .rules']),
            ({'src/sub/.rules': b'- *\n'}, [':x .rules']),
            ({'src/.rules': ('-x /' + name + '\n').encode()}, [': .rules']),
            ({'src/sub/.rules': ('-x /' + name + '\n').encode()}, [': .rules']),
            ({'dst/sub/.rules': ('-x /' + attr_name('stale') + '\n').encode()}, [': .rules']),
        ]
        for rulefiles, rules in cases:
            with self.subTest(rulefiles=rulefiles, rules=rules):
                self.check_case(['-aX'], rules, rulefiles=rulefiles)

    def test_hardlinks_relative_and_destination_links(self):
        for flags, options, source in ((['-aHX'], {'hardlinks': True}, 'src/'),
                                       (['-aHXX'], {'hardlinks': True}, 'src/'),
                                       (['-aRX'], {}, './src/sub/deep/file'),
                                       (['-aRXm'], {}, './src/sub/deep/file'),
                                       (['-aX'], {'destination_link': True}, 'src/')):
            with self.subTest(flags=flags, options=options):
                self.check_case(flags, source=source, **options)

    @unittest.skipUnless(DARWIN, 'Darwin resource forks')
    def test_resource_forks_preserve_mtimes(self):
        for clone in (False, True):
            for flags in (['-aX'], ['-aXX'], ['-aXn'], ['-aX', '--inplace']):
                with self.subTest(clone=clone, flags=flags):
                    self.check_case(flags, clone=clone, resource_forks=True)

    def test_readonly_files(self):
        for clone in (False, True):
            for flags in (['-aX'], ['-aXX'], ['-aX', '--inplace']):
                with self.subTest(clone=clone, flags=flags):
                    self.check_case(flags, clone=clone, readonly=True)

    def test_attribute_only_updates_and_idempotence(self):
        self.fixture()
        command = [str(transfer.BINARY), '-aXii', '--out-format=%i|%n', '--no-fallback', str(self.root / 'src') + '/', str(self.root / 'dst') + '/']
        first = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn(b'.f........x|same', first.stdout)
        before = snapshot(self.root)
        second = subprocess.run(command, capture_output=True, timeout=30)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn(b'x|', second.stdout)
        self.assertEqual(snapshot(self.root), before)


if __name__ == '__main__':
    unittest.main()
