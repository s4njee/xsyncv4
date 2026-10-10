#!/usr/bin/env python3
"""Personal-default precedence, quoting, fallback and server isolation."""
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import unittest

from progress_test import capture

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()


class DefaultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync defaults ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.env = {key: value for key, value in os.environ.items()
                    if key not in ('XSYNC_OPTS', 'XSYNC_RSH', 'RSYNC_RSH', 'XSYNC_CONFIG', 'XSYNC_FALLBACK', 'XSYNC_PROGRESS', 'XDG_CONFIG_HOME')}
        self.env['HOME'] = str(self.root)
        self.config = self.root / '.config/xsync/config'
        self.config.parent.mkdir(parents=True)
        self.source = self.root / 'source'
        self.source.write_bytes(b'personal defaults fixture')
        self.dest = self.root / 'destination'

    def run_xsync(self, *args, **kwargs):
        return subprocess.run([str(BINARY), *args], env=self.env, capture_output=True, timeout=10, **kwargs)

    def copy(self, *flags):
        result = self.run_xsync('--no-fallback', '-a', *flags, str(self.source), str(self.dest))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_config_environment_and_flags(self):
        self.config.write_text('# Personal defaults\n--dry-run\n--jobs=2\n')
        self.copy()
        self.assertFalse(self.dest.exists())
        self.env['XSYNC_OPTS'] = '--no-dry-run --jobs=3'
        self.copy()
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.dest.unlink()
        self.copy('--dry-run', '--jobs=1')
        self.assertFalse(self.dest.exists())
        self.env['XSYNC_OPTS'] = '--dry-run'
        self.copy('--no-dry-run')
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def terminal_copy(self, *flags):
        self.env['TERM'] = 'xterm-256color'
        code, output = capture([str(BINARY), '--no-fallback', '-a', *flags,
                                str(self.source), str(self.dest)], env=self.env)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())
        self.dest.unlink()
        return output

    def test_progress_terminal_default_and_script_silence(self):
        output = self.terminal_copy()
        self.assertIn(b'\x1b[?25l', output)
        self.assertIn(b'\x1b[?25h', output)
        self.assertIn(b'1 file', output)
        self.assertEqual(self.terminal_copy('--no-progress'), b'')
        self.assertEqual(self.terminal_copy('-q'), b'')
        self.assertEqual(self.terminal_copy('--progress', '-q'), b'')
        result = self.copy()
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'')

    def test_progress_environment_and_config_precedence(self):
        self.config.write_text('--no-progress\n')
        self.assertEqual(self.terminal_copy(), b'')
        self.env['XSYNC_OPTS'] = '--progress'
        self.assertIn(b'1 file', self.terminal_copy())
        self.env['XSYNC_PROGRESS'] = '0'
        self.assertEqual(self.terminal_copy(), b'')
        self.assertIn(b'1 file', self.terminal_copy('--progress'))
        self.env['XSYNC_PROGRESS'] = '1'
        self.assertIn(b'1 file', self.terminal_copy())
        self.assertEqual(self.terminal_copy('--no-progress'), b'')
        self.env['XSYNC_PROGRESS'] = 'auto'
        self.env['XSYNC_OPTS'] = ''
        self.assertEqual(self.terminal_copy(), b'')
        self.config.unlink()
        self.assertIn(b'1 file', self.terminal_copy())
        self.env['XSYNC_PROGRESS'] = '1'
        result = self.copy()
        self.assertIn(b'1 file', result.stderr)
        self.assertNotIn(b'\x1b[', result.stderr)

    def test_invalid_progress_environment_and_control_isolation(self):
        self.env['XSYNC_PROGRESS'] = 'yes'
        result = self.run_xsync('-a', str(self.source), str(self.dest))
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'XSYNC_PROGRESS must be 0, 1, or auto', result.stderr)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.run_xsync('--help').returncode, 0)
        self.assertEqual(self.run_xsync('--version').returncode, 0)
        server = self.run_xsync('--server', input=b'')
        self.assertEqual(server.returncode, 2)
        self.assertNotIn(b'XSYNC_PROGRESS', server.stderr)

    def test_paths_and_shell_word_quoting(self):
        source = self.root / 'tree'
        source.mkdir()
        (source / 'space name').write_bytes(b'skip')
        (source / 'keep').write_bytes(b'keep')
        self.config.write_text("--exclude 'space name'\n")
        self.env['XSYNC_OPTS'] = '--exclude="other name"'
        result = self.run_xsync('--no-fallback', '-a', str(source) + '/', str(self.dest))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['keep'])
        self.dest.rename(self.root / 'first-result')
        result = self.run_xsync('--no-fallback', '-a', '--filter=!', str(source) + '/', str(self.dest))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ['keep', 'space name'])

    def test_remote_shell_precedence(self):
        capture = self.root / 'shell.json'
        shells = {}
        for label in ('config', 'options', 'rsync', 'xsync', 'flags'):
            path = self.root / (label + ' shell')
            path.write_text('#!/usr/bin/env python3\nimport sys,json\nfrom pathlib import Path\n'
                            + 'Path(' + repr(str(capture)) + ').write_text(json.dumps([' + repr(label) + ',sys.argv[1:]]))\n'
                            + 'sys.exit(255)\n')
            path.chmod(0o755)
            shells[label] = shlex.join([str(path), 'value with spaces'])
        self.config.write_text('--rsh ' + shlex.quote(shells['config']) + '\n')
        def check(label, *flags):
            capture.unlink(missing_ok=True)
            result = self.run_xsync('--no-fallback', '-a', *flags, str(self.source), 'user@[::1]:dest')
            self.assertEqual(result.returncode, 255, result.stderr)
            selected, args = json.loads(capture.read_text())
            self.assertEqual(selected, label)
            self.assertEqual(args[:4], ['value with spaces', '-l', 'user', '::1'])
        check('config')
        self.env['XSYNC_OPTS'] = '--rsh=' + shlex.quote(shells['options'])
        check('options')
        self.env['RSYNC_RSH'] = shells['rsync']
        check('rsync')
        self.env['XSYNC_RSH'] = shells['xsync']
        check('xsync')
        check('flags', '-e', shells['flags'])
        check('flags', '--rsh=' + shells['flags'])
        result = self.run_xsync('--no-fallback', '-a', '-e', '', str(self.source), 'host:dest')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(b'empty remote shell command', result.stderr)

    def test_config_selection(self):
        self.config.write_text('--dry-run\n')
        xdg = self.root / 'xdg'
        (xdg / 'xsync').mkdir(parents=True)
        (xdg / 'xsync/config').write_text('--no-dry-run\n')
        self.env['XDG_CONFIG_HOME'] = str(xdg)
        self.copy()
        self.assertTrue(self.dest.exists())
        self.dest.unlink()
        self.env['XSYNC_CONFIG'] = str(self.config)
        self.copy()
        self.assertFalse(self.dest.exists())
        self.env['XSYNC_CONFIG'] = ''
        self.copy()
        self.assertTrue(self.dest.exists())
        self.env['XSYNC_CONFIG'] = str(self.root / 'missing config')
        result = self.run_xsync('-a', str(self.source), str(self.dest))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(b'cannot read defaults file', result.stderr)

    def test_invalid_defaults_and_control_invocations(self):
        for value in ("--rsh 'unterminated", '--rsh', '--', '/unexpected/path', '--install host',
                      '--server', '--help', '--version', '-aV'):
            with self.subTest(value=value):
                self.env['XSYNC_OPTS'] = value
                result = self.run_xsync('-a', str(self.source), str(self.dest))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(self.dest.exists())
                self.assertEqual(self.run_xsync('--help').returncode, 0)
                self.assertEqual(self.run_xsync('--version').returncode, 0)
                # The server bypasses even malformed defaults, then rejects EOF.
                server = self.run_xsync('--server', input=b'')
                self.assertEqual(server.returncode, 2, server.stderr)
                self.assertNotIn(b'XSYNC_OPTS', server.stderr)

    def test_server_ignores_client_defaults(self):
        self.config.write_text('--dry-run\n--rsh ignored-config-shell\n')
        self.env['XSYNC_OPTS'] = '--dry-run'
        result = self.run_xsync('--no-fallback', '-a', '--no-dry-run',
                                '-e', shlex.quote(str(REPO / 'tests/fakessh.sh')),
                                '--rsync-path=' + shlex.quote(str(BINARY)), str(self.source), 'host:' + str(self.dest))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def test_fallback_keeps_effective_defaults(self):
        capture = self.root / 'fallback.json'
        commands = self.root / 'bin'
        commands.mkdir()
        rsync = commands / 'rsync'
        rsync.write_text('#!/usr/bin/env python3\nimport sys,json\nfrom pathlib import Path\n'
                         + 'Path(' + repr(str(capture)) + ').write_text(json.dumps(sys.argv[1:]))\n'
                         + 'sys.exit(37)\n')
        rsync.chmod(0o755)
        self.env['PATH'] = str(commands) + ':' + os.environ['PATH']
        self.config.write_text('--fallback --jobs=2 --exclude="space name"\n')
        self.env['XSYNC_FALLBACK'] = '0'
        result = self.run_xsync('-b', str(self.source), str(self.dest))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(capture.exists())
        self.env['XSYNC_OPTS'] = '--jobs=3 --no-clone'
        result = self.run_xsync('--fallback', '-b', str(self.source), str(self.dest))
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(json.loads(capture.read_text()), ['--exclude=space name', '-b', str(self.source), str(self.dest)])
        self.assertEqual(result.stderr.count(b'falling back to rsync'), 1)


if __name__ == '__main__':
    unittest.main()
