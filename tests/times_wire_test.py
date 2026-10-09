#!/usr/bin/env python3
"""Negotiated time fields must be complete before receiver publication."""
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire
import xattrs_wire_test as xwire
from xattrs_test import DARWIN

ATIME = 8388608
CRTIME = 16777216


def signed(value): return wire.var((value << 1) ^ (value >> 63))


class TimeWireTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def configured(self, create=False):
        proc, target = self.server(features=1 | ATIME | (CRTIME if create else 0))
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def directory(self, root=None, entry=None, create=False):
        times = signed(1200000000) + (signed(1000000000) if create else b'')
        body = wire.string('') + wire.var(0o755) + b'\0' * 4 + (times if root is None else root)
        if entry is None: body += b'\0'
        else: body += b'\1' + wire.string('file') + b'\1' + wire.var(0o644) + b'\0\0' + entry + wire.var(4)
        return wire.frame(2, b'\0\0\0\1' + body)

    def test_truncated_directory_time_fields_before_writes(self):
        for create in ([False, True] if DARWIN else [False]):
            for bad in (b'', b'\x80' * 10, b'\xff' * 9 + b'\2'):
                for entry in (False, True):
                    with self.subTest(create=create, bad=bad, entry=entry):
                        proc, target = self.configured(create)
                        self.rejected(proc, target, self.directory(entry=bad, create=create) if entry else self.directory(root=bad, create=create))

    def test_fresh_time_fields_before_file_publication(self):
        for create in ([False, True] if DARWIN else [False]):
            for bad in (b'', b'\x80' * 10, b'\xff' * 9 + b'\2'):
                with self.subTest(create=create, bad=bad):
                    proc, target = self.configured(create)
                    times = signed(1200000000) + (signed(1000000000) if create else b'')
                    proc.stdin.write(self.directory(entry=times, create=create)); proc.stdin.flush()
                    self.assertEqual(wire.read_frame(proc)[0], 3)
                    raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + bad
                    proc.stdin.write(xwire.data_record(raw)); proc.stdin.flush()
                    kind, message = wire.read_frame(proc)
                    self.assertEqual((kind, message[:2]), (8, b'\2\2'))
                    proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 2)
                    self.assertFalse((target / 'file').exists())

    def test_fresh_time_fields_preserve_requested_values(self):
        for create in ([False, True] if DARWIN else [False]):
            with self.subTest(create=create):
                proc, target = self.configured(create)
                listed = signed(1200000000) + (signed(1000000000) if create else b'')
                proc.stdin.write(self.directory(entry=listed, create=create)); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                fresh = signed(1200000100) + (signed(1000000100) if create else b'')
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + fresh + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 7)
                proc.stdin.close(); proc.stdin = None; proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0)
                result = (target / 'file').stat()
                self.assertEqual(result.st_atime_ns, 1200000100 * 10**9)
                if create: self.assertEqual(int(result.st_birthtime), 1000000100)
                self.assertEqual((target / 'file').read_bytes(), b'data')

    @unittest.skipIf(DARWIN, 'Darwin supports native creation times')
    def test_unsupported_creation_times_refuse_before_writes(self):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1 | CRTIME) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        kind, message = wire.read_frame(proc)
        self.assertEqual((kind, message[:2]), (8, b'\2\4'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 4)
        self.assertFalse(target.exists())

    def test_helper_time_flags_require_client_negotiation(self):
        for flag in ('--atimes', '--open-noatime', *(['--crtimes'] if DARWIN else [])):
            with self.subTest(flag=flag):
                target = self.root / 'uncreated'
                options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
                hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1) + options + b'\0\1' + wire.string(str(target))
                proc = subprocess.Popen([str(wire.BINARY), '--server', flag], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.addCleanup(self.close, proc)
                proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
                kind, message = wire.read_frame(proc)
                self.assertEqual((kind, message[:2]), (8, b'\2\4'))
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 4)
                self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
