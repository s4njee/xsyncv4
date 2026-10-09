#!/usr/bin/env python3
"""Mixed-version transfers against a frozen, independently built protocol-3 peer."""
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()
HOST = os.environ.get('XSYNC_RIG_HOST')
SSH = ['ssh', '-i', '/keys/id test', '-oBatchMode=yes', '-oStrictHostKeyChecking=no',
       '-oUserKnownHostsFile=/dev/null', '-oLogLevel=ERROR']
RSH = shlex.join(SSH) if HOST else shlex.quote(str(REPO / 'tests/fakessh.sh'))


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync protocols ')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = pathlib.Path(cls.tmp.name)
        old = cls.root / 'legacy source'
        old.mkdir()
        fixture = REPO / 'tests/fixtures/protocol3.tar.gz'
        manifest = json.loads((REPO / 'tests/fixtures/protocol3.json').read_text())
        if hashlib.sha256(fixture.read_bytes()).hexdigest() != manifest['sha256']:
            raise RuntimeError('frozen legacy protocol fixture hash mismatch')
        with tarfile.open(fixture) as archive:
            # Portable to the rig's Python 3.11, which predates tar data filters.
            for member in archive:
                parts = pathlib.PurePosixPath(member.name)
                if parts.is_absolute() or '..' in parts.parts or not (member.isdir() or member.isfile()):
                    raise RuntimeError('invalid member in frozen protocol source archive')
                target = old.joinpath(*parts.parts)
                if member.isdir(): target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
                    target.chmod(member.mode & 0o777)
        cls.legacy = cls.build(old, cls.root / 'legacy build')
        cls.subset = cls.build(REPO, cls.root / 'subset build', '-DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=1')
        cls.old_rsh = RSH
        cls.remote_legacy = str(cls.legacy)
        cls.remote_subset = str(cls.subset)
        if HOST:
            import ssh_test
            ssh_test.SSHTests.setUpClass()
            ssh_test.remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', cls.root)
            for local, name in ((cls.legacy, 'legacy xsync'), (cls.subset, 'subset xsync')):
                target = cls.root / name
                subprocess.run(['rsync', '-a', '-e', RSH, str(local), HOST + ':' + str(target)],
                               check=True, capture_output=True, timeout=20)
                if name.startswith('legacy'): cls.remote_legacy = str(target)
                else: cls.remote_subset = str(target)

    @classmethod
    def build(cls, source, output, *options):
        for args in (['cmake', '-S', str(source), '-B', str(output), '-G', 'Ninja', *options],
                     ['cmake', '--build', str(output), '-j4']):
            result = subprocess.run(args, capture_output=True, timeout=120)
            if result.returncode:
                raise RuntimeError(result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
        return output / 'xsync'

    @classmethod
    def tearDownClass(cls):
        if HOST:
            from ssh_test import remote_code
            remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])', cls.root)
        cls.tmp.cleanup()

    def test_mixed_version_push_pull(self):
        for client, server, label in ((BINARY, self.remote_legacy, 'new-old'),
                                       (self.legacy, '/usr/local/bin/xsync' if HOST else str(BINARY), 'old-new')):
            for direction in ('push', 'pull'):
                with self.subTest(versions=label, direction=direction):
                    root = self.root / (label + direction)
                    source = root / 'source with spaces'
                    source.mkdir(parents=True)
                    (source / 'file').write_bytes(os.urandom(2 * 1024 * 1024))
                    (source / 'link').symlink_to('file')
                    (source / 'outside').symlink_to('../../outside')
                    host = HOST or 'fake'
                    a, b = str(source) + '/', str(root / 'destination') + '/'
                    if HOST:
                        from ssh_test import remote_code
                        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', root)
                        if direction == 'pull':
                            subprocess.run(['rsync', '-a', '-e', RSH, a, host + ':' + a], check=True, capture_output=True)
                    if direction == 'push': b = host + ':' + b
                    else: a = host + ':' + a
                    command = [str(client), '--no-fallback', '-az', '--partial', '--safe-links', '--delete', '-e', RSH,
                               '--rsync-path=' + shlex.quote(server), a, b]
                    for _ in range(2):
                        result = subprocess.run(command, capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertNotIn(b'falling back', result.stderr)
                        self.assertNotIn(b'protocol version mismatch', result.stderr)
                    destination = root / 'destination'
                    code = '''import pathlib,hashlib,sys,json
p=pathlib.Path(sys.argv[1]); print(json.dumps({'hash':hashlib.sha256((p/'file').read_bytes()).hexdigest(),
'link':str((p/'link').readlink()),'outside':(p/'outside').is_symlink()}))
'''
                    if HOST and direction == 'push':
                        from ssh_test import remote_json
                        actual = remote_json(code, destination)
                    else:
                        actual = json.loads(subprocess.check_output(['python3', '-c', code, str(destination)]))
                    self.assertEqual(actual, {'hash': hashlib.sha256((source / 'file').read_bytes()).hexdigest(),
                                              'link': 'file', 'outside': False})

    def test_common_subset_without_compression(self):
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                root = self.root / ('subset-' + direction)
                source = root / 'source'
                source.mkdir(parents=True)
                (source / 'file').write_bytes(b'compressible' * 200000)
                host = HOST or 'fake'
                a, b = str(source) + '/', str(root / 'destination') + '/'
                if HOST:
                    from ssh_test import remote_code
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', root)
                    if direction == 'pull':
                        subprocess.run(['rsync', '-a', '-e', RSH, a, host + ':' + a], check=True, capture_output=True)
                if direction == 'push': b = host + ':' + b
                else: a = host + ':' + a
                result = subprocess.run([str(BINARY), '--no-fallback', '-rz', '-e', RSH,
                                         '--rsync-path=' + shlex.quote(self.remote_subset), a, b],
                                        capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                dest = root / 'destination/file'
                if HOST and direction == 'push':
                    from ssh_test import remote_code
                    actual = remote_code('import pathlib,hashlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())', dest).strip()
                else: actual = hashlib.sha256(dest.read_bytes()).hexdigest()
                self.assertEqual(actual, hashlib.sha256((source / 'file').read_bytes()).hexdigest())

    def test_requested_feature_is_never_silently_dropped(self):
        source = self.root / 'feature source'
        source.write_bytes(b'unchanged')
        for flags in (['-rl', '--safe-links'], ['-a']):
            with self.subTest(flags=flags):
                target = self.root / 'unsupported feature destination'
                result = subprocess.run([str(BINARY), '--no-fallback', *flags, '-e', RSH,
                                         '--rsync-path=' + shlex.quote(self.remote_subset), str(source),
                                         (HOST or 'fake') + ':' + str(target)], capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 4, result.stderr)
                self.assertIn(b'peer does not support', result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                self.assertFalse(target.exists())
                if HOST:
                    from ssh_test import remote_json
                    self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))


if __name__ == '__main__':
    unittest.main()
