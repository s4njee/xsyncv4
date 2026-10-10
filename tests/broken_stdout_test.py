#!/usr/bin/env python3
"""Closed diagnostic pipes cancel active work with rsync's diagnostic exit 13."""
import json
import os
import pathlib
import select
import shlex
import signal
import subprocess
import tempfile
import time
import unittest

from output_test import BINARY, HOST, RSH
import ssh_test
from ssh_test import remote_code, remote_json

REPO = pathlib.Path(__file__).resolve().parent.parent
ENV = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='0')
RSYNC = os.environ.get('XSYNC_TEST_RSYNC', '/opt/homebrew/bin/rsync' if os.uname().sysname == 'Darwin' else 'rsync')


class BrokenStdoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST: ssh_test.SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync closed stdout ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root/'source'; self.source.mkdir()
        (self.source/'blob').write_bytes(b'data'*1024*1024)
        if HOST:
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1],ignore_errors=True)', self.root)
            subprocess.run(['rsync','-a','-e',RSH,str(self.source)+'/',HOST+':'+str(self.source)+'/'],
                           check=True, capture_output=True, timeout=20)

    def command(self, direction, flags, name):
        source, target = str(self.source)+'/', str(self.root/name)+'/'
        args = [str(BINARY),'--no-fallback','-a','--no-clone','--atomic',*flags]
        pid = self.root/(name+'.pid')
        if direction != 'local':
            if HOST:
                ssh_test.SSHTests.configure(self, pid, {})
                server = 'python3 /work/tests/rig/server.py'
            else:
                helper = self.root/(name+' peer.py')
                helper.write_text('import os,sys,pathlib\npathlib.Path('+repr(str(pid))+').write_text(str(os.getpid()))\n'
                                  'os.execve('+repr(str(BINARY))+', ['+repr(str(BINARY))+',*sys.argv[1:]], os.environ)\n')
                server = shlex.join(['python3',str(helper)])
            args += ['-e',RSH,'--rsync-path='+server]
            if direction == 'push': target = (HOST or 'fake')+':'+target
            else: source = (HOST or 'fake')+':'+source
        return args+[source,target], pid

    def target_state(self, direction, target):
        code = '''import pathlib,sys,json
p=pathlib.Path(sys.argv[1]); print(json.dumps([[x.name,x.stat().st_size] for x in p.iterdir() if x.is_file()] if p.exists() else []))'''
        if HOST and direction == 'push': return remote_json(code, target)
        return [[p.name,p.stat().st_size] for p in target.iterdir() if p.is_file()] if target.exists() else []

    def mkdir_target(self, direction, target):
        if HOST and direction == 'push': remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir()', target)
        else: target.mkdir()

    def assert_peer_stopped(self, direction, marker):
        if direction == 'local': return
        code = '''import pathlib,sys,json,subprocess
p=pathlib.Path(sys.argv[1]); pid=p.read_text() if p.exists() else ''
r=subprocess.run(['ps','-o','stat=','-p',pid],capture_output=True,text=True) if pid else None
print(json.dumps(bool(r and r.stdout.strip() and not r.stdout.lstrip().startswith('Z'))))'''
        started = time.monotonic()
        while True:
            alive = remote_json(code, marker) if HOST else json.loads(subprocess.run(
                ['python3','-c',code,str(marker)], capture_output=True,text=True,check=True).stdout)
            if not alive: return
            if time.monotonic()-started > 1.5:
                if HOST: remote_code('import pathlib,os,signal,sys; os.kill(int(pathlib.Path(sys.argv[1]).read_text()),signal.SIGKILL)',marker)
                else: os.kill(int(marker.read_text()), signal.SIGKILL)
                self.fail('remote server survived stdout closure')
            time.sleep(.025)

    def closed_run(self, command):
        reader, writer = os.pipe(); os.close(reader)
        try: return subprocess.run(command,stdout=writer,stderr=subprocess.PIPE,env=ENV,timeout=10)
        finally: os.close(writer)

    def assert_diagnostic_error(self, result):
        self.assertEqual(result.returncode,13,result.stderr)
        self.assertIn(b'write stdout failed:',result.stderr)
        self.assertIn(b'errors with program diagnostics (code 13)',result.stderr)
        self.assertNotIn(b'error: received SIGINT',result.stderr)

    def test_closed_before_transfer_prevents_writes(self):
        for direction in ('local','push','pull'):
            for index, flags in enumerate((['-v'],['-i'],['--stats'],['-vn'],['--list-only'])):
                with self.subTest(direction=direction,flags=flags):
                    name = f'preclosed-{direction}-{index}'
                    command, _ = self.command(direction,flags,name)
                    self.assert_diagnostic_error(self.closed_run(command))
                    self.assertEqual(self.target_state(direction,self.root/name),[])
                    self.assertFalse((self.root/name).exists())

    def test_silent_transfers_do_not_depend_on_stdout(self):
        (self.source/'blob').write_bytes(b'silent')
        if HOST:
            subprocess.run(['rsync','-a','-e',RSH,str(self.source)+'/',HOST+':'+str(self.source)+'/'],check=True,capture_output=True)
        for direction in ('local','push','pull'):
            for index, flags in enumerate(([],['-q'],['-qv'],['--out-format='])):
                with self.subTest(direction=direction,flags=flags):
                    name = f'silent-{direction}-{index}'
                    command, pid = self.command(direction,flags,name)
                    result = self.closed_run(command)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertEqual(self.target_state(direction,self.root/name),[['blob',6]])
                    self.assert_peer_stopped(direction,pid)

    def test_closing_after_first_line_stops_transfer(self):
        for direction in ('local','push','pull'):
            with self.subTest(direction=direction):
                name = 'intro-'+direction
                command, pid = self.command(direction,['-v','--bwlimit=64'],name)
                proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV)
                try:
                    self.assertTrue(select.select([proc.stdout],[],[],10)[0],'no initial output')
                    self.assertTrue(proc.stdout.readline())
                    started = time.monotonic(); proc.stdout.close()
                    proc.wait(timeout=3); error = proc.stderr.read()
                    self.assertLess(time.monotonic()-started,2)
                    self.assert_diagnostic_error(subprocess.CompletedProcess(command,proc.returncode,stderr=error))
                    self.assert_peer_stopped(direction,pid)
                    self.assertEqual(self.target_state(direction,self.root/name),[])
                finally:
                    if proc.poll() is None: proc.kill(); proc.wait()
                    proc.stderr.close()
                    proc.stdout.close()

    def test_closing_during_buffered_events_cleans_or_keeps_partial(self):
        # -i events are sorted until completion: polling must detect closure
        # while bytes are moving, even without -v or --progress output.
        for direction in ('local','push','pull'):
            for partial in (False,True):
                with self.subTest(direction=direction,partial=partial):
                    name = f'midcopy-{direction}-{partial}'; target = self.root/name
                    self.mkdir_target(direction,target)
                    command, pid = self.command(direction,['-i','--bwlimit=1024',*(['--partial'] if partial else [])],name)
                    proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV)
                    try:
                        deadline = time.monotonic()+10
                        while not any(size >= 1024*1024+65536 for _,size in self.target_state(direction,target)):
                            self.assertIsNone(proc.poll(),'transfer ended before cancellation')
                            self.assertLess(time.monotonic(),deadline,'no data written')
                            time.sleep(.025)
                        started = time.monotonic(); proc.stdout.close()
                        proc.wait(timeout=3); error = proc.stderr.read()
                        self.assertLess(time.monotonic()-started,2)
                        self.assert_diagnostic_error(subprocess.CompletedProcess(command,proc.returncode,stderr=error))
                        self.assert_peer_stopped(direction,pid)
                        files = self.target_state(direction,target)
                        if partial:
                            self.assertEqual([name for name,_ in files],['blob'])
                            self.assertGreater(files[0][1],0)
                            self.assertLess(files[0][1],4*1024*1024)
                            # The retained prefix remains resumable after a diagnostic failure.
                            resume, _ = self.command(direction,['--partial'],name)
                            result = subprocess.run(resume,capture_output=True,env=ENV,timeout=15)
                            self.assertEqual(result.returncode,0,result.stderr)
                            self.assertEqual(self.target_state(direction,target),[['blob',4*1024*1024]])
                        else: self.assertEqual(files,[])
                    finally:
                        if proc.poll() is None: proc.kill(); proc.wait()
                        proc.stdout.close(); proc.stderr.close()

    def test_large_dry_run_matches_reference_exit(self):
        for index in range(3000): (self.source/(str(index).zfill(4)+'x'*95)).touch()
        for binary in (str(BINARY),RSYNC):
            with self.subTest(binary=binary):
                # Some libc/iconv combinations let rsync's ignored fflush
                # hide EPIPE. Force its fwrite to observe the failed write.
                args = [binary,'-avn',*(['--outbuf=N'] if binary == RSYNC else []),
                        str(self.source)+'/',str(self.root/'dry')+'/']
                result = self.closed_run(args)
                self.assertEqual(result.returncode,13,result.stderr)
                self.assertFalse((self.root/'dry').exists())

    def test_listing_closure_reports_error(self):
        for index in range(3000): (self.source/(str(index).zfill(4)+'x'*95)).touch()
        command = [str(BINARY),'--no-fallback','-a',str(self.source)+'/']
        proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV)
        try:
            self.assertTrue(select.select([proc.stdout],[],[],10)[0])
            self.assertTrue(proc.stdout.readline()); proc.stdout.close()
            proc.wait(timeout=3)
            self.assert_diagnostic_error(subprocess.CompletedProcess(command,proc.returncode,stderr=proc.stderr.read()))
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
            proc.stdout.close(); proc.stderr.close()

    def test_help_and_version_closed_stdout(self):
        for flag in ('--help','--version'):
            with self.subTest(flag=flag): self.assert_diagnostic_error(self.closed_run([str(BINARY),flag]))

    @unittest.skipUnless(pathlib.Path('/dev/full').exists(),'Linux full output device')
    def test_full_stdout_reports_diagnostic_io(self):
        (self.source/'blob').write_bytes(b'small')
        for args in (['--help'],['--version'],['-av',str(self.source)+'/',str(self.root/'full')+'/'],
                     ['-a','--stats',str(self.source)+'/',str(self.root/'stats')+'/']):
            with self.subTest(args=args), open('/dev/full','wb') as out:
                result = subprocess.run([str(BINARY),*args],stdout=out,stderr=subprocess.PIPE,env=ENV,timeout=5)
                self.assert_diagnostic_error(result)
                self.assertIn(b'No space left on device',result.stderr)


if __name__ == '__main__': unittest.main()
