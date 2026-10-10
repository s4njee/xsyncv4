#!/usr/bin/env python3
"""Subtree deletion parity, inherited merge rules, limits and dry runs."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

import difftest
import output_test as transfer
from filter_diff_test import RSYNC


class DeletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-delete-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.seed = self.root / 'seed'
        self.source.mkdir(); self.seed.mkdir()
        (self.source / 'keep').write_bytes(b'current')
        (self.seed / 'keep').write_bytes(b'current')
        self.outside = self.root / 'outside'
        self.outside.mkdir()
        (self.outside / 'sentinel').write_bytes(b'untouched')
        for number in range(32):
            branch = self.seed / f'stale-{number:03}'
            branch.mkdir()
            for sub in range(4):
                leaf = branch / f'sub-{sub}'
                leaf.mkdir()
                for index in range(4): (leaf / f'file-{index}').write_bytes(b'stale')
            (branch / 'outside-link').symlink_to(self.outside)
            (branch / 'protected').write_bytes(b'protected')
        for path in [self.source, self.seed, *self.source.rglob('*'), *self.seed.rglob('*')]:
            os.utime(path, ns=(1700000000000000000, 1700000000000000000), follow_symlinks=False)
        self.env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')

    def compare(self, direction, flags):
        expected, actual = self.root / 'expected', self.root / 'actual'
        for target in (expected, actual):
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(self.seed, target, symlinks=True)
        before_source = difftest.snapshot(str(self.source))
        before_outside = difftest.snapshot(str(self.outside))
        before_target = difftest.snapshot(str(actual))
        begin = time.time_ns() - 2_000_000_000
        outputs = []
        for native, target in ((False, expected), (True, actual)):
            binary = str(transfer.BINARY) if native else RSYNC
            command = [binary, '-ai', *flags]
            if native: command += ['--no-fallback', '--no-clone', '-j4']
            source, destination = str(self.source) + '/', str(target) + '/'
            if direction != 'local':
                command += ['-e', shlex.quote(str(transfer.REPO / 'tests/fakessh.sh')),
                            '--rsync-path=' + shlex.quote(binary)]
                if direction == 'push': destination = 'fake:' + destination
                else: source = 'fake:' + source
            result = subprocess.run(command + [source, destination], env=self.env,
                                    capture_output=True, timeout=30)
            outputs.append((result.returncode, sorted(line for line in result.stdout.splitlines()
                                                     if len(line) >= 12 and line[11:12] == b' ')))
        self.assertEqual(outputs[1], outputs[0])
        differences = difftest.compare(difftest.snapshot(str(expected)), difftest.snapshot(str(actual)),
                                       window=(begin, time.time_ns() + 2_000_000_000))
        self.assertFalse(differences, '\n'.join(differences))
        self.assertEqual(difftest.snapshot(str(self.source)), before_source)
        self.assertEqual(difftest.snapshot(str(self.outside)), before_outside)
        if '-n' in flags: self.assertEqual(difftest.snapshot(str(actual)), before_target)

    def test_many_subtrees_local_push_pull_and_delete_after(self):
        for direction in ('local', 'push', 'pull'):
            for deletion in ('--delete', '--delete-after'):
                with self.subTest(direction=direction, deletion=deletion):
                    self.compare(direction, [deletion])

    def test_nested_receiver_merge_protection(self):
        # A parent merge file can itself disappear, but its rules must still
        # protect descendants for all sibling tasks.
        (self.seed / '.rules').write_text('P protected\n')
        for direction in ('local', 'push', 'pull'):
            for deletion in ('--delete', '--delete-after'):
                with self.subTest(direction=direction, deletion=deletion):
                    self.compare(direction, [deletion, '--filter=: .rules'])

    def test_finite_limits_retain_serial_selection(self):
        for direction in ('local', 'push', 'pull'):
            for limit in (0, 1, 5, 40):
                with self.subTest(direction=direction, limit=limit):
                    self.compare(direction, ['--delete', '--max-delete=' + str(limit)])

    def test_dry_runs_leave_destination_unchanged(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                self.compare(direction, ['--delete', '-n'])


if __name__ == '__main__': unittest.main()
