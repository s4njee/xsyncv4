#!/usr/bin/env python3
"""Delete-after scans the updated receiver hierarchy and merge files."""
import os
import random
import subprocess
import time
import unittest

import difftest
import filter_merge_test as merges
import filter_diff_test as filters
import output_test as transfer


class AfterDifferentials(merges.MergeDifferentials):
    reference_codes = (0, 23, 25)
    test_invalid_side_modifiers = None
    test_documented_CVS_clear = None
    test_listing_contexts_and_multiple_roots = None
    test_merge_file_errors = None

    def setUp(self):
        super().setUp()
        self.extra_files = {}
        self.broken_source = False
        self.env = dict(os.environ, HOME=str(self.root / 'CVS home'), CVSIGNORE='', XSYNC_CONFIG='', XSYNC_OPTS='')
        self.server_env = {'HOME': self.env['HOME'], 'CVSIGNORE': '', 'XSYNC_CONFIG': '', 'XSYNC_OPTS': ''}

    def fixture(self, remote=False):
        # Distinct lengths force rule-file transfers despite identical fixture
        # timestamps; comments preserve the rule meanings.
        files = self.rulefiles
        self.rulefiles = {name: ('# sender rules\n' if name.startswith('src/') else
                                '# receiver rules before transfer\n' if name.startswith('dst/') else '') + data
                          for name, data in files.items()}
        try: super().fixture(False)
        finally: self.rulefiles = files
        if self.extra_files or self.broken_source:
            tree = difftest.Tree(str(self.root))
            tree.dirs = {name: [entry['mode'], entry['mtime']] for name, entry in difftest.snapshot(str(self.root)).items()
                         if entry['type'] == 'dir'}
            for name, contents in self.extra_files.items(): tree.f(name, contents.encode())
            if self.broken_source: tree.ln('src/broken', 'missing-target')
            tree.done()
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([filters.RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/',
                            transfer.HOST + ':' + str(self.root) + '/'], capture_output=True, check=True, timeout=20)

    def run_after(self, direction):
        cases = [
            ([': .rules'], {'src/.rules': 'P stale.*\n', 'dst/.rules': 'R stale.*\n'}),
            ([': .rules'], {'src/.rules': 'R stale.*\n', 'dst/.rules': 'P stale.*\n'}),
            ([': .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': 'P *.txt\n'}),
            ([': .rules'], {'src/.rules': '-p *.o\n', 'dst/.rules': 'P *.o\n'}),
            ([': .rules'], {'src/.rules': '- *.txt\n', 'src/dir1/.rules': '!\nP /b.o\n',
                           'dst/.rules': 'P *.o\n', 'dst/dir1/.rules': 'R *.o\n'}),
            ([': .rules'], {'src/.rules': 'R *.o\n', 'src/dir1/.rules': 'P *.o\n',
                           'dst/.rules': 'P *.o\n', 'dst/dir1/.rules': 'R *.o\n'}),
            ([': .rules'], {'dst/.rules': 'P stale.*\n'}),
            ([': .rules'], {'dst/gone/.rules': 'P stale.o\n'}),
            ([':e .rules'], {'src/.rules': 'R stale.*\n', 'dst/.rules': 'P stale.*\n'}),
            ([':r .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '+ *.o\n'}),
            ([':s .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': '- stale.*\n'}),
            (['. {root}/global.rules'], {'global.rules': ': .rules\n', 'src/.rules': 'P stale.*\n'}),
            ([': .rules'], {'src/.rules': ': .next\n', 'src/.next': 'P stale.*\n',
                           'dst/.rules': ': .old\n', 'dst/.old': 'P *.txt\n'}),
            (['P stale.*', ': .rules'], {'src/.rules': '!\nR stale.*\n', 'dst/.rules': 'P *.o\n'}),
            ([': .rules', 'P stale.*'], {'src/.rules': '!\nR stale.*\n', 'dst/.rules': 'P *.o\n'}),
            ([':n .rules'], {'src/.rules': 'P stale.*\n', 'dst/.rules': 'R stale.*\n'}),
            ([':p .rules'], {'src/.rules': '- *.o\n', 'dst/.rules': 'P *.txt\n'}),
            ([':x .rules'], {'src/.rules': '-C\n', 'dst/.rules': '+C\n'}),
            ([': .rules'], {'src/.rules': '-C\n', 'dst/.rules': '+C\n'}),
            (['+ .rules', ': .rules'], {'src/.rules': '+C\n- *\n', 'dst/.rules': '-C\n'}),
        ]
        for index, (rules, files) in enumerate(cases):
            self.flags = ['--delete-after']
            self.rulefiles = {name: data.replace('{root}', str(self.root)) for name, data in files.items()}
            for deleted in (False, True):
                self.check_rules(direction, 'after-' + str(index), [r.format(root=self.root) for r in rules], deleted)
        for flags in (['-F'], ['-FF']):
            self.flags = ['--delete-after', *flags]
            self.rulefiles = {'.rsync-filter': '- *.o\n', 'src/.rsync-filter': 'P stale.*\n',
                              'dst/.rsync-filter': 'R stale.*\n', 'src/dir1/.rsync-filter': '!\nP *.o\n'}
            self.check_rules(direction, str(flags), [])
        self.rulefiles = {'src/.rules': 'R stale.*\n', 'dst/.rules': 'P stale.*\n'}
        for extra in (['--dry-run'], ['--max-delete=0'], ['--max-delete=1'], ['--max-delete=3'],
                      ['--delete-after']):
            self.flags = ['--delete-after', *extra]
            self.check_rules(direction, str(extra), [': .rules'])
        self.named_source = True
        self.flags = ['--delete-after']
        self.rulefiles = {'src/.rules': 'P stale.*\n', 'dst/.rules': '- *\n', 'dst/src/.rules': 'R stale.*\n'}
        self.extra_files = {'dst/src/stale.o': 'retained by the new rules', 'dst/src/stale.txt': 'also retained'}
        for rule in (': .rules', ': /.rules', ': ../.rules'):
            self.check_rules(direction, 'named-' + rule, [rule])
        self.named_source = False
        self.extra_files = {}
        for ignore in (False, True):
            self.broken_source = True
            self.flags = ['--delete-after', '--copy-links'] + (['--ignore-errors'] if ignore else [])
            self.rulefiles = {'src/.rules': 'R stale.*\n', 'dst/.rules': 'P stale.*\n'}
            self.check_rules(direction, 'source-error-' + str(ignore), [': .rules'])
        self.broken_source = False
        for rule in ('P old', 'R old'):
            self.flags = ['--delete-after']
            self.rulefiles = {'src/.rules': rule + '\n', 'dst/.rules': 'P old\n'}
            self.extra_files = {'src/replace-directory': 'new file', 'dst/replace-directory/old': 'old child',
                                'src/replace-file/child': 'new child', 'dst/replace-file': 'old file'}
            self.check_rules(direction, 'replacement-' + rule, [': .rules'])
        self.extra_files = {}
        first = int(os.environ.get('XSYNC_AFTER_SEED', '808300'))
        for seed in range(first, first + int(os.environ.get('XSYNC_AFTER_CASES', '24'))):
            rng = random.Random(seed)
            self.rulefiles = {}
            for directory in ('src', 'src/dir1', 'src/dir1/deep', 'dst', 'dst/dir1', 'dst/gone'):
                rules = []
                for _ in range(rng.randrange(5)):
                    rules.append('!' if rng.randrange(7) == 0 else rng.choice(['-', '+', 'P', 'R', '-p']) + ' ' +
                                 rng.choice(['*.o', '*.txt', 'stale.*', '/a.txt', '/b.o', 'deep/', 'link', '.hidden']))
                self.rulefiles[directory + '/.rules'] = '\n'.join(rules) + '\n'
            self.flags = ['--delete-after']
            self.check_rules(direction, seed, [rng.choice([':', ':e', ':n', ':p']) + ' .rules'], rng.choice((False, True)))

    def test_local(self): self.run_after('local')
    def test_push(self): self.run_after('push')
    def test_pull(self): self.run_after('pull')

    def test_without_filter_configuration(self):
        self.flags = ['--delete-after']
        self.rulefiles = {}
        for direction in ('local', 'push', 'pull'):
            self.check_rules(direction, 'without-filters', [])

    def test_conflicting_delete_modes_leave_destination_unchanged(self):
        self.rulefiles = {}
        self.fixture()
        before = difftest.snapshot(str(self.root))
        for other in ('--delete-before', '--delete-during', '--del', '--delete-delay'):
            for native in (False, True):
                command = [str(transfer.BINARY) if native else filters.RSYNC, '-a', '--delete-after', other]
                if native: command += ['--no-fallback']
                result = subprocess.run(command + [str(self.root / 'src') + '/', str(self.root / 'dst') + '/'],
                                        capture_output=True, env=self.env, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b'multiple --delete-WHEN', result.stderr)
                self.assertEqual(difftest.snapshot(str(self.root)), before)

    def test_file_created_during_transfer_is_deleted(self):
        data = b'late scan coverage\n' * 120000
        for native in (False, True):
            with self.subTest(native=native):
                self.rulefiles = {}
                self.fixture()
                source, target = self.root / 'src', self.root / 'dst'
                (source / 'slow').write_bytes(data)
                command = [str(transfer.BINARY) if native else filters.RSYNC,
                           '-a', '--delete-after', '--bwlimit=512K']
                if native: command += ['--no-fallback', '--no-clone']
                proc = subprocess.Popen(command + [str(source) + '/', str(target) + '/'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
                self.addCleanup(self.close_transfer, proc)
                deadline = time.monotonic() + 10
                while not list(target.glob('.slow.*')) and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertIsNone(proc.poll(), 'transfer finished before the destination could be changed')
                self.assertTrue(list(target.glob('.slow.*')), 'transfer did not start within ten seconds')
                (target / 'late').write_bytes(b'created after the generator scan')
                stdout, stderr = proc.communicate(timeout=15)
                self.assertEqual(proc.returncode, 0, stderr)
                self.assertFalse((target / 'late').exists())
                self.assertEqual((target / 'slow').read_bytes(), data)
                self.assertEqual((source / 'slow').read_bytes(), data)

    @staticmethod
    def close_transfer(proc):
        if proc.poll() is None: proc.kill()
        proc.communicate(timeout=5)


if __name__ == '__main__': unittest.main()
