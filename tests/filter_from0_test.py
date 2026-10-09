#!/usr/bin/env python3
"""NUL-delimited filter input and option ordering against real rsync."""
import os
import shlex
import subprocess
import unittest

import difftest
import output_test as transfer
import filter_diff_test as filters
from filter_diff_test import RSYNC


class From0Differentials(filters.FilterDifferentials):
    def fixture(self, remote=False):
        super().fixture(False)
        tree = difftest.Tree(str(self.root))
        tree.dirs = {name: [entry['mode'], entry['mtime']]
                     for name, entry in difftest.snapshot(str(self.root)).items() if entry['type'] == 'dir'}
        for top in ('src', 'dst'):
            for directory in ('', 'dir1/', 'dir1/deep/'):
                for name in ('line\nbreak', 'carriage\rreturn', 'sp ace', 'plain', '#comment', ';comment'):
                    tree.f(top + '/' + directory + name, (top + ':' + name).encode())
        for name, content in self.rulefiles.items(): tree.f(name, content)
        tree.done()
        if transfer.HOST and remote:
            from ssh_test import remote_code
            remote_code('import shutil,pathlib,sys; p=pathlib.Path(sys.argv[1]); shutil.rmtree(p,ignore_errors=True); p.mkdir()', self.root)
            subprocess.run([RSYNC, '-a', '-e', transfer.RSH, str(self.root) + '/',
                            transfer.HOST + ':' + str(self.root) + '/'],
                           capture_output=True, check=True, timeout=20)

    def run_cases(self, direction):
        nul_patterns = b'\0#comment\0;comment\0line\nbreak\0carriage\rreturn\0sp ace\0plain'
        cases = [
            (['--from0', '--exclude-from={root}/patterns'], {'patterns': nul_patterns}, []),
            (['--from0', '--include-from={root}/patterns'], {'patterns': b'*/\0' + nul_patterns}, ['- *']),
            (['--from0', '--exclude-from={root}/patterns'], {'patterns': b'a.txt\0b.o\0'}, []),
            (['--exclude-from={root}/patterns', '--from0'], {'patterns': b'a.txt\nb.o\0'}, []),
            (['--from0', '--no-from0', '--exclude-from={root}/patterns'], {'patterns': b'a.txt\nb.o\0'}, []),
            (['--from0', '--filter=. {root}/global'], {'global': b'- line\nbreak\0- carriage\rreturn\0- sp ace\0'}, []),
            (['--from0', '--filter=.- {root}/global'], {'global': nul_patterns}, []),
            (['--from0', '--filter=.+ {root}/global'], {'global': b'*/\0' + nul_patterns}, ['- *']),
            (['--from0', '--filter=.w {root}/global'], {'global': b'-_a.txt\0-_b.o\0'}, []),
            (['--filter=.w {root}/global', '--from0'], {'global': b'-_a.txt\0-_b.o\0'}, []),
            (['--from0', '--filter=.C {root}/global'], {'global': b'a.txt\0b.o\0'}, []),
            (['--from0', '--filter=. {root}/global'],
             {'global': ('. {root}/nested\0'.format(root=self.root)).encode(), 'nested': b'- line\nbreak\0- sp ace\0'}, []),
            (['--from0'], {'src/.rules': b'- line\nbreak\0- carriage\rreturn\0- sp ace\0',
                           'src/dir1/.rules': b'+ line\nbreak\0', 'dst/.rules': b'P stale.o\0P sp ace\0'}, [': .rules']),
            (['--from0'], {'src/.rules': b'- line\nbreak\0', 'dst/.rules': b'P stale.o\0'}, [':n .rules']),
            (['--from0'], {'src/.rules': b'- line\nbreak\0', 'dst/.rules': b'P stale.o\0'}, [':e .rules']),
            (['--from0'], {'src/.rules': b'line\nbreak\0carriage\rreturn\0'}, [':- .rules']),
            (['--from0'], {'src/.rules': b'-_a.txt\0-_b.o\0'}, [':w .rules']),
            (['--from0'], {'src/.cvsignore': b'a.txt\0b.o\0'}, [':C']),
            (['--from0'], {'src/.rules': b': .nested\0- line\nbreak\0',
                           'src/.nested': b'- sp ace\0', 'src/dir1/.nested': b'!\0- plain\0'}, [': .rules']),
            (['--from0'], {'src/.rules': b'- line\nbreak\0'}, [':s .rules']),
            (['--from0'], {'src/.rules': b'- line\nbreak\0', 'dst/.rules': b'- sp ace\0'}, [':r .rules']),
            (['--from0', '--delete-after'], {'src/.rules': b'P line\nbreak\0- sp ace\0',
                                            'dst/.rules': b'R line\nbreak\0P stale.o\0'}, [': .rules']),
            (['-0', '-m'], {'src/.rules': b'- line\nbreak\0'}, [': .rules']),
        ]
        for index, (flags, files, rules) in enumerate(cases):
            # rsync does not forward -0 to an SSH helper without --files-from.
            # Explicit helper flags exercise NUL parsing at either endpoint.
            self.server_flags = ['--from0'] if direction != 'local' and index >= 12 else []
            self.flags = [flag.format(root=self.root) for flag in flags]
            self.rulefiles = files
            # Nested single-instance files resolve relative to their parent.
            for deleted in (False, True):
                self.check_rules(direction, index, rules, deleted)

        # With ordinary SSH invocation the remote filter files remain line-mode,
        # while the client's directory contexts use its final -0 setting.
        self.server_flags = []
        for rule in (': .rules', ':w .rules', ':C'):
            self.flags = ['--from0']
            self.rulefiles = {'src/.rules': b'-_a.txt\0-_b.o\0', 'dst/.rules': b'-_stale.o\0-_stale.txt\0',
                             'src/.cvsignore': b'a.txt\0b.o\0'}
            self.check_rules(direction, 'default-helper-' + rule, [rule])

    def test_local(self): self.run_cases('local')
    def test_push(self): self.run_cases('push')
    def test_pull(self): self.run_cases('pull')

    def test_stdin_and_order(self):
        self.flags = []
        self.rulefiles = {}
        for flags, data in (
            (['--from0', '--exclude-from=-'], b'line\nbreak\0carriage\rreturn\0sp ace\0'),
            (['--exclude-from=-', '--from0'], b'a.txt\nb.o\0'),
            (['--from0', '--filter=. -'], b'- line\nbreak\0- sp ace\0'),
            (['--from0', '--filter=.w -'], b'-_a.txt\0-_b.o\0'),
            (['--from0', '--no-from0', '--exclude-from=-'], b'a.txt\nb.o\0'),
        ):
            with self.subTest(flags=flags):
                results = []
                for native in (False, True):
                    self.fixture()
                    command = [str(transfer.BINARY) if native else RSYNC, '-ai', '--out-format=%i|%n', *flags]
                    if native: command += ['--no-fallback', '--no-clone']
                    result = subprocess.run(command + [str(self.root / 'src') + '/', str(self.root / 'dst') + '/'],
                                            input=data, capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    results.append((difftest.snapshot(str(self.root)), sorted(result.stdout.splitlines())))
                differences = difftest.compare(results[0][0], results[1][0])
                self.assertFalse(differences, '\n'.join(differences))
                self.assertEqual(results[0][1], results[1][1])

    def test_invalid_side_modifiers(self):
        self.rulefiles = {}
        super().test_invalid_side_modifiers()

    def test_listing_and_source_integrity(self):
        self.rulefiles = {'src/.rules': b'- line\nbreak\0- carriage\rreturn\0',
                          'src/dir1/.rules': b'+ line\nbreak\0'}
        for remote in (False, True):
            self.fixture(remote)
            before = difftest.snapshot(str(self.root))
            outputs = []
            for native in (False, True):
                command = [str(transfer.BINARY) if native else RSYNC, '-r0l', '--filter=: .rules']
                if native: command += ['--no-fallback']
                source = str(self.root / 'src') + '/'
                if remote:
                    server = ('/usr/local/bin/xsync' if transfer.HOST else str(transfer.BINARY)) if native else 'rsync'
                    command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(server) + ' --from0']
                    source = (transfer.HOST or 'fake') + ':' + source
                result = subprocess.run(command + [source], capture_output=True, timeout=20,
                                        env=dict(os.environ, TZ='UTC', LC_ALL='C'))
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(result.stdout)
            self.assertEqual(*outputs)
            self.assertEqual(difftest.snapshot(str(self.root)), before)


if __name__ == '__main__': unittest.main()
