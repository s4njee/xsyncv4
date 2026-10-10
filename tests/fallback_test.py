#!/usr/bin/env python3
"""Fallback eligibility, exact argv preservation, and actual rsync transfers."""
import json
import os
import pathlib
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xs')).resolve()
SELF_BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_EXECUTABLE', BINARY)).resolve()


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync fallback ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.src = self.root / 'source'
        self.src.mkdir()
        (self.src / 'file with spaces').write_bytes(b'fallback data' * 30000)
        (self.src / 'hard link').hardlink_to(self.src / 'file with spaces')
        self.env = dict(os.environ)
        self.env.pop('XSYNC_FALLBACK', None)

    def run_sync(self, *args, env=None, mask=0o022):
        return subprocess.run([str(BINARY), *map(str, args)], env=env or self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
                              preexec_fn=lambda: os.umask(mask))

    def fake_rsync(self, code=19):
        directory = self.root / 'commands with spaces'
        directory.mkdir()
        script = directory / 'rsync'
        script.write_text('#!' + sys.executable + '\nimport os,sys,json\n'
                          'print(json.dumps({"args":sys.argv[1:],"umask":os.umask(0)}))\n'
                          f'sys.exit({code})\n')
        script.chmod(0o755)
        self.env['PATH'] = str(directory)
        return directory

    def fake_shell(self):
        script = self.root / 'remote shell.py'
        script.write_text('''import os,sys,struct
if sys.argv[-1] != '--server':
 os.execv(sys.argv[1],sys.argv[1:])
header=sys.stdin.buffer.read(5)
if len(header)==5: sys.stdin.buffer.read(struct.unpack('<IB',header)[0])
case=os.environ['XSYNC_TEST_PEER']
def frame(kind,payload):
 sys.stdout.buffer.write(struct.pack('<IB',len(payload),kind)+payload); sys.stdout.buffer.flush()
if case=='missing': sys.exit(127)
elif case=='mismatch': frame(1,b'XSYNC\\x01\\x00')
elif case=='fatal_mismatch': frame(8,b'\\x02\\x02protocol version mismatch: test peer')
elif case=='banner': print('welcome to a broken shell',flush=True)
elif case in ('disconnect','capability','xattr_legacy','darwin_acl_legacy'):
 import re,pathlib
 version=int(re.search(r'PROTO_VERSION = (\\d+)',pathlib.Path(sys.argv[2]).read_text())[1])
 features = 262159 if case=='xattr_legacy' else 2097167 if case=='darwin_acl_legacy' else 15
 def var(value):
  result=bytearray()
  while value>=128: result.append((value&127)|128); value>>=7
  return bytes(result)+bytes([value])
 frame(1,b'XSYNC\\x01'+bytes([version])+(var(features) if version>=4 else b''))
else: sys.exit(255)
''')
        # The fake rsync branch drops the Python fixture arguments before invoking
        # the existing shell simulator, exactly as a real sshd handles its command.
        text = script.read_text().replace('os.execv(sys.argv[1],sys.argv[1:])',
                                         'os.execv(sys.argv[1],[sys.argv[1],*sys.argv[3:]])')
        script.write_text(text)
        return shlex.join([sys.executable, str(script), str(REPO / 'tests/fakessh.sh'), str(REPO / 'src/common.h')])

    def test_original_arguments_and_extensions(self):
        self.fake_rsync()
        original = ['-abX', '-e', 'ssh -i "a key"', '--out-format=%i %n',
                    '--rsync-path=custom wrapper', 'source with spaces/', 'user@host:dest with spaces/']
        result = self.run_sync('--no-clone', '-j8', '--atomic', *original, mask=0o077)
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'args': original, 'umask': 0o077})
        self.assertEqual(result.stderr.count(b'falling back to rsync:'), 1)
        self.assertEqual(len(result.stderr.splitlines()), 1)
        result = self.run_sync('-avj', '3', '-b', 'a', 'b')
        self.assertEqual(json.loads(result.stdout)['args'], ['-av', '-b', 'a', 'b'])

    def test_strict_switches_and_invalid_options(self):
        self.fake_rsync()
        for flags, env in ((['-b', '--no-fallback'], self.env),
                           (['--no-fallback', '-b'], self.env),
                           (['-b'], dict(self.env, XSYNC_FALLBACK='0')),
                           (['-b', '--server'], self.env),
                           (['--not-a-real-option'], self.env),
                           (['-f', 'invalid rule'], self.env),
                           (['--max-delete=invalid'], self.env)):
            with self.subTest(flags=flags):
                result = self.run_sync(*flags, self.src, self.root / 'dest', env=env)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                self.assertEqual(result.stdout, b'')
                self.assertFalse((self.root / 'dest').exists())
        result = self.run_sync('-b', '--fallback', 'src', 'dst', env=dict(self.env, XSYNC_FALLBACK='0'))
        self.assertEqual(result.returncode, 19)
        # A value resembling a control flag is still an option value.
        result = self.run_sync('-b', '-e', '--no-fallback', 'src', 'dst')
        self.assertEqual(json.loads(result.stdout)['args'], ['-b', '-e', '--no-fallback', 'src', 'dst'])
        result = self.run_sync('-b', '--', '--no-fallback', 'dst')
        self.assertEqual(json.loads(result.stdout)['args'], ['-b', '--', '--no-fallback', 'dst'])

    def test_native_hardlinks_and_umask(self):
        dest = self.root / 'destination'
        result = self.run_sync('--no-fallback', '-aH', str(self.src) + '/', dest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((dest / 'file with spaces').read_bytes(), (self.src / 'file with spaces').read_bytes())
        self.assertEqual((dest / 'hard link').stat().st_ino, (dest / 'file with spaces').stat().st_ino)
        dest = self.root / 'mask destination'
        result = self.run_sync('--no-fallback', '-rH', str(self.src) + '/', dest, mask=0o077)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE((dest / 'file with spaces').stat().st_mode), 0o600)

    def test_daemon_arguments_and_filters(self):
        self.fake_rsync()
        for args in (['-a', 'rsync://host/module', 'dst'], ['-a', 'src', 'host::module'],
                     ['-ab', '-f', 'P keep', 'src', 'dst'], ['-ab', '-F', 'src', 'dst']):
            with self.subTest(args=args):
                result = self.run_sync(*args)
                self.assertEqual(result.returncode, 19, result.stderr)
                self.assertEqual(json.loads(result.stdout)['args'], args)

    def test_no_recursive_alias_and_missing_rsync(self):
        directory = self.root / 'bin'
        directory.mkdir()
        (directory / 'rsync').symlink_to(SELF_BINARY)
        self.env['PATH'] = str(directory)
        result = self.run_sync('-b', 'src', 'dst')
        self.assertEqual(result.returncode, 127)
        self.assertIn(b'no real rsync', result.stderr)
        (directory / 'rsync').unlink()
        result = self.run_sync('-b', 'src', 'dst')
        self.assertEqual(result.returncode, 127)

    def test_remote_metadata_refuse_or_delegate_before_writes(self):
        from acls_test import get_acl, set_acl
        source = self.src / 'file with spaces'
        set_acl(source)
        before = get_acl(source)
        for direction in ('push', 'pull'):
            for flags in ('-aA', '-aAX', '-rltE'):
                with self.subTest(direction=direction, flags=flags):
                    dest = self.root / (direction + flags)
                    a, b = str(self.src) + '/', str(dest)
                    a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                    environment = dict(self.env, XSYNC_TEST_PEER='capability')
                    arguments = [flags, '-e', self.fake_shell(), a, b]
                    result = self.run_sync('--no-fallback', *arguments, env=environment)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertFalse(dest.exists())
                    # Use rsync as the explicit fallback peer; the client's
                    # native negotiation fails before it sends any directory.
                    fallback_arguments = [flags, '-e', self.fake_shell(), a, b]
                    result = self.run_sync(*fallback_arguments, env=environment)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr.count(b'falling back'), 1)
                    if 'A' in flags: self.assertEqual(get_acl(dest / source.name), before)
                    else: self.assertEqual((dest / source.name).stat().st_mode & 0o7777, source.stat().st_mode & 0o777 & ~0o022)
                    self.assertEqual(get_acl(source), before)

    def test_remote_link_dest_refuses_or_delegates_before_writes(self):
        import shutil
        basis = self.root / 'previous snapshot'
        shutil.copytree(self.src, basis)
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                dest = self.root / ('snapshot-' + direction)
                a, b = str(self.src) + '/', str(dest)
                a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                environment = dict(self.env, XSYNC_TEST_PEER='capability')
                arguments = ['-a', '--link-dest=' + str(basis), '-e', self.fake_shell(), a, b]
                result = self.run_sync('--no-fallback', *arguments, env=environment)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertFalse(dest.exists())
                result = self.run_sync(*arguments, env=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr.count(b'falling back'), 1)
                self.assertEqual((dest / 'file with spaces').stat().st_ino, (basis / 'file with spaces').stat().st_ino)

    def test_remote_sparse_refuses_or_delegates_before_writes(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                dest = self.root / ('sparse-' + direction)
                a, b = str(self.src) + '/', str(dest)
                a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                environment = dict(self.env, XSYNC_TEST_PEER='capability')
                arguments = ['-aS', '-e', self.fake_shell(), a, b]
                result = self.run_sync('--no-fallback', *arguments, env=environment)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertFalse(dest.exists())
                result = self.run_sync(*arguments, env=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr.count(b'falling back'), 1)
                self.assertEqual((dest / 'file with spaces').read_bytes(), (self.src / 'file with spaces').read_bytes())

    def test_remote_chown_refuses_or_delegates_before_writes(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                dest = self.root / ('chown-' + direction)
                a, b = str(self.src) + '/', str(dest)
                a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                environment = dict(self.env, XSYNC_TEST_PEER='capability')
                arguments = ['-a', f'--chown={os.getuid()}:{os.getgid()}', '-e', self.fake_shell(), a, b]
                result = self.run_sync('--no-fallback', *arguments, env=environment)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertFalse(dest.exists())
                result = self.run_sync(*arguments, env=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr.count(b'falling back'), 1)
                self.assertEqual((dest / 'file with spaces').read_bytes(), (self.src / 'file with spaces').read_bytes())

    def test_explicit_server_acl_option_refuses_before_writes(self):
        import wire_test as wire
        target = self.root / 'server ACL destination'
        options = bytes(name == 'recursive' for name in wire.BOOLS)
        options += b''.join(wire.var(2 if name == 'jobs' else 0) for name in wire.INTS)
        hello = b'XSYNC\1' + wire.var(wire.VERSION) + b'R' + wire.var(15) + options + b'\0\1' + wire.string(str(target))
        for flag in ('-A', '--acls'):
            with self.subTest(flag=flag):
                proc = subprocess.Popen([str(BINARY), '--server', flag], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
                try:
                    proc.stdin.write(wire.frame(1, hello)); proc.stdin.flush()
                    kind, message = wire.read_frame(proc)
                    self.assertEqual(kind, 8)
                    self.assertEqual(message[:2], b'\2\4')
                    self.assertIn(b'peer does not support the required ACL style', message)
                    proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 4)
                    self.assertFalse(target.exists())
                finally:
                    if proc.poll() is None: proc.kill()
                    proc.communicate()

    def test_remote_xattrs_capability_guard(self):
        from xattrs_test import attr_name, get_attrs, set_attr
        source = self.src / 'file with spaces'
        set_attr(source, attr_name('fallback-binary'), b'\0\xff\r\n')
        before = get_attrs(source)
        rsh = self.fake_shell()
        for direction, peer in ((direction, peer) for direction in ('push', 'pull') for peer in ('capability', 'xattr_legacy')):
            for flags in ('-aX', '-aXX'):
                with self.subTest(direction=direction, flags=flags, peer=peer):
                    dest = self.root / (direction + peer + flags)
                    a, b = str(self.src) + '/', str(dest)
                    a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                    environment = dict(self.env, XSYNC_TEST_PEER=peer)
                    result = self.run_sync('--no-fallback', flags, '-e', rsh, a, b, env=environment)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertFalse(dest.exists())
                    self.assertEqual(get_attrs(source), before)
                    result = self.run_sync(flags, '-e', rsh, a, b, env=environment)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr.count(b'falling back'), 1)
                    self.assertEqual(get_attrs(dest / source.name), before)
                    self.assertEqual(get_attrs(source), before)

    @unittest.skipUnless(sys.platform == 'darwin', 'Darwin UUID capability')
    def test_darwin_acl_peer_without_uuid_support(self):
        from acls_test import get_acl, set_acl
        source = self.src / 'file with spaces'
        set_acl(source)
        before = get_acl(source)
        rsh = self.fake_shell()
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                dest = self.root / ('ACL UUID legacy ' + direction)
                a, b = str(source), str(dest)
                a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                environment = dict(self.env, XSYNC_TEST_PEER='darwin_acl_legacy')
                result = self.run_sync('--no-fallback', '-rA', '-e', rsh, a, b, env=environment)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn(b'peer does not support unresolved ACL UUID principals', result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                self.assertFalse(dest.exists())
                self.assertEqual(get_acl(source), before)
                result = self.run_sync('-rA', '-e', rsh, a, b, env=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr.count(b'falling back'), 1)
                self.assertEqual(dest.read_bytes(), source.read_bytes())
                self.assertEqual(get_acl(dest), before)
                self.assertEqual(get_acl(source), before)

    def test_remote_handshake_fallback_and_strict_failures(self):
        rsh = self.fake_shell()
        for case in ('missing', 'mismatch', 'fatal_mismatch'):
            for direction in ('push', 'pull'):
                with self.subTest(case=case, direction=direction):
                    dest = self.root / (case + direction)
                    a, b = str(self.src) + '/', str(dest)
                    a, b = (a, 'fake:' + b) if direction == 'push' else ('fake:' + a, b)
                    result = self.run_sync('-a', '-e', rsh, a, b, env=dict(self.env, XSYNC_TEST_PEER=case))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((dest / 'file with spaces').read_bytes(), (self.src / 'file with spaces').read_bytes())
                    self.assertEqual(result.stderr.count(b'falling back'), 1)
        for case, code in (('missing', 127), ('mismatch', 2), ('fatal_mismatch', 2),
                           ('banner', 2), ('disconnect', 12), ('auth', 255)):
            with self.subTest(strict=case):
                flags = [] if case in ('banner', 'disconnect', 'auth') else ['--no-fallback']
                dest = self.root / ('strict-' + case)
                result = self.run_sync(*flags, '-a', '-e', rsh, self.src, 'fake:' + str(dest),
                                       env=dict(self.env, XSYNC_TEST_PEER=case))
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                self.assertFalse(dest.exists())


if __name__ == '__main__':
    unittest.main()
