#!/usr/bin/env python3
"""Install into a disposable prefix and exercise the resulting executable/UI."""
import fcntl
import os
import pathlib
import pty
import select
import shlex
import signal
import struct
import subprocess
import tempfile
import termios
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BUILD = pathlib.Path(os.environ.get('XSYNC_TEST_BUILD', REPO / 'build'))


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xsync installed ')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.prefix = self.root / 'prefix with spaces'
        result = subprocess.run(['cmake', '--install', str(BUILD), '--prefix', str(self.prefix)],
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.binary = self.prefix / 'bin/xsync'

    def test_installed_executable_and_manual(self):
        source = self.root / 'source'
        source.write_bytes(b'installed copy works')
        result = subprocess.run([str(self.binary), '--no-fallback', '-a', str(source), str(self.root / 'dest')],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'dest').read_bytes(), source.read_bytes())
        self.assertEqual((self.root / 'dest').stat().st_mtime_ns, source.stat().st_mtime_ns)
        manual = self.prefix / 'share/man/man1/xsync.1'
        result = subprocess.run(['mandoc', '-Tlint', str(manual)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        plain = subprocess.check_output(['mandoc', '-Tascii', str(manual)]).decode()
        # Remove terminal bold/underline overstrikes before checking displayed text.
        while '\b' in plain:
            import re
            plain = re.sub('.\x08', '', plain)
        for option in ('--install', '--no-fallback', '--safe-links', '--atomic', '--delete'):
            self.assertIn(option, plain)
        self.assertTrue((self.prefix / 'share/zsh/site-functions/_xsync').exists())
        self.assertFalse((self.prefix / 'include').exists(), 'dependency headers leaked into the package')
        self.assertFalse((self.prefix / 'lib').exists(), 'dependency libraries leaked into the package')

    def test_live_zsh_completion(self):
        home = self.root / 'home'
        home.mkdir()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 180, 0, 0))
        def tty():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        env = dict(os.environ, HOME=str(home), TERM='xterm', PATH=str(self.prefix / 'bin') + ':' + os.environ.get('PATH', ''))
        proc = subprocess.Popen(['zsh', '-df'], stdin=slave, stdout=slave, stderr=slave, env=env, preexec_fn=tty)
        os.close(slave)
        output = bytearray()
        def read_until(marker):
            start = len(output)
            deadline = time.monotonic() + 10
            while marker not in output[start:]:
                if time.monotonic() > deadline: self.fail('zsh completion timeout: ' + output.decode(errors='replace'))
                if select.select([master], [], [], 0.2)[0]: output.extend(os.read(master, 65536))
        try:
            setup = "fpath=(" + shlex.quote(str(self.prefix / 'share/zsh/site-functions')) + " $fpath); "
            setup += "autoload -Uz compinit; compinit -D; "
            setup += "r07_capture() { zle -I; print -r -- CAPTURE=$BUFFER; zle kill-whole-line; }; "
            setup += "zle -N r07_capture; bindkey '^X' r07_capture; print READY_R07\n"
            os.write(master, setup.encode())
            read_until(b'\r\nREADY_R07\r\n')
            for prefix, expected in (('--no-fall', '--no-fallback '), ('--jo', '--jobs='), ('--dry-ru', '--dry-run ')):
                os.write(master, ('xsync ' + prefix + '\t').encode())
                # The completion widget runs synchronously before the next key.
                os.write(master, b'\x18')
                read_until(('CAPTURE=xsync ' + expected).encode())
        finally:
            os.write(master, b'\x04')
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            os.close(master)


if __name__ == '__main__':
    unittest.main()
