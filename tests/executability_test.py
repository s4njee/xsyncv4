#!/usr/bin/env python3
"""Compare executable-bit preservation with modern rsync, including peers."""
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest

import output_test as transfer
from xattrs_test import RSYNC

SOURCE_MODES = (0o600, 0o644, 0o700, 0o744, 0o601, 0o610, 0o640, 0o755, 0o4755)
DEST_MODES = (0o600, 0o644, 0o700, 0o744, 0o601, 0o610, 0o640, 0o755, 0o400, 0o200, 0, 0o6750)


def snapshot(root):
    return {str(p.relative_to(root)): (stat.S_IFMT(p.lstat().st_mode), stat.S_IMODE(p.lstat().st_mode),
                                     p.lstat().st_size if p.is_file() and not p.is_symlink() else None)
            for p in [root] + sorted(root.rglob('*'))}


class ExecutabilityDifferentials(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='xsync executability ')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def fixture(self, writable=False, readable=False):
        for side in ('src', 'dst'):
            root = self.root / side
            if root.exists(): shutil.rmtree(root)
            root.mkdir(); (root / 'sub').mkdir()
            for src_mode in SOURCE_MODES:
                for dst_mode in DEST_MODES:
                    if writable and not dst_mode & 0o200: continue
                    if readable and not dst_mode & 0o400: continue
                    for kind in ('same', 'changed'):
                        if kind == 'changed' and not dst_mode & 0o400: continue
                        path = root / f'{kind}-{src_mode:o}-{dst_mode:o}'
                        path.write_bytes(b'old' if side == 'dst' and kind == 'changed' else b'data')
                        path.chmod(src_mode if side == 'src' else dst_mode)
            if side == 'src':
                for mode in SOURCE_MODES:
                    path = root / f'new-{mode:o}'; path.write_bytes(b'new'); path.chmod(mode)
            (root / 'sub/file').write_bytes(b'nested')
            (root / 'sub/file').chmod(0o744 if side == 'src' else 0o640)
            (root / 'sub').chmod(0o700 if side == 'src' else 0o755)
            (root / 'link').symlink_to('sub/file')
            if side == 'src':
                for name in ('replace-dir', 'replace-link'):
                    (root / name).write_bytes(b'replacement'); (root / name).chmod(0o744)
            else:
                (root / 'replace-dir').mkdir(); (root / 'replace-link').symlink_to('sub/file')
            os.mkfifo(root / 'fifo', 0o600 if side == 'src' else 0o700)
            for path in [root] + sorted(root.rglob('*')):
                os.utime(path, (1500000000, 1500000000), follow_symlinks=False)

    def run_sync(self, native, flags, direction):
        command = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n']
        if native: command += ['--no-fallback', '--no-clone', '-j8']
        a, b = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY) if native else RSYNC)]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        result = subprocess.run(command + [a, b], capture_output=True, timeout=40,
                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
        self.assertEqual(result.returncode, 0, (native, direction, flags, result.stderr))
        return result

    def check(self, flags, direction):
        results = []
        for native in (False, True):
            self.fixture(writable='--inplace' in flags, readable=any('X' in f or f == '--checksum' for f in flags))
            before = snapshot(self.root / 'dst')
            result = self.run_sync(native, flags, direction)
            after = snapshot(self.root / 'dst')
            if '-n' in flags: self.assertEqual(after, before)
            else:
                for path in (self.root / 'dst').glob('changed-*'):
                    mode = stat.S_IMODE(path.stat().st_mode)
                    path.chmod(mode | 0o400)
                    self.assertEqual(path.read_bytes(), b'data')
                    path.chmod(mode)
            results.append((after, sorted(result.stdout.splitlines())))
        self.assertEqual(results[1], results[0], (flags, direction))

    def test_modes_and_precedence_local_push_pull(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-rltDE'], ['-rltD', '--executability'], ['-aE'], ['-aE', '--no-perms'],
                          ['-rltDE', '-n'], ['-rltDE', '--checksum'], ['-rltDE', '--inplace'],
                          ['-rLtDE'], ['-aAXE', '--no-perms']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction)

    def test_unreadable_replacements_retain_other_permission_bits(self):
        # Native byte copies need no readable basis. Keep the original mode;
        # rsync's receiver can instead apply new-file defaults in this case.
        for direction in ('local', 'push', 'pull'):
            for destination_mode in (0, 0o200):
                with self.subTest(direction=direction, mode=destination_mode):
                    for side in ('src', 'dst'):
                        root = self.root / side
                        if root.exists(): shutil.rmtree(root)
                        root.mkdir(); (root / 'file').write_bytes(b'old' if side == 'dst' else b'new data')
                        (root / 'file').chmod(destination_mode if side == 'dst' else 0o755)
                    self.run_sync(True, ['-rltE'], direction)
                    result = self.root / 'dst/file'
                    self.assertEqual(stat.S_IMODE(result.stat().st_mode), destination_mode)
                    result.chmod(destination_mode | 0o400)
                    self.assertEqual(result.read_bytes(), b'new data')

    def test_hard_link_anchor_and_alias(self):
        for direction in ('local', 'push', 'pull'):
            for flags in (['-rltHE'], ['-aHE'], ['-aHAXE', '--no-perms']):
                results = []
                for native in (False, True):
                    self.fixture(readable=True)
                    for side in ('src', 'dst'):
                        root = self.root / side
                        (root / 'anchor').write_bytes(b'data')
                        (root / 'anchor').chmod(0o744 if side == 'src' else 0o640)
                        os.link(root / 'anchor', root / 'alias')
                        for name in ('anchor', 'alias'): os.utime(root / name, (1500000000, 1500000000))
                    result = self.run_sync(native, flags, direction)
                    self.assertEqual((self.root / 'dst/anchor').stat().st_ino, (self.root / 'dst/alias').stat().st_ino)
                    results.append((snapshot(self.root / 'dst'), sorted(result.stdout.splitlines())))
                self.assertEqual(results[1], results[0], (flags, direction))


if __name__ == '__main__': unittest.main()
