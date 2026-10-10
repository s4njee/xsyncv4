#!/usr/bin/env python3
"""ACL fields and identities must be checked before destination publication."""
import os
import ctypes
import struct
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire
import xattrs_wire_test as xwire
from acls_test import get_acl, set_acl
from xattrs_test import DARWIN

CAPABILITY = (2097152 | 4194304) if DARWIN else 1048576
UNDEFINED = 0xffffffff


def record(tag, permissions=4, flags=0, ident=60000, name=b''):
    return b''.join(wire.var(value) for value in (tag, permissions, flags, ident)) + wire.string(name)


def acl(access=(), defaults=(), complete=1, flags=0):
    return bytes([complete]) + wire.var(flags) + wire.var(len(access)) + b''.join(access) + wire.var(len(defaults)) + b''.join(defaults)


def named_acl(ident=60000, name=b'', permission=4):
    if DARWIN: return acl([record(1, permissions=128, ident=ident, name=name)])
    return acl([record(1, 6, ident=UNDEFINED), record(2, permission, ident=ident, name=name),
                record(4, 4, ident=UNDEFINED), record(16, 4, ident=UNDEFINED), record(32, 4, ident=UNDEFINED)])


def directory(root=None, entry=None, kind=1):
    body = wire.string('') + wire.var(0o755) + b'\0' * 4 + (acl() if root is None else root)
    if entry is None: body += b'\0'
    else:
        extra = wire.var(4) if kind == 1 else wire.string('outside') if kind == 3 else b''
        body += b'\1' + wire.string('file') + bytes([kind]) + wire.var(0o644) + b'\0\0' + extra + entry
    return wire.frame(2, b'\0\0\0\1' + body)


class AclWireTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def configured(self, numeric=False, deleting=False):
        if not numeric:
            proc, target = self.server(features=1 | CAPABILITY, deleting=deleting)
        else:
            target = self.root / 'uncreated'
            options = bytes(name in ('recursive', 'numeric_ids') for name in wire.BOOLS)
            options += b''.join(wire.var(2 if name == 'jobs' else 0) for name in wire.INTS)
            hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1 | CAPABILITY) + options + b'\0\1' + wire.string(str(target))
            proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(self.close, proc)
            proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
            self.assertEqual(wire.read_frame(proc)[0], 1)
        proc.stdin.write(wire.frame(30, b'\1')); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def test_configuration_and_style_negotiation(self):
        for payload in (b'', b'\0', b'\2', b'\1x'):
            proc, target = self.server(features=1 | CAPABILITY)
            self.rejected(proc, target, wire.frame(30, payload))
        proc, target = self.server(features=1 | CAPABILITY)
        self.rejected(proc, target, wire.frame(2, b''))
        proc, target = self.configured()
        self.rejected(proc, target, wire.frame(30, b'\1'))
        proc, target = self.server(features=1)
        self.rejected(proc, target, wire.frame(30, b'\1'))
        proc, target = self.server(features=1 | CAPABILITY)
        self.rejected(proc, target, struct.pack('<IB', 1024 * 1024, 30))
        cases = [(3145729, 2), (1 | (1048576 if DARWIN else 2097152), 4), (4194305, 2)]
        if DARWIN: cases.append((2097153, 4))
        for features, status in cases:
            target = self.root / 'uncreated'
            options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
            hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(features) + options + b'\0\1' + wire.string(str(target))
            proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(self.close, proc)
            proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
            kind, message = wire.read_frame(proc)
            self.assertEqual((kind, message[:2]), (8, bytes([2, status])))
            proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, status)
            self.assertFalse(target.exists())

    def malformed(self):
        common = [b'', b'\2\0\0\0', b'\1\x80', b'\1\0\x80',
                  b'\1\0' + wire.var(8192), acl([record(0)]),
                  acl([record(1, ident=1 << 32)]), acl([record(1, permissions=1 << 32)]),
                  acl([record(1, flags=1 << 32)]), acl([record(1, name=b'a\0b')]),
                  acl([record(1, name=b'x' * 256)]), named_acl()[:-1],
                  acl([record(1)], complete=0), acl(flags=1 << 32),
                  b'\1\0\1' + b'\x81' + b'\x80' * 8 + b'\x02']
        if DARWIN:
            common += [acl([record(7)]), acl([record(1, permissions=1)]),
                       acl([record(1, flags=1)]), acl([record(1, ident=UNDEFINED)]),
                       acl(defaults=[record(1)]), acl(flags=2), acl([record(1)] * 129),
                       acl([record(5, ident=UNDEFINED, name=b'')]),
                       acl([record(6, ident=UNDEFINED, name=b'x' * 15)]),
                       acl([record(5, ident=UNDEFINED, name=b'x' * 17)]),
                       acl([record(6, ident=1, name=b'x' * 16)])]
        else:
            common += [acl([record(3)]), acl([record(1, 8, ident=UNDEFINED)]), acl(flags=1),
                       acl([record(1, flags=16, ident=UNDEFINED)]),
                       acl([record(1, ident=60000)]), acl([record(1, ident=UNDEFINED, name=b'root')]),
                       acl([record(2, ident=UNDEFINED)]), acl([record(2)]),
                       acl([record(1, ident=UNDEFINED)] * 2),
                       acl([record(32, ident=UNDEFINED), record(1, ident=UNDEFINED)]),
                       acl([record(1, ident=UNDEFINED), record(2, ident=2), record(2, ident=1), record(4, ident=UNDEFINED),
                            record(16, ident=UNDEFINED), record(32, ident=UNDEFINED)])]
        return common

    def test_directory_acl_validation_before_writes(self):
        for bad in self.malformed():
            for entry in (False, True):
                with self.subTest(bad=bad, entry=entry):
                    proc, target = self.configured()
                    self.rejected(proc, target, directory(entry=bad) if entry else directory(root=bad))
        for data in (directory(entry=named_acl(), kind=3), wire.frame(2, directory()[5:] + b'x')):
            proc, target = self.configured()
            self.rejected(proc, target, data)

    def test_fresh_data_acl_validation_before_publication(self):
        for bad in (*self.malformed(), acl(complete=0)):
            with self.subTest(bad=bad):
                proc, target = self.configured()
                proc.stdin.write(directory(entry=acl())); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + bad + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw)); proc.stdin.flush()
                kind, message = wire.read_frame(proc)
                self.assertEqual((kind, message[:2]), (8, b'\2\2'))
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 2)
                self.assertFalse((target / 'file').exists())

    @unittest.skipUnless(DARWIN, 'Darwin UUID ACL principals')
    def test_unresolved_binary_uuid_principals(self):
        import uuid
        principal = uuid.UUID('01234567-89ab-cdef-0012-3456789abcde')
        for numeric in (False, True):
            for tag in (5, 6):
                with self.subTest(numeric=numeric, tag=tag):
                    proc, target = self.configured(numeric=numeric)
                    proc.stdin.write(directory(entry=acl())); proc.stdin.flush()
                    self.assertEqual(wire.read_frame(proc)[0], 3)
                    metadata = acl([record(tag, permissions=128, ident=UNDEFINED, name=principal.bytes)])
                    raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + metadata + wire.string(b'data')
                    proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                    self.assertEqual(wire.read_frame(proc)[0], 7)
                    proc.stdin.close(); proc.stdin = None
                    proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 0)
                    self.assertEqual((target / 'file').read_bytes(), b'data')
                    result = get_acl(target / 'file').lower()
                    self.assertIn(str(principal), result)
                    self.assertIn(':allow:' if tag == 5 else ':deny:', result)

    def test_names_map_without_owner_group_and_numeric_ids_override(self):
        for numeric in (False, True):
            with self.subTest(numeric=numeric):
                proc, target = self.configured(numeric=numeric)
                proc.stdin.write(directory(entry=acl())); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + named_acl(name=b'root') + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 7)
                proc.stdin.close(); proc.stdin = None
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual((target / 'file').read_bytes(), b'data')
                result = get_acl(target / 'file')
                if DARWIN:
                    if numeric:
                        import uuid
                        qualifier = (ctypes.c_ubyte * 16)()
                        self.assertEqual(ctypes.CDLL(None).mbr_uid_to_uuid(60000, qualifier), 0)
                        self.assertIn(str(uuid.UUID(bytes=bytes(qualifier))).upper(), result)
                    else: self.assertIn(':root:', result)
                else:
                    data = os.getxattr(target / 'file', 'system.posix_acl_access')
                    self.assertEqual(struct.unpack_from('<I', data, 16)[0], 60000 if numeric else 0)
                import shutil
                shutil.rmtree(target)

    def test_incomplete_source_acl_preserves_existing_file_and_deletions(self):
        proc, target = self.configured(deleting=True)
        target.mkdir()
        file = target / 'file'; file.write_bytes(b'old!'); set_acl(file, 1)
        extra = target / 'extra'; extra.write_bytes(b'keep me')
        before = get_acl(file)
        proc.stdin.write(directory(entry=acl(complete=0))); proc.stdin.flush()
        while wire.read_frame(proc)[0] != 3: pass
        proc.stdin.write(wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
        while wire.read_frame(proc)[0] != 7: pass
        proc.stdin.close(); proc.stdin = None
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 23)
        self.assertEqual(file.read_bytes(), b'old!')
        self.assertEqual(get_acl(file), before)
        self.assertEqual(extra.read_bytes(), b'keep me')


if __name__ == '__main__': unittest.main()
