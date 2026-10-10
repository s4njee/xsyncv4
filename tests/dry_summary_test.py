#!/usr/bin/env python3
"""Dry-run plans are visible and exact, with no destination mutations."""
import json
import os
import pathlib
import shlex
import subprocess
import sys
import unittest

import output_test as fixture
from output_test import BINARY, HOST
from io_limit_test import PREAMBLE
from progress_test import ENV

SNAPSHOT = '''import pathlib,sys,json,hashlib
p=pathlib.Path(sys.argv[1]); rows=[]
for f in sorted(p.rglob('*')) if p.exists() else []:
 s=f.lstat(); rows.append([str(f.relative_to(p)),s.st_mode,s.st_size,s.st_mtime_ns,s.st_ino,
                         f.readlink().as_posix() if f.is_symlink() else hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None])
print(json.dumps(rows))
'''


class DrySummaryTests(unittest.TestCase):
    setUp = fixture.OutputTests.setUp
    refresh_remote = fixture.OutputTests.refresh_remote
    run_copy = fixture.OutputTests.run_copy

    @classmethod
    def setUpClass(cls): fixture.OutputTests.setUpClass.__func__(cls)

    def snapshot(self, direction, target):
        if HOST and direction == 'push':
            from ssh_test import remote_code
            return json.loads(remote_code(SNAPSHOT, self.root / target))
        return json.loads(subprocess.check_output([sys.executable, '-c', SNAPSHOT, str(self.root / target)]))

    def test_new_tree_summary_without_verbose(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                before = self.snapshot(direction, direction)
                result = self.run_copy(direction, ['-n'], name=direction)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'would transfer 4 files (19B), delete 0\n')
                self.assertEqual(result.stderr, b'')
                self.assertEqual(self.snapshot(direction, direction), before)

    def test_changed_file_and_recursive_deletion_plan(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                target = 'changed-' + direction
                copied = self.run_copy(direction, name=target)
                self.assertEqual(copied.returncode, 0, copied.stderr)
                code = 'import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/"stale").mkdir(); (p/"stale"/"a").write_bytes(b"a"); (p/"stale"/"b").write_bytes(b"b"); (p/"old").write_bytes(b"old"); (p/"protected").write_bytes(b"protected")'
                if HOST and direction == 'push':
                    from ssh_test import remote_code
                    remote_code(code, self.root / target)
                else: subprocess.run([sys.executable, '-c', code, str(self.root / target)], check=True)
                (self.source / 'a').write_bytes(b'new longer contents')
                if HOST and direction == 'pull': self.refresh_remote()
                before = self.snapshot(direction, target)
                result = self.run_copy(direction, ['-n', '--delete-after', '--exclude=protected', '--stats'], name=target)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.splitlines()[-1], b'would transfer 1 files (19B), delete 4')
                self.assertIn(b'Number of regular files transferred: 1', result.stdout)
                self.assertIn(b'Total transferred file size: 19 bytes', result.stdout)
                self.assertEqual(self.snapshot(direction, target), before)
                (self.source / 'a').write_bytes(b'first')
                if HOST: self.refresh_remote()

    def test_noop_filters_and_quiet(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                copied = self.run_copy(direction, name=direction)
                self.assertEqual(copied.returncode, 0, copied.stderr)
                result = self.run_copy(direction, ['-n', '-c'], name=direction)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'would transfer 0 files (0B), delete 0\n')
                result = self.run_copy(direction, ['-n', '--exclude=*'], name='filtered-' + direction)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'would transfer 0 files (0B), delete 0\n')
                result = self.run_copy(direction, ['-n', '-q'], name='quiet-' + direction)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr, b'')

    def test_legacy_push_requires_totals_unless_quiet(self):
        peer = self.root / 'peer.py'
        peer.write_text(PREAMBLE + '\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var(15))\n'
                        'send(10,b"\\0"*4)\n'
                        'while True:\n t,p=read_frame()\n if t==2: send(3,var(take_var(p)[0])+b"\\0")\n if t==6: break\n'
                        'send(7,b"\\0"*6)\n')
        command = [str(BINARY), '--no-fallback', '-rn', '--numeric-ids', '-e', shlex.join([sys.executable, str(peer)]),
                   '--rsync-path=unused']
        result = subprocess.run(command + [str(self.source) + '/', 'fake:target'], env=ENV, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'peer does not support dry-run transfer totals', result.stderr)
        result = subprocess.run(command + ['-q', str(self.source) + '/', 'fake:target'], env=ENV, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, b'')


if __name__ == '__main__': unittest.main()
