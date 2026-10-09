#!/usr/bin/env python3
"""Staged prune lists must be complete and valid before creating a destination."""
import unittest

import filter_wire_test as configured
import wire_test as wire


class PruneStreamTests(unittest.TestCase):
    setUp = configured.FilterWireTests.setUp
    server = configured.FilterWireTests.server
    close = staticmethod(configured.FilterWireTests.close)
    rejected = configured.FilterWireTests.rejected

    def test_incomplete_or_unsafe_staged_lists(self):
        for label, data in (
            ('end-before-list', wire.frame(6, wire.var(0))),
            ('staged-end-before-list', wire.directory([('file', 1, wire.var(1))]) + wire.frame(6, wire.var(0))),
            ('missing-root', wire.frame(5, b'')),
            ('unsafe-name', wire.directory([('..', 1, wire.var(1))]) + wire.frame(5, b'')),
            ('unsafe-child', wire.directory([('hot', 2, wire.var(0))]) +
             wire.directory(rel='../outside', ident=1, parent=1) + wire.frame(5, b'')),
        ):
            with self.subTest(label=label):
                proc, target = self.server(features=32769)
                proc.stdin.write(wire.frame(21, b'\1')); proc.stdin.flush()
                self.rejected(proc, target, data)


if __name__ == '__main__': unittest.main()
