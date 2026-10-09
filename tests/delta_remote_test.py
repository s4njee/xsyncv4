#!/usr/bin/env python3
"""Actual bidirectional wire cost versus rsync, including real SSH in the rig."""
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

from delta_test import BINARY, REPO, MIB
from ssh_test import HOST, RSH as SSH_RSH, remote_code, remote_json

REFERENCE = '/opt/homebrew/bin/rsync' if pathlib.Path('/opt/homebrew/bin/rsync').exists() else shutil.which('rsync')
RSH = SSH_RSH if HOST else str(REPO / 'tests/fakessh.sh')
SNAPSHOT = '''import pathlib,sys,hashlib,json
p=pathlib.Path(sys.argv[1]); s=p.stat(); h=hashlib.sha256()
with p.open('rb') as f:
 while b:=f.read(1<<20): h.update(b)
print(json.dumps([s.st_size,s.st_mode&4095,s.st_mtime_ns,h.hexdigest(),s.st_ino]))
'''
FIXTURE = '''import pathlib,sys,random,os,shutil
root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True,exist_ok=True); size=int(sys.argv[2])
basis=root/'basis'; source=root/'source'; rng=random.Random(84492)
with basis.open('wb') as f:
 block=rng.randbytes(4<<20)
 for n in range(size//len(block)): f.write(block)
shutil.copyfile(basis,source)
with source.open('r+b') as f:
 for off in (size//3+731,size//2+29,size-8711): f.seek(off); f.write(b'edited database record')
source.chmod(0o640); os.utime(source,ns=(1600000000123456789,)*2)
os.utime(basis,ns=(1500000000000000000,)*2)
'''

class RemoteDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync delta wire ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        if HOST:
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def snapshot(self, path, remote=False):
        if remote: return remote_json(SNAPSHOT, path)
        return json.loads(subprocess.check_output(['python3', '-c', SNAPSHOT, str(path)]))

    def prepare(self, size):
        subprocess.run(['python3', '-c', FIXTURE, str(self.root), str(size)], check=True)
        if HOST: remote_code(FIXTURE, self.root, size)

    def seed(self, path, remote=False):
        if remote:
            remote_code('import shutil,sys; shutil.copyfile(sys.argv[1],sys.argv[2])', self.root / 'basis', path)
        else: shutil.copyfile(self.root / 'basis', path)

    def run_copy(self, binary, direction, path, flags=()):
        native = pathlib.Path(binary) == BINARY
        source, destination = str(self.root / 'source'), str(path)
        if direction == 'push': destination = (HOST or 'fake') + ':' + destination
        else: source = (HOST or 'fake') + ':' + source
        peer = ('/usr/local/bin/xsync' if native else '/usr/bin/rsync') if HOST else str(binary)
        command = [str(binary), '-a', '--stats', '-e', RSH, '--rsync-path=' + shlex.quote(peer), *flags]
        if native: command += ['--no-fallback', '--out-format=%i|%n|%b', '-j4']
        result = subprocess.run(command + [source, destination], capture_output=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def wire(self, result):
        fields = [re.search(rb'Total bytes ' + field + rb': ([\d,]+)', result.stdout) for field in (b'sent', b'received')]
        self.assertTrue(all(fields), result.stdout)
        return sum(int(field[1].replace(b',', b'')) for field in fields)

    def budget(self, size, flags=()):
        self.prepare(size)
        expected = self.snapshot(self.root / 'source')[:4]
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction, size=size, flags=flags):
                actual, reference = self.root / 'native', self.root / 'reference'
                remote = bool(HOST and direction == 'push')
                self.seed(actual, remote), self.seed(reference, remote)
                native = self.run_copy(BINARY, direction, actual, flags)
                rsync = self.run_copy(REFERENCE, direction, reference, flags)
                self.assertEqual(self.snapshot(actual, remote)[:4], expected)
                self.assertEqual(self.snapshot(reference, remote)[:4], expected)
                cost, baseline = self.wire(native), self.wire(rsync)
                self.assertLessEqual(cost, baseline * 1.2, (native.stdout, rsync.stdout))
                self.assertLess(cost, size // 8)
                self.assertIn(b'Delta matched data:', native.stdout)
                print(f'\n{direction} {size // MIB} MiB {flags}: total wire xsync={cost}, rsync={baseline} ({cost/baseline:.3f}x)', flush=True)

    def test_edited_large_file_wire_budget(self): self.budget(64 * MIB)
    def test_compressed_wire_budget(self): self.budget(64 * MIB, ['-z'])
    def test_inplace_wire_budget(self): self.budget(64 * MIB, ['--inplace'])

    @unittest.skipUnless(os.environ.get('XSYNC_DELTA_LARGE'), 'set XSYNC_DELTA_LARGE=1 for the 2 GiB acceptance fixture')
    def test_two_gib_wire_budget(self): self.budget(2 * 1024 * MIB)

    def test_whole_file_disables_remote_delta(self):
        self.prepare(4 * MIB)
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                target = self.root / 'whole'
                remote = bool(HOST and direction == 'push')
                self.seed(target, remote)
                result = self.run_copy(BINARY, direction, target, ['-W'])
                self.assertGreater(self.wire(result), 4 * MIB)
                self.assertIn(b'Delta matched data: 0 bytes', result.stdout)
                self.assertEqual(self.snapshot(target, remote)[:4], self.snapshot(self.root / 'source')[:4])

if __name__ == '__main__': unittest.main()
