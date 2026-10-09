#!/usr/bin/env python3
"""Root-only rsync differential tests across machines with different ID databases."""
import json
import os
import pathlib
import shlex
import subprocess
import tempfile
import unittest

from ssh_test import HOST, SSH, RSH, remote_code, remote_json

SETUP = """import pathlib,subprocess,sys
shared,only=map(int,sys.argv[1:3])
for name,ident in [('shared',shared),('onlyhere',only),('runner',60000)]:
 for args in (['groupadd','-g',str(ident),name],['useradd','-u',str(ident),'-g',str(ident),'-M','-s','/bin/sh',name]):
  r=subprocess.run(args,capture_output=True)
  if r.returncode not in (0,9): raise RuntimeError(r.stderr.decode())
p=pathlib.Path('/etc/sudoers.d/xsync-rig'); p.write_text('runner ALL=(ALL) NOPASSWD: ALL\\n'); p.chmod(0o440)
"""
FIXTURE = """import os,pathlib,stat,sys
root=pathlib.Path(sys.argv[1]); shared,only=map(int,sys.argv[2:4]); existing=sys.argv[4]=='1'
root.mkdir(parents=True,exist_ok=True)
for side in ('src','ref','got'):
 p=root/side
 if side!='src' and not existing: continue
 p.mkdir(); (p/'sub').mkdir()
 for name,owner in [('shared',shared),('only',only),('unknown',45454),('root',0)]:
  f=p/'sub'/name; f.write_bytes((b'source '+name.encode()) if side=='src' else b'previous bytes')
  os.chown(f,owner if side=='src' else 44444,owner if side=='src' else 44444); f.chmod(0o640)
 f=p/'sub/setid'; f.write_bytes(b'set-id file' if side=='src' else b'previous'); os.chown(f,shared if side=='src' else 44444,shared if side=='src' else 44444); f.chmod(0o6751)
 (p/'link').symlink_to('sub/shared'); os.lchown(p/'link',shared if side=='src' else 44444,shared if side=='src' else 44444)
 os.mkfifo(p/'fifo',0o640); os.mknod(p/'char',stat.S_IFCHR|0o620,os.makedev(1,3)); os.mknod(p/'block',stat.S_IFBLK|0o600,os.makedev(7,0)); os.mknod(p/'socket',stat.S_IFSOCK|0o640)
 for f in [p/'fifo',p/'char',p/'block',p/'socket',p/'sub',p]:
  os.chown(f,shared if side=='src' else 44444,shared if side=='src' else 44444)
 (p/'sub').chmod(0o2770); p.chmod(0o750)
 for f in list(p.rglob('*'))+[p]: os.utime(f,ns=(1234567890123456789,1234567890123456789 if side=='src' else 1200000000000000000),follow_symlinks=False)
"""
SNAPSHOT = """import hashlib,json,os,pathlib,stat,sys
root=pathlib.Path(sys.argv[1]); result={}
for f in [root]+sorted(root.rglob('*')):
 st=f.lstat(); row=[stat.S_IFMT(st.st_mode),st.st_mode & 4095,st.st_uid,st.st_gid,st.st_mtime_ns]
 if stat.S_ISREG(st.st_mode): row += [hashlib.sha256(f.read_bytes()).hexdigest()]
 elif stat.S_ISLNK(st.st_mode): row += [os.readlink(f)]
 elif stat.S_ISCHR(st.st_mode) or stat.S_ISBLK(st.st_mode): row += [os.major(st.st_rdev),os.minor(st.st_rdev)]
 result[str(f.relative_to(root))]=row
print(json.dumps(result,sort_keys=True))
"""


