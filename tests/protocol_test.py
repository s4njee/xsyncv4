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
import sys
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
        cls.global_filters = cls.build(REPO, cls.root / 'global filters build', '-DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=4095')
        cls.merge_filters = cls.build(REPO, cls.root / 'merge filters build', '-DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=8191')
        cls.after_filters = cls.build(REPO, cls.root / 'after filters build', '-DCMAKE_CXX_FLAGS=-DXSYNC_PROTOCOL_FEATURES=32767')
        cls.old_rsh = RSH
        cls.remote_legacy = str(cls.legacy)
        cls.remote_subset = str(cls.subset)
        cls.remote_global_filters = str(cls.global_filters)
        cls.remote_merge_filters = str(cls.merge_filters)
        cls.remote_after_filters = str(cls.after_filters)
        if HOST:
            import ssh_test
            ssh_test.SSHTests.setUpClass()
            ssh_test.remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', cls.root)
            for local, name in ((cls.legacy, 'legacy xsync'), (cls.subset, 'subset xsync'),
                                (cls.global_filters, 'global filters xsync'), (cls.merge_filters, 'merge filters xsync'),
                                (cls.after_filters, 'after filters xsync')):
                target = cls.root / name
                subprocess.run(['rsync', '-a', '-e', RSH, str(local), HOST + ':' + str(target)],
                               check=True, capture_output=True, timeout=20)
                if name.startswith('legacy'): cls.remote_legacy = str(target)
                elif name.startswith('subset'): cls.remote_subset = str(target)
                elif name.startswith('global'): cls.remote_global_filters = str(target)
                elif name.startswith('merge'): cls.remote_merge_filters = str(target)
                else: cls.remote_after_filters = str(target)

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
        for flags in (['-rl', '--safe-links'], ['-a'], ['-E'], ['-H'], ['-A'], ['-AX'], ['-U'], ['-UU'], ['--open-noatime'], *([['--fileflags']] if sys.platform == 'darwin' else []), ['--bwlimit=256'], ['--timeout=1'], ['--filter=P stale']):
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

    def test_legacy_metadata_requests_refuse_before_destination_writes(self):
        source = self.root / 'ACL feature source'; source.mkdir()
        (source / 'file').write_bytes(b'unchanged')
        for flags in ('-rltE', '-aA', '-aAX', '-aU', '-aUU', *(['--fileflags', '-aN', '-aUN'] if sys.platform == 'darwin' else [])):
            for direction in ('push', 'pull'):
                with self.subTest(flags=flags, direction=direction):
                    target = self.root / ('ACL refused ' + flags + direction)
                    a, b = str(source) + '/', str(target)
                    if HOST:
                        from ssh_test import remote_code
                        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(exist_ok=True); (p/"file").write_bytes(b"unchanged")', source)
                    if direction == 'push': b = (HOST or 'fake') + ':' + b
                    else: a = (HOST or 'fake') + ':' + a
                    result = subprocess.run([str(BINARY), '--no-fallback', flags, '-e', RSH,
                                             '--rsync-path=' + shlex.quote(self.remote_legacy), a, b], capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(b'peer does not support', result.stderr)
                    self.assertFalse(target.exists())
                    if HOST:
                        from ssh_test import remote_json
                        self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_executability_with_perms_needs_no_extra_capability(self):
        source = self.root / 'redundant executability'; source.mkdir()
        (source / 'file').write_bytes(b'data'); (source / 'file').chmod(0o751)
        for peer in (self.remote_subset, self.remote_legacy):
            for direction in ('push', 'pull'):
                target = self.root / ('perms E ' + pathlib.Path(peer).parent.name + direction)
                if HOST and direction == 'pull':
                    subprocess.run(['rsync', '-a', '-e', RSH, str(source) + '/', HOST + ':' + str(source) + '/'],
                                   check=True, capture_output=True, timeout=20)
                a, b = str(source) + '/', str(target) + '/'
                if direction == 'push': b = (HOST or 'fake') + ':' + b
                else: a = (HOST or 'fake') + ':' + a
                result = subprocess.run([str(BINARY), '--no-fallback', '-rpE', '-e', RSH,
                                         '--rsync-path=' + shlex.quote(peer), a, b], capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                if HOST and direction == 'push':
                    from ssh_test import remote_json
                    mode = remote_json('import os,sys,json; print(json.dumps(os.stat(sys.argv[1]).st_mode & 4095))', target / 'file')
                else: mode = (target / 'file').stat().st_mode & 0o7777
                self.assertEqual(mode, 0o751)

    def test_chmod_uses_existing_mode_fields_with_frozen_and_subset_peers(self):
        source = self.root / 'permission overrides'; source.mkdir()
        (source / 'file').write_bytes(b'data'); (source / 'file').chmod(0o751)
        for peer in (self.remote_subset, self.remote_legacy):
            for direction in ('push', 'pull'):
                target = self.root / ('chmod ' + pathlib.Path(peer).parent.name + direction)
                if HOST and direction == 'pull':
                    subprocess.run(['rsync', '-a', '-e', RSH, str(source) + '/', HOST + ':' + str(source) + '/'],
                                   check=True, capture_output=True, timeout=20)
                a, b = str(source) + '/', str(target) + '/'
                if direction == 'push': b = (HOST or 'fake') + ':' + b
                else: a = (HOST or 'fake') + ':' + a
                result = subprocess.run([str(BINARY), '--no-fallback', '-rp', '--chmod=F640', '-e', RSH,
                                         '--rsync-path=' + shlex.quote(peer), a, b], capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                if HOST and direction == 'push':
                    from ssh_test import remote_json
                    mode = remote_json('import os,sys,json; print(json.dumps(os.stat(sys.argv[1]).st_mode & 4095))', target / 'file')
                else: mode = (target / 'file').stat().st_mode & 0o7777
                self.assertEqual(mode, 0o640)

    def test_chown_requires_capability_but_empty_fields_remain_compatible(self):
        source = self.root / 'ownership overrides'; source.mkdir()
        (source / 'file').write_bytes(b'data')
        for peer in (self.remote_subset, self.remote_legacy):
            for direction in ('push', 'pull'):
                for requested in (True, False):
                    with self.subTest(peer=peer, direction=direction, requested=requested):
                        target = self.root / ('chown ' + pathlib.Path(peer).parent.name + direction + str(requested))
                        if HOST and direction == 'pull':
                            subprocess.run(['rsync', '-a', '-e', RSH, str(source) + '/', HOST + ':' + str(source) + '/'],
                                           check=True, capture_output=True, timeout=20)
                        a, b = str(source) + '/', str(target) + '/'
                        if direction == 'push': b = (HOST or 'fake') + ':' + b
                        else: a = (HOST or 'fake') + ':' + a
                        result = subprocess.run([str(BINARY), '--no-fallback', '-r', '--numeric-ids',
                                                 '--chown=' + (f'{os.getuid()}:{os.getgid()}' if requested else ':'),
                                                 '-e', RSH, '--rsync-path=' + shlex.quote(peer), a, b],
                                                capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, 4 if requested else 0, result.stderr)
                        if requested:
                            self.assertIn(b'peer does not support --chown', result.stderr)
                            self.assertFalse(target.exists())
                        elif not HOST or direction == 'pull':
                            self.assertEqual((target / 'file').read_bytes(), b'data')

    def test_formatted_output_requires_negotiated_support(self):
        source = self.root / 'format source'
        source.write_bytes(b'unchanged')
        for peer in (self.remote_subset, self.remote_legacy):
            for direction in ('push', 'pull'):
                for option in ('--out-format=%n', '--log-file=' + str(self.root / 'unopened log'), '-H', '--bwlimit=256', '--timeout=1', '--filter=H hidden'):
                    with self.subTest(peer=peer, direction=direction, option=option):
                        target = self.root / 'uncreated format destination'
                        a, b = str(source), str(target)
                        if HOST and direction == 'pull':
                            subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                        if direction == 'push': b = (HOST or 'fake') + ':' + b
                        else: a = (HOST or 'fake') + ':' + a
                        result = subprocess.run([str(BINARY), '--no-fallback', option, '-e', RSH,
                                                 '--rsync-path=' + shlex.quote(peer), a, b],
                                                capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, 4, result.stderr)
                        expected = b'peer does not support extended filters' if option.startswith('--filter') else \
                                   b'peer does not support bandwidth limits and idle timeouts' if option.startswith(('--bwlimit', '--timeout')) else \
                                   b'peer does not support hard-link preservation' if option == '-H' else b'peer does not support structured file output'
                        self.assertIn(expected, result.stderr)
                        self.assertFalse(target.exists())
                        self.assertFalse((self.root / 'unopened log').exists())
                        if HOST:
                            from ssh_test import remote_json
                            self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_merge_filters_require_their_own_capability(self):
        source = self.root / 'merge source'
        source.mkdir()
        (source / 'file').write_bytes(b'unchanged')
        for direction in ('push', 'pull'):
            for flags in (['--filter=: .rules'], ['-F']):
                with self.subTest(direction=direction, flags=flags):
                    target = self.root / 'uncreated merge destination'
                    a, b = str(source) + '/', str(target) + '/'
                    if HOST and direction == 'pull':
                        subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                    if direction == 'push': b = (HOST or 'fake') + ':' + b
                    else: a = (HOST or 'fake') + ':' + a
                    result = subprocess.run([str(BINARY), '--no-fallback', '-r', *flags, '-e', RSH,
                                             '--rsync-path=' + shlex.quote(self.remote_global_filters), a, b],
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(b'peer does not support per-directory filters', result.stderr)
                    self.assertNotIn(b'falling back', result.stderr)
                    self.assertFalse(target.exists())
                    if HOST:
                        from ssh_test import remote_json
                        self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_cvs_filters_require_their_own_capability(self):
        source = self.root / 'cvs source'
        source.mkdir()
        (source / 'file').write_bytes(b'unchanged')
        for direction in ('push', 'pull'):
            for flags in (['--filter=-C'], ['-C'], ['--filter=: .rules']):
                with self.subTest(direction=direction, flags=flags):
                    target = self.root / 'uncreated cvs destination'
                    a, b = str(source) + '/', str(target) + '/'
                    if HOST and direction == 'pull':
                        subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                    if direction == 'push': b = (HOST or 'fake') + ':' + b
                    else: a = (HOST or 'fake') + ':' + a
                    result = subprocess.run([str(BINARY), '--no-fallback', '-r', *flags, '-e', RSH,
                                             '--rsync-path=' + shlex.quote(self.remote_merge_filters), a, b],
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(b'peer does not support global CVS filters', result.stderr)
                    self.assertNotIn(b'falling back', result.stderr)
                    self.assertFalse(target.exists())
                    self.assertEqual((source / 'file').read_bytes(), b'unchanged')
                    if HOST:
                        from ssh_test import remote_json
                        self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_delete_after_requires_its_own_capability(self):
        source = self.root / 'after source'
        source.mkdir()
        (source / 'file').write_bytes(b'unchanged')
        for direction in ('push', 'pull'):
            for filters in ([], ['--filter=P stale.*']):
                with self.subTest(direction=direction, filters=filters):
                    target = self.root / 'uncreated after destination'
                    a, b = str(source) + '/', str(target) + '/'
                    if HOST and direction == 'pull':
                        subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                    if direction == 'push': b = (HOST or 'fake') + ':' + b
                    else: a = (HOST or 'fake') + ':' + a
                    result = subprocess.run([str(BINARY), '--no-fallback', '-r', '--delete-after', *filters,
                                             '-e', RSH, '--rsync-path=' + shlex.quote(self.remote_merge_filters), a, b],
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(b'peer does not support --delete-after', result.stderr)
                    self.assertFalse(target.exists())
                    self.assertEqual((source / 'file').read_bytes(), b'unchanged')
                    if HOST:
                        from ssh_test import remote_json
                        self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_prune_empty_requires_its_own_capability(self):
        source = self.root / 'prune source'
        source.mkdir()
        (source / 'file').write_bytes(b'unchanged')
        for direction in ('push', 'pull', 'listing'):
            for filters in ([], ['--filter=P stale.*']):
                with self.subTest(direction=direction, filters=filters):
                    target = self.root / 'uncreated prune destination'
                    a, b = str(source) + '/', str(target) + '/'
                    if HOST and direction != 'push':
                        subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                    if direction == 'push': b = (HOST or 'fake') + ':' + b
                    else: a = (HOST or 'fake') + ':' + a
                    result = subprocess.run([str(BINARY), '--no-fallback', '-rm', *filters,
                                             '-e', RSH, '--rsync-path=' + shlex.quote(self.remote_after_filters),
                                             *([a] if direction == 'listing' else [a, b])],
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 4, result.stderr)
                    self.assertIn(b'peer does not support --prune-empty-dirs', result.stderr)
                    self.assertFalse(target.exists())
                    self.assertEqual((source / 'file').read_bytes(), b'unchanged')
                    if HOST:
                        from ssh_test import remote_json
                        self.assertFalse(remote_json('import pathlib,json,sys; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', target))

    def test_basic_single_merge_works_with_legacy_helper(self):
        source = self.root / 'single merge source'
        source.mkdir()
        (source / 'file').write_bytes(b'transferred')
        (source / 'hidden').write_bytes(b'excluded')
        rules = self.root / 'client-only.rules'
        rules.write_text('- hidden\n')
        for direction in ('push', 'pull'):
            with self.subTest(direction=direction):
                target = self.root / ('single merge destination ' + direction)
                a, b = str(source) + '/', str(target) + '/'
                if HOST and direction == 'pull':
                    subprocess.run(['rsync', '-a', '-e', RSH, a, HOST + ':' + a], check=True, capture_output=True)
                if direction == 'push': b = (HOST or 'fake') + ':' + b
                else: a = (HOST or 'fake') + ':' + a
                result = subprocess.run([str(BINARY), '--no-fallback', '-r', '--filter=. ' + str(rules),
                                         '-e', RSH, '--rsync-path=' + shlex.quote(self.remote_legacy), a, b],
                                        capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(b'falling back', result.stderr)
                if HOST and direction == 'push':
                    from ssh_test import remote_json
                    files = remote_json('import pathlib,json,sys; print(json.dumps({p.name:p.read_text() for p in pathlib.Path(sys.argv[1]).iterdir()}))', target)
                else: files = {p.name:p.read_text() for p in target.iterdir()}
                self.assertEqual(files, {'file': 'transferred'})


if __name__ == '__main__':
    unittest.main()
