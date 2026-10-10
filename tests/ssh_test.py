#!/usr/bin/env python3
"""Real-SSH transfer and interrupt checks; invoked by tests/ssh-rig.sh."""
import fcntl
import hashlib
import json
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
import threading
import time
import unittest

HOST = os.environ.get("XSYNC_RIG_HOST")
BINARY = os.environ.get("XSYNC_TEST_BINARY", "/usr/local/bin/xs")
SSH = ["ssh", "-i", "/keys/id test", "-oBatchMode=yes", "-oStrictHostKeyChecking=no",
       "-oUserKnownHostsFile=/dev/null", "-oLogLevel=ERROR"]
RSH = shlex.join(SSH)


def remote_code(code, *args):
    result = subprocess.run([*SSH, HOST, shlex.join(["python3", "-c", code, *map(str, args)])],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout


def remote_json(code, *args):
    return json.loads(remote_code(code, *args))


@unittest.skipUnless(HOST, "run via tests/ssh-rig.sh")
class SSHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        deadline = time.monotonic() + 10
        while True:
            try:
                remote_code("print('ready')")
                return
            except AssertionError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.1)

    def configure(self, pid, env):
        remote_code("import pathlib,sys; pathlib.Path('/rig/config.json').write_text(sys.argv[1])",
                    json.dumps({"pid": str(pid), "env": env}))

    def test_transfer_and_rerun(self):
        # Paths and the identity filename contain spaces; ssh performs a real key login.
        for transport in ("push", "pull"):
            with self.subTest(transport=transport), tempfile.TemporaryDirectory(dir="/rig", prefix="tree with spaces ") as tmp:
                root = pathlib.Path(tmp)
                src, dst = root / "source", root / "destination"
                src.mkdir()
                (src / "sub").mkdir()
                for i in range(100):
                    (src / "sub" / str(i)).write_bytes((str(i) * 100).encode())
                (src / "blob").write_bytes(b"0123456789" * 300000)
                (src / "link").symlink_to("sub/0")
                remote_code("import pathlib,sys; pathlib.Path(sys.argv[1]).mkdir(parents=True)", root)
                if transport == "pull":
                    subprocess.run([*SSH, HOST, shlex.join(["mkdir", "-p", str(src)])], check=True)
                    subprocess.run(["rsync", "-a", "-e", RSH, str(src) + "/", HOST + ":" + str(src) + "/"], check=True)
                self.configure(root / "pid", {})
                a, b = str(src) + "/", str(dst) + "/"
                if transport == "push":
                    b = HOST + ":" + b
                else:
                    a = HOST + ":" + a
                command = [BINARY, "-az", "--delete", "-e", RSH, "--rsync-path=python3 /work/tests/rig/server.py", a, b]
                for _ in range(2):
                    result = subprocess.run(command, capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                snapshot = """import pathlib,sys,json,hashlib
p=pathlib.Path(sys.argv[1]); result={}
for f in p.rglob('*'):
 if f.is_symlink(): result[str(f.relative_to(p))]=['link',str(f.readlink())]
 elif f.is_file(): result[str(f.relative_to(p))]=['file',hashlib.sha256(f.read_bytes()).hexdigest(),f.stat().st_mode & 4095,f.stat().st_mtime_ns]
print(json.dumps(result))
"""
                expected = json.loads(subprocess.check_output(["python3", "-c", snapshot, str(src)]))
                actual = remote_json(snapshot, dst) if transport == "push" else json.loads(subprocess.check_output(["python3", "-c", snapshot, str(dst)]))
                self.assertEqual(expected, actual)
                remote_code("import shutil,sys; shutil.rmtree(sys.argv[1])", root)

    def test_sigint_stops_both_sides(self):
        longest = 0.0
        for transport in ("push", "pull"):
            for phase in ("reading", "draining"):
                for partial in (False, True):
                    with self.subTest(transport=transport, phase=phase, partial=partial), tempfile.TemporaryDirectory(dir="/rig") as tmp:
                        root = pathlib.Path(tmp)
                        src, dst, pid_path = root / "source", root / "destination", root / "pid"
                        size = 8 * 1024 * 1024
                        src.mkdir()
                        (src / "file").write_bytes(b"x" * size)
                        dst.mkdir()
                        (dst / "file").write_bytes(b"old complete file")
                        remote_code("import pathlib,sys; p=pathlib.Path(sys.argv[1]); (p/'source').mkdir(parents=True); (p/'source/file').write_bytes(b'x'*int(sys.argv[2])); (p/'destination').mkdir(); (p/'destination/file').write_bytes(b'old complete file')", root, size)
                        marker, end = root / "active", root / "data_end"
                        fault = {"LD_PRELOAD": "/work/build/fault_io.so"}
                        if phase == "reading":
                            fault.update(XSYNC_FAULT_PATH=str(src), XSYNC_FAULT_READ_NOTIFY=str(marker), XSYNC_FAULT_READ_DELAY_US="500000")
                        else:
                            fault.update(XSYNC_FAULT_PATH=str(dst), XSYNC_FAULT_WRITE_NOTIFY=str(marker), XSYNC_FAULT_WRITE_DELAY_US="200000")
                        client_env = dict(os.environ, TERM="xterm-256color")
                        if (transport == "push") == (phase == "reading"):
                            client_env.update(fault)
                            server_env = {}
                        else:
                            server_env = fault
                        if phase == "draining":
                            if transport == "push":
                                client_env.update(LD_PRELOAD="/work/build/fault_io.so", XSYNC_FAULT_DATA_END_NOTIFY=str(end))
                            else:
                                server_env["LD_PRELOAD"] = "/work/build/fault_io.so"
                                server_env["XSYNC_FAULT_DATA_END_NOTIFY"] = str(end)
                        self.configure(pid_path, server_env)
                        a, b = str(src) + "/", str(dst) + "/"
                        if transport == "push":
                            b = HOST + ":" + b
                        else:
                            a = HOST + ":" + a
                        master, slave = pty.openpty()
                        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 120, 0, 0))
                        initial_terminal = termios.tcgetattr(slave)
                        output = bytearray()
                        reading = threading.Event()
                        reading.set()
                        def drain():
                            while reading.is_set():
                                if select.select([master], [], [], 0.05)[0]:
                                    try:
                                        chunk = os.read(master, 65536)
                                        if chunk: output.extend(chunk)
                                    except OSError:
                                        break
                        thread = threading.Thread(target=drain)
                        thread.start()
                        args = [BINARY, "-a", "--no-clone", "--progress", "-j1", "-e", RSH,
                                "--rsync-path=python3 /work/tests/rig/server.py", *( ["--partial"] if partial else []), a, b]
                        proc = subprocess.Popen(args, env=client_env, stdout=subprocess.DEVNULL, stderr=slave)
                        server_pid = None
                        try:
                            deadline = time.monotonic() + 10
                            while time.monotonic() < deadline and proc.poll() is None:
                                server_state = remote_json("import pathlib,sys,json; p=pathlib.Path(sys.argv[1]); print(json.dumps([p.read_text() if p.exists() else None,pathlib.Path(sys.argv[2]).exists(),pathlib.Path(sys.argv[3]).exists()]))", pid_path, str(marker) + ".1" if phase == "reading" else marker, end)
                                server_pid = int(server_state[0]) if server_state[0] else None
                                active = (marker.parent / (marker.name + ".1")).exists() if phase == "reading" and transport == "push" else marker.exists() if phase == "draining" and transport == "pull" else server_state[1]
                                ended = end.exists() if transport == "push" else server_state[2]
                                if server_pid and active and (phase == "reading" or ended):
                                    break
                                time.sleep(0.01)
                            else:
                                self.fail("transfer did not reach the requested live phase")
                            started = time.monotonic()
                            proc.send_signal(signal.SIGINT)
                            self.assertEqual(proc.wait(timeout=3), 20)
                            while remote_json("import os,sys,json; print(json.dumps(os.path.exists('/proc/'+sys.argv[1])))", server_pid):
                                self.assertLess(time.monotonic() - started, 1.0, "server survived client interruption")
                            elapsed = time.monotonic() - started
                            self.assertLess(elapsed, 1.0)
                            longest = max(longest, elapsed)
                            self.assertEqual(initial_terminal, termios.tcgetattr(slave))
                            time.sleep(0.05)
                            self.assertIn((bytes([27]) + b"[?25l"), output)
                            self.assertIn((bytes([27]) + b"[?25h"), output)
                            self.assertGreater(output.rfind((bytes([27]) + b"[?25h")), output.rfind((bytes([27]) + b"[?25l")))
                            inspect = "import pathlib,sys,json,hashlib; p=pathlib.Path(sys.argv[1]); f=p/'file'; print(json.dumps([sorted(x.name for x in p.iterdir()),f.stat().st_size,hashlib.sha256(f.read_bytes()).hexdigest()]))"
                            state = remote_json(inspect, dst) if transport == "push" else json.loads(subprocess.check_output(["python3", "-c", inspect, str(dst)]))
                            self.assertEqual(state[0], ["file"])
                            if not partial:
                                self.assertEqual(state[2], hashlib.sha256(b"old complete file").hexdigest())
                            else:
                                self.assertLess(state[1], size)
                            # Both source trees are still complete and no receiver temp survives.
                            self.assertEqual((src / "file").stat().st_size, size)
                            self.assertEqual(remote_json("import pathlib,sys,json; print(json.dumps((pathlib.Path(sys.argv[1])/'file').stat().st_size))", src), size)
                        finally:
                            if proc.poll() is None:
                                proc.kill()
                            proc.wait()
                            if server_pid:
                                remote_code("import os,sys,signal; p=int(sys.argv[1]);\ntry: os.kill(p,signal.SIGKILL)\nexcept ProcessLookupError: pass", server_pid)
                            reading.clear()
                            thread.join()
                            os.close(slave)
                            os.close(master)
                            remote_code("import shutil,sys; shutil.rmtree(sys.argv[1])", root)
        print("Maximum server shutdown after client SIGINT: %.3fs" % longest, flush=True)


if __name__ == "__main__":
    unittest.main()
