#!/usr/bin/env python3
"""CVS filter ordering, deletion and distinct client/server settings against rsync."""
import os
import random
import subprocess
import unittest

import difftest
import output_test as transfer
import filter_diff_test as filters


class CvsDifferentials(filters.FilterDifferentials):
    reference_codes = (0, 4)
    def setUp(self):
        super().setUp()
        self.client_home = 'home.keep *.custom'
        self.client_ignore = 'env.keep'
        self.peer_home = 'peer.keep *.peer'
        self.peer_ignore = 'peer-env.keep'
        self.rules_file = '-C\n'
        self.env = dict(os.environ, HOME=str(self.root / 'client home'), CVSIGNORE=self.client_ignore,
                        XSYNC_CONFIG='', XSYNC_OPTS='')
        self.server_env = {'HOME': str(self.root / 'server home'), 'CVSIGNORE': self.peer_ignore,
                           'XSYNC_CONFIG': '', 'XSYNC_OPTS': ''}

    def fixture(self, remote=False):
        super().fixture(False)
        tree = difftest.Tree(str(self.root))
        tree.dirs = {name: [entry['mode'], entry['mtime']] for name, entry in difftest.snapshot(str(self.root)).items()
                     if entry['type'] == 'dir'}
        for top in ('src', 'dst'):
            for name in ('home.keep', 'env.keep', 'peer.keep', 'peer-env.keep', 'a.custom', 'a.peer', 'a.old', '.git',
                         '.svn/file', 'RCS/file', 'dir1/home.keep', 'dir1/a.custom', 'dir1/a.peer'):
                tree.f(top + '/' + name, (top + ':different:' + name + ('-old' if top == 'dst' else '')).encode())
        for name in ('gone/obsolete.o', 'gone/home.keep', 'gone/a.custom', 'gone/env.keep', 'gone/peer.keep', 'gone/peer-env.keep'):
            tree.f('dst/' + name, name.encode())
        tree.f('src/.cvsignore', b'*.txt\n')
        tree.f('src/dir1/.cvsignore', b'*.o\n')
        tree.f('dst/.cvsignore', b'*.custom\n')
        tree.f('global.rules', self.rules_file.encode())
        tree.f('src/.rules', self.rules_file.encode())
        tree.f('dst/.rules', self.rules_file.encode())
        tree.f('client home/.cvsignore', self.client_home.encode())
        tree.f('server home/.cvsignore', self.peer_home.encode())
        tree.done()
        self.env['CVSIGNORE'] = self.client_ignore
        self.server_env['CVSIGNORE'] = self.peer_ignore
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([filters.RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/',
                            transfer.HOST + ':' + str(self.root) + '/'], capture_output=True, check=True, timeout=20)

    def run_cases(self, direction):
        cases = [
            (['-C'], []), (['--cvs-exclude'], []), (['-C', '--include=*.o'], []),
            (['--include=*.o', '-C'], []), (['-CC'], []), (['--cvs-exclude', '-C'], []),
            ([], ['-C']), ([], ['+ *.o', '-C']), ([], ['-C', '+ *.o']),
            ([], ['+C', '- *']), ([], ['+C', '-C', '- *']), ([], ['-Cr', '-Cs']),
            ([], ['-Cs', '-Cr']), ([], ['-Cp']), ([], ['-Cx']), ([], ['-C!']),
            ([], ['-C', '!', '+C', '- *']), ([], ['-C ignored']),
            (['-C'], ['-Cs']), (['-C'], ['+C']),
            ([], ['.s {root}/global.rules']), ([], [': .rules']),
            ([], ['-Cr']), ([], ['exclude,C']), ([], ['-C/']),
            ([], [': .missing', '!', '-C']), ([], ['-Csr']),
            ([], [':s .rules']), ([], [':r .rules']), ([], [':p .rules']),
            ([], ['.r {root}/global.rules']), ([], ['.p {root}/global.rules']),
            ([], ['.x {root}/global.rules']), ([], [':x .rules']), ([], [':n .rules']),
        ]
        for index, (flags, rules) in enumerate(cases):
            self.flags = flags
            for deleted in (False, True):
                self.check_rules(direction, 'cvs-' + str(index), [rule.format(root=self.root) for rule in rules], deleted)
        first = int(os.environ.get('XSYNC_CVS_SEED', '808200'))
        for seed in range(first, first + int(os.environ.get('XSYNC_CVS_CASES', '24'))):
            rng = random.Random(seed)
            self.client_home = ' '.join(rng.sample(['home.keep', '*.custom', '*.txt', '/a.txt', '*.o'], rng.randrange(1, 5)))
            self.client_ignore = ' '.join(rng.sample(['env.keep', '*.peer', 'dir1/*.o', 'stale.*'], rng.randrange(1, 4)))
            self.peer_home = ' '.join(rng.sample(['peer.keep', '*.peer', '*.txt', 'dir1/*.custom'], rng.randrange(1, 4)))
            self.peer_ignore = rng.choice(['peer-env.keep', '*.o', '*.txt', 'stale.*'])
            self.flags = rng.choice([[], ['-C'], ['--cvs-exclude']])
            rules = [rng.choice(['-C', '+C', '-Cs', '-Cr', '-Cp', '-Cx'])]
            rules += [rng.choice(['+', '-', 'P', 'R']) + ' ' + rng.choice(['*.o', '*.txt', 'home.keep', 'stale.*'])]
            rng.shuffle(rules)
            self.check_rules(direction, seed, rules, rng.choice((False, True)))

    def test_local(self): self.run_cases('local')
    def test_push(self): self.run_cases('push')
    def test_pull(self): self.run_cases('pull')

    def test_pull_rejects_global_cvs_disagreement_before_writes(self):
        self.fixture(True)
        before = difftest.snapshot(str(self.root))
        result, actual, output = self.copy(True, 'pull', ['-C'], False)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn(b'rejecting excluded file-list name', result.stderr)
        self.assertEqual(actual, before)
        self.assertEqual(output, [])

    def test_global_list_clear(self):
        # Released reference binaries reject ! in CVS word lists. Verify the
        # documented clearing directly, retaining unrelated CLI exclusions.
        self.flags = []
        self.client_home = '*.o ! home.keep'
        self.client_ignore = '! env.keep'
        self.peer_home = self.client_home
        self.peer_ignore = self.client_ignore
        for direction in ('local', 'push', 'pull'):
            self.fixture(direction != 'local')
            before = difftest.snapshot(str(self.root))
            result, actual, _ = self.copy(True, direction, ['- *.txt', '-C'], False)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ('b.o', 'home.keep'):
                self.assertEqual(actual['dst/' + name]['hash'], before['src/' + name]['hash'])
            for name in ('env.keep', 'a.txt'):
                self.assertEqual(actual['dst/' + name]['hash'], before['dst/' + name]['hash'])


if __name__ == '__main__': unittest.main()
