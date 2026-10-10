#!/usr/bin/env python3
"""Requested metadata composes across byte, clone, dry-run and in-place paths."""
import os
import stat
import subprocess
import unittest

import chown_test as ownership
from acls_test import get_acl
from times_test import creation
from xattrs_test import DARWIN, get_attrs


class MetadataCompositionTests(unittest.TestCase):
    setUp = ownership.OwnershipDifferentials.setUp
    clear_acls = ownership.OwnershipDifferentials.clear_acls

    def command(self, *args):
        command = ownership.OwnershipDifferentials.command(self, *args)
        command[command.index('--out-format=%i|%n')] = '--out-format=%i|%n|%b'
        return command

    def clear_flags(self):
        if DARWIN:
            for path in [self.root] + list(self.root.rglob('*')):
                os.chflags(path, 0, follow_symlinks=False)

    def tearDown(self):
        self.clear_flags()
        ownership.OwnershipDifferentials.tearDown(self)

    def fixture(self):
        self.clear_flags()
        ownership.OwnershipDifferentials.fixture(self, metadata=True)
        for side in ('src', 'dst'):
            root = self.root / side
            for path in [root] + sorted(root.rglob('*')):
                creation(path, 1000000000 if side == 'src' else 1000000100)
                os.utime(path, (1200000000 if side == 'src' else 1300000000, 1500000000), follow_symlinks=False)
            if DARWIN and side == 'src':
                # Set blocking flags only after both names of shared inodes
                # have received their requested times.
                for path in [root] + sorted(root.rglob('*')):
                    flags = stat.UF_NODUMP if path.is_dir() else stat.UF_HIDDEN
                    if path.name in ('anchor', 'alias', 'sub'): flags |= stat.UF_IMMUTABLE
                    os.chflags(path, flags, follow_symlinks=False)

    def state(self):
        root = self.root / 'dst'
        times, flags = {}, {}
        for path in [root] + sorted(root.rglob('*')):
            st = path.lstat()
            name = str(path.relative_to(root))
            times[name] = (None if path.is_dir() or path.is_symlink() else int(st.st_atime),
                           int(st.st_birthtime) if DARWIN else None)
            if DARWIN: flags[name] = st.st_flags
        details = tuple((get_acl(root / n), get_attrs(root / n))
                        for n in ('.', 'same', 'changed', 'sub', 'sub/nested', 'anchor'))
        return ownership.snapshot(root), details, times, flags

    def test_all_requested_metadata_with_permissions_and_ownership(self):
        cases = [(direction, extra, False) for direction in ('local', 'push', 'pull')
                 for extra in ((), ('--inplace',), ('-n',))]
        if DARWIN: cases.append(('local', (), True))
        for direction, extra, clone in cases:
            with self.subTest(direction=direction, extra=extra, clone=clone):
                results = []
                for native in (False, True):
                    self.fixture()
                    before = self.state()
                    # Capturing the baseline reads data. Restore access times
                    # so the observation itself cannot affect a dry-run check.
                    for path in (self.root / 'dst').rglob('*'):
                        if not path.is_dir() and not path.is_symlink():
                            os.utime(path, (1300000000, 1500000000))
                    flags = ['-aHAXU' + ('N' if DARWIN else ''), f'--chown={self.uid}:{self.gid}',
                             '--chmod=D2755,F0640' if clone else '--chmod=D2755,F4640', *extra]
                    if DARWIN and native: flags.append('--fileflags')
                    result = subprocess.run(self.command(native, flags, direction, clone), capture_output=True,
                                            timeout=30, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, (native, result.stdout, result.stderr))
                    after = self.state()
                    if '-n' in extra: self.assertEqual(after, before)
                    else:
                        self.assertEqual((self.root / 'dst/anchor').stat().st_ino,
                                         (self.root / 'dst/alias').stat().st_ino)
                        if DARWIN and native:
                            for name, actual in after[3].items():
                                source = (self.root / 'src' / name).lstat()
                                self.assertEqual(actual, 0 if stat.S_ISLNK(source.st_mode) else source.st_flags, name)
                    # The upstream fileflags patch corrupts its U+flags wire
                    # fields. Compare all other requested metadata with modern
                    # rsync and check flags independently against source stat.
                    rows = []
                    for row in result.stdout.splitlines():
                        code, name, transferred = row.split(b'|')
                        if clone and native and name == b'changed': self.assertEqual(int(transferred), 0)
                        self.assertEqual(len(code), 12 if DARWIN and native else 11)
                        rows.append((code[:11], name))
                    results.append((after[:3], sorted(rows)))
                self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
