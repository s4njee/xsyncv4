#!/usr/bin/env python3
"""Access/create-time behavior across metadata updates, data copies and peers."""
import ctypes
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

import output_test as transfer
from xattrs_test import DARWIN, RSYNC

ACCESS = 1200000000
MODIFY = 1500000000
CREATE = 1000000000


if DARWIN:
    class Attributes(ctypes.Structure):
        _fields_ = [('count', ctypes.c_ushort), ('pad', ctypes.c_ushort),
                    ('common', ctypes.c_uint), ('volume', ctypes.c_uint),
                    ('directory', ctypes.c_uint), ('file', ctypes.c_uint), ('fork', ctypes.c_uint)]
    class Timespec(ctypes.Structure):
        _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]
    LIBC = ctypes.CDLL(None, use_errno=True)
    LIBC.setattrlist.argtypes = (ctypes.c_char_p, ctypes.POINTER(Attributes), ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong)


def creation(path, seconds, nanoseconds=0):
    if not DARWIN: return
    fields = Attributes(); fields.count = 5; fields.common = 512
    time = Timespec(seconds, nanoseconds)
    if LIBC.setattrlist(os.fsencode(path), ctypes.byref(fields), ctypes.byref(time), ctypes.sizeof(time), 1):
        raise OSError(ctypes.get_errno(), 'set creation time', str(path))


def snapshot(root):
    result = {}
    for path in [root] + sorted(root.rglob('*')):
        st = path.lstat()
        result[str(path.relative_to(root))] = (st.st_mode, st.st_size if path.is_file() and not path.is_symlink() else None,
                                             st.st_mtime_ns, int(st.st_atime) if not path.is_dir() and not path.is_symlink() else None,
                                             int(st.st_birthtime) if DARWIN else None)
    return result


