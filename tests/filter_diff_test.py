#!/usr/bin/env python3
"""Reproducible native filter differential fuzzer, including push/pull deletion.

XSYNC_FILTER_SEED selects the first seed; XSYNC_FILTER_CASES sets the count
(default 48). A failure prints its seed and full rule list for reproduction.
Tree comparisons include source integrity, types, data, modes and timestamps.
Run through ssh-rig.sh to use real SSH rather than the local fake shell.
"""
import json
import os
import pathlib
import random
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

import difftest
import output_test as transfer

RSYNC = os.environ.get('XSYNC_TEST_RSYNC', shutil.which('rsync'))


class FilterDifferentials(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if transfer.HOST:
            import ssh_test
            ssh_test.SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if transfer.HOST else '/tmp', prefix='xsync filters ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        if transfer.HOST:
            from ssh_test import remote_code
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1],ignore_errors=True)', self.root)

    def fixture(self, remote=False):
        for child in self.root.iterdir():
            if child.is_dir(): shutil.rmtree(child)
            else: child.unlink()
        tree = difftest.Tree(str(self.root))
        for top in ('src', 'dst'):
            tree.d(top)
            for directory in ('dir1', 'dir1/deep', 'empty', 'keep'):
                tree.d(top + '/' + directory)
            for name in ('a.txt', 'b.o', '.hidden', 'keep/file', 'dir1/a.txt', 'dir1/b.o', 'dir1/deep/c.o'):
                tree.f(top + '/' + name, ((top if top == 'src' else 'destination-old') + ':' + name).encode())
            tree.ln(top + '/link', 'a.txt')
        for name in ('stale.o', 'stale.txt', 'gone/stale.o', 'gone/stale.txt', 'gone/deep/file', 'dir1/stale.o'):
            tree.f('dst/' + name, name.encode())
        tree.done()
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/', transfer.HOST + ':' + str(self.root) + '/'],
                           capture_output=True, check=True, timeout=20)

    def copy(self, native, direction, rules, delete_excluded):
        source, destination = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if getattr(self, 'named_source', False): source = source.rstrip('/')
        command = [str(transfer.BINARY) if native else RSYNC, '-ai', '--delete', '--out-format=%i|%n']
        command += list(getattr(self, 'flags', ()))
        if native: command += ['--no-fallback', '--no-clone', '-j8']
        if delete_excluded: command.append('--delete-excluded')
        command += ['--filter=' + rule for rule in rules]
        if direction != 'local':
            server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
            server_command = shlex.quote(server)
            if getattr(self, 'server_env', None):
                server_command = shlex.join(['env', *[key + '=' + value for key, value in self.server_env.items()], server])
            command += ['-e', transfer.RSH, '--rsync-path=' + server_command]
            if direction == 'push': destination = (transfer.HOST or 'fake') + ':' + destination
            else: source = (transfer.HOST or 'fake') + ':' + source
        result = subprocess.run(command + [source, destination], capture_output=True, timeout=20,
                                env=getattr(self, 'env', None))
        snapshot = difftest.snapshot(str(self.root))
        if transfer.HOST and direction != 'local':
            from ssh_test import remote_json
            remote = remote_json('import sys,json; sys.path.insert(0,"/work/tests"); import difftest; print(json.dumps(difftest.snapshot(sys.argv[1])))', self.root)
            # The source lives remotely for pull, the destination remotely for push.
            prefix = 'dst/' if direction == 'push' else 'src/'
            top = prefix.rstrip('/')
            snapshot = {key: value for key, value in snapshot.items() if key != top and not key.startswith(prefix)}
            snapshot.update({key: value for key, value in remote.items() if key == top or key.startswith(prefix)})
        # Include itemized entries/deletions but exclude informational notices.
        output = sorted(line for line in result.stdout.splitlines() if len(line) > 11 and line[11:12] == b'|')
        return result, snapshot, output

    def check_rules(self, direction, label, rules, delete_excluded=False):
        with self.subTest(direction=direction, seed=label, rules=rules, delete_excluded=delete_excluded):
            begin = time.time_ns() - 2_000_000_000
            self.fixture(direction != 'local')
            original = difftest.snapshot(str(self.root))
            reference, expected, ref_output = self.copy(False, direction, rules, delete_excluded)
            self.assertIn(reference.returncode, getattr(self, 'reference_codes', (0,)), reference.stderr)
            self.fixture(direction != 'local')
            result, actual, output = self.copy(True, direction, rules, delete_excluded)
            self.assertEqual(result.returncode, reference.returncode, result.stderr)
            self.assertNotIn(b'falling back', result.stderr)
            if reference.returncode == 4:
                self.assertIn(b'rejecting excluded file-list name', reference.stderr)
                self.assertIn(b'rejecting excluded file-list name', result.stderr)
                self.assertFalse(any(line.startswith(b'*deleting') for line in output))
                source = lambda tree: {k: v for k, v in tree.items() if k == 'src' or k.startswith('src/')}
                self.assertEqual(source(expected), source(original))
                self.assertEqual(source(actual), source(original))
                return
            differences = difftest.compare(expected, actual, window=(begin, time.time_ns() + 2_000_000_000))
            self.assertFalse(differences, '\n'.join(differences))
            self.assertEqual(output, ref_output)

    def run_cases(self, direction):
        directed = [
            ['P stale.*', 'P /gone/'], ['H *.o'], ['H *.o', 'P stale.*'],
            ['S /dir1/', 'H */'], ['R stale.o', 'P *.o'], ['P *.o', 'R stale.o'],
            ['-s *.o'], ['-r *.o'], ['-p *.o'], ['-p /gone/'], ['-!p *.txt'],
            ['+s */', '-s *'], ['-x *'], ['-/ ' + str(self.root / 'src/a.txt')],
            ['-/ ' + str(self.root / 'dst/stale.o')],
        ]
        for index, rules in enumerate(directed):
            for deleted in (False, True): self.check_rules(direction, 'directed-' + str(index), rules, deleted)
        patterns = ['*.o', '*.txt', 'stale.*', '/a.txt', '/gone/', 'gone/***', '*/', 'dir1/***',
                    'dir1/*.o', '**/deep/***', 'keep', 'link', '.hidden', 'nonexistent']
        prefixes = ['-', '+', 'H', 'S', 'P', 'R', '-s', '+s', '-r', '+r', '-sr', '+sr', '-p', '+p', '-!', '+!', '-!p', '-x']
        first = int(os.environ.get('XSYNC_FILTER_SEED', '80800'))
        for seed in range(first, first + int(os.environ.get('XSYNC_FILTER_CASES', '48'))):
            rng = random.Random(seed)
            rules = [rng.choice(prefixes) + ' ' + rng.choice(patterns) for _ in range(rng.randint(1, 8))]
            self.check_rules(direction, seed, rules, rng.choice((False, True)))

    def test_local(self): self.run_cases('local')
    def test_push(self): self.run_cases('push')
    def test_pull(self): self.run_cases('pull')

    def test_invalid_side_modifiers(self):
        for prefix in ('H', 'S', 'P', 'R'):
            for modifier in ('s', 'r', 'C'):
                rule = prefix + modifier + ' *.o'
                with self.subTest(rule=rule):
                    self.fixture()
                    before = difftest.snapshot(str(self.root))
                    for binary in (RSYNC, str(transfer.BINARY)):
                        command = [binary, '-a', '--filter=' + rule, str(self.root / 'src') + '/', str(self.root / 'dst') + '/']
                        if binary == str(transfer.BINARY): command.insert(1, '--no-fallback')
                        result = subprocess.run(command, capture_output=True, timeout=10)
                        self.assertEqual(result.returncode, 1, result.stderr)
                        self.assertEqual(difftest.snapshot(str(self.root)), before)


if __name__ == '__main__': unittest.main()
