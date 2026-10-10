#!/usr/bin/env python3
"""Check benchmark ownership and independent verification safeguards."""
import fcntl
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'file').write_bytes(b'expected payload\n')
        self.work = self.root / 'work'
        self.output = self.root / 'result.json'

    def run_harness(self, *extra):
        return subprocess.run([sys.executable, str(HERE / 'run.py'),
                               '--corpus', str(self.source), '--work', str(self.work),
                               '--output', str(self.output), *extra],
                              capture_output=True, text=True, timeout=20)

    def test_unowned_destination_is_preserved(self):
        self.work.mkdir()
        sentinel = self.work / 'valuable'
        sentinel.write_text('keep')
        result = self.run_harness()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no benchmark ownership marker', result.stderr)
        self.assertEqual(sentinel.read_text(), 'keep')
        self.assertFalse(self.output.exists())

    def test_concurrent_owner_is_rejected(self):
        self.work.mkdir()
        (self.work / '.xs-benchmark-work').touch()
        with (self.work / '.xs-benchmark-lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_harness()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('another benchmark owns', result.stderr)
        self.assertFalse(self.output.exists())

    def test_path_escape_is_rejected_before_work_creation(self):
        result = self.run_harness('--label', '../elsewhere')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('safe file name', result.stderr)
        self.assertFalse(self.work.exists())

    def test_successful_but_corrupt_tool_is_not_reported_as_complete(self):
        rsync = shutil.which('rsync')
        if not rsync:
            self.skipTest('rsync required for independent verification')
        fake = self.root / 'corrupt-xs'
        fake.write_text('#!/usr/bin/env python3\n'
                        'import pathlib, sys\n'
                        'if "--version" in sys.argv:\n'
                        '    print("deliberately corrupt fixture")\n'
                        'else:\n'
                        '    dest = pathlib.Path(sys.argv[-1])\n'
                        '    dest.mkdir(parents=True)\n'
                        '    (dest / "file").write_bytes(b"corruption\\n")\n')
        fake.chmod(0o755)
        result = self.run_harness('--runs', '1', '--scenarios', 'fresh',
                                  '--rsync', rsync, '--xsync', str(fake))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('verification failed', result.stderr)
        data = json.loads(self.output.read_text())
        self.assertFalse(data.get('complete', False))
        self.assertEqual([r['tool'] for r in data['records']], ['rsync'])

    def test_resource_wrapper_preserves_stdio_and_exit_status(self):
        metrics = self.root / 'metrics.json'
        result = subprocess.run([sys.executable, str(HERE / 'measure.py'),
                                 '--metrics', str(metrics), '--', sys.executable, '-c',
                                 'import sys; data=sys.stdin.buffer.read(); '
                                 'sys.stdout.buffer.write(data); sys.stderr.write("diagnostic"); '
                                 'sys.exit(7)'], input=b'\x00wire\xff\n', capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, b'\x00wire\xff\n')
        self.assertEqual(result.stderr, b'diagnostic')
        data = json.loads(metrics.read_text())
        self.assertEqual(data['returncode'], 7)
        self.assertGreater(data['max_rss_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
