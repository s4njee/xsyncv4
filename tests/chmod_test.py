#!/usr/bin/env python3
"""Permission overrides alter incoming modes across data and metadata paths."""
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

import output_test as transfer
from xattrs_test import DARWIN, RSYNC

SOURCE = (0o400, 0o600, 0o644, 0o700, 0o744, 0o4755, 0o6750, 0o1755)
DESTINATION = (0o400, 0o600, 0o644, 0o700, 0o6750)
RULES = ('D2775,F664', 'ugo=rwX', 'a-x,a+X', 'Fu-s,Fg-s,Dg+s', 'a+s,o+t',
         'Fu=st', 'F0', 'F000', 'Fu=,Fg=r,Fo=', '+r,-w,=rX', 'uD+r,gF=rx')


def accessible(root):
    if not root.exists(): return
    root.chmod(0o700)
    for base, dirs, files in os.walk(root):
        for name in dirs:
            p = Path(base) / name
            if not p.is_symlink(): p.chmod(0o700)


def snapshot(root):
    result, restore = {}, []
    def capture(p):
        st = p.lstat()
        content = None
        if stat.S_ISREG(st.st_mode):
            readable = st.st_mode & 0o400
            if not readable: p.chmod(st.st_mode | 0o400)
            try: content = p.read_bytes()
            finally:
                if not readable: p.chmod(stat.S_IMODE(st.st_mode))
        result[str(p.relative_to(root))] = (st.st_mode, st.st_mtime_ns, st.st_size if stat.S_ISREG(st.st_mode) else None, content)
        if stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) & 0o700 != 0o700:
            restore.append((p, stat.S_IMODE(st.st_mode))); p.chmod(st.st_mode | 0o700)
    try:
        capture(root)
        for base, dirs, files in os.walk(root):
            for name in dirs + files: capture(Path(base) / name)
    finally:
        for p, mode in reversed(restore): p.chmod(mode)
    return result


