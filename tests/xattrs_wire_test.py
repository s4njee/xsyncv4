#!/usr/bin/env python3
"""Negotiated xattrs are validated before metadata or file publication."""
import ctypes
import base64
import ctypes.util
import struct
import subprocess
import os
import unittest

import filter_wire_test as configured
import wire_test as wire
from xattrs_test import attr_name, get_attrs, set_attr


def attributes(pairs=(), complete=1):
    return bytes([complete]) + wire.var(len(pairs)) + b''.join(wire.string(name) + b'\0' + wire.string(value) for name, value in pairs)


def directory(root_attrs=None, entry_attrs=None):
    root_attrs = attributes() if root_attrs is None else root_attrs
    body = wire.string('') + wire.var(0o755) + b'\0' * 4 + root_attrs
    if entry_attrs is None:
        body += wire.var(0)
    else:
        body += wire.var(1) + wire.string('file') + b'\1' + wire.var(0o644) + b'\0\0' + wire.var(4) + entry_attrs
    return wire.frame(2, b'\0\0\0\1' + body)


def checksum(raw):
    lib = ctypes.CDLL(ctypes.util.find_library('xxhash'))
    lib.XXH3_64bits.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
    lib.XXH3_64bits.restype = ctypes.c_uint64
    return struct.pack('<Q', lib.XXH3_64bits(raw, len(raw)))


def data_record(raw):
    return wire.frame(4, b'\0' + checksum(raw) + raw)


def stream(value, ident=1):
    result = wire.frame(27, wire.var(ident) + wire.var(len(value)))
    for offset in range(0, len(value), 65536):
        result += wire.frame(28, wire.var(ident) + wire.var(offset) + wire.string(value[offset:offset + 65536]))
    return result + wire.frame(29, wire.var(ident) + checksum(value))


def reference(name, ident=1):
    return b'\1\1' + wire.string(name) + b'\1' + wire.var(ident)


class XattrWireTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def configured(self, deleting=False):
        proc, target = self.server(features=786433, deleting=deleting)
        proc.stdin.write(wire.frame(26, b'\1')); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 10)
        return proc, target

    def test_configurations(self):
        for value in (b'', b'\0', b'\3', b'\xff', b'\1x'):
            with self.subTest(value=value):
                proc, target = self.server(features=786433)
                self.rejected(proc, target, wire.frame(26, value))
        proc, target = self.server(features=786433)
        self.rejected(proc, target, wire.frame(2, b''))
        proc, target = self.server(features=786433)
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

    def test_stream_capability_required_before_destination_work(self):
        for features, status in ((262145, 4), (524289, 2)):
            options = bytes(name == 'recursive' for name in wire.BOOLS)
            options += b''.join(wire.var(2 if name == 'jobs' else 0) for name in wire.INTS)
            target = self.root / 'uncreated'
            hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(features) + options + b'\0\1' + wire.string(str(target))
            proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.addCleanup(self.close, proc)
            proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
            kind, payload = wire.read_frame(proc)
            self.assertEqual((kind, payload[:2]), (8, bytes([2, status])))
            proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, status)
            self.assertFalse(target.exists())

    def test_invalid_streams_before_directory_creation(self):
        start = wire.frame(27, b'\1\3')
        chunk = wire.frame(28, b'\1\0' + wire.string(b'abc'))
        ending = wire.frame(29, b'\1' + checksum(b'abc'))
        for label, frames in (
            ('missing-start', chunk), ('missing-end', ending),
            ('too-many-active', b''.join(wire.frame(27, wire.var(i) + b'\3') for i in range(1, 66))),
            ('empty-start', wire.frame(27, b'')), ('zero-id', wire.frame(27, b'\0\3')),
            ('unordered-id', wire.frame(27, b'\2\3')), ('zero-size', wire.frame(27, b'\1\0')),
            ('huge-size', wire.frame(27, b'\1' + wire.var(1 << 63))),
            ('overflow-id', wire.frame(27, b'\x81' + b'\x80' * 8 + b'\x02\3')),
            ('overflow-size', wire.frame(27, b'\1' + b'\x81' + b'\x80' * 8 + b'\x02')),
            ('large-chunk', wire.frame(27, b'\1' + wire.var(65537)) + wire.frame(28, b'\1\0' + wire.string(b'x' * 65537))),
            ('trailing-start', start + wire.frame(27, b'\2\3x')),
            ('duplicate-start', start + start),
            ('start-header', struct.pack('<IB', 21, 27)),
            ('chunk-header', struct.pack('<IB', 65536 + 33, 28)),
            ('end-header', struct.pack('<IB', 19, 29)),
            ('empty-chunk', start + wire.frame(28, b'\1\0\0')),
            ('offset-gap', start + wire.frame(28, b'\1\1' + wire.string(b'a'))),
            ('overrun', start + wire.frame(28, b'\1\0' + wire.string(b'abcd'))),
            ('duplicate-chunk', start + chunk + chunk),
            ('trailing-chunk', start + wire.frame(28, b'\1\0' + wire.string(b'abc') + b'x')),
            ('early-end', start + ending), ('short-end', start + chunk + wire.frame(29, b'\1x')),
            ('duplicate-end', start + chunk + ending + ending),
            ('chunk-after-end', start + chunk + ending + chunk),
            ('forward-reference', directory(root_attrs=reference('user.foo'))),
            ('unfinished-reference', start + directory(root_attrs=reference('user.foo'))),
            ('duplicate-reference', stream(b'abc') + directory(root_attrs=b'\1\2' + reference('user.foo')[2:] + reference('user.bar')[2:])),
            ('unknown-kind', directory(root_attrs=b'\1\1' + wire.string('user.foo') + b'\2')),
            ('large-inline', directory(root_attrs=attributes([('user.foo', b'x' * 65537)]))),
        ):
            with self.subTest(label=label):
                proc, target = self.configured()
                self.rejected(proc, target, frames)
        proc, target = self.server(features=1)
        self.rejected(proc, target, start)

    def test_stream_storage_failure_precedes_destination_work(self):
        self.env = dict(os.environ, TMPDIR=str(self.root / 'missing temporary directory'))
        proc, target = self.configured()
        proc.stdin.write(wire.frame(27, b'\1\3')); proc.stdin.flush()
        kind, payload = wire.read_frame(proc)
        self.assertEqual((kind, payload[:2]), (8, b'\2\x0b'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 11)
        self.assertFalse(target.exists())

    def test_stream_checksum_rejects_corruption(self):
        proc, target = self.configured()
        proc.stdin.write(stream(b'abc')[:-8] + checksum(b'bad')); proc.stdin.flush()
        kind, payload = wire.read_frame(proc)
        self.assertEqual((kind, payload[:2]), (8, b'\2\x0c'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 12)
        self.assertFalse(target.exists())

    def test_interleaved_streams_apply_binary_values(self):
        name = attr_name('wire-stream')
        value = b'\0\xffstreamed value'
        proc, target = self.configured()
        # Small values also use the stream when the sender's inline quota is full.
        frames = wire.frame(27, b'\1' + wire.var(len(value))) + wire.frame(27, b'\2\3')
        frames += wire.frame(28, b'\2\0' + wire.string(b'abc'))
        frames += wire.frame(28, b'\1\0' + wire.string(value))
        frames += wire.frame(29, b'\2' + checksum(b'abc')) + wire.frame(29, b'\1' + checksum(value))
        # Darwin's canonical names carry a user. prefix on the wire.
        canonical = name if name.startswith('user.') else 'user.' + name
        attrs = b'\1\2' + reference(canonical, 1)[2:] + reference(canonical + '-second', 2)[2:]
        proc.stdin.write(frames + directory(root_attrs=attrs) + wire.frame(5, b'') + wire.frame(6, b'\0')); proc.stdin.flush()
        while wire.read_frame(proc)[0] != 7: pass
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(base64.b64decode(get_attrs(target)[name]), value)
        self.assertEqual(base64.b64decode(get_attrs(target)[name + '-second']), b'abc')

    def test_unreferenced_stream_protects_deletion(self):
        for frames in (wire.frame(27, b'\1\3'), stream(b'abc')):
            proc, target = self.configured(deleting=True)
            target.mkdir(exist_ok=True)
            (target / 'extra').write_bytes(b'keep')
            proc.stdin.write(frames + directory() + wire.frame(5, b'') + wire.frame(6, b'\0')); proc.stdin.flush()
            while True:
                kind, payload = wire.read_frame(proc)
                if kind == 8 and payload[:1] == b'\2': break
            self.assertEqual(payload[:2], b'\2\2')
            proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 2)
            self.assertEqual((target / 'extra').read_bytes(), b'keep')

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
