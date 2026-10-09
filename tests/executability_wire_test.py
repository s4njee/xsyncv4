#!/usr/bin/env python3
"""Fresh execution bits use the original destination mode, not a prior plan."""
import os
import shutil
import subprocess
import unittest

import filter_wire_test as configured
import wire_test as wire
import xattrs_wire_test as xwire

EXECUTABILITY = 67108864


class ExecutabilityWireTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)

    def test_fresh_bits_retain_original_destination_read_and_execute_classes(self):
        for listed, fresh, destination, expected in ((0o600, 0o744, 0o601, 0o601),
                                                    (0o744, 0o600, 0o750, 0o640),
                                                    (0o600, 0o744, 0o640, 0o750),
                                                    (0o744, 0o744, 0o640, 0o750)):
            with self.subTest(listed=listed, fresh=fresh, destination=destination):
                target = self.root / 'uncreated'
                if target.exists(): shutil.rmtree(target)
                target.mkdir(); (target / 'file').write_bytes(b'old'); (target / 'file').chmod(destination)
                proc, target = self.server(features=1 | EXECUTABILITY)
                self.assertEqual(wire.read_frame(proc)[0], 10)
                body = wire.string('') + wire.var(0o755) + b'\0' * 4 + b'\1' + wire.string('file')
                body += b'\1' + wire.var(listed) + b'\0' * 2 + wire.var(4)
                proc.stdin.write(wire.frame(2, b'\0\0\0\1' + body)); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 3)
                raw = b'\0\0\1' + wire.var(fresh) + b'\0' * 4 + wire.string(b'data')
                proc.stdin.write(xwire.data_record(raw) + wire.frame(5, b'\0' * 5) + wire.frame(6, b'\0')); proc.stdin.flush()
                self.assertEqual(wire.read_frame(proc)[0], 7)
                proc.stdin.close(); proc.stdin = None; proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual((target / 'file').stat().st_mode & 0o7777, expected)
                self.assertEqual((target / 'file').read_bytes(), b'data')

    def test_explicit_helper_option_requires_negotiation(self):
        target = self.root / 'uncreated'
        options = bytes(name == 'recursive' for name in wire.BOOLS) + b''.join(wire.var(0) for _ in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1) + options + b'\0\1' + wire.string(str(target))
        proc = subprocess.Popen([str(wire.BINARY), '--server', '-E'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close, proc)
        proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
        kind, message = wire.read_frame(proc)
        self.assertEqual((kind, message[:2]), (8, b'\2\4'))
        proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 4)
        self.assertFalse(target.exists())


if __name__ == '__main__': unittest.main()
