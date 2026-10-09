#!/usr/bin/env python3
"""Receiver prune-empty differential fuzzer for transfers and source listings."""
import os
import random
import shlex
import subprocess
import unittest

import difftest
import filter_after_test as after
import filter_diff_test as filters
import output_test as transfer


class PruneDifferentials(after.AfterDifferentials):
    test_conflicting_delete_modes_leave_destination_unchanged = None
    test_file_created_during_transfer_is_deleted = None
    test_without_filter_configuration = None

    def fixture(self, remote=False):
        super().fixture(False)
        tree = difftest.Tree(str(self.root))
        tree.dirs = {name: [entry['mode'], entry['mtime']] for name, entry in difftest.snapshot(str(self.root)).items()
                     if entry['type'] == 'dir'}
        for top in ('src', 'dst'):
            for name in ('chain/deep/empty', 'unicode-é/deeper', 'a-dash/deep', 'a/deep'):
                tree.d(top + '/' + name)
        tree.done()
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([filters.RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/',
                            transfer.HOST + ':' + str(self.root) + '/'], capture_output=True, check=True, timeout=20)

    def run_prune(self, direction):
        directed = [[], ['+ */', '- *'], ['+ */', '+ *.txt', '- *'], ['H !*/'],
                    ['H *.txt', 'H *.o', 'H .hidden', 'H link'], ['P empty/'], ['+ empty/'],
                    ['P chain/deep/'], ['P chain/deep/empty/'], ['-r chain/'], ['-p chain/'],
                    ['-x chain/'], ['P */', 'H !*/'], ['R chain/', 'P */', 'H !*/'],
                    ['P empty/', 'H !*/'], ['P dir1/deep/', 'H !*/'],
                    ['-r/ {root}/dst/empty/'], ['-r/ {root}/src/empty/'],
                    ['-!r empty/'], ['-s *.o'], ['-r *.o'], ['-C'], [':C', '-C']]
        for index, rules in enumerate(directed):
            self.flags = ['-m']; self.rulefiles = {}
            for excluded in (False, True):
                self.check_rules(direction, 'global-' + str(index), [r.format(root=self.root) for r in rules], excluded)
        merges = [
            ([': .rules'], {'src/.rules': 'P empty/\n'}),
            ([': .rules'], {'dst/.rules': 'P empty/\n'}),
            ([': .rules'], {'src/.rules': 'R empty/\n', 'dst/.rules': 'P empty/\n'}),
            ([': .rules'], {'src/.rules': 'P empty/\n', 'dst/.rules': 'R empty/\n'}),
            ([':e .rules'], {'src/.rules': '+ */\n- *\n', 'dst/.rules': 'P dir1/\n'}),
            ([':e .rules'], {'src/.rules': '- *.o\n', 'src/dir1/.rules': '!\n- *.txt\n'}),
            ([':n .rules'], {'src/.rules': '+ */\n- *\n', 'src/dir1/.rules': '- *.o\n'}),
            (['P dir1/deep/', ':e .rules'], {'src/.rules': '+ */\n- *\n'}),
            ([': .rules'], {'src/.rules': '-C\n', 'dst/.rules': '+C\n'}),
            ([':C', '-C'], {'src/.cvsignore': '*.o *.txt\n'}),
            (['. {root}/global.rules'], {'global.rules': ':e .rules\n', 'src/.rules': '+ */\n- *\n'}),
        ]
        for index, (rules, files) in enumerate(merges):
            self.rulefiles = files
            for mode in ('--delete', '--delete-after'):
                self.flags = ['-m', mode]
                self.check_rules(direction, 'merge-' + str(index) + mode, [r.format(root=self.root) for r in rules])
        self.rulefiles = {}
        for flags in (['--min-size=1M'], ['--max-size=1'], ['--existing'], ['--ignore-existing'],
                      ['--dry-run'], ['--no-recursive', '--dirs'], ['--no-prune-empty-dirs'],
                      ['--max-delete=0'], ['--max-delete=1'], ['--max-delete=2'], ['--max-delete=3'],
                      ['--max-delete=4'], ['--max-delete=8'], ['--delete-after', '--max-delete=3']):
            self.flags = ['-m', *flags]
            self.check_rules(direction, str(flags), [])
        self.named_source = True
        for rules in ([], ['P src/empty/'], ['H !*/']):
            self.flags = ['-m']; self.rulefiles = {}
            self.check_rules(direction, 'named-' + str(rules), rules)
        self.named_source = False
        for ignore in (False, True):
            self.broken_source = True
            self.flags = ['-m', '--copy-links'] + (['--ignore-errors'] if ignore else [])
            self.check_rules(direction, 'source-error-' + str(ignore), ['+ */', '- *.o'])
        self.broken_source = False
        first = int(os.environ.get('XSYNC_PRUNE_SEED', '808400'))
        patterns = ['*.o', '*.txt', 'stale.*', '*/', 'empty/', 'chain/', 'dir1/', 'deep/', 'link', '.hidden']
        for seed in range(first, first + int(os.environ.get('XSYNC_PRUNE_CASES', '24'))):
            rng = random.Random(seed)
            self.flags = ['-m'] + (['--delete-after'] if rng.randrange(3) == 0 else [])
            self.rulefiles = {}
            rules = [rng.choice(['+', '-', 'H', 'S', 'P', 'R', '-r', '-s', '-p']) + ' ' + rng.choice(patterns)
                     for _ in range(rng.randrange(1, 6))]
            if rng.randrange(2): rules.extend(['+ */', '- *'])
            self.check_rules(direction, seed, rules, rng.choice((False, True)))

    def test_local(self): self.run_prune('local')
    def test_push(self): self.run_prune('push')
    def test_pull(self): self.run_prune('pull')

    def test_merge_shorthand_and_pruned_statistics(self):
        self.rulefiles = {'src/.rsync-filter': '- *.o\n', 'dst/.rsync-filter': 'P empty/\n'}
        for flags in (['-m', '-F'], ['-m', '-FF'], ['-m', '-FF', '--delete-after']):
            self.flags = flags
            for direction in ('local', 'push', 'pull'):
                self.check_rules(direction, str(flags), [])
        self.rulefiles = {}; self.flags = ['-m', '--stats']
        for direction in ('local', 'push', 'pull'):
            self.fixture(direction != 'local')
            result, _, _ = self.copy(True, direction, [], False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'Number of files: 11 (reg: 7, dir: 3, link: 1)', result.stdout)

    def test_empty_roots(self):
        self.rulefiles = {}
        for direction in ('local', 'push', 'pull'):
            for trailing in (False, True):
                with self.subTest(direction=direction, trailing=trailing):
                    trees = []
                    for native in (False, True):
                        self.fixture(direction != 'local')
                        source = str(self.root / 'src/empty') + ('/' if trailing else '')
                        target = str(self.root / 'new target')
                        command = [str(transfer.BINARY) if native else filters.RSYNC, '-am']
                        if native: command += ['--no-fallback']
                        if direction != 'local':
                            server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                            if direction == 'push': target = (transfer.HOST or 'fake') + ':' + target
                            else: source = (transfer.HOST or 'fake') + ':' + source
                        result = subprocess.run(command + [source, target], capture_output=True, env=self.env, timeout=20)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        if transfer.HOST and direction == 'push':
                            from ssh_test import remote_json
                            tree = remote_json('import sys,json; sys.path.insert(0,"/work/tests"); import difftest; '
                                               'print(json.dumps(difftest.snapshot(sys.argv[1])))', self.root)
                        else: tree = difftest.snapshot(str(self.root))
                        self.assertEqual('new target' in tree, trailing)
                        trees.append(tree)
                    self.assertFalse(difftest.compare(*trees))

    def test_listing_pruning(self):
        for remote in (False, True):
            self.rulefiles = {'src/.rules': '+ */\n- *.o\n'}
            self.fixture(remote)
            before = difftest.snapshot(str(self.root))
            for roots in (['src/'], ['src'], ['src/empty'], ['src', 'src/dir1']):
                for rules in ([], ['+ */', '- *'], ['P chain/deep/empty/', 'H !*/'], [':e .rules']):
                    with self.subTest(remote=remote, roots=roots, rules=rules):
                        outputs = []
                        for native in (False, True):
                            command = [str(transfer.BINARY) if native else filters.RSYNC, '-rlm']
                            if native: command += ['--no-fallback']
                            command += ['--filter=' + rule for rule in rules]
                            sources = [str(self.root / root) + ('/' if root.endswith('/') else '') for root in roots]
                            if remote:
                                server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                                command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server)]
                                sources = [(transfer.HOST or 'fake') + ':' + source for source in sources]
                            if len(sources) > 1:
                                command += ['--list-only']
                                sources += [str(self.root / 'unused listing destination')]
                            result = subprocess.run(command + sources, capture_output=True, env=self.env, timeout=20)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            outputs.append(sorted(line[43:] for line in result.stdout.splitlines()))
                        self.assertEqual(*outputs)
            self.assertEqual(difftest.snapshot(str(self.root)), before)


if __name__ == '__main__': unittest.main()
