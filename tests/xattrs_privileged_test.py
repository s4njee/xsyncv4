#!/usr/bin/env python3
"""Linux root namespace parity; run in an isolated SYS_ADMIN-capable test rig."""
import os
import shlex
import shutil
import subprocess
import tempfile
import socket
import stat
import struct
import sys
import unittest

import xattrs_test as attrs


@unittest.skipUnless(sys.platform.startswith('linux') and os.geteuid() == 0, 'Linux root namespaces')
class PrivilegedXattrDifferentials(attrs.XattrDifferentials):
    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile() as probe:
            try: os.setxattr(probe.name, 'trusted.xsync-probe', b'probe')
            except OSError as error: raise unittest.SkipTest('trusted namespace unavailable: ' + str(error))

    def fixture(self, ownership=None, **kwargs):
        super().fixture(**kwargs)
        for side in ('src', 'dst'):
            root = self.root / side
            os.mknod(root / 'character', stat.S_IFCHR | 0o600, os.makedev(1, 3))
            os.mknod(root / 'block', stat.S_IFBLK | 0o600, os.makedev(7, 0))
            with socket.socket(socket.AF_UNIX) as sock: sock.bind(str(root / 'socket'))
            if side == 'src':
                os.mkfifo(root / 'new-pipe')
                (root / 'new-link').symlink_to('same')
                os.mknod(root / 'new-character', stat.S_IFCHR | 0o600, os.makedev(1, 3))
                os.mknod(root / 'new-block', stat.S_IFBLK | 0o600, os.makedev(7, 0))
                with socket.socket(socket.AF_UNIX) as sock: sock.bind(str(root / 'new-socket'))
            for name in ('', 'sub', 'same', 'changed', 'new', 'big', 'link', 'pipe', 'character', 'block', 'socket', 'new-pipe', 'new-link', 'new-character', 'new-block', 'new-socket'):
                path = root / name
                if not path.exists() and not path.is_symlink(): continue
                value = (b'link-' if path.is_symlink() else b'inode-') + (b'\0\xffsource' if side == 'src' else b'old')
                os.setxattr(path, 'trusted.xsync-value', value, follow_symlinks=False)
                if side == 'dst': os.setxattr(path, 'trusted.xsync-stale', b'remove', follow_symlinks=False)
                os.utime(path, ns=(1500000000000000000, 1500000000000000000), follow_symlinks=False)
            for name in ('same', 'changed', 'new', 'big'):
                path = root / name
                if not path.exists(): continue
                if side == 'src' and ownership:
                    os.chown(path, 60000 if ownership in ('owner', 'both') else 0,
                             60000 if ownership in ('group', 'both') else 0)
                # The same bytes on both sides expose ownership-only cap loss.
                os.setxattr(path, 'security.capability', struct.pack('<IIIII', 0x02000001, 1 << 10, 0, 0, 0))
        if ownership:
            source, target = self.root / 'src/same', self.root / 'dst/same'
            for name in os.listxattr(target): os.removexattr(target, name)
            for name in os.listxattr(source): os.setxattr(target, name, os.getxattr(source, name))
        return attrs.snapshot(self.root)

    # Explicit cases avoid replaying inherited broad suites with this fixture.
    test_clone = test_local = test_namespace_aliases = test_filters = test_merges = None
    test_hardlinks_relative_and_destination_links = None
    test_resource_forks_preserve_mtimes = test_large_resource_forks = None
    test_readonly_files = test_attribute_only_updates_and_idempotence = None

    def test_privileged_types_and_filters(self):
        for direction in ('local', 'push', 'pull'):
            for flags, rules in (
                (['-aX'], ()), (['-aXX'], ()), (['-aXn'], ()), (['-aXL'], ()),
                (['-aX'], ('-x trusted.xsync-value',)),
                (['-aX'], ('+x trusted.*', '-x *')),
                (['-aX'], ('-x security.capability',)),
                (['-aX', '--inplace'], ()),
                (['-aX', '--no-atomic'], ()),
            ):
                with self.subTest(direction=direction, flags=flags, rules=rules):
                    self.check_case(flags, rules=rules, direction=direction)

    def test_ownership_restores_capabilities(self):
        for direction in ('local', 'push', 'pull'):
            for ownership in ('owner', 'group', 'both'):
                for flags, rules in (
                    (['-aX', '--numeric-ids'], ()), (['-aXn', '--numeric-ids'], ()),
                    (['-aX', '--numeric-ids', '--inplace'], ()),
                    (['-aX', '--numeric-ids'], ('-x security.capability',)),
                ):
                    with self.subTest(direction=direction, ownership=ownership, flags=flags, rules=rules):
                        self.check_case(flags, rules=rules, direction=direction, ownership=ownership)


