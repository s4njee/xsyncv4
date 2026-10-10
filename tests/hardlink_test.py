#!/usr/bin/env python3
"""Native hard-link topology, metadata and output against rsync, including SSH."""
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
from output_test import BINARY, HOST, RSH

REPO = pathlib.Path(__file__).resolve().parent.parent
REFERENCE = '/opt/homebrew/bin/rsync' if pathlib.Path('/opt/homebrew/bin/rsync').exists() else shutil.which('rsync')
SNAPSHOT = '''import pathlib,sys,json,stat,hashlib
root=pathlib.Path(sys.argv[1]); result={}; groups={}
for path in sorted(root.rglob('*')):
 s=path.lstat(); rel=str(path.relative_to(root)); kind=stat.S_IFMT(s.st_mode)
 record=[kind,s.st_mode&4095,s.st_mtime_ns]
 if stat.S_ISREG(s.st_mode): record.append(hashlib.sha256(path.read_bytes()).hexdigest())
 elif stat.S_ISLNK(s.st_mode): record.append(str(path.readlink()))
 result[rel]=record
 if not stat.S_ISDIR(s.st_mode): groups.setdefault((s.st_dev,s.st_ino),[]).append(rel)
for group in groups.values():
 for rel in group: result[rel].append(group if len(group)>1 else [])
print(json.dumps(result,sort_keys=True))
'''

class HardlinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync hard links ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'sub').mkdir()
        (self.source / 'a').write_bytes(b'0123456789abcdef' * 140000)
        for name in ('m', 'z', 'sub/q'):
            os.link(self.source / 'a', self.source / name)
        (self.source / 'sym').symlink_to('a')
        os.link(self.source / 'sym', self.source / 'sym2', follow_symlinks=False)
        os.mkfifo(self.source / 'pipe')
        os.link(self.source / 'pipe', self.source / 'pipe2')
        for path in [*self.source.rglob('*'), self.source]:
            os.utime(path, ns=(1000000000000000000, 1000000000000000000), follow_symlinks=False)
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)
            subprocess.run([REFERENCE, '-aH', '-e', RSH, str(self.source) + '/', HOST + ':' + str(self.source) + '/'], check=True, capture_output=True)

    def copy(self, binary, direction, target, flags=()):
        source, dest = str(self.source) + '/', str(self.root / target) + '/'
        command = [str(binary), '-aH', '-j8' if binary == BINARY else '-i', *flags]
        if binary == BINARY: command += ['--no-fallback', '-i']
        if direction != 'local':
            peer = '/usr/local/bin/xs' if HOST and binary == BINARY else '/usr/bin/rsync' if HOST else str(binary)
            command += ['-e', RSH, '--rsync-path=' + shlex.quote(peer)]
            if direction == 'push': dest = (HOST or 'fake') + ':' + dest
            else: source = (HOST or 'fake') + ':' + source
        result = subprocess.run(command + [source, dest], capture_output=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        return sorted(line for line in result.stdout.splitlines() if len(line) > 11 and line[11:12] == b' ' and line[:1] in b'<>ch.')

    def snapshot(self, direction, target):
        path = self.root / target
        if HOST and direction == 'push':
            from ssh_test import remote_json
            return remote_json(SNAPSHOT, path)
        return json.loads(subprocess.check_output(['python3', '-c', SNAPSHOT, str(path)]))

    def compare(self, direction, suffix, flags=(), repeat=2):
        reference, actual = suffix + '-ref', suffix + '-native'
        for run in range(repeat):
            expected = self.copy(REFERENCE, direction, reference, flags)
            got = self.copy(BINARY, direction, actual, flags)
            self.assertEqual(got, expected, (direction, flags, run))
            self.assertEqual(self.snapshot(direction, actual), self.snapshot(direction, reference))

    def test_fresh_existing_and_compressed_large_groups(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (('--no-clone',), ()) if direction == 'local' else ((),):
                # --no-clone is an xsync option; apply it only to its invocation.
                suffix = direction + ('-bytes' if flags else '-default')
                for run in range(2):
                    expected = self.copy(REFERENCE, direction, suffix + '-ref', ['-z'])
                    got = self.copy(BINARY, direction, suffix + '-native', ['-z', *flags])
                    self.assertEqual(got, expected)
                    self.assertEqual(self.snapshot(direction, suffix + '-native'), self.snapshot(direction, suffix + '-ref'))

    def test_dry_run_has_no_side_effects(self):
        for direction in ('local', 'push', 'pull'):
            self.compare(direction, direction + '-dry', ['-n'], repeat=1)
            self.assertEqual(self.snapshot(direction, direction + '-dry-native'), {})

    def test_unchanged_repeated_itemize_and_quiet(self):
        for direction in ('local', 'push', 'pull'):
            self.compare(direction, direction + '-unchanged', repeat=1)
            expected = self.copy(REFERENCE, direction, direction + '-unchanged-ref', ['-i'])
            actual = self.copy(BINARY, direction, direction + '-unchanged-native', ['-i'])
            self.assertEqual(actual, expected)
            self.compare(direction, direction + '-quiet', ['-q'], repeat=1)

    def test_inplace_keeps_groups(self):
        for direction in ('local', 'push', 'pull'):
            self.compare(direction, direction + '-inplace', ['--inplace', '--ignore-times'])

if __name__ == '__main__':
    unittest.main()
