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
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()
HOST = os.environ.get('XSYNC_LAN_HOST')
SSH = ['ssh', '-oBatchMode=yes', '-oConnectTimeout=8']


@unittest.skipUnless(HOST, 'set XSYNC_LAN_HOST to an authorized SSH target')
class LANTests(unittest.TestCase):
    def remote(self, code, *args):
        result = subprocess.run([*SSH, HOST, shlex.join(['python3', '-c', code, *map(str, args)])],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_missing_helper_fallback(self):
        helper = self.remote("import shutil; print(shutil.which('xsync') or '')")
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


if __name__ == '__main__':
    unittest.main()
