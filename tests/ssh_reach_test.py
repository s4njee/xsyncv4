#!/usr/bin/env python3
"""R-01: OpenSSH authentication prompts, multiplexing and startup output."""
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

import ssh_test
from ssh_test import BINARY, HOST, SSH, RSH, remote_code, remote_json

ESC = bytes([27])
PASSPHRASE = "xsync-disposable-passphrase"
PASSWORD = "xsync-disposable-password"


def interactive(command, replies, timeout=20):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0))
    initial = termios.tcgetattr(slave)
    def controlling_terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    env = dict(os.environ, TERM="xterm-256color")
    env.pop("SSH_AUTH_SOCK", None)
    proc = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                            env=env, preexec_fn=controlling_terminal)
    output, answers = bytearray(), []
    pending = list(replies)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            ready = select.select([master], [], [], 0.05)[0]
            if ready:
                try: chunk = os.read(master, 65536)
                except OSError: break
                output.extend(chunk)
                if pending and pending[0][0] in output:
                    pattern, answer = pending.pop(0)
                    answers.append(output.find(pattern))
                    os.write(master, answer)
            elif proc.poll() is not None:
                break
        if proc.poll() is None:
            raise AssertionError("interactive SSH timed out: " + output.decode(errors="replace"))
        if pending:
            raise AssertionError("SSH did not display expected prompts: " + output.decode(errors="replace"))
        if termios.tcgetattr(slave) != initial:
            raise AssertionError("SSH left terminal settings changed")
        return proc.returncode, bytes(output), answers
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        os.close(slave)
        os.close(master)


