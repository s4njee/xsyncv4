#!/usr/bin/env python3
"""Relative source paths, implied directories and deletion ownership vs rsync."""
import os
import shlex
import subprocess
import unittest

import difftest
import output_test as transfer
import filter_diff_test as filters
from filter_diff_test import RSYNC


class RelativeDifferentials(filters.FilterDifferentials):
    def fixture(self, remote=False):
        super().fixture(False)
        tree = difftest.Tree(str(self.root))
        tree.dirs = {name: [entry['mode'], entry['mtime']]
                     for name, entry in difftest.snapshot(str(self.root)).items() if entry['type'] == 'dir'}
        tree.d('src/dir1/empty/chain', 0o750)
        tree.ln('src/alias', 'dir1')
        tree.f('src/line\nbreak', b'newline file')
        tree.f('src/carriage\rreturn', b'carriage file')
        tree.f('dst/src/unlisted', b'keep parent sibling')
        tree.f('dst/src/dir1/unlisted', b'keep implied sibling')
        tree.f('dst/src/dir1/deep/unlisted', b'keep another sibling')
        tree.f('outside/sentinel', b'never change through destination symlinks')
        for name, contents in getattr(self, 'rulefiles', {}).items(): tree.f(name, contents)
        if getattr(self, 'destination_link', False):
            import shutil
            shutil.rmtree(self.root / 'dst/src')
            tree.dirs = {name: attrs for name, attrs in tree.dirs.items() if name != 'dst/src' and not name.startswith('dst/src/')}
            tree.ln('dst/src', '../outside')
        tree.done()
        self.fixture_snapshot = difftest.snapshot(str(self.root))
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/', transfer.HOST + ':' + str(self.root) + '/'],
                           capture_output=True, check=True, timeout=20)

    def copy(self, native, direction, rules, delete_excluded):
        sources = [source.format(root=self.root) for source in self.sources]
        destination = str(self.root / 'dst') + '/'
        command = [str(transfer.BINARY) if native else RSYNC, '-i', '--out-format=%i|%n', *self.flags]
        if native:
            command += ['--no-fallback', '-j8']
            if not getattr(self, 'clone', False): command += ['--no-clone']
        if delete_excluded: command += ['--delete-excluded']
        command += ['--filter=' + rule for rule in rules]
        if direction != 'local':
            server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
            if direction == 'push': destination = (transfer.HOST or 'fake') + ':' + destination
            else: sources = [(transfer.HOST or 'fake') + ':' + source for source in sources]
        result = subprocess.run(command + sources + [destination], capture_output=True, timeout=20,
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
        self.assertEqual(immutable(snapshot), immutable(self.fixture_snapshot))
        output = sorted(line for line in result.stdout.splitlines() if len(line) > 11 and line[11:12] == b'|')
        return result, snapshot, output

    def run_cases(self, direction):
        leaf = '{root}/./src/dir1/deep/c.o'
        cut = '{root}/src/./dir1/deep/c.o'
        cases = [
            (['-R'], [leaf], []), (['-lptR'], [leaf], []), (['-aR'], [leaf], []),
            (['--relative', '-a'], [leaf], []),
            (['-aR', '--delete'], [leaf], []), (['-aR', '--delete-after'], [leaf], []),
            (['-aRm', '--delete'], [leaf], []), (['-aR', '-n'], [leaf], []),
            (['-aR'], [cut], []), (['-aR', '--delete'], [cut], []),
            (['-aR'], ['{root}/./src/dir1'], []),
            (['-aR', '--delete'], ['{root}/./src/dir1'], []),
            (['-aR', '--delete-after'], ['{root}/./src/dir1/'], []),
            (['-aRm', '--delete-after'], ['{root}/./src/dir1/'], []),
            (['-dR'], ['{root}/./src/dir1'], []), (['-dR'], ['{root}/./src/dir1/'], []),
            (['-dR', '--delete'], ['{root}/./src/dir1/'], []),
            (['-R'], ['{root}/./src/dir1/'], []),
            (['-aR'], ['{root}/./src/empty'], []), (['-aRm'], ['{root}/./src/empty'], []),
            (['-aR'], ['{root}/./src/alias/deep/c.o'], []),
            (['-aR'], ['{root}/./src/alias/'], []),
            (['-aR'], ['{root}/./src/link'], []),
            (['-aRL'], ['{root}/./src/link'], []),
            (['-aRs'], ['{root}/./src/line\nbreak', '{root}/./src/carriage\rreturn'], []),
            (['-aR'], [leaf, leaf], []),
            (['-aR'], [leaf, '{root}/./src/dir1/a.txt', '{root}/./src/a.txt'], []),
            (['-aR'], ['{root}/./src/dir1', leaf], []),
            (['-aR'], ['{root}/./src/dir1/', '{root}/src/./dir1/'], []),
            (['-aR'], [leaf], ['- src/', '- dir1/', '- deep/']),
            (['-aR'], [leaf], ['- c.o']),
            (['-aR'], ['{root}/./src/dir1/'], ['- *.o']),
            (['-aR', '--delete'], [leaf], ['P unlisted']),
            (['-aR', '--delete'], ['{root}/./src/dir1/'], ['P unlisted']),
            (['-aR', '--existing'], [leaf], []),
            (['-aR', '--ignore-existing'], [leaf], []),
            (['-aR', '--min-size=1m'], [leaf], []),
            (['-aR', '--checksum'], [leaf], []),
            (['-aRH'], ['{root}/./src/dir1/'], []),
            (['-aR', '--safe-links'], ['{root}/./src/link'], []),
            (['-aR'], ['{root}/./src/missing'], []),
            (['-aR', '--no-relative'], [leaf], []),
        ]
        self.reference_codes = (0, 1, 4, 23)
        self.destination_link = False
        self.rulefiles = {}
        for index, (flags, sources, rules) in enumerate(cases):
            self.flags, self.sources = flags, sources
            self.check_rules(direction, index, rules)
        self.reference_codes = (0,)
        self.sources = [leaf]
        for flags in (['-aR'], ['-aRm'], ['-aR', '--delete'], ['-aR', '--delete-after']):
            self.destination_link = True
            self.flags = flags
            self.check_rules(direction, 'destination-symlink-' + repr(flags), [])
        self.destination_link = False
        self.flags = ['-aR', '--delete']
        for rule, files in (
            (': .rules', {'src/.rules': b'- *.o\n'}),
            (': .rules', {'src/dir1/.rules': b'- *.o\n'}),
            (': .rules', {'src/.rules': b'- *.o\n', 'src/dir1/.rules': b'+ *.o\n'}),
            (':n .rules', {'src/.rules': b'- *.o\n'}),
            (': .rules', {'dst/src/.rules': b'P unlisted\n'}),
        ):
            self.rulefiles = files
            self.check_rules(direction, 'implied-merge-' + repr(files), [rule])

    def test_local(self): self.run_cases('local')
    def test_push(self): self.run_cases('push')
    def test_pull(self): self.run_cases('pull')

    def test_invalid_side_modifiers(self):
        self.rulefiles = {}
        super().test_invalid_side_modifiers()

    def test_clone_and_source_alias(self):
        self.clone = True
        self.flags = ['-aR']
        self.rulefiles = {}
        for source in ('{root}/./src/dir1/a.txt', '{root}/./src/alias/deep/c.o', '{root}/./src/dir1/'):
            self.sources = [source]
            self.check_rules('local', 'clone-' + source, [])

    def test_listing(self):
        self.rulefiles = {'src/.rules': b'- *.o\n', 'src/dir1/.rules': b'+ *.o\n'}
        for remote in (False, True):
            self.fixture(remote)
            before = difftest.snapshot(str(self.root))
            for sources in (['{root}/./src/dir1/a.txt'], ['{root}/./src/dir1'],
                            ['{root}/src/./dir1/'], ['{root}/./src/alias/deep/c.o'],
                            ['{root}/./src/empty'], ['{root}/./src/dir1', '{root}/./src/a.txt']):
                for flags in (['-Rl'], ['-Rrl'], ['-Rrlm'], ['-Rrl', '--filter=: .rules']):
                    with self.subTest(remote=remote, sources=sources, flags=flags):
                        outputs = []
                        for native in (False, True):
                            command = [str(transfer.BINARY) if native else RSYNC, '--list-only', *flags]
                            if native: command += ['--no-fallback']
                            args = [source.format(root=self.root) for source in sources]
                            if remote:
                                server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                                command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                                args = [(transfer.HOST or 'fake') + ':' + source for source in args]
                            result = subprocess.run(command + args + [str(self.root / 'unused')], capture_output=True, timeout=20,
                                                    env=dict(os.environ, TZ='UTC', LC_ALL='C'))
                            self.assertEqual(result.returncode, 0, result.stderr)
                            outputs.append(result.stdout)
                        self.assertEqual(*outputs)
                        self.assertEqual(difftest.snapshot(str(self.root)), before)

    def test_dotdot_is_rejected_before_destination_creation(self):
        self.rulefiles = {}
        for direction in ('local', 'push', 'pull'):
            self.fixture(direction != 'local')
            before = difftest.snapshot(str(self.root))
            self.flags = ['-aR']
            self.sources = ['{root}/./src/dir1/a.txt', '{root}/./src/dir1/../a.txt']
            result, actual, output = self.copy(True, direction, [], False)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(b'found ".." dir in relative path', result.stderr)
            self.assertEqual(actual, before)
            self.assertFalse(output)

    def test_implied_directory_overrides_explicit_symlink(self):
        self.rulefiles = {}
        self.flags = ['-lptR']
        link, leaf = '{root}/./src/alias', '{root}/./src/alias/a.txt'
        for direction in ('local', 'push', 'pull'):
            for sources in ([link, leaf], [leaf, link]):
                self.sources = sources
                self.check_rules(direction, 'directory-priority-' + repr(sources), [])

    def test_absolute_paths_and_cut_prefix(self):
        self.rulefiles = {}
        for direction in ('local', 'push', 'pull'):
            for source in ('{root}/src/dir1/deep/c.o', '{root}/src/./dir1/deep/c.o',
                           '{root}/src/../src/./dir1/deep/c.o'):
                self.sources = [source]
                self.flags = ['-aR', '--out-format=%i|%n|%f|%o']
                self.check_rules(direction, 'absolute-' + source, [])


if __name__ == '__main__': unittest.main()
