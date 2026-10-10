#!/usr/bin/env python3
"""Aggregate pacing, transport deadlines, keep-alives and negotiation."""
import json
import os
import pathlib
import select
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from output_test import BINARY, HOST, RSH
from ssh_test import remote_code
import wire_test as wire
from wire_test import var, string, frame, read_frame

REPO = pathlib.Path(__file__).resolve().parent.parent
ENV = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', XSYNC_FALLBACK='0')
IO_FEATURE = 1024
PREAMBLE = r'''
import os,sys,struct,time,select,json
def exact(n):
 data=b''
 while len(data)<n:
  part=os.read(0,n-len(data))
  if not part: raise EOFError()
  data+=part
 return data
def read_frame():
 n,k=struct.unpack('<IB',exact(5));return k,exact(n)
def var(n):
 data=bytearray()
 while n>=128: data.append((n&127)|128);n>>=7
 return bytes(data+bytes([n]))
def take_var(data,pos=0):
 value=shift=0
 while True:
  b=data[pos];pos+=1;value|=(b&127)<<shift
  if b<128:return value,pos
  shift+=7
def send(kind,data=b''):
 data=struct.pack('<IB',len(data),kind)+data
 while data: data=data[os.write(1,data):]
'''


class IOLimitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library_tmp = tempfile.TemporaryDirectory(prefix='xsync-io-fault-')
        cls.addClassCleanup(cls.library_tmp.cleanup)
        cls.fault = pathlib.Path(cls.library_tmp.name)/'fault_io.so'
        args = ['c++','-std=c++20','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',
                str(REPO/'tests/fault_io.cpp'),'-o',str(cls.fault)]
        if sys.platform=='darwin': args += ['-arch','arm64','-arch','x86_64']
        else: args += ['-ldl']
        subprocess.run(args,check=True,capture_output=True)
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync io limits ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root/'source'; self.source.mkdir()
        for i in range(4): (self.source/f'file-{i}').write_bytes(os.urandom(192*1024))
        if HOST:
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            subprocess.run(['rsync', '-a', '-e', RSH, str(self.source)+'/', HOST+':'+str(self.source)+'/'],
                           capture_output=True, check=True, timeout=20)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def command(self, direction, flags, name=None):
        source = str(self.source)+'/'
        dest = str(self.root/(name or direction))+'/'
        args = [str(BINARY), '--no-fallback', '-a', '--no-clone', '-j8', *flags]
        if direction != 'local':
            args += ['-e', RSH, '--rsync-path='+shlex.quote('/usr/local/bin/xs' if HOST else str(BINARY))]
            if direction == 'push': dest = (HOST or 'fake')+':'+dest
            else: source = (HOST or 'fake')+':'+source
        return args+[source,dest]

    def test_aggregate_rate_local_push_pull(self):
        for direction in ('local','push','pull'):
            with self.subTest(direction=direction):
                start = time.monotonic()
                result = subprocess.run(self.command(direction, ['--bwlimit=256', '--timeout=1']),
                                        env=ENV, capture_output=True, timeout=20)
                elapsed = time.monotonic()-start
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertGreaterEqual(elapsed, 2.8, 'rate bypassed: '+str(elapsed))
                self.assertLess(elapsed, 15, result.stderr)
                self.assertNotIn(b'error summary', result.stderr)
                if HOST and direction == 'push':
                    result = subprocess.run(['rsync','-a','-e',RSH,HOST+':'+str(self.root/direction)+'/',
                                             str(self.root/'verified')+'/'], capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    target = self.root/'verified'
                else: target = self.root/direction
                for p in self.source.iterdir(): self.assertEqual((target/p.name).read_bytes(), p.read_bytes())

    def test_local_default_clone_cannot_bypass_limit_and_zero_disables(self):
        start = time.monotonic()
        result = subprocess.run([str(BINARY),'--no-fallback','-a','--bwlimit=256',str(self.source)+'/',str(self.root/'clone')+'/'],
                                capture_output=True, env=ENV, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(time.monotonic()-start, 2.8)
        result = subprocess.run(self.command('local',['--bwlimit=0','--timeout=0'],name='unlimited'),
                                capture_output=True, env=ENV, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_compression_limits_wire_bytes(self):
        (self.root/'compressible').write_bytes(b'x'*(3*1024*1024))
        for direction in ('push','pull'):
            source=str(self.root/'compressible');target=str(self.root/('compressed-'+direction))
            if HOST:
                subprocess.run(['rsync','-a','-e',RSH,source,HOST+':'+source],capture_output=True,check=True,timeout=20)
            if direction=='push':target=(HOST or 'fake')+':'+target
            else:source=(HOST or 'fake')+':'+source
            start=time.monotonic()
            result=subprocess.run([str(BINARY),'--no-fallback','-azW','--bwlimit=128','--timeout=1',
                                   '-e',RSH,'--rsync-path='+shlex.quote('/usr/local/bin/xs' if HOST else str(BINARY)),source,target],
                                  capture_output=True,env=ENV,timeout=8)
            self.assertEqual(result.returncode,0,result.stderr)
            # Three MiB of content would take 24 seconds if charged before zstd.
            self.assertLess(time.monotonic()-start,6,result.stderr)
            if HOST and direction=='push':
                remote_code('import pathlib,sys; assert pathlib.Path(sys.argv[1]).read_bytes()==b"x"*(3*1024*1024)',
                            self.root/'compressed-push')
            else:self.assertEqual((self.root/('compressed-'+direction)).read_bytes(),b'x'*(3*1024*1024))
    def peer(self, body, features=1537, handshake=True):
        script = self.root/'peer.py'
        setup = f'FEATURES={features}\n' + PREAMBLE
        if handshake:
            setup += f'read_frame()\nsend(1,b"XSYNC\\1"+var({wire.VERSION})+var(FEATURES))\n'
            if features & IO_FEATURE:
                setup += 'kind,config=read_frame()\nassert kind==17,(kind,config)\n'
        script.write_text(setup+body+'\n')
        return shlex.join([sys.executable,str(script)])

    def run_peer(self, body, *flags, features=1537, handshake=True):
        command = [str(BINARY),'--no-fallback',*flags,'-e',self.peer(body,features,handshake),
                   '--rsync-path=unused','fake:source/']
        start = time.monotonic()
        result = subprocess.run(command, capture_output=True, env=ENV, timeout=6)
        return result, time.monotonic()-start

    def test_rate_units_rounding_and_wire_configuration(self):
        for value, expected in [('0',0),('1',1024),('0.5',1024),('1.5KiB',2048),('1.5KB',1024),
                                ('256k',262144),('1m',1048576),('1MB',1000448)]:
            with self.subTest(value=value):
                result,_ = self.run_peer('rate,p=take_var(config);seconds,p=take_var(config,p)\n'
                                         'assert p==len(config)\nprint(json.dumps([rate,seconds]),file=sys.stderr)\n'
                                         'send(5,b"\\0\\0")\n', '--bwlimit='+value, '--timeout=2')
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stderr),[expected,2])

    def test_invalid_cli_values_are_rejected(self):
        values = {'bwlimit':['-1','nan','inf','1e999','0.1','1b','1junk','1K/s','1e30'],
                  'timeout':['-1','nan','inf','0.5','1s','2147483648','184467440737095516160']}
        for option, invalid in values.items():
            for value in invalid:
                with self.subTest(option=option,value=value):
                    result = subprocess.run([str(BINARY),'--no-fallback','--'+option+'='+value,str(self.source)],
                                            capture_output=True,env=ENV,timeout=5)
                    self.assertEqual(result.returncode,1,result.stderr)
                    self.assertIn(('--'+option).encode(),result.stderr)

    def test_handshake_partial_frame_idle_and_post_eof_deadlines(self):
        before = {p.name:p.read_bytes() for p in self.source.iterdir()}
        cases = [(False,'time.sleep(10)'),(False,'os.write(1,b"\\x10\\0");time.sleep(10)'),
                 (True,'time.sleep(10)'),(True,'os.write(1,struct.pack("<IB",32,16)+b"xx");time.sleep(10)'),
                 (True,'send(5,b"\\0\\0");os.close(1);time.sleep(10)')]
        for handshake, body in cases:
            with self.subTest(handshake=handshake,body=body):
                result,elapsed = self.run_peer(body,'--timeout=1',handshake=handshake)
                self.assertEqual(result.returncode,30,result.stderr)
                self.assertIn(b'I/O timeout after 1 second',result.stderr)
                self.assertIn(b'idle timeout (code 30): 1 error',result.stderr)
                self.assertLess(elapsed,3)
                self.assertEqual({p.name:p.read_bytes() for p in self.source.iterdir()}, before)
                self.assertFalse((self.root/'target').exists())

    def test_keepalives_during_long_work_and_client_heartbeats(self):
        body = '''start=time.monotonic();received=0
while time.monotonic()-start<2.2:
 send(18)
 if select.select([0],[],[],0.15)[0]:
  kind,payload=read_frame();assert kind==18 and not payload;received+=1
assert received>=3,received
send(5,b"\\0\\0")
'''
        result,elapsed = self.run_peer(body,'--timeout=1')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertGreaterEqual(elapsed,2.2)
        self.assertNotIn(b'timeout',result.stderr)

    def test_keepalive_does_not_hide_a_blocked_writer(self):
        # Request one huge source, stop draining stdin, but continue sending
        # heartbeats. A write stall must expire even with a live receive path.
        (self.root/'huge').write_bytes(b'x'*(8*1024*1024))
        body = '''send(10,b"\\0\\0\\0\\0")
while True:
 kind,payload=read_frame()
 if kind==2:
  ident,_=take_var(payload);send(3,var(ident)+b"\\1\\0");break
while True: send(18);time.sleep(0.15)
'''
        rsh = self.peer(body,features=1025)
        start=time.monotonic()
        result = subprocess.run([str(BINARY),'--no-fallback','-r','--numeric-ids','-W','--timeout=1',
                                 '-e',rsh,'--rsync-path=unused',str(self.root/'huge'),'fake:target'],
                                capture_output=True,env=ENV,timeout=6)
        self.assertEqual(result.returncode,30,result.stderr)
        self.assertLess(time.monotonic()-start,3)

    def test_native_helper_keeps_alive_during_delayed_source_io(self):
        # Direct native peer keeps fault interposition out of SIP-protected shells.
        env=dict(ENV,XSYNC_FAULT_PATH=str((self.source/'file-0').resolve()),XSYNC_FAULT_READ_DELAY_US='2200000')
        env['DYLD_INSERT_LIBRARIES' if sys.platform=='darwin' else 'LD_PRELOAD']=str(self.fault)
        rsh=shlex.join([sys.executable,str(REPO/'tests/fault_ssh.py')])
        for direction in ('push','pull'):
            with self.subTest(direction=direction):
                source=str(self.source)+'/'
                target=str(self.root/('delayed-'+direction))+'/'
                if direction=='push':target='fake:'+target
                else:source='fake:'+source
                start=time.monotonic()
                result=subprocess.run([str(BINARY),'--no-fallback','-aW','--no-clone','--timeout=1',
                                       '-e',rsh,'--rsync-path='+shlex.quote(str(BINARY)),source,target],
                                      capture_output=True,env=env,timeout=8)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertGreaterEqual(time.monotonic()-start,2.1,'source delay did not activate')
                for p in self.source.iterdir():self.assertEqual((self.root/('delayed-'+direction)/p.name).read_bytes(),p.read_bytes())

    def test_simultaneous_read_write_stalls_report_one_timeout(self):
        (self.root/'huge').write_bytes(b'x'*(8*1024*1024))
        body='''send(10,b"\\0\\0\\0\\0")
while True:
 kind,payload=read_frame()
 if kind==2:
  ident,_=take_var(payload);send(3,var(ident)+b"\\1\\0");break
time.sleep(10)
'''
        for attempt in range(4):
            with self.subTest(attempt=attempt):
                result=subprocess.run([str(BINARY),'--no-fallback','-r','--numeric-ids','-W','--timeout=1',
                                       '-e',self.peer(body,features=1025),'--rsync-path=unused',
                                       str(self.root/'huge'),'fake:target'],capture_output=True,env=ENV,timeout=6)
                self.assertEqual(result.returncode,30,result.stderr)
                self.assertEqual(result.stderr.count(b'error summary:'),1,result.stderr)
                self.assertIn(b'error summary: 1 error (showing first 1)',result.stderr)

    def test_invalid_and_unnegotiated_keepalives(self):
        for features,body in [(1537,'send(18,b"bad")'),(513,'send(18)')]:
            result,_=self.run_peer(body,features=features)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertIn(b'keep-alive',result.stderr)

    def test_remote_timeout_exit_is_preserved(self):
        result,_=self.run_peer('sys.exit(30)','--timeout=1')
        self.assertEqual(result.returncode,30,result.stderr)
        self.assertIn(b'remote peer timed out',result.stderr)

    def test_feature_absence_refuses_or_falls_back_before_writes(self):
        for flag in ('--bwlimit=1m','--timeout=1'):
            result,_ = self.run_peer('sys.stdin.buffer.read()',flag,features=513)
            self.assertEqual(result.returncode,4,result.stderr)
            self.assertIn(b'bandwidth limits and idle timeouts',result.stderr)
        commands=self.root/'commands';commands.mkdir()
        script=commands/'rsync'
        script.write_text('#!'+sys.executable+'\nimport sys,json\nprint(json.dumps(sys.argv[1:]));sys.exit(19)\n')
        script.chmod(0o755)
        rsh=self.peer('sys.stdin.buffer.read()',features=513)
        args=['--bwlimit=256','--timeout=1','-e',rsh,'--rsync-path=unused','fake:source/']
        result=subprocess.run([str(BINARY),*args],capture_output=True,env=dict(ENV,PATH=str(commands),XSYNC_FALLBACK='1'),timeout=6)
        self.assertEqual(result.returncode,19,result.stderr)
        self.assertEqual(json.loads(result.stdout),args)
        self.assertEqual(result.stderr.count(b'falling back to rsync'),1)
        self.assertFalse((self.root/'target').exists())

    def test_interruption_during_throttling_is_prompt(self):
        for direction in ('local','push','pull'):
            with self.subTest(direction=direction):
                proc=subprocess.Popen(self.command(direction,['--bwlimit=16','--timeout=1','--partial']),
                                      stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=ENV)
                try:
                    time.sleep(0.5);start=time.monotonic();proc.send_signal(signal.SIGINT)
                    stdout,stderr=proc.communicate(timeout=3)
                    self.assertEqual(proc.returncode,20,stderr)
                    self.assertLess(time.monotonic()-start,2)
                    self.assertNotIn(b'code 30',stderr)
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.communicate(timeout=3)

    def test_timeout_preserves_atomic_and_partial_cleanup(self):
        source=self.root/'large';source.write_bytes(os.urandom(4*1024*1024))
        proxy=self.root/'stall-proxy.py'
        proxy.write_text(PREAMBLE+f'''
import threading,subprocess
peer=subprocess.Popen([{str(BINARY)!r},'--server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
def copy_input():
 try:
  while True:
   data=os.read(0,65536)
   if not data:break
   peer.stdin.write(data);peer.stdin.flush()
 except (BrokenPipeError,OSError):pass
threading.Thread(target=copy_input,daemon=True).start()
def peer_exact(n):
 data=b''
 while len(data)<n:
  part=os.read(peer.stdout.fileno(),n-len(data))
  if not part:raise EOFError()
  data+=part
 return data
while True:
 header=peer_exact(5);n,kind=struct.unpack('<IB',header);data=peer_exact(n)
 send(kind,data)
 if kind==4:time.sleep(10)
''')
        for partial in (False,True):
            with self.subTest(partial=partial):
                target=self.root/('partial' if partial else 'atomic')
                target.write_bytes(b'previous valid destination')
                command=[str(BINARY),'--no-fallback','-aW','--no-clone','--timeout=1',
                         '-e',shlex.join([sys.executable,str(proxy)]),'--rsync-path=unused']
                if partial:command+=['--partial']
                result=subprocess.run(command+['fake:'+str(source),str(target)],capture_output=True,env=ENV,timeout=6)
                self.assertEqual(result.returncode,30,result.stderr)
                if partial:
                    data=target.read_bytes();self.assertGreater(len(data),0);self.assertLess(len(data),source.stat().st_size)
                    self.assertEqual(data,source.read_bytes()[:len(data)])
                else:self.assertEqual(target.read_bytes(),b'previous valid destination')
                self.assertFalse(list(self.root.glob('.'+target.name+'.*')))

    def test_malformed_io_configuration_never_opens_destination(self):
        for payload in (b'',var(512)+b'\0',var(1<<63)+b'\0',b'\0'+var(1<<31),b'\0\0X',b'X'*21):
            with self.subTest(payload=payload):
                options=bytes(name=='recursive' for name in wire.BOOLS)
                options+=b''.join(var(1 if name=='max_delete' else 2 if name=='jobs' else 0) for name in wire.INTS)
                hello=b'XSYNC\1'+var(wire.VERSION)+b'R'+var(1025)+options+b'\0\1'+string(str(self.root/'uncreated'))
                proc=subprocess.Popen([str(BINARY),'--server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    proc.stdin.write(frame(1,hello));proc.stdin.flush()
                    self.assertEqual(read_frame(proc)[0],1)
                    proc.stdin.write(frame(17,payload));proc.stdin.flush()
                    kind,body=read_frame(proc)
                    self.assertEqual(kind,8)
                    self.assertIn(b'malformed I/O configuration',body)
                    stdout,stderr=proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode,2,stderr)
                    self.assertNotIn(b'error summary',stderr)
                    self.assertFalse((self.root/'uncreated').exists())
                finally:
                    if proc.poll() is None:proc.kill()
                    proc.communicate(timeout=3)


if __name__=='__main__':unittest.main()
