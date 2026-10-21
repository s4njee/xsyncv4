#!/usr/bin/env python3
"""Concurrent file publication and parallel directory finalization on the receiver."""
import os
from pathlib import Path
import random
import shlex
import signal
import stat
import subprocess
import tempfile
import time
import unittest

import output_test as transfer

FAKESSH = shlex.quote(str(transfer.REPO / 'tests/fakessh.sh'))


class ReceiverConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-receiver-')
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.unlock, Path(self.tmp.name))
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')

    @staticmethod
    def unlock(root):
        # Read-only test directories would stop the temporary tree's removal.
        for directory, _, _ in os.walk(root):
            os.chmod(directory, 0o755)

    def deep_tree(self, base=5, depth=4):
        """base**depth leaf directories, one file each, with modes and times varied per directory."""
        source = self.root / 'source'
        rng = random.Random(11)
        def build(path, level):
            path.mkdir()
            if level == depth:
                (path / 'leaf').write_bytes(rng.randbytes(rng.randrange(0, 3000)))
                os.chmod(path / 'leaf', rng.choice((0o644, 0o600, 0o755, 0o444)))
            else:
                for index in range(base): build(path / f'd{index}', level + 1)
            os.utime(path, ns=(0, rng.randrange(10**17, 10**18)))
        build(source, 0)
        # Restrictive modes on whole subtrees: their children must still be finished first.
        for directory in sorted((d for d, _, _ in os.walk(source)), key=len, reverse=True):
            if rng.random() < 0.15:
                times = os.stat(directory)
                os.chmod(directory, rng.choice((0o555, 0o511, 0o700, 0o750)))
                os.utime(directory, ns=(times.st_atime_ns, times.st_mtime_ns))
        return source

    def snapshot(self, root):
        result = {}
        for directory, names, files in os.walk(root):
            for name in names + files:
                path = Path(directory) / name
                st = path.lstat()
                content = path.read_bytes() if stat.S_ISREG(st.st_mode) else None
                result[str(path.relative_to(root))] = (stat.S_IMODE(st.st_mode), st.st_mtime_ns, content)
        return result

    def test_deep_tree_modes_and_times_survive_parallel_finalization(self):
        source = self.deep_tree()
        expected = self.snapshot(source)
        for direction in ('local', 'push', 'pull'):
            for jobs in ('-j1', '-j8'):
                with self.subTest(direction=direction, jobs=jobs):
                    target = self.root / f'{direction}{jobs}'
                    src, dst = f'{source}/', f'{target}/'
                    if direction == 'push': dst = 'fake:' + dst
                    if direction == 'pull': src = 'fake:' + src
                    command = [str(transfer.BINARY), '--no-fallback', '--no-progress', '--no-clone', '-a', jobs,
                               '-e', FAKESSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY)), src, dst]
                    result = subprocess.run(command, capture_output=True, env=self.env, timeout=120)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    actual = self.snapshot(target)
                    self.assertEqual(sorted(actual), sorted(expected))
                    mismatched = [name for name in expected if actual[name] != expected[name]]
                    self.assertEqual(mismatched, [])

    def test_interrupted_concurrent_receive_leaves_no_temporaries(self):
        source = self.root / 'source'
        rng = random.Random(5)
        for index in range(4000):
            directory = source / f'd{index % 40}'
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f'f{index}').write_bytes(rng.randbytes(rng.randrange(0, 20000)))
        expected = {str(path.relative_to(source)): path.read_bytes() for path in source.rglob('*') if path.is_file()}
        for atomic in ('--atomic', '--no-atomic'):
            for delay in (0.15, 0.3, 0.6):
                with self.subTest(atomic=atomic, delay=delay):
                    target = self.root / f'target{atomic}{delay}'
                    command = [str(transfer.BINARY), '--no-fallback', '--no-progress', '-a', '-j8', atomic,
                               '--bwlimit=20000', '-e', FAKESSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY)),
                               f'{source}/', f'fake:{target}/']
                    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=self.env)
                    time.sleep(delay)
                    proc.send_signal(signal.SIGINT)
                    _, stderr = proc.communicate(timeout=60)
                    self.assertIn(proc.returncode, (0, 20), stderr)
                    time.sleep(0.5)  # The receiving helper finishes its own cleanup after the client.
                    leftovers = [str(p) for p in target.rglob('.*') if p.is_file()] if target.exists() else []
                    self.assertEqual(leftovers, [])
                    if atomic == '--atomic':
                        # Every published name holds the whole file; nothing is truncated.
                        for path in (target.rglob('*') if target.exists() else ()):
                            if path.is_file():
                                self.assertEqual(path.read_bytes(), expected[str(path.relative_to(target))], path)


if __name__ == '__main__': unittest.main()
