#!/usr/bin/env python3
"""Native formatted output, deterministic ordering, and mirrored client logs."""
import errno
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()
HOST = os.environ.get('XSYNC_RIG_HOST')
SSH = ['ssh', '-i', '/keys/id test', '-oBatchMode=yes', '-oStrictHostKeyChecking=no',
       '-oUserKnownHostsFile=/dev/null', '-oLogLevel=ERROR']
RSH = shlex.join(SSH) if HOST else shlex.quote(str(REPO / 'tests/fakessh.sh'))


class OutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            import ssh_test
            ssh_test.SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync output ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root / 'source with spaces'
        self.source.mkdir()
        (self.source / 'z').write_bytes(b'last')
        (self.source / 'a').write_bytes(b'first')
        (self.source / 'sub').mkdir()
        (self.source / 'sub' / 'nested').write_bytes(b'nested')
        (self.source / 'link').symlink_to('a')
        (self.source / 'utf8-é').write_bytes(b'utf8')
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)
            self.refresh_remote()

    def refresh_remote(self):
        subprocess.run(['rsync', '-a', '-e', RSH, str(self.source) + '/', HOST + ':' + str(self.source) + '/'],
                       check=True, capture_output=True, timeout=20)

    def run_copy(self, direction='local', flags=(), name='target', log=None, server=None):
        source, target = str(self.source) + '/', str(self.root / name) + '/'
        command = [str(BINARY), '--no-fallback', '-a', '--no-clone', '-j8', *flags]
        if log is not None: command += ['--log-file=' + str(log)]
        if direction != 'local':
            command += ['-e', RSH, '--rsync-path=' + shlex.quote(server or ('/usr/local/bin/xsync' if HOST else str(BINARY)))]
            if direction == 'push': target = (HOST or 'fake') + ':' + target
            else: source = (HOST or 'fake') + ':' + source
        return subprocess.run(command + [source, target], capture_output=True, timeout=30)

    def test_all_fields_local_push_pull(self):
        for direction in ('local', 'push', 'pull'):
            with self.subTest(direction=direction):
                log = self.root / (direction + '.log')
                result = self.run_copy(direction, ['--out-format=%i|%n|%L|%l|%o|%f|%b|%t|%%'], name=direction, log=log)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, log.read_bytes())
                rows = [line.split('|') for line in result.stdout.decode().splitlines()]
                names = [row[1] for row in rows]
                self.assertEqual(names, ['./', 'a', 'link', 'sub/', 'sub/nested', 'utf8-é', 'z'])
                for row in rows:
                    code, name, link, size, operation, full, transferred, when, percent = row
                    source = self.source / name.rstrip('/')
                    self.assertEqual(int(size), source.lstat().st_size)
                    self.assertEqual(operation, 'recv' if direction == 'pull' else 'send')
                    self.assertEqual(full, name.rstrip('/') if direction == 'pull' else
                                     (str(source) + ('/.' if name == './' else '')).lstrip('/'))
                    self.assertRegex(when, r'^\d{4}/\d\d/\d\d \d\d:\d\d:\d\d$')
                    self.assertEqual(percent, '%')
                    self.assertEqual(link, ' -> a' if source.is_symlink() else '')
                    if source.is_file() and not source.is_symlink():
                        self.assertEqual(code, ('<' if direction == 'push' else '>') + 'f+++++++++')
                        self.assertEqual(int(transferred), source.stat().st_size)
                    else: self.assertEqual(int(transferred), 0)
                self.assertNotIn(b'\x1b', result.stdout)

    def test_completion_order_is_sorted_repeatedly(self):
        for number in range(100):
            path = self.source / f'file-{number:03}'
            path.write_bytes(os.urandom(1 if number % 2 else 30000))
        (self.source / 'aaa-big').write_bytes(os.urandom(3 * 1024 * 1024))
        if HOST: self.refresh_remote()
        for direction in ('local', 'push', 'pull'):
            previous = None
            for repeat in range(3):
                result = self.run_copy(direction, ['--out-format=%n'], name=f'{direction}-{repeat}')
                self.assertEqual(result.returncode, 0, result.stderr)
                names = result.stdout.splitlines()
                self.assertEqual(names, sorted(names))
                if previous is not None: self.assertEqual(result.stdout, previous)
                previous = result.stdout

    def test_default_verbose_itemize_and_log_stream(self):
        for direction in ('local', 'push', 'pull'):
            for flag in ('-v', '-i', '--stats'):
                plain = self.run_copy(direction, [flag], name=direction + flag + '-plain')
                self.assertEqual(plain.returncode, 0, plain.stderr)
                expected = {'./', 'a', 'link', 'sub/', 'sub/nested', 'utf8-é', 'z'}
                paths = []
                for line in plain.stdout.decode().splitlines():
                    name = (line[12:] if flag == '-i' else line).split(' -> ')[0]
                    if name in expected: paths.append(name)
                self.assertEqual(paths, [] if flag == '--stats' else sorted(expected))
                log = self.root / (direction + flag + '.log')
                result = self.run_copy(direction, [flag], name=direction + flag, log=log)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, log.read_bytes())
                self.assertIn(b'a\n', result.stdout)
                result = self.run_copy(direction, [flag], name=direction + flag, log=log)
                self.assertEqual(result.returncode, 0, result.stderr)
                # Logs append; no overwrite between invocations.
                self.assertTrue(log.read_bytes().endswith(result.stdout))

    def test_empty_format_quiet_and_width(self):
        for flags in (['--out-format='], ['-q', '--out-format=%n']):
            log = self.root / ('empty' + str(len(flags)) + '.log')
            result = self.run_copy(flags=flags, name='empty' + str(len(flags)), log=log)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(log.read_bytes(), b'')
        result = self.run_copy(flags=['--out-format=%-12n|%8l'], name='width')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'a           |       5', result.stdout.splitlines())

    def test_repeated_itemize_reports_unchanged_entries(self):
        for direction in ('local', 'push', 'pull'):
            target = 'repeated-' + direction
            result = self.run_copy(direction, name=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_copy(direction, ['-i'], name=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, b'')
            result = self.run_copy(direction, ['-ii', '--out-format=%i|%n'], name=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.decode().splitlines(), [
                '.d         |./', '.f         |a', '.L         |link', '.d         |sub/',
                '.f         |sub/nested', '.f         |utf8-é', '.f         |z'])

    def test_delete_and_metadata_output(self):
        for direction in ('local', 'push', 'pull'):
            result = self.run_copy(direction, name=direction)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = self.root / direction
            if HOST and direction == 'push':
                from ssh_test import remote_code
                remote_code("import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/'extra').write_text('extra'); (p/'a').chmod(0o600)", target)
            else:
                (target / 'extra').write_text('extra')
                (target / 'a').chmod(0o600)
            result = self.run_copy(direction, ['--delete', '--out-format=%i|%n|%o|%b'], name=direction)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertIn(b'.f...p.....|a|' + (b'recv' if direction == 'pull' else b'send') + b'|0', lines)
            self.assertIn(b'*deleting  |extra|del.|0', lines)

    def test_resume_bytes_and_dry_run(self):
        data = os.urandom(2 * 1024 * 1024)
        (self.source / 'big').write_bytes(data)
        if HOST: self.refresh_remote()
        for direction in ('local', 'push', 'pull'):
            target = self.root / ('resume-' + direction)
            if HOST and direction == 'push':
                from ssh_test import remote_code
                # Seed using rsync to avoid embedding binary content in a command.
                seed = self.root / 'seed'; seed.write_bytes(data[:1024 * 1024])
                remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', target)
                subprocess.run(['rsync', '-a', '-e', RSH, str(seed), HOST + ':' + str(target / 'big')], check=True, capture_output=True)
            else:
                target.mkdir(); (target / 'big').write_bytes(data[:1024 * 1024])
            result = self.run_copy(direction, ['--partial', '-z', '--out-format=%n|%l|%b'], name=target.name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'big|2097152|1048576', result.stdout.splitlines())
            result = self.run_copy(direction, ['-n', '--out-format=%n|%b'], name='dry-' + direction)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = result.stdout.splitlines()
            self.assertTrue(all(line.endswith(b'|0') for line in rows[:-1]))
            self.assertRegex(rows[-1], rb'^would transfer \d+ files \(.+\), delete 0$')

    def test_control_and_invalid_bytes_in_names(self):
        invalid_allowed = True
        for name in ('new\nline', 'literal\\#012', 'bad-\udcff'):
            try: (self.source / name).write_bytes(b'name')
            except OSError as error:
                if name != 'bad-\udcff' or error.errno not in (errno.EILSEQ, 92): raise
                invalid_allowed = False  # APFS requires valid UTF-8 names.
        result = self.run_copy(flags=['--out-format=%n'], name='escaped')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'new\\#012line', result.stdout.splitlines())
        self.assertIn(b'literal\\#134#012', result.stdout.splitlines())
        if invalid_allowed: self.assertIn(b'bad-\\#377', result.stdout.splitlines())
        self.assertIn('utf8-é'.encode(), result.stdout.splitlines())
        result = self.run_copy(flags=['--out-format=%n', '-8'], name='raw')
        self.assertEqual(result.returncode, 0, result.stderr)
        if invalid_allowed: self.assertIn(b'bad-\xff', result.stdout.splitlines())
        self.assertIn(b'new\\#012line', result.stdout.splitlines())

    def test_hostile_remote_output(self):
        peer = self.root / 'output peer.py'
        peer.write_text(r"""import os,struct,sys
case=sys.argv[1]
def var(n):
 b=bytearray()
 while n>=128: b.append((n&127)|128); n>>=7
 b.append(n); return bytes(b)
def string(s):
 if isinstance(s,str): s=s.encode()
 return var(len(s))+s
def send(kind,p):
 sys.stdout.buffer.write(struct.pack('<IB',len(p),kind)+p); sys.stdout.buffer.flush()
def read():
 h=sys.stdin.buffer.read(5)
 if len(h)!=5: sys.exit(0)
 n,k=struct.unpack('<IB',h); return k,sys.stdin.buffer.read(n)
def firstvar(p):
 n=0;shift=0
 for b in p:
  n|=(b&127)<<shift
  if b<128: return n
  shift+=7
_,hello=read()
send(1,b'XSYNC\1'+var(hello[6])+var(1 if case=='unnegotiated' else 97 if case=='time_overflow' else 33))
if case=='time_overflow': read() # negotiated output configuration
send(10,string('')+string('')+var(0)+var(0))
while True:
 kind,payload=read()
 if kind==2: send(3,var(firstvar(payload))+var(0))
 if kind==6: break
code='>f+++++++++' if case!='control_code' else '\x1bf+++++++++'
size=(1<<63) if case=='negative_size' else 0
p=string(code)+string('display')+string('/outside/display-only')+string('')+b'\1'
p+=var(size)+var(0)+var(((1<<63)-1)<<1 if case=='time_overflow' else 0)
if case=='trailing': p+=b'junk'
send(11,p)
send(7,b'\0'*6)
""")
        for case in ('unnegotiated', 'control_code', 'negative_size', 'trailing', 'time_overflow'):
            with self.subTest(case=case):
                flags = ['-ril'] if case != 'time_overflow' else ['-rl', '--out-format=%n|%f|%t']
                shell = shlex.join([sys.executable, str(peer), case])
                result = subprocess.run([str(BINARY), '--no-fallback', *flags, '-e', shell,
                                         str(self.source) + '/', 'fake:' + str(self.root / 'uncreated')],
                                        capture_output=True, timeout=20)
                if case == 'time_overflow':
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, b'display|outside/display-only|?\n')
                else:
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(b'output', result.stderr)
                self.assertFalse((self.root / 'uncreated').exists())

    def test_log_open_failure_prevents_transfer(self):
        result = self.run_copy(log=self.root / 'missing' / 'file')
        self.assertEqual(result.returncode, 11, result.stderr)
        self.assertIn(b'open log file', result.stderr)
        self.assertFalse((self.root / 'target').exists())


if __name__ == '__main__': unittest.main()
