#!/usr/bin/env python3
"""Installer over actual SSH, in the disposable server container only."""
import hashlib
import os
import pathlib
import subprocess
import tempfile
import unittest
import ssh_test
from ssh_test import BINARY, HOST, RSH, remote_code, remote_json


@unittest.skipUnless(HOST, 'run via tests/ssh-rig.sh')
class SSHInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ssh_test.SSHTests.setUpClass()

    def test_explicit_install_and_version_guard(self):
        initial = remote_json("import pathlib,json; p=pathlib.Path.home()/'.local/bin/xsync'; print(json.dumps(p.exists()))")
        self.assertFalse(initial, 'test requires the disposable rig server without a user-local xsync')
        try:
            with tempfile.TemporaryDirectory(dir='/rig', prefix='release files ') as tmp:
                releases = pathlib.Path(tmp)
                data = pathlib.Path(BINARY).read_bytes()
                for name in ('xsync-linux-amd64', 'xsync-linux-arm64'):
                    (releases / name).write_bytes(data)
                command = [BINARY, '-e', RSH, '--install', HOST]
                env = dict(os.environ, XSYNC_RELEASE_DIR=str(releases))
                result = subprocess.run(command, capture_output=True, env=env, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = remote_code("import pathlib,hashlib; p=pathlib.Path.home()/'.local/bin/xsync'; print(hashlib.sha256(p.read_bytes()).hexdigest())")
                self.assertEqual(actual, hashlib.sha256(data).hexdigest() + '\n')
                remote_code("import pathlib; p=pathlib.Path.home()/'.local/bin/xsync'; p.write_text('#!/bin/sh\\necho \\\"xsync  version 99.0.0  protocol version 3\\\"\\n'); p.chmod(0o755)")
                newer = remote_code("import pathlib; print((pathlib.Path.home()/'.local/bin/xsync').read_text())")
                result = subprocess.run(command, capture_output=True, env=env, timeout=15)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn(b'refusing to overwrite', result.stderr)
                self.assertEqual(remote_code("import pathlib; print((pathlib.Path.home()/'.local/bin/xsync').read_text())"), newer)
                result = subprocess.run([*command, '--force'], capture_output=True, env=env, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = remote_code("import pathlib,hashlib; p=pathlib.Path.home()/'.local/bin/xsync'; print(hashlib.sha256(p.read_bytes()).hexdigest())")
                self.assertEqual(actual, hashlib.sha256(data).hexdigest() + '\n')
                remote_code("import pathlib,subprocess; p=pathlib.Path.home()/'.local/bin/xsync'; subprocess.run([str(p),'--version'],check=True); assert not list(p.parent.glob('.xsync-install.*'))")
        finally:
            remote_code("import pathlib; (pathlib.Path.home()/'.local/bin/xsync').unlink(missing_ok=True)")


if __name__ == '__main__':
    unittest.main()
