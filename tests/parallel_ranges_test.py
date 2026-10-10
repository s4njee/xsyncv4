#!/usr/bin/env python3
"""Prove ranges overlap on both ends and stay within the configured worker budget."""
import hashlib
import os
import pathlib
import random
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', ROOT / 'build/xs')).resolve()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


class RangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='xs-range-fixture-')
        cls.root = pathlib.Path(cls.fixture.name)
        cls.source = cls.root / 'source'
        block = random.Random(321).randbytes(1 << 20)
        with cls.source.open('wb') as out:
            for _ in range(64): out.write(block)
            out.write(b'tail past the ranges')
        cls.expected = digest(cls.source)
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xs-range-lib-')
        cls.library = pathlib.Path(cls.library_tmp.name) / 'fault.so'
        command = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   '-fPIC', str(ROOT / 'tests/fault_io.cpp'), '-o', str(cls.library)]
        if sys.platform != 'darwin': command += ['-ldl']
        subprocess.run(command, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()
        cls.library_tmp.cleanup()

    def run_copy(self, direction, jobs=4, peer=None, compress=False):
        with tempfile.TemporaryDirectory(prefix='xs-range-copy-') as tmp:
            destination = pathlib.Path(tmp) / 'destination'
            trace = pathlib.Path(tmp) / 'trace'
            env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FAULT_PATH='/tmp',
                       XSYNC_FAULT_RANGE_TRACE=str(trace))
            # macOS fixture paths start in /private/var/folders rather than /tmp.
            env['XSYNC_FAULT_PATH'] = '/'
            env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.library)
            command = [str(BINARY), '-a' + ('z' if compress else ''), '--no-clone', '--no-fallback',
                       '--no-progress']
            if jobs is not None: command += ['-j' + str(jobs)]
            source, target = str(self.source), str(destination)
            if direction != 'local':
                command += ['-e', str(ROOT / 'tests/fakessh.sh'), '--rsync-path=' + shlex.join(['env', ('DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD') + '=' + str(self.library), str(peer or BINARY)])]
                if direction == 'push': target = 'test:' + target
                else: source = 'test:' + source
            result = subprocess.run(command + [source, target], env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(digest(destination), self.expected)
            self.assertFalse(list(pathlib.Path(tmp).glob('.destination.*')))
            active, peak = {}, {}
            for line in sorted((trace.read_text() if trace.exists() else '').splitlines(), key=lambda line: int(line.split()[0])):
                _, pid, tid, operation, event = line.split()
                key = (pid, operation)
                threads = active.setdefault(key, set())
                if event == 'start': threads.add(tid)
                else: threads.discard(tid)
                peak[key] = max(peak.get(key, 0), len(threads))
            return peak

    def test_local_push_pull_overlap_reads_and_writes(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                peak = self.run_copy(direction)
                for operation in ('read', 'write'):
                    observed = max((n for (_, op), n in peak.items() if op == operation), default=0)
                    self.assertGreaterEqual(observed, 2, (direction, operation, peak))
                    self.assertLessEqual(observed, 4, (direction, operation, peak))

    def test_one_worker_and_compressed_transfer(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                peak = self.run_copy(direction, jobs=1)
                self.assertLessEqual(max(peak.values(), default=0), 1)
        self.run_copy('push', compress=True)
        self.run_copy('pull', compress=True)

    def test_default_keeps_single_file_io_serial(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                peak = self.run_copy(direction, jobs=None)
                self.assertTrue(peak, 'the instrumented transfer must perform I/O')
                self.assertLessEqual(max(peak.values()), 1, (direction, peak))

    def test_every_worker_can_produce_ranges_without_deadlock(self):
        with tempfile.TemporaryDirectory(prefix='xs-range-producers-') as tmp:
            source, target = pathlib.Path(tmp) / 'source', pathlib.Path(tmp) / 'target'
            source.mkdir()
            for index in range(8):
                directory = source / str(index)
                directory.mkdir()
                os.link(self.source, directory / "file")
            for direction in ('local', 'push', 'pull'):
                with self.subTest(direction=direction):
                    if target.exists():
                        import shutil
                        shutil.rmtree(target)
                    command = [str(BINARY), '-a', '--no-clone', '--no-fallback', '--no-progress', '-j4']
                    src, dst = str(source) + '/', str(target) + '/'
                    if direction != 'local':
                        command += ['-e', str(ROOT / 'tests/fakessh.sh'), '--rsync-path=' + str(BINARY)]
                        if direction == 'push': dst = 'test:' + dst
                        else: src = 'test:' + src
                    result = subprocess.run(command + [src, dst], capture_output=True, timeout=60,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(sorted(p.name for p in target.iterdir()), [str(i) for i in range(8)])
                    for directory in target.iterdir(): self.assertEqual(digest(directory / "file"), self.expected)

    @unittest.skipUnless(os.environ.get('XSYNC_RANGE_LEGACY'), 'provide frozen native peer')
    def test_parallel_chunks_interoperate_with_frozen_peer(self):
        peer = pathlib.Path(os.environ['XSYNC_RANGE_LEGACY']).resolve()
        self.run_copy('push', peer=peer)
        self.run_copy('pull', peer=peer)


if __name__ == '__main__':
    unittest.main()
