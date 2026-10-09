#!/usr/bin/env python3
"""Remote helper precedence, with a real sshd and an isolated remote home."""
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest
import ssh_test
from ssh_test import BINARY, HOST, remote_code, remote_json


@unittest.skipUnless(HOST, 'run via tests/ssh-rig.sh')
class LookupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ssh_test.SSHTests.setUpClass()

    def test_search_order_and_explicit_override(self):
        with tempfile.TemporaryDirectory(dir='/rig', prefix="lookup 'spaces ") as tmp:
            root = pathlib.Path(tmp)
            source = root / 'source'
            source.write_bytes(b'lookup test' * 100000)
            remote_code('''import pathlib,sys
root=pathlib.Path(sys.argv[1]); (root/'bin').mkdir(parents=True); (root/'bin/sh').symlink_to('/bin/sh')
(root/'home/.local/bin').mkdir(parents=True)
for relative,tag in [('bin/xsync','path'),('home/.local/bin/xsync','home'),("env 'program",'env'),('local program','local')]:
 p=root/relative; p.write_text('#!/bin/sh\\necho LOOKUP:'+tag+' >&2\\nexec /usr/local/bin/xsync "$@"\\n'); p.chmod(0o755)
''', root)
            try:
                rsh = shlex.join([sys.executable, '/work/tests/rig/lookup_shell.py'])
                for case in ('path', 'home', 'env', 'local', 'explicit', 'missing'):
                    with self.subTest(case=case):
                        if case == 'home':
                            remote_code("import pathlib,sys; (pathlib.Path(sys.argv[1])/'bin/xsync').unlink()", root)
                        if case == 'env':
                            remote_code("import pathlib,sys; (pathlib.Path(sys.argv[1])/'home/.local/bin/xsync').unlink()", root)
                        config = {'PATH': str(root / 'bin'), 'HOME': str(root / 'home'),
                                  'XSYNC_REMOTE_PATH': str(root / "env 'program")}
                        env = dict(os.environ, XSYNC_TEST_LOOKUP=json.dumps(config))
                        env.pop('XSYNC_REMOTE_PATH', None)
                        flags = []
                        if case == 'local': env['XSYNC_REMOTE_PATH'] = str(root / 'local program')
                        if case == 'explicit': flags = ['--rsync-path=' + shlex.quote(str(root / "env 'program"))]
                        if case == 'missing':
                            config['XSYNC_REMOTE_PATH'] = str(root / 'absent program')
                            env['XSYNC_TEST_LOOKUP'] = json.dumps(config)
                        dest = root / ('out-' + case)
                        result = subprocess.run([BINARY, '--no-fallback', '-a', '-e', rsh, *flags,
                                                 str(source), HOST + ':' + str(dest)], env=env,
                                                capture_output=True, timeout=15)
                        self.assertEqual(result.returncode, 127 if case == 'missing' else 0, result.stderr)
                        if case == 'missing':
                            self.assertNotIn(b'LOOKUP:', result.stderr)
                            self.assertFalse(remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', dest))
                        else:
                            expected = 'env' if case == 'explicit' else case
                            self.assertEqual(result.stderr.strip(), ('LOOKUP:' + expected).encode())
                            actual = remote_code('import pathlib,hashlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())', dest)
                            self.assertEqual(actual.strip(), hashlib.sha256(source.read_bytes()).hexdigest())
            finally:
                remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])', root)


if __name__ == '__main__':
    unittest.main()
