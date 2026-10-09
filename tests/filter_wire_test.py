#!/usr/bin/env python3
"""Extended filters require negotiation; invalid config cannot open a destination."""
import json
import os
import pathlib
import shlex
import struct
import subprocess
import sys
import tempfile
import unittest

import wire_test as wire
from wire_test import frame, read_frame, string, var


class FilterWireTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync filter wire ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def server(self, features=2049, deleting=False):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' or (deleting and name == 'del') for name in wire.BOOLS)
        options += b''.join(var(1 if name == 'max_delete' else 2 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + var(wire.VERSION) + b'R' + var(features) + options + b'\0\1' + string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=getattr(self, 'env', None))
        self.addCleanup(self.close, proc)
        proc.stdin.write(frame(1, hello)); proc.stdin.flush()
        self.assertEqual(read_frame(proc)[0], 1)
        return proc, target

    @staticmethod
    def close(proc):
        if proc.poll() is None: proc.kill()
        proc.communicate(timeout=5)

    def rejected(self, proc, target, data):
        proc.stdin.write(data); proc.stdin.flush()
        kind, message = read_frame(proc)
        if kind == 10: kind, message = read_frame(proc)  # Destination description precedes receiver reads.
        self.assertEqual(kind, 8)
        self.assertEqual(message[:2], b'\2\2')
        self.assertIn(b'protocol error', message)
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(target.exists())

    def test_bad_configurations(self):
        for label, data in (
            ('wrong-frame', frame(2, b'')),
            ('truncated-count', frame(19, b'\x80')),
            ('too-many-rules', frame(19, var(10001))),
            ('short-rule-list', frame(19, var(2) + string('P keep'))),
            ('truncated-rule', frame(19, var(1) + var(8) + b'P')),
            ('unknown-rule', frame(19, var(1) + string('unknown keep'))),
            ('invalid-side', frame(19, var(1) + string('Ps keep'))),
            ('unnegotiated-merge', frame(19, var(1) + string(': .rules'))),
            ('single-instance-file-read', frame(19, var(1) + string('. /etc/passwd'))),
            ('trailing-bytes', frame(19, var(1) + string('P keep') + b'x')),
            ('oversized-header', struct.pack('<IB', 1024 * 1024 + 1, 19)),
        ):
            with self.subTest(label=label):
                proc, target = self.server()
                self.rejected(proc, target, data)

    def test_unnegotiated_config(self):
        proc, target = self.server(features=1)
        self.rejected(proc, target, frame(19, var(1) + string('P keep')))

    def test_delete_after_configuration(self):
        for payload in (b'', b'\0', b'\2', b'\1x'):
            with self.subTest(payload=payload):
                proc, target = self.server(features=16385, deleting=True)
                self.rejected(proc, target, frame(20, payload))
        proc, target = self.server(features=16385)
        self.rejected(proc, target, frame(20, b'\1'))
        proc, target = self.server(features=1, deleting=True)
        self.rejected(proc, target, frame(20, b'\1'))

    def test_prune_empty_configuration(self):
        for payload in (b'', b'\0', b'\2', b'\1x'):
            with self.subTest(payload=payload):
                proc, target = self.server(features=32769)
                self.rejected(proc, target, frame(21, payload))
        proc, target = self.server(features=1)
        self.rejected(proc, target, frame(21, b'\1'))

    def test_cvs_configuration(self):
        for label, payload in (
            ('missing-flag', b''), ('invalid-flag', b'\2\0'),
            ('missing-count', b'\1'), ('too-many', b'\0' + var(10001)),
            ('truncated-rule', b'\0' + var(1) + string('-C')[:-1]),
            ('trailing', b'\0\0x'),
        ):
            with self.subTest(label=label):
                proc, target = self.server(features=14337)
                self.rejected(proc, target, frame(19, payload))
        proc, target = self.server(features=10241)  # CVS without per-directory support.
        self.rejected(proc, target, frame(19, b'\1\0'))

    def test_unnegotiated_cvs_cannot_read_home(self):
        # A FIFO makes accidental HOME access observable as a timeout.
        home = self.root / 'home'; home.mkdir()
        os.mkfifo(home / '.cvsignore')
        self.env = dict(os.environ, HOME=str(home))
        for features in (2049, 6145):
            proc, target = self.server(features=features)
            self.rejected(proc, target, frame(19, var(1) + string('-C')))

    def test_extended_rule_in_frozen_hello_is_rejected(self):
        for features, rule in ((1, 'P keep'), (2049, 'P keep'), (2049, '-C'), (14337, '-C')):
            with self.subTest(features=features, rule=rule):
                target = self.root / 'uncreated'
                options = bytes(name == 'recursive' for name in wire.BOOLS)
                options += b''.join(var(1 if name == 'max_delete' else 2 if name == 'jobs' else 0) for name in wire.INTS)
                hello = b'XSYNC\1' + var(wire.VERSION) + b'R' + var(features) + options
                hello += var(1) + string(rule) + var(1) + string(str(target))
                proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.addCleanup(self.close, proc)
                self.rejected(proc, target, frame(1, hello))

    def test_missing_feature_preserves_original_fallback_arguments(self):
        peer = self.root / 'peer.py'
        answer = frame(1, b'XSYNC\1' + var(wire.VERSION) + var(1))
        peer.write_text('import sys,struct\n'
                        'h=sys.stdin.buffer.read(5); sys.stdin.buffer.read(struct.unpack("<IB",h)[0])\n'
                        f'sys.stdout.buffer.write({answer!r}); sys.stdout.buffer.flush()\n'
                        'sys.stdin.buffer.read()\n')
        rsh = shlex.join([sys.executable, str(peer)])
        source = self.root / 'source'; source.write_bytes(b'original')
        target = self.root / 'uncreated'
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='0')
        directory = self.root / 'commands'; directory.mkdir()
        capture = directory / 'rsync'
        capture.write_text('#!' + sys.executable + '\nimport sys,json\nprint(json.dumps(sys.argv[1:]));sys.exit(19)\n')
        capture.chmod(0o755)
        for flags, diagnostic in ((['--delete', '--filter=P stale.*'], b'extended filters'),
                                  (['--delete-after'], b'--delete-after'),
                                  (['-m'], b'--prune-empty-dirs')):
            with self.subTest(flags=flags):
                original = ['-a', *flags, '-e', rsh, '--rsync-path=unused', str(source), 'fake:' + str(target)]
                env['XSYNC_FALLBACK'] = '0'
                result = subprocess.run([str(wire.BINARY), *original], capture_output=True, env=env, timeout=10)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn(b'peer does not support ' + diagnostic, result.stderr)
                env.update(PATH=str(directory), XSYNC_FALLBACK='1')
                result = subprocess.run([str(wire.BINARY), *original], capture_output=True, env=env, timeout=10)
                self.assertEqual(result.returncode, 19, result.stderr)
                self.assertEqual(json.loads(result.stdout), original)
                self.assertEqual(result.stderr.count(b'falling back to rsync'), 1)
        self.assertFalse(target.exists())
        self.assertEqual(source.read_bytes(), b'original')



if __name__ == '__main__': unittest.main()
