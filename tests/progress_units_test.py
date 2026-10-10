#!/usr/bin/env python3
"""Size boundaries agree across progress, stats, plans, and JSON."""
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import unittest

from output_test import BINARY, HOST, RSH
from progress_test import ENV


class ProgressUnitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync-progress-units-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.source = self.root / 'source'; self.source.mkdir()
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)
        self.serial = 0

    def copy(self, size, flags, direction='local'):
        (self.source / 'file').write_bytes(b'x' * size)
        self.serial += 1
        source, dest = str(self.source) + '/', str(self.root / str(self.serial)) + '/'
        args = [str(BINARY), '--no-fallback', '-a', '--no-clone', *flags]
        if direction != 'local':
            args += ['-e', RSH, '--rsync-path=' + shlex.quote('/usr/local/bin/xsync' if HOST else str(BINARY))]
            if direction == 'push': dest = (HOST or 'fake') + ':' + dest
            else:
                if HOST: subprocess.run(['rsync', '-a', '-e', RSH, source, HOST + ':' + source], check=True, capture_output=True)
                source = (HOST or 'fake') + ':' + source
        result = subprocess.run(args + [source, dest], env=ENV, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_progress_and_stats_boundaries(self):
        cases = [(999, '999B', '999B', '999', '999'),
                 (1000, '1.00K', '1000B', '1.00K', '1000'),
                 (1023, '1.02K', '1023B', '1.02K', '1023'),
                 (1024, '1.02K', '1.00K', '1.02K', '1.00K'),
                 (1048576, '1.05M', '1.00M', '1.05M', '1.00M')]
        for direction in ('local', 'push', 'pull'):
            for size, decimal, binary, dec_num, bin_num in cases:
                for human in (None, '-h', '-hh'):
                    with self.subTest(direction=direction, size=size, human=human):
                        result = self.copy(size, ['--progress', '--stats'] + ([human] if human else []), direction)
                        amount = binary if human == '-hh' else decimal
                        number = bin_num if human == '-hh' else dec_num if human else format(size, ',')
                        self.assertIn((amount + ' in ').encode(), result.stderr)
                        self.assertIn(('Total transferred file size: ' + number + ' bytes').encode(), result.stdout)

    def test_dry_run_uses_progress_units(self):
        for direction in ('local', 'push', 'pull'):
            for human in (None, '-h', '-hh'):
                with self.subTest(direction=direction, human=human):
                    result = self.copy(1048576, ['-n'] + ([human] if human else []), direction)
                    amount = '1.00M' if human == '-hh' else '1.05M'
                    self.assertEqual(result.stdout, ('would transfer 1 files (' + amount + '), delete 0\n').encode())

    def test_json_counters_are_unscaled(self):
        for human in (None, '-h', '-hh'):
            result = self.copy(1048576, ['--progress=json'] + ([human] if human else []))
            rows = [json.loads(line) for line in result.stderr.splitlines()]
            self.assertEqual(rows[-1]['bytes'], 1048576)
            self.assertEqual(rows[-1]['bytes_total'], 1048576)
            self.assertEqual(next(r['size'] for r in rows if r['type'] == 'file'), 1048576)

    def test_progress2_human_byte_columns(self):
        for human, amount in ((None, '1,048,576'), ('-h', '1.05M'), ('-hh', '1.00M')):
            result = self.copy(1048576, ['--info=progress2'] + ([human] if human else []))
            self.assertRegex(result.stderr.splitlines()[-1], (r'^\s*' + amount + r'\s+100%').encode())


if __name__ == '__main__': unittest.main()
