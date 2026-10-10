#!/usr/bin/env python3
"""macOS special inodes, immutable destinations, dataless policy and deep paths."""
import os
from pathlib import Path
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest

import output_test as transfer
from xattrs_test import DARWIN, RSYNC
import link_dest_test as snapshots


@unittest.skipUnless(DARWIN, 'macOS behavior')
class MacSpecificTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): snapshots.LinkDestFailures.setUpClass.__func__(cls)
    environment = snapshots.LinkDestFailures.environment

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/tmp', prefix='e12-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def command(self, native, source, target, direction, *flags):
        args = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n']
        if native: args += ['--no-fallback', '-j8']
        a, b = str(source), str(target)
        if direction != 'local':
            args += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        return args + [a, b]

    def test_sockets_and_hard_link_aliases(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-a'], ['-aH'], ['-aHX'], ['-rlt', '--specials']):
                results = []
                for native in (False, True):
                    source, target = self.root / 'source', self.root / 'target'
                    for parent in (source, target):
                        if parent.exists(): shutil.rmtree(parent)
                        parent.mkdir(); parent.chmod(0o750)
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.bind(str(source / 'socket')); sock.close()
                    (source / 'socket').chmod(0o640); os.link(source / 'socket', source / 'alias')
                    for path in [source, target, *source.iterdir()]: os.utime(path, (1500000000, 1500000000))
                    result = subprocess.run(self.command(native, str(source) + '/', str(target) + '/', direction, *flags), capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, (direction, native, flags, result.stderr))
                    state = {}
                    for path in target.iterdir():
                        st = path.lstat()
                        self.assertTrue(stat.S_ISSOCK(st.st_mode))
                        state[path.name] = (st.st_mode, st.st_uid, st.st_gid, st.st_mtime_ns)
                    self.assertEqual(set(state), {'socket', 'alias'})
                    self.assertEqual((target / 'socket').stat().st_ino == (target / 'alias').stat().st_ino, any('H' in flag for flag in flags))
                    results.append((state, sorted(result.stdout.splitlines())))
                self.assertEqual(results[0], results[1], (direction, flags))

    def test_long_socket_names_use_a_short_temporary_bind_name(self):
        source = self.root / 'source'; source.mkdir()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(source / 'short')); sock.close()
        name = 's' * 180; (source / 'short').rename(source / name)
        for direction in ('local', 'push', 'pull'):
            target = self.root / direction
            result = subprocess.run(self.command(True, str(source) + '/', str(target) + '/', direction, '-a'), capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(stat.S_ISSOCK((target / name).lstat().st_mode))
            self.assertEqual([p.name for p in target.iterdir()], [name])

    def test_socket_metadata_api_limits_are_explicit(self):
        from times_test import creation
        source = self.root / 'source'; source.mkdir()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(source / 'socket')); sock.close()
        creation(source / 'socket', 1000000000)
        for direction in ('local', 'push', 'pull'):
            for extra in ('-A', '-N'):
                target = self.root / (direction + extra)
                result = subprocess.run(self.command(True, str(source) + '/', str(target) + '/', direction, '-a', extra), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 23, (direction, extra, result.stderr))
                self.assertIn(b'Operation not supported on socket', result.stderr)
            target = self.root / (direction + 'flags')
            result = subprocess.run(self.command(True, str(source) + '/', str(target) + '/', direction, '-a', '--fileflags'), capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            os.chflags(source / 'socket', stat.UF_NODUMP)
            try:
                target = self.root / (direction + 'different-flags')
                result = subprocess.run(self.command(True, str(source) + '/', str(target) + '/', direction, '-a', '--fileflags'), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertIn(b'file flags', result.stderr)
            finally: os.chflags(source / 'socket', 0)

    def test_socket_snapshot_reuse_keeps_prior_metadata(self):
        from times_test import creation
        source, basis = self.root / 'source', self.root / 'basis'; source.mkdir()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(source / 'socket')); sock.close()
        os.link(source / 'socket', source / 'alias')
        creation(source / 'socket', 1000000000)
        for path in [source, *source.iterdir()]: os.utime(path, (1500000000, 1500000000))
        subprocess.run([RSYNC, '-aHNX', str(source) + '/', str(basis)], check=True, capture_output=True)
        before = (basis / 'socket').stat()
        for direction in ('local', 'push', 'pull'):
            for extra in (False, True):
                target = self.root / (direction + str(extra))
                result = subprocess.run(self.command(True, str(source) + '/', str(target) + '/', direction, '-aHX', *(['-N'] if extra else []), '--link-dest=' + str(basis)), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, (direction, extra, result.stderr))
                self.assertEqual((target / 'socket').stat().st_ino, before.st_ino)
                self.assertEqual((target / 'alias').stat().st_ino, before.st_ino)
                after = (basis / 'socket').stat()
                self.assertEqual((after.st_mode, after.st_mtime_ns, after.st_birthtime), (before.st_mode, before.st_mtime_ns, before.st_birthtime))

    def injected_command(self, source, target, direction):
        args = [str(self.injected_binary), '--no-fallback', '-a', '--no-clone']
        a, b = str(source) + '/', str(target) + '/'
        if direction != 'local':
            args += ['-e', shlex.join([sys.executable, str(transfer.REPO / 'tests/fault_ssh.py')]), '--rsync-path=' + str(self.injected_binary)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        return args + [a, b]

    def test_socket_creation_failures_are_reported_and_cleaned(self):
        source = self.root / 'source'; source.mkdir()
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(str(source / 'socket')); sock.close()
        for direction in ('local', 'push', 'pull'):
            target = self.root / direction
            env = self.environment(target); env['XSYNC_FAULT_BIND_ERROR'] = '13'
            result = subprocess.run(self.injected_command(source, target, direction), env=env, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertIn(b'create socket', result.stderr)
            self.assertEqual(list(target.iterdir()), [])

    def test_socket_creation_stays_in_the_pinned_parent(self):
        for direction in ('local', 'push', 'pull'):
            for child in self.root.iterdir(): shutil.rmtree(child) if child.is_dir() and not child.is_symlink() else child.unlink()
            source, target, outside = [self.root / name for name in ('source', 'target', 'outside')]
            (source / 'nested').mkdir(parents=True); outside.mkdir()
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(str(source / 'nested/socket')); sock.close()
            marker = self.root / 'selected'
            env = self.environment(target)
            env.update(XSYNC_FAULT_AT_OP='open', XSYNC_FAULT_AT_NAME='.xsync-socket-', XSYNC_FAULT_AT_PREFIX='1', XSYNC_FAULT_AT_NOTIFY=str(marker))
            proc = subprocess.Popen(self.injected_command(source, target, direction), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while not marker.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.005)
                self.assertTrue(marker.exists(), 'socket creation not reached')
                (target / 'nested').rename(self.root / 'pinned')
                (target / 'nested').symlink_to(outside, target_is_directory=True)
                out, err = proc.communicate(timeout=15)
            finally:
                if proc.poll() is None: proc.kill()
                proc.communicate()
            self.assertEqual(proc.returncode, 23, (out, err))
            self.assertEqual(list(outside.iterdir()), [])
            self.assertTrue(stat.S_ISSOCK((self.root / 'pinned/socket').lstat().st_mode))
            self.assertFalse(any(p.name.startswith('.xsync-') for p in (self.root / 'pinned').iterdir()))

    def test_immutable_destinations_report_failures_without_changing_data(self):
        for direction in ('local', 'push', 'pull'):
            for inplace in (False, True):
                for native in (False, True):
                    source, target = self.root / 'source', self.root / 'target'
                    source.write_bytes(b'new contents'); source.chmod(0o600)
                    target.write_bytes(b'old contents'); target.chmod(0o640)
                    os.chflags(target, stat.UF_IMMUTABLE)
                    before = target.stat()
                    try:
                        result = subprocess.run(self.command(native, source, target, direction, '-a', *(['--inplace'] if inplace else [])), capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, 23, (direction, native, result.stderr))
                        self.assertEqual(target.read_bytes(), b'old contents')
                        after = target.stat()
                        self.assertEqual((after.st_ino, after.st_mode, after.st_flags, after.st_mtime_ns), (before.st_ino, before.st_mode, before.st_flags, before.st_mtime_ns))
                        self.assertFalse(any(p.name.startswith(('.target.', '.xsync-')) for p in self.root.iterdir()))
                    finally: os.chflags(target, 0)

    def test_dataless_flags_force_reads_instead_of_clones(self):
        # Synthetic SF_DATALESS verifies the control path without requiring a
        # user's iCloud file or claiming a real cloud hydration test.
        for directory in (False, True):
            for dataless in (False, True):
                source = self.root / 'source'; target = self.root / 'target'
                for path in (source, target):
                    if path.exists(): shutil.rmtree(path) if path.is_dir() else path.unlink()
                if directory:
                    (source / 'leaf').mkdir(parents=True)
                    file = source / 'leaf/file'; file.write_bytes(b'dataless policy data' * 1024)
                else:
                    file = source; file.write_bytes(b'dataless policy data' * 1024)
                clone, read = self.root / 'cloned', self.root / 'read'
                for marker in (clone, read.with_name('read.1')):
                    if marker.exists(): marker.unlink()
                env = self.environment(source)
                env.update(XSYNC_FAULT_CLONE_NOTIFY=str(clone), XSYNC_FAULT_READ_NOTIFY=str(read))
                if dataless: env['XSYNC_FAULT_DATALESS'] = '1'
                a = str(source) + ('/' if directory else '')
                args = [str(self.injected_binary), '--no-fallback', '-a', '--clone', a, str(target)]
                result = subprocess.run(args, env=env, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((target / 'leaf/file' if directory else target).read_bytes(), file.read_bytes())
                self.assertEqual(clone.exists(), not dataless)
                if dataless: self.assertTrue(read.with_name('read.1').exists())

    @unittest.skipUnless(os.environ.get('XSYNC_ICLOUD_FILE'), 'set XSYNC_ICLOUD_FILE to an opted-in dataless file')
    def test_opted_in_icloud_file_becomes_a_resident_copy(self):
        source = Path(os.environ['XSYNC_ICLOUD_FILE']).resolve()
        if not source.stat().st_flags & 0x40000000: self.skipTest('opted-in file is already resident')
        target = self.root / 'hydrated'
        result = subprocess.run([str(transfer.BINARY), '--no-fallback', '-a', '--clone', str(source), str(target)], capture_output=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(target.stat().st_flags & 0x40000000)
        self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_sources_beyond_path_max_report_a_partial_transfer(self):
        source = self.root / 'deep'; source.mkdir()
        name = 'directory-' + 'x' * 20
        limit = os.pathconf(source, 'PC_PATH_MAX')
        depth = limit // (len(name) + 1) + 10
        fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for _ in range(depth):
                os.mkdir(name, dir_fd=fd)
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = child
            leaf = os.open('file', os.O_WRONLY | os.O_CREAT, 0o640, dir_fd=fd)
            os.write(leaf, b'deep source contents'); os.close(leaf)
        finally: os.close(fd)
        for direction in ('local', 'push', 'pull'):
            for native in (False, True):
                target = self.root / (direction + str(native))
                result = subprocess.run(self.command(native, str(source) + '/', str(target) + '/', direction, '-a', *(['--no-clone'] if native else [])), capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 23, (direction, native, result.stdout, result.stderr))
                if native:
                    self.assertIn(b'File name too long', result.stderr)
                    self.assertIn(b'error summary', result.stderr)
                else: self.assertIn(b'max-path', result.stderr)


if __name__ == '__main__': unittest.main()
