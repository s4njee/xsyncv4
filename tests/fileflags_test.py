#!/usr/bin/env python3
"""BSD flags across metadata updates, bytes, clones and negotiated peers."""
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

import output_test as transfer
from xattrs_test import DARWIN, RSYNC as STANDARD_RSYNC

RSYNC = os.environ.get('XSYNC_FILEFLAGS_RSYNC', STANDARD_RSYNC)


def clear_flags(root):
    if not root.exists(): return
    for p in [root] + sorted(root.rglob('*')):
        os.chflags(p, 0, follow_symlinks=False)


def snapshot(root):
    result = {}
    for p in [root] + sorted(root.rglob('*')):
        st = p.lstat()
        result[str(p.relative_to(root))] = (st.st_mode, st.st_flags, st.st_mtime_ns,
                                          p.read_bytes() if stat.S_ISREG(st.st_mode) else None)
    return result


@unittest.skipUnless(DARWIN, 'BSD st_flags preservation requires Darwin')
class FileflagsDifferentials(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run([RSYNC, '--version'], capture_output=True, timeout=10)
        if b'file-flags' not in result.stdout:
            raise unittest.SkipTest('set XSYNC_FILEFLAGS_RSYNC to the pinned patched reference')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync BSD flags ')
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(clear_flags, self.root)

    def fixture(self, hardlinks=False, immutable=False):
        clear_flags(self.root)
        for side in ('src', 'dst'):
            p = self.root / side
            if p.exists(): shutil.rmtree(p)
            p.mkdir(); (p / 'sub').mkdir()
            for name in ('same', 'clear', 'changed', 'sub/file', 'linked-a'):
                (p / name).write_bytes(b'old' if side == 'dst' and name == 'changed' else b'data')
            os.link(p / 'linked-a', p / 'linked-b')
            if side == 'src':
                for name in ('new-hidden', 'new-immutable', 'new-append'): (p / name).write_bytes(b'new')
            else: (p / 'extra').write_bytes(b'extra')
            os.mkfifo(p / 'fifo'); (p / 'link').symlink_to('same')
            for f in [p] + sorted(p.rglob('*')): os.utime(f, (1500000000, 1500000000), follow_symlinks=False)
            for name in ('same', 'changed', 'sub/file', 'fifo'):
                os.chflags(p / name, stat.UF_NODUMP if side == 'src' else stat.UF_HIDDEN)
            os.chflags(p / 'clear', 0 if side == 'src' else stat.UF_NODUMP | stat.UF_HIDDEN)
            os.chflags(p / 'link', stat.UF_HIDDEN if side == 'src' else stat.UF_NODUMP, follow_symlinks=False)
            os.chflags(p / 'linked-a', (stat.UF_IMMUTABLE if immutable else stat.UF_HIDDEN) if side == 'src' else 0)
            if side == 'src':
                os.chflags(p / 'new-hidden', stat.UF_HIDDEN)
                os.chflags(p / 'new-immutable', stat.UF_IMMUTABLE)
                os.chflags(p / 'new-append', stat.UF_APPEND)
                os.chflags(p / 'sub', stat.UF_IMMUTABLE | stat.UF_NODUMP)
                os.chflags(p, stat.UF_HIDDEN | stat.UF_NODUMP)

    def run_sync(self, native, flags, direction, clone=False, expected=0):
        command = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n']
        if native:
            command += ['--no-fallback', '-j8']
            if not clone: command += ['--no-clone']
        a, b = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        result = subprocess.run(command + [a, b], capture_output=True, timeout=30,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, expected, (native, direction, flags, result.stdout, result.stderr))
        return result

    def check_case(self, flags, direction='local', clone=False):
        results = []
        for native in (False, True):
            self.fixture()
            before = snapshot(self.root / 'dst')
            result = self.run_sync(native, flags, direction, clone)
            after = snapshot(self.root / 'dst')
            if '-n' in flags: self.assertEqual(after, before)
            results.append((after, sorted(result.stdout.splitlines())))
        self.assertEqual(results[1], results[0], (flags, direction, clone))

    def test_data_metadata_specials_and_itemization(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-a', '--fileflags'], ['-rltD', '--fileflags'], ['-aAX', '--fileflags'],
                          ['-aH', '--fileflags'], ['-a', '--fileflags', '-n'], ['-a', '--fileflags', '--checksum'],
                          ['-a', '--fileflags', '--inplace'], ['-aL', '--fileflags'],
                          ['-a', '--fileflags', '--delete'], ['-a', '--fileflags', '-ii']):
                with self.subTest(direction=direction, flags=flags): self.check_case(flags, direction)

    def test_clones_preserve_requested_flags(self):
        for flags in (['-a', '--fileflags'], ['-aAX', '--fileflags'], ['-aH', '--fileflags']):
            with self.subTest(flags=flags): self.check_case(flags, clone=True)

    def timed_fixture(self, metadata=False):
        from times_test import creation
        from acls_test import set_acl
        from xattrs_test import attr_name, set_attr
        self.fixture()
        for side in ('src', 'dst'):
            p = self.root / side
            if metadata:
                set_acl(p / 'changed', 0 if side == 'src' else 1)
                set_attr(p / 'changed', attr_name('fileflags-composition'), side.encode())
            for f in [p] + sorted(p.rglob('*')):
                saved = f.lstat().st_flags
                os.chflags(f, 0, follow_symlinks=False)
                creation(f, 1000000000 if side == 'src' else 1000000100)
                os.utime(f, (1200000000 if side == 'src' else 1300000000, 1500000000), follow_symlinks=False)
                os.chflags(f, saved, follow_symlinks=False)

    def timed_snapshot(self):
        from acls_test import get_acl
        from xattrs_test import get_attrs
        root = self.root / 'dst'
        times = {}
        for f in [root] + sorted(root.rglob('*')):
            st = f.lstat()
            times[str(f.relative_to(root))] = (int(st.st_birthtime), st.st_atime_ns if not f.is_symlink() and not f.is_dir() else None)
        return (snapshot(root), times, get_acl(root / 'changed'), get_attrs(root / 'changed'))

    def test_flags_compose_with_creation_times_acls_and_links(self):
        for direction, clone, flags in [(d, False, f) for d in ('local', 'push', 'pull')
                                        for f in ('-aN', '-aHAXN', '-rltDEN')] + [('local', True, '-aN'), ('local', True, '-aHAXN')]:
            with self.subTest(direction=direction, clone=clone, flags=flags):
                results = []
                for native in (False, True):
                    self.timed_fixture(metadata='AX' in flags)
                    result = self.run_sync(native, [flags, '--fileflags'], direction, clone)
                    state, times, acl, attrs = self.timed_snapshot()
                    # -U is checked independently below: the pinned upstream
                    # fileflags.diff writes flags before atime but reads them
                    # after atime, corrupting both fields when both are present.
                    results.append((state, {n: t[0] for n, t in times.items()}, acl, attrs, sorted(result.stdout.splitlines())))
                self.assertEqual(results[1], results[0])

    def test_native_flags_compose_with_access_creation_times_acls_and_links(self):
        from acls_test import get_acl
        from xattrs_test import get_attrs
        for direction, clone, flags in [(d, False, f) for d in ('local', 'push', 'pull')
                                        for f in ('-aUN', '-aHAXUN', '-rltDEUN')] + [('local', True, '-aUN'), ('local', True, '-aHAXUN')]:
            with self.subTest(direction=direction, clone=clone, flags=flags):
                self.timed_fixture(metadata='AX' in flags)
                expected = snapshot(self.root / 'src')
                acl, attrs = get_acl(self.root / 'src/changed'), get_attrs(self.root / 'src/changed')
                # snapshot() reads data; restore the requested source atimes.
                for f in (self.root / 'src').rglob('*'):
                    if f.is_symlink() or f.is_dir(): continue
                    saved = f.lstat().st_flags
                    os.chflags(f, 0); os.utime(f, (1200000000, 1500000000)); os.chflags(f, saved)
                result = self.run_sync(True, [flags, '--fileflags'], direction, clone)
                actual, times, actual_acl, actual_attrs = self.timed_snapshot()
                self.assertEqual(set(actual), set(expected) | {'extra'})
                for name, row in expected.items():
                    wanted = list(row)
                    if name == 'link': wanted[1] = stat.UF_NODUMP  # Physical links skip flags.
                    self.assertEqual(actual[name], tuple(wanted), (name, flags, direction, clone))
                    self.assertEqual(times[name][0], 1000000000, name)
                    if times[name][1] is not None: self.assertEqual(times[name][1], 1200000000000000000, name)
                if 'H' in flags:
                    self.assertEqual((self.root / 'dst/linked-a').stat().st_ino, (self.root / 'dst/linked-b').stat().st_ino)
                if 'AX' in flags: self.assertEqual((actual_acl, actual_attrs), (acl, attrs))
                for row in result.stdout.splitlines(): self.assertEqual(len(row.split(b'|')[0]), 12)

    def test_pinned_reference_flags_atime_wire_order_defect(self):
        # Preserve a reproducible boundary rather than compare native metadata
        # against a known-corrupt reference result. This only uses owned paths.
        for side in ('src', 'dst'):
            p = self.root / side; p.mkdir(); (p / 'file').write_bytes(b'data')
            os.utime(p / 'file', (1200000000 if side == 'src' else 1300000000, 1500000000))
        os.chflags(self.root / 'src/file', stat.UF_HIDDEN)
        self.run_sync(False, ['-aU', '--fileflags'], 'local', expected=23)
        st = (self.root / 'dst/file').stat()
        self.assertEqual(st.st_flags, 0)
        self.assertEqual(int(st.st_atime), 128)

    def test_immutable_hard_links_publish_before_flags(self):
        for direction in ('local', 'push', 'pull'):
            for clone in ((False, True) if direction == 'local' else (False,)):
                with self.subTest(direction=direction, clone=clone):
                    self.fixture(immutable=True)
                    source = self.root / 'src/linked-a'
                    os.chflags(source, 0); source.write_bytes(b'updated linked contents')
                    os.utime(source, (1500000000, 1500000000)); os.chflags(source, stat.UF_IMMUTABLE)
                    self.run_sync(True, ['-aH', '--fileflags'], direction, clone)
                    target = self.root / 'dst'
                    self.assertEqual((target / 'linked-a').stat().st_ino, (target / 'linked-b').stat().st_ino)
                    self.assertEqual((target / 'linked-a').stat().st_flags, stat.UF_IMMUTABLE)
                    self.assertEqual((target / 'linked-a').read_bytes(), b'updated linked contents')
                    result = self.run_sync(True, ['-aH', '--fileflags'], direction, clone)
                    self.assertEqual(result.stdout, b'')

    def test_clones_without_option_keep_flags_superset(self):
        self.fixture(immutable=True)
        source = self.root / 'src/linked-a'
        os.chflags(source, 0); source.write_bytes(b'updated linked contents')
        os.utime(source, (1500000000, 1500000000)); os.chflags(source, stat.UF_IMMUTABLE)
        self.run_sync(True, ['-aH'], 'local', clone=True)
        target = self.root / 'dst'
        for name in ('linked-a', 'linked-b', 'new-immutable'):
            self.assertEqual((target / name).stat().st_flags, stat.UF_IMMUTABLE)
        self.assertEqual((target / 'linked-a').stat().st_ino, (target / 'linked-b').stat().st_ino)
        self.assertEqual((target / 'linked-a').read_bytes(), b'updated linked contents')

    def test_older_helper_refuses_or_delegates_before_writes(self):
        import fallback_test as fallback
        helper = fallback.FallbackTests('runTest'); helper.setUp()
        self.addCleanup(helper.doCleanups)
        file = helper.src / 'file with spaces'; os.chflags(file, stat.UF_HIDDEN)
        environment = dict(helper.env, XSYNC_TEST_PEER='capability', XSYNC_CONFIG='', XSYNC_OPTS='')
        environment['PATH'] = str(Path(RSYNC).resolve().parent) + ':' + environment.get('PATH', '/usr/bin:/bin')
        for direction in ('push', 'pull'):
            target = helper.root / direction
            a, b = str(helper.src) + '/', str(target)
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
            arguments = ['-a', '--fileflags', '-e', helper.fake_shell(), a, b]
            result = helper.run_sync('--no-fallback', *arguments, env=environment)
            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn(b'peer does not support --fileflags', result.stderr)
            self.assertFalse(target.exists())
            result = helper.run_sync(*arguments, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr.count(b'falling back'), 1)
            self.assertEqual((target / file.name).stat().st_flags, stat.UF_HIDDEN)
            self.assertEqual((target / file.name).read_bytes(), file.read_bytes())

    def test_existing_immutable_destination_is_not_forced_mutable(self):
        for direction in ('local', 'push', 'pull'):
            for operation in ('metadata', 'data', 'inplace'):
                results = []
                for native in (False, True):
                    clear_flags(self.root)
                    for side in ('src', 'dst'):
                        p = self.root / side
                        if p.exists(): shutil.rmtree(p)
                        p.mkdir(); (p / 'file').write_bytes(b'data' if operation == 'metadata' else b'old' if side == 'dst' else b'new longer data')
                        for f in (p, p / 'file'): os.utime(f, (1500000000, 1500000000))
                    os.chflags(self.root / 'dst/file', stat.UF_IMMUTABLE)
                    flags = ['-a', '--fileflags'] + (['--inplace'] if operation == 'inplace' else [])
                    self.run_sync(native, flags, direction, expected=0 if operation == 'metadata' else 23)
                    f = self.root / 'dst/file'
                    self.assertEqual(f.read_bytes(), b'data' if operation == 'metadata' else b'old')
                    self.assertEqual(f.stat().st_flags, 0 if operation == 'metadata' else stat.UF_IMMUTABLE)
                    self.assertFalse(any(p.name.startswith('.file.') for p in f.parent.iterdir()))
                    results.append((f.read_bytes(), f.stat().st_flags, f.stat().st_mode, f.stat().st_mtime_ns))
                self.assertEqual(results[1], results[0], (direction, operation))

    def test_no_fileflags_and_archive_do_not_preserve_flags(self):
        for direction in ('local', 'push', 'pull'):
            results = []
            for native in (False, True):
                self.fixture()
                result = self.run_sync(native, ['-a', '--fileflags', '--no-fileflags'], direction)
                rows = sorted(result.stdout.splitlines())
                if not native:
                    rows = [row[:-len(row.split(b'|')[-1]) - 2] + b'|' + row.split(b'|')[-1] for row in rows]
                else:
                    self.assertTrue(all(len(row.split(b'|')[0]) == 11 for row in rows))
                results.append((snapshot(self.root / 'dst'), rows))
            self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
