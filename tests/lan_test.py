#!/usr/bin/env python3
"""Disposable-directory LAN smoke check. Never uploads or installs a helper.

XSYNC_LAN_HOST=user@host python3 tests/lan_test.py -v
"""
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xs')).resolve()
HOST = os.environ.get('XSYNC_LAN_HOST')
NATIVE = os.environ.get('XSYNC_LAN_NATIVE') == '1'
SSH = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=8']


@unittest.skipUnless(HOST, 'set XSYNC_LAN_HOST to an authorized SSH target')
class LANTests(unittest.TestCase):
    def remote(self, code, *args):
        result = subprocess.run([*SSH, HOST, shlex.join(['python3', '-c', code, *map(str, args)])],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_missing_helper_fallback(self):
        if NATIVE:
            self.skipTest('native checklist selected')
        helper = self.remote("import shutil; print(shutil.which('xs') or '')")
        if helper:
            self.skipTest('remote xsync already installed; use the native LAN checklist')
        remote_root = self.remote("import tempfile; print(tempfile.mkdtemp(prefix='xsync-lan-'))")
        try:
            with tempfile.TemporaryDirectory(prefix='xsync-lan-') as tmp:
                root = pathlib.Path(tmp)
                source = root / 'source with spaces'
                source.mkdir()
                (source / 'file with spaces').write_bytes(os.urandom(2 * 1024 * 1024))
                (source / 'link').symlink_to('file with spaces')
                target = HOST + ':' + remote_root + '/destination with spaces/'
                rsh = shlex.join(SSH)
                command = [str(BINARY), '-a', '-e', rsh, str(source) + '/', target]
                strict = subprocess.run([*command[:1], '--no-fallback', *command[1:]],
                                        capture_output=True, timeout=20)
                self.assertEqual(strict.returncode, 127, strict.stderr)
                self.assertNotIn(b'falling back', strict.stderr)
                self.assertEqual(self.remote('import os,sys; print(os.listdir(sys.argv[1]))', remote_root), '[]')
                push = subprocess.run(command, capture_output=True, timeout=25)
                self.assertEqual(push.returncode, 0, push.stderr)
                self.assertEqual(push.stderr.count(b'falling back'), 1)
                dest = root / 'pulled back'
                pull = subprocess.run([str(BINARY), '-a', '-e', rsh, target, str(dest) + '/'],
                                      capture_output=True, timeout=25)
                self.assertEqual(pull.returncode, 0, pull.stderr)
                self.assertEqual(pull.stderr.count(b'falling back'), 1)
                self.assertEqual(hashlib.sha256((source / 'file with spaces').read_bytes()).digest(),
                                 hashlib.sha256((dest / 'file with spaces').read_bytes()).digest())
                self.assertEqual((dest / 'link').readlink(), (source / 'link').readlink())
                self.assertEqual((dest / 'file with spaces').stat().st_mtime_ns,
                                 (source / 'file with spaces').stat().st_mtime_ns)
                platform = self.remote("import os,platform,json; print(json.dumps({'system':platform.system(),"
                                       "'machine':platform.machine(),'host':platform.node()}))")
                print('\nLAN fallback push/pull verified: ' + platform, flush=True)
        finally:
            self.remote('import shutil,sys; shutil.rmtree(sys.argv[1])', remote_root)

    @unittest.skipUnless(NATIVE, 'set XSYNC_LAN_NATIVE=1 after explicit installation')
    def test_native_lan_checklist(self):
        remote_root = self.remote("import tempfile; print(tempfile.mkdtemp(prefix='xsync-native-lan-'))")
        try:
            # SSH adds a random suffix to ControlPath; macOS's default temp
            # prefix alone can consume most of the Unix socket path limit.
            with tempfile.TemporaryDirectory(dir='/tmp', prefix='xsync native lan ') as tmp:
                root = pathlib.Path(tmp)
                source = root / 'source with spaces'
                source.mkdir()
                (source / 'sub').mkdir()
                for i in range(100): (source / 'sub' / str(i)).write_bytes(str(i).encode() * 1000)
                (source / 'file with spaces').write_bytes(os.urandom(2 * 1024 * 1024))
                (source / 'straße').write_text('unicode file')
                (source / 'link').symlink_to('file with spaces')
                socket = root / 'master socket'
                control = [*SSH, '-oControlMaster=auto', '-oControlPersist=30', '-S', str(socket)]
                rsh = shlex.join(control)
                target = HOST + ':' + remote_root + '/destination with spaces/'
                flags = [str(BINARY), '--no-fallback', '-az', '--delete', '--progress', '-e', rsh]
                try:
                    for _ in range(2):
                        result = subprocess.run([*flags, str(source) + '/', target], capture_output=True, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertNotIn(b'falling back', result.stderr)
                    master = subprocess.run([*control, '-O', 'check', HOST], capture_output=True, timeout=10)
                    self.assertEqual(master.returncode, 0, master.stderr)
                    self.assertIn(b'Master running', master.stderr)
                    (source / 'sub/0').unlink()
                    (source / 'new file').write_bytes(b'updated source')
                    self.remote("import pathlib,sys; (pathlib.Path(sys.argv[1])/'destination with spaces/orphan').write_text('delete this')", remote_root)
                    result = subprocess.run([*flags, str(source) + '/', target], capture_output=True, timeout=25)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    pulled = root / 'pulled'
                    for _ in range(2):
                        result = subprocess.run([*flags, target, str(pulled) + '/'], capture_output=True, timeout=25)
                        self.assertEqual(result.returncode, 0, result.stderr)
                    snapshot = '''import pathlib,hashlib,json,sys
p=pathlib.Path(sys.argv[1]); tree={}
for f in p.rglob('*'):
 key=str(f.relative_to(p))
 if f.is_symlink(): tree[key]=['link',str(f.readlink())]
 elif f.is_file(): tree[key]=['file',hashlib.sha256(f.read_bytes()).hexdigest(),f.stat().st_mode&4095,f.stat().st_mtime_ns]
 elif f.is_dir(): tree[key]=['dir',f.stat().st_mode&4095,f.stat().st_mtime_ns]
print(json.dumps(tree,sort_keys=True))
'''
                    expected = json.loads(subprocess.check_output(['python3', '-c', snapshot, str(source)]))
                    actual = json.loads(subprocess.check_output(['python3', '-c', snapshot, str(pulled)]))
                    remote_tree = json.loads(self.remote(snapshot, remote_root + '/destination with spaces'))
                    self.assertEqual(expected, actual)
                    self.assertEqual(expected, remote_tree)
                    for stream, code in (('stdout', 2), ('stderr', 0)):
                        command = "printf 'LAN shell banner\\n'" + (' >&2' if stream == 'stderr' else '')
                        command += '; exec "$HOME/.local/bin/xs"'
                        result = subprocess.run([*flags, '--rsync-path=' + command, str(source) + '/', target],
                                                capture_output=True, timeout=25)
                        self.assertEqual(result.returncode, code, result.stderr)
                        self.assertNotIn(b'falling back', result.stderr)
                        self.assertIn(b'remote shell is printing text' if code else b'LAN shell banner', result.stderr)
                    print('\nNative LAN push/pull, update/delete, ControlMaster, banner/stderr and metadata verified: ' + HOST,
                          flush=True)
                finally:
                    subprocess.run([*control, '-O', 'exit', HOST], capture_output=True, timeout=10)
        finally:
            self.remote('import shutil,sys; shutil.rmtree(sys.argv[1])', remote_root)


if __name__ == '__main__':
    unittest.main()
