#!/usr/bin/env python3
"""Observe raw/compressed frames from real push/pull transfers and verify bytes."""
import json
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

import output_test as transfer


class CompressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = tempfile.TemporaryDirectory(prefix='xs-compression-policy-')
        cls.addClassCleanup(cls.lib.cleanup)
        cls.policy = Path(cls.lib.name) / 'policy-test'
        flags = (shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'libzstd'], text=True))
                 if shutil.which('pkg-config') else ['-lzstd'])
        subprocess.run(['c++', '-std=c++20', '-I' + str(transfer.REPO / 'src'),
                        str(transfer.REPO / 'tests/compression_policy_test.cpp'),
                        str(transfer.REPO / 'src/compression.cpp'), *flags, '-o', str(cls.policy)],
                       check=True, capture_output=True, timeout=60)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-compression-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        self.env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')

    def copy(self, direction, flags=(), name='file.bin', data=None, compress=True, policy=True, rate=0):
        if data is None: data = b'repeated payload\n' * 131072
        (self.source / name).write_bytes(data)
        destination = self.root / ('destination-' + direction)
        if destination.exists(): shutil.rmtree(destination)
        log = self.root / ('frames-' + direction + '.json')
        helper = [sys.executable, str(transfer.REPO / 'tests/compression_proxy.py'),
                  '--log', str(log), *(['--rate', str(rate)] if rate else []), str(transfer.BINARY)]
        command = [str(transfer.BINARY), '-az' if compress else '-a', '--whole-file', '--no-progress', '--no-fallback', '-j1',
                   *flags, '-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.join(helper)]
        source, target = str(self.source) + '/', str(destination) + '/'
        if direction == 'push': target = 'fake:' + target
        else: source = 'fake:' + source
        result = subprocess.run(command + [source, target], capture_output=True, env=self.env, timeout=90)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((destination / name).read_bytes(), data)
        self.assertEqual((self.source / name).read_bytes(), data)
        frames = json.loads(log.read_text())
        self.assertEqual(any(frame['kind'] == 37 for frame in frames), policy)
        explicit = any(flag.startswith(('--compress-level=', '--zl=')) for flag in flags)
        self.assertEqual([frame['flag'] for frame in frames if frame['kind'] == 37], [int(explicit)] if policy else [])
        self.last_stdout = result.stdout
        data_frames = [frame for frame in frames if frame['kind'] == 4 and
                       frame['direction'] == ('client' if direction == 'push' else 'server')]
        self.assertTrue(data_frames)
        return data_frames

    def test_compressible_blocks_are_compressed_push_pull(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                frames = self.copy(direction)
                self.assertTrue(any(frame['flag'] == 1 and frame['bytes'] < 65536 for frame in frames))

    def test_suffix_sampling_and_measured_rate_policy(self):
        subprocess.run([str(self.policy)], check=True, timeout=10)

    def test_incompressible_blocks_are_raw_push_pull(self):
        data = random.Random(42).randbytes(2 * 1024 * 1024)
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                frames = self.copy(direction, data=data)
                self.assertTrue(all(frame['flag'] == 0 for frame in frames if frame['bytes'] > 65536))

    def test_default_and_custom_suffixes_are_raw(self):
        for direction in ('push', 'pull'):
            for name, flags in (('archive.GZ', []), ('file.mp4', ['--skip-compress=mp[34]'])):
                with self.subTest(direction=direction, name=name):
                    frames = self.copy(direction, flags, name)
                    self.assertTrue(all(frame['flag'] == 0 for frame in frames))
                    (self.source / name).unlink()

    def test_small_skipped_files_are_isolated_from_compressed_neighbors(self):
        (self.source / 'a.txt').write_bytes(b'compressible' * 4000)
        (self.source / 'c.txt').write_bytes(b'compressible' * 4000)
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                frames = self.copy(direction, name='b.gz', data=b'raw suffix data' * 1000)
                self.assertTrue(any(frame['flag'] == 0 and frame['bytes'] > 10000 for frame in frames))
                self.assertTrue(any(frame['flag'] == 1 for frame in frames))

    def test_empty_suffix_override_allows_compression(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                frames = self.copy(direction, ['--skip-compress='], 'archive.gz')
                self.assertTrue(any(frame['flag'] == 1 for frame in frames))

    def test_explicit_zero_and_negative_levels_preserve_data(self):
        for direction in ('push', 'pull'):
            for level in (0, -1000, 9):
                with self.subTest(direction=direction, level=level):
                    self.copy(direction, ['--compress-level=' + str(level)], compress=False)

    def test_compression_choice_implies_compression(self):
        for direction in ('push', 'pull'):
            self.copy(direction, ['--compress-choice=zstd'], compress=False)

    def test_a_slow_push_compresses_without_z_unless_turned_off(self):
        # The proxy passes 16 MiB/s, far below 256 MiB/s, as an internet link does.
        slow = 16 << 20
        frames = self.copy('push', compress=False, policy=False, rate=slow)
        self.assertTrue(any(frame['flag'] == 1 for frame in frames), 'a slow push compresses without -z')
        for off in (['--no-auto-compress'], ['--compress-choice=none'], ['--bwlimit=65536']):
            with self.subTest(off=off):
                frames = self.copy('push', off, compress=False, policy=False, rate=slow)
                self.assertTrue(all(frame['flag'] == 0 for frame in frames))
        frames = self.copy('pull', compress=False, policy=False, rate=slow)
        self.assertTrue(all(frame['flag'] == 0 for frame in frames), 'a server does not compress without -z')

    def test_none_choice_remains_raw_after_z_or_explicit_level(self):
        for direction in ('push', 'pull'):
            for later in ('-z', '--compress-level=3'):
                frames = self.copy(direction, ['--compress-choice=none', later], policy=False)
                self.assertTrue(all(frame['flag'] == 0 for frame in frames))

    def test_real_transport_measurements_select_level_and_explicit_override(self):
        # Exceed both 48 MiB writer queues so some compression necessarily
        # happens after sustained transport measurements become available.
        raw = random.Random(42).randbytes(128 * 1024 * 1024)
        (self.source / 'a-random.bin').write_bytes(raw)
        for direction, flags, level in (('push', [], 6), ('pull', ['--compress-level=9'], 9)):
            with self.subTest(direction=direction):
                self.copy(direction, ['--bwlimit=7168', '-vv', *flags], name='z-text.bin', data=b'x' * (4 * 1024 * 1024))
                self.assertEqual((self.root / ('destination-' + direction) / 'a-random.bin').read_bytes(), raw)
                self.assertIn(f'Compression level: {level} ('.encode(), self.last_stdout)

    @unittest.skipUnless(os.environ.get('XSYNC_COMPRESSION_LEGACY'), 'provide a pre-policy native binary')
    def test_mixed_peer_versions_and_custom_pull_rejection(self):
        legacy = os.environ['XSYNC_COMPRESSION_LEGACY']
        data = b'mixed-peer data\n' * 131072
        (self.source / 'file.gz').write_bytes(data)
        for client, server, label in ((str(transfer.BINARY), legacy, 'new-old'),
                                      (legacy, str(transfer.BINARY), 'old-new')):
            for direction in ('push', 'pull'):
                with self.subTest(label=label, direction=direction):
                    destination = self.root / (label + '-' + direction)
                    source, target = str(self.source) + '/', str(destination) + '/'
                    if direction == 'push': target = 'fake:' + target
                    else: source = 'fake:' + source
                    command = [client, '-az', '--whole-file', '--no-fallback', '--no-progress', '-j1',
                               '-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')),
                               '--rsync-path=' + shlex.quote(server), source, target]
                    result = subprocess.run(command, env=self.env, capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((destination / 'file.gz').read_bytes(), data)
        destination = self.root / 'rejected'
        command = [str(transfer.BINARY), '-az', '--skip-compress=gz', '--no-fallback', '--no-progress',
                   '-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + shlex.quote(legacy),
                   'fake:' + str(self.source) + '/', str(destination) + '/']
        result = subprocess.run(command, env=self.env, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn(b'peer does not support --skip-compress', result.stderr)
        self.assertFalse(destination.exists())


if __name__ == '__main__': unittest.main()
