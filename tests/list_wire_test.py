#!/usr/bin/env python3
"""Listing negotiation and hostile metadata never enter the transfer receiver."""
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
from wire_test import var, string, frame, read_frame

class ListWireTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync list wire ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

    def peer(self, frames, features=513, exit_code=0):
        path = self.root / 'peer.py'
        path.write_text('import sys,struct\n'
                        'header=sys.stdin.buffer.read(5)\n'
                        'if len(header)==5: sys.stdin.buffer.read(struct.unpack("<IB",header)[0])\n'
                        f'sys.stdout.buffer.write({frame(1, b"XSYNC" + bytes([1]) + var(wire.VERSION) + var(features)) + frames!r})\n'
                        'sys.stdout.buffer.flush()\n'
                        'sys.stdin.buffer.read()\n' + f'sys.exit({exit_code})\n')
        return shlex.join([sys.executable, str(path)])

    def run_list(self, rsh, *flags, env=None):
        return subprocess.run([str(wire.BINARY), *flags, '-e', rsh, '--rsync-path=unused',
                               'fake:' + str(self.root/'source')], capture_output=True, timeout=10, env=env)

    def test_bad_entries_and_completions(self):
        base = string('safe') + b'\1' + var(0o644) + var(5) + b'\0' + string('')
        for case in ('absolute', 'parent', 'empty_part', 'nul', 'mode', 'size', 'type', 'target',
                     'truncated', 'trailing', 'count', 'status', 'short_end', 'data_frame', 'after_end'):
            with self.subTest(case=case):
                bad = string('/outside') + base[len(string('safe')):] if case == 'absolute' else \
                      string('sub/../outside') + base[len(string('safe')):] if case == 'parent' else \
                      string('sub//outside') + base[len(string('safe')):] if case == 'empty_part' else \
                      string('nul\0name') + base[len(string('safe')):] if case == 'nul' else \
                      string('safe') + b'\1' + var(0o10000) + var(5) + b'\0\0' if case == 'mode' else \
                      string('safe') + b'\1' + var(0o644) + var(1 << 63) + b'\0\0' if case == 'size' else \
                      string('safe') + b'\0' + var(0o644) + var(5) + b'\0\0' if case == 'type' else \
                      base[:-1] + string('unexpected') if case == 'target' else \
                      base[:-1] if case == 'truncated' else base + b'X'
                frames = frame(5, b'\0\1') if case == 'count' else \
                         frame(5, var(999) + b'\0') if case == 'status' else \
                         frame(5, b'\0') if case == 'short_end' else \
                         frame(4, b'') if case == 'data_frame' else \
                         frame(5, b'\0\0') + frame(16, base) if case == 'after_end' else frame(16, bad)
                result = self.run_list(self.peer(frames), '--no-fallback')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'protocol error', result.stderr)
                self.assertFalse((self.root/'source').exists())

    def test_missing_feature_strict_and_original_argument_fallback(self):
        rsh = self.peer(b'', features=1)
        result = self.run_list(rsh, '--no-fallback')
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn(b'source listing', result.stderr)
        directory = self.root/'commands'; directory.mkdir()
        script = directory/'rsync'
        script.write_text('#!' + sys.executable + '\nimport sys,json\nprint(json.dumps(sys.argv[1:]));sys.exit(19)\n')
        script.chmod(0o755)
        env = dict(os.environ, PATH=str(directory), XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='1')
        result = self.run_list(rsh, env=env)
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['-e', rsh, '--rsync-path=unused',
                                                   'fake:' + str(self.root/'source')])
        self.assertEqual(result.stderr.count(b'falling back to rsync'), 1)
        self.assertFalse((self.root/'source').exists())

    def test_listing_feature_cannot_request_receiver_role(self):
        target = self.root/'uncreated'
        options = bytes(name == 'recursive' for name in wire.BOOLS)
        options += b''.join(var(1 if name == 'max_delete' else 2 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + var(wire.VERSION) + b'R' + var(513) + options + b'\0\1' + string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            proc.stdin.write(frame(1, hello)); proc.stdin.flush()
            kind, payload = read_frame(proc)
            self.assertEqual(kind, 8)
            self.assertIn(b'listing requires sender role', payload)
            proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(target.exists())
        finally:
            if proc.poll() is None: proc.kill()
            proc.communicate(timeout=5)

    def test_shell_failure_after_valid_completion_is_not_lost(self):
        result = self.run_list(self.peer(frame(5, b'\0\0'), exit_code=255), '--no-fallback')
        self.assertEqual(result.returncode, 255, result.stderr)
        self.assertIn(b'remote shell exited', result.stderr)

    def test_cvs_source_metadata_and_validation(self):
        for name, source, code in (('safe', None, 2), ('safe', '/source/\0safe', 2),
                                    ('unsafe.o', '/source/unsafe.o', 4), ('safe', '/source/safe', 0)):
            with self.subTest(name=name, source=source):
                entry = string(name) + b'\1' + var(0o644) + var(5) + b'\0' + string('')
                if source is not None: entry += string(source)
                frames = frame(16, entry) + frame(5, b'\0\1')
                result = self.run_list(self.peer(frames, features=10753), '--no-fallback', '--filter=-C')
                self.assertEqual(result.returncode, code, result.stderr)
                if code == 2: self.assertIn(b'protocol error', result.stderr)
                elif code == 4:
                    self.assertIn(b'rejecting excluded file-list name', result.stderr)
                    self.assertEqual(result.stdout, b'')
                else: self.assertIn(b'safe', result.stdout)
                self.assertFalse((self.root/'source').exists())

if __name__ == '__main__': unittest.main()
