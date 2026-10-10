#!/usr/bin/env python3
"""File-list source selection, local/remote list input, and stdin vs rsync."""
import os
import shlex
import subprocess
import unittest
import pathlib
import json

import difftest
import output_test as transfer
import filter_diff_test as filters
import relative_test
from filter_diff_test import RSYNC


class FilesFromDifferentials(filters.FilterDifferentials):
    fixture = relative_test.RelativeDifferentials.fixture

    def copy(self, native, direction, rules, delete_excluded):
        source, destination = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        command = [str(transfer.BINARY) if native else RSYNC, '-i', '--out-format=%i|%n', *self.flags]
        if native: command += ['--no-fallback', '--no-clone', '-j8']
        if delete_excluded: command += ['--delete-excluded']
        command += ['--filter=' + rule for rule in rules]
        listpath = str(self.root / 'names')
        if self.list_mode == 'stdin': listpath = '-'
        elif self.list_mode == 'remote': listpath = ':' + listpath
        elif self.list_mode == 'host': listpath = (transfer.HOST or 'fake') + ':' + listpath
        if direction != 'local':
            server = ('/usr/local/bin/xs' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.join([server, *getattr(self, 'server_flags', [])])]
            if direction == 'push': destination = (transfer.HOST or 'fake') + ':' + destination
            else: source = (transfer.HOST or 'fake') + ':' + source
        result = subprocess.run(command + ['--files-from=' + listpath, source, destination],
                                input=self.names if self.list_mode == 'stdin' else None, capture_output=True, timeout=30,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        snapshot = difftest.snapshot(str(self.root))
        if transfer.HOST and direction != 'local':
            from ssh_test import remote_json
            remote = remote_json('import sys,json; sys.path.insert(0,"/work/tests"); import difftest; print(json.dumps(difftest.snapshot(sys.argv[1])))', self.root)
            prefix = 'dst/' if direction == 'push' else 'src/'
            top = prefix.rstrip('/')
            snapshot = {key: value for key, value in snapshot.items() if key != top and not key.startswith(prefix)}
            snapshot.update({key: value for key, value in remote.items() if key == top or key.startswith(prefix)})
        immutable = lambda data: {key: value for key, value in data.items()
                                  if key == 'src' or key.startswith('src/') or key == 'outside' or key.startswith('outside/')}
        # JSON remote snapshots represent hard-link tuples as lists.
        self.assertEqual(json.dumps(immutable(snapshot), sort_keys=True),
                         json.dumps(immutable(self.fixture_snapshot), sort_keys=True))
        output = sorted(line for line in result.stdout.splitlines() if len(line) > 11 and line[11:12] == b'|')
        return result, snapshot, output

    def check_list(self, direction, label, flags, names, rules=(), mode='file', extra=None):
        self.destination_link = False
        self.flags, self.names, self.list_mode = flags, names, mode
        self.rulefiles = {'names': names, **(extra or {})}
        self.reference_codes = (0, 1, 4, 23)
        self.rejection_diagnostic = b'file-list name'
        self.check_rules(direction, label, rules)

    def run_cases(self, direction):
        cases = [
            (['-a'], b'dir1/deep/c.o\n', []),
            (['-ar'], b'dir1\n', []), (['-a'], b'dir1\n', []),
            (['-a'], b'dir1/\n', []), (['-ar'], b'dir1/\n', []),
            (['-a'], b'.\n', []), (['-a'], b'./\n', []), (['-ar'], b'.\n', []),
            (['-a', '--no-relative'], b'dir1/deep/c.o\n', []),
            (['-a', '--no-relative'], b'dir1/\n', []),
            (['-ar', '--no-relative'], b'dir1/\n', []),
            (['-ar', '--no-recursive'], b'dir1/\n', []),
            (['--no-recursive', '-a'], b'dir1/\n', []),
            (['-r', '-a'], b'dir1\n', []),
            (['-a', '--no-dirs'], b'dir1/\n', []),
            (['-a'], b'\n# comment\r\n; comment\ndir1/a.txt\rdir1/deep/c.o', []),
            (['-a'], b'/dir1/deep/c.o\n../a.txt\ndir1/../a.txt\n../../dir1/a.txt\n', []),
            (['-a'], b'dir1/./deep/c.o\n', []),
            (['-a'], b'dir1/a.txt\ndir1/a.txt\na.txt\ndir1/deep/c.o\n', []),
            (['-a', '--delete'], b'dir1/deep/c.o\n', []),
            (['-a', '--delete'], b'dir1/\n', []),
            (['-ar', '--delete-after'], b'dir1\n', []),
            (['-ar', '--delete-after'], b'.\n', ['P stale.*']),
            (['-arm'], b'empty\ndir1/empty/chain\ndir1/deep/c.o\n', []),
            (['-a'], b'alias/deep/c.o\n', []),
            (['-a'], b'alias\nalias/a.txt\n', []),
            (['-aL'], b'link\n', []), (['-a'], b'link\n', []),
            (['-a'], b'dir1/deep/c.o\n', ['- dir1/', '- deep/']),
            (['-a'], b'dir1/deep/c.o\n', ['- c.o']),
            (['-ar'], b'dir1/\n', ['- *.o']),
            (['-a'], b'missing\ndir1/a.txt\n', []),
            (['-a'], b'', []), (['-ar', '--delete'], b'', []),
            (['-a', '--from0'], b'line\nbreak\0carriage\rreturn\0dir1/a.txt\0', []),
            (['-a', '--from0'], b'# comment\0;comment\0dir1/deep/c.o', []),
            (['-a'], b'a.txt\0dir1/a.txt\ndir1/deep/c.o\n', []),
            (['-an'], b'dir1/deep/c.o\n', []),
            (['-aH'], b'dir1/a.txt\na.txt\n', []),
        ]
        for mode in (('file', 'stdin') if direction == 'local' else ('file', 'stdin', 'remote', 'host')):
            for index, (flags, names, rules) in enumerate(cases):
                self.check_list(direction, str(index) + '-' + mode, flags, names, rules, mode)
        for names in (b'dir1/deep/c.o\n', b'dir1/\n'):
            self.check_list(direction, 'merge-' + repr(names), ['-ar', '--delete-after'], names,
                            [': .rules'], extra={'src/.rules': b'- *.o\n', 'dst/.rules': b'P stale.*\n'})

    def test_local(self): self.run_cases('local')
    def test_push(self): self.run_cases('push')
    def test_pull(self): self.run_cases('pull')

    def test_streaming_boundaries(self):
        names = b'#' + b'x' * 65533 + b'\r\n' + b'dir1/deep/c.o\n' + b'a.txt\n' * 200000
        for direction in ('local', 'push', 'pull'):
            for mode in (('file', 'stdin') if direction == 'local' else ('file', 'stdin', 'remote')):
                self.check_list(direction, 'large-' + mode, ['-a'], names, mode=mode)

    def test_merges_special_names_and_hardlinks(self):
        self.fixture_hardlinks = {'src/linked': 'src/a.txt'}
        for direction in ('local', 'push', 'pull'):
            modes = ('file', 'stdin') if direction == 'local' else ('file', 'stdin', 'remote')
            for mode in modes:
                for names, flags, rules, extra in (
                    (b'a.txt\nlinked\n', ['-aH'], [], {}),
                    (b'space name\0[brackets]*?\0line\nbreak\0', ['-a0'], [],
                     {'src/space name': b'space', 'src/[brackets]*?': b'literal'}),
                    (b'dir1/deep/c.o\0', ['-ar0'], [': .rules'], {'src/dir1/.rules': b'- *.o\0'}),
                    (b'dir1/\0', ['-ar0', '--delete-after'], [': .rules'],
                     {'src/dir1/.rules': b'- *.o\0', 'dst/dir1/.rules': b'P stale.*\0'}),
                    (b'.\ndir1/deep/c.o\n', ['-a'], [': .rules'], {'src/.rules': b'- *.o\n'}),
                    (b'dir1/./deep/c.o\n', ['-a'], [': .rules'], {'src/dir1/.rules': b'- *.o\n'}),
                ):
                    self.check_list(direction, 'special-' + repr(names) + '-' + mode, flags, names, rules, mode, extra)
            if direction != 'local':
                self.server_flags = ['--from0']
                self.check_list(direction, 'helper-from0', ['-a'], b'dir1/a.txt\0dir1/deep/c.o\0', mode='remote')
                self.server_flags = []

    def test_record_limits_and_nul_suffix(self):
        for direction in ('local', 'push', 'pull'):
            modes = ('file', 'stdin') if direction == 'local' else ('file', 'stdin', 'remote')
            for mode in modes:
                for names in (b'#' + b'x' * (1024 * 1024 + 2) + b'\na.txt\n',
                              b'a.txt\0' + b'x' * (1024 * 1024 + 2) + b'\n'):
                    self.check_list(direction, 'record-limit-' + mode + '-' + repr(names[:8]), ['-a'], names, mode=mode)

    def test_listing(self):
        for remote in (False, True):
            for mode in (('file', 'stdin') if not remote else ('file', 'stdin', 'remote')):
                for names in (b'dir1/deep/c.o\n', b'dir1/\n', b'.\n', b'', b'dir1/./deep/c.o\n'):
                    for flags in (['-al'], ['-arl'], ['-arm'], ['-al', '--no-relative']):
                        with self.subTest(remote=remote, mode=mode, names=names, flags=flags):
                            self.rulefiles = {'names': names}
                            self.fixture(remote)
                            before = difftest.snapshot(str(self.root))
                            outputs = []
                            for native in (False, True):
                                command = [str(transfer.BINARY) if native else RSYNC, '--list-only', *flags]
                                if native: command += ['--no-fallback']
                                source = str(self.root / 'src') + '/'
                                listpath = str(self.root / 'names') if mode != 'stdin' else '-'
                                if remote:
                                    server = ('/usr/local/bin/xs' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                                    command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                                    source = (transfer.HOST or 'fake') + ':' + source
                                    if mode == 'remote': listpath = ':' + listpath
                                result = subprocess.run(command + ['--files-from=' + listpath, source, str(self.root / 'unused')],
                                                        input=names if mode == 'stdin' else None, capture_output=True, timeout=20,
                                                        env=dict(os.environ, TZ='UTC', LC_ALL='C'))
                                self.assertEqual(result.returncode, 0, result.stderr)
                                outputs.append(result.stdout)
                            self.assertEqual(*outputs)
                            self.assertEqual(difftest.snapshot(str(self.root)), before)

    def test_input_errors_do_not_create_destination(self):
        self.rulefiles = {'names': b'a.txt\n', 'empty-list': b''}
        for direction in ('local', 'push', 'pull'):
            self.fixture(direction != 'local')
            for name, source_name, list_name, expected in (
                ('missing-list', 'src', 'missing', 1),
                ('directory-list', 'src', 'src', 0 if direction == 'pull' else 12),
                ('missing-source', 'missing-src', 'names', 12 if direction == 'pull' else 3),
                ('file-source', 'src/a.txt', 'names', 12 if direction == 'pull' else 3),
                ('empty-list-source', 'missing-src', 'empty-list', 12 if direction == 'pull' else 3),
            ):
                with self.subTest(direction=direction, error=name):
                    for native in (False, True):
                        source, destination = str(self.root / source_name), str(self.root / ('unused-' + name + '-' + str(native)))
                        target = pathlib.Path(destination)
                        command = [str(transfer.BINARY) if native else RSYNC, '-a', '--files-from=' + str(self.root / list_name)]
                        if native: command += ['--no-fallback']
                        if direction != 'local':
                            server = ('/usr/local/bin/xs' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                            if direction == 'push': destination = (transfer.HOST or 'fake') + ':' + destination
                            else: source = (transfer.HOST or 'fake') + ':' + source
                        result = subprocess.run(command + [source, destination], capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, expected, result.stderr)
                        # An empty list is a successful empty transfer in pull.
                        if expected:
                            if transfer.HOST and direction == 'push':
                                from ssh_test import remote_json
                                exists = remote_json('import os,sys,json; print(json.dumps(os.path.exists(sys.argv[1])))', target)
                                self.assertFalse(exists)
                            else: self.assertFalse(target.exists())

    def test_file_list_syntax(self):
        self.rulefiles = {'names': b'a.txt\n'}
        self.fixture()
        source, destination = str(self.root / 'src'), str(self.root / 'unused')
        listpath = str(self.root / 'names')
        for args in (['--files-from=' + listpath, source],
                     ['--list-only', '--files-from=' + listpath, source],
                     ['--files-from=' + listpath, source, source, destination],
                     ['--files-from=:' + listpath, source, destination],
                     ['--files-from=:-', source, 'fake:' + destination],
                     ['--files-from=other:' + listpath, source, 'fake:' + destination]):
            with self.subTest(args=args):
                before = difftest.snapshot(str(self.root))
                for binary in (RSYNC, str(transfer.BINARY)):
                    command = [binary, '-a', *(['--no-fallback'] if binary == str(transfer.BINARY) else []), *args]
                    result = subprocess.run(command, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(difftest.snapshot(str(self.root)), before)


if __name__ == '__main__': unittest.main()
