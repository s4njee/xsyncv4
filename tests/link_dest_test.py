#!/usr/bin/env python3
"""Snapshot reuse compares data, selected metadata and prior-inode stability."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import stat
import tempfile
import random
import re
import json
import sys
import time
import unittest

import output_test as transfer
from acls_test import get_acl, set_acl
from xattrs_test import DARWIN, RSYNC, attr_name, get_attrs, set_attr

REFERENCE_ONLY = os.environ.get('XSYNC_LINK_DEST_REFERENCE_ONLY') == '1'


class LinkDestDifferentials(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync link dest ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def fixture(self, scenario):
        for child in self.root.iterdir():
            shutil.rmtree(child) if child.is_dir() and not child.is_symlink() else child.unlink()
        source, basis, target = [self.root / name for name in ('source', 'previous snapshot', 'new snapshot')]
        source.mkdir(); (source / 'nested').mkdir()
        (source / 'file').write_bytes(random.Random(687).randbytes(8 * 1024 * 1024) if scenario == 'large-change' else b'snapshot data' * 1024 + bytes(16384))
        (source / 'nested/file').write_bytes(b'nested snapshot data')
        if scenario.startswith('symlink-'):
            (source / 'file').unlink(); (source / 'file').symlink_to('absent referent')
        elif scenario.startswith('fifo-'):
            (source / 'file').unlink(); os.mkfifo(source / 'file', 0o640)
        if scenario.startswith('hardlink-'): (source / 'alias').hardlink_to(source / 'file')
        for path in (source, source / 'nested', source / 'file', source / 'nested/file'):
            if not path.is_symlink(): path.chmod(0o750 if path.is_dir() else 0o640)
            os.utime(path, (1500000000, 1500000000), follow_symlinks=False)
        if (source / 'file').is_file() and not (source / 'file').is_symlink():
            set_attr(source / 'file', attr_name('snapshot'), b'metadata')
        subprocess.run([RSYNC, '-aHX' if scenario == 'hardlink-shared' else '-aX', str(source) + '/', str(basis)], check=True, capture_output=True)
        if scenario == 'basis-symlink':
            actual = self.root / 'real previous snapshot'; basis.rename(actual); basis.symlink_to(actual, target_is_directory=True)
        if scenario == 'destination-symlink':
            parent = self.root / 'physical destination'; parent.mkdir()
            actual = parent / 'new snapshot'; actual.mkdir()
            basis.rename(parent / 'previous snapshot'); basis = parent / 'previous snapshot'
            target.symlink_to(actual, target_is_directory=True)
        if scenario == 'acl':
            if DARWIN: subprocess.run(['chmod', '+a', 'group:wheel allow read,readattr', str(source / 'file')], check=True, capture_output=True)
            else: set_acl(source / 'file', 1)
        if scenario == 'dir-mode':
            basis.chmod(0o700); (basis / 'nested').chmod(0o700)
        if scenario == 'dir-time':
            os.utime(basis, (1500000001, 1500000001)); os.utime(basis / 'nested', (1500000001, 1500000001))
        if scenario == 'dir-xattr': set_attr(basis / 'nested', attr_name('old-directory'), b'old value')
        if scenario == 'large-change':
            with (source / 'file').open('r+b') as stream:
                stream.seek(4 * 1024 * 1024 + 31); stream.write(b'edited record')
            os.utime(source / 'file', (1500000002, 1500000002))
        if scenario == 'fifo-mode': (basis / 'file').chmod(0o600)
        if scenario in ('fifo-time', 'symlink-time'): os.utime(basis / 'file', (1500000001, 1500000001), follow_symlinks=False)
        if scenario == 'symlink-target':
            (source / 'file').unlink(); (source / 'file').symlink_to('new absent referent')
            os.utime(source / 'file', (1500000000, 1500000000), follow_symlinks=False)
            os.utime(source, (1500000000, 1500000000))
        if scenario in ('mode', 'no-perms', 'no-perms-changed', 'xattr-no-perms'): (basis / 'file').chmod(0o600)
        if scenario in ('executability', 'executability-changed'): (source / 'file').chmod(0o755)
        if scenario == 'ownership': os.chown(basis / 'file', 10001, 10002)
        if scenario in ('time', 'size-only', 'checksum-time'): os.utime(basis / 'file', (1500000001, 1500000001))
        if scenario in ('changed', 'no-perms-changed', 'executability-changed'):
            (source / 'file').write_bytes(b'changed contents')
            os.utime(source / 'file', (1500000002, 1500000002))
        if scenario == 'checksum-data':
            with (basis / 'file').open('r+b') as stream: stream.write(b'old data here')
            os.utime(basis / 'file', (1500000000, 1500000000))
        if scenario in ('xattr', 'xattr-no-perms'): set_attr(basis / 'file', attr_name('snapshot'), b'old metadata')
        if scenario == 'multiple':
            shutil.copytree(basis, self.root / 'older snapshot', copy_function=shutil.copy2)
            (self.root / 'older snapshot/file').chmod(0o600)
        if scenario in ('existing', 'existing-shared', 'existing-ignore', 'existing-update'):
            target.mkdir(); (target / 'nested').mkdir()
            if scenario == 'existing-shared':
                os.link(basis / 'file', target / 'file')
                (source / 'file').chmod(0o600)
            else: (target / 'file').write_bytes(b'outdated target')
            for path in (target, target / 'nested'): os.utime(path, (1, 1))
            if scenario == 'existing': os.utime(target / 'file', (1, 1))
            if scenario in ('existing-ignore', 'existing-update'): os.utime(target / 'file', (1500000002, 1500000002))
        return source, basis, target

    def snapshot(self, root):
        root = root.resolve()
        result = {}
        for path in [root] + sorted(root.rglob('*')):
            st = path.lstat()
            result[str(path.relative_to(root))] = (st.st_mode & 0o7777, st.st_uid, st.st_gid,
                                                  st.st_mtime_ns, path.read_bytes() if stat.S_ISREG(st.st_mode) else os.readlink(path) if stat.S_ISLNK(st.st_mode) else None,
                                                  get_attrs(path), get_acl(path))
        return result

    def check(self, scenario, direction, flags=(), relative=False):
        results = []
        for native in ((False,) if REFERENCE_ONLY else (False, True)):
            source, basis, target = self.fixture(scenario)
            prior = self.snapshot(basis)
            command = [str(transfer.BINARY) if native else RSYNC, '-a', *flags, '--out-format=%i|%n']
            if native: command += ['--no-fallback', '--no-clone', '-j8']
            if scenario == 'multiple': command += ['--link-dest=' + str(self.root / 'older snapshot')]
            if scenario == 'maximum': command += ['--link-dest=' + str(basis)] * 19
            command += ['--link-dest=' + ('../previous snapshot' if relative else str(basis))]
            a, b = str(source) + '/', str(target) + '/'
            if direction != 'local':
                command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
                if direction == 'push': b = 'fake:' + b
                else: a = 'fake:' + a
            result = subprocess.run(command + [a, b], capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (native, scenario, direction, result.stdout, result.stderr))
            if '-n' in flags:
                self.assertFalse(target.exists())
                self.assertEqual(self.snapshot(basis), prior)
                results.append(sorted(result.stdout.splitlines()))
                continue
            # Hard-link creation changes ctime/nlink by definition. Prior data,
            # mode, IDs, selected times and xattrs must stay unchanged for a
            # fresh snapshot. An existing shared destination keeps rsync's
            # ordinary metadata-update semantics and is checked separately.
            if scenario != 'existing-shared': self.assertEqual(self.snapshot(basis), prior)
            same_inode = (target / 'file').lstat().st_ino == (basis / 'file').lstat().st_ino
            expected_link = scenario in ('exact', 'no-perms', 'multiple', 'maximum', 'existing', 'existing-shared', 'symlink-exact', 'fifo-exact', 'hardlink-shared', 'dir-mode', 'dir-time', 'dir-xattr', 'basis-symlink', 'destination-symlink')
            self.assertEqual(same_inode, expected_link, (native, scenario, direction))
            if stat.S_ISREG((source / 'file').lstat().st_mode):
                expected = b'outdated target' if scenario in ('existing-ignore', 'existing-update') else (basis / 'file').read_bytes() if scenario == 'checksum-data' and '-c' not in flags else (source / 'file').read_bytes()
                self.assertEqual((target / 'file').read_bytes(), expected)
            elif (source / 'file').is_symlink(): self.assertEqual(os.readlink(target / 'file'), os.readlink(source / 'file'))
            if scenario.startswith('hardlink-'):
                self.assertEqual((target / 'alias').stat().st_ino, (target / 'file').stat().st_ino)
            if scenario == 'large-change' and native and direction != 'local':
                total = sum(int(match.group(1).replace(b',', b'')) for match in re.finditer(rb'Total bytes (?:sent|received): ([0-9,]+)', result.stdout))
                self.assertGreater(total, 0, result.stdout)
                self.assertLess(total, 1024 * 1024, result.stdout)
            rows = [line for line in result.stdout.splitlines() if b'|' in line or line.startswith(b'created directory')] if '--stats' in flags else result.stdout.splitlines()
            results.append((self.snapshot(target), same_inode, sorted(rows)))
        if not REFERENCE_ONLY: self.assertEqual(results[1], results[0], (scenario, direction, flags))

    def test_regular_snapshot_selection_and_metadata(self):
        scenarios = [('exact', []), ('mode', []), ('no-perms', ['--no-perms']),
                     ('time', []), ('size-only', ['--size-only']), ('checksum-time', ['-c']),
                     ('changed', []), ('checksum-data', ['-c']), ('xattr', ['-X']), ('ignore-times', ['-I']),
                     ('multiple', []), ('maximum', []), ('existing', []), ('existing-shared', [])]
        for direction in ('local', 'push', 'pull'):
            for scenario, flags in scenarios:
                with self.subTest(direction=direction, scenario=scenario): self.check(scenario, direction, flags)

    def test_repeated_itemization_and_sparse_reuse(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-ii'], ['-S'], ['-AX'], ['--chmod=F640'], ['--ignore-existing']):
                with self.subTest(direction=direction, flags=flags):
                    self.check('exact', direction, flags)

    def test_existing_destination_guards_precede_snapshot_reuse(self):
        for direction in ('local', 'push', 'pull'):
            for scenario, flags in (('existing-ignore', ['--ignore-existing']), ('existing-update', ['--update'])):
                with self.subTest(direction=direction, scenario=scenario): self.check(scenario, direction, flags)
            source, basis, target = self.fixture('exact')
            args = [str(transfer.BINARY), '--no-fallback', '-a', '--existing', '--link-dest=' + str(basis)]
            a, b = str(source) + '/', str(target) + '/'
            if direction != 'local':
                args += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY))]
                if direction == 'push': b = 'fake:' + b
                else: a = 'fake:' + a
            result = subprocess.run(args + [a, b], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / 'file').exists())
            self.assertFalse((target / 'nested/file').exists())

    def test_directory_metadata_and_acls(self):
        for direction in ('local', 'push', 'pull'):
            for scenario, flags in (('dir-mode', []), ('dir-time', []), ('dir-xattr', ['-X']), ('acl', ['-A'])):
                with self.subTest(direction=direction, scenario=scenario): self.check(scenario, direction, flags)

    def test_permission_inheritance_and_ownership(self):
        for direction in ('local', 'push', 'pull'):
            for scenario, flags in (('no-perms-changed', ['--no-perms']), ('executability', ['--no-perms', '-E']),
                                    ('executability-changed', ['--no-perms', '-E']), ('xattr-no-perms', ['--no-perms', '-X'])):
                with self.subTest(direction=direction, scenario=scenario): self.check(scenario, direction, flags)
            if os.getuid() == 0:
                with self.subTest(direction=direction, scenario='ownership'):
                    self.check('ownership', direction, ['--numeric-ids', '--chown=0:0'])

    def test_selected_access_and_creation_times_prevent_sharing(self):
        from times_test import creation
        for direction in ('local', 'push', 'pull'):
            for extra in (['-UU', '-N'] if DARWIN else ['-UU']):
                results = []
                for native in (False, True):
                    source, basis, target = self.fixture('exact')
                    for parent in (source, basis):
                        for path in [parent] + list(parent.rglob('*')):
                            os.utime(path, (1200000000, 1500000000))
                            creation(path, 1000000000)
                    if extra == '-N': creation(basis / 'file', 1000000001)
                    else: os.utime(basis / 'file', (1200000001, 1500000000))
                    args = [str(transfer.BINARY) if native else RSYNC, '-a', extra, '--out-format=%i|%n', '--link-dest=' + str(basis)]
                    if native: args += ['--no-fallback', '--no-clone']
                    a, b = str(source) + '/', str(target) + '/'
                    if direction != 'local':
                        args += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
                        if direction == 'push': b = 'fake:' + b
                        else: a = 'fake:' + a
                    result = subprocess.run(args + [a, b], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, (native, extra, result.stderr))
                    dest = (target / 'file').stat()
                    if native or extra == '-N': self.assertNotEqual(dest.st_ino, (basis / 'file').stat().st_ino)
                    self.assertEqual(int(dest.st_birthtime) if extra == '-N' else int(dest.st_atime), 1000000000 if extra == '-N' else 1200000000)
                    self.assertEqual((target / 'file').read_bytes(), (source / 'file').read_bytes())
                    results.append(sorted(result.stdout.splitlines()))
                # rsync can share the inode for -U and update the old snapshot's
                # access time. Native selection requires matching requested
                # atimes and copies this file independently.
                if extra == '-N': self.assertEqual(results[0], results[1], (direction, extra))

    def test_large_delta_bases_are_read_only(self):
        for direction in ('local', 'push', 'pull'):
            for inplace in (False, True):
                flags = ['--stats', '--no-whole-file'] + (['--inplace'] if inplace else [])
                with self.subTest(direction=direction, inplace=inplace): self.check('large-change', direction, flags)

    def test_symlinks_special_files_and_hard_link_groups(self):
        for direction in ('local', 'push', 'pull'):
            for scenario in ('symlink-exact', 'symlink-time', 'symlink-target', 'fifo-exact', 'fifo-mode', 'fifo-time', 'hardlink-shared', 'hardlink-separate'):
                flags = ['-HX'] if scenario.startswith('hardlink-') else ['-X']
                with self.subTest(direction=direction, scenario=scenario): self.check(scenario, direction, flags)

    def test_relative_paths_and_dry_run(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction, dry=False): self.check('exact', direction, relative=True)
            with self.subTest(direction=direction, dry=True): self.check('exact', direction, ['-n'], relative=True)
            with self.subTest(direction=direction, root='basis'): self.check('basis-symlink', direction)
            with self.subTest(direction=direction, root='destination'): self.check('destination-symlink', direction, relative=True)

    def test_missing_empty_and_too_many_bases(self):
        for direction in ('local', 'push', 'pull'):
            for empty in (False, True):
                results = []
                for native in (False, True):
                    source, basis, target = self.fixture('exact')
                    if empty:
                        target.mkdir(); target.chmod(0o750)
                        os.utime(target, (1500000000, 1500000000))
                    value = '' if empty else str(self.root / 'absent snapshot')
                    args = [str(transfer.BINARY) if native else RSYNC, '-a', '--link-dest=' + value, '--out-format=%i|%n']
                    if native: args += ['--no-fallback', '--no-clone']
                    a, b = str(source) + '/', str(target) + '/'
                    if direction != 'local':
                        args += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
                        if direction == 'push': b = 'fake:' + b
                        else: a = 'fake:' + a
                    result = subprocess.run(args + [a, b], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    if native or not empty: self.assertIn(b'link-dest', result.stderr)
                    self.assertNotEqual((target / 'file').stat().st_ino, (basis / 'file').stat().st_ino)
                    # rsync itemizes the newly created root against its dummy
                    # basis when all --link-dest arguments are unavailable.
                    # xsync reports newly created directories as new.
                    # Regular-file rows and the final tree agree.
                    root_rows = [row for row in result.stdout.splitlines() if row.endswith(b'|./')]
                    if not empty:
                        self.assertEqual(len(root_rows), 1)
                        self.assertTrue(root_rows[0].startswith(b'cd'), root_rows)
                        if native: self.assertEqual(root_rows[0], b'cd+++++++++|./')
                    results.append((self.snapshot(target), sorted(row for row in result.stdout.splitlines() if not row.startswith((b'cd', b'.d')))))
                self.assertEqual(results[0], results[1])
        source, basis, target = self.fixture('exact')
        result = subprocess.run([str(transfer.BINARY), '--no-fallback', '-a', *(['--link-dest=' + str(basis)] * 21), str(source) + '/', str(target)], capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(target.exists())

    def test_selection_and_single_file_destination_names(self):
        for direction in ('local', 'push', 'pull'):
            for selection in ('files-from', 'relative', 'single-file', 'renamed-file'):
                results = []
                for native in (False, True):
                    source, basis, target = self.fixture('exact')
                    target.mkdir(); target.chmod(0o750); os.utime(target, (1500000000, 1500000000))
                    args = [str(transfer.BINARY) if native else RSYNC, '-ar', '--link-dest=' + str(basis), '--out-format=%i|%n']
                    if native: args += ['--no-fallback', '--no-clone']
                    a, b = str(source) + '/', str(target) + '/'
                    if selection == 'files-from':
                        listing = self.root / 'files'; listing.write_bytes(b'nested/file\0')
                        args += ['--from0', '--files-from=' + str(listing)]
                    elif selection == 'relative':
                        args.append('-R'); a = str(source) + '/./nested/file'
                    else:
                        a = str(source / 'file'); b = str(target / ('file' if selection == 'single-file' else 'renamed'))
                    if direction != 'local':
                        args += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
                        if direction == 'push': b = 'fake:' + b
                        else: a = 'fake:' + a
                    result = subprocess.run(args + [a, b], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, (direction, selection, native, result.stderr))
                    name = 'nested/file' if selection in ('relative', 'files-from') else 'file' if selection == 'single-file' else 'renamed'
                    candidate = basis / name
                    self.assertEqual((target / name).stat().st_ino == candidate.stat().st_ino if candidate.exists() else False, selection != 'renamed-file')
                    if selection in ('relative', 'files-from'): self.assertFalse((target / 'file').exists())
                    # Single-file copies do not preserve their destination
                    # parent's mtime; compare only transfer-owned children.
                    state = self.snapshot(target); state.pop('.')
                    results.append((state, sorted(result.stdout.splitlines())))
                self.assertEqual(results[0], results[1], (direction, selection))


class LinkDestFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-linkdest-lib-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = Path(cls.library_tmp.name) / 'fault.so'
        command = ['c++', '-std=c++20', '-dynamiclib' if DARWIN else '-shared', '-fPIC',
                   str(transfer.REPO / 'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if DARWIN: command += ['-arch', 'arm64', '-arch', 'x86_64']
        else: command.append('-ldl')
        subprocess.run(command, check=True, capture_output=True)
        cls.injected_binary = transfer.BINARY
        if DARWIN and os.environ.get('XSYNC_TEST_ARCH'):
            # A system shell clears DYLD variables. Re-inject after arch has
            # launched, for both the client and the direct fake-SSH helper.
            cls.injected_binary = Path(cls.library_tmp.name) / 'arch-helper.py'
            launcher = ['/usr/bin/arch', '-' + os.environ['XSYNC_TEST_ARCH'], '-e',
                        'DYLD_INSERT_LIBRARIES=' + str(cls.fault), os.environ['XSYNC_TEST_EXECUTABLE']]
            cls.injected_binary.write_text('#!' + sys.executable + '\nimport os,sys\nos.execv("/usr/bin/arch", ' + repr(launcher) + ' + sys.argv[1:])\n')
            cls.injected_binary.chmod(0o755)

    def command(self, source, basis, target, direction, *flags):
        args = [str(self.injected_binary), '--no-fallback', '--no-clone', '-a', '--link-dest=' + str(basis), *flags]
        a, b = str(source) + '/', str(target) + '/'
        if direction != 'local':
            args += ['-e', shlex.join([sys.executable, str(transfer.REPO / 'tests/fault_ssh.py')]), '--rsync-path=' + str(self.injected_binary)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        return args + [a, b]

    def fixture(self, root):
        source, basis, target, outside = [root / name for name in ('source', 'basis', 'target', 'outside')]
        for parent in (source, basis, outside): (parent / 'nested').mkdir(parents=True)
        for parent in (source, basis):
            (parent / 'nested/file').write_bytes(b'valid snapshot' + bytes(1024 * 1024))
            (parent / 'nested/file').chmod(0o640)
            os.utime(parent / 'nested/file', (1500000000, 1500000000))
        (outside / 'nested/file').write_bytes(b'outside sentinel')
        return source, basis, target, outside

    def environment(self, basis):
        return dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FAULT_PATH=str(basis.resolve()),
                    **{'DYLD_INSERT_LIBRARIES' if DARWIN else 'LD_PRELOAD': str(self.fault)})

    def test_cross_device_links_fall_back_to_independent_copies(self):
        for direction in ('local', 'push', 'pull'):
            for sparse in (False, True):
                with self.subTest(direction=direction, sparse=sparse), tempfile.TemporaryDirectory() as tmp:
                    source, basis, target, outside = self.fixture(Path(tmp))
                    old = (basis / 'nested/file').stat()
                    env = self.environment(basis); env['XSYNC_FAULT_LINK_EXDEV'] = '1'
                    result = subprocess.run(self.command(source, basis, target, direction, *(['-S'] if sparse else [])), env=env, capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((target / 'nested/file').read_bytes(), (source / 'nested/file').read_bytes())
                    self.assertNotEqual((target / 'nested/file').stat().st_ino, old.st_ino)
                    current = (basis / 'nested/file').stat()
                    self.assertEqual((current.st_mode, current.st_ino, current.st_mtime_ns, current.st_nlink), (old.st_mode, old.st_ino, old.st_mtime_ns, old.st_nlink))
                    self.assertFalse(any(p.name.startswith('.xsync-') for p in target.rglob('*')))

    def test_replaced_basis_entries_never_publish_unchecked_links(self):
        for direction in ('local', 'push', 'pull'):
            for mutation in ('leaf', 'symlink', 'parent', 'metadata'):
                with self.subTest(direction=direction, mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    source, basis, target, outside = self.fixture(root)
                    marker = root / 'selected'
                    env = self.environment(basis)
                    env.update(XSYNC_FAULT_AT_OP='link', XSYNC_FAULT_AT_NAME='file', XSYNC_FAULT_AT_NOTIFY=str(marker))
                    proc = subprocess.Popen(self.command(source, basis, target, direction), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        deadline = time.monotonic() + 10
                        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline: time.sleep(.005)
                        self.assertTrue(marker.exists(), 'basis publication not reached')
                        if mutation == 'parent':
                            (basis / 'nested').rename(basis / 'pinned')
                            (basis / 'nested').symlink_to(outside / 'nested', target_is_directory=True)
                        elif mutation == 'metadata': (basis / 'nested/file').chmod(0o600)
                        else:
                            (basis / 'nested/file').rename(basis / 'old file')
                            if mutation == 'leaf': (basis / 'nested/file').write_bytes(b'changed snapshot')
                            else: (basis / 'nested/file').symlink_to(outside / 'nested/file')
                        out, err = proc.communicate(timeout=15)
                    finally:
                        if proc.poll() is None: proc.kill()
                        proc.communicate()
                    self.assertEqual(proc.returncode, 0, (out, err))
                    self.assertEqual((target / 'nested/file').read_bytes(), (source / 'nested/file').read_bytes())
                    self.assertEqual((target / 'nested/file').stat().st_mode & 0o777, 0o640)
                    self.assertEqual((outside / 'nested/file').read_bytes(), b'outside sentinel')
                    self.assertEqual((outside / 'nested/file').stat().st_nlink, 1)
                    self.assertFalse(any(p.name.startswith('.xsync-') for p in target.rglob('*')))


@unittest.skipUnless(transfer.HOST, 'run via tests/ssh-rig.sh')
class LinkDestSSH(unittest.TestCase):
    def test_snapshot_reuse_and_changed_delta(self):
        from ssh_test import SSHTests, remote_code, remote_json
        SSHTests.setUpClass()
        snapshot = '''import os,pathlib,sys,json,hashlib,stat
p=pathlib.Path(sys.argv[1]);result={}
for f in sorted(p.rglob('*')):
 s=f.lstat();result[str(f.relative_to(p))]=[s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_mtime_ns,hashlib.sha256(f.read_bytes()).hexdigest() if stat.S_ISREG(s.st_mode) else os.readlink(f) if stat.S_ISLNK(s.st_mode) else None]
print(json.dumps(result))'''
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction), tempfile.TemporaryDirectory(dir='/rig', prefix='link dest ssh ') as tmp:
                root = Path(tmp); source, basis, target = [root / name for name in ('source', 'basis', 'target')]
                source.mkdir(); (source / 'file').write_bytes(random.Random(687).randbytes(8 * 1024 * 1024))
                (source / 'alias').hardlink_to(source / 'file'); (source / 'link').symlink_to('file'); os.mkfifo(source / 'fifo')
                set_attr(source / 'file', attr_name('snapshot'), b'metadata')
                for path in source.iterdir(): os.utime(path, (1500000000, 1500000000), follow_symlinks=False)
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', root)
                try:
                    if direction == 'pull':
                        subprocess.run([RSYNC, '-aHX', '-e', transfer.RSH, str(source) + '/', transfer.HOST + ':' + str(source) + '/'], check=True, capture_output=True)
                    a = (transfer.HOST + ':' if direction == 'pull' else '') + str(source) + '/'
                    remote_prefix = transfer.HOST + ':' if direction == 'push' else ''
                    args = [str(transfer.BINARY), '--no-fallback', '-aHSX', '--stats', '-e', transfer.RSH, '--rsync-path=/usr/local/bin/xsync']
                    first = subprocess.run(args + [a, remote_prefix + str(basis) + '/'], capture_output=True, timeout=30)
                    self.assertEqual(first.returncode, 0, first.stderr)
                    def state(path):
                        return remote_json(snapshot, path) if direction == 'push' else json.loads(subprocess.check_output([sys.executable, '-c', snapshot, str(path)]))
                    prior = state(basis)
                    second = subprocess.run(args + ['--link-dest=../basis', a, remote_prefix + str(target) + '/'], capture_output=True, timeout=30)
                    self.assertEqual(second.returncode, 0, second.stderr)
                    current = state(target)
                    self.assertEqual(current, prior)
                    self.assertEqual(state(basis), prior)
                    change = '''import os,pathlib,sys
p=pathlib.Path(sys.argv[1])/'file'
with p.open('r+b') as f: f.seek(4*1024*1024+31);f.write(b'edited record')
os.utime(p,(1500000002,1500000002))'''
                    if direction == 'pull': remote_code(change, source)
                    else: subprocess.run([sys.executable, '-c', change, str(source)], check=True)
                    changed = root / 'changed'
                    third = subprocess.run(args + ['--no-whole-file', '--inplace', '--link-dest=../basis', a, remote_prefix + str(changed) + '/'], capture_output=True, timeout=30)
                    self.assertEqual(third.returncode, 0, third.stderr)
                    total = sum(int(m.group(1).replace(b',', b'')) for m in re.finditer(rb'Total bytes (?:sent|received): ([0-9,]+)', third.stdout))
                    self.assertGreater(total, 0); self.assertLess(total, 1024 * 1024)
                    after = state(changed)
                    expected = remote_json(snapshot, source) if direction == 'pull' else json.loads(subprocess.check_output([sys.executable, '-c', snapshot, str(source)]))
                    self.assertEqual(after['file'][1:], expected['file'][1:])
                    self.assertEqual(after['file'][0], after['alias'][0])
                    self.assertNotEqual(after['file'][0], prior['file'][0])
                    self.assertEqual(state(basis), prior)
                finally: remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])', root)


if __name__ == '__main__': unittest.main()
