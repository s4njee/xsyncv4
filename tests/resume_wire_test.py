#!/usr/bin/env python3
"""Resume validation and partial-prefix integrity under out-of-order wire data."""
import ctypes
import ctypes.util
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

import wire_test as wire
from wire_test import var, string, frame, directory, read_frame

MIB = 1024 * 1024
BINARY = wire.BINARY


class ResumeWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = ctypes.CDLL(ctypes.util.find_library('xxhash'))
        cls.lib.XXH3_64bits.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
        cls.lib.XXH3_64bits.restype = ctypes.c_uint64

    def data(self, raw):
        import struct
        return frame(4, b'\0' + struct.pack('<Q', self.lib.XXH3_64bits(raw, len(raw))) + raw)

    def chunk(self, offset, data, prefix=0):
        return self.data(var(0) + var(0) + b'\2' + var(0) + var(prefix) + var(offset) + var(2 * MIB) + string(data))

    def end(self, prefix=0):
        return self.data(var(0) + var(0) + b'\10' + var(0) + var(prefix) + var(2 * MIB) + b'\0' + var(0o644) + b'\0' * 4)

    def start(self, destination):
        options = bytes(name in ('recursive', 'perms', 'partial') for name in wire.BOOLS)
        options += b''.join(var(1 if name == 'max_delete' else 4 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + var(wire.VERSION) + b'R' + var(31) + options + b'\0\1' + string(str(destination))
        proc = subprocess.Popen([str(BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def cleanup():
            if proc.poll() is None: proc.kill()
            proc.communicate(timeout=5)
        self.addCleanup(cleanup)
        proc.stdin.write(frame(1, hello))
        proc.stdin.flush()
        for _ in range(2): self.assertIn(read_frame(proc)[0], (1, 10))
        proc.stdin.write(directory([('large', 1, var(2 * MIB))]))
        proc.stdin.flush()
        while read_frame(proc)[0] != 3: pass
        return proc

    def finish(self, proc):
        proc.stdin.write(frame(6, var(0)))
        proc.stdin.flush()
        while read_frame(proc)[0] != 7: pass
        proc.stdin.close()
        proc.stdin = None
        return proc.communicate(timeout=5)

    def test_gap_is_not_retained_as_verified_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            proc = self.start(root)
            proc.stdin.write(self.chunk(MIB, b'B' * MIB))
            proc.stdin.flush()
            deadline = time.monotonic() + 5
            while not any(p.stat().st_size == 2 * MIB for p in root.glob('.large.*')):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.005)
            proc.stdin.close()
            proc.stdin = None
            proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 12)
            self.assertEqual((root / 'large').stat().st_size, 0)
            self.assertEqual(list(root.glob('.large.*')), [])

    def test_completion_and_chunks_can_arrive_out_of_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            proc = self.start(root)
            proc.stdin.write(self.end() + self.chunk(MIB, b'B' * MIB) + self.chunk(0, b'A' * MIB))
            self.finish(proc)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual((root / 'large').read_bytes(), b'A' * MIB + b'B' * MIB)

    def test_unoffered_prefix_and_overlapping_chunks_fail(self):
        for kind in ('unoffered', 'overlap'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                proc = self.start(root)
                if kind == 'unoffered': bad = self.chunk(MIB, b'B' * MIB, prefix=1)
                else: bad = self.chunk(0, b'A' * MIB) + self.chunk(0, b'B' * MIB)
                proc.stdin.write(bad)
                proc.stdin.flush()
                proc.wait(timeout=5)
                proc.stdin.close()
                proc.stdin = None
                out, err = proc.communicate(timeout=5)
                self.assertEqual(proc.returncode, 2, err)
                self.assertIn(b'protocol error', out)

    def test_changed_destination_prefix_is_never_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            target = root / 'large'
            target.write_bytes(b'A' * MIB)
            proc = self.start(root)
            # The receiver has already sent the old A prefix's hash in NEED.
            target.write_bytes(b'C' * MIB)
            proc.stdin.write(self.chunk(MIB, b'B' * MIB, prefix=MIB) + self.end(prefix=MIB))
            out, err = self.finish(proc)
            self.assertEqual(proc.returncode, 23, err)
            self.assertEqual(target.read_bytes(), b'C' * MIB)
            self.assertEqual(list(root.glob('.large.*')), [])


if __name__ == '__main__':
    unittest.main()
