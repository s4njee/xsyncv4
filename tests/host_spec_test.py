#!/usr/bin/env python3
"""Compare host selection with real rsync and exercise native remote paths."""
import json
import os
import pathlib
import shlex
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xs')).resolve()
RSYNC = shutil.which('rsync')


class HostSpecTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync host specs ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.write_bytes(b'host parser fixture')
        self.capture = self.root / 'argv.json'
        self.shell = self.root / 'capture shell'
        self.shell.write_text('#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n'
                              + 'Path(' + repr(str(self.capture)) + ').write_text(json.dumps(sys.argv[1:]))\n'
                              + 'sys.exit(255)\n')
        self.shell.chmod(0o755)

    @unittest.skipUnless(RSYNC, 'real rsync is needed as the parsing oracle')
    def test_ssh_arguments_match_rsync(self):
        cases = [
            'host:path', 'host:', 'user@host:', '@host:path', ':path', 'user@:path',
            'one@two@host:path', '[::1]:path', 'user@[::1]:', '[fe80::1%lo0]:path',
            '[::ffff:127.0.0.1]:path', '[host]:path', '[a@b]:path', 'user@[a@b]:path',
            'host]:path', 'host:path::with:colons', 'host:dir/a::b',
        ]
        for spec in cases:
            for pull in (False, True):
                with self.subTest(spec=spec, pull=pull):
                    paths = [spec, str(self.root / 'destination')] if pull else [str(self.source), spec]
                    results = []
                    for binary, strict in ((RSYNC, []), (str(BINARY), ['--no-fallback'])):
                        self.capture.unlink(missing_ok=True)
                        cmd = [binary, *strict, '-a', '-e', shlex.join([str(self.shell), '-l', 'alternate']),
                               '--rsync-path=ENGINE_TOKEN', *paths]
                        result = subprocess.run(cmd, capture_output=True, timeout=10)
                        self.assertTrue(self.capture.exists(), result.stderr)
                        arguments = json.loads(self.capture.read_text())
                        results.append(arguments[:arguments.index('ENGINE_TOKEN')])
                        self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(results[0], results[1])

    @unittest.skipUnless(RSYNC, 'real rsync is needed as the parsing oracle')
    def test_local_paths_match_rsync(self):
        cases = ['[::1', '[]:file', 'a[b]:file', '[::1]extra:file', '[::1]/file',
                 '[bad/ip]:file', 'sub/a::b', './a::b', '[::1]', 'plain']
        for case_index, name in enumerate(cases):
            with self.subTest(name=name):
                case_root = self.root / ('case-' + str(case_index))
                source = case_root / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(b'local filename with punctuation')
                for index, (binary, strict) in enumerate(((RSYNC, []), (str(BINARY), ['--no-fallback']))):
                    destination = case_root / ('local-result-' + str(index))
                    result = subprocess.run([binary, *strict, '-a', name, str(destination)], cwd=case_root,
                                            capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_daemon_detection_only_at_host_separator(self):
        for spec in ('host::module', '[::1]::module', 'user@[::1]::module', 'RSYNC://host/module'):
            with self.subTest(spec=spec):
                self.capture.unlink(missing_ok=True)
                result = subprocess.run([str(BINARY), '--no-fallback', '-a', '-e', str(self.shell),
                                         str(self.source), spec], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b'rsync daemon transfers', result.stderr)
                self.assertFalse(self.capture.exists())

    def exercise_remote_paths(self, rsh, host):
        remote = self.root / 'remote cwd'
        remote.mkdir()
        command = 'cd ' + shlex.quote(str(remote)) + ' && exec ' + shlex.quote(str(BINARY))
        def run(paths):
            result = subprocess.run([str(BINARY), '--no-fallback', '-az', '-e', rsh,
                                     '--rsync-path=' + command, *paths], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(b'falling back', result.stderr)
        run([str(self.source), host + ':'])
        self.assertEqual((remote / 'source').read_bytes(), self.source.read_bytes())
        pulled = self.root / 'pulled'
        run([host + ':', str(pulled)])
        self.assertEqual((pulled / 'source').read_bytes(), self.source.read_bytes())
        run([str(self.source), host + ':a::b'])
        self.assertEqual((remote / 'a::b').read_bytes(), self.source.read_bytes())
        (remote / 'second').write_bytes(b'second source')
        multi = self.root / 'multiple'
        run([host + ':source', ':second', str(multi)])
        self.assertEqual((multi / 'source').read_bytes(), self.source.read_bytes())
        self.assertEqual((multi / 'second').read_bytes(), b'second source')

    def test_native_empty_paths_and_colons(self):
        for host in ('fakehost', 'user@fakehost', '[::1]', 'user@[::1]'):
            with self.subTest(host=host):
                self.exercise_remote_paths(shlex.quote(str(REPO / 'tests/fakessh.sh')), host)
                shutil.rmtree(self.root / 'remote cwd')
                shutil.rmtree(self.root / 'pulled')
                shutil.rmtree(self.root / 'multiple')

    @unittest.skipUnless(os.environ.get('XSYNC_RIG_HOST'), 'real IPv6 SSH check runs in the Linux rig')
    def test_real_ipv6_ssh(self):
        # A separate sshd on the client loopback avoids requiring external IPv6.
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as listener:
            listener.bind(('::1', 0))
            port = listener.getsockname()[1]
        authorized = self.root / 'authorized_keys'
        shutil.copy('/keys/id test.pub', authorized)
        config = self.root / 'sshd_config'
        config.write_text(f'Port {port}\nListenAddress ::1\n'
                          'HostKey /etc/ssh/ssh_host_ed25519_key\n'
                          f'AuthorizedKeysFile "{authorized}"\nStrictModes no\n'
                          'PermitRootLogin prohibit-password\nPasswordAuthentication no\nUsePAM no\n'
                          f'PidFile "{self.root}/sshd.pid"\n')
        log = (self.root / 'sshd.log').open('wb')
        daemon = subprocess.Popen(['/usr/sbin/sshd', '-D', '-e', '-f', str(config)], stderr=log)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as probe:
                        probe.settimeout(.2)
                        probe.connect(('::1', port))
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        log.flush()
                        self.fail((self.root / 'sshd.log').read_text())
                    time.sleep(.05)
            ssh = ['ssh', '-i', '/keys/id test', '-p', str(port), '-oBatchMode=yes',
                   '-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null', '-oLogLevel=ERROR']
            self.exercise_remote_paths(shlex.join(ssh), 'root@[::1]')
        finally:
            daemon.terminate()
            daemon.wait(timeout=5)
            log.close()


if __name__ == '__main__':
    unittest.main()