@unittest.skipUnless(HOST, "run via tests/ssh-rig.sh ssh_reach_test.py")
class SSHReachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ssh_test.SSHTests.setUpClass()
        cls.scratch = tempfile.TemporaryDirectory(dir="/rig", prefix="reach-")
        cls.root = pathlib.Path(cls.scratch.name)
        cls.key = cls.root / "encrypted key"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", PASSPHRASE, "-f", str(cls.key)], check=True)
        remote_code("import pathlib,sys; p=pathlib.Path('/root/.ssh/authorized_keys'); p.write_text(p.read_text()+sys.argv[1]); p.chmod(0o600)", cls.key.with_suffix(".pub").read_text())
        cls.daemon = int(remote_code("""import pathlib,subprocess,sys
subprocess.run(['chpasswd'],input='root:'+sys.argv[1]+'\\n',text=True,check=True)
p=pathlib.Path('/rig/auth_sshd.conf')
p.write_text('Port 2222\\nListenAddress 0.0.0.0\\nHostKey /etc/ssh/ssh_host_ed25519_key\\nPidFile /rig/auth_sshd.pid\\nUsePAM no\\nPermitRootLogin yes\\nPasswordAuthentication yes\\nKbdInteractiveAuthentication no\\nStrictModes yes\\n')
child=subprocess.Popen(['/usr/sbin/sshd','-D','-f',str(p)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
print(child.pid)
""", PASSWORD))
        cls.src = cls.root / "source"
        cls.src.write_bytes(b"real ssh authentication" * 10000)
        remote_code("import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)", cls.root)

    @classmethod
    def tearDownClass(cls):
        remote_code("import os,signal,sys,shutil; os.kill(int(sys.argv[1]),signal.SIGTERM); shutil.rmtree(sys.argv[2])", cls.daemon, cls.root)
        cls.scratch.cleanup()

    def command(self, shell, name, program="/usr/local/bin/xsync"):
        return [BINARY, "-a", "--progress", "-e", shlex.join(shell), "--rsync-path=" + program,
                str(self.src), HOST + ":" + str(self.root / name)]

    def transferred(self, name):
        self.assertEqual(remote_json("import pathlib,sys,json,hashlib; print(json.dumps(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest()))", self.root / name),
                         __import__("hashlib").sha256(self.src.read_bytes()).hexdigest())

    def test_host_key_and_passphrase(self):
        known = self.root / "new known hosts"
        shell = ["ssh", "-i", str(self.key), "-oIdentitiesOnly=yes", "-oPreferredAuthentications=publickey",
                 "-oStrictHostKeyChecking=ask", '-oUserKnownHostsFile="' + str(known) + '"']
        rc, output, prompts = interactive(self.command(shell, "passphrase"),
                                         [(b"Are you sure you want to continue connecting", b"yes\n"),
                                          (b"Enter passphrase for key", PASSPHRASE.encode() + b"\n")])
        self.assertEqual(rc, 0, output.decode(errors="replace"))
        self.assertTrue(known.exists())
        self.assertGreater(output.find(ESC + b"[?25l"), max(prompts), "progress obscured an authentication prompt")
        self.assertGreater(output.rfind(ESC + b"[?25h"), output.rfind(ESC + b"[?25l"))
        self.transferred("passphrase")

    def test_password_prompt(self):
        shell = ["ssh", "-p2222", "-oPreferredAuthentications=password", "-oPubkeyAuthentication=no",
                 "-oStrictHostKeyChecking=no", "-oUserKnownHostsFile=/dev/null", "-oLogLevel=ERROR"]
        rc, output, prompts = interactive(self.command(shell, "password"), [(b"password:", PASSWORD.encode() + b"\n")])
        self.assertEqual(rc, 0, output.decode(errors="replace"))
        self.assertGreater(output.find(ESC + b"[?25l"), prompts[0])
        self.assertGreater(output.rfind(ESC + b"[?25h"), output.rfind(ESC + b"[?25l"))
        self.transferred("password")

    def test_cancel_authentication(self):
        shell = ["ssh", "-i", str(self.key), "-oIdentitiesOnly=yes", "-oStrictHostKeyChecking=no", "-oUserKnownHostsFile=/dev/null"]
        rc, output, _ = interactive(self.command(shell, "cancelled"), [(b"Enter passphrase for key", bytes([3]))])
        self.assertEqual(rc, 20, output.decode(errors="replace"))
        self.assertNotIn(ESC + b"[?25l", output)
        self.assertFalse(remote_json("import pathlib,sys,json; print(json.dumps(pathlib.Path(sys.argv[1]).exists()))", self.root / "cancelled"))

    def test_controlmaster_reuse(self):
        control = self.root / "control"
        shell = [*SSH, "-oControlMaster=auto", "-oControlPersist=30", "-oControlPath=" + str(control)]
        try:
            for name in ("master-first", "master-second"):
                result = subprocess.run(self.command(shell, name), capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.transferred(name)
            check = subprocess.run([*SSH, "-S", str(control), "-O", "check", HOST], capture_output=True, timeout=5)
            self.assertEqual(check.returncode, 0, check.stderr.decode())
            self.assertIn(b"Master running", check.stderr)
        finally:
            subprocess.run([*SSH, "-S", str(control), "-O", "exit", HOST], capture_output=True, timeout=5)

    def test_shell_stdout_and_stderr(self):
        for message in ("hello", "hi", "welcome to the remote shell\\n"):
            script = self.root / ("banner-" + str(len(message)))
            program = "#!/bin/sh\nprintf '%s' " + shlex.quote(message) + "\nexec /usr/local/bin/xsync \"$@\"\n"
            remote_code("import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)", script, program)
            result = subprocess.run(self.command(SSH, "banner-result", str(script)), capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr.decode())
            self.assertIn(b"remote shell is printing text", result.stderr)
            self.assertNotIn(ESC + b"[?25l", result.stderr)
        script = self.root / "stderr"
        program = "#!/bin/sh\nprintf '%s\\n' 'remote stderr stays visible' >&2\nexec /usr/local/bin/xsync \"$@\"\n"
        remote_code("import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.write_text(sys.argv[2]); p.chmod(0o755)", script, program)
        result = subprocess.run(self.command(SSH, "stderr-result", str(script)), capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b"remote stderr stays visible", result.stderr)
        self.transferred("stderr-result")


if __name__ == "__main__":
    unittest.main()
