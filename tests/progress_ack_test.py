#!/usr/bin/env python3
"""Push bars follow receiver writes, with bounded negotiated ACK frames."""
import os
import hashlib
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

from output_test import BINARY, HOST, RSH
from progress_test import capture, ENV, CSI
from io_limit_test import PREAMBLE

REPO = pathlib.Path(__file__).resolve().parent.parent


class ProgressAckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-progress-ack-lib-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.library = pathlib.Path(cls.library_tmp.name)/'fault_io.so'
        args = ['c++', '-std=c++20', '-dynamiclib' if sys.platform == 'darwin' else '-shared', '-fPIC',
                str(REPO/'tests/fault_io.cpp'), '-o', str(cls.library)]
        if sys.platform == 'darwin': args += ['-arch', 'arm64', '-arch', 'x86_64']
        else: args += ['-ldl']
        subprocess.run(args, check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync-progress-ack-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.source = self.root/'source'; self.source.mkdir()
        (self.source/'large').write_bytes(b'x'*4*1024*1024)
        self.dest = self.root/'dest'
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def test_slow_receiver_does_not_show_early_100_percent(self):
        marker = self.root/'writing'
        env = dict(ENV, XSYNC_FAULT_PATH=str(self.dest), XSYNC_FAULT_WRITE_DELAY_US='500000',
                   XSYNC_FAULT_WRITE_NOTIFY=str(marker))
        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.library)
        # Native exec preserves DYLD through the fake SSH hop on macOS.
        rsh = shlex.join([sys.executable, str(REPO/'tests/fault_ssh.py')])
        server = str(BINARY)
        if HOST:
            rsh = RSH
            server = shlex.join(['env', 'LD_PRELOAD=/work/build/fault_io.so',
                                 'XSYNC_FAULT_PATH='+str(self.dest), 'XSYNC_FAULT_WRITE_DELAY_US=500000',
                                 'XSYNC_FAULT_WRITE_NOTIFY='+str(marker), '/usr/local/bin/xs'])
        command = [str(BINARY), '--no-fallback', '-a', '--progress', '-j1', '-e', rsh,
                   '--rsync-path='+server, str(self.source)+'/', (HOST or 'fake')+':'+str(self.dest)+'/']
        code, data = capture(command, width=160, env=env)
        self.assertEqual(code, 0, data[:1200])
        marker_exists = marker.exists()
        if HOST:
            from ssh_test import remote_code
            marker_exists = remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).exists())', marker).strip() == 'True'
        if not marker_exists and os.environ.get('XSYNC_PROGRESS_FAULT_OPTIONAL') == '1':
            self.skipTest('static binary or launcher cannot use fault interposition')
        self.assertTrue(marker_exists, 'write-delay fixture did not interpose on the receiver')
        frames = re.findall(rb'\x1b\[\?2026h(.*?)\x1b\[\?2026l', data, re.S)
        totals = [CSI.sub(b'', frame).splitlines()[-1] for frame in frames]
        percentages = [int(re.search(rb'(\d+)%', line)[1]) for line in totals if b'%' in line]
        for percent in (0,25,50,75): self.assertIn(percent, percentages)
        self.assertNotIn(100, percentages[:-1], 'sender finished reading while receiver was still writing')
        self.assertTrue(any(b'sent ' in line and b' wire' in line for line in totals))
        if HOST:
            digest = remote_code('import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())', self.dest/'large').strip()
            self.assertEqual(digest, hashlib.sha256((self.source/'large').read_bytes()).hexdigest())
        else: self.assertEqual((self.dest/'large').read_bytes(), (self.source/'large').read_bytes())
        self.assertIn(b'1 file', data)

    def test_unnegotiated_malformed_and_oversized_acks(self):
        for features, payload in ((1, b'\0\0'), (1|2147483648, b'\x80'),
                                  (1|2147483648, b'\0\0trailing'), (1|2147483648, b'x'*21)):
            with self.subTest(features=features, payload=payload):
                peer = self.root/'peer.py'
                peer.write_text(PREAMBLE + '\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var('+str(features)+'))\n'
                                'send(10,var(0)+var(0)+var(0)+var(0))\nsend(34,'+repr(payload)+')\n'
                                'time.sleep(2)\n')
                rsh = shlex.join([sys.executable, str(peer)])
                result = subprocess.run([str(BINARY),'--no-fallback','-a','--numeric-ids','--progress','-e',rsh,
                                         '--rsync-path=unused',str(self.source)+'/', 'fake:dest'],
                                        env=ENV,capture_output=True,timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'progress acknowledgment', result.stderr)

    def test_compressed_delta_inplace_and_sparse_completion(self):
        for mode, flags in (('compressed', ['-z']), ('delta', ['-I']),
                            ('inplace', ['-I','--inplace']), ('sparse', ['-S'])):
            with self.subTest(mode=mode):
                target = self.root/mode
                if mode in ('delta','inplace'):
                    if HOST:
                        from ssh_test import remote_code
                        remote_code('import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.mkdir(); (p/"large").write_bytes(b"x"*4*1024*1024)', target)
                    else:
                        target.mkdir(); (target/'large').write_bytes(b'x'*4*1024*1024)
                    with (self.source/'large').open('r+b') as f: f.seek(123456); f.write(b'changed bytes')
                elif mode == 'sparse': (self.source/'large').write_bytes(b'\0'*4*1024*1024)
                peer = '/usr/local/bin/xs' if HOST else str(BINARY)
                command = [str(BINARY), '--no-fallback','-a','-hh','--progress','-j2','-e',RSH,
                           '--rsync-path='+shlex.quote(peer), *flags, str(self.source)+'/',(HOST or 'fake')+':'+str(target)+'/']
                code, data = capture(command, width=160)
                self.assertEqual(code, 0, data[:1000])
                self.assertIn(b'1 file', data)
                self.assertIn(b'4.00M', data)
                if HOST:
                    from ssh_test import remote_code
                    digest = remote_code('import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())', target/'large').strip()
                    self.assertEqual(digest, hashlib.sha256((self.source/'large').read_bytes()).hexdigest())
                else: self.assertEqual((target/'large').read_bytes(), (self.source/'large').read_bytes())


if __name__ == '__main__': unittest.main()