def local_code(code, *args):
    result = subprocess.run(["python3", "-c", code, *map(str, args)], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout


@unittest.skipUnless(HOST and os.geteuid() == 0, "run via tests/ssh-rig.sh root_test.py")
class RootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        local_code(SETUP, 1111, 22222)
        remote_code(SETUP, 3333, 33333)
        # 'onlyhere' intentionally has distinct names on opposite hosts.
        subprocess.run(["usermod", "-l", "clientonly", "onlyhere"], check=True)
        subprocess.run(["groupmod", "-n", "clientonly", "onlyhere"], check=True)
        remote_code("import subprocess; subprocess.run(['usermod','-l','serveronly','onlyhere'],check=True); subprocess.run(['groupmod','-n','serveronly','onlyhere'],check=True)")

    def test_root_differential(self):
        count = 0
        for transport in ("local", "push", "pull"):
            for state in ("fresh", "update", "inplace", "unchanged"):
                for options in (("-a",), ("-a", "--numeric-ids"), ("-rlptoD",), ("-rlptgD",)):
                    for sudo in (False, True):
                        with self.subTest(transport=transport, state=state, options=options, sudo=sudo), tempfile.TemporaryDirectory(dir="/rig", prefix="root-") as tmp:
                            root = pathlib.Path(tmp)
                            existing = state != "fresh"
                            local_code(FIXTURE, root, 1111, 22222, int(existing))
                            remote_code(FIXTURE, root, 3333, 33333, int(existing))
                            remote_receiver = transport == "push"
                            flags = [*options, *( ["--inplace"] if state == "inplace" else [])]
                            # Unchanged files exercise metadata-only paths in addition to copies.
                            if state == "unchanged":
                                code = "import pathlib,sys,shutil,os; p=pathlib.Path(sys.argv[1]);\nfor side in ('ref','got'):\n for f in (p/'src').rglob('*'):\n  if f.is_file() and not f.is_symlink():\n   d=p/side/f.relative_to(p/'src'); shutil.copyfile(f,d); os.utime(d,ns=(f.stat().st_atime_ns,f.stat().st_mtime_ns))"
                                # On different hosts, same contents and timestamps still permit
                                # uid/gid mapping and existing device/symlink metadata changes.
                                if remote_receiver: remote_code(code, root)
                                else: local_code(code, root)
                            src = str(root / "src") + "/"
                            for tool, destname in (("rsync", "ref"), ("xsync", "got")):
                                path = "/usr/bin/rsync" if tool == "rsync" else "/usr/local/bin/xsync"
                                command = [path, *flags]
                                dest = str(root / destname) + "/"
                                if transport != "local":
                                    command += ["-e", RSH, "--rsync-path=" + (("runuser -u runner -- sudo -n " if sudo else "") + path)]
                                    if remote_receiver: dest = HOST + ":" + dest
                                    else: src = HOST + ":" + str(root / "src") + "/"
                                command += [src, dest]
                                if sudo:
                                    command = ["runuser", "-u", "runner", "--", "sudo", "-n", *command]
                                result = subprocess.run(command, capture_output=True, timeout=20)
                                self.assertEqual(result.returncode, 0, tool + ": " + result.stderr.decode())
                            snapshots = remote_json if remote_receiver else lambda code, path: json.loads(local_code(code, path))
                            expected, actual = snapshots(SNAPSHOT, root / "ref"), snapshots(SNAPSHOT, root / "got")
                            self.assertEqual(expected, actual)
                            # Ensure the reference truly exercised name mapping or numeric fallback.
                            if "-a" in options:
                                shared = (3333 if transport == "push" else 1111)
                                if "--numeric-ids" in options: shared = 3333 if transport == "pull" else 1111
                                self.assertEqual(actual["sub/shared"][2:4], [shared, shared])
                                self.assertEqual(actual["sub/only"][2:4], [33333 if transport == "pull" else 22222] * 2)
                                self.assertEqual(actual["sub/unknown"][2:4], [45454, 45454])
                                self.assertEqual(actual["char"][-2:], [1, 3])
                                self.assertEqual(actual["block"][-2:], [7, 0])
                            count += 1
                            remote_code("import shutil,sys; shutil.rmtree(sys.argv[1])", root)
        print("Root differential cases passed: %d" % count, flush=True)


if __name__ == "__main__":
    unittest.main()
