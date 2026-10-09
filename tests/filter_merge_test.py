#!/usr/bin/env python3
"""Merge-file differential cases and seeded inheritance checks against rsync."""
import os
import random
import shlex
import subprocess
import unittest

import difftest
import output_test as transfer
import filter_diff_test as global_filters
from filter_diff_test import RSYNC


class MergeDifferentials(global_filters.FilterDifferentials):
    def fixture(self, remote=False):
        super().fixture(False)
        tree = difftest.Tree(str(self.root))
        tree.dirs = {name: [entry['mode'], entry['mtime']] for name, entry in difftest.snapshot(str(self.root)).items()
                     if entry['type'] == 'dir'}
        for name, contents in self.rulefiles.items(): tree.f(name, contents.encode())
        tree.done()
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/', transfer.HOST + ':' + str(self.root) + '/'],
                           capture_output=True, check=True, timeout=20)

    def test_invalid_side_modifiers(self):
        self.rulefiles = {}
        super().test_invalid_side_modifiers()

    def run_merges(self, direction):
        cases = [
            ([': .rules'], {'src/.rules': '- *.o\n', 'src/dir1/.rules': '+ *.o\n'}),
            ([': .rules'], {'src/.rules': '- *.o\n', 'src/dir1/.rules': '!\n- *.txt\n'}),
            ([': .rules'], {'src/.rules': '- /a.txt\n', 'src/dir1/.rules': '- /b.o\n'}),
            (['+ *.o', ': .rules'], {'src/.rules': '- *.o\n'}),
            ([': .rules', '+ *.o'], {'src/.rules': '- *.o\n'}),
            ([':n .rules'], {'src/.rules': '- *.o\n'}),
            ([':e .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': 'P stale.*\n'}),
            ([':s .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '- stale.*\n'}),
            ([':r .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '- stale.*\n'}),
            ([':p .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '- *.o\n'}),
            ([':- .rules'], {'src/.rules': '*.o\n# comment\n', 'src/dir1/.rules': '*.txt\n'}),
            ([':+ .rules', '- *.o'], {'src/.rules': '*.o\n'}),
            ([':w .rules'], {'src/.rules': '-_*.o +_*.txt\n'}),
            ([':C'], {'src/.cvsignore': '*.o *.txt\n', 'src/dir1/.cvsignore': '*.txt\n'}),
            ([': .rules'], {'dst/.rules': 'P stale.*\n', 'dst/gone/.rules': 'P stale.o\n'}),
            ([': .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': 'P *.txt\n'}),
            ([': .one', ': .two'], {'src/.one': '- *.o\n', 'src/.two': '+ *.o\n', 'src/dir1/.one': '!\n'}),
            (['. {root}/global.rules'], {'global.rules': '# comment\n- *.o\n+ *.txt\n'}),
            (['.- {root}/global.rules'], {'global.rules': '*.o\n# comment\n'}),
            (['.+ {root}/global.rules', '- *.o'], {'global.rules': '*.o\n'}),
            (['.w {root}/global.rules'], {'global.rules': '-_*.o +_*.txt\n'}),
            (['.C {root}/global.rules'], {'global.rules': '*.o *.txt\n'}),
            (['.s {root}/global.rules'], {'global.rules': '- *.o\n'}),
            (['. {root}/global.rules'], {'global.rules': ': .rules\n', 'src/.rules': '- *.o\n'}),
            ([': /.rules'], {'.rules': '- *.o\n', 'src/dir1/.rules': '+ *.o\n'}),
            ([': ../.rules'], {'.rules': '- *.o\n', 'src/.rules': '!\n- /a.txt\n'}),
            ([': .rules'], {'src/.rules': ': .next\n', 'src/.next': '- *.o\n', 'src/dir1/.next': '+ *.o\n'}),
            (['. {root}/global.rules'], {'global.rules': '. {root}/other.rules\n- *.txt\n', 'other.rules': '- *.o\n'}),
            (['. {root}/global.rules'], {'global.rules': '- *.o\n!\n- *.txt\n'}),
            ([': .rules'], {'src/.rules': ': .rules\n- *.o\n'}),
            ([':s .rules', ':r .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '- stale.*\n'}),
            ([': .one', 'P stale.*', ': .two'], {'src/.one': ': .two\n', 'dst/.one': ': .two\n', 'dst/.two': 'R stale.*\n'}),
            ([': {root}/src/../.rules'], {'.rules': '- *.o\n', 'src/.rules': '- /a.txt\n'}),
            ([': {root}/./.rules'], {'.rules': '- *.o\n', 'src/.rules': '- /a.txt\n'}),
        ]
        for index, (rules, files) in enumerate(cases):
            self.flags = []
            self.rulefiles = {name: contents.replace('{root}', str(self.root)) for name, contents in files.items()}
            for deleted in (False, True):
                self.check_rules(direction, 'merge-' + str(index), [rule.format(root=self.root) for rule in rules], deleted)
        for flags in (['-F'], ['-FF'], ['-FFF']):
            self.flags = flags
            self.rulefiles = {'.rsync-filter': '- *.o\n', 'src/dir1/.rsync-filter': '+ *.o\n'}
            self.check_rules(direction, flags, [])
        self.flags = []
        self.named_source = True
        for rules in ([': .rules'], [': /.rules'], [': ../.rules']):
            self.rulefiles = {'.rules': '- *.o\n', 'src/.rules': '- /a.txt\n', 'src/dir1/.rules': '+ *.o\n'}
            self.check_rules(direction, 'named-' + rules[0], rules)
        self.named_source = False
        first = int(os.environ.get('XSYNC_MERGE_SEED', '808100'))
        for seed in range(first, first + int(os.environ.get('XSYNC_MERGE_CASES', '24'))):
            rng = random.Random(seed)
            self.rulefiles = {}
            for directory in ('src', 'src/dir1', 'src/dir1/deep', 'dst', 'dst/dir1', 'dst/gone'):
                rules = []
                for _ in range(rng.randrange(5)):
                    rules.append('!' if rng.randrange(7) == 0 else rng.choice(['-', '+', 'P', 'R', '-p']) + ' ' +
                                 rng.choice(['*.o', '*.txt', 'stale.*', '/a.txt', '/b.o', 'deep/', 'link', '.hidden']))
                self.rulefiles[directory + '/.rules'] = '\n'.join(rules) + '\n'
            self.check_rules(direction, seed, [rng.choice([':', ':e', ':n', ':p']) + ' .rules'], rng.choice((False, True)))

    def test_local(self): self.run_merges('local')
    def test_push(self): self.run_merges('push')
    def test_pull(self): self.run_merges('pull')

    def test_documented_CVS_clear(self):
        # Released rsync 3.2.7/3.4.4 reject ! in :C/.C word files. Test the
        # documented list-clear semantics directly (also fixed in upstream).
        self.flags = []
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                self.rulefiles = {'src/.cvsignore': '*.o *.txt\n! *.o\n'}
                self.fixture(direction != 'local')
                before = difftest.snapshot(str(self.root))
                result, actual, output = self.copy(True, direction, [':C'], False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(actual['dst/a.txt']['hash'], before['src/a.txt']['hash'])
                self.assertNotIn('dst/b.o', actual)
                self.assertEqual(actual['dst/dir1/b.o']['hash'], before['src/dir1/b.o']['hash'])
                self.assertEqual({k:v for k,v in actual.items() if k.startswith('src/')},
                                 {k:v for k,v in before.items() if k.startswith('src/')})

    def test_listing_contexts_and_multiple_roots(self):
        self.rulefiles = {'src/.rules': '- *.o\n', 'src/dir1/.rules': '+ *.o\n- /a.txt\n',
                          'src/dir1/deep/.rules': '!\n- *.txt\n'}
        for remote in (False, True):
            self.fixture(remote)
            before = difftest.snapshot(str(self.root))
            for sources in ((str(self.root / 'src') + '/',), (str(self.root / 'src'),),
                            (str(self.root / 'src/dir1'),),
                            (str(self.root / 'src'), str(self.root / 'src/dir1'))):
                for rule in (': .rules', ': src/.rules', ': ./src/.rules'):
                    with self.subTest(remote=remote, sources=sources, rule=rule):
                        outputs = []
                        for native in (False, True):
                            command = [str(transfer.BINARY) if native else RSYNC, '-rl', '--filter=' + rule]
                            if native: command += ['--no-fallback']
                            if remote:
                                server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                                command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                            args = [(transfer.HOST or 'fake') + ':' + path if remote else path for path in sources]
                            if len(sources) > 1:
                                command += ['--list-only']
                                args += [str(self.root / 'unused listing destination')]
                            result = subprocess.run(command + args, capture_output=True, timeout=20,
                                                    cwd=self.root,
                                                    env=dict(os.environ, TZ='UTC', LC_ALL='C'))
                            self.assertEqual(result.returncode, 0, result.stderr)
                            outputs.append(result.stdout)
                        self.assertEqual(*outputs)
                        self.assertEqual(difftest.snapshot(str(self.root)), before)

    def test_merge_file_errors(self):
        self.rulefiles = {'bad.rules': ':s .rules\n', 'src/.rules': 'P *.o\n',
                          'loop.rules': '. {root}/loop.rules\n'}
        self.rulefiles = {name: contents.replace('{root}', str(self.root)) for name, contents in self.rulefiles.items()}
        self.fixture()
        for rule, code in (('. ' + str(self.root / 'missing'), 11), (':s .rules', 1),
                           ('. ' + str(self.root / 'loop.rules'), 11)):
            with self.subTest(rule=rule):
                before = difftest.snapshot(str(self.root))
                result = subprocess.run([str(transfer.BINARY), '--no-fallback', '-r', '--filter=' + rule,
                                         str(self.root / 'src') + '/', str(self.root / 'dst') + '/'],
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(difftest.snapshot(str(self.root)), before)


if __name__ == '__main__': unittest.main()
