#!/usr/bin/env python3
"""Sparse allocation preserves bytes and metadata across all data paths."""
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

import resume_test as resume

import output_test as transfer
from xattrs_test import DARWIN, RSYNC, attr_name, get_attrs, set_attr


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): result.update(block)
    return result.digest()


class SparseDifferentials(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync sparse ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, pattern='mixed', existing=True, size=8 * 1024 * 1024 + 37, old_size=None):
        for side in ('src', 'dst'):
            root = self.root / side
            if root.exists(): shutil.rmtree(root)
            root.mkdir()
            if side == 'src':
                with (root / 'payload').open('wb') as stream:
                    stream.truncate(size)
                    if pattern != 'zero':
                        for offset, data in ((3, b'head'), (size // 2 + 111, b'middle')):
                            stream.seek(offset); stream.write(data)
                        if pattern == 'mixed': stream.seek(size - 13); stream.write(b'tail')
            elif existing:
                with (root / 'payload').open('wb') as stream:
                    remaining = old_size if old_size is not None else size
                    while remaining:
                        count = min(remaining, 1024 * 1024)
                        stream.write(b'Q' * count); remaining -= count
            for path in [root] + list(root.iterdir()):
                path.chmod(0o751 if side == 'src' else 0o640 if path.is_file() else 0o750)
                os.utime(path, (1500000000, 1500000000 if side == 'src' else 1500000100))

    def command(self, native, flags, direction):
        command = [str(transfer.BINARY) if native else RSYNC, '-a', *flags, '--out-format=%i|%n']
        if native: command += ['--no-fallback', '-j8', '--no-clone']
        source, target = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
            if direction == 'push': target = 'fake:' + target
            else: source = 'fake:' + source
        return command + [source, target]

    def state(self):
        result = {}
        root = self.root / 'dst'
        for path in [root] + sorted(root.iterdir()):
            st = path.stat()
            result[path.name if path != root else '.'] = (st.st_mode & 0o7777, st.st_uid, st.st_gid,
                st.st_mtime_ns, st.st_size if path.is_file() else None, digest(path) if path.is_file() else None)
        return result

    def check(self, flags, direction, pattern='mixed', existing=True, old_size=None, size=8 * 1024 * 1024 + 37, delta_basis=False):
        results = []
        for native in (False, True):
            self.fixture(pattern, existing, size=size, old_size=old_size)
            if delta_basis:
                target = self.root / 'dst/payload'
                shutil.copyfile(self.root / 'src/payload', target)
                with target.open('r+b') as stream:
                    stream.seek(5 * 1024 * 1024 + 53); stream.write(b'old basis bytes')
                os.utime(target, (1500000100, 1500000100))
            source = self.root / 'src/payload'
            expected = digest(source)
            before = self.state()
            result = subprocess.run(self.command(native, flags, direction), capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (native, flags, direction, result.stdout, result.stderr))
            state = self.state()
            self.assertEqual(digest(source), expected)
            if '-n' in flags: self.assertEqual(state, before)
            else:
                target = self.root / 'dst/payload'
                self.assertEqual(digest(target), expected, (native, flags, direction, pattern, existing))
                if native and size >= 65536 and not any(f in flags for f in ('--no-sparse', '--no-S')):
                    st = target.stat()
                    self.assertLess(st.st_blocks * 512, st.st_size // 8, (native, flags, st.st_blocks, st.st_size))
            results.append((state, sorted(result.stdout.splitlines())))
        self.assertEqual(results[1], results[0])

    def test_empty_and_small_zero_files(self):
        for direction in ('local', 'push', 'pull'):
            for size in (0, 1, 4095, 4096, 4097):
                for existing in (False, True):
                    with self.subTest(direction=direction, size=size, existing=existing):
                        self.check(['-S', '--inplace'], direction, pattern='zero', existing=existing, size=size)

    def test_sparse_disables_file_and_directory_clones(self):
        self.fixture(existing=False)
        source = self.root / 'src/payload'
        nested = self.root / 'src/nested'; nested.mkdir()
        shutil.copyfile(source, nested / 'payload')
        command = self.command(True, ['-S', '--clone'], 'local')
        command.remove('--no-clone')
        result = subprocess.run(command, capture_output=True, timeout=30,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        for target in (self.root / 'dst/payload', self.root / 'dst/nested/payload'):
            self.assertEqual(digest(target), digest(source))
            self.assertLess(target.stat().st_blocks * 512, target.stat().st_size // 8)

    def test_reused_delta_blocks(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-S', '--no-whole-file'], ['-S', '--inplace', '--no-whole-file']):
                with self.subTest(direction=direction, flags=flags):
                    self.check(flags, direction, delta_basis=True)

    def test_hard_links_extended_attributes_and_permissions(self):
        for direction in ('local', 'push', 'pull'):
            results = []
            for native in (False, True):
                self.fixture(existing=False)
                source = self.root / 'src/payload'
                (self.root / 'src/alias').hardlink_to(source)
                set_attr(source, attr_name('sparse-metadata'), b'attribute' * (4096 if DARWIN else 256))
                os.utime(source, (1500000000, 1500000000))
                os.utime(source.parent, (1500000000, 1500000000))
                result = subprocess.run(self.command(native, ['-HAXS', '--chmod=F640'], direction),
                                        capture_output=True, timeout=30, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                self.assertEqual(result.returncode, 0, (native, direction, result.stderr))
                target, alias = self.root / 'dst/payload', self.root / 'dst/alias'
                self.assertEqual(target.stat().st_ino, alias.stat().st_ino)
                self.assertEqual(digest(target), digest(source))
                self.assertEqual(get_attrs(target), get_attrs(source))
                if native: self.assertLess(target.stat().st_blocks * 512, target.stat().st_size // 8)
                results.append((self.state(), get_attrs(target), sorted(result.stdout.splitlines())))
            self.assertEqual(results[1], results[0], direction)

    @unittest.skipIf(os.geteuid() == 0, 'write-only permissions require an unprivileged receiver')
    def test_write_only_inplace_destination(self):
        for direction in ('local', 'push', 'pull'):
            for permissions in (True, False):
                results = []
                for native in (False, True):
                    self.fixture()
                    target = self.root / 'dst/payload'; target.chmod(0o200)
                    flags = ['-SW', '--inplace'] + ([] if permissions else ['--no-perms'])
                    result = subprocess.run(self.command(native, flags, direction), capture_output=True, timeout=30,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, (native, direction, permissions, result.stderr))
                    mode = target.stat().st_mode & 0o7777
                    target.chmod(mode | 0o400)
                    try: content = digest(target)
                    finally: target.chmod(mode)
                    self.assertEqual(content, digest(self.root / 'src/payload'))
                    # rsync 3.4.4 replaces an unreadable basis mode even with
                    # --no-perms; native writes retain the requested mode.
                    self.assertEqual(mode, 0o751 if permissions or not native else 0o200,
                                     (native, direction, permissions))
                    results.append((mode if permissions else None, content, target.stat().st_mtime_ns, sorted(result.stdout.splitlines())))
                self.assertEqual(results[1], results[0], (direction, permissions))

    def test_zero_mixed_and_trailing_zero_data_paths(self):
        for direction in ('local', 'push', 'pull'):
            for pattern in ('zero', 'mixed', 'trailing'):
                for existing in (False, True):
                    for flags in (['-S'], ['-S', '-W'], ['-S', '--inplace']):
                        with self.subTest(direction=direction, pattern=pattern, existing=existing, flags=flags):
                            self.check(flags, direction, pattern, existing)

    def test_dry_checksum_compression_cancellation_and_size_changes(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-S', '-n'], ['-S', '-c'], ['-S', '-z'], ['--sparse', '--no-sparse'],
                          ['-S', '--no-S'], ['--no-sparse', '-S'], ['-S', '--inplace', '-W']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction)
            for old_size in (1024 * 1024 + 29, 12 * 1024 * 1024 + 91):
                with self.subTest(direction=direction, old_size=old_size):
                    self.check(['-S', '--inplace'], direction, pattern='trailing', old_size=old_size)


class SparseResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resume.ResumeTests.setUpClass.__func__(cls)
        with cls.source.open('wb') as stream:
            stream.truncate(64 * resume.MIB)
            for offset in range(0, 64 * resume.MIB, resume.MIB):
                stream.seek(offset); stream.write(b'sparse interruption marker')
        cls.digest = resume.sha(cls.source)
        os.utime(cls.source, ns=(1600000000123456789, 1600000000123456789))

    tearDownClass = classmethod(resume.ResumeTests.tearDownClass.__func__)
    fault_env = resume.ResumeTests.fault_env
    wire_bytes = resume.ResumeTests.wire_bytes
    test_sparse_halfway_interrupt_and_disconnect_resume = resume.ResumeTests.test_halfway_interrupt_and_disconnect_resume

    def command(self, transport, target, *flags):
        return resume.ResumeTests.command(self, transport, target, '-S', *flags)

    def check_file(self, target):
        resume.ResumeTests.check_file(self, target)
        self.assertLess(target.stat().st_blocks * 512, target.stat().st_size // 8)

    def test_source_growth_and_shrink_refresh_sparse_eof(self):
        for direction in ('local', 'push', 'pull'):
            for initial, final in ((4 * resume.MIB + 123, 12 * resume.MIB + 37),
                                   (12 * resume.MIB + 37, 4 * resume.MIB + 123)):
                for inplace in (False, True):
                    with self.subTest(direction=direction, initial=initial, final=final, inplace=inplace), tempfile.TemporaryDirectory() as tmp:
                        root = Path(tmp); source, target = root / 'source', root / 'target'
                        with source.open('wb') as stream:
                            stream.truncate(initial); stream.write(b'head')
                        source.chmod(0o640)
                        if inplace: target.write_bytes(b'old' * 32768)
                        marker = root / 'read'
                        env = self.fault_env(source)
                        env.update(XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US='300000')
                        arguments = [str(transfer.BINARY), '--no-fallback', '--no-clone', '-aSW', '-j8']
                        if inplace: arguments.append('--inplace')
                        a, b = str(source), str(target)
                        if direction != 'local':
                            injection = [k + '=' + v for k, v in env.items() if k.startswith('XSYNC_FAULT_') or k in ('DYLD_INSERT_LIBRARIES', 'LD_PRELOAD')]
                            arguments += ['-e', transfer.RSH, '--rsync-path=' + shlex.join(['env', *injection, str(transfer.BINARY)])]
                            if direction == 'push': b = 'fake:' + b
                            else: a = 'fake:' + a
                        proc = subprocess.Popen(arguments + [a, b], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                        try:
                            deadline = time.monotonic() + 10
                            while not marker.with_name('read.1').exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
                            self.assertTrue(marker.with_name('read.1').exists(), 'read did not reach source mutation point')
                            with source.open('r+b') as stream:
                                stream.truncate(final); stream.seek(final - 8); stream.write(b'new tail')
                            out, err = proc.communicate(timeout=30)
                            self.assertEqual(proc.returncode, 0, (out, err))
                            self.assertEqual(target.stat().st_size, final)
                            self.assertEqual(digest(target), digest(source))
                            self.assertEqual(target.stat().st_mtime_ns, source.stat().st_mtime_ns)
                            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
                            self.assertLess(target.stat().st_blocks * 512, final // 8)
                            self.assertFalse(list(root.glob('.target.*')))
                        finally:
                            if proc.poll() is None: proc.kill()
                            proc.communicate(timeout=5)


@unittest.skipUnless(transfer.HOST, 'real SSH runs in the isolated Linux rig')
class SparseSSH(unittest.TestCase):
    setUp = SparseDifferentials.setUp

    @classmethod
    def setUpClass(cls):
        from ssh_test import SSHTests
        SSHTests.setUpClass()

    def test_sparse_allocation_bytes_and_metadata_over_ssh(self):
        from ssh_test import remote_code, remote_json
        SparseDifferentials.fixture(self, existing=False)
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', self.root)
        self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)
        source = self.root / 'src/payload'
        remote_source, remote_target = self.root / 'remote-source', self.root / 'remote-target'
        subprocess.run(['rsync', '-a', '-e', transfer.RSH, str(source), transfer.HOST + ':' + str(remote_source)],
                       check=True, capture_output=True, timeout=20)
        expected = digest(source).hex()
        for direction in ('push', 'pull'):
            for existing in (False, True):
                for flags in ([], ['-W'], ['--inplace'], ['-c'], ['-z'], ['--partial']):
                    with self.subTest(direction=direction, existing=existing, flags=flags):
                        target = self.root / 'target'
                        if target.exists(): target.unlink()
                        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.unlink(missing_ok=True); '
                                    'p.write_bytes(b"Q"*int(sys.argv[2])) if int(sys.argv[2]) else None',
                                    remote_target, source.stat().st_size if existing and direction == 'push' else 0)
                        if existing and direction == 'pull': target.write_bytes(b'Q' * source.stat().st_size)
                        a, b = (str(source), transfer.HOST + ':' + str(remote_target)) if direction == 'push' else \
                            (transfer.HOST + ':' + str(remote_source), str(target))
                        result = subprocess.run([str(transfer.BINARY), '--no-fallback', '--no-clone', '-aS', '-j8',
                                                 *flags, '-e', transfer.RSH, '--rsync-path=' + str(transfer.BINARY), a, b],
                                                capture_output=True, timeout=30)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        if direction == 'push':
                            state = remote_json('import os,hashlib,json,sys; p=sys.argv[1]; s=os.stat(p); '
                                                'print(json.dumps([s.st_size,s.st_mode&511,s.st_mtime_ns,s.st_blocks*512,'
                                                'hashlib.sha256(open(p,"rb").read()).hexdigest()]))', remote_target)
                        else:
                            st = target.stat()
                            state = [st.st_size, st.st_mode & 0o777, st.st_mtime_ns, st.st_blocks * 512, digest(target).hex()]
                        self.assertEqual(state[:3], [source.stat().st_size, 0o751, source.stat().st_mtime_ns])
                        self.assertEqual(state[4], expected)
                        self.assertLess(state[3], state[0] // 8)


if __name__ == '__main__': unittest.main()
