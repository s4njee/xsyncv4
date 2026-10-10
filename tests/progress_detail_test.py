#!/usr/bin/env python3
"""Wire/compression detail and measured pipeline-stage estimates."""
import os
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


class ProgressDetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-progress-detail-lib-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.library = pathlib.Path(cls.library_tmp.name)/'fault_io.so'
        args = ['c++','-std=c++20','-dynamiclib' if sys.platform == 'darwin' else '-shared','-fPIC',
                str(REPO/'tests/fault_io.cpp'),'-o',str(cls.library)]
        args += ['-arch','arm64','-arch','x86_64'] if sys.platform == 'darwin' else ['-ldl']
        subprocess.run(args,check=True,capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync-progress-detail-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.source = self.root/'source'; self.source.mkdir()
        (self.source/'large').write_bytes(os.urandom(2*1024*1024))
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code,'import shutil,sys; shutil.rmtree(sys.argv[1])',self.root)

    def run_copy(self, direction, flags=(), env=None, name='target'):
        source, target = str(self.source)+'/', str(self.root/name)+'/'
        env = env or ENV
        rsh = shlex.join([sys.executable,str(REPO/'tests/fault_ssh.py')])
        peer = str(BINARY)
        if HOST:
            rsh = RSH
            variables = [key+'='+value for key,value in env.items() if key.startswith('XSYNC_FAULT_')]
            peer = shlex.join(['env','LD_PRELOAD=/work/build/fault_io.so',*variables,'/usr/local/bin/xs'])
        if direction == 'push': target = (HOST or 'fake')+':'+target
        else:
            if HOST:
                subprocess.run(['rsync','-a','-e',RSH,source,HOST+':'+source],check=True,capture_output=True)
            source = (HOST or 'fake')+':'+source
        command = [str(BINARY),'--no-fallback','-a','--progress','-j1','-e',rsh,'--rsync-path='+peer,*flags,source,target]
        stdout_path = self.root/'stdout'
        with stdout_path.open('wb') as output:
            code, data = capture(command,width=160,env=env,stdout=output)
        self.assertEqual(code,0,data[:1600])
        return CSI.sub(b'',data), stdout_path.read_bytes()

    def test_wire_rate_and_compression_ratio_push_pull(self):
        (self.source/'large').write_bytes(b'x'*2*1024*1024)
        for direction in ('push','pull'):
            with self.subTest(direction=direction):
                data, _ = self.run_copy(direction,('-z',),name=direction)
                self.assertRegex(data, rb'wire [\d.]+[KMGT]?/s')
                ratio = re.search(rb'ratio ([\d.]+)x',data)
                self.assertIsNotNone(ratio,data)
                self.assertGreater(float(ratio[1]),100)

    def test_incompressible_ratio_is_one(self):
        data, _ = self.run_copy('push',('-z',))
        self.assertIn(b'ratio 1.0x',data)

    def test_limiting_stages_push_pull(self):
        for direction in ('push','pull'):
            for stage in ('reading','network','writing'):
                with self.subTest(direction=direction,stage=stage):
                    name = direction+'-'+stage
                    marker = self.root/(name+'-marker')
                    env = dict(ENV)
                    flags = ['-vv']
                    if stage == 'network': flags += ['--bwlimit=1024']
                    else:
                        path = self.source if stage == 'reading' else self.root/name
                        env['XSYNC_FAULT_PATH'] = str(path)
                        env['DYLD_INSERT_LIBRARIES' if sys.platform == 'darwin' else 'LD_PRELOAD'] = str(self.library)
                        if stage == 'reading':
                            env['XSYNC_FAULT_EACH_READ_DELAY_US']='500000'
                            env['XSYNC_FAULT_READ_NOTIFY']=str(marker)
                        else:
                            env['XSYNC_FAULT_WRITE_DELAY_US']='500000'
                            env['XSYNC_FAULT_WRITE_NOTIFY']=str(marker)
                    _, output = self.run_copy(direction,flags,env,name)
                    if stage != 'network':
                        probe = pathlib.Path(str(marker)+'.1') if stage == 'reading' else marker
                        exists = probe.exists()
                        if HOST and direction == 'pull' and stage == 'reading':
                            from ssh_test import remote_code
                            exists = remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).exists())',probe).strip()=='True'
                        if HOST and direction == 'push' and stage == 'writing':
                            from ssh_test import remote_code
                            exists = remote_code('import pathlib,sys; print(pathlib.Path(sys.argv[1]).exists())',probe).strip()=='True'
                        if not exists and os.environ.get('XSYNC_PROGRESS_FAULT_OPTIONAL')=='1': self.skipTest('interposition unavailable')
                        self.assertTrue(exists,'stage delay did not interpose')
                    self.assertIn(('limiting stage: '+stage).encode(),output)

    def test_malformed_unnegotiated_stage_frames(self):
        for features, payload in ((1, b'\0\0'), (1|4294967296, b'\x80'),
                                  (1|4294967296,b'\0\0extra'), (1|4294967296,b'x'*21)):
            with self.subTest(features=features,payload=payload):
                peer = self.root/'peer.py'
                peer.write_text(PREAMBLE+'\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var('+str(features)+'))\n'
                                'send(35,'+repr(payload)+')\ntime.sleep(2)\n')
                rsh = shlex.join([sys.executable,str(peer)])
                result = subprocess.run([str(BINARY),'--no-fallback','-r','--numeric-ids','-vv','--progress',
                                         '-e',rsh,'--rsync-path=unused','fake:source',str(self.root/'target')],
                                        env=ENV,capture_output=True,timeout=5)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertIn(b'stage metrics',result.stderr)

    def test_missing_receiver_time_is_not_accepted(self):
        peer = self.root/'peer.py'
        peer.write_text(PREAMBLE+'\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var(4294967297))\n'
                        'send(10,b"\\0\\0\\0\\0")\n'
                        'while read_frame()[0]!=2: pass\nsend(3,b"\\0\\0")\n'
                        'send(7,b"\\0"*6)\ntime.sleep(2)\n')
        rsh = shlex.join([sys.executable,str(peer)])
        result = subprocess.run([str(BINARY),'--no-fallback','-r','--numeric-ids','-vv','--progress',
                                 '-e',rsh,'--rsync-path=unused',str(self.source)+'/', 'fake:target'],
                                env=ENV,capture_output=True,timeout=5)
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertIn(b'receiver stage metrics',result.stderr)


if __name__ == '__main__': unittest.main()
