#!/usr/bin/env python3
"""Exercise the gate with real transfers, delayed tools and corrupt output."""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
BINARY = HERE.parent / 'build' / 'xs'
RSYNC = shutil.which('rsync')
OUTPUT_ROOT = None


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        policy = json.loads((HERE / 'ci-policy.json').read_text())
        # These behavior checks run on potentially busy developer machines.
        # Hosted measurements use the stricter, unmodified checked-in policy.
        policy['minimum_relative_ratio'] = 0.60
        self.policy = self.root / 'policy.json'
        self.policy.write_text(json.dumps(policy))

    def gate(self, candidate, scenarios, samples=3, reference=None):
        output = self.root / 'result.json'
        command = [sys.executable, str(HERE / 'ci.py'), '--reference', str(reference or BINARY),
                   '--candidate', str(candidate), '--rsync', RSYNC,
                   '--work', str(self.root / 'work'), '--output', str(output),
                   '--policy', str(self.policy), '--samples', str(samples),
                   '--smoke-fixtures', '--scenarios', scenarios]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        data = json.loads(output.read_text())
        if OUTPUT_ROOT:
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
            proof = dict(data, self_test=self._testMethodName, production_measurement=False,
                         control_startup_delay_seconds=0.05 if reference else 0)
            (OUTPUT_ROOT / (self._testMethodName + '.json')).write_text(json.dumps(proof, indent=2) + '\n')
            (OUTPUT_ROOT / (self._testMethodName + '.log')).write_text(result.stdout + result.stderr)
        return result, data

    def wrapper(self, name, body):
        path = self.root / name
        path.write_text('#!' + sys.executable + '\nimport os, pathlib, sys, time\n' + body + '\n')
        path.chmod(0o755)
        return path

    def test_healthy_local_pipe_checksum_and_update_scenarios_pass(self):
        # The same product is both controls. Add the same 50 ms startup delay
        # to each so millisecond smoke copies test gate behavior without a
        # short process-scheduling interval deciding the self-test's verdict.
        # Production measurements use the actual binaries and fixed policy.
        healthy = self.wrapper('healthy-control-xs',
                               'if "--version" not in sys.argv: time.sleep(0.05)\n'
                               f'os.execv({str(BINARY)!r}, [{str(BINARY)!r}, *sys.argv[1:]])')
        result, data = self.gate(healthy, 'local-fresh,local-noop,local-rt,local-rlt,pipe-fresh,pipe-checksum,local-update,pipe-update,large-pipe,large-single-local,large-single-pipe,large-single-compressed,tiny-pipe', samples=24, reference=healthy)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(data['complete'])
        self.assertTrue(data['passed'])
        self.assertEqual(len(data['records']), 13 * 24 * 3)
        self.assertEqual(len(data['warmups']), 13 * 3)
        self.assertTrue(all(r['verified'] and r['warmup'] for r in data['warmups']))
        self.assertTrue(all(not r['warmup'] for r in data['records']))
        self.assertTrue(all(r['verified'] for r in data['records']))

    def test_real_slowdown_fails_after_successful_verification(self):
        slow = self.wrapper('slow-xs',
                            'if "--version" not in sys.argv: time.sleep(0.3)\n'
                            f'os.execv({str(BINARY)!r}, [{str(BINARY)!r}, *sys.argv[1:]])')
        result, data = self.gate(slow, 'local-noop,pipe-fresh')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(data['complete'])
        self.assertFalse(data['passed'])
        self.assertTrue(all(r['verified'] for r in data['records']))
        self.assertTrue(all(not r['passed'] for r in data['ratios']))
        self.assertNotIn('error', data)

    def test_corruption_is_a_failure_even_when_tool_exits_zero(self):
        corrupt = self.wrapper('corrupt-xs',
                               f'if "--version" in sys.argv: os.execv({str(BINARY)!r}, [{str(BINARY)!r}, "--version"])\n'
                               'dest = pathlib.Path(sys.argv[-1]); dest.mkdir(parents=True)\n'
                               '(dest / "wrong").write_bytes(b"corruption")')
        result, data = self.gate(corrupt, 'local-fresh', samples=1)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(data.get('complete', False))
        self.assertFalse(data['passed'])
        self.assertIn('verification failed', data['error'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--xsync', type=pathlib.Path, default=BINARY)
    parser.add_argument('--rsync', default=RSYNC)
    parser.add_argument('--output-root', type=pathlib.Path)
    args, remaining = parser.parse_known_args()
    BINARY = args.xsync.resolve()
    RSYNC = args.rsync
    OUTPUT_ROOT = args.output_root
    if not RSYNC or not BINARY.is_file():
        parser.error('xs binary and rsync are required')
    unittest.main(argv=[sys.argv[0], *remaining])
