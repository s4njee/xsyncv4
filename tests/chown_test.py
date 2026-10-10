#!/usr/bin/env python3
"""Receiver-side owner/group overrides compared with rsync."""
import grp
import os
from pathlib import Path
import pwd
import shlex
import shutil
import subprocess
import tempfile
import unittest

import output_test as transfer
from chmod_test import snapshot as contents
from xattrs_test import DARWIN, RSYNC


def snapshot(root):
    result = contents(root)
    for name, value in list(result.items()):
        st = (root / name).lstat()
        result[name] = value + (st.st_uid, st.st_gid)
    return result


class OwnershipDifferentials(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync-chown-')
        self.root = Path(self.tmp.name)
        self.uid, self.gid = os.getuid(), os.getgid()
        self.user, self.group = pwd.getpwuid(self.uid).pw_name, grp.getgrgid(self.gid).gr_name

    def tearDown(self):
        self.clear_acls(self.root)
        self.tmp.cleanup()

    def clear_acls(self, root):
        if DARWIN and root.exists():
            for p in [root] + list(root.rglob('*')):
                subprocess.run(['chmod', *(['-h'] if p.is_symlink() else []), '-N', str(p)], capture_output=True)

    def fixture(self, metadata=False):
        from acls_test import set_acl
        from xattrs_test import attr_name, set_attr
        for side in ('src', 'dst'):
            root = self.root / side
            if root.exists():
                self.clear_acls(root)
                shutil.rmtree(root)
            (root / 'sub').mkdir(parents=True)
            for name in ('same', 'changed', 'sub/nested', 'anchor'):
                (root / name).write_bytes(b'old' if side == 'dst' and name == 'changed' else b'data')
            os.link(root / 'anchor', root / 'alias')
            (root / 'link').symlink_to('same')
            os.mkfifo(root / 'fifo', 0o640)
            if side == 'src': (root / 'new').write_bytes(b'new')
            for p in [root] + sorted(root.rglob('*')):
                if self.uid == 0:
                    os.chown(p, 60000 if side == 'src' else 60002, 60001 if side == 'src' else 60002,
                             follow_symlinks=False)
                if not p.is_symlink(): p.chmod(0o755 if p.is_dir() else 0o4755 if side == 'src' else 0o640)
                os.utime(p, (1500000000, 1500000000), follow_symlinks=False)
            if metadata:
                for name in ('.', 'same', 'changed', 'sub', 'sub/nested', 'anchor'):
                    set_acl(root / name, 0 if side == 'src' else 1, inherit=name in ('.', 'sub') and not DARWIN)
                    if DARWIN:
                        # Mapping wheel to our own group must retain benign
                        # permissions so both receivers can publish data.
                        subprocess.run(['chmod', '-a', 'group:wheel deny delete', str(root / name)], check=True, capture_output=True)
                        subprocess.run(['chmod', '+a', 'group:wheel allow readattr', str(root / name)], check=True, capture_output=True)
                set_attr(root / 'anchor', attr_name('ownership'), side.encode())

    def command(self, native, flags, direction, clone=False, helper_flags=()):
        command = [str(transfer.BINARY) if native else RSYNC, *flags, '--out-format=%i|%n']
        if native:
            command += ['--no-fallback', '-j8']
            if not clone: command.append('--no-clone')
        source, destination = str(self.root / 'src') + '/', str(self.root / 'dst') + '/'
        if direction != 'local':
            helper = shlex.join([str(transfer.BINARY) if native else RSYNC, *helper_flags])
            command += ['-e', transfer.RSH, '--rsync-path=' + helper]
            if direction == 'push': destination = 'fake:' + destination
            else: source = 'fake:' + source
        return command + [source, destination]

    def check(self, flags, direction, metadata=False, clone=False, helper_flags=()):
        from acls_test import get_acl
        from xattrs_test import get_attrs
        results = []
        for native in (False, True):
            self.fixture(metadata)
            before, source = snapshot(self.root / 'dst'), snapshot(self.root / 'src')
            source_metadata = tuple((get_acl(self.root / 'src' / n), get_attrs(self.root / 'src' / n))
                                    for n in ('.', 'same', 'changed', 'sub', 'sub/nested', 'anchor')) if metadata else None
            result = subprocess.run(self.command(native, flags, direction, clone, helper_flags), capture_output=True,
                                    timeout=30, env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (native, flags, direction, result.stderr))
            after = snapshot(self.root / 'dst')
            self.assertEqual(snapshot(self.root / 'src'), source)
            if metadata:
                self.assertEqual(tuple((get_acl(self.root / 'src' / n), get_attrs(self.root / 'src' / n))
                                       for n in ('.', 'same', 'changed', 'sub', 'sub/nested', 'anchor')), source_metadata)
            if '-n' in flags: self.assertEqual(after, before)
            if any(f.startswith('-') and not f.startswith('--') and 'H' in f for f in flags) and '-n' not in flags:
                self.assertEqual((self.root / 'dst/anchor').stat().st_ino, (self.root / 'dst/alias').stat().st_ino)
            extra = tuple((get_acl(self.root / 'dst' / n), get_attrs(self.root / 'dst' / n))
                          for n in ('.', 'same', 'changed', 'sub', 'sub/nested', 'anchor')) if metadata else None
            results.append((after, extra, sorted(result.stdout.splitlines())))
        self.assertEqual(results[1], results[0])

    def test_numeric_named_omitted_empty_and_repeated_fields(self):
        targets = (str(self.uid), ':' + str(self.gid), f'{self.uid}:{self.gid}', self.user,
                   ':' + self.group, self.user + ':' + self.group, '', ':')
        if self.uid == 0: targets += ('60003', ':60004', '60003:60004')
        for direction in ('local', 'push', 'pull'):
            for target in targets:
                with self.subTest(direction=direction, target=target): self.check(['-a', '--chown=' + target], direction)
            with self.subTest(direction=direction, repeated=True):
                self.check(['-a', '--chown=' + self.user, '--chown=:' + self.group], direction)

    def test_dry_run_inplace_hardlinks_numeric_ids_and_option_order(self):
        target = f'--chown={self.uid}:{self.gid}'
        for direction in ('local', 'push', 'pull'):
            for flags in (['-a', target, '-n'], ['-a', target, '--inplace'], ['-aH', target],
                          ['-a', target, '--numeric-ids'], ['-a', target, '--no-owner'],
                          ['-rltD', target],
                          ['-a', '--chown=' + self.user, '--no-owner', '--chown=']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction)
        if DARWIN:
            self.check(['-a', target], 'local', clone=True)

    def test_group_override_after_no_group(self):
        flags = ['-a', f'--chown={self.uid}:{self.gid}', '--no-group']
        for direction in ('local', 'pull'):
            with self.subTest(direction=direction): self.check(flags, direction)
        # rsync's push can re-enable -g on its receiver while its sender omits
        # group information. It then attempts group 0, which fails for a
        # non-root receiver. The negotiated native layout retains the actual
        # identifiers and applies the requested receiver override.
        for native in (False, True):
            self.fixture()
            source = snapshot(self.root / 'src')
            result = subprocess.run(self.command(native, flags, 'push'), capture_output=True, timeout=20,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0 if native or self.uid == 0 else 23, result.stderr)
            if native:
                state = snapshot(self.root / 'dst')
                self.assertTrue(all(row[-1] == self.gid for row in state.values()))
                self.assertEqual(state['changed'][3], b'data')
                self.assertEqual(state['new'][3], b'new')
            self.assertEqual(snapshot(self.root / 'src'), source)

    def test_acls_xattrs_and_hardlinks(self):
        target = f'--chown={self.uid}:{self.gid}'
        for direction in ('local', 'push', 'pull'):
            for flags in (['-aAX', target], ['-aHAX', target], ['-aAX', target, '-n'],
                          ['-aAX', target, '--chmod=D2755,F4640']):
                with self.subTest(direction=direction, flags=flags): self.check(flags, direction, metadata=True)
        if DARWIN: self.check(['-aHAX', target], 'local', metadata=True, clone=True)

    def test_unknown_receiver_names_warn_without_changing_exit_status(self):
        for direction in ('local', 'push', 'pull'):
            for target in ('xsync_missing_user_60000', ':xsync_missing_group_60000'):
                with self.subTest(direction=direction, target=target):
                    for native in (False, True):
                        self.fixture()
                        result = subprocess.run(self.command(native, ['-a', '--chown=' + target], direction),
                                                capture_output=True, timeout=20,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertIn(b'Unknown --', result.stderr)

    def test_explicit_helpers_with_disjoint_fields(self):
        # A pulling helper sends source identities; only the client resolves
        # incoming overrides. An unknown source-side target must not warn.
        for direction, target, helper in (
            ('push', self.user, ':' + self.group),
            ('push', ':' + self.group, self.user),
            ('pull', ':' + self.group, 'xsync_missing_source_user'),
        ):
            with self.subTest(direction=direction, target=target, helper=helper):
                self.fixture()
                source = snapshot(self.root / 'src')
                result = subprocess.run(self.command(True, ['-a', '--chown=' + target], direction,
                                                     helper_flags=('--chown=' + helper,)),
                                        capture_output=True, timeout=20,
                                        env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(b'Unknown --', result.stderr)
                state = snapshot(self.root / 'dst')
                uid = 60000 if direction == 'pull' and self.uid == 0 else self.uid
                self.assertTrue(all(row[-2:] == (uid, self.gid) for row in state.values()))
                self.assertEqual(state['changed'][3], b'data')
                self.assertEqual(state['new'][3], b'new')
                self.assertEqual(snapshot(self.root / 'src'), source)

    @unittest.skipUnless(DARWIN, 'Darwin ACL publication denial')
    def test_mapped_delete_denial_preserves_existing_data(self):
        for direction in ('local', 'push', 'pull'):
            for native in (False, True):
                with self.subTest(direction=direction, native=native):
                    self.fixture(metadata=True)
                    subprocess.run(['chmod', '+a', 'group:wheel deny delete', str(self.root / 'src/changed')],
                                   check=True, capture_output=True)
                    source = snapshot(self.root / 'src')
                    result = subprocess.run(self.command(native, ['-aAX', f'--chown={self.uid}:{self.gid}'], direction),
                                            capture_output=True, timeout=20,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 23, result.stderr)
                    self.assertIn(b'rename', result.stderr.lower())
                    self.assertEqual((self.root / 'dst/changed').read_bytes(), b'old')
                    self.assertEqual(snapshot(self.root / 'src'), source)

    @unittest.skipIf(DARWIN, 'POSIX duplicate ACL principals')
    def test_colliding_mapped_acl_principals_preserve_order_and_round_trip(self):
        import struct
        records = ((1, 7, 0xffffffff), (2, 7, 60000), (2, 5, 60001), (4, 5, 0xffffffff),
                   (8, 5, 60002), (8, 4, 60003), (16, 5, 0xffffffff), (32, 5, 0xffffffff))
        data = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', *entry) for entry in records)
        for direction in ('local', 'push', 'pull'):
            results = []
            for native in (False, True):
                with self.subTest(direction=direction, native=native):
                    self.fixture(metadata=True)
                    for name in ('same', 'changed'):
                        os.setxattr(self.root / 'src' / name, 'system.posix_acl_access', data)
                    source = snapshot(self.root / 'src')
                    result = subprocess.run(self.command(native, ['-aAX', f'--chown={self.uid}:{self.gid}'], direction),
                                            capture_output=True, timeout=20,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((self.root / 'dst/changed').read_bytes(), b'data')
                    self.assertEqual(snapshot(self.root / 'src'), source)
                    from acls_test import get_acl
                    first = (snapshot(self.root / 'dst'), tuple(get_acl(self.root / 'dst' / n) for n in ('same', 'changed')),
                             sorted(result.stdout.splitlines()))
                    shutil.rmtree(self.root / 'src')
                    (self.root / 'dst').rename(self.root / 'src')
                    (self.root / 'dst').mkdir()
                    result = subprocess.run(self.command(native, ['-aA'], direction), capture_output=True, timeout=20,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    results.append((first, snapshot(self.root / 'dst'),
                                    tuple(get_acl(self.root / 'dst' / n) for n in ('same', 'changed')),
                                    sorted(result.stdout.splitlines())))
            self.assertEqual(results[1], results[0])

    def test_repeated_fields_and_overflow_fail_before_writes(self):
        self.fixture()
        before = snapshot(self.root / 'dst')
        for args in (['--chown=0', '--chown=1'], ['--chown=:0', '--chown=:1'],
                     ['--chown=0:0', '--chown=1:'], ['--chown=4294967296'],
                     ['--chown=:4294967296'], ['--chown=0,1']):
            with self.subTest(args=args):
                result = subprocess.run(self.command(True, ['-a', *args], 'local'), capture_output=True, timeout=10,
                                        env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(snapshot(self.root / 'dst'), before)


if __name__ == '__main__': unittest.main()
