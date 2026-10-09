#!/usr/bin/env python3
"""Streaming local deltas: edited blocks, shifts, moved data and receiver/source races."""
import os
import pathlib
import random
import re
import subprocess
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()
MIB = 1024 * 1024

class DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-delta-lib-')
        cls.fault = pathlib.Path(cls.library_tmp.name) / 'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                '-fPIC', str(REPO / 'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform != 'darwin': args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)
        cls.data = random.Random(847).randbytes(4 * MIB + 173)

    @classmethod
    def tearDownClass(cls): cls.library_tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync-delta-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source, self.dest = self.root / 'source', self.root / 'destination'

    def prepare(self, source, basis):
        self.source.write_bytes(source)
        self.source.chmod(0o640)
        os.utime(self.source, ns=(1600000000123456789, 1600000000123456789))
        self.dest.write_bytes(basis)
        os.utime(self.dest, ns=(1500000000000000000, 1500000000000000000))

    def command(self, *flags):
        return [str(BINARY), '--no-fallback', '-a', '--no-clone', '--stats', '--out-format=%i|%n|%b',
                *flags, str(self.source), str(self.dest)]

    def run_copy(self, *flags):
        result = subprocess.run(self.command(*flags), capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.assertEqual(self.dest.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        self.assertEqual(self.dest.stat().st_mode & 0o777, 0o640)
        self.assertFalse(any(p.name.startswith(('.destination.', '.xsync-basis-')) for p in self.root.iterdir()))
        return result

    def field(self, result, name):
        match = re.search(name.encode() + rb': ([\d,]+)', result.stdout)
        self.assertIsNotNone(match, result.stdout)
        return int(match[1].replace(b',', b''))

    def test_edits_insertions_deletions_reorder_and_tail(self):
        data = self.data
        changed = [data[:12345] + b'new data' + data[12353:],
                   b'inserted at start' + data,
                   data[:98765] + b'inserted in middle' + data[98765:],
                   data[:56789] + data[56896:],
                   data[MIB:3*MIB] + data[:MIB] + data[3*MIB:],
                   data + b'new trailing data', data[:-357]]
        for source in changed:
            with self.subTest(size=len(source)):
                self.prepare(source, data)
                result = self.run_copy()
                self.assertGreater(self.field(result, 'Delta matched data'), len(source) * .8)
                self.assertLess(self.field(result, 'Delta literal data'), 100000)

    def test_inplace_uses_snapshot_and_preserves_inode(self):
        data = self.data
        self.prepare(data[MIB:] + data[:MIB], data)
        alias = self.root / 'outside-hardlink'
        os.link(self.dest, alias)
        inode = self.dest.stat().st_ino
        result = self.run_copy('--inplace')
        self.assertEqual(self.dest.stat().st_ino, inode)
        self.assertEqual(alias.stat().st_ino, inode)
        self.assertEqual(alias.read_bytes(), self.source.read_bytes())
        self.assertGreater(self.field(result, 'Delta matched data'), len(data) * .8)

    def test_whole_file_and_threshold(self):
        for source, flags in ((self.data + b'end', ['-W']), (self.data + b'end', ['--whole-file']),
                              (self.data[:MIB], []), (self.data[:MIB-1], [])):
            with self.subTest(size=len(source), flags=flags):
                self.prepare(source, self.data)
                result = self.run_copy(*flags)
                self.assertEqual(self.field(result, 'Delta matched data'), 0)
                self.assertEqual(self.field(result, 'Delta literal data'), 0)
                line = result.stdout.splitlines()[0]
                self.assertEqual(int(line.split(b'|')[-1]), len(source))
        self.prepare(self.data + b'end', self.data)
        result = self.run_copy('--whole-file', '--no-whole-file')
        self.assertGreater(self.field(result, 'Delta matched data'), 0)

    def test_unrelated_data_and_random_edit_fuzzer(self):
        rng = random.Random(2441)
        for number in range(25):
            basis = rng.randbytes(MIB + rng.randrange(100, 3000))
            source = basis
            for _ in range(3):
                offset = rng.randrange(len(source))
                source = source[:offset] + rng.randbytes(rng.randrange(1, 128)) + source[offset+rng.randrange(0, 128):]
            if number == 24: source = rng.randbytes(len(source))
            self.prepare(source, basis)
            self.run_copy()

    def race(self, change, *flags):
        self.prepare(self.data + b'end', self.data)
        marker = self.root / 'source-read'
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.fault)
        env.update(XSYNC_FAULT_PATH=str(self.source.resolve()), XSYNC_FAULT_PREAD_NOTIFY=str(marker),
                   XSYNC_FAULT_PREAD_MIN_SIZE=str(MIB // 2), XSYNC_FAULT_PREAD_DELAY_US='300000')
        proc = subprocess.Popen(self.command(*flags), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.002)
            self.assertTrue(marker.exists(), 'matcher did not reach its source read')
            change()
            out, err = proc.communicate(timeout=30)
        finally:
            if proc.poll() is None: proc.kill()
            proc.communicate()
        return proc.returncode, out, err

    def test_source_change_retries_consistently(self):
        def change():
            with self.source.open('r+b') as stream:
                stream.seek(2*MIB); stream.write(b'changed during delta')
        code, out, err = self.race(change)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def test_changed_basis_is_rejected_without_publication(self):
        def change():
            with self.dest.open('r+b') as stream:
                stream.seek(MIB); stream.write(b'changed receiver basis')
        code, out, err = self.race(change)
        self.assertEqual(code, 23, err)
        self.assertIn(b'reconstruct delta', err)
        self.assertNotEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.assertFalse(any(p.name.startswith('.destination.') for p in self.root.iterdir()))

    def test_basis_path_replacement_does_not_follow_symlink(self):
        outside = self.root / 'outside'
        outside.write_bytes(b'outside sentinel')
        before = outside.stat()
        def change():
            self.dest.unlink(); self.dest.symlink_to(outside)
        code, out, err = self.race(change)
        self.assertEqual(code, 0, err)
        self.assertFalse(self.dest.is_symlink())
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.assertEqual(outside.read_bytes(), b'outside sentinel')
        self.assertEqual((outside.stat().st_ino, outside.stat().st_mtime_ns, outside.stat().st_nlink),
                         (before.st_ino, before.st_mtime_ns, before.st_nlink))

if __name__ == '__main__': unittest.main()
