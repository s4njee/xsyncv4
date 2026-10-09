#!/usr/bin/env python3
"""Negotiated delta records: bounds, completion, integrity and receiver anchoring."""
import ctypes
import ctypes.util
import pathlib
import random
import struct
import subprocess
import tempfile
import unittest

import wire_test as wire
from wire_test import var, string, frame, directory, read_frame

MIB = 1024 * 1024

def take_var(data, position=0):
    result = shift = 0
    while True:
        byte = data[position]; position += 1
        result |= (byte & 127) << shift
        if not byte & 128: return result, position
        shift += 7

class Hash128(ctypes.Structure):
    _fields_ = [('low', ctypes.c_uint64), ('high', ctypes.c_uint64)]

class DeltaWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ctypes.CDLL(ctypes.util.find_library('xxhash'))
        cls.lib.XXH3_64bits.argtypes = cls.lib.XXH3_128bits.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
        cls.lib.XXH3_64bits.restype = ctypes.c_uint64
        cls.lib.XXH3_128bits.restype = Hash128
        cls.basis = random.Random(32).randbytes(2 * MIB)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync delta wire ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.target = self.root / 'large'
        self.target.write_bytes(self.basis)

    def start(self, features=257, partial=False):
        options = bytes(name in ('recursive', 'perms', 'ignore_times') or (partial and name == 'partial') for name in wire.BOOLS)
        options += b''.join(var(1 if name == 'max_delete' else 4 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + var(wire.VERSION) + b'R' + var(features) + options + b'\0\1' + string(str(self.root))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None: proc.kill()
            proc.communicate(timeout=5)
        self.addCleanup(cleanup)
        proc.stdin.write(frame(1, hello)); proc.stdin.flush()
        for _ in range(2): self.assertIn(read_frame(proc)[0], (1, 10))
        proc.stdin.write(directory([('large', 1, var(len(self.basis)))])); proc.stdin.flush()
        while read_frame(proc)[0] != 3: pass
        return proc

    def signatures(self, proc):
        proc.stdin.write(frame(13, var(0) + var(0))); proc.stdin.flush()
        while True:
            kind, payload = read_frame(proc)
            if kind == 14: break
            self.assertNotEqual(kind, 8, payload)
        self.assertEqual(payload[:4], b'\0\0\0\1')
        size, position = take_var(payload, 4)
        block, position = take_var(payload, position)
        count, position = take_var(payload, position)
        self.assertEqual(size, len(self.basis))
        self.assertEqual(len(payload) - position, 12 * count)
        return block, count

    def data(self, raw):
        return frame(4, b'\0' + struct.pack('<Q', self.lib.XXH3_64bits(raw, len(raw))) + raw)

    def copy(self, first, count, offset=0, total=None, attempt=0):
        return self.data(b'\0\0\100' + var(attempt) + var(offset) + var(total or len(self.basis)) + var(first) + var(count))

    def end(self, digest=None, status=0, total=None, attempt=0):
        if digest is None:
            h = self.lib.XXH3_128bits(self.basis, len(self.basis)); digest = struct.pack('<QQ', h.low, h.high)
        return self.data(b'\0\0\40' + var(attempt) + var(len(self.basis) if total is None else total) + bytes([status]) +
                         var(0o644) + b'\0' * 4 + digest)

    def finish(self, proc):
        proc.stdin.write(frame(5, b'') + frame(6, var(0))); proc.stdin.flush()
        while read_frame(proc)[0] != 7: pass
        proc.stdin.close(); proc.stdin = None
        return proc.communicate(timeout=10)

    def reject(self, proc, data):
        proc.stdin.write(data); proc.stdin.flush()
        proc.wait(timeout=10)
        proc.stdin.close(); proc.stdin = None
        out, err = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 2, (out, err))
        self.assertIn(b'protocol error', out)

    def test_unnegotiated_unrequested_and_duplicate_signatures(self):
        for case in ('unnegotiated', 'index', 'trailing', 'duplicate'):
            with self.subTest(case=case):
                proc = self.start(1 if case == 'unnegotiated' else 257)
                if case == 'duplicate': self.signatures(proc)
                request = frame(13, var(0) + var(7 if case == 'index' else 0) + (b'X' if case == 'trailing' else b''))
                self.reject(proc, request)
                self.assertEqual(self.target.read_bytes(), self.basis)

    def test_bad_references_overlap_and_mixed_records(self):
        for case in ('unrequested', 'index', 'count', 'wide_index', 'wide_count', 'overlap', 'mixed', 'size', 'digest_short'):
            with self.subTest(case=case):
                proc = self.start()
                block, count = (4096, 512) if case == 'unrequested' else self.signatures(proc)
                bad = self.copy(count, 1) if case == 'index' else self.copy(0, count + 1) if case == 'count' else \
                      self.copy(1 << 32, 1) if case == 'wide_index' else self.copy(0, 1 << 32) if case == 'wide_count' else \
                      self.copy(0, count) + self.copy(0, 1) if case == 'overlap' else \
                      self.copy(0, 1) + self.data(b'\0\0\2\0\0' + var(len(self.basis)) + string(b'x')) if case == 'mixed' else \
                      self.copy(0, count) + self.end(total=len(self.basis) - 1) if case == 'size' else \
                      self.end(digest=b'x') if case == 'digest_short' else self.copy(0, count)
                self.reject(proc, bad)
                self.assertEqual(self.target.read_bytes(), self.basis)

    def test_out_of_order_completion_and_replay_rejection(self):
        proc = self.start(); block, count = self.signatures(proc)
        halfway = count // 2
        proc.stdin.write(self.end() + self.copy(halfway, count-halfway, halfway*block) + self.copy(0, halfway)); proc.stdin.flush()
        out, err = self.finish(proc)
        self.assertEqual(proc.returncode, 0, (out, err))
        self.assertEqual(self.target.read_bytes(), self.basis)
        proc = self.start(); block, count = self.signatures(proc)
        self.reject(proc, self.copy(0, count) + self.end() + self.end())

    def test_final_checksum_failure_never_retains_unverified_output(self):
        proc = self.start(partial=True); block, count = self.signatures(proc)
        proc.stdin.write(self.copy(0, count) + self.end(digest=b'\0' * 16))
        out, err = self.finish(proc)
        self.assertEqual(proc.returncode, 23, (out, err))
        self.assertEqual(self.target.read_bytes(), self.basis)
        self.assertEqual(list(self.root.glob('.large.*')), [])

    def test_data_end_cannot_hide_missing_file_completion(self):
        for case in ('no_data', 'no_end', 'gap'):
            with self.subTest(case=case):
                proc = self.start(); block, count = self.signatures(proc)
                records = b'' if case == 'no_data' else self.copy(0, count) if case == 'no_end' else self.end() + self.copy(1, count-1, block)
                self.reject(proc, records + frame(5, b'') + frame(6, var(0)))
                self.assertEqual(self.target.read_bytes(), self.basis)

    def test_changed_basis_fails_and_replaced_path_stays_anchored(self):
        for replace in (False, True):
            with self.subTest(replace=replace):
                self.target.write_bytes(self.basis)
                proc = self.start(); block, count = self.signatures(proc)
                outside = self.root / 'outside'; outside.write_bytes(b'outside sentinel')
                if replace: self.target.unlink(); self.target.symlink_to(outside)
                else:
                    with self.target.open('r+b') as stream: stream.write(b'changed basis')
                proc.stdin.write(self.copy(0, count) + self.end())
                out, err = self.finish(proc)
                self.assertEqual(proc.returncode, 0 if replace else 23, (out, err))
                if replace: self.assertEqual(self.target.read_bytes(), self.basis)
                self.assertEqual(outside.read_bytes(), b'outside sentinel')
                self.assertEqual(list(self.root.glob('.large.*')), [])

class DeltaSenderTrustTests(unittest.TestCase):
    def test_bad_signatures_flags_dimensions_and_unsolicited_replies(self):
        for case in ('flag', 'compression_flag', 'compression_limit', 'size', 'block', 'count', 'short', 'trailing', 'unsolicited_ack', 'unnegotiated'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                source = pathlib.Path(tmp) / 'source'
                source.write_bytes(b'A' * (2 * MIB))
                options = bytes(name == 'recursive' for name in wire.BOOLS)
                options += b''.join(var(1 if name == 'max_delete' else 2 if name == 'jobs' else 0) for name in wire.INTS)
                features = 1 if case == 'unnegotiated' else 259 if case == 'compression_limit' else 257
                hello = b'XSYNC\1' + var(wire.VERSION) + b'S' + var(features) + options + b'\0\1' + string(str(source))
                proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    proc.stdin.write(frame(1, hello)); proc.stdin.flush()
                    self.assertEqual(read_frame(proc)[0], 1)
                    proc.stdin.write(frame(10, string('') + string('') + b'\0\0')); proc.stdin.flush()
                    while read_frame(proc)[0] != 2: pass
                    if case != 'unnegotiated':
                        proc.stdin.write(frame(3, b'\0\1\0\1')); proc.stdin.flush()
                        while read_frame(proc)[0] != 13: pass
                    body = b'\2' if case == 'flag' else \
                           b'\1' + var(0) + var(4096) + var(1) if case == 'size' else \
                           b'\1' + var(2 * MIB) + var(0) + var(1) if case == 'block' else \
                           b'\1' + var(2 * MIB) + var(4096) + var(1 << 32) if case == 'count' else \
                           b'\1' + var(2 * MIB) + var(4096) + var(512) + b'x' if case == 'short' else b'\0X'
                    bad = frame(15, b'\0\0') if case == 'unsolicited_ack' else \
                          frame(14, b'\0\0\1' + var(1 << 30) + b'x') if case == 'compression_limit' else \
                          frame(14, b'\0\0' + (b'\2' if case == 'compression_flag' else b'\0') + body)
                    proc.stdin.write(bad); proc.stdin.flush(); proc.wait(timeout=10)
                    proc.stdin.close(); proc.stdin = None
                    out, err = proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode, 2, (out, err))
                    self.assertIn(b'protocol error', out)
                finally:
                    if proc.poll() is None: proc.kill()
                    proc.communicate(timeout=5)

if __name__ == '__main__': unittest.main()
