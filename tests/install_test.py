#!/usr/bin/env python3
"""Explicit installer checks in a disposable mock SSH home; no real host writes."""
import hashlib
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xs')).resolve()


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="xsync install 'test ")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.home = self.root / 'remote home'
        self.home.mkdir()
        self.target = self.home / '.local/bin/xs'
        self.releases = self.root / 'release files'
        self.releases.mkdir()
        for name in ('linux-amd64', 'linux-arm64', 'darwin-universal'):
            shutil.copy2(BINARY, self.releases / ('xs-' + name))
        commands = self.root / 'commands'
        commands.mkdir()
        uname = commands / 'uname'
        uname.write_text('#!/bin/sh\ncase "$1" in -s) printf "%s\\n" "$XSYNC_TEST_SYSTEM";; '
                         '-m) printf "%s\\n" "$XSYNC_TEST_ARCH";; esac\n')
        uname.chmod(0o755)
        shell = self.root / 'mock ssh.py'
        shell.write_text('''import os,sys,subprocess
os.environ['HOME']=os.environ['XSYNC_TEST_HOME']
if os.environ.get('XSYNC_TEST_BANNER'): print('a bad shell banner',flush=True)
if os.environ.get('XSYNC_TEST_TRUNCATE') and 'cat >' in sys.argv[-1]:
 data=sys.stdin.buffer.read(100)
 sys.exit(subprocess.run(['/bin/sh','-c',sys.argv[-1]],input=data).returncode)
os.execv('/bin/sh',['sh','-c',sys.argv[-1]])
''')
        self.rsh = shlex.join([sys.executable, str(shell)])
        self.env = dict(os.environ, XSYNC_RELEASE_DIR=str(self.releases), XSYNC_TEST_HOME=str(self.home),
                        XSYNC_TEST_SYSTEM='Linux', XSYNC_TEST_ARCH='aarch64',
                        PATH=str(commands) + ':' + os.environ.get('PATH', '/usr/bin:/bin'))

    def install(self, *args, env=None):
        return subprocess.run([str(BINARY), '-e', self.rsh, '--install', 'user@fixture', *args],
                              env=env or self.env, capture_output=True, timeout=15)

    def fixture_version(self, version):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text('#!/bin/sh\nprintf "%s\\n" "xs  version ' + version + '  protocol version 3"\n')
        self.target.chmod(0o755)
        return self.target.read_bytes()

    def test_architecture_and_fresh_install(self):
        for system, arch, artifact in (('Linux', 'x86_64', 'linux-amd64'), ('Linux', 'aarch64', 'linux-arm64'),
                                       ('Darwin', 'arm64', 'darwin-universal'), ('Darwin', 'x86_64', 'darwin-universal')):
            with self.subTest(system=system, arch=arch):
                if self.target.exists(): self.target.unlink()
                result = self.install(env=dict(self.env, XSYNC_TEST_SYSTEM=system, XSYNC_TEST_ARCH=arch))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(('Installed xs-' + artifact).encode(), result.stdout)
                self.assertEqual(self.target.read_bytes(), BINARY.read_bytes())
                self.assertEqual(self.target.stat().st_mode & 0o777, 0o755)
                self.assertEqual(list(self.target.parent.glob('.xs-install.*')), [])
                version = subprocess.run([str(self.target), '--version'], capture_output=True)
                self.assertEqual(version.returncode, 0)

    def test_newer_version_refusal_and_force(self):
        for version in ('0.2.0', '1.0.0'):
            with self.subTest(version=version):
                previous = self.fixture_version(version)
                result = self.install()
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn(b'refusing to overwrite', result.stderr)
                self.assertEqual(self.target.read_bytes(), previous)
                result = self.install('--force')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.target.read_bytes(), BINARY.read_bytes())

    def test_failed_upload_preserves_existing_binary(self):
        previous = self.fixture_version('0.0.1')
        result = self.install(env=dict(self.env, XSYNC_TEST_TRUNCATE='1'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), previous)
        self.assertEqual(list(self.target.parent.glob('.xs-install.*')), [])

    def test_platform_banner_and_missing_artifact(self):
        for env, code in ((dict(self.env, XSYNC_TEST_ARCH='riscv64'), 4),
                          (dict(self.env, XSYNC_TEST_BANNER='1'), 2),
                          (dict(self.env, XSYNC_RELEASE_DIR=str(self.root / 'missing')), 3)):
            with self.subTest(env=env):
                result = self.install(env=env)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertFalse(self.target.exists())
                self.assertNotIn(b'falling back', result.stderr)

    def test_install_never_runs_during_transfer(self):
        source = self.root / 'source'
        source.write_bytes(b'ordinary local transfer')
        result = subprocess.run([str(BINARY), '-a', str(source), str(self.root / 'dest')],
                                env=self.env, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.target.exists())
        result = self.install(str(source), str(self.root / 'dest'))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
