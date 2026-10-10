#!/usr/bin/env python3
"""Large staged lists must finish before NEED, without scanner-window deadlocks."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BINARY = Path(os.environ.get('XSYNC_TEST_BINARY', ROOT / 'build/xs')).resolve()
RSYNC = shutil.which('rsync')
RSH = shlex.quote(str(ROOT / 'tests/fakessh.sh'))


@unittest.skipUnless(RSYNC, 'requires rsync')
class ListingWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='xs-listing-window-')
        cls.root = Path(cls.fixture.name)
        cls.source = cls.root / 'source'
        cls.source.mkdir()
        # More than the production 65,536-entry window; each list is small.
        for d in range(68):
            directory = cls.source / f'dir-{d:03}'
            directory.mkdir()
            for i in range(1024):
                (directory / f'file-{i:04}').touch()
        cls.names = cls.root / 'files-from'
        cls.names.write_text(''.join(f'dir-{d:03}/\n' for d in range(68)))

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def copy(self, direction, flags):
        destination = self.root / ('destination-' + direction)
        if destination.exists():
            shutil.rmtree(destination)
        a, b = str(self.source) + '/', str(destination) + '/'
        if direction == 'push':
            b = 'fake:' + b
        else:
            a = 'fake:' + a
        command = [str(BINARY), *flags, '--no-fallback', '--no-progress', '-j2',
                   '-e', RSH, '--rsync-path=' + shlex.quote(str(BINARY)), a, b]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        proof = subprocess.run([RSYNC, '-anci', '--delete', str(self.source) + '/',
                                str(destination) + '/'], capture_output=True, text=True, timeout=120)
        self.assertEqual(proof.returncode, 0, proof.stderr)
        self.assertEqual(proof.stdout, '', 'independent checksum/metadata verification differs')
        self.assertEqual(sum(len(files) for _, _, files in os.walk(destination)), 68 * 1024)
        shutil.rmtree(destination)

    def test_pruning_push_defers_need_without_deadlock(self):
        self.copy('push', ['-am'])

    def test_pruning_pull_defers_need_without_deadlock(self):
        self.copy('pull', ['-am'])

    def test_validated_files_from_pull_defers_need_without_deadlock(self):
        self.copy('pull', ['-ar', '--files-from=' + str(self.names)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
