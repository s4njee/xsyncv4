#!/usr/bin/env python3
"""List-only output against rsync: local, native remote, filters and no writes."""
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from output_test import BINARY, HOST, RSH
from ssh_test import remote_code, remote_json

REPO = pathlib.Path(__file__).resolve().parent.parent
REFERENCE = '/opt/homebrew/bin/rsync' if pathlib.Path('/opt/homebrew/bin/rsync').exists() else shutil.which('rsync')
ENV = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', TZ='UTC', LC_ALL='C.UTF-8')
FIXTURE = r'''import pathlib,sys,os,socket
root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True,exist_ok=True)
source=root/'source'; source.mkdir(); (source/'a-dir').mkdir(); (source/'sub dir').mkdir()
(source/'a-dir'/'deep').mkdir(); (source/'a-dir'/'deep'/'nested').write_text('nested')
(source/'a-dir'/'z').write_text('child'); (source/'sub dir'/'x').write_text('other child')
(source/'a').write_bytes(b'hello'); (source/'big').write_bytes(b'x'*2012345)
(source/'unicode strasse ß').write_text('unicode'); (source/'newline\nname').write_text('escaped')
(source/'tab\tname').write_text('tab'); (source/'octal\\#012').write_text('slash')
(source/'link').symlink_to('a'); (source/'dirlink').symlink_to('sub dir'); (source/'dangling').symlink_to('missing')
os.mkfifo(source/'pipe')
s=socket.socket(socket.AF_UNIX); s.bind(str(source/'socket')); s.close()
(root/'ignored').write_text('destination sentinel')
for p in [*source.rglob('*'),source]:
 if not p.is_symlink(): p.chmod(0o1750 if p.is_dir() else 0o644)
 os.utime(p,ns=(1600000000123456789,)*2,follow_symlinks=False)
'''
SNAPSHOT = '''import pathlib,sys,stat,json,hashlib
root=pathlib.Path(sys.argv[1]); data={}
for p in [root,*sorted(root.rglob('*'))]:
 s=p.lstat(); data[str(p.relative_to(root))]=[s.st_mode,s.st_size,s.st_mtime_ns,s.st_ino]
 if stat.S_ISREG(s.st_mode): data[str(p.relative_to(root))].append(hashlib.sha256(p.read_bytes()).hexdigest())
 elif stat.S_ISLNK(s.st_mode): data[str(p.relative_to(root))].append(str(p.readlink()))
print(json.dumps(data,sort_keys=True))
'''

class ListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-list-fault-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = pathlib.Path(cls.library_tmp.name)/'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                '-fPIC', str(REPO/'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform != 'darwin': args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync listings ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        subprocess.run(['python3', '-c', FIXTURE, str(self.root)], check=True, env=ENV)
        self.source = self.root / 'source'
        if HOST:
            remote_code(FIXTURE, self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def snapshot(self, remote):
        if remote and HOST: return remote_json(SNAPSHOT, self.root)
        return json.loads(subprocess.check_output(['python3', '-c', SNAPSHOT, str(self.root)]))

    def run_list(self, binary, remote, sources, flags=(), explicit=False, log=None):
        native = pathlib.Path(binary) == BINARY
        command = [str(binary), *flags]
        if native: command += ['--no-fallback']
        if log: command += ['--log-file=' + str(log)]
        if remote:
            peer = ('/usr/local/bin/xs' if native else '/usr/bin/rsync') if HOST else str(binary)
            command += ['-e', RSH, '--rsync-path=' + shlex.quote(peer)]
        if explicit: command += ['--list-only']
        args = [(HOST or 'fake') + ':' + str(p) if remote else str(p) for p in sources]
        if explicit: args += [str(self.root / 'ignored')]
        return subprocess.run(command + args, capture_output=True, timeout=20, env=ENV)

    def compare(self, source, flags=(), explicit=False, expected_code=0):
        for remote in (False, True):
            with self.subTest(remote=remote, source=source, flags=flags, explicit=explicit):
                before = self.snapshot(remote)
                # Homebrew rsync 3.4.4 rejects remote names for a /.. argument.
                # Its local listing proves /.. means the same as /../; use that
                # equivalent spelling for the remote reference comparison.
                reference_source = [str(p)+'/' if remote and str(p).endswith('/..') else p for p in source]
                expected = self.run_list(REFERENCE, remote, reference_source, flags, explicit)
                actual = self.run_list(BINARY, remote, source, flags, explicit)
                self.assertEqual(expected.returncode, expected_code, expected.stderr)
                self.assertEqual(actual.returncode, expected.returncode, actual.stderr)
                self.assertEqual(actual.stdout, expected.stdout, (actual.stderr, expected.stderr))
                self.assertEqual(self.snapshot(remote), before)

    def test_single_entry_trailing_slash_and_recursive(self):
        for path in (self.source, str(self.source)+'/', self.source/'a', self.source/'link', self.source/'pipe', self.source/'socket',
                     str(self.source)+'/.', self.source/'a-dir'/'..'):
            for flags in ((), ('-r',), ('-a',), ('-d',), ('-l',), ('--no-dirs',)):
                self.compare([path], flags)

    def test_styles_escaping_filters_and_dry_run(self):
        for flags in (('-h',), ('-hh',), ('--no-h',), ('--no-human-readable',), ('-q',), ('-8',),
                      ('-n',), ('-i',), ('--out-format=%n',), ('--out-format=',),
                      ('-r', '--exclude=a-dir'), ('-r', '--exclude=*'), ('-r', '--min-size=3M'),
                      ('-rl', '--safe-links')):
            self.compare([str(self.source)+'/'], flags)

    def test_copy_links_reports_dangling_source(self):
        self.compare([str(self.source)+'/'], ['-rL'], expected_code=23)

    def test_explicit_listing_never_changes_destination(self):
        self.compare([str(self.source)+'/'], ['-r', '--delete', '--inplace', '--mkpath'], explicit=True)
        self.compare([self.source/'a', self.source/'link'], ['-l'], explicit=True)
        self.compare([self.source/'a-dir', self.source/'a-dir'], ['-r'], explicit=True)

    def test_logs_and_stats_report_no_transfers(self):
        for remote in (False, True):
            with self.subTest(remote=remote):
                log = self.root / ('remote.log' if remote else 'local.log')
                result = self.run_list(BINARY, remote, [str(self.source)+'/'], ['--stats', '-r'], log=log)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, log.read_bytes())
                for field in (b'Number of regular files transferred: 0', b'Number of created files: 0',
                              b'Number of deleted files: 0', b'Total transferred file size: 0 bytes'):
                    self.assertIn(field, result.stdout)
                self.assertEqual((self.root/'ignored').read_text(), 'destination sentinel')

    def test_missing_source_returns_partial_error(self):
        for remote in (False, True):
            result = self.run_list(BINARY, remote, [self.root/'missing'])
            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertIn(b'No such file or directory', result.stderr)

    def test_listing_does_not_read_regular_file_contents(self):
        source = self.source/'big'
        env = dict(ENV, XSYNC_FAULT_PATH=str(source.resolve()), XSYNC_FAULT_READ_ERROR='1')
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.fault)
        for remote in (False, True):
            args = [str(BINARY), '--no-fallback', '-c']
            if remote:
                args += ['-e', shlex.join([sys.executable, str(REPO/'tests/fault_ssh.py')]),
                         '--rsync-path=' + shlex.quote(str(BINARY))]
            args += [('fake:' if remote else '') + str(source)]
            result = subprocess.run(args, capture_output=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'2,012,345', result.stdout)
        # Positive control proves the injected read failure is actually active.
        result = subprocess.run([str(BINARY), '--no-fallback', '--no-clone', '-W', str(source),
                                 str(self.root/'read-control')], capture_output=True, env=env, timeout=10)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertIn(b'read errors', result.stderr)

if __name__ == '__main__': unittest.main()