class ChmodDifferentials(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='xsync chmod ')
        self.root = Path(tmp.name)
        self.addCleanup(tmp.cleanup)
        self.addCleanup(accessible, self.root)

    def fixture(self, inplace=False, metadata=False):
        from acls_test import set_acl
        from xattrs_test import attr_name, set_attr
        for side in ('src', 'dst'):
            root = self.root / side
            accessible(root)
            if root.exists(): shutil.rmtree(root)
            root.mkdir(); (root / 'sub').mkdir()
            for source in SOURCE:
                for destination in DESTINATION:
                    if inplace and not destination & 0o200: continue
                    for kind in ('same', 'changed'):
                        p = root / f'{kind}-{source:o}-{destination:o}'
                        p.write_bytes(b'old' if kind == 'changed' and side == 'dst' else b'data')
                        p.chmod(source if side == 'src' else destination)
                if side == 'src':
                    p = root / f'new-{source:o}'; p.write_bytes(b'new'); p.chmod(source)
            (root / 'sub/file').write_bytes(b'nested'); (root / 'sub/file').chmod(0o744 if side == 'src' else 0o600)
            (root / 'anchor').write_bytes(b'linked contents'); os.link(root / 'anchor', root / 'alias')
            (root / 'anchor').chmod(0o744 if side == 'src' else 0o600)
            (root / 'link').symlink_to('sub/file'); os.mkfifo(root / 'fifo', 0o640)
            if metadata:
                set_acl(root / 'anchor', 0 if side == 'src' else 1)
                set_attr(root / 'anchor', attr_name('chmod-composition'), side.encode())
            for p in [root] + sorted(root.rglob('*')): os.utime(p, (1500000000, 1500000000), follow_symlinks=False)
            (root / 'sub').chmod(0o2750 if side == 'src' else 0o755)

    def command(self, native, flags, direction, clone=False, helper_flags=()):
        command = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n']
        if native:
            command += ['--no-fallback', '-j8']
            if not clone: command += ['--no-clone']
        a, b = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            helper = shlex.join([str(transfer.BINARY) if native else RSYNC, *helper_flags])
            command += ['-e', transfer.RSH, '--rsync-path=' + helper]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        return command + [a, b]

    def check(self, flags, direction='local', clone=False, umask=0o22, helper_flags=()):
        from acls_test import get_acl
        from xattrs_test import get_attrs
        results = []
        for native in (False, True):
            self.fixture(inplace='--inplace' in flags, metadata=any('AX' in f for f in flags))
            before, source = snapshot(self.root / 'dst'), snapshot(self.root / 'src')
            result = subprocess.run(self.command(native, flags, direction, clone, helper_flags), capture_output=True, timeout=60,
                                    umask=umask, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (native, flags, direction, result.stderr))
            after = snapshot(self.root / 'dst')
            self.assertEqual(snapshot(self.root / 'src'), source)
            if '-n' in flags: self.assertEqual(after, before)
            if any('H' in f and f.startswith('-') and not f.startswith('--') for f in flags) and '-n' not in flags:
                self.assertEqual((self.root / 'dst/anchor').stat().st_ino, (self.root / 'dst/alias').stat().st_ino)
            extra = (get_acl(self.root / 'dst/anchor'), get_attrs(self.root / 'dst/anchor')) if any('AX' in f for f in flags) else None
            # U-09 intentionally adds a dry-run summary that rsync omits;
            # dry_summary_test.py checks it independently of itemization.
            results.append((after, extra, sorted(line for line in result.stdout.splitlines()
                                                if not line.startswith(b'would transfer '))))
        self.assertEqual(results[1], results[0], (flags, direction, clone, umask))

    def test_numeric_symbolic_directory_file_and_special_modes(self):
        for direction in ('local', 'push', 'pull'):
            for rule in RULES:
                with self.subTest(direction=direction, rule=rule): self.check(['-a', '--chmod=' + rule], direction)

    def test_without_perms_executability_and_repeated_options(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-rltD', '--chmod=ugo=rwX'], ['-rltDE', '--chmod=a-x,a+X'],
                          ['-a', '--chmod=a-x', '--chmod=u+X,g+X'], ['-a', '--chmod=D2775,F664', '--no-perms']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction)

    def test_clone_links_checksum_inplace_dry_run_and_acls(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-a', '--chmod=D2775,F640', '-n'], ['-a', '--chmod=ugo=rwX', '--inplace'],
                          ['-aH', '--chmod=ugo=rwX'], ['-aL', '--chmod=ugo=rwX'],
                          ['-a', '--chmod=ugo=rwX', '--checksum'], ['-aHAX', '--chmod=D2775,F640']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction)
        if DARWIN:
            for flags in (['-a', '--chmod=ugo=rwX'], ['-aHAX', '--chmod=D2775,F640']):
                with self.subTest(clone=True, flags=flags): self.check(flags, clone=True)

    def test_omitted_classes_obey_umask(self):
        for direction in ('local', 'push', 'pull'):
            for mask in (0, 0o22, 0o77):
                with self.subTest(direction=direction, umask=mask): self.check(['-a', '--chmod=+rwX,-w,=rX'], direction, umask=mask)

    def test_explicit_helper_rules(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                self.check(['-a', '--chmod=a-x,a+X'], direction, helper_flags=['--chmod=Fu+x'])

    def test_acl_replacement_reports_basic_permissions_and_special_bits(self):
        from acls_test import get_acl, set_acl
        for direction in ('local', 'push', 'pull'):
            for dry in (False, True):
                for rule in ('D755,F640', 'D2755,F4640'):
                    with self.subTest(direction=direction, dry=dry, rule=rule):
                        results = []
                        for native in (False, True):
                            self.fixture(metadata=True)
                            for side in ('src', 'dst'):
                                for name in ('.', 'sub', 'sub/file'):
                                    p = self.root / side / name
                                    set_acl(p, 0 if side == 'src' else 1)
                                    if side == 'dst': p.chmod(0o700 if p.is_dir() else 0o600)
                            flags = ['-aAX', '--chmod=' + rule] + (['-n'] if dry else [])
                            result = subprocess.run(self.command(native, flags, direction), capture_output=True, timeout=20,
                                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                            self.assertEqual(result.returncode, 0, result.stderr)
                            state = snapshot(self.root / 'dst')
                            results.append((state, tuple(get_acl(self.root / 'dst' / n) for n in ('.', 'sub', 'sub/file')),
                                            sorted(line for line in result.stdout.splitlines()
                                                   if not line.startswith(b'would transfer '))))
                        self.assertEqual(results[1], results[0])

    @unittest.skipIf(DARWIN, 'POSIX default ACLs')
    def test_default_acl_change_does_not_consume_basic_mode_itemization(self):
        from acls_test import get_acl, set_acl
        for direction in ('local', 'push', 'pull'):
            results = []
            for native in (False, True):
                self.fixture()
                for side in ('src', 'dst'):
                    p = self.root / side
                    set_acl(p, inherit=side == 'src')
                    if side == 'dst': p.chmod(0o700)
                result = subprocess.run(self.command(native, ['-aA', '--chmod=D775,F640'], direction), capture_output=True, timeout=20,
                                        env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                self.assertEqual(result.returncode, 0, result.stderr)
                results.append((snapshot(self.root / 'dst'), get_acl(self.root / 'dst'), sorted(result.stdout.splitlines())))
            self.assertEqual(results[1], results[0])

    def test_shared_destination_xattrs_compare_each_source(self):
        from xattrs_test import attr_name, set_attr, snapshot as attr_snapshot
        name = attr_name('chmod-shared')
        for direction in ('local', 'push', 'pull'):
            for values in ((b'alias-src', b'anchor-src'), (b'dst', b'anchor-src'), (b'alias-src', b'dst')):
                with self.subTest(direction=direction, values=values):
                    results = []
                    for native in (False, True):
                        self.fixture()
                        alias = self.root / 'src/alias'
                        alias.unlink(); shutil.copy2(self.root / 'src/anchor', alias)
                        os.utime(self.root / 'src', (1500000000, 1500000000))
                        set_attr(alias, name, values[0])
                        set_attr(self.root / 'src/anchor', name, values[1])
                        set_attr(self.root / 'dst/anchor', name, b'dst')
                        result = subprocess.run(self.command(native, ['-aX', '--chmod=F640'], direction),
                                                capture_output=True, timeout=20,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        results.append((snapshot(self.root / 'dst'), attr_snapshot(self.root / 'dst'),
                                        sorted(result.stdout.splitlines())))
                    self.assertEqual(results[1], results[0])

    @unittest.skipIf(DARWIN, 'POSIX access ACL mode reconstruction')
    def test_posix_acl_group_modes_on_metadata_and_data_updates(self):
        from acls_test import get_acl, set_acl
        names = ('same-744-600', 'changed-744-600')
        for direction in ('local', 'push', 'pull'):
            for flags in ('-aA', '-rltDA', '-rltDAE'):
                with self.subTest(direction=direction, flags=flags):
                    results = []
                    for native in (False, True):
                        self.fixture()
                        for side in ('src', 'dst'):
                            for name in names:
                                p = self.root / side / name
                                p.chmod(0o750 if side == 'src' else 0o600)
                                set_acl(p, 0 if side == 'src' else 1)
                                os.utime(p, (1500000000, 1500000000))
                        result = subprocess.run(self.command(native, [flags, '--chmod=F660'], direction),
                                                capture_output=True, timeout=20,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        results.append((snapshot(self.root / 'dst'),
                                        tuple(get_acl(self.root / 'dst' / n) for n in names),
                                        sorted(result.stdout.splitlines())))
                    self.assertEqual(results[1], results[0])

    def test_invalid_rules_fail_before_writes(self):
        self.fixture()
        before = snapshot(self.root / 'dst')
        for rule in ('', ',', 'u', 'u8', '8', '10000', 'DF755', 'Du+x,F', 'u=r,', 'u=r,g=u',
                     'u+r+w', 'u+q', '755x', 'u755', 'F=777', 'u=r, bad'):
            with self.subTest(rule=rule):
                result = subprocess.run(self.command(True, ['-a', '--chmod=' + rule], 'local'), capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn(b'Invalid argument passed to --chmod', result.stderr)
                self.assertEqual(snapshot(self.root / 'dst'), before)

    def test_listing_modes_without_source_writes(self):
        for direction in ('local', 'pull'):
            for rule in ('D2775,F640', 'a-x,a+X'):
                with self.subTest(direction=direction, rule=rule):
                    results = []
                    for native in (False, True):
                        self.fixture()
                        before = snapshot(self.root / 'src')
                        binary = str(transfer.BINARY) if native else RSYNC
                        command = [binary, '-rltp', '--chmod=' + rule]
                        if native: command += ['--no-fallback']
                        source = str(self.root / 'src') + '/'
                        if direction == 'pull':
                            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(binary)]
                            source = 'fake:' + source
                        result = subprocess.run(command + [source], capture_output=True, timeout=15,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', TZ='UTC', LC_ALL='C.UTF-8'))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(snapshot(self.root / 'src'), before)
                        results.append(sorted(result.stdout.splitlines()))
                    self.assertEqual(results[1], results[0])

    def test_restrictive_directory_modes_finalize_after_children(self):
        # Modern rsync can lose pathname access after applying these root modes
        # and report partial failure. Native pinned directories finish children
        # and metadata before making the root restrictive.
        for direction in ('local', 'push', 'pull'):
            for rule, directory_mode in (('D0,F600', 0), ('u=st', 0o5055)):
                with self.subTest(direction=direction, rule=rule):
                    self.fixture()
                    result = subprocess.run(self.command(True, ['-a', '--chmod=' + rule], direction), capture_output=True, timeout=30,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    state = snapshot(self.root / 'dst')
                    self.assertEqual(stat.S_IMODE(state['.'][0]), directory_mode)
                    self.assertEqual(state['changed-644-600'][3], b'data')
                    self.assertEqual(state['new-644'][3], b'new')

    def test_relative_file_lists_and_single_file_rename(self):
        for direction in ('local', 'push', 'pull'):
            for selection in ('relative', 'files-from', 'rename'):
                with self.subTest(direction=direction, selection=selection):
                    results = []
                    for native in (False, True):
                        self.fixture()
                        names = self.root / 'names'; names.write_text('sub/file\nchanged-644-600\n')
                        command = [str(transfer.BINARY) if native else RSYNC, '-ar', '--chmod=D2775,F640', '--out-format=%i|%n']
                        if native: command += ['--no-fallback', '--no-clone']
                        source, destination = 'src/', 'dst/'
                        if selection == 'relative': source = 'src/./sub/file'; command += ['-R']
                        elif selection == 'files-from': command += ['--files-from=' + str(names)]
                        else: source, destination = 'src/changed-644-600', 'dst/renamed'
                        if direction != 'local':
                            binary = str(transfer.BINARY) if native else RSYNC
                            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(binary)]
                            if direction == 'push': destination = 'fake:' + str(self.root) + '/' + destination
                            else: source = 'fake:' + str(self.root) + '/' + source
                        result = subprocess.run(command + [source, destination], cwd=self.root, capture_output=True, timeout=15,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        rows = snapshot(self.root / 'dst')
                        # A root with no source attributes has an unrequested
                        # current-clock mtime after temporary files are renamed.
                        rows['.'] = (rows['.'][0], None, *rows['.'][2:])
                        results.append((rows, sorted(result.stdout.splitlines())))
                    self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
