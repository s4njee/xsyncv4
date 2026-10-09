#!/usr/bin/env python3
"""Stop large native transfers at half, verify retained bytes and resume wire cost."""
import hashlib
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get('XSYNC_TEST_BINARY', REPO / 'build/xsync')).resolve()
MIB = 1024 * 1024
HOST = os.environ.get('XSYNC_RIG_HOST')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


class ResumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='xsync resume fixture ')
        # glibc splits LD_PRELOAD on whitespace, even within a library filename.
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-resume-lib-')
        cls.root = pathlib.Path(cls.fixture.name)
        cls.fault = pathlib.Path(cls.library_tmp.name) / 'fault_io.so'
        command = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared',
                   '-fPIC', str(REPO / 'tests/fault_io.cpp'), '-o', str(cls.fault)]
        if sys.platform != 'darwin': command.append('-ldl')
        subprocess.run(command, check=True, capture_output=True)
        cls.source = cls.root / 'large'
        with cls.source.open('wb') as stream:
            for _ in range(64): stream.write(os.urandom(MIB))
        cls.digest = sha(cls.source)
        cls.source.chmod(0o640)
        os.utime(cls.source, ns=(1600000000123456789, 1600000000123456789))

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()
        cls.library_tmp.cleanup()

    def fault_env(self, path):
        env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.fault)
        env['XSYNC_FAULT_PATH'] = str(path.resolve())
        return env

    def command(self, transport, target, *flags):
        a, b = str(self.source), str(target)
        rsh = shlex.join([sys.executable, str(REPO / 'tests/fault_ssh.py')])
        if transport == 'push': b = 'fake:' + b
        if transport == 'pull': a = 'fake:' + a
        return [str(BINARY), '--no-fallback', '-aP', '--no-clone', '--stats', '-j4',
                '-e', rsh, '--rsync-path=' + str(BINARY), *flags, a, b]

    def check_file(self, target):
        self.assertEqual(sha(target), self.digest)
        self.assertEqual(target.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(list(target.parent.glob('.' + target.name + '.*')), [])

    def wire_bytes(self, result, direction):
        field = 'sent' if direction == 'push' else 'received'
        match = re.search(rb'Total bytes ' + field.encode() + rb': ([\d,]+)', result.stdout)
        self.assertIsNotNone(match, result.stdout)
        return int(match[1].replace(b',', b''))

    def test_halfway_interrupt_and_disconnect_resume(self):
        for transport, event in (('local', 'signal'), ('push', 'signal'), ('pull', 'signal'),
                                 ('push', 'disconnect'), ('pull', 'disconnect')):
            with self.subTest(transport=transport, event=event), tempfile.TemporaryDirectory(prefix='xsync half ') as tmp:
                root = pathlib.Path(tmp)
                target = root / 'large'
                env = self.fault_env(root)
                marker = root / 'halfway'
                env.update(XSYNC_FAULT_WRITE_DELAY_US='400000', XSYNC_FAULT_WRITE_FROM_OFFSET=str(32 * MIB),
                           XSYNC_FAULT_WRITE_NOTIFY=str(marker), XSYNC_FAULT_SERVER_PID=str(root / 'server.pid'))
                proc = subprocess.Popen(self.command(transport, target), env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                try:
                    deadline = time.monotonic() + 10
                    while True:
                        if marker.exists(): break
                        self.assertIsNone(proc.poll(), 'transfer finished before the half-way stop')
                        self.assertLess(time.monotonic(), deadline, 'half-way transfer timeout')
                        time.sleep(.001)
                    if event == 'signal': proc.send_signal(signal.SIGINT)
                    else:
                        victim = proc.pid if transport == 'push' else int((root / 'server.pid').read_text())
                        os.kill(victim, signal.SIGKILL)
                    out, err = proc.communicate(timeout=5)
                    expected = 20 if event == 'signal' else -signal.SIGKILL if transport == 'push' else 12
                    self.assertEqual(proc.returncode, expected, err)
                    deadline = time.monotonic() + 5
                    while not target.exists() or list(root.glob('.large.*')):
                        self.assertLess(time.monotonic(), deadline, 'partial cleanup timeout')
                        time.sleep(.005)
                    kept = target.stat().st_size
                    self.assertGreaterEqual(kept, 31 * MIB)
                    self.assertLessEqual(kept, 36 * MIB)
                    with target.open('rb') as partial, self.source.open('rb') as original:
                        self.assertEqual(hashlib.sha256(partial.read()).digest(), hashlib.sha256(original.read(kept)).digest())
                    result = subprocess.run(self.command(transport, target), capture_output=True, timeout=15,
                                            env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.check_file(target)
                    if transport != 'local':
                        sent = self.wire_bytes(result, transport)
                        self.assertGreaterEqual(sent, self.source.stat().st_size - kept)
                        self.assertLess(sent, self.source.stat().st_size - kept + 256 * 1024)
                        print(f'\n{transport}/{event}: kept {kept // MIB} MiB; resumed wire {sent} bytes', flush=True)
                finally:
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    proc.communicate(timeout=5)

    def test_remote_verified_and_invalid_prefixes(self):
        for transport in ('push', 'pull'):
            for kind in ('valid', 'corrupt', 'empty', 'complete', 'oversized'):
                with self.subTest(transport=transport, kind=kind), tempfile.TemporaryDirectory() as tmp:
                    target = pathlib.Path(tmp) / 'large'
                    size = 0 if kind == 'empty' else self.source.stat().st_size if kind in ('complete', 'oversized') else 20 * MIB + 123
                    with self.source.open('rb') as source: target.write_bytes(source.read(size))
                    if kind == 'oversized':
                        with target.open('ab') as stream: stream.write(b'extra old tail')
                    if kind == 'corrupt':
                        with target.open('r+b') as stream:
                            stream.seek(5 * MIB)
                            stream.write(b'corrupt prefix')
                    os.utime(target, (1, 1))
                    result = subprocess.run(self.command(transport, target), capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.check_file(target)
                    accepted = size if kind in ('valid', 'corrupt', 'complete', 'oversized') else 0
                    if kind == 'corrupt':
                        # E04 rejects the corrupt prefix, then independently verifies
                        # and reuses its unaffected blocks through negotiated deltas.
                        matched = re.search(rb'Delta matched data: ([\d,]+)', result.stdout)
                        self.assertIsNotNone(matched, result.stdout)
                        self.assertGreater(int(matched[1].replace(b',', b'')), size - 256 * 1024)
                    cost = self.wire_bytes(result, transport)
                    remaining = self.source.stat().st_size - accepted
                    self.assertGreaterEqual(cost, remaining)
                    self.assertLess(cost, remaining + 256 * 1024)

    def test_local_reuses_verified_bytes(self):
        for valid in (True, False):
            with self.subTest(valid=valid), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                target = root / 'large'
                with self.source.open('rb') as source: target.write_bytes(source.read(20 * MIB + 123))
                if not valid:
                    with target.open('r+b') as stream: stream.write(b'invalid')
                marker = root / 'source-read'
                env = self.fault_env(self.source)
                env['XSYNC_FAULT_READ_NOTIFY'] = str(marker)
                env['XSYNC_FAULT_PREAD_NOTIFY'] = str(root / 'delta-read')
                env['XSYNC_FAULT_PREAD_MIN_SIZE'] = str(MIB // 2)
                result = subprocess.run(self.command('local', target), capture_output=True, env=env, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.check_file(target)
                # Prefix hashing uses small preads; actual source data uses read or larger delta preads.
                self.assertEqual((root / 'source-read.1').exists() or (root / 'delta-read').exists(), not valid)

    def test_inplace_verified_prefix(self):
        for transport in ('local', 'push', 'pull'):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory() as tmp:
                target = pathlib.Path(tmp) / 'large'
                kept = 20 * MIB + 123
                with self.source.open('rb') as source: target.write_bytes(source.read(kept))
                result = subprocess.run(self.command(transport, target, '--inplace'), capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.check_file(target)
                if transport != 'local':
                    cost = self.wire_bytes(result, transport)
                    self.assertLess(cost, self.source.stat().st_size - kept + 256 * 1024)

    def test_whole_file_disables_resume(self):
        for transport in ('push', 'pull'):
            for flags, resume in ((['-W'], False), (['--whole-file', '--no-whole-file'], True)):
                with self.subTest(transport=transport, flags=flags), tempfile.TemporaryDirectory() as tmp:
                    target = pathlib.Path(tmp) / 'large'
                    kept = 20 * MIB + 123
                    with self.source.open('rb') as source: target.write_bytes(source.read(kept))
                    result = subprocess.run(self.command(transport, target, *flags), capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.check_file(target)
                    cost = self.wire_bytes(result, transport)
                    remaining = self.source.stat().st_size - (kept if resume else 0)
                    self.assertGreaterEqual(cost, remaining)
                    self.assertLess(cost, remaining + 256 * 1024)

    def test_prefix_and_offsets_above_four_gib(self):
        # Sparse fixtures cover 64-bit offsets without allocating gigabytes.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            source, target = root / 'source', root / 'target'
            prefix = 1 << 32
            tail = os.urandom(MIB)
            with source.open('wb') as stream:
                stream.seek(prefix)
                stream.write(tail)
            with target.open('wb') as stream: stream.truncate(prefix)
            command = [str(BINARY), '--no-fallback', '-aP', '--inplace', '--stats', '-j4',
                       '-e', shlex.join([sys.executable, str(REPO / 'tests/fault_ssh.py')]),
                       '--rsync-path=' + str(BINARY), str(source), 'fake:' + str(target)]
            result = subprocess.run(command, capture_output=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.stat().st_size, prefix + MIB)
            with target.open('rb') as stream:
                self.assertEqual(stream.read(MIB), bytes(MIB))
                stream.seek(prefix - MIB)
                self.assertEqual(stream.read(MIB), bytes(MIB))
                self.assertEqual(stream.read(), tail)
            cost = self.wire_bytes(result, 'push')
            self.assertGreaterEqual(cost, MIB)
            self.assertLess(cost, MIB + 256 * 1024)

    @unittest.skipUnless(HOST, 'real SSH resume runs in the isolated Linux rig')
    def test_real_ssh_halfway_resume(self):
        import ssh_test
        from ssh_test import RSH, remote_code, remote_json
        ssh_test.SSHTests.setUpClass()
        remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
        subprocess.run(['rsync', '-a', '-e', RSH, str(self.source), HOST + ':' + str(self.source)],
                       check=True, capture_output=True, timeout=20)
        try:
            for transport in ('push', 'pull'):
                with self.subTest(transport=transport), tempfile.TemporaryDirectory(prefix='xsync ssh half ') as tmp:
                    root = pathlib.Path(tmp)
                    target, marker, pidfile = root / 'large', root / 'halfway', root / 'server.pid'
                    remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', root)
                    def configure(env):
                        remote_code("import pathlib,sys; pathlib.Path('/rig/config.json').write_text(sys.argv[1])",
                                    json.dumps({'pid': str(pidfile), 'env': env}))
                    fault = {'LD_PRELOAD': '/work/build/fault_io.so', 'XSYNC_FAULT_PATH': str(root),
                             'XSYNC_FAULT_WRITE_FROM_OFFSET': str(32 * MIB),
                             'XSYNC_FAULT_WRITE_DELAY_US': '400000', 'XSYNC_FAULT_WRITE_NOTIFY': str(marker)}
                    configure(fault if transport == 'push' else {})
                    env = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='')
                    if transport == 'pull': env.update(fault)
                    a, b = str(self.source), str(target)
                    if transport == 'push': b = HOST + ':' + b
                    else: a = HOST + ':' + a
                    command = [str(BINARY), '--no-fallback', '-aP', '--stats', '-j4', '-e', RSH,
                               '--rsync-path=python3 /work/tests/rig/server.py', a, b]
                    proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, env=env, start_new_session=True)
                    try:
                        deadline = time.monotonic() + 10
                        while not (remote_json('import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))', marker)
                                   if transport == 'push' else marker.exists()):
                            self.assertIsNone(proc.poll(), 'SSH transfer finished before half-way stop')
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.005)
                        if transport == 'push': proc.kill()
                        else:
                            remote_code('import os,pathlib,signal,sys; os.kill(int(pathlib.Path(sys.argv[1]).read_text()),signal.SIGKILL)', pidfile)
                        out, err = proc.communicate(timeout=8)
                        self.assertEqual(proc.returncode, -signal.SIGKILL if transport == 'push' else 12, err)
                        inspect = '''import pathlib,sys,json,hashlib
p=pathlib.Path(sys.argv[1]); print(json.dumps(None if not p.exists() or list(p.parent.glob('.large.*')) else
{'size':p.stat().st_size,'hash':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':p.stat().st_mode&511,'mtime':p.stat().st_mtime_ns}))
'''
                        deadline = time.monotonic() + 5
                        while True:
                            state = remote_json(inspect, target) if transport == 'push' else json.loads(subprocess.check_output(['python3', '-c', inspect, str(target)]))
                            if state: break
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        kept = state['size']
                        self.assertGreaterEqual(kept, 31 * MIB)
                        self.assertLessEqual(kept, 36 * MIB)
                        with self.source.open('rb') as source:
                            self.assertEqual(state['hash'], hashlib.sha256(source.read(kept)).hexdigest())
                        configure({})
                        result = subprocess.run(command, capture_output=True, timeout=20,
                                                env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        state = remote_json(inspect, target) if transport == 'push' else json.loads(subprocess.check_output(['python3', '-c', inspect, str(target)]))
                        self.assertEqual(state, {'size':self.source.stat().st_size,'hash':self.digest.hex(),
                                                'mode':0o640,'mtime':self.source.stat().st_mtime_ns})
                        cost = self.wire_bytes(result, transport)
                        self.assertGreaterEqual(cost, self.source.stat().st_size - kept)
                        self.assertLess(cost, self.source.stat().st_size - kept + 256 * 1024)
                        print(f'\nReal SSH {transport}: kept {kept // MIB} MiB; resumed wire {cost} bytes', flush=True)
                    finally:
                        try: os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        proc.communicate(timeout=5)
                        remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])', root)
        finally:
            remote_code('import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)


if __name__ == '__main__':
    unittest.main()
