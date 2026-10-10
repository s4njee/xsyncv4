#!/usr/bin/env python3
"""Receiver directory retirement must preserve parents and protocol validation."""
import os
import pathlib
import subprocess
import tempfile
import unittest

import wire_test as wire

FEATURE = 1 << 35


def directory(entries=(), *, rel='', ident=0, parent=0, index=0, children=0):
    body = wire.string(rel) + wire.var(0o755) + b'\0' * 4
    body += wire.var(children) + wire.var(len(entries))
    for name in entries:
        body += wire.string(name) + b'\2' + wire.var(0o755) + b'\0\0\0'
    return wire.frame(2, wire.var(ident) + wire.var(parent) + wire.var(index) + b'\1' + body)


class DirectoryLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs-directory-lifetime-')
        self.addCleanup(self.tmp.cleanup)
        self.target = pathlib.Path(self.tmp.name) / 'target'
        options = bytes(name in ('recursive', 'perms') for name in wire.BOOLS)
        options += b''.join(wire.var(4 if name == 'jobs' else 1 if name == 'max_delete' else 0)
                            for name in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(1 | FEATURE)
        hello += options + b'\0\1' + wire.string(str(self.target))
        self.proc = subprocess.Popen([str(wire.BINARY), '--server'], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.addCleanup(self.close)
        self.send(wire.frame(1, hello))
        self.assertEqual({wire.read_frame(self.proc)[0], wire.read_frame(self.proc)[0]}, {1, 10})

    def close(self):
        if self.proc.poll() is None: self.proc.kill()
        self.proc.communicate()

    def send(self, data):
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def need(self, ident):
        kind, payload = wire.read_frame(self.proc)
        self.assertEqual(kind, 3, payload)
        self.assertEqual(payload, wire.var(ident) + b'\0')

    def finish(self):
        self.send(wire.frame(5, b'') + wire.frame(6, b'\0'))
        kind, payload = wire.read_frame(self.proc)
        self.assertEqual(kind, 7, payload)
        self.assertEqual(payload[0], 0)
        _, err = self.proc.communicate(timeout=10)
        self.assertEqual(self.proc.returncode, 0, err)

    def rejected(self, data):
        self.send(data)
        self.proc.wait(timeout=10)
        out, err = self.proc.communicate(timeout=10)
        self.assertEqual(self.proc.returncode, 2, err)
        self.assertIn(b'protocol error', out + err)

    def test_late_siblings_use_total_count_not_remaining_count(self):
        self.send(directory(('left', 'right'), children=2)); self.need(0)
        self.send(directory(rel='left', ident=1, parent=1)); self.need(1)
        # The first child's generator may have finished and retired before the
        # second arrives. A completed child must not consume a future slot.
        self.send(directory(rel='right', ident=2, parent=1, index=1)); self.need(2)
        self.finish()
        self.assertEqual(sorted(p.name for p in self.target.iterdir()), ['left', 'right'])

    def test_parent_survives_until_grandchild_finishes(self):
        self.send(directory(('child',), children=1)); self.need(0)
        self.send(directory(('grandchild',), rel='child', ident=1, parent=1, children=1)); self.need(1)
        self.send(directory(rel='child/grandchild', ident=2, parent=2)); self.need(2)
        self.finish()
        self.assertTrue((self.target / 'child/grandchild').is_dir())

    def test_missing_declared_child_is_not_success(self):
        self.send(directory(('child',), children=1)); self.need(0)
        self.rejected(wire.frame(5, b'') + wire.frame(6, b'\0'))

    def test_data_end_requires_list_end(self):
        self.send(directory()); self.need(0)
        self.rejected(wire.frame(6, b'\0'))

    def test_empty_registry_does_not_allow_a_missing_root(self):
        self.rejected(wire.frame(5, b'') + wire.frame(6, b'\0'))

    def test_count_cannot_exceed_listing(self):
        self.rejected(directory(('child',), children=2))

    def test_extra_child_is_rejected(self):
        self.send(directory(('left', 'right'), children=1)); self.need(0)
        self.send(directory(rel='left', ident=1, parent=1)); self.need(1)
        self.rejected(directory(rel='right', ident=2, parent=1, index=1))

    def test_duplicate_retired_id_is_rejected(self):
        self.send(directory()); self.need(0)
        self.rejected(directory())

    def test_child_after_zero_child_root_is_rejected(self):
        self.send(directory(('child',))); self.need(0)
        self.rejected(directory(rel='child', ident=1, parent=1))


if __name__ == '__main__': unittest.main()
