#!/usr/bin/env python3
"""Negotiated xattrs are validated before metadata or file publication."""
import ctypes
import ctypes.util
import struct
import unittest

import filter_wire_test as configured
import wire_test as wire
from xattrs_test import attr_name, get_attrs, set_attr


def attributes(pairs=(), complete=1):
    return bytes([complete]) + wire.var(len(pairs)) + b''.join(wire.string(name) + wire.string(value) for name, value in pairs)


def directory(root_attrs=None, entry_attrs=None):
    root_attrs = attributes() if root_attrs is None else root_attrs
    body = wire.string('') + wire.var(0o755) + b'\0' * 4 + root_attrs
    if entry_attrs is None:
        body += wire.var(0)
    else:
        body += wire.var(1) + wire.string('file') + b'\1' + wire.var(0o644) + b'\0\0' + wire.var(4) + entry_attrs
    return wire.frame(2, b'\0\0\0\1' + body)


def data_record(raw):
    lib = ctypes.CDLL(ctypes.util.find_library('xxhash'))
    lib.XXH3_64bits.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    lib.XXH3_64bits.restype = ctypes.c_uint64
    return wire.frame(4, b'\0' + struct.pack('<Q', lib.XXH3_64bits(raw, len(raw))) + raw)


class XattrWireTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def configured(self, deleting=False):
        proc, target = self.server(features=262145, deleting=deleting)
        proc.stdin.write(wire.frame(26, b'\1')); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def test_configurations(self):
        for value in (b'', b'\0', b'\3', b'\xff', b'\1x'):
            with self.subTest(value=value):
                proc, target = self.server(features=262145)
                self.rejected(proc, target, wire.frame(26, value))
        proc, target = self.server(features=262145)
        self.rejected(proc, target, wire.frame(2, b''))
        proc, target = self.server(features=262145)
        self.rejected(proc, target, struct.pack('<IB', 1024 * 1024, 26))
        proc, target = self.server(features=1)
        self.rejected(proc, target, wire.frame(26, b'\1'))
        proc, target = self.configured()
        self.rejected(proc, target, wire.frame(26, b'\1'))

    def malformed(self):
        return (
            b'', b'\2\0', b'\1\x80', b'\1' + wire.var(65537),
            attributes([(b'', b'x')]), attributes([(b'user.bad\0name', b'x')]),
            attributes([(b'user.' + b'x' * 1024, b'x')]),
            attributes([(b'user.same', b'a'), (b'user.same', b'b')]),
            b'\1\1' + wire.string('user.foo') + wire.var(10) + b'x',
            attributes([(b'user.foo', b'x')], complete=0),
        )

    def test_directory_attribute_validation(self):
        for bad in self.malformed():
            for entry in (False, True):
                with self.subTest(bad=bad, entry=entry):
                    proc, target = self.configured()
                    self.rejected(proc, target, directory(entry_attrs=bad) if entry else directory(root_attrs=bad))
        proc, target = self.configured()
        self.rejected(proc, target, wire.frame(2, directory()[5:] + b'x'))

    def test_data_attributes_validated_before_file_creation(self):
        for bad in (*self.malformed(), attributes(complete=0)):
            with self.subTest(bad=bad):
                proc, target = self.configured()
                proc.stdin.write(directory(entry_attrs=attributes())); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                # R_WHOLE metadata precedes its file bytes.
                raw = b'\0\0\1' + wire.var(0o644) + b'\0' * 4 + bad + wire.string(b'data')
                proc.stdin.write(data_record(raw)); proc.stdin.flush()
                kind, message = wire.read_frame(proc)
                self.assertEqual(kind, 8)
                self.assertEqual(message[:2], b'\2\2')
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 2)
                self.assertFalse((target / 'file').exists())

    def test_incomplete_source_attributes_protect_destination_and_deletion(self):
        proc, target = self.configured(deleting=True)
        target.mkdir()
        (target / 'file').write_bytes(b'old!')
        (target / 'extra').write_bytes(b'keep extra')
        set_attr(target / 'file', attr_name('keep'), b'\0\xffprotected')
        before = get_attrs(target / 'file')
        proc.stdin.write(directory(entry_attrs=attributes(complete=0)) + wire.frame(5, b'') + wire.frame(6, wire.var(23)))
        proc.stdin.flush()
        while True:
            kind, payload = wire.read_frame(proc)
            if kind == 7:
                self.assertEqual(payload[0], 23)
                break
            self.assertIn(kind, (3, 8))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 23)
        self.assertEqual((target / 'file').read_bytes(), b'old!')
        self.assertEqual(get_attrs(target / 'file'), before)
        self.assertEqual((target / 'extra').read_bytes(), b'keep extra')


if __name__ == '__main__': unittest.main()
