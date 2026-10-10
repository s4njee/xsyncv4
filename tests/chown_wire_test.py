#!/usr/bin/env python3
"""Ownership configuration and identities reject malformed peers before publication."""
import os
import struct
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire
import xattrs_wire_test as xwire

CHOWN = 268435456


class OwnershipWireTests(unittest.TestCase):
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def setUp(self):
        configured.FilterWireTests.setUp(self)

    def server(self, features=1 | CHOWN, helper=(), role=b'R'):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' for name in wire.BOOLS)
        options += b''.join(wire.var(2 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + role + wire.var(features) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server', *helper], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        return proc, target

    def configured(self):
        proc, target = self.server()
        self.assertEqual(wire.read_frame(proc)[0], 1)
        proc.stdin.write(wire.frame(31, wire.string(str(os.getuid())) + wire.string(str(os.getgid())))); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def directory(self, root_uid=None, root_gid=None, file_uid=None, file_gid=None):
        def identity(value): return wire.var(os.getuid()) if value is None else value
        body = wire.string('') + wire.var(0o755) + b'\0\0' + identity(root_uid) + identity(root_gid)
        body += b'\1' + wire.string('file') + b'\1' + wire.var(0o644) + b'\0\0' + identity(file_uid) + identity(file_gid) + wire.var(4)
        return wire.frame(2, b'\0\0\0\1' + body)

    def test_invalid_configurations_and_unnegotiated_frames(self):
        for label, data in (
            ('wrong-frame', wire.frame(2, b'')), ('empty', wire.frame(31, b'')),
            ('truncated', wire.frame(31, b'\x80')), ('missing-group', wire.frame(31, wire.string('0'))),
            ('empty-fields', wire.frame(31, b'\0\0')),
            ('user-nul', wire.frame(31, wire.string(b'a\0b') + b'\0')),
            ('group-nul', wire.frame(31, b'\0' + wire.string(b'a\0b'))),
            ('user-colon', wire.frame(31, wire.string('a:b') + b'\0')),
            ('extra-map', wire.frame(31, wire.string('0,1') + b'\0')),
            ('trailing', wire.frame(31, wire.string('0') + b'\0x')),
            ('oversized-header', struct.pack('<IB', 1024 * 1024 + 1, 31)),
        ):
            with self.subTest(label=label):
                proc, target = self.server(); self.assertEqual(wire.read_frame(proc)[0], 1)
                self.rejected(proc, target, data)
        proc, target = self.server(features=1); self.assertEqual(wire.read_frame(proc)[0], 1)
        self.rejected(proc, target, wire.frame(31, wire.string('0') + b'\0'))
        proc, target = self.server(role=b'S'); self.assertEqual(wire.read_frame(proc)[0], 1)
        self.rejected(proc, target, wire.frame(31, wire.string('0') + b'\0'))

    def test_root_and_entry_identity_overflow(self):
        for field in ('root_uid', 'root_gid', 'file_uid', 'file_gid'):
            for bad in (wire.var(1 << 32), b'\x80' * 10):
                with self.subTest(field=field, bad=bad):
                    proc, target = self.configured()
                    self.rejected(proc, target, self.directory(**{field: bad}))

    def test_fresh_identity_overflow_before_file_publication(self):
        for field in (0, 1):
            for bad in (wire.var(1 << 32), b'\x80' * 10):
                with self.subTest(field=field, bad=bad):
                    proc, target = self.configured()
                    proc.stdin.write(self.directory()); proc.stdin.flush()
                    self.assertEqual(wire.read_frame(proc)[0], 3)
                    identities = [wire.var(os.getuid()), wire.var(os.getgid())]; identities[field] = bad
                    raw = b'\0\0\1' + wire.var(0o644) + b''.join(identities) + b'\0\0' + wire.string('data')
                    proc.stdin.write(xwire.data_record(raw)); proc.stdin.flush()
                    kind, message = wire.read_frame(proc)
                    self.assertEqual((kind, message[:2]), (8, b'\2\2'))
                    proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 2)
                    self.assertFalse((target / 'file').exists())

    def test_overrides_apply_to_fresh_source_identities(self):
        proc, target = self.configured()
        proc.stdin.write(self.directory(file_uid=wire.var(60001), file_gid=wire.var(60002))); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 3)
        raw = b'\0\0\1' + wire.var(0o644) + wire.var(60003) + wire.var(60004) + b'\0\0' + wire.string('data')
        proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 7)
        proc.stdin.close(); proc.stdin = None; proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        st = (target / 'file').stat()
        self.assertEqual((st.st_uid, st.st_gid), (os.getuid(), os.getgid()))
        self.assertEqual((target / 'file').read_bytes(), b'data')

    def test_explicit_helper_requires_negotiation_and_disjoint_fields(self):
        for helper, features, payload, status in (
            (['--chown=0'], 1, None, 4),
            (['--chown=0'], 1 | 4 | CHOWN, wire.string('0') + b'\0', 1),
            (['--chown=:0'], 1 | 4 | CHOWN, b'\0' + wire.string('0'), 1),
        ):
            with self.subTest(helper=helper, status=status):
                proc, target = self.server(features=features, helper=helper)
                kind, message = wire.read_frame(proc)
                if payload is not None:
                    self.assertEqual(kind, 1)
                    proc.stdin.write(wire.frame(31, payload)); proc.stdin.flush()
                    kind, message = wire.read_frame(proc)
                self.assertEqual((kind, message[:2]), (8, bytes([2, status])))
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, status)
                self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