@unittest.skipUnless(sys.platform.startswith('linux') and os.geteuid() == 0, 'Linux mixed privilege namespaces')
class PrivilegedRoleTests(unittest.TestCase):
    setUpClass = classmethod(PrivilegedXattrDifferentials.setUpClass.__func__)

    def test_root_and_unprivileged_sender_receiver_filters(self):
        for direction in ('push', 'pull'):
            for user_client in (False, True):
                for flags, rules in (
                    (['-aX'], ()), (['-aXX'], ()),
                    (['-aX'], ('+x *',)), (['-aX', '--delete'], ('+x *',)),
                    (['-aX'], ('-x security.capability',)),
                    (['-aX', '--delete'], ('-x security.capability',)),
                ):
                    with self.subTest(direction=direction, user_client=user_client, flags=flags, rules=rules), tempfile.TemporaryDirectory() as tmp:
                        root = attrs.Path(tmp); root.chmod(0o755)
                        results = []
                        for native in (False, True):
                            for side in ('src', 'dst'):
                                path = root / side
                                if path.exists(): shutil.rmtree(path)
                                path.mkdir(); os.chown(path, 60000, 60000)
                                f = path / 'file'; f.write_bytes(b'same'); os.chown(f, 60000, 60000)
                                (path / 'link').symlink_to('file'); os.chown(path / 'link', 60000, 60000, follow_symlinks=False)
                                os.setxattr(f, 'user.value', b'source' if side == 'src' else b'old')
                                os.setxattr(f, 'trusted.value', b'source' if side == 'src' else b'old')
                                os.setxattr(path / 'link', 'trusted.link', side.encode(), follow_symlinks=False)
                                os.setxattr(f, 'security.capability', struct.pack('<IIIII', 0x02000001, 1 << 10, 0, 0, 0))
                                if side == 'dst': os.setxattr(f, 'user.rsync.security.capability', b'old alias')
                                for leaf in (f, path / 'link', path):
                                    os.utime(leaf, ns=(1500000000000000000, 1500000000000000000), follow_symlinks=False)
                            before = attrs.snapshot(root / 'src')
                            binary = str(attrs.transfer.BINARY) if native else attrs.RSYNC
                            privilege = ['setpriv', '--reuid=60000', '--regid=60000', '--clear-groups']
                            command = (privilege if user_client else []) + [binary, '-i', '--out-format=%i|%n', *flags]
                            if native: command += ['--no-fallback', '--no-clone']
                            server = shlex.join(([] if user_client else privilege) + [binary])
                            command += ['-e', shlex.quote(str(attrs.transfer.REPO / 'tests/fakessh.sh')), '--rsync-path=' + server]
                            command += ['--filter=' + rule for rule in rules]
                            src, dst = str(root / 'src') + '/', str(root / 'dst') + '/'
                            if direction == 'push': dst = 'fake:' + dst
                            else: src = 'fake:' + src
                            result = subprocess.run(command + [src, dst], capture_output=True, timeout=30,
                                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                            if not native:
                                reference_status = result.returncode
                                self.assertIn(reference_status, (0, 23), (command, result.stderr))
                            else: self.assertEqual(result.returncode, reference_status, (command, result.stderr))
                            self.assertEqual(attrs.snapshot(root / 'src'), before)
                            results.append((attrs.snapshot(root / 'dst'), sorted(result.stdout.splitlines())))
                        self.assertEqual(results[1], results[0])


if __name__ == '__main__': unittest.main()