class TimeDifferentials(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='xsync times ')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def fixture(self):
        for side in ('src', 'dst'):
            p = self.root / side
            if p.exists(): shutil.rmtree(p)
            p.mkdir(); (p / 'sub').mkdir()
            for name in ('same', 'changed', 'sub/file'):
                (p / name).write_bytes(b'old' if side == 'dst' and name == 'changed' else b'data')
            if side == 'src': (p / 'new').write_bytes(b'new')
            (p / 'link').symlink_to('same'); os.mkfifo(p / 'fifo')
            for path in [p] + sorted(p.rglob('*')):
                os.utime(path, ns=((ACCESS if side == 'src' else ACCESS - 100) * 10**9 + 123456789,
                                  MODIFY * 10**9), follow_symlinks=False)
                creation(path, CREATE if side == 'src' else CREATE - 100)

    def command(self, native, flags, direction, clone=False):
        command = [str(transfer.BINARY) if native else RSYNC, '-i', '--out-format=%i|%n', *flags]
        if native:
            command += ['--no-fallback', '-j8']
            if not clone: command += ['--no-clone']
        a, b = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        return command + [a, b]

    def run_sync(self, native, flags, direction, clone=False):
        result = subprocess.run(self.command(native, flags, direction, clone), capture_output=True, timeout=30,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 0, (flags, direction, result.stdout, result.stderr))
        return result

    def check_case(self, flags, direction='local', clone=False):
        results = []
        start = time.time_ns() - 2 * 10**9
        for native in (False, True):
            self.fixture()
            before = snapshot(self.root / 'dst')
            result = self.run_sync(native, flags, direction, clone)
            after = snapshot(self.root / 'dst')
            if '-n' in flags: self.assertEqual(after, before)
            results.append((after, sorted(result.stdout.splitlines())))
        stop = time.time_ns() + 2 * 10**9
        expected, expected_output = results[0]
        actual, output = results[1]
        self.assertEqual(actual.keys(), expected.keys())
        for name, row in expected.items():
            for column, value in enumerate(row):
                if column == 3 and (not any('U' in flag and flag.startswith('-') and not flag.startswith('--') for flag in flags) or '--no-atimes' in flags):
                    continue  # Unrequested atimes depend on incidental basis reads.
                if clone and column == 4 and name in ('changed', 'new') and not any('N' in flag for flag in flags):
                    self.assertEqual(actual[name][column], CREATE)
                    continue  # APFS clones carry source creation times without -N.
                other = actual[name][column]
                # Non-preserved timestamps on freshly written files/directories
                # are current-clock values; fixed metadata must still agree.
                scale = 1 if column == 2 else 10**9
                dynamic = column >= 2 and value is not None and other is not None and start <= value * scale <= stop and start <= other * scale <= stop
                if not dynamic: self.assertEqual(other, value, (flags, direction, name, column))
        self.assertEqual(output, expected_output, (flags, direction))

    def test_access_time_paths(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-aU'], ['-aUU'], ['-aU', '--inplace'], ['-aU', '--checksum'],
                          ['-aU', '-n'], ['-aUO'], ['-aUJ'], ['-rU'], ['-aU', '--no-atimes'],
                          ['-a', '--open-noatime']):
                with self.subTest(direction=direction, flags=flags): self.check_case(flags, direction)

    @unittest.skipUnless(DARWIN, 'creation times require the native Darwin API')
    def test_creation_time_paths(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-aN'], ['-aUN'], ['-aN', '--inplace'], ['-aN', '--checksum'],
                          ['-aN', '-n'], ['-aNO'], ['-aNJ'], ['-rN'], ['-aN', '--no-crtimes']):
                with self.subTest(direction=direction, flags=flags): self.check_case(flags, direction)

    @unittest.skipUnless(DARWIN, 'APFS clone time correction')
    def test_clone_time_paths(self):
        for flags in (['-aU'], ['-aN'], ['-aUN'], ['-aUNO'], ['-aUNJ']):
            with self.subTest(flags=flags): self.check_case(flags, clone=True)

    def test_repeat_with_open_noatime(self):
        self.fixture()
        self.run_sync(True, ['-aUU'] + (['-N'] if DARWIN else []), 'local')
        # The sender's atime can advance on systems without O_NOATIME. Synchronize
        # once more; the third metadata-only sync must then be empty.
        self.run_sync(True, ['-aUU'] + (['-N'] if DARWIN else []), 'local')
        result = self.run_sync(True, ['-aUU'] + (['-N'] if DARWIN else []), 'local')
        self.assertEqual(result.stdout, b'')

    def test_metadata_composition_and_followed_links(self):
        from acls_test import get_acl, set_acl
        from xattrs_test import attr_name, get_attrs, set_attr
        for direction in ('local', 'push', 'pull'):
            for flags in (['-aUL'], ['-aUH'], ['-aUAX'], *([['-aUNL'], ['-aUNH'], ['-aUNAX']] if DARWIN else [])):
                with self.subTest(direction=direction, flags=flags):
                    if 'H' not in flags[0] and 'AX' not in flags[0]:
                        self.check_case(flags, direction)
                        continue
                    results = []
                    for native in (False, True):
                        self.fixture()
                        for side in ('src', 'dst'):
                            file = self.root / side / 'changed'
                            if 'H' in flags[0]: os.link(file, self.root / side / 'alias')
                            else:
                                set_acl(file, 0 if side == 'src' else 1)
                                set_attr(file, attr_name('times'), side.encode())
                        output = self.run_sync(native, flags, direction)
                        file = self.root / 'dst' / 'changed'
                        result = [file.stat().st_atime_ns]
                        if DARWIN: result.append(int(file.stat().st_birthtime))
                        if 'H' in flags[0]: self.assertEqual(file.stat().st_ino, (self.root / 'dst/alias').stat().st_ino)
                        else: result += [get_acl(file), get_attrs(file)]
                        result.append(sorted(output.stdout.splitlines()))
                        self.assertEqual(file.read_bytes(), b'data')
                        results.append(result)
                    self.assertEqual(results[1], results[0])

    def test_matching_access_seconds_keep_unrequested_fraction(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-aU'], ['-aUU']):
                with self.subTest(direction=direction, flags=flags):
                    results = []
                    for native in (False, True):
                        self.fixture()
                        file = self.root / 'dst/same'
                        os.utime(file, ns=(ACCESS * 10**9 + 987654321, MODIFY * 10**9))
                        result = self.run_sync(native, flags, direction)
                        results.append((file.stat().st_atime_ns, sorted(result.stdout.splitlines())))
                        self.assertEqual(file.stat().st_atime_ns, ACCESS * 10**9 + 987654321)
                    self.assertEqual(results[1], results[0])

    def test_large_whole_delta_inplace_and_resume_paths(self):
        content = b'a' * (3 * 1024 * 1024)
        changed = content[:1024 * 1024] + b'new block' + content[1024 * 1024 + 9:]
        for direction in ('local', 'push', 'pull'):
            for preservation in (['-aU', '-aUN'] if DARWIN else ['-aU']):
                for mode in ('whole', 'delta', 'inplace', 'resume'):
                    with self.subTest(direction=direction, preservation=preservation, mode=mode):
                        results = []
                        for native in (False, True):
                            self.fixture()
                            for side in ('src', 'dst'):
                                file = self.root / side / 'changed'
                                file.write_bytes(changed if side == 'src' else content[:512 * 1024] if mode == 'resume' else content)
                                os.utime(file, ns=((ACCESS if side == 'src' else ACCESS - 100) * 10**9 + 123456789,
                                                  (MODIFY if side == 'src' else MODIFY - 100) * 10**9))
                                creation(file, CREATE if side == 'src' else CREATE - 100)
                            extra = ['--whole-file'] if mode == 'whole' else ['--inplace'] if mode == 'inplace' else ['--partial'] if mode == 'resume' else []
                            result = self.run_sync(native, [preservation, *extra], direction)
                            file = self.root / 'dst/changed'; st = file.stat()
                            self.assertEqual(st.st_atime_ns, ACCESS * 10**9)
                            if 'N' in preservation: self.assertEqual(int(st.st_birthtime), CREATE)
                            results.append((st.st_mtime_ns, sorted(result.stdout.splitlines())))
                            self.assertEqual(file.read_bytes(), changed)
                        self.assertEqual(results[1], results[0])

    @unittest.skipIf(DARWIN, 'Darwin has native creation-time setters')
    def test_local_creation_time_unsupported_before_writes(self):
        self.fixture()
        before = snapshot(self.root / 'dst')
        result = subprocess.run(self.command(True, ['-aN'], 'local'), capture_output=True, timeout=10,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(snapshot(self.root / 'dst'), before)

    @unittest.skipUnless(DARWIN, 'Darwin creation-time fractions')
    def test_matching_creation_seconds_keep_unrequested_fraction(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                results = []
                for native in (False, True):
                    self.fixture()
                    for name in ('', 'same', 'link'): creation(self.root / 'dst' / name, CREATE, 987654321)
                    result = self.run_sync(native, ['-aN'], direction)
                    values = [(self.root / 'dst' / name).lstat().st_birthtime for name in ('', 'same', 'link')]
                    self.assertTrue(all(value > CREATE + 0.9 for value in values))
                    results.append((values, sorted(result.stdout.splitlines())))
                self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
