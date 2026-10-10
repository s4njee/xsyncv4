#!/usr/bin/env python3
"""Malformed negotiated compression policies fail before opening a destination."""
import os
import struct
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire

POLICY = 17179869184


class CompressionWireTests(unittest.TestCase):
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected
    setUp = configured.FilterWireTests.setUp

    def server(self, compress=True):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' or (compress and name == 'compress') for name in wire.BOOLS)
        options += b''.join(wire.var(6 if name == 'compress_level' else 2 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(3 | POLICY) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        self.assertEqual(wire.read_frame(proc)[0], 1)
        return proc, target

    def test_bad_flags_truncation_suffixes_and_trailing_bytes(self):
        payloads = (b'', b'\2' + wire.string('gz'), b'\0\5gz', b'\0' + wire.string('[]'),
                    b'\0' + wire.string(b'gz\0zip'), b'\0' + wire.string('gz') + b'extra',
                    b'\0' + wire.string('x' * 65537))
        for payload in payloads:
            with self.subTest(length=len(payload)):
                proc, target = self.server()
                self.rejected(proc, target, wire.frame(37, payload))

    def test_wrong_frame_type_and_policy_without_compression(self):
        proc, target = self.server()
        self.rejected(proc, target, wire.frame(2, b'\0' + wire.string('gz')))
        proc, target = self.server(compress=False)
        self.rejected(proc, target, wire.frame(37, b'\0' + wire.string('gz')))

    def test_oversized_header_is_rejected_without_waiting_for_body(self):
        proc, target = self.server()
        self.rejected(proc, target, struct.pack('<IB', 1 << 20, 37))


if __name__ == '__main__': unittest.main()
