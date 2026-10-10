#!/usr/bin/env python3
"""Exercise live progress through a real PTY and the tmux terminal emulator."""
import errno
import fcntl
import os
import pathlib
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import termios
import unicodedata
import unittest

from output_test import BINARY, HOST, RSH

REPO = pathlib.Path(__file__).resolve().parent.parent
CSI = re.compile(rb'\x1b\[[0-?]*[ -/]*[@-~]')
ENV = dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS='', LC_ALL='en_US.UTF-8' if sys.platform == 'darwin' else 'C.UTF-8', TERM='xterm-256color')


def columns(text):
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)


def capture(command, width=80, env=None, resize=(), interrupt=False):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, width, 0, 0))
    proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=slave, env=env or ENV, start_new_session=True)
    os.close(slave)
    data = bytearray()
    started = time.monotonic()
    pending = list(resize)
    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed > 15:
                raise TimeoutError('progress child exceeded 15s')
            if pending and elapsed >= pending[0][0]:
                _, size = pending.pop(0)
                fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 24, size, 0, 0))
                proc.send_signal(signal.SIGWINCH)
            if interrupt and elapsed >= .5:
                proc.send_signal(signal.SIGINT)
                interrupt = False
            if select.select([master], [], [], .03)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO: break
                    raise
                if not chunk: break
                data.extend(chunk)
        return proc.wait(timeout=2), bytes(data)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        os.close(master)


class ProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HOST:
            from ssh_test import SSHTests
            SSHTests.setUpClass()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/rig' if HOST else '/tmp', prefix='xsync-progress-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.source = self.root/'source'; self.source.mkdir()
        (self.source/'wide-界-é-e\u0301.dat').write_bytes(b'x' * (1024 * 1024))
        if HOST:
            from ssh_test import remote_code
            remote_code('import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)', self.root)
            self.addCleanup(remote_code, 'import shutil,sys; shutil.rmtree(sys.argv[1])', self.root)

    def command(self, flags=(), direction='local', target='target'):
        source, dest = str(self.source)+'/', str(self.root/target)+'/'
        args = [str(BINARY), '-a', '--no-fallback', '--no-clone', '--progress', '-j1', '--bwlimit=1024', *flags]
        if direction != 'local':
            args += ['-e', RSH, '--rsync-path='+shlex.quote('/usr/local/bin/xsync' if HOST else str(BINARY))]
            if direction == 'push': dest = (HOST or 'fake')+':'+dest
            else: source = (HOST or 'fake')+':'+source
        return args+[source, dest]

    def test_narrow_unicode_frames_and_cursor(self):
        for width in (1, 12, 32, 80, 120):
            with self.subTest(width=width):
                code, data = capture(self.command(target=str(width)), width)
                self.assertEqual(code, 0, data)
                self.assertIn(b'\x1b[?25l', data)
                self.assertTrue(data.count(b'\x1b[?25h') >= data.count(b'\x1b[?25l'))
                frames = re.findall(rb'\x1b\[\?2026h(.*?)\x1b\[\?2026l', data, re.S)
                self.assertGreater(len(frames), 2)
                for frame in frames:
                    text = CSI.sub(b'', frame).decode('utf-8')
                    for line in text.replace('\r', '').split('\n'):
                        self.assertLessEqual(columns(line), width - 1, repr(line))

    def test_ascii_locale_and_dumb_terminal(self):
        for term in ('xterm-256color', 'dumb'):
            with self.subTest(term=term):
                code, data = capture(self.command(target=term), env=dict(ENV, LC_ALL='C', TERM=term))
                self.assertEqual(code, 0, data)
                self.assertTrue(data.isascii(), data)
                if term == 'dumb': self.assertNotIn(b'\x1b', data)
                else:
                    self.assertIn(b'\\#347', data)
                    self.assertIn(b'#', data)

    def test_unsafe_names_even_with_raw_output(self):
        old = next(self.source.iterdir())
        # APFS rejects invalid UTF-8 names; Linux also covers arbitrary bytes.
        name = os.fsencode(self.source) + b'/tab\tbad' + (b'' if sys.platform == 'darwin' else b'\xff') + b'\x1bname'
        os.rename(old, name)
        code, data = capture(self.command(('-8',)))
        self.assertEqual(code, 0, data)
        data.decode('utf-8')
        self.assertIn(b'\\#011', data)
        if sys.platform != 'darwin': self.assertIn(b'\\#377', data)
        self.assertIn(b'\\#033', data)

    def test_resize_no_color_and_interrupt(self):
        code, data = capture(self.command(('--bwlimit=512',)), width=120,
                             env=dict(ENV, NO_COLOR='1'), resize=((.25, 18), (.65, 70)), interrupt=True)
        self.assertEqual(code, 20, data)
        self.assertIn(b'\x1b[?25h', data)
        self.assertNotRegex(data, rb'\x1b\[[\d;]*m')
        self.assertIn(b'code 20', data)

    def test_push_over_transport(self):
        code, data = capture(self.command(direction='push'))
        self.assertEqual(code, 0, data)
        self.assertIn(b'\x1b[?25h', data)

    @unittest.skipUnless(shutil.which('tmux'), 'tmux is not installed')
    def test_tmux_resize_keeps_prior_output(self):
        socket = str(self.root/'tmux.sock')
        def tmux(*args):
            return subprocess.run(['tmux', '-S', socket, *map(str, args)], check=True,
                                  capture_output=True, timeout=5).stdout
        command = "printf 'SENTINEL-BEFORE-PROGRESS\\n'; " + shlex.join(self.command(('--bwlimit=512',))) + "; printf '\\nSENTINEL-AFTER-PROGRESS\\n'; sleep 8"
        tmux('-f', '/dev/null', 'new-session', '-d', '-x', 120, '-y', 24, '-s', 'progress',
             'env '+shlex.join([key+'='+value for key, value in ENV.items() if key in ('TERM','LC_ALL','XSYNC_CONFIG','XSYNC_OPTS')])+' sh -c '+shlex.quote(command))
        self.addCleanup(lambda: subprocess.run(['tmux','-S',socket,'kill-server'], capture_output=True))
        deadline = time.monotonic()+5
        while b'%' not in tmux('capture-pane','-p'):
            if time.monotonic() > deadline: self.fail('no live tmux progress')
            time.sleep(.04)
        tmux('resize-window', '-x', 18, '-y', 24)
        time.sleep(.2)
        narrow = tmux('capture-pane','-p','-S','-200')
        self.assertIn(b'SENTINEL-BEFORE-', narrow)
        tmux('resize-window','-x',90,'-y',24)
        while b'SENTINEL-AFTER-PROGRESS' not in tmux('capture-pane','-p'):
            if time.monotonic() > deadline: self.fail('tmux progress did not finish')
            time.sleep(.04)
        final = tmux('capture-pane','-p','-S','-200')
        self.assertIn(b'SENTINEL-BEFORE-PROGRESS', final)
        self.assertNotIn('━'.encode(), final, 'stale live bar survived completion')
        self.assertEqual(tmux('display-message','-p','#{cursor_flag}').strip(), b'1')


if __name__ == '__main__': unittest.main()
