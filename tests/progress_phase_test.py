#!/usr/bin/env python3
"""Visible checksum/deletion/wait phases, including bounded peer snapshots."""
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import unittest

import progress_ack_test as ack_fixture
from output_test import BINARY, HOST, RSH
from progress_test import capture, ENV, CSI
from io_limit_test import PREAMBLE

REPO = pathlib.Path(__file__).resolve().parent.parent
PHASE = 8589934592


class PhaseProgressTests(unittest.TestCase):
    setUp = ack_fixture.ProgressAckTests.setUp

    @classmethod
    def setUpClass(cls):
        ack_fixture.ProgressAckTests.setUpClass.__func__(cls)

    def command(self, direction, flags, env):
        source, dest = str(self.source) + '/', str(self.dest) + '/'
        args = [str(BINARY), '--no-fallback', '-a', '--no-clone', '-j1', *flags]
        if direction != 'local':
            rsh = shlex.join([sys.executable, str(REPO / 'tests/fault_ssh.py')])
            peer = str(BINARY)
            if HOST:
                rsh = RSH
                variables = [k + '=' + v for k, v in env.items() if k.startswith('XSYNC_FAULT_')]
                peer = shlex.join(['env', 'LD_PRELOAD=/work/build/fault_io.so', *variables, '/usr/local/bin/xsync'])
            args += ['-e', rsh, '--rsync-path=' + peer]
            if direction == 'push': dest = (HOST or 'fake') + ':' + dest
            else:
                if HOST:
                    subprocess.run(['rsync', '-a', '-e', RSH, source, HOST + ':' + source], check=True, capture_output=True)
                source = (HOST or 'fake') + ':' + source
        return args + [source, dest]

    def fault_env(self, **values):
        env = dict(ENV, XSYNC_FAULT_PATH=str(self.dest), **values)
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.library)
        return env

    def marker(self, path, direction):
        exists = path.exists()
        if HOST and direction == 'push':
            from ssh_test import remote_code
            exists = remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).exists())', path).strip() == 'True'
        if not exists and os.environ.get('XSYNC_PROGRESS_FAULT_OPTIONAL') == '1': self.skipTest('fault interposition unavailable')
        self.assertTrue(exists, 'phase delay fixture did not interpose')

    def prepare_dest(self, direction, stale=False):
        if self.dest.exists(): shutil.rmtree(self.dest)
        if HOST and direction == 'push':
            from ssh_test import remote_code
            remote_code('import shutil,sys,pathlib; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.dest)
            if not stale:
                subprocess.run(['rsync', '-a', '-e', RSH, str(self.source) + '/', HOST + ':' + str(self.dest) + '/'], check=True, capture_output=True)
            else:
                remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); [(p/str(i)).write_bytes(b"stale") for i in range(16)]', self.dest)
        else:
            shutil.copytree(self.source, self.dest)
            if stale:
                for i in range(16): (self.dest / str(i)).write_bytes(b'stale')

    def test_verifying_labels_and_counters(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                self.prepare_dest(direction)
                marker = self.root / ('reading-' + direction)
                env = self.fault_env(XSYNC_FAULT_READ_DELAY_US='400000', XSYNC_FAULT_READ_NOTIFY=str(marker))
                code, data = capture(self.command(direction, ['--progress', '-c'], env), width=160, env=env)
                self.assertEqual(code, 0, data)
                self.marker(pathlib.Path(str(marker) + '.1'), direction)
                self.assertRegex(CSI.sub(b'', data), rb'verifying\s+\d+ checks')

    def test_deleting_labels_and_counters(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                self.prepare_dest(direction, stale=True)
                marker = self.root / ('deleting-' + direction)
                env = self.fault_env(XSYNC_FAULT_UNLINK_DELAY_US='100000', XSYNC_FAULT_UNLINK_NOTIFY=str(marker))
                code, data = capture(self.command(direction, ['--progress', '--delete-after'], env), width=160, env=env)
                self.assertEqual(code, 0, data)
                self.marker(marker, direction)
                counts = [int(n) for n in re.findall(rb'deleting\s+(\d+)', CSI.sub(b'', data))]
                self.assertGreater(len(set(counts)), 3, data)
                self.assertEqual(counts, sorted(counts))
                if HOST and direction == 'push':
                    from ssh_test import remote_code
                    names = json.loads(remote_code('import json,pathlib,sys; print(json.dumps(sorted(p.name for p in pathlib.Path(sys.argv[1]).iterdir())))', self.dest))
                else: names = sorted(p.name for p in self.dest.iterdir())
                self.assertEqual(names, ['large'])

    def test_waiting_receiver_and_json_phase_counts(self):
        marker = self.root / 'writing'
        env = self.fault_env(XSYNC_FAULT_WRITE_DELAY_US='400000', XSYNC_FAULT_WRITE_NOTIFY=str(marker))
        code, data = capture(self.command('push', ['--progress'], env), width=160, env=env)
        self.assertEqual(code, 0, data)
        self.marker(marker, 'push')
        self.assertIn(b'waiting for receiver', data)
        if self.dest.exists(): shutil.rmtree(self.dest)
        self.prepare_dest('push', stale=True)
        env = self.fault_env(XSYNC_FAULT_UNLINK_DELAY_US='100000', XSYNC_FAULT_UNLINK_NOTIFY=str(self.root / 'unlink-json'))
        result = subprocess.run(self.command('push', ['--progress=json', '--delete-after'], env), env=env, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertIn('deleting', [r.get('phase') for r in rows])
        self.assertEqual(rows[-1]['deleted'], 16)
        self.assertEqual(rows[-1]['phase'], 'complete')

    def test_malformed_and_unnegotiated_phase_frames(self):
        for features, payload in ((1, b'\0\0\0'), (1 | PHASE, b'\x04\0\0'),
                                  (1 | PHASE, b'\0\x80'), (1 | PHASE, b'\0\0\0extra'),
                                  (1 | PHASE, b'x' * 22)):
            with self.subTest(features=features, payload=payload):
                peer = self.root / 'peer.py'
                peer.write_text(PREAMBLE + '\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var(' + str(features) + '))\n'
                                'send(36,' + repr(payload) + ')\ntime.sleep(2)\n')
                result = subprocess.run([str(BINARY), '--no-fallback', '-r', '--numeric-ids', '--progress',
                                         '-e', shlex.join([sys.executable, str(peer)]), '--rsync-path=unused',
                                         'fake:source', str(self.root / 'target')], env=ENV, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'progress phase', result.stderr)


if __name__ == '__main__': unittest.main()
