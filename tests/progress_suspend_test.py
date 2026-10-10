#!/usr/bin/env python3
"""Job control and cursor restoration on concurrent fatal/forced exits."""
import os
import pathlib
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from progress_test import capture, ENV
from output_test import BINARY
from io_limit_test import PREAMBLE


class SuspendProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync-suspend-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.source = self.root/'source'; self.source.mkdir()
        (self.source/'blob').write_bytes(b'x'*(4*1024*1024))

    def command(self, *flags):
        return [str(BINARY),'--no-fallback','-a','--no-clone','--progress','--bwlimit=1024',
                *flags,str(self.source)+'/',str(self.root/'dest')+'/']

    def assert_restored(self, data):
        self.assertIn(b'\x1b[?25l',data)
        self.assertGreater(data.rfind(b'\x1b[?25h'),data.rfind(b'\x1b[?25l'),data)

    @unittest.skipUnless(shutil.which('tmux'), 'tmux is not installed')
    def test_ctrl_z_fg_clears_and_redraws(self):
        socket = str(self.root/'tmux.sock')
        def tmux(*args):
            return subprocess.run(['tmux','-S',socket,*map(str,args)],check=True,capture_output=True,timeout=5).stdout
        tmux('-f','/dev/null','new-session','-d','-x',120,'-y',24,'/bin/bash --noprofile --norc -i')
        self.addCleanup(lambda: subprocess.run(['tmux','-S',socket,'kill-server'],capture_output=True))
        def send(text):
            tmux('send-keys','-l',text); tmux('send-keys','Enter')
        def pane(): return tmux('capture-pane','-p','-S','-200')
        def wait_for(predicate):
            deadline = time.monotonic()+12
            while not predicate():
                if time.monotonic()>deadline: self.fail('tmux wait failed: '+repr(pane()))
                time.sleep(.04)
        send("PS1='XSUSPEND-PROMPT>'; printf 'SENTINEL-BEFORE-PROGRESS\\n'")
        send('env '+shlex.join([k+'='+ENV[k] for k in ('TERM','LC_ALL','XSYNC_CONFIG','XSYNC_OPTS')])+' '+shlex.join(self.command()))
        wait_for(lambda: tmux('display-message','-p','#{cursor_flag}').strip()==b'0' and b'%' in pane())
        tmux('send-keys','C-z')
        wait_for(lambda: b'Stopped' in pane() and tmux('display-message','-p','#{cursor_flag}').strip()==b'1')
        self.assertNotIn('━'.encode(),pane(),'live rows survived suspension')
        def sizes(): return sorted((p.name,p.stat().st_size) for p in (self.root/'dest').glob('*') if p.is_file())
        before = sizes(); time.sleep(.25); self.assertEqual(sizes(),before,'copy continued while suspended')
        tmux('resize-window','-x',90,'-y',24)
        send("fg; rc=$?; printf 'XSUSPEND-%s:%s\\n' DONE \"$rc\"")
        wait_for(lambda: b'XSUSPEND-DONE:0' in pane())
        self.assertIn(b'SENTINEL-BEFORE-PROGRESS',pane())
        self.assertNotIn('━'.encode(),pane(),'live rows survived completion')
        self.assertEqual(tmux('display-message','-p','#{cursor_flag}').strip(),b'1')
        self.assertEqual((self.root/'dest/blob').read_bytes(),(self.source/'blob').read_bytes())

    def test_worker_fatal_and_competing_eof_restore(self):
        for index in range(9):
            with self.subTest(index=index):
                peer = self.root/'peer.py'
                peer.write_text(PREAMBLE+'\nread_frame()\nsend(1,b"XSYNC\\1"+var(4)+var(1))\nsend(4,b"")\n'+('time.sleep(.25)\n' if index==0 else ''))
                command = [str(BINARY),'--no-fallback','-r','--numeric-ids','--progress',
                           '-e',shlex.join([sys.executable,str(peer)]),'--rsync-path=unused','fake:source',str(self.root/'dest')+'/']
                code,data = capture(command)
                self.assertIn(code,(2,12),data)
                if index==0: self.assertIn(b'short DATA frame',data)
                self.assert_restored(data)

    def test_repeated_interrupts_restore_and_json_has_no_escapes(self):
        for mode in ('--progress','--progress=json'):
            with self.subTest(mode=mode):
                code,data = capture(self.command(mode),signals=((.3,signal.SIGINT),(.3,signal.SIGTERM)))
                self.assertEqual(code,20,data)
                if mode=='--progress': self.assert_restored(data)
                else: self.assertNotIn(b'\x1b',data)

    def test_closed_stdout_restores(self):
        (self.root/'dest').mkdir()
        reader,writer = os.pipe()
        closed = False
        seen = bytearray()
        def close_after_live(chunk):
            nonlocal closed
            seen.extend(chunk)
            if not closed and b'\x1b[?25l' in seen:
                os.close(reader); closed = True
        try: code,data = capture(self.command('-v'),stdout=writer,on_output=close_after_live)
        finally:
            os.close(writer)
            if not closed: os.close(reader)
        self.assertEqual(code,13,data)
        self.assert_restored(data)


if __name__=='__main__': unittest.main()
