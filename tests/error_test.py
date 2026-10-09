#!/usr/bin/env python3
"""Bounded end-of-run diagnostics without changing transfer stdout or exit codes."""
import os
import pathlib
import re
import select
import shlex
import signal
import subprocess
import sys
import tempfile
import unittest

from output_test import BINARY, HOST, RSH
from ssh_test import remote_code
import list_wire_test
from wire_test import frame, var

REPO = pathlib.Path(__file__).resolve().parent.parent
ENV = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='0')


class ErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-error-fault-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = pathlib.Path(cls.library_tmp.name)/'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                '-fPIC', str(REPO/'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform == 'darwin': args += ['-arch', 'arm64', '-arch', 'x86_64']
        else: args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync errors ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.good = self.root/'good'
        self.good.write_text('healthy sibling')
        if HOST:
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True); '
                        '(p/"good").write_text("healthy sibling")', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def summary(self, result, count, shown=None, code=23):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stderr.count(b'xsync: error summary:'), 1, result.stderr)
        summary = result.stderr.split(b'xsync: error summary: ')[1]
        header = f'{count} error' + ('s' if count != 1 else '')
        header += f' (showing first {min(count, 10) if shown is None else shown})\n'
        self.assertTrue(summary.startswith(header.encode()), summary)
        self.assertIn(f'(code {code})'.encode(), summary.splitlines()[-1])
        samples = [line for line in summary.splitlines() if line.startswith(b'    ')]
        self.assertEqual(len(samples), min(count, 10) if shown is None else shown, summary)
        if count > 10: self.assertIn(f'{count-10} more errors not shown'.encode(), summary)
        return summary

    def copy(self, direction, count, *flags):
        sources = [str(self.good)] + [str(self.root/f'missing-{i:02}') for i in range(count)]
        destination = str(self.root/('target-' + direction)) + '/'
        command = [str(BINARY), '--no-fallback', '-a', '--no-clone', '-j8', *flags]
        if direction != 'local':
            command += ['-e', RSH, '--rsync-path=' + shlex.quote('/usr/local/bin/xsync' if HOST else str(BINARY))]
            if direction == 'push': destination = (HOST or 'fake') + ':' + destination
            else: sources = [(HOST or 'fake') + ':' + s for s in sources]
        return subprocess.run(command + sources + [destination], capture_output=True, timeout=30, env=ENV)

    def test_local_push_pull_exact_counts_first_ten_and_logs(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                log = self.root/(direction + '.log')
                result = self.copy(direction, 17, '--stats', '--out-format=%i|%n', '--log-file=' + str(log))
                summary = self.summary(result, 17)
                self.assertIn(b'partial transfer (code 23): 17 errors', summary)
                for i in range(17):
                    self.assertEqual(summary.count(f'missing-{i:02}'.encode()), int(i < 10), summary)
                self.assertEqual(log.read_bytes(), result.stdout)
                self.assertNotIn(b'error summary', result.stdout)
                self.assertIn(b'good', result.stdout)
                if direction == 'push' and HOST:
                    remote_code('import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_text()=="healthy sibling"',
                                self.root/'target-push/good')
                else:
                    self.assertEqual((self.root/('target-' + direction)/'good').read_text(), 'healthy sibling')

    def test_quiet_retains_summary(self):
        result = self.copy('local', 3, '-q', '--stats')
        self.summary(result, 3)
        self.assertEqual(result.stdout, b'')

    def test_remote_receiver_errors_count_once(self):
        source = self.root/'receiver-source'; source.mkdir()
        target = self.root/'receiver-target'; target.mkdir()
        for i in range(17):
            (source/f'blocked-{i:02}').write_text('new file')
            (target/f'blocked-{i:02}').mkdir()
            (target/f'blocked-{i:02}'/'keep').write_text('protected')
        if HOST:
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); '
                        '[(p/f"blocked-{i:02}").mkdir() for i in range(17)]; '
                        '[(p/f"blocked-{i:02}"/"keep").write_text("protected") for i in range(17)]', target)
        result = subprocess.run([str(BINARY), '--no-fallback', '-a', '--no-clone', '-j8',
                                 '-e', RSH, '--rsync-path=' + shlex.quote('/usr/local/bin/xsync' if HOST else str(BINARY)),
                                 str(source)+'/', (HOST or 'fake') + ':' + str(target)+'/'],
                                capture_output=True, timeout=30, env=ENV)
        summary = self.summary(result, 17)
        self.assertEqual(summary.count(b'could not make way'), 10, summary)
        if HOST:
            remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); '
                        'assert all((p/f"blocked-{i:02}"/"keep").read_text()=="protected" for i in range(17))', target)
        else:
            self.assertTrue(all((target/f'blocked-{i:02}'/'keep').read_text() == 'protected' for i in range(17)))

    def test_success_has_no_error_summary(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                result = self.copy(direction, 0)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(b'error summary', result.stderr)

    def test_concurrent_source_failures(self):
        source = self.root/'damaged'; source.mkdir()
        for i in range(64): (source/f'file-{i:02}').write_bytes(b'x'*4096)
        env = dict(ENV, XSYNC_FAULT_PATH=str(source.resolve()), XSYNC_FAULT_READ_ERROR='1')
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.fault)
        result = subprocess.run([str(BINARY), '--no-fallback', '-a', '--no-clone', '-W', '-j8',
                                 str(source)+'/', str(self.root/'target')+'/'], env=env,
                                capture_output=True, timeout=30)
        summary = self.summary(result, 64)
        samples = re.findall(rb'file-\d\d', summary)
        self.assertEqual(len(set(samples)), 10, summary)
        self.assertIn(b'Input/output error', summary)
        self.assertFalse(list((self.root/'target').glob('file-*')))

    def peer(self, messages, final=23):
        frames = b''.join(frame(8, bytes([kind]) + var(code) + text) for kind, code, text in messages)
        if not any(kind == 2 for kind, _, _ in messages): frames += frame(5, var(final) + b'\0')
        return list_wire_test.ListWireTests.peer(self, frames)

    def run_peer(self, messages, final=23):
        return subprocess.run([str(BINARY), '--no-fallback', '-e', self.peer(messages, final),
                               '--rsync-path=unused', 'fake:source/'], capture_output=True, timeout=10, env=ENV)

    def test_grouped_first_ten_and_escaped_samples(self):
        codes = [23, 24, 23, 11, 24, 23, 11, 24, 23, 11, 2, 23, 24, 11]
        messages = [(1, code, f'example-{i:02}\n\x1b[31m'.encode()) for i, code in enumerate(codes)]
        result = self.run_peer([(1, 0, b'warning only')] + messages, final=11)
        summary = self.summary(result, 14, code=11)
        for code in set(codes):
            self.assertIn(f'(code {code}): {codes.count(code)} error'.encode(), summary)
        for i in range(14): self.assertEqual(summary.count(f'example-{i:02}'.encode()), int(i < 10), summary)
        self.assertEqual(summary.count(b'\\#012\\#033[31m'), 10, summary)
        self.assertNotIn(b'warning only', summary)
        self.assertNotIn(b'\x1b', summary)

    def test_fatal_includes_prior_errors_and_original_exit_line(self):
        result = self.run_peer([(1, 23, b'earlier failure'), (2, 12, b'fatal stream failure')])
        summary = self.summary(result, 2, code=12)
        self.assertIn(b'partial transfer (code 23): 1 error', summary)
        self.assertIn(b'stream IO (code 12): 1 error', summary)
        self.assertTrue(summary.endswith(b'xsync error: exiting (code 12)\n'), summary)

    def test_interruption_retains_prior_diagnostics(self):
        # No completion: wait after one diagnostic, then interrupt the client.
        frames = frame(8, b'\1' + var(23) + b'failure before interruption')
        peer = list_wire_test.ListWireTests.peer(self, frames)
        proc = subprocess.Popen([str(BINARY), '--no-fallback', '-e', peer, '--rsync-path=unused',
                                 'fake:source/'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        try:
            self.assertTrue(select.select([proc.stderr], [], [], 10)[0], 'diagnostic did not arrive')
            prefix = os.read(proc.stderr.fileno(), 4096)
            self.assertIn(b'failure before interruption', prefix)
            proc.send_signal(signal.SIGINT)
            stdout, stderr = proc.communicate(timeout=10)
            result = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, prefix + stderr)
            summary = self.summary(result, 1, code=20)
            self.assertIn(b'partial transfer (code 23): 1 error', summary)
        finally:
            if proc.poll() is None: proc.kill()
            proc.communicate(timeout=5)

    def test_completion_without_details_is_not_lost(self):
        result = self.run_peer([])
        summary = self.summary(result, 1)
        self.assertIn(b'errors were reported while listing remote sources', summary)

    def test_thousands_of_errors_retain_only_ten_samples(self):
        result = self.run_peer([(1, 23, f'failure-{i:04}'.encode()) for i in range(6000)])
        summary = self.summary(result, 6000)
        self.assertLess(len(summary), 1000, summary)
        for i in range(10): self.assertIn(f'failure-{i:04}'.encode(), summary)
        self.assertNotIn(b'failure-0010', summary)

    def test_vanished_warning_exit_and_zero_code_notice(self):
        result = self.run_peer([(1, 24, b'source vanished')], final=24)
        summary = self.summary(result, 1, code=24)
        self.assertIn(b'vanished source files (code 24): 1 error', summary)
        self.assertTrue(summary.splitlines()[-1].startswith(b'xsync warning:'), summary)
        result = self.run_peer([(1, 0, b'warning only')], final=0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'warning only', result.stderr)
        self.assertNotIn(b'error summary', result.stderr)


if __name__ == '__main__': unittest.main()
