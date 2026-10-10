#!/usr/bin/env python3
"""Parse machine progress on pipes and PTYs, including actual remote file events."""
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import unittest

import output_test as output_fixture
from output_test import BINARY, HOST
from progress_test import capture, ENV
from progress_ack_test import PREAMBLE

LINE = re.compile(rb'^\s*[\d,]+\s+\d+%\s+[\d.]+(?:B|kB|MB|GB|TB)/s\s+\d+:\d\d:\d\d \(xfr#\d+, (?:ir|to)-chk=\d+/\d+\)$')


class MachineProgressTests(unittest.TestCase):
    setUp = output_fixture.OutputTests.setUp
    refresh_remote = output_fixture.OutputTests.refresh_remote
    run_copy = output_fixture.OutputTests.run_copy

    @classmethod
    def setUpClass(cls):
        output_fixture.OutputTests.setUpClass.__func__(cls)

    def records(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'')
        self.assertNotIn(b'\x1b', result.stderr)
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(rows[0]['type'], 'progress')
        self.assertEqual(rows[-1]['type'], 'complete')
        self.assertTrue(rows[-1]['success'])
        self.assertEqual(rows[-1]['exit_code'], 0)
        self.assertFalse(rows[-1]['scanning'])
        return rows

    def test_json_file_events_local_push_pull(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                rows = self.records(self.run_copy(direction, ['--progress=json'], name=direction))
                files = [r for r in rows if r['type'] == 'file']
                self.assertEqual(sorted(r['path'] for r in files), ['a', 'sub/nested', 'utf8-é', 'z'])
                self.assertEqual(rows[-1]['files'], 4)
                self.assertEqual(rows[-1]['bytes'], 19)
                for row in files:
                    self.assertEqual(bytes.fromhex(row['path_bytes_hex']), os.fsencode(row['path']))

    def test_json_ticks_and_raw_byte_counters(self):
        (self.source / 'large').write_bytes(b'x' * (2 * 1024 * 1024))
        rows = self.records(self.run_copy(flags=['--progress=json', '--bwlimit=1024']))
        ticks = [r for r in rows if r['type'] == 'progress']
        self.assertGreater(len(ticks), 5)
        self.assertEqual(rows[-1]['bytes'], 2 * 1024 * 1024 + 19)
        self.assertEqual(rows[-1]['files'], 5)
        self.assertEqual(sorted(r['elapsed_ms'] for r in ticks), [r['elapsed_ms'] for r in ticks])
        self.assertTrue(all(type(r['bytes']) is int for r in ticks))

    def test_json_name_escaping_and_terminal(self):
        name = 'quote"-slash\\-tab\t-newline\n-é'
        (self.source / name).write_bytes(b'name')
        if sys.platform != 'darwin':
            with open(os.fsencode(self.source) + b'/invalid-\xff', 'wb') as out: out.write(b'invalid')
        code, data = capture([str(BINARY), '--no-fallback', '-a', '--no-clone', '--progress=json', '-8',
                              str(self.source) + '/', str(self.root / 'target')], env=ENV)
        rows = self.records(subprocess.CompletedProcess([], code, b'', data))
        files = [r for r in rows if r['type'] == 'file']
        self.assertIn(name, [r['path'] for r in files])
        if sys.platform != 'darwin':
            self.assertIn(b'invalid-\xff', [bytes.fromhex(r['path_bytes_hex']) for r in files])

    def test_progress2_line_shape_local_push_pull(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                result = self.run_copy(direction, ['--info=progress2'], name=direction)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'')
                self.assertNotIn(b'\x1b', result.stderr)
                self.assertTrue(result.stderr.splitlines())
                for line in result.stderr.splitlines(): self.assertRegex(line, LINE)
                self.assertIn(b'100%', result.stderr.splitlines()[-1])
                self.assertIn(b'(xfr#4, to-chk=0/', result.stderr.splitlines()[-1])

    def test_mode_precedence_quiet_and_validation(self):
        result = self.run_copy(flags=['--progress=json', '--info=progress2'])
        self.assertRegex(result.stderr.splitlines()[-1], LINE)
        result = self.run_copy(flags=['--info=progress2', '--progress=json'], name='json')
        self.records(result)
        for flag in ('--no-progress', '--quiet'):
            result = self.run_copy(flags=['--progress=json', flag], name=flag)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, b'')
        for flag in ('--progress=other', '--no-progress=json'):
            result = self.run_copy(flags=[flag], name=flag)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'--progress accepts only =json', result.stderr)

    def test_json_dry_run_file_events(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                rows = self.records(self.run_copy(direction, ['--progress=json', '-n'], name='dry-' + direction))
                self.assertEqual(sorted(r['path'] for r in rows if r['type'] == 'file'),
                                 ['a', 'sub/nested', 'utf8-é', 'z'])
                self.assertTrue(all(r['dry_run'] for r in rows))
                self.assertFalse((self.root / ('dry-' + direction)).exists())

    def test_json_requires_native_structured_peer(self):
        peer = self.root / 'old-peer.py'
        peer.write_text(PREAMBLE + '\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var(1))\ntime.sleep(.2)\n')
        result = subprocess.run([str(BINARY), '--no-fallback', '-r', '--numeric-ids', '--progress=json',
                                 '-e', shlex.join([sys.executable, str(peer)]), '--rsync-path=unused',
                                 'fake:source', str(self.root / 'target')], env=ENV, capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'peer does not support JSON file events', result.stderr)
        self.assertFalse((self.root / 'target').exists())
        for flags in (['--progress=json', '-b'], ['-b', '--progress=json']):
            result = self.run_copy(flags=flags, name='fallback')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'JSON progress requires a native transfer', result.stderr)

    @unittest.skipUnless(sys.platform == 'darwin', 'whole-directory clones require APFS')
    def test_json_clones_emit_each_file(self):
        rows = self.records(self.run_copy(flags=['--clone', '--progress=json']))
        self.assertEqual(sorted(r['path'] for r in rows if r['type'] == 'file'),
                         ['a', 'sub/nested', 'utf8-é', 'z'])


if __name__ == '__main__':
    unittest.main()
