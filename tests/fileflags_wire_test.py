#!/usr/bin/env python3
"""Negotiated BSD flags are bounded and read before metadata/publication."""
import os
import shutil
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire
import xattrs_wire_test as xwire
from xattrs_test import DARWIN

FILEFLAGS = 134217728


def clear_flags(root):
    if DARWIN:
        for p in [root] + sorted(root.rglob('*')): os.chflags(p, 0, follow_symlinks=False)


class FileflagsWireTests(unittest.TestCase):
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def setUp(self):
        configured.FilterWireTests.setUp(self)
        self.addCleanup(clear_flags, self.root)

    def configured(self):
        proc, target = self.server(features=1 | FILEFLAGS)
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def directory(self, root=b'\0', entry=b'\0'):
        body = wire.string('') + wire.var(0o755) + b'\0' * 4 + root
        if entry is None: body += b'\0'
        else: body += b'\1' + wire.string('file') + b'\1' + wire.var(0o644) + b'\0\0' + entry + wire.var(4)
        return wire.frame(2, b'\0\0\0\1' + body)

    @unittest.skipUnless(DARWIN, 'native BSD flags')
    def test_directory_fields_reject_truncation_and_overflow_before_writes(self):
        for bad in (b'', b'\x80' * 10, wire.var(1 << 32)):
            for entry in (False, True):
                with self.subTest(bad=bad, entry=entry):
                    proc, target = self.configured()
                    self.rejected(proc, target, self.directory(entry=bad) if entry else self.directory(root=bad, entry=None))

    @unittest.skipUnless(DARWIN, 'native BSD flags')
    def test_fresh_fields_reject_before_file_publication(self):
        for bad in (b'', b'\x80' * 10, wire.var(1 << 32)):
            with self.subTest(bad=bad):
                proc, target = self.configured()
                proc.stdin.write(self.directory()); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + bad
                proc.stdin.write(xwire.data_record(raw)); proc.stdin.flush()
                kind, message = wire.read_frame(proc)
                self.assertEqual((kind, message[:2]), (8, b'\2\2'))
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 2)
                self.assertFalse((target / 'file').exists())

    @unittest.skipUnless(DARWIN, 'native BSD flags')
    def test_fresh_flags_replace_listed_flags(self):
        for listed, fresh in ((0, 2), (2, 0), (0, 4), (1, 0x8000)):
            with self.subTest(listed=listed, fresh=fresh):
                target = self.root / 'uncreated'
                if target.exists(): clear_flags(target); shutil.rmtree(target)
                proc, target = self.configured()
                proc.stdin.write(self.directory(entry=wire.var(listed))); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + wire.var(fresh) + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 7)
                proc.stdin.close(); proc.stdin = None; proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual((target / 'file').stat().st_flags, fresh)
                self.assertEqual((target / 'file').read_bytes(), b'data')

    @unittest.skipUnless(DARWIN, 'native BSD flags')
    def test_unsettable_synthetic_flag_reports_partial(self):
        for flags in (0x10000, 0x40000000, 0x20):
            with self.subTest(flags=flags):
                target = self.root / 'uncreated'
                if target.exists(): clear_flags(target); shutil.rmtree(target)
                proc, target = self.configured()
                proc.stdin.write(self.directory()); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + wire.var(flags) + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                messages = []
                while True:
                    kind, message = wire.read_frame(proc); messages.append((kind, message))
                    if kind == 7: break
                proc.stdin.close(); proc.stdin = None; proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 23)
                self.assertTrue(any(kind == 8 and b'file flags' in message for kind, message in messages))
                self.assertEqual((target / 'file').stat().st_flags, 0)
                self.assertEqual((target / 'file').read_bytes(), b'data')

    @unittest.skipUnless(DARWIN, 'native BSD flags')
    def test_explicit_helper_flags_require_negotiation(self):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server', '--fileflags'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        kind, message = wire.read_frame(proc)
        self.assertEqual((kind, message[:2]), (8, b'\2\4'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 4)
        self.assertFalse(target.exists())

    @unittest.skipIf(DARWIN, 'Darwin supports BSD flags')
    def test_linux_refuses_before_writes(self):
        target = self.root / 'uncreated'
        result = subprocess.run([str(wire.BINARY), '--no-fallback', '--fileflags', str(self.root), str(target)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'not supported on this platform', result.stderr)
        options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1 | FILEFLAGS) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        kind, message = wire.read_frame(proc)
        self.assertEqual((kind, message[:2]), (8, b'\2\4'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 4)
        self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
