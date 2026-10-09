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

    def test_relative_configuration(self):
        for payload in (b'', b'\0', b'\2', b'\1x'):
            with self.subTest(payload=payload):
                proc, target = self.server(features=65537)
                self.rejected(proc, target, frame(22, payload))
        proc, target = self.server(features=1)
        self.rejected(proc, target, frame(22, b'\1'))
        proc, target = self.server(features=65537)
        self.rejected(proc, target, struct.pack('<IB', 1024 * 1024, 22))

    def test_relative_directory_metadata(self):
        for label, data in (
            ('invalid-selection-flag', wire.directory([('dir', 2, var(0) + b'\2' + string('/source/dir'))])),
            ('truncated-selection-flag', wire.directory([('dir', 2, var(0))])),
            ('nul-source', wire.directory([('dir', 2, var(0) + b'\1' + string(b'/source\0/dir'))])),
            ('trailing-directory', frame(2, wire.directory()[5:] + b'x')),
        ):
            with self.subTest(label=label):
                proc, target = self.server(features=65537)
                proc.stdin.write(frame(22, b'\1')); proc.stdin.flush()
                self.rejected(proc, target, data)

    def test_files_from_configuration(self):
        for payload in (b'', b'\1', b'\0\0\0', b'\3\0\0', b'\1\2\0',
                        b'\1\0\x80', b'\1\0' + string('unexpected'),
                        b'\2\0' + string('-'), b'\2\0' + string(b'bad\0path'),
                        b'\1\0\0x'):
            with self.subTest(payload=payload):
                proc, target = self.server(features=131073)
                self.rejected(proc, target, frame(23, payload))
        proc, target = self.server(features=131073)
        self.rejected(proc, target, struct.pack('<IB', 1024 * 1024 + 17, 23))

    def test_files_from_stream(self):
        for label, data in (
            ('empty-data', frame(24, b'')),
            ('oversized-data', struct.pack('<IB', 65537, 24)),
            ('oversized-end', struct.pack('<IB', 11, 25)),
            ('missing-count', frame(25, b'')),
            ('truncated-count', frame(25, b'\x80')),
            ('trailing-count', frame(25, b'\0x')),
            ('wrong-count', frame(24, b'a\n') + frame(25, var(1))),
            ('unexpected-frame', frame(2, b'')),
        ):
            with self.subTest(label=label):
                proc, target = self.server(features=131073)
                proc.stdin.write(frame(23, b'\1\0\0')); proc.stdin.flush()
                self.assertEqual(read_frame(proc), (23, b'\0'))
                self.rejected(proc, target, data)
        for kind in (23, 24, 25):
            proc, target = self.server(features=1)
            self.rejected(proc, target, frame(kind, b'\0'))

    def test_files_from_directory_metadata_without_relative(self):
        for data in (wire.directory([('dir', 2, var(0) + b'\2' + string('/source/dir'))]),
                     wire.directory([('dir', 2, var(0))]),
                     wire.directory([('dir', 2, var(0) + b'\1' + string(b'/source\0/dir'))])):
            proc, target = self.server(features=131073)
            proc.stdin.write(frame(23, b'\1\0\0')); proc.stdin.flush()
            self.assertEqual(read_frame(proc), (23, b'\0'))
            self.rejected(proc, target, frame(25, b'\0') + data)

    def test_files_from_fallback_preserves_stdin(self):
        peer = self.root / 'peer.py'
        answer = frame(1, b'XSYNC\1' + var(wire.VERSION) + var(1))
        peer.write_text('import sys,struct\n'
                        'h=sys.stdin.buffer.read(5); sys.stdin.buffer.read(struct.unpack("<IB",h)[0])\n'
                        f'sys.stdout.buffer.write({answer!r}); sys.stdout.buffer.flush()\n'
                        'sys.stdin.buffer.read()\n')
        directory = self.root / 'commands'; directory.mkdir()
        capture = directory / 'rsync'
        capture.write_text('#!' + sys.executable + '\nimport sys,json\n'
                           'print(json.dumps([sys.argv[1:],sys.stdin.buffer.read().hex()]));sys.exit(19)\n')
        capture.chmod(0o755)
        env = dict(os.environ, PATH=str(directory), XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='1')
        rsh = shlex.join([sys.executable, str(peer)])
        source = self.root / 'source'; source.mkdir()
        target = self.root / 'uncreated'
        names = b'a\0line\nbreak\0'
        for flags, stdin in ((['--from0', '--files-from=-'], names),
                             (['--filter=. -', '--files-from=-'], b'- *.o\n')):
            with self.subTest(flags=flags):
                original = ['-a', *flags, '-e', rsh, '--rsync-path=unused', str(source), 'fake:' + str(target)]
                result = subprocess.run([str(wire.BINARY), *original], input=stdin, capture_output=True, env=env, timeout=10)
                self.assertEqual(result.returncode, 19, result.stderr)
                self.assertEqual(json.loads(result.stdout), [original, stdin.hex()])
                self.assertEqual(result.stderr.count(b'falling back to rsync'), 1)
                self.assertFalse(target.exists())

    def test_files_from_pull_rejects_unrequested_names_before_writes(self):
        peer = self.root / 'peer.py'
        hello = frame(1, b'XSYNC\1' + var(wire.VERSION) + var(131073))
        bad = wire.directory([('unexpected', 1, var(0) + string('/source/unexpected'))])
        peer.write_text('import sys,struct\n'
                        'r=sys.stdin.buffer; w=sys.stdout.buffer\n'
                        'def read():\n h=r.read(5); n,k=struct.unpack("<IB",h); return k,r.read(n)\n'
                        f'read(); w.write({hello!r}); w.flush()\n'
                        f'assert read()[0]==23; w.write({frame(23, b"\0")!r}); w.flush()\n'
                        'while read()[0]!=25: pass\n'
                        'assert read()[0]==10\n'
                        f'w.write({bad!r}+{frame(5, b"")!r}); w.flush()\n'
                        'r.read()\n')
        target = self.root / 'uncreated'
        result = subprocess.run([str(wire.BINARY), '--no-fallback', '-r', '--no-relative', '--files-from=-',
                                 '-e', shlex.join([sys.executable, str(peer)]), '--rsync-path=unused',
                                 'fake:source', str(target)], input=b'allowed\n', capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn(b'rejecting unrequested file-list name: unexpected', result.stderr)
        self.assertFalse(target.exists())

    def test_files_from_bad_acknowledgement_does_not_read_fifo(self):
        peer = self.root / 'peer.py'
        hello = frame(1, b'XSYNC\1' + var(wire.VERSION) + var(131073))
        fifo = self.root / 'names'; os.mkfifo(fifo)
        target = self.root / 'uncreated'
        for answer in (frame(23, b''), frame(23, b'\2'), frame(23, b'\1'), frame(23, b'\0x'), frame(24, b'\0')):
            with self.subTest(answer=answer):
                peer.write_text('import sys,struct\n'
                                'r=sys.stdin.buffer; w=sys.stdout.buffer\n'
                                'def read():\n h=r.read(5); n,k=struct.unpack("<IB",h); return k,r.read(n)\n'
                                f'read(); w.write({hello!r}); w.flush()\n'
                                f'assert read()[0]==23; w.write({answer!r}); w.flush()\n'
                                'r.read()\n')
                result = subprocess.run([str(wire.BINARY), '--no-fallback', '--no-relative', '--files-from=' + str(fifo),
                                         '-e', shlex.join([sys.executable, str(peer)]), '--rsync-path=unused',
                                         'fake:source', str(target)], capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'malformed files-from acknowledgement', result.stderr)
                self.assertFalse(target.exists())

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
                                  (['-m'], b'--prune-empty-dirs'),
                                  (['-R'], b'--relative')):
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
